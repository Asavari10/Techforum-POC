"""Setup test database"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import pymysql
from src.payment_service.api import create_app

def setup_test_database():
    """Create and setup test database"""
    try:
        # Connect to MySQL server
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create test database
            test_db = os.getenv('MYSQL_TEST_DATABASE', 'payment_system_test')
            cursor.execute(f"DROP DATABASE IF EXISTS `{test_db}`")
            cursor.execute(f"CREATE DATABASE `{test_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
        connection.commit()
        print(f"Test database '{test_db}' created successfully")
        
        # Create tables
        app = create_app('testing')
        with app.app_context():
            from src.models.payment_models import db
            db.create_all()
            print("Test database tables created successfully")
        
    except Exception as e:
        print(f"Error setting up test database: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    setup_test_database()