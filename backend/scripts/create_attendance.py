from database import SessionLocal
from models import User, Unit, Enrollment, Attendance, AttendanceType
from datetime import datetime

def create_attendance():
    db = SessionLocal()
    try:
        # Get Wesley's user
        wesley = db.query(User).filter(User.username == "wesley").first()
        if not wesley:
            print("Wesley not found")
            return

        # Create INTE 324 unit
        inte324 = Unit(
            code="INTE 324",
            name="Software Engineering",
            lecturer_id=1  # Assuming lecturer ID 1 exists
        )
        db.add(inte324)
        db.commit()

        # Enroll Wesley in INTE 324
        enrollment = Enrollment(
            user_id=wesley.id,
            unit_id=inte324.id
        )
        db.add(enrollment)
        db.commit()

        # Create attendance record
        attendance = Attendance(
            user_id=wesley.id,
            unit_id=inte324.id,
            attendance_type=AttendanceType.MANUAL,
            bluetooth_address=wesley.bluetooth_address,
            marked_at=datetime.utcnow()
        )
        db.add(attendance)
        db.commit()

        print("Created attendance record for Wesley in INTE 324")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_attendance() 