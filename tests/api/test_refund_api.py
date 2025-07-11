"""API Tests for Refund endpoints"""
import pytest
import json
import uuid

class TestRefundAPI:
    """Test Refund API endpoints"""
    
    def test_create_refund_api_contract(self, client):
        """Test refund creation API contract"""
        # First create and process a payment
        unique_id = str(uuid.uuid4())[:8]
        payment_payload = {
            'merchant_id': f'REFUND_MERCHANT_{unique_id}',
            'customer_id': f'REFUND_CUSTOMER_{unique_id}',
            'amount': 300.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        # Create payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_payload),
                                     content_type='application/json')
        payment_id = create_response.get_json()['payment']['id']
        
        # Process payment until successful
        for _ in range(5):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment_data = process_response.get_json()['payment']
                if payment_data['status'] == 'completed':
                    break
        
        if payment_data['status'] != 'completed':
            pytest.skip("Payment processing failed")
        
        # Test refund creation
        refund_payload = {
            'amount': 150.00,
            'reason': 'API Test Refund'
        }
        
        refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                     data=json.dumps(refund_payload),
                                     content_type='application/json')
        
        assert refund_response.status_code == 201
        
        data = refund_response.get_json()
        assert data['success'] is True
        assert 'refund' in data
        
        refund = data['refund']
        assert refund['amount'] == 150.00
        assert refund['reason'] == 'API Test Refund'
        assert refund['payment_id'] == payment_id
    
    def test_refund_validation_errors(self, client):
        """Test refund validation errors"""
        # Test refund on non-existent payment
        refund_payload = {'amount': 50.00}
        
        response = client.post('/api/v1/payments/non-existent/refund',
                              data=json.dumps(refund_payload),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'Payment not found' in data['errors'][0]


class TestTransactionAPI:
    """Test Transaction listing API"""
    
    def test_get_payment_transactions(self, client):
        """Test getting payment transactions"""
        # Create and process a payment
        unique_id = str(uuid.uuid4())[:8]
        payment_payload = {
            'merchant_id': f'TXN_MERCHANT_{unique_id}',
            'customer_id': f'TXN_CUSTOMER_{unique_id}',
            'amount': 100.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_payload),
                                     content_type='application/json')
        payment_id = create_response.get_json()['payment']['id']
        
        # Process payment
        client.post(f'/api/v1/payments/{payment_id}/process')
        
        # Get transactions
        txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
        
        assert txn_response.status_code == 200
        data = txn_response.get_json()
        assert data['success'] is True
        assert 'transactions' in data
        assert isinstance(data['transactions'], list)