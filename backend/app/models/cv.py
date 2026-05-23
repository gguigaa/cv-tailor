from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CVProfile(Base):
    __tablename__ = "cv_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    cv_pt = Column(Text, nullable=True)   # Master CV em português
    cv_en = Column(Text, nullable=True)   # Master CV em inglês
    base_prompt = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    accent_color = Column(String(7), nullable=True)  # ex: "#2a5f4b"

    user = relationship("User", back_populates="cv_profile")


class GeneratedCV(Base):
    __tablename__ = "generated_cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_description = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    lang = Column(String(2), default="pt")
    prompt_used = Column(Text, nullable=True)
    cv_snapshot = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="generated_cvs")
