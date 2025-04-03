from sqlalchemy import create_engine, text

SQLALCHEMY_DATABASE_URL = "sqlite:///./attendance.db"

def upgrade():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        # Create temporary table
        connection.execute(text("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR UNIQUE,
                username VARCHAR UNIQUE,
                full_name VARCHAR,
                hashed_password VARCHAR,
                role VARCHAR,
                bluetooth_address VARCHAR,
                admission_number VARCHAR(50) UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Copy data from old table to new table
        connection.execute(text("""
            INSERT INTO users_new (
                id, email, username, full_name, hashed_password, 
                role, bluetooth_address, is_active, created_at
            )
            SELECT id, email, username, full_name, hashed_password, 
                   role, bluetooth_address, is_active, created_at
            FROM users;
        """))
        
        # Drop old table
        connection.execute(text("DROP TABLE users;"))
        
        # Rename new table to old table name
        connection.execute(text("ALTER TABLE users_new RENAME TO users;"))
        
        connection.commit()

def downgrade():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        # Create temporary table without admission_number
        connection.execute(text("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR UNIQUE,
                username VARCHAR UNIQUE,
                full_name VARCHAR,
                hashed_password VARCHAR,
                role VARCHAR,
                bluetooth_address VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Copy data excluding admission_number
        connection.execute(text("""
            INSERT INTO users_new (
                id, email, username, full_name, hashed_password, 
                role, bluetooth_address, is_active, created_at
            )
            SELECT id, email, username, full_name, hashed_password, 
                   role, bluetooth_address, is_active, created_at
            FROM users;
        """))
        
        # Drop old table
        connection.execute(text("DROP TABLE users;"))
        
        # Rename new table to old table name
        connection.execute(text("ALTER TABLE users_new RENAME TO users;"))
        
        connection.commit()

if __name__ == "__main__":
    upgrade() 