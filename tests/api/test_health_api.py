"""API Tests for Health and System endpoints"""
import pytest
import json

class TestHealthAPI:
    """Test Health check API"""
    
    def test_health_check_response_format(self, client):
        """Test health check API response format"""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = response.get_json()
        
        # Required fields
        required_fields = ['status', 'service', 'database', 'version']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Value validation
        assert data['status'] == 'healthy'
        assert data['service'] == 'payment-api'
        assert data['database'] in ['connected', 'error']
        assert isinstance(data['version'], str)
    
    def test_health_check_performance(self, client):
        """Test health check response time"""
        import time
        
        start_time = time.time()
        response = client.get('/health')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Health check should be fast (under 1 second)
        assert response_time < 1.0
        assert response.status_code == 200