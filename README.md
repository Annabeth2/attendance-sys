# Attendance Management System

A modern attendance management system that supports both Bluetooth-based and manual attendance tracking.

## Features

- User authentication (Lecturers and Students)
- Bluetooth-based attendance tracking
- Manual attendance marking for lecturers
- Real-time attendance monitoring
- Attendance reports and statistics
- Unit management
- Student enrollment tracking

## Prerequisites

- Python 3.8 or later
- Windows 10 or later (for Bluetooth functionality)
- Git (for cloning the repository)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/attendance-system.git
cd attendance-system
```

2. Run the start script:
```bash
start.bat
```

The script will:
- Create a virtual environment
- Install dependencies
- Set up the database
- Start the backend server (port 8000)
- Start the frontend server (port 3000)

## Usage

1. Access the frontend at http://localhost:3000
2. Register a new account:
   - For lecturers: Use the registration form
   - For students: Use the registration form with your admission number and Bluetooth address

3. Log in with your credentials

## Development

The project structure:
```
attendance_system/
├── backend/           # FastAPI backend
│   ├── main.py       # Main application
│   ├── models.py     # Database models
│   ├── schemas.py    # Pydantic schemas
│   └── database.py   # Database configuration
├── frontend/         # Frontend files
│   ├── index.html    # Main page
│   ├── login.html    # Login page
│   └── serve.py      # Frontend server
└── start.bat         # Startup script
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 