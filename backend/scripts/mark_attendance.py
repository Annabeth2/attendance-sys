import requests
import json

def mark_attendance():
    # First get the token
    token_response = requests.post(
        "http://127.0.0.1:8000/token",
        data={"username": "wesley", "password": "wesley123"}
    )
    
    if token_response.status_code != 200:
        print("Failed to get token:", token_response.text)
        return
        
    token = token_response.json()["access_token"]
    
    # Now mark attendance
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "user_id": 1,
        "unit_id": 1,
        "attendance_type": "MANUAL",
        "bluetooth_address": "00:1F:47:EF:9A:47"
    }
    
    response = requests.post(
        "http://127.0.0.1:8000/attendance/mark",
        headers=headers,
        json=data
    )
    
    print("Response:", response.text)

if __name__ == "__main__":
    mark_attendance() 