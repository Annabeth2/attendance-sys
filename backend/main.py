from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import jwt
from passlib.context import CryptContext
from models import Base, User, Unit, Enrollment, Attendance, UserRole, AttendanceType
from database import SessionLocal, engine
from schemas import (
    UserCreate, User as UserSchema, 
    UnitCreate, Unit as UnitSchema, 
    Attendance as AttendanceSchema,
    AttendanceSummary
)
import logging
from pydantic import BaseModel
from bluetooth_scanner import BluetoothScanner, start_scanner, stop_scanner
import asyncio
import traceback
from sqlalchemy import text
import re
from sqlalchemy.sql import func

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Attendance System API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add custom middleware to handle CORS headers in every response
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    # Allow requests from any origin in development
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
    return response

# Security
SECRET_KEY = "your-secret-key"  # Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
                "admission_number": user.admission_number
            }
        }
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/token/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=UserSchema)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Validate admission number for students
    if user.role == UserRole.STUDENT:
        if not user.admission_number:
            raise HTTPException(status_code=400, detail="Admission number is required for students")
        
        # Validate admission number format
        admission_pattern = r'^\d{4}/\d{2}/\d{4}/\d{2}/\d{2}$'
        if not re.match(admission_pattern, user.admission_number):
            raise HTTPException(
                status_code=400, 
                detail="Invalid admission number format. Use xxxx/xx/xxxx/xx/xx (e.g., 2023/01/1234/01/01)"
            )
        
        db_user = db.query(User).filter(User.admission_number == user.admission_number).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Admission number already registered")
    
    # Validate bluetooth_address for students
    if user.role == UserRole.STUDENT and not user.bluetooth_address:
        raise HTTPException(status_code=400, detail="Bluetooth address is required for students")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role=user.role,
        bluetooth_address=user.bluetooth_address,
        full_name=user.full_name,
        admission_number=user.admission_number
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    try:
        logger.info(f"User role: {current_user.role}")  # Debug log
        return current_user
    except Exception as e:
        logger.error(f"Error in read_users_me: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None

@app.put("/users/me", response_model=UserSchema)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Update user fields if provided
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        if user_update.email is not None:
            current_user.email = user_update.email
        if user_update.phone is not None:
            current_user.phone = user_update.phone
        if user_update.department is not None:
            current_user.department = user_update.department

        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/units", response_model=UnitSchema)
def create_unit(unit: UnitCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=403, detail="Only lecturers can create units")
    
    unit_data = unit.model_dump()
    unit_data["lecturer_id"] = current_user.id
    db_unit = Unit(**unit_data)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.get("/units", response_model=List[UnitSchema])
def get_units(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == UserRole.LECTURER:
        return db.query(Unit).filter(Unit.lecturer_id == current_user.id).all()
    else:
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()
        unit_ids = [enrollment.unit_id for enrollment in enrollments]
        return db.query(Unit).filter(Unit.id.in_(unit_ids)).all()

@app.post("/enroll/{unit_id}")
def enroll_in_unit(unit_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can enroll in units")
    
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Check if already enrolled
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.unit_id == unit_id
    ).first()
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this unit")
    
    enrollment = Enrollment(user_id=current_user.id, unit_id=unit_id)
    db.add(enrollment)
    db.commit()
    return {"message": "Enrolled successfully"}

@app.get("/enrolled-units", response_model=List[UnitSchema])
def get_enrolled_units(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can view enrolled units")
    
    enrollments = db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    unit_ids = [enrollment.unit_id for enrollment in enrollments]
    return db.query(Unit).filter(Unit.id.in_(unit_ids)).all()

class BroadcastStart(BaseModel):
    unit_id: int

@app.post("/bluetooth/start-broadcast")
async def start_bluetooth_broadcast(
    broadcast: BroadcastStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=403, detail="Only lecturers can start Bluetooth broadcast")
    
    unit = db.query(Unit).filter(Unit.id == broadcast.unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    if unit.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to broadcast for this unit")
    
    # Generate a unique Bluetooth beacon ID for this session
    beacon_id = f"{current_user.id}_{broadcast.unit_id}_{datetime.utcnow().timestamp()}"
    
    # Start the Bluetooth scanner with broadcast info
    broadcast_info = {
        "beacon_id": beacon_id,
        "unit_id": broadcast.unit_id,
        "unit_code": unit.code,
        "lecturer_id": current_user.id
    }
    await start_scanner(broadcast_info)
    
    return {
        "beacon_id": beacon_id,
        "unit_id": broadcast.unit_id,
        "lecturer_name": current_user.full_name or current_user.username,
        "unit_code": unit.code
    }

@app.post("/bluetooth/stop-broadcast")
async def stop_bluetooth_broadcast(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=403, detail="Only lecturers can stop Bluetooth broadcast")
    
    await stop_scanner()
    return {"message": "Bluetooth broadcast stopped successfully"}

@app.post("/bluetooth/mark-attendance")
async def mark_bluetooth_attendance(
    beacon_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can mark attendance via Bluetooth")
    
    if not current_user.bluetooth_address:
        raise HTTPException(status_code=400, detail="Student must have a registered Bluetooth MAC address")
    
    try:
        # Parse beacon_id to get unit_id and timestamp
        lecturer_id, unit_id, timestamp = beacon_id.split('_')
        unit_id = int(unit_id)
        timestamp = float(timestamp)
        
        # Check if beacon is still valid (within last 5 minutes)
        if datetime.utcnow().timestamp() - timestamp > 300:  # 5 minutes
            raise HTTPException(status_code=400, detail="Bluetooth beacon has expired")
        
        # Check if student is enrolled
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.unit_id == unit_id
        ).first()
        if not enrollment:
            raise HTTPException(status_code=400, detail="Not enrolled in this unit")
        
        # Check if attendance already marked for today
        today = datetime.utcnow().date()
        existing_attendance = db.query(Attendance).filter(
            Attendance.user_id == current_user.id,
            Attendance.unit_id == unit_id,
            Attendance.marked_at >= today
        ).first()
        if existing_attendance:
            raise HTTPException(status_code=400, detail="Already marked attendance for this unit today")
        
        # Check if the student's device was detected by the scanner
        if not scanner.is_device_detected(str(current_user.id)):
            raise HTTPException(status_code=400, detail="Your device was not detected in the classroom")
        
        # Create attendance record
        attendance = Attendance(
            user_id=current_user.id,
            unit_id=unit_id,
            attendance_type=AttendanceType.BLUETOOTH,
            bluetooth_address=current_user.bluetooth_address
        )
        db.add(attendance)
        db.commit()
        
        return {
            "message": "Attendance marked successfully",
            "mac_address": current_user.bluetooth_address
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid beacon ID")

@app.get("/attendance/student", response_model=List[AttendanceSummary])
async def get_student_attendance(
    current_user: User = Depends(get_current_user),
    unit_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can access this endpoint")
    
    # Get all units the student is enrolled in
    query = db.query(Enrollment).filter(Enrollment.user_id == current_user.id)
    if unit_id:
        query = query.filter(Enrollment.unit_id == unit_id)
    
    enrollments = query.all()
    
    attendance_summaries = []
    for enrollment in enrollments:
        # Get attendance records for this unit
        attendance_records = db.query(Attendance).filter(
            Attendance.user_id == current_user.id,
            Attendance.unit_id == enrollment.unit_id
        ).all()
        
        # Calculate attendance percentage
        attended_classes = len(attendance_records)
        percentage = (attended_classes / 12) * 100  # 12 classes per unit
        
        # Add percentage to each record
        for record in attendance_records:
            record.percentage = percentage
            record.attended_classes = attended_classes
        
        attendance_summaries.append(AttendanceSummary(
            unit_id=enrollment.unit_id,
            unit_code=enrollment.unit.code,
            unit_name=enrollment.unit.name,
            attended_classes=attended_classes,
            percentage=percentage,
            attendance_records=attendance_records,
            user=current_user
        ))
    
    return attendance_summaries

@app.get("/attendance/lecturer", response_model=List[AttendanceSummary])
async def get_lecturer_attendance(
    current_user: User = Depends(get_current_user),
    unit_id: Optional[int] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=403, detail="Only lecturers can access this endpoint")
    
        # Get all units taught by the lecturer
    query = db.query(Unit).filter(Unit.lecturer_id == current_user.id)
    if unit_id:
        query = query.filter(Unit.id == unit_id)
    
    units = query.all()
    
    attendance_summaries = []
    for unit in units:
        # Get attendance records for this unit with user information
        query = db.query(Attendance).join(
            User, 
            Attendance.user_id == User.id  # Explicitly specify the join condition
        ).filter(Attendance.unit_id == unit.id)
        
        if date:
            query = query.filter(func.date(Attendance.marked_at) == date)
        
        attendance_records = query.all()
        
        # Group attendance by student
        student_attendance = {}
        for record in attendance_records:
            if record.user_id not in student_attendance:
                student_attendance[record.user_id] = []
            student_attendance[record.user_id].append(record)
        
        # Calculate attendance percentage for each student
        for student_id, records in student_attendance.items():
            attended_classes = len(records)
            percentage = (attended_classes / 12) * 100  # 12 classes per unit
            
            # Add percentage to each record
            for record in records:
                record.percentage = percentage
                record.attended_classes = attended_classes
        
        attendance_summaries.append(AttendanceSummary(
            unit_id=unit.id,
            unit_code=unit.code,
            unit_name=unit.name,
            attended_classes=len(attendance_records),
            percentage=(len(attendance_records) / (12 * len(student_attendance))) * 100 if student_attendance else 0,
            attendance_records=attendance_records
        ))
    
    return attendance_summaries

@app.get("/units/available", response_model=List[UnitSchema])
def get_available_units(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can view available units")
    
    # Get all units
    all_units = db.query(Unit).all()
    
    # Get units the student is already enrolled in
    enrolled_units = db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    enrolled_unit_ids = [enrollment.unit_id for enrollment in enrolled_units]
    
    # Filter out units the student is already enrolled in
    available_units = [unit for unit in all_units if unit.id not in enrolled_unit_ids]
    
    return available_units

@app.get("/enrollments/student", response_model=List[UnitSchema])
def get_student_enrollments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can view their enrollments")
    
    # Get all enrollments for the student
    enrollments = db.query(Enrollment).filter(Enrollment.user_id == current_user.id).all()
    
    # Get the corresponding
    unit_ids = [enrollment.unit_id for enrollment in enrollments]
    units = db.query(Unit).filter(Unit.id.in_(unit_ids)).all()
    
    return units

@app.delete("/enroll/{unit_id}")
def unenroll_from_unit(unit_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can unenroll from units")
    
    # Check if enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.unit_id == unit_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this unit")
    
    # Check if attendance has been marked for this unit
    attendance_exists = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        Attendance.unit_id == unit_id
    ).first()
    
    if attendance_exists:
        raise HTTPException(
            status_code=400, 
            detail="Cannot drop this unit because attendance has already been marked. Please contact your lecturer for assistance."
        )
    
    db.delete(enrollment)
    db.commit()
    return {"message": "Successfully unenrolled from unit"}

class AttendanceCreate(BaseModel):
    unit_id: int
    attendance_type: AttendanceType
    latitude: float
    longitude: float
    timestamp: datetime

@app.post("/attendance", response_model=AttendanceSchema)
def create_attendance(attendance: AttendanceCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can mark attendance")
    
    db = SessionLocal()
    try:
        # Check if student is enrolled in the unit
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_id == current_user.id,
            Enrollment.unit_id == attendance.unit_id
        ).first()
        
        if not enrollment:
            raise HTTPException(status_code=403, detail="You are not enrolled in this unit")
        
        # Check if attendance already marked for this unit today
        today = datetime.now().date()
        existing_attendance = db.query(Attendance).filter(
            Attendance.student_id == current_user.id,
            Attendance.unit_id == attendance.unit_id,
            Attendance.timestamp >= today
        ).first()
        
        if existing_attendance:
            raise HTTPException(status_code=400, detail="Attendance already marked for this unit today")
        
        # Create attendance record
        db_attendance = Attendance(
            student_id=current_user.id,
            unit_id=attendance.unit_id,
            attendance_type=attendance.attendance_type,
            latitude=attendance.latitude,
            longitude=attendance.longitude,
            timestamp=attendance.timestamp
        )
        
        db.add(db_attendance)
        db.commit()
        db.refresh(db_attendance)
        return db_attendance
    finally:
        db.close()

# Initialize the Bluetooth scanner
scanner = BluetoothScanner()

@app.on_event("startup")
async def startup_event():
    # Initialize the scanner but don't start scanning
    logger.info("Bluetooth scanner initialized")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    if scanner:
        await stop_scanner()
    logger.info("Bluetooth scanner stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint to monitor system status"""
    try:
        # Check database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        # Check Bluetooth scanner status
        scanner_status = "running" if scanner.scanning else "stopped"
        
        # Get system metrics
        metrics = {
            "database": "healthy",
            "bluetooth_scanner": scanner_status,
            "detected_devices": len(scanner.detected_devices),
            "uptime": datetime.utcnow() - scanner.start_time if hasattr(scanner, 'start_time') else None
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@app.get("/debug/bluetooth")
async def debug_bluetooth():
    """Debug endpoint for Bluetooth functionality"""
    try:
        return {
            "scanner_status": "running" if scanner.scanning else "stopped",
            "detected_devices": [
                {
                    "address": address,
                    "last_seen": last_seen.isoformat()
                }
                for address, last_seen in scanner.detected_devices.items()
            ],
            "last_error": str(scanner.last_error) if hasattr(scanner, 'last_error') else None
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# Add new endpoint for manual attendance marking
class ManualAttendanceCreate(BaseModel):
    unit_id: int
    admission_number: str
    attendance_type: AttendanceType = AttendanceType.MANUAL

@app.post("/attendance/manual", response_model=AttendanceSchema)
def mark_manual_attendance(
    attendance: ManualAttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.LECTURER:
        raise HTTPException(status_code=403, detail="Only lecturers can mark manual attendance")
    
    # Get the unit and verify lecturer owns it
    unit = db.query(Unit).filter(Unit.id == attendance.unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    if unit.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to mark attendance for this unit")
    
    # Find student by admission number
    student = db.query(User).filter(
        User.admission_number == attendance.admission_number,
        User.role == UserRole.STUDENT
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if student is enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == student.id,
        Enrollment.unit_id == attendance.unit_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this unit")
    
    # Check if attendance already marked for today
    today = datetime.utcnow().date()
    existing_attendance = db.query(Attendance).filter(
        Attendance.user_id == student.id,
        Attendance.unit_id == attendance.unit_id,
        Attendance.marked_at >= today
    ).first()
    if existing_attendance:
        raise HTTPException(status_code=400, detail="Attendance already marked for this student today")
    
    # Create attendance record
    db_attendance = Attendance(
        user_id=student.id,
        unit_id=attendance.unit_id,
        attendance_type=attendance.attendance_type,
        marked_by=current_user.id
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
