"""
FastAPI application for Fish Species Detection
Three-stage pipeline: YOLOv8s (detection) → EfficientNetB3 (classification) → SavedModel Disease Detection (health)
"""
import base64
import json
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Prediction, Pond, Report, RevokedToken
from app.utils.model_loader import ModelLoader
from app.utils.image_processor import ImageProcessor
from app.schemas.models import (
    PredictionResult,
    PredictionHistoryItem,
    UserCreate,
    FarmerCreate,
    UserResponse,
    PondResponse,
    ReportResponse,
    LoginRequest,
    Token,
    TokenData,
    HealthCheckResponse,
    ErrorResponse,
    AdminPondResponse,
    AdminReportResponse,
    ClassProbability
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for models
YOLO_MODEL = None
EFFICIENTNET_MODEL = None
DISEASE_MODEL = None
CLASS_NAMES = None

# Configuration
MODEL_BASE_PATH = os.path.join(os.path.dirname(__file__), '..', '..')
YOLO_MODEL_PATH = os.path.join(MODEL_BASE_PATH, 'best.pt')
EFFICIENTNET_MODEL_PATH = os.path.join(MODEL_BASE_PATH, 'best_pt_folder')  # or best.h5
CLASS_MAP_PATH = os.path.join(MODEL_BASE_PATH, 'clf_class_names.json')
DISEASE_MODEL_PATH = os.path.join(MODEL_BASE_PATH, 'model', 'Disease_model', 'saved_model')

# Check if using local models or from best_pt_folder
if not os.path.exists(YOLO_MODEL_PATH):
    YOLO_MODEL_PATH = os.path.join(MODEL_BASE_PATH, 'best_pt_folder', 'best.pt')

EFFICIENTNET_H5_PATH = os.path.join(MODEL_BASE_PATH, 'efficientnet_fish.h5')
if not os.path.exists(CLASS_MAP_PATH):
    CLASS_MAP_PATH = os.path.join(MODEL_BASE_PATH, 'best_pt_folder', 'clf_class_names.json')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown event handler
    """
    logger.info("=" * 60)
    logger.info("🚀 Fish Detection API Starting Up")
    logger.info("=" * 60)
    
    try:
        global YOLO_MODEL, EFFICIENTNET_MODEL, DISEASE_MODEL, CLASS_NAMES
        
        logger.info(f"YOLO Model Path: {YOLO_MODEL_PATH}")
        logger.info(f"EfficientNet Model Path: {EFFICIENTNET_H5_PATH}")
        logger.info(f"Disease Model Path: {DISEASE_MODEL_PATH}")
        logger.info(f"Class Map Path: {CLASS_MAP_PATH}")
        
        # Load models
        YOLO_MODEL, EFFICIENTNET_MODEL, DISEASE_MODEL, CLASS_NAMES = ModelLoader.setup_models(
            yolo_model_path=YOLO_MODEL_PATH,
            efficientnet_model_path=EFFICIENTNET_H5_PATH,
            disease_model_path=DISEASE_MODEL_PATH,
            class_map_path=CLASS_MAP_PATH
        )
        logger.info("✅ All models loaded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load models: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 Fish Detection API Shutting Down")
    logger.info("=" * 60)


# Create FastAPI app
app = FastAPI(
    title="🐟 Fish Species Detection API",
    description="Three-stage pipeline: YOLOv8s detection → EfficientNetB3 species classification → SavedModel disease detection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Authentication configuration
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-super-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_token_response(user: User) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        role=user.role
    )


def get_user(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def is_token_revoked(db: Session, jti: str) -> bool:
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        jti: str | None = payload.get("jti")
        if username is None or jti is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception

    if is_token_revoked(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


def get_current_consumer(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "consumer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consumer access only")
    return current_user


def get_current_farmer(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "farmer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Farmer access only")
    return current_user


def get_current_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access only")
    return current_user


def prediction_to_history_item(prediction: Prediction) -> PredictionHistoryItem:
    probabilities = json.loads(prediction.all_class_probabilities)
    return PredictionHistoryItem(
        id=prediction.id,
        filename=prediction.filename,
        species=prediction.species,
        species_confidence=prediction.species_confidence,
        species_confidence_percent=prediction.species_confidence_percent,
        yolo_confidence=prediction.yolo_confidence,
        yolo_confidence_percent=prediction.yolo_confidence_percent,
        is_valid_detection=prediction.is_valid_detection,
        all_class_probabilities=[ClassProbability(**prob) for prob in probabilities],
        disease_status=prediction.disease_status,
        disease_confidence=prediction.disease_confidence,
        disease_confidence_percent=prediction.disease_confidence_percent,
        message=prediction.message,
        detection_count=prediction.detection_count,
        created_at=prediction.created_at.isoformat(),
        image_url=f"/predictions/{prediction.id}/image"
    )


def pond_to_response(pond: Pond) -> PondResponse:
    species_list: List[str] = []
    if pond.fish_species:
        try:
            parsed = json.loads(pond.fish_species)
            if isinstance(parsed, list):
                species_list = [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, TypeError):
            species_list = []

    return PondResponse(
        id=pond.id,
        name=pond.name,
        latitude=pond.latitude,
        longitude=pond.longitude,
        estimated_area=pond.estimated_area,
        fish_species=species_list,
        verified=pond.verified,
        created_at=pond.created_at.isoformat(),
        image_url=f"/ponds/{pond.id}/image" if pond.geo_image_data else None
    )


def save_prediction(
    db: Session,
    user: User,
    filename: str,
    content_type: str | None,
    image_bytes: bytes,
    response: PredictionResult,
    class_probabilities: List[ClassProbability]
) -> Prediction:
    prediction = Prediction(
        user_id=user.id,
        filename=filename,
        image_content_type=content_type or "application/octet-stream",
        image_data=image_bytes,
        species=response.species,
        species_confidence=response.species_confidence,
        species_confidence_percent=response.species_confidence_percent,
        disease_status=response.disease_status,
        disease_confidence=response.disease_confidence,
        disease_confidence_percent=response.disease_confidence_percent,
        yolo_confidence=response.yolo_confidence,
        yolo_confidence_percent=response.yolo_confidence_percent,
        is_valid_detection=response.is_valid_detection,
        message=response.message,
        detection_count=response.detection_count,
        all_class_probabilities=json.dumps([prob.model_dump() for prob in class_probabilities])
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    response.prediction_id = prediction.id
    return prediction

# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check() -> HealthCheckResponse:
    """
    Check if API and models are ready
    """
    models_ready = ModelLoader.is_loaded()
    
    return HealthCheckResponse(
        status="✅ Healthy" if models_ready else "❌ Not Ready",
        yolo_model_loaded=YOLO_MODEL is not None,
        efficientnet_model_loaded=EFFICIENTNET_MODEL is not None,
        message="All models loaded and ready" if models_ready else "Models not yet loaded"
    )


@app.post(
    "/token",
    response_model=Token,
    tags=["Authentication"],
    summary="Login and obtain an access token"
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return create_token_response(user)


@app.post(
    "/login",
    response_model=Token,
    tags=["Authentication"],
    summary="Login using JSON credentials"
)
async def login(
    login_in: LoginRequest,
    db: Session = Depends(get_db)
) -> Token:
    user = authenticate_user(db, login_in.username, login_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return create_token_response(user)


@app.post(
    "/logout",
    tags=["Authentication"],
    summary="Logout current user and revoke the token"
)
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti: str | None = payload.get("jti")
        exp_timestamp = payload.get("exp")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token for logout"
        )

    if not jti or not exp_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload"
        )

    if not is_token_revoked(db, jti):
        revoked = RevokedToken(
            jti=jti,
            expires_at=datetime.utcfromtimestamp(exp_timestamp)
        )
        db.add(revoked)
        db.commit()

    return {"detail": "Successfully logged out"}


@app.post(
    "/consumer-register",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Register a new consumer account"
)
async def register_consumer(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_password = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        full_name=user_in.full_name or user_in.username,
        phone_number=user_in.phone_number,
        hashed_password=hashed_password,
        role="consumer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        disabled=user.disabled,
        phone_number=user.phone_number
    )


@app.post(
    "/farmer-register",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Register a new farmer account"
)
async def register_farmer(
    farmer_in: FarmerCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    existing_username = db.query(User).filter(User.username == farmer_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # phone number is required for farmer accounts
    if not farmer_in.phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is required for farmer registration"
        )
    existing_phone = db.query(User).filter(User.phone_number == farmer_in.phone_number).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    hashed_password = get_password_hash(farmer_in.password)
    user = User(
        username=farmer_in.username,
        full_name=farmer_in.full_name or farmer_in.username,
        phone_number=farmer_in.phone_number,
        hashed_password=hashed_password,
        role="farmer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        disabled=user.disabled,
        phone_number=user.phone_number
    )


@app.post(
    "/admin-register",
    response_model=UserResponse,
    tags=["Authentication"],
    summary="Register a new admin account"
)
async def register_admin(
    admin_in: FarmerCreate,
    db: Session = Depends(get_db)
) -> UserResponse:
    existing_username = db.query(User).filter(User.username == admin_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # allow admin phone number optional but ensure uniqueness if provided
    if admin_in.phone_number:
        existing_phone = db.query(User).filter(User.phone_number == admin_in.phone_number).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    hashed_password = get_password_hash(admin_in.password)
    user = User(
        username=admin_in.username,
        full_name=admin_in.full_name or admin_in.username,
        phone_number=admin_in.phone_number,
        hashed_password=hashed_password,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        disabled=user.disabled,
        phone_number=user.phone_number
    )


# ═══════════════════════════════════════════════════════════════
# PREDICTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.post(
    "/predict",
    response_model=PredictionResult,
    tags=["Prediction"],
    summary="Predict fish species from image"
)
async def predict_fish(
    file: UploadFile = File(
        ...,
        description="Image file (JPG, PNG, etc.)"
    ),
    current_user: User = Depends(get_current_consumer),
    db: Session = Depends(get_db)
) -> PredictionResult:
    """
    Upload fish image and get species + disease predictions
    
    **Three-Stage Pipeline:**
    1. **YOLO Detection**: Locates fish in image
    2. **EfficientNet Classification**: Classifies the detected fish species
    3. **Disease Detection(EfficientNetB0)**: Determines if fish is healthy or diseased
    
    **Request:**
    - Content-Type: multipart/form-data
    - file: Image binary data
    
    **Response includes:**
    - species: Predicted fish species (Catla, CommonCarp, Mori, Rohu, SilverCarp)
    - species_confidence: EfficientNet confidence (0-1)
    - disease_status: Health status (HEALTHY or DISEASED)
    - disease_confidence: TFLite disease model confidence (0-1)
    - yolo_confidence: YOLO detection confidence (0-1)
    - all_class_probabilities: Probabilities for all 5 fish species
    
    **Example Species:**
    - Catla
    - CommonCarp
    - Mori
    - Rohu
    - SilverCarp
    """
    
    # Validate models are loaded
    if not ModelLoader.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Models not loaded. Please try again in a few seconds."
        )
    
    try:
        logger.info(f"📥 Received prediction request for file: {file.filename}")
        
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            logger.warning(f"Invalid file type: {file_ext}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file bytes
        image_bytes = await file.read()
        
        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )
        
        logger.info(f"File size: {len(image_bytes) / 1024 / 1024:.2f} MB")
        
        # Run inference (three-stage pipeline: detection → species → disease)
        result_dict = ImageProcessor.run_inference(
            image_bytes=image_bytes,
            yolo_model=YOLO_MODEL,
            efficientnet_model=EFFICIENTNET_MODEL,
            disease_model=DISEASE_MODEL,
            class_names=CLASS_NAMES,
            yolo_conf=0.20
        )
        
        # Convert all_class_probabilities to ClassProbability objects
        class_probs = [
            ClassProbability(
                class_name=prob["class_name"],
                probability=prob["probability"],
                confidence_percent=prob["confidence_percent"]
            )
            for prob in result_dict["all_class_probabilities"]
        ]
        
        # Create response (includes disease status from stage 3)
        response = PredictionResult(
            success=result_dict["success"],
            species=result_dict["species"],
            species_confidence=result_dict["species_confidence"],
            species_confidence_percent=result_dict["species_confidence_percent"],
            disease_status=result_dict.get("disease_status", "UNKNOWN"),
            disease_confidence=result_dict.get("disease_confidence", 0.0),
            disease_confidence_percent=result_dict.get("disease_confidence_percent", "0%"),
            yolo_confidence=result_dict["yolo_confidence"],
            yolo_confidence_percent=result_dict["yolo_confidence_percent"],
            is_valid_detection=result_dict["is_valid_detection"],
            all_class_probabilities=class_probs,
            message=result_dict["message"],
            detection_count=result_dict["detection_count"]
        )
        save_prediction(
            db=db,
            user=current_user,
            filename=file.filename,
            content_type=file.content_type,
            image_bytes=image_bytes,
            response=response,
            class_probabilities=class_probs
        )
        
        logger.info(f"✅ Prediction complete: {response.species} ({response.species_confidence_percent})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Prediction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post(
    "/predict-batch",
    tags=["Prediction"],
    summary="Batch prediction (multiple images)"
)
async def predict_batch(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_consumer),
    db: Session = Depends(get_db)
):
    """
    Upload multiple fish images and get species + disease predictions for all
    
    **Three-Stage Pipeline (applied to each image):**
    1. YOLO Detection
    2. EfficientNet Species Classification
    3. TFLite Disease Detection
    
    **Limitations:**
    - Max 10 images per request
    - Processing is sequential (one after another)
    
    **Response includes disease status for each image**
    """
    
    if not ModelLoader.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Models not loaded"
        )
    
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images per request"
        )
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    results = []
    
    for file in files:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            logger.warning(f"Invalid file type for batch item: {file.filename}")
            results.append({
                "filename": file.filename,
                "error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            })
            continue

        try:
            image_bytes = await file.read()
            if not image_bytes:
                results.append({
                    "filename": file.filename,
                    "error": "Empty file uploaded"
                })
                continue
            
            result_dict = ImageProcessor.run_inference(
                image_bytes=image_bytes,
                yolo_model=YOLO_MODEL,
                efficientnet_model=EFFICIENTNET_MODEL,
                disease_model=DISEASE_MODEL,
                class_names=CLASS_NAMES,
                yolo_conf=0.20
            )
            
            class_probs = [
                ClassProbability(
                    class_name=prob["class_name"],
                    probability=prob["probability"],
                    confidence_percent=prob["confidence_percent"]
                )
                for prob in result_dict["all_class_probabilities"]
            ]

            response = PredictionResult(
                success=result_dict["success"],
                species=result_dict["species"],
                species_confidence=result_dict["species_confidence"],
                species_confidence_percent=result_dict["species_confidence_percent"],
                disease_status=result_dict.get("disease_status", "UNKNOWN"),
                disease_confidence=result_dict.get("disease_confidence", 0.0),
                disease_confidence_percent=result_dict.get("disease_confidence_percent", "0%"),
                yolo_confidence=result_dict["yolo_confidence"],
                yolo_confidence_percent=result_dict["yolo_confidence_percent"],
                is_valid_detection=result_dict["is_valid_detection"],
                all_class_probabilities=class_probs,
                message=result_dict["message"],
                detection_count=result_dict["detection_count"]
            )
            save_prediction(
                db=db,
                user=current_user,
                filename=file.filename,
                content_type=file.content_type,
                image_bytes=image_bytes,
                response=response,
                class_probabilities=class_probs
            )

            results.append({
                "filename": file.filename,
                "prediction": response
            })
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {str(e)}")
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {"batch_size": len(files), "results": results}


# ═══════════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════════

@app.get(
    "/predictions",
    response_model=List[PredictionHistoryItem],
    tags=["History"],
    summary="List previous predictions for the current consumer"
)
async def get_prediction_history(
    current_user: User = Depends(get_current_consumer),
    db: Session = Depends(get_db)
) -> List[PredictionHistoryItem]:
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return [prediction_to_history_item(pred) for pred in predictions]


@app.get(
    "/predictions/{prediction_id}",
    response_model=PredictionHistoryItem,
    tags=["History"],
    summary="Get detail for a single previous prediction"
)
async def get_prediction_detail(
    prediction_id: int,
    current_user: User = Depends(get_current_consumer),
    db: Session = Depends(get_db)
) -> PredictionHistoryItem:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction or prediction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    return prediction_to_history_item(prediction)


@app.get(
    "/predictions/{prediction_id}/image",
    tags=["History"],
    summary="Download the original image for a previous prediction"
)
async def get_prediction_image(
    prediction_id: int,
    current_user: User = Depends(get_current_consumer),
    db: Session = Depends(get_db)
):
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction or prediction.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )

    return StreamingResponse(
        iter([prediction.image_data]),
        media_type=prediction.image_content_type or "application/octet-stream"
    )


# ═══════════════════════════════════════════════════════════════
# FARMER POND ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post(
    "/ponds",
    response_model=PondResponse,
    tags=["Farmer"],
    summary="Create a new pond"
)
async def create_pond(
    name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    estimated_area: float = Form(...),
    fish_species: str = Form(...),
    geo_image: UploadFile = File(...),
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> PondResponse:
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    image_ext = os.path.splitext(geo_image.filename or "")[1].lower()
    if image_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed: {', '.join(sorted(allowed_extensions))}"
        )

    geo_image_bytes = await geo_image.read()
    if not geo_image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty geo-tagged image uploaded")

    species_list: List[str] = []
    try:
        parsed_species = json.loads(fish_species)
        if isinstance(parsed_species, list):
            species_list = [str(item).strip() for item in parsed_species if str(item).strip()]
        else:
            species_list = [part.strip() for part in fish_species.split(",") if part.strip()]
    except json.JSONDecodeError:
        species_list = [part.strip() for part in fish_species.split(",") if part.strip()]

    if not species_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fish_species must contain at least one species"
        )

    pond = Pond(
        user_id=current_user.id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        estimated_area=estimated_area,
        fish_species=json.dumps(species_list),
        geo_image_content_type=geo_image.content_type or "application/octet-stream",
        geo_image_data=geo_image_bytes,
        verified=False
    )
    db.add(pond)
    db.commit()
    db.refresh(pond)
    return pond_to_response(pond)


@app.get(
    "/ponds",
    response_model=List[PondResponse],
    tags=["Farmer"],
    summary="List ponds owned by the current farmer"
)
async def list_ponds(
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> List[PondResponse]:
    ponds = (
        db.query(Pond)
        .filter(Pond.user_id == current_user.id)
        .order_by(Pond.created_at.desc())
        .all()
    )
    return [pond_to_response(pond) for pond in ponds]


@app.get(
    "/ponds/{pond_id}",
    response_model=PondResponse,
    tags=["Farmer"],
    summary="Get details for a single farmer pond"
)
async def get_pond_detail(
    pond_id: int,
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> PondResponse:
    pond = db.query(Pond).filter(Pond.id == pond_id, Pond.user_id == current_user.id).first()
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond not found")
    return pond_to_response(pond)


@app.get(
    "/ponds/{pond_id}/image",
    tags=["Farmer"],
    summary="Download geo-tagged image for a farmer pond"
)
async def get_pond_image(
    pond_id: int,
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
):
    pond = db.query(Pond).filter(Pond.id == pond_id, Pond.user_id == current_user.id).first()
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond not found")
    if not pond.geo_image_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond image not found")

    return StreamingResponse(
        iter([pond.geo_image_data]),
        media_type=pond.geo_image_content_type or "application/octet-stream"
    )


# Admin endpoints for ponds
@app.get(
    "/admin/ponds",
    response_model=List[AdminPondResponse],
    tags=["Admin"],
    summary="List all ponds (pending first)"
)
async def admin_list_ponds(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> List[AdminPondResponse]:
    ponds = (
        db.query(Pond)
        .order_by(Pond.verified.asc(), Pond.created_at.desc())
        .all()
    )
    response = []
    for pond in ponds:
        species_list: List[str] = []
        if pond.fish_species:
            try:
                parsed = json.loads(pond.fish_species)
                if isinstance(parsed, list):
                    species_list = [str(item).strip() for item in parsed if str(item).strip()]
            except (json.JSONDecodeError, TypeError):
                species_list = []

        owner = pond.owner
        response.append(AdminPondResponse(
            id=pond.id,
            name=pond.name,
            latitude=pond.latitude,
            longitude=pond.longitude,
            estimated_area=pond.estimated_area,
            fish_species=species_list,
            verified=pond.verified,
            created_at=pond.created_at.isoformat(),
            image_url=f"/admin/ponds/{pond.id}/image" if pond.geo_image_data else None,
            owner_username=owner.username if owner else "",
            owner_phone=owner.phone_number if owner else None
        ))
    return response


@app.patch(
    "/admin/ponds/{pond_id}/verify",
    tags=["Admin"],
    summary="Set pond verification status (admin only)"
)
async def admin_verify_pond(
    pond_id: int,
    verified: bool,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond not found")
    pond.verified = bool(verified)
    db.add(pond)
    db.commit()
    db.refresh(pond)
    return {
        "id": pond.id,
        "verified": pond.verified
    }


@app.get(
    "/admin/ponds/{pond_id}/image",
    tags=["Admin"],
    summary="Download geo-tagged image for any pond (admin only)"
)
async def admin_get_pond_image(
    pond_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    pond = db.query(Pond).filter(Pond.id == pond_id).first()
    if not pond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond not found")
    if not pond.geo_image_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pond image not found")

    return StreamingResponse(
        iter([pond.geo_image_data]),
        media_type=pond.geo_image_content_type or "application/octet-stream"
    )


# ═══════════════════════════════════════════════════════════════
# FARMER REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post(
    "/reports",
    response_model=ReportResponse,
    tags=["Farmer"],
    summary="Create a new report for a pond"
)
async def create_report(
    pond_name: str = Form(...),
    report_name: str = Form(...),
    symptoms: str = Form(...),
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> ReportResponse:
    pond = db.query(Pond).filter(
        Pond.user_id == current_user.id,
        Pond.name == pond_name
    ).first()
    if not pond:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pond '{pond_name}' not found for this farmer"
        )

    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    file_ext = os.path.splitext(photo.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid photo type. Allowed: {', '.join(allowed_extensions)}")

    image_bytes = await photo.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty photo uploaded")

    report = Report(
        user_id=current_user.id,
        pond_id=pond.id,
        report_name=report_name,
        symptoms=symptoms,
        photo_content_type=photo.content_type or "image/jpeg",
        photo_data=image_bytes
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportResponse(
        id=report.id,
        report_name=report.report_name,
        symptoms=report.symptoms,
        pond_id=pond.id,
        pond_name=pond.name,
        created_at=report.created_at.isoformat(),
        verified=report.verified,
        photo_url=f"/reports/{report.id}/photo"
    )


@app.get(
    "/reports",
    response_model=List[ReportResponse],
    tags=["Farmer"],
    summary="List reports created by the current farmer"
)
async def list_reports(
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> List[ReportResponse]:
    reports = (
        db.query(Report)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    response = []
    for report in reports:
        response.append(ReportResponse(
            id=report.id,
            report_name=report.report_name,
            symptoms=report.symptoms,
            pond_id=report.pond_id,
            pond_name=report.pond.name if report.pond else "",
            created_at=report.created_at.isoformat(),
            verified=report.verified,
            photo_url=f"/reports/{report.id}/photo"
        ))
    return response


# Admin endpoints for reports
@app.get(
    "/admin/reports",
    response_model=List[AdminReportResponse],
    tags=["Admin"],
    summary="List all reports (pending first)"
)
async def admin_list_reports(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> List[AdminReportResponse]:
    reports = (
        db.query(Report)
        .order_by(Report.verified.asc(), Report.created_at.desc())
        .all()
    )
    response = []
    for report in reports:
        farmer = report.owner
        response.append(AdminReportResponse(
            id=report.id,
            report_name=report.report_name,
            symptoms=report.symptoms,
            pond_id=report.pond_id,
            pond_name=report.pond.name if report.pond else "",
            created_at=report.created_at.isoformat(),
            photo_url=f"/admin/reports/{report.id}/photo",
            verified=report.verified,
            farmer_username=farmer.username if farmer else "",
            farmer_phone=farmer.phone_number if farmer else None
        ))
    return response


@app.patch(
    "/admin/reports/{report_id}/verify",
    tags=["Admin"],
    summary="Set report verification status (admin only)"
)
async def admin_verify_report(
    report_id: int,
    verified: bool,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report.verified = bool(verified)
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "verified": report.verified
    }


@app.get(
    "/admin/reports/{report_id}/photo",
    tags=["Admin"],
    summary="Download report photo for any report (admin only)"
)
async def admin_get_report_photo(
    report_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not report.photo_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report photo not found")

    return StreamingResponse(
        iter([report.photo_data]),
        media_type=report.photo_content_type or "application/octet-stream"
    )


@app.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
    tags=["Farmer"],
    summary="Get details for a single farmer report"
)
async def get_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
) -> ReportResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    pond_name = report.pond.name if report.pond else ""
    return ReportResponse(
        id=report.id,
        report_name=report.report_name,
        symptoms=report.symptoms,
        pond_id=report.pond_id,
        pond_name=pond_name,
        created_at=report.created_at.isoformat(),
        verified=report.verified,
        photo_url=f"/reports/{report.id}/photo"
    )


@app.get(
    "/reports/{report_id}/photo",
    tags=["Farmer"],
    summary="Download the photo attached to a report"
)
async def get_report_photo(
    report_id: int,
    current_user: User = Depends(get_current_farmer),
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return StreamingResponse(
        iter([report.photo_data]),
        media_type=report.photo_content_type or "application/octet-stream"
    )


@app.get(
    "/",
    tags=["Info"],
    summary="API information"
)
async def root():
    """
    Root endpoint - returns API information
    """
    return {
        "api_name": "🐟 Fish Species Detection API",
        "version": "1.0.0",
        "description": "Three-stage fish detection pipeline: detection → species classification → disease detection",
        "endpoints": {
            "health": "/health",
            "token": "/token (POST)",
            "login": "/login (POST)",
            "logout": "/logout (POST)",
            "consumer_register": "/consumer-register (POST)",
            "farmer_register": "/farmer-register (POST)",
            "predict_single": "/predict (POST)",
            "predict_batch": "/predict-batch (POST)",
            "ponds": "/ponds",
            "reports": "/reports",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "token_expiry_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
        "supported_species": CLASS_NAMES if CLASS_NAMES else ["Loading..."],
        "models": {
            "detection": "YOLOv8s",
            "species_classification": "EfficientNetB3",
            "disease_detection": "EfficientNetB0 (SavedModel)"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
