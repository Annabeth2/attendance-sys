from database import Base, engine, DATA_DIR, DB_PATH, init_db, logger
from models import User, Unit, Enrollment, Attendance
import os
import sys
import shutil

def recreate_database():
    """Recreate the database from scratch."""
    try:
        # Backup existing database if it exists
        if os.path.exists(DB_PATH):
            backup_path = f"{DB_PATH}.backup"
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Created backup at {backup_path}")
            
            # Remove existing database file
            os.remove(DB_PATH)
            logger.info(f"Removed existing database at {DB_PATH}")

        # Create all tables
        init_db()
        logger.info("Created new database with updated schema")
        
        return True
    except Exception as e:
        logger.error(f"Error recreating database: {e}")
        return False

if __name__ == "__main__":
    try:
        success = recreate_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 