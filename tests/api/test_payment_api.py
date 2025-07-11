"""API Tests - Focus on HTTP contracts, status codes, and response formats"""
import pytest
import json
import uuid
from decimal import Decimal

class TestPaymentAPI:
    """Test Payment API endpoints"""
    
    def test_create_payment_api_contract(self, client):
        """Test payment creation API contract"""
        unique_id = str(uuid.uuid4())[:8]
        
        payload = {
            'merchant_id': f'API_MERCHANT_{unique_id}',
            'customer_id': f'API_CUSTOMER_{unique_id}',
            'amount': 150.75,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'API Contract Test',
            'card_last_four': '4567',
            'card_type': 'VISA'
        }
        
        response = client.post('/api/v1/payments',
                              data=json.dumps(payload),
                              content_type='application/json')
        
        # Test status code
        assert response.status_code == 201
        
        # Test response structure
        data = response.get_json()
        assert 'success' in data
        assert 'payment' in data
        assert data['success'] is True
        
        # Test payment object structure
        payment = data['payment']
        required_fields = [
            'id', 'merchant_id', 'customer_id', 'amount', 'currency',
            'payment_method', 'status', 'created_at', 'updated_at'
        ]
        for field in required_fields:
            assert field in payment, f"Missing required field: {field}"
        
        # Test data types
        assert isinstance(payment['amount'], (int, float))
        assert isinstance(payment['created_at'], str)
        assert payment['status'] == 'pending'
    
    def test_create_payment_validation_errors(self, client):
        """Test API validation error responses"""
        test_cases = [
            # Missing required fields
            {
                'payload': {'amount': 100},
                'expected_errors': ['merchant_id', 'customer_id', 'payment_method']
            },
            # Invalid amount
            {
                'payload': {
                    'merchant_id': 'TEST_MERCHANT',
                    'customer_id': 'TEST_CUSTOMER',
                    'amount': -50,
                    'payment_method': 'credit_card'
                },
                'expected_errors': ['Amount must be at least']
            },
            # Invalid currency
            {
                'payload': {
                    'merchant_id': 'TEST_MERCHANT',
                    'customer_id': 'TEST_CUSTOMER',
                    'amount': 100,
                    'currency': 'INVALID',
                    'payment_method': 'credit_card'
                },
                'expected_errors': ['Currency INVALID not supported']
            },
            # Invalid payment method
            {
                'payload': {
                    'merchant_id': 'TEST_MERCHANT',
                    'customer_id': 'TEST_CUSTOMER',
                    'amount': 100,
                    'payment_method': 'invalid_method'
                },
                'expected_errors': ['Invalid payment method']
            }
        ]
        
        for case in test_cases:
            response = client.post('/api/v1/payments',
                                  data=json.dumps(case['payload']),
                                  content_type='application/json')
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['success'] is False
            assert 'errors' in data
            
            # Check if expected error messages are present
            error_text = ' '.join(data['errors'])
            for expected_error in case['expected_errors']:
                assert expected_error in error_text

    def test_get_payment_api_responses(self, client):
        """Test GET payment API responses"""
        # Test 404 for non-existent payment
        response = client.get('/api/v1/payments/non-existent-id')
        assert response.status_code == 404
        
        data = response.get_json()
        assert data['success'] is False
        assert 'errors' in data
        
        # Create a payment to test successful retrieval
        unique_id = str(uuid.uuid4())[:8]
        payment_payload = {
            'merchant_id': f'GET_TEST_{unique_id}',
            'customer_id': f'GET_CUSTOMER_{unique_id}',
            'amount': 99.99,
            'currency': 'EUR',
            'payment_method': 'debit_card'
        }
        
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_payload),
                                     content_type='application/json')
        
        payment_id = create_response.get_json()['payment']['id']
        
        # Test successful retrieval
        get_response = client.get(f'/api/v1/payments/{payment_id}')
        assert get_response.status_code == 200
        
        data = get_response.get_json()
        assert data['success'] is True
        assert data['payment']['id'] == payment_id
        assert data['payment']['amount'] == 99.99
    
    def test_list_payments_api_pagination(self, client):
        """Test payments listing API with pagination"""
        # Test default pagination
        response = client.get('/api/v1/payments')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'payments' in data
        assert 'total' in data
        assert 'offset' in data
        assert 'limit' in data
        assert isinstance(data['payments'], list)
        
        # Test custom pagination
        response = client.get('/api/v1/payments?limit=5&offset=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['limit'] == 5
        assert data['offset'] == 10
        
        # Test filtering
        response = client.get('/api/v1/payments?merchant_id=TEST_MERCHANT')
        assert response.status_code == 200
    
    def test_payment_processing_api(self, client):
        """Test payment processing API"""
        # Create a payment first
        unique_id = str(uuid.uuid4())[:8]
        payment_payload = {
            'merchant_id': f'PROCESS_TEST_{unique_id}',
            'customer_id': f'PROCESS_CUSTOMER_{unique_id}',
            'amount': 200.00,
            'currency': 'GBP',
            'payment_method': 'credit_card'
        }
        
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_payload),
                                     content_type='application/json')
        
        payment_id = create_response.get_json()['payment']['id']
        
        # Test processing
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        assert process_response.status_code == 200
        
        data = process_response.get_json()
        assert data['success'] is True
        assert data['payment']['status'] in ['completed', 'failed']
        
        # Test processing non-existent payment
        invalid_response = client.post('/api/v1/payments/invalid-id/process')
        assert invalid_response.status_code == 400


class TestPaymentAPIHeaders:
    """Test API headers and content types"""
    
    def test_content_type_validation(self, client):
        """Test API requires proper content type"""
        payload = {
            'merchant_id': 'TEST_MERCHANT',
            'customer_id': 'TEST_CUSTOMER',
            'amount': 100,
            'payment_method': 'credit_card'
        }
        
        # Test without content-type header
        response = client.post('/api/v1/payments', data=json.dumps(payload))
        # Should still work but test the behavior
        
        # Test with wrong content-type
        response = client.post('/api/v1/payments',
                              data=json.dumps(payload),
                              content_type='text/plain')
        # Should handle gracefully
    
    def test_api_response_headers(self, client):
        """Test API response headers"""
        response = client.get('/health')
        
        # Check CORS headers if enabled
        # assert 'Access-Control-Allow-Origin' in response.headers
        
        # Check content type
        assert response.content_type == 'application/json'


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        malformed_json = '{"merchant_id": "TEST", "amount":}'
        
        response = client.post('/api/v1/payments',
                              data=malformed_json,
                              content_type='application/json')
        
        assert response.status_code == 400
    
    def test_empty_request_body(self, client):
        """Test handling of empty request body"""
        response = client.post('/api/v1/payments',
                              data='',
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False