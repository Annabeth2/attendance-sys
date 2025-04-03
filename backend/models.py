from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base
from sqlalchemy.sql import func
from typing import Optional
from pydantic import BaseModel

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    LECTURER = "LECTURER"

class AttendanceType(str, enum.Enum):
    BLUETOOTH = "BLUETOOTH"
    MANUAL = "MANUAL"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole))
    bluetooth_address = Column(String, nullable=True)
    admission_number = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    units = relationship("Unit", back_populates="lecturer")
    enrollments = relationship("Enrollment", back_populates="user")
    attendances = relationship("Attendance", back_populates="user", foreign_keys="Attendance.user_id")
    marked_attendances = relationship("Attendance", back_populates="marked_by_user", foreign_keys="Attendance.marked_by")

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    lecturer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    lecturer = relationship("User", back_populates="units")
    enrollments = relationship("Enrollment", back_populates="unit")
    attendances = relationship("Attendance", back_populates="unit")

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    unit_id = Column(Integer, ForeignKey("units.id"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="enrollments")
    unit = relationship("Unit", back_populates="enrollments")

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    unit_id = Column(Integer, ForeignKey("units.id"))
    attendance_type = Column(Enum(AttendanceType))
    bluetooth_address = Column(String, nullable=True)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    marked_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="attendances", foreign_keys=[user_id])
    unit = relationship("Unit", back_populates="attendances")
    marked_by_user = relationship("User", back_populates="marked_attendances", foreign_keys=[marked_by])

class UserCreate(BaseModel):
    email: str
    username: str
    password: str
    role: UserRole
    bluetooth_address: Optional[str] = None
    full_name: Optional[str] = None
    admission_number: Optional[str] = None

class UserSchema(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole
    bluetooth_address: Optional[str] = None
    admission_number: Optional[str] = None

    class Config:
        from_attributes = True 