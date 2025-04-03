from database import SessionLocal
from models import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user():
    db = SessionLocal()
    try:
        # Create Wesley's account
        user = User(
            username="wesley",
            email="wesley@example.com",
            hashed_password=pwd_context.hash("wesley123"),
            role=UserRole.STUDENT,
            bluetooth_address="a4:12:32:b4:7b:49"
        )
        db.add(user)
        db.commit()
        print("Created Wesley's account")
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_user() 