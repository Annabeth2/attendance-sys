import requests
from models import UserRole

def create_test_accounts():
    base_url = "http://localhost:8000"
    
    # Create lecturer account
    lecturer_data = {
        "email": "lecturer@test.com",
        "username": "testlecturer",
        "password": "test123",
        "role": UserRole.LECTURER,
        "full_name": "Test Lecturer"
    }
    
    # Create student account
    student_data = {
        "email": "student@test.com",
        "username": "teststudent",
        "password": "test123",
        "role": UserRole.STUDENT,
        "full_name": "Test Student",
        "admission_number": "STU001",
        "bluetooth_address": "00:1F:47:EF:9A:47"
    }
    
    try:
        # Register lecturer
        response = requests.post(f"{base_url}/register", json=lecturer_data)
        if response.status_code == 200:
            print("Created lecturer account")
        else:
            print(f"Error creating lecturer account: {response.text}")
        
        # Register student
        response = requests.post(f"{base_url}/register", json=student_data)
        if response.status_code == 200:
            print("Created student account")
        else:
            print(f"Error creating student account: {response.text}")
        
        print("\nTest accounts created successfully!")
        print("\nLecturer Account:")
        print(f"Username: testlecturer")
        print(f"Password: test123")
        print("\nStudent Account:")
        print(f"Username: teststudent")
        print(f"Password: test123")
        print(f"Admission Number: STU001")
        print(f"Bluetooth Address: 00:1F:47:EF:9A:47")
        
    except Exception as e:
        print(f"Error creating test accounts: {str(e)}")

if __name__ == "__main__":
    create_test_accounts() 