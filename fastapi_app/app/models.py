from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    LargeBinary,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    phone_number = Column(String(50), unique=True, nullable=True, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(50), nullable=False, default="consumer")
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    predictions = relationship("Prediction", back_populates="user")
    ponds = relationship("Pond", back_populates="owner")
    reports = relationship("Report", back_populates="owner")


class Pond(Base):
    __tablename__ = "ponds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    estimated_area = Column(Float, nullable=True)
    fish_species = Column(Text, nullable=True)
    geo_image_content_type = Column(String(64), nullable=True)
    geo_image_data = Column(LargeBinary, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="ponds")
    reports = relationship("Report", back_populates="pond")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pond_id = Column(Integer, ForeignKey("ponds.id"), nullable=False)
    report_name = Column(String(200), nullable=False)
    symptoms = Column(Text, nullable=False)
    photo_content_type = Column(String(64), nullable=True)
    photo_data = Column(LargeBinary, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="reports")
    pond = relationship("Pond", back_populates="reports")


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(256), nullable=False)
    image_content_type = Column(String(64), nullable=True)
    image_data = Column(LargeBinary, nullable=False)
    species = Column(String(150), nullable=False)
    species_confidence = Column(Float, nullable=False)
    species_confidence_percent = Column(String(50), nullable=False)
    disease_status = Column(String(100), nullable=False)
    disease_confidence = Column(Float, nullable=False)
    disease_confidence_percent = Column(String(50), nullable=False)
    yolo_confidence = Column(Float, nullable=False)
    yolo_confidence_percent = Column(String(50), nullable=False)
    is_valid_detection = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    detection_count = Column(Integer, nullable=False)
    all_class_probabilities = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="predictions")
