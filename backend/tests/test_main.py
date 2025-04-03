import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from main import app, get_db
from database import Base
from models import User, Unit, Enrollment, Attendance, UserRole, AttendanceType
from passlib.context import CryptContext

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)

# Test data
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_user(test_db, username: str, role: UserRole, bluetooth_address: str = None):
    try:
        hashed_password = pwd_context.hash("testpassword")
        user = User(
            username=username,
            email=f"{username}@test.com",
            hashed_password=hashed_password,
            role=role,
            bluetooth_address=bluetooth_address
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user
    except:
        test_db.rollback()
        raise

def get_test_token(client, username: str):
    response = client.post("/token", data={
        "username": username,
        "password": "testpassword"
    })
    return response.json()["access_token"]

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture
def test_lecturer(test_db):
    return create_test_user(test_db, "testlecturer", UserRole.LECTURER)

@pytest.fixture
def test_student(test_db):
    return create_test_user(test_db, "teststudent", UserRole.STUDENT, "00:11:22:33:44:55")

@pytest.fixture
def test_unit(test_db, test_lecturer):
    unit = Unit(
        code="TEST101",
        name="Test Unit",
        lecturer_id=test_lecturer.id
    )
    test_db.add(unit)
    test_db.commit()
    test_db.refresh(unit)
    return unit

def test_register_student(client):
    response = client.post("/register", json={
        "username": "newstudent",
        "email": "newstudent@test.com",
        "password": "testpassword",
        "role": "student",
        "bluetooth_address": "00:11:22:33:44:55"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newstudent"
    assert data["role"] == "student"
    assert data["bluetooth_address"] == "00:11:22:33:44:55"

def test_register_lecturer(client):
    response = client.post("/register", json={
        "username": "newlecturer",
        "email": "newlecturer@test.com",
        "password": "testpassword",
        "role": "lecturer"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newlecturer"
    assert data["role"] == "lecturer"
    assert data["bluetooth_address"] is None

def test_login(client, test_student):
    response = client.post("/token", data={
        "username": "teststudent",
        "password": "testpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_create_unit(client, test_lecturer):
    token = get_test_token(client, "testlecturer")
    response = client.post("/units", 
        json={
            "code": "TEST101",
            "name": "Test Unit"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "TEST101"
    assert data["name"] == "Test Unit"

def test_enroll_in_unit(client, test_student, test_unit):
    token = get_test_token(client, "teststudent")
    response = client.post(f"/enroll/{test_unit.id}", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Enrolled successfully"

def test_mark_attendance(client, test_student, test_unit, test_db):
    token = get_test_token(client, "teststudent")
    # First enroll the student
    client.post(f"/enroll/{test_unit.id}", 
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Create a valid beacon ID
    beacon_id = f"1_{test_unit.id}_{datetime.utcnow().timestamp()}"
    
    response = client.post("/bluetooth/mark-attendance",
        params={"beacon_id": beacon_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Attendance marked successfully"
    assert data["mac_address"] == "00:11:22:33:44:55"

def test_get_student_attendance(client, test_student, test_unit):
    token = get_test_token(client, "teststudent")
    response = client.get("/attendance/student",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "metrics" in data
    assert "database" in data["metrics"]
    assert "bluetooth_scanner" in data["metrics"]

def test_debug_bluetooth(client):
    response = client.get("/debug/bluetooth")
    assert response.status_code == 200
    data = response.json()
    assert "scanner_status" in data
    assert "detected_devices" in data
    assert isinstance(data["detected_devices"], list) 