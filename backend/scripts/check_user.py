from database import SessionLocal
from models import User

def check_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "wesley").first()
        if user:
            print(f"User found: {user.username}")
            print(f"Bluetooth address: {user.bluetooth_address}")
            print(f"Role: {user.role}")
        else:
            print("User not found")
    finally:
        db.close()

if __name__ == "__main__":
    check_user() 