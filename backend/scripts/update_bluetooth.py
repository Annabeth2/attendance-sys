from database import SessionLocal
from models import User

def update_bluetooth():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "wesley").first()
        if user:
            user.bluetooth_address = "a4:12:32:b4:7b:49"
            db.commit()
            print("Updated Wesley's Bluetooth address")
        else:
            print("User not found")
    finally:
        db.close()

if __name__ == "__main__":
    update_bluetooth() 