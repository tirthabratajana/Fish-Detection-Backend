"""
Pydantic models for request/response schemas
"""
from typing import List, Optional
from pydantic import BaseModel


class ClassProbability(BaseModel):
    """Individual class probability"""
    class_name: str
    probability: float
    confidence_percent: str


class PredictionResult(BaseModel):
    """Complete prediction result from all three stages"""
    success: bool
    species: str
    species_confidence: float
    species_confidence_percent: str
    yolo_confidence: float
    yolo_confidence_percent: str
    is_valid_detection: bool
    all_class_probabilities: List[ClassProbability]
    disease_status: str
    disease_confidence: float
    disease_confidence_percent: str
    message: str
    detection_count: int
    prediction_id: Optional[int] = None


class PredictionHistoryItem(BaseModel):
    """Stored prediction history for a user"""
    id: int
    filename: str
    species: str
    species_confidence: float
    species_confidence_percent: str
    yolo_confidence: float
    yolo_confidence_percent: str
    is_valid_detection: bool
    all_class_probabilities: List[ClassProbability]
    disease_status: str
    disease_confidence: float
    disease_confidence_percent: str
    message: str
    detection_count: int
    created_at: str
    image_url: str


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class FarmerCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    phone_number: str


class UserResponse(BaseModel):
    username: str
    full_name: str
    role: str
    disabled: bool
    phone_number: Optional[str] = None


class PondResponse(BaseModel):
    id: int
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_area: Optional[float] = None
    fish_species: List[str] = []
    verified: bool
    created_at: str
    image_url: Optional[str] = None


class ReportCreate(BaseModel):
    pond_name: str
    report_name: str
    symptoms: str


class ReportResponse(BaseModel):
    id: int
    report_name: str
    symptoms: str
    pond_id: int
    pond_name: str
    created_at: str
    photo_url: str
    verified: bool


class AdminPondResponse(BaseModel):
    id: int
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    estimated_area: Optional[float] = None
    fish_species: List[str] = []
    verified: bool
    created_at: str
    image_url: Optional[str] = None
    owner_username: str
    owner_phone: Optional[str]


class AdminReportResponse(BaseModel):
    id: int
    report_name: str
    symptoms: str
    pond_id: int
    pond_name: str
    created_at: str
    photo_url: str
    verified: bool
    farmer_username: str
    farmer_phone: Optional[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    yolo_model_loaded: bool
    efficientnet_model_loaded: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool
    error: str
    details: str = None
