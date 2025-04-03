from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_base_dir():
    """Get the absolute path to the AppData directory."""
    app_data_dir = os.getenv('APPDATA')
    if not app_data_dir:
        raise Exception("APPDATA environment variable not found")
    
    base_dir = os.path.join(app_data_dir, 'attendance_system')
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# Get the base directory and create data directory
BASE_DIR = get_base_dir()
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Construct the path to the database file
DB_PATH = os.path.join(DATA_DIR, 'attendance.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

def setup_database():
    """Setup the database connection."""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    return engine, SessionLocal, Base

# Initialize database components
engine, SessionLocal, Base = setup_database()

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully") 