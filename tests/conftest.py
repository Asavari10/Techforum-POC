"""Test configuration and fixtures"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.payment_service.api import create_app

@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    yield app

@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()