import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from bluetooth_scanner import BluetoothScanner
from models import User, Unit, Enrollment, Attendance, UserRole, AttendanceType
from passlib.context import CryptContext
import uuid
from database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture
def mock_device():
    return {
        "address": "00:11:22:33:44:55",
        "name": "Test Device",
        "rssi": -50
    }

@pytest.fixture
def mock_advertisement_data():
    return {
        "local_name": "Test Device",
        "service_data": {},
        "manufacturer_data": {}
    }

@pytest.fixture
def test_student(test_db):
    try:
        unique_id = str(uuid.uuid4())[:8]
        hashed_password = pwd_context.hash("testpassword")
        student = User(
            username=f"teststudent_{unique_id}",
            email=f"teststudent_{unique_id}@test.com",
            hashed_password=hashed_password,
            role=UserRole.STUDENT,
            bluetooth_address="00:11:22:33:44:55"
        )
        test_db.add(student)
        test_db.commit()
        test_db.refresh(student)
        return student
    except:
        test_db.rollback()
        raise

@pytest.fixture
def test_unit(test_db, test_student):
    try:
        unique_id = str(uuid.uuid4())[:8]
        unit = Unit(
            code=f"TEST{unique_id}",
            name=f"Test Unit {unique_id}",
            lecturer_id=1
        )
        test_db.add(unit)
        test_db.commit()
        test_db.refresh(unit)
        return unit
    except:
        test_db.rollback()
        raise

@pytest.fixture
def test_enrollment(test_db, test_student, test_unit):
    try:
        enrollment = Enrollment(
            user_id=test_student.id,
            unit_id=test_unit.id
        )
        test_db.add(enrollment)
        test_db.commit()
        test_db.refresh(enrollment)
        return enrollment
    except:
        test_db.rollback()
        raise

@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def scanner(db):
    scanner = BluetoothScanner(db=db)
    yield scanner
    asyncio.create_task(scanner.stop())

@pytest.mark.asyncio
async def test_scanner_initialization(scanner):
    assert scanner.scanning is False
    assert scanner.detected_devices == {}
    assert scanner.cleanup_task is None
    assert scanner.scanner is None

@pytest.mark.asyncio
async def test_scanner_start_stop(scanner):
    # Mock the BleakScanner
    with patch('bluetooth_scanner.BleakScanner') as mock_scanner:
        mock_scanner_instance = AsyncMock()
        mock_scanner.return_value = mock_scanner_instance
        
        # Start scanning
        await scanner.start()
        assert scanner.scanning is True
        assert scanner.cleanup_task is not None
        assert scanner.scanner is not None
        mock_scanner_instance.start.assert_called_once()
        
        # Stop scanning
        await scanner.stop()
        assert scanner.scanning is False
        assert scanner.cleanup_task is None
        assert scanner.scanner is None
        mock_scanner_instance.stop.assert_called_once()

@pytest.mark.asyncio
async def test_device_detection(scanner, db):
    # Create a test student
    student = User(
        username="test_student",
        email="test@example.com",
        role=UserRole.STUDENT,
        bluetooth_address="00:11:22:33:44:55"
    )
    db.add(student)
    db.commit()
    
    # Create a test unit and enrollment
    unit = Unit(
        code="TEST101",
        name="Test Unit",
        lecturer_id=1
    )
    db.add(unit)
    db.commit()
    
    enrollment = Enrollment(
        user_id=student.id,
        unit_id=unit.id
    )
    db.add(enrollment)
    db.commit()
    
    # Mock device detection
    device = MagicMock()
    device.address = "00:11:22:33:44:55"
    advertisement_data = MagicMock()
    
    # Call the callback
    await scanner.device_detection_callback(device, advertisement_data)
    
    # Check if device was detected
    assert device.address in scanner.detected_devices
    
    # Check if attendance was created
    attendance = db.query(Attendance).filter(
        Attendance.user_id == student.id,
        Attendance.unit_id == unit.id,
        Attendance.marked_at >= datetime.utcnow().date()
    ).first()
    
    assert attendance is not None
    assert attendance.attendance_type == AttendanceType.BLUETOOTH
    assert attendance.bluetooth_address == device.address

@pytest.mark.asyncio
async def test_cleanup_old_devices(scanner):
    # Add some test devices
    scanner.detected_devices = {
        "device1": datetime.utcnow(),
        "device2": datetime.utcnow()
    }
    
    # Start scanning to start cleanup task
    await scanner.start()
    
    # Wait for cleanup
    await asyncio.sleep(0.1)
    
    # Stop scanning
    await scanner.stop()
    
    # Check if cleanup task was cancelled
    assert scanner.cleanup_task is None

@pytest.mark.asyncio
async def test_process_device_no_student(scanner, db):
    # Test with non-existent device
    await scanner.process_device("00:11:22:33:44:55")
    
    # Check that no attendance was created
    attendance = db.query(Attendance).first()
    assert attendance is None

@pytest.mark.asyncio
async def test_process_device_existing_attendance(scanner, db):
    # Create a test student
    student = User(
        username="test_student",
        email="test@example.com",
        role=UserRole.STUDENT,
        bluetooth_address="00:11:22:33:44:55"
    )
    db.add(student)
    db.commit()
    
    # Create a test unit and enrollment
    unit = Unit(
        code="TEST101",
        name="Test Unit",
        lecturer_id=1
    )
    db.add(unit)
    db.commit()
    
    enrollment = Enrollment(
        user_id=student.id,
        unit_id=unit.id
    )
    db.add(enrollment)
    db.commit()
    
    # Create existing attendance
    existing_attendance = Attendance(
        user_id=student.id,
        unit_id=unit.id,
        attendance_type=AttendanceType.BLUETOOTH,
        bluetooth_address="00:11:22:33:44:55",
        marked_at=datetime.utcnow()
    )
    db.add(existing_attendance)
    db.commit()
    
    # Process device
    await scanner.process_device("00:11:22:33:44:55")
    
    # Check that no new attendance was created
    attendances = db.query(Attendance).filter(
        Attendance.user_id == student.id,
        Attendance.unit_id == unit.id,
        Attendance.marked_at >= datetime.utcnow().date()
    ).all()
    
    assert len(attendances) == 1
    assert attendances[0] == existing_attendance

@pytest.mark.asyncio
async def test_invalid_device_handling(scanner, mock_advertisement_data):
    # Create an invalid device object
    invalid_device = MagicMock()
    invalid_device.address = None
    
    await scanner.device_detection_callback(invalid_device, mock_advertisement_data)
    assert not any(device for device in scanner.detected_devices)

@pytest.mark.asyncio
async def test_error_handling(scanner):
    # Simulate an error during scanning
    scanner.scanning = True
    
    # Create a device that will cause an error
    error_device = MagicMock()
    error_device.address = "error_device"
    
    # Mock the process_device method to raise an exception
    async def mock_process_device(*args, **kwargs):
        raise Exception("Test error")
    
    scanner.process_device = mock_process_device
    
    # Try to process the device
    await scanner.device_detection_callback(error_device, MagicMock())
    
    # Check that the error was recorded
    assert scanner.last_error == "Test error"
    
    # Stop scanning
    await scanner.stop()
    assert scanner.scanning is False

@pytest.mark.asyncio
async def test_duplicate_attendance_prevention(scanner, test_db, test_student, test_unit, test_enrollment):
    scanner.db = test_db
    
    # Mark attendance first time
    await scanner.process_device(test_student.bluetooth_address)
    
    # Try to mark attendance again
    await scanner.process_device(test_student.bluetooth_address)
    
    # Verify only one attendance record exists
    attendances = test_db.query(Attendance).filter(
        Attendance.user_id == test_student.id,
        Attendance.unit_id == test_unit.id,
        Attendance.marked_at >= datetime.utcnow().date()
    ).all()
    
    assert len(attendances) == 1 