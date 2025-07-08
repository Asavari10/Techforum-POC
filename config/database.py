import os
from urllib.parse import quote_plus

class DatabaseConfig:
    @staticmethod
    def get_mysql_uri():
        """Construct MySQL URI from environment variables"""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        username = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_DATABASE', 'payment_system')
        
        # URL encode password to handle special characters
        encoded_password = quote_plus(password) if password else ''
        
        if encoded_password:
            return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
        else:
            return f"mysql+pymysql://{username}@{host}:{port}/{database}?charset=utf8mb4"
    
    @staticmethod
    def get_test_mysql_uri():
        """Get test database URI"""
        host = os.getenv('MYSQL_HOST', 'localhost')
        port = os.getenv('MYSQL_PORT', '3306')
        username = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', '')
        database = os.getenv('MYSQL_TEST_DATABASE', 'payment_system_test')
        
        encoded_password = quote_plus(password) if password else ''
        
        if encoded_password:
            return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
        else:
            return f"mysql+pymysql://{username}@{host}:{port}/{database}?charset=utf8mb4"