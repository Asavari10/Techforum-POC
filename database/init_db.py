"""Database initialization script"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import pymysql
from src.payment_service.api import create_app
from src.models.payment_models import db

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    try:
        # Connect to MySQL server (without specifying database)
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create main database
            main_db = os.getenv('MYSQL_DATABASE', 'payment_system')
            test_db = os.getenv('MYSQL_TEST_DATABASE', 'payment_system_test')
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{main_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{test_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
        connection.commit()
        print(f"Databases '{main_db}' and '{test_db}' created successfully")
        
    except Exception as e:
        print(f"Error creating databases: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()
    return True

def initialize_tables():
    """Initialize database tables"""
    try:
        app = create_app('development')
        
        with app.app_context():
            # Create all tables
            db.create_all()
            print("Database tables initialized successfully")
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Created tables: {tables}")
            
    except Exception as e:
        print(f"Error initializing tables: {e}")
        return False
    return True

if __name__ == "__main__":
    print("Initializing Payment System Database...")
    
    # Check if .env file exists
    env_file = project_root / '.env'
    if not env_file.exists():
        print("Error: .env file not found!")
        print(f"Please create .env file in: {env_file}")
        sys.exit(1)
    
    # Create databases
    if create_database_if_not_exists():
        # Initialize tables
        if initialize_tables():
            print("Database initialization complete!")
        else:
            print("Failed to initialize tables")
            sys.exit(1)
    else:
        print("Failed to create databases")
        sys.exit(1)