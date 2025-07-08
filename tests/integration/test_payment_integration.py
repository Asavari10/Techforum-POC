"""Integration tests for payment workflows"""
import pytest
import json
import time

def test_complete_payment_workflow(client):
    """Test complete payment workflow from creation to refund"""
    # Step 1: Create payment
    payment_data = {
        'merchant_id': 'MERCHANT_INTEGRATION',
        'customer_id': 'CUSTOMER_INTEGRATION',
        'amount': 199.99,
        'currency': 'USD',
        'payment_method': 'credit_card',
        'description': 'Integration test payment',
        'card_last_four': '4321',
        'card_type': 'MASTERCARD'
    }
    
    create_response = client.post('/api/v1/payments', 
                                 data=json.dumps(payment_data),
                                 content_type='application/json')
    
    assert create_response.status_code == 201
    payment = json.loads(create_response.data)['payment']
    payment_id = payment['id']
    
    # Verify payment is pending
    assert payment['status'] == 'pending'
    assert payment['amount'] == 199.99
    
    # Step 2: Process payment
    process_response = client.post(f'/api/v1/payments/{payment_id}/process')
    assert process_response.status_code == 200
    
    processed_payment = json.loads(process_response.data)['payment']
    assert processed_payment['status'] in ['completed', 'failed']
    
    # Step 3: Get payment transactions
    transactions_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
    assert transactions_response.status_code == 200
    
    transactions_data = json.loads(transactions_response.data)
    assert transactions_data['success'] is True
    assert len(transactions_data['transactions']) >= 1
    
    # Step 4: Create refund if payment was successful
    if processed_payment['status'] == 'completed':
        refund_data = {
            'amount': 50.00,
            'reason': 'Integration test refund'
        }
        
        refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                     data=json.dumps(refund_data),
                                     content_type='application/json')
        
        assert refund_response.status_code == 201
        refund = json.loads(refund_response.data)['refund']
        assert refund['amount'] == 50.00

def test_multiple_currency_payments(client):
    """Test payments with different currencies"""
    currencies = ['USD', 'EUR', 'GBP', 'JPY']
    
    for currency in currencies:
        payment_data = {
            'merchant_id': 'MERCHANT_MULTICURRENCY',
            'customer_id': f'CUSTOMER_{currency}',
            'amount': 100.00 if currency != 'JPY' else 10000,  # JPY doesn't use decimals
            'currency': currency,
            'payment_method': 'credit_card',
            'description': f'Test payment in {currency}',
            'card_last_four': '9999',
            'card_type': 'VISA'
        }
        
        response = client.post('/api/v1/payments', 
                              data=json.dumps(payment_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        payment = json.loads(response.data)['payment']
        assert payment['currency'] == currency