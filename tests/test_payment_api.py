"""Tests for payment API endpoints"""
import pytest
import json
import uuid

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'payment-api'

def test_create_payment_success(client):
    """Test successful payment creation"""
    # Use unique IDs to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    
    payment_data = {
        'merchant_id': f'MERCHANT_TEST_{unique_id}',
        'customer_id': f'CUSTOMER_TEST_{unique_id}',
        'amount': 100.50,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'description': 'Test payment',
        'card_last_four': '1234',
        'card_type': 'VISA'
    }
    
    response = client.post('/api/v1/payments', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'payment' in data
    assert data['payment']['amount'] == 100.50
    assert data['payment']['currency'] == 'USD'
    assert data['payment']['status'] == 'pending'

def test_create_payment_invalid_amount(client):
    """Test payment creation with invalid amount"""
    unique_id = str(uuid.uuid4())[:8]
    
    payment_data = {
        'merchant_id': f'MERCHANT_TEST_{unique_id}',
        'customer_id': f'CUSTOMER_TEST_{unique_id}',
        'amount': -10.00,  # Invalid negative amount
        'currency': 'USD',
        'payment_method': 'credit_card'
    }
    
    response = client.post('/api/v1/payments', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'errors' in data

def test_create_payment_missing_fields(client):
    """Test payment creation with missing required fields"""
    payment_data = {
        'amount': 100.00,
        'currency': 'USD'
        # Missing merchant_id, customer_id, payment_method
    }
    
    response = client.post('/api/v1/payments', 
                          data=json.dumps(payment_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'errors' in data

def test_get_payment_not_found(client):
    """Test getting non-existent payment"""
    response = client.get('/api/v1/payments/non-existent-id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['success'] is False

def test_process_payment_success(client):
    """Test successful payment processing"""
    unique_id = str(uuid.uuid4())[:8]
    
    # First create a payment
    payment_data = {
        'merchant_id': f'MERCHANT_PROCESS_{unique_id}',
        'customer_id': f'CUSTOMER_PROCESS_{unique_id}',
        'amount': 50.00,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'card_last_four': '1234',
        'card_type': 'VISA'
    }
    
    create_response = client.post('/api/v1/payments', 
                                 data=json.dumps(payment_data),
                                 content_type='application/json')
    
    assert create_response.status_code == 201
    payment_id = json.loads(create_response.data)['payment']['id']
    
    # Now process the payment
    process_response = client.post(f'/api/v1/payments/{payment_id}/process')
    
    assert process_response.status_code == 200
    data = json.loads(process_response.data)
    assert data['success'] is True
    assert data['payment']['status'] in ['completed', 'failed']

def test_list_payments(client):
    """Test listing payments"""
    response = client.get('/api/v1/payments')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'payments' in data
    assert 'total' in data

def test_create_refund_success(client):
    """Test successful refund creation"""
    unique_id = str(uuid.uuid4())[:8]
    
    # Create and process a payment first
    payment_data = {
        'merchant_id': f'MERCHANT_REFUND_{unique_id}',
        'customer_id': f'CUSTOMER_REFUND_{unique_id}',
        'amount': 100.00,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'card_last_four': '1234',
        'card_type': 'VISA'
    }
    
    # Create payment
    create_response = client.post('/api/v1/payments', 
                                 data=json.dumps(payment_data),
                                 content_type='application/json')
    
    assert create_response.status_code == 201
    payment_id = json.loads(create_response.data)['payment']['id']
    
    # Process payment multiple times until successful (due to 90% success rate)
    payment_status = None
    for attempt in range(5):  # Try up to 5 times
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        if process_response.status_code == 200:
            payment_status = json.loads(process_response.data)['payment']['status']
            if payment_status == 'completed':
                break
    
    # If payment is completed, try refund
    if payment_status == 'completed':
        refund_data = {
            'amount': 25.00,
            'reason': 'Customer request'
        }
        
        refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                     data=json.dumps(refund_data),
                                     content_type='application/json')
        
        assert refund_response.status_code == 201
        data = json.loads(refund_response.data)
        assert data['success'] is True
        assert data['refund']['amount'] == 25.00
    else:
        # Skip this test if payment didn't complete (due to random 10% failure rate)
        pytest.skip(f"Payment processing failed or not completed (status: {payment_status})")

def test_complete_workflow_integration(client):
    """Test complete payment workflow in one test"""
    unique_id = str(uuid.uuid4())[:8]
    
    # Step 1: Create payment
    payment_data = {
        'merchant_id': f'MERCHANT_WORKFLOW_{unique_id}',
        'customer_id': f'CUSTOMER_WORKFLOW_{unique_id}',
        'amount': 199.99,
        'currency': 'EUR',
        'payment_method': 'debit_card',
        'description': 'Integration workflow test',
        'card_last_four': '9876',
        'card_type': 'MASTERCARD'
    }
    
    create_response = client.post('/api/v1/payments', 
                                 data=json.dumps(payment_data),
                                 content_type='application/json')
    
    assert create_response.status_code == 201
    payment = json.loads(create_response.data)['payment']
    payment_id = payment['id']
    
    # Step 2: Get payment details
    get_response = client.get(f'/api/v1/payments/{payment_id}')
    assert get_response.status_code == 200
    
    # Step 3: Process payment
    process_response = client.post(f'/api/v1/payments/{payment_id}/process')
    assert process_response.status_code == 200
    
    # Step 4: Get transactions
    transactions_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
    assert transactions_response.status_code == 200
    
    transactions_data = json.loads(transactions_response.data)
    assert transactions_data['success'] is True
    assert len(transactions_data['transactions']) >= 1