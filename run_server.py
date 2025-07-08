"""Main server runner script"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.payment_service.api import create_app

def main():
    """Run the payment API server"""
    app = create_app()
    
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Payment API Server...")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Health Check: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/health")
    print("-" * 50)
    
    try:
        app.run(debug=debug, host=host, port=port)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")

if __name__ == '__main__':
    main()