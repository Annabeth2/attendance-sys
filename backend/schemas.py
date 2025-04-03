from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, AttendanceType
import re

def validate_mac_address(mac: str) -> bool:
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(mac_pattern.match(mac))

def validate_admission_number_format(admission: str) -> bool:
    # Format: xxxx/xx/xxxx/xx/xx
    pattern = r'^\d{4}/\d{2}/\d{4}/\d{2}/\d{2}$'
    return bool(re.match(pattern, admission))

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: UserRole
    bluetooth_address: Optional[str] = None
    full_name: Optional[str] = None
    admission_number: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None

    @validator('bluetooth_address')
    def validate_bluetooth_address(cls, v, values):
        if 'role' in values and values['role'] == UserRole.STUDENT:
            if not v:
                raise ValueError('Bluetooth MAC address is required for students')
            if not validate_mac_address(v):
                raise ValueError('Invalid MAC address format. Use XX:XX:XX:XX:XX:XX')
        return v

    @validator('admission_number')
    def validate_admission_number(cls, v, values):
        if 'role' in values and values['role'] == UserRole.STUDENT:
            if not v:
                raise ValueError('Admission number is required for students')
            if not v.strip():
                raise ValueError('Admission number cannot be empty')
            if not validate_admission_number_format(v):
                raise ValueError('Invalid admission number format. Use xxxx/xx/xxxx/xx/xx')
        return v

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Unit schemas
class UnitBase(BaseModel):
    code: str
    name: str

class UnitCreate(UnitBase):
    lecturer_id: Optional[int] = None

class Unit(UnitBase):
    id: int
    lecturer_id: int

    class Config:
        from_attributes = True

# Enrollment schemas
class EnrollmentBase(BaseModel):
    user_id: int
    unit_id: int

class EnrollmentCreate(EnrollmentBase):
    pass

class Enrollment(EnrollmentBase):
    id: int
    enrolled_at: datetime
    user: User
    unit: Unit

    class Config:
        from_attributes = True

# Attendance schemas
class AttendanceBase(BaseModel):
    unit_id: int
    attendance_type: AttendanceType

class AttendanceCreate(AttendanceBase):
    pass

class Attendance(AttendanceBase):
    id: int
    user_id: int
    marked_at: Optional[datetime] = None
    percentage: Optional[float] = None
    total_classes: int = 12  # Total classes per unit per semester
    attended_classes: Optional[int] = None
    user: Optional[User] = None  # Add user relationship

    class Config:
        from_attributes = True

# Add new schema for attendance summary
class AttendanceSummary(BaseModel):
    unit_id: int
    unit_code: str
    unit_name: str
    total_classes: int = 12
    attended_classes: int
    percentage: float
    attendance_records: List[Attendance]
    user: Optional[User] = None

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None

class UserSchema(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: UserRole
    bluetooth_address: Optional[str] = None
    admission_number: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True 