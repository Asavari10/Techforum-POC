"""End-to-End Tests for specific business scenarios"""
import pytest
import json
import uuid

class TestEcommerceScenarios:
    """Test e-commerce business scenarios"""
    
    def test_subscription_payment_scenario(self, client):
        """Test monthly subscription payment scenario"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Monthly subscription payment
        subscription_payment = {
            'merchant_id': 'SUBSCRIPTION_SERVICE',
            'customer_id': f'SUB_CUSTOMER_{unique_id}',
            'amount': 29.99,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Monthly Premium Subscription',
            'card_last_four': '4242',
            'card_type': 'VISA'
        }
        
        # Process subscription payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(subscription_payment),
                                     content_type='application/json')
        
        assert create_response.status_code == 201
        payment_id = create_response.get_json()['payment']['id']
        
        # Process payment
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        assert process_response.status_code == 200
        
        payment_data = process_response.get_json()['payment']
        
        if payment_data['status'] == 'completed':
            # Customer cancels subscription mid-month - pro-rated refund
            prorated_refund = {
                'amount': 15.00,  # Half month refund
                'reason': 'Mid-month subscription cancellation - prorated refund'
            }
            
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(prorated_refund),
                                         content_type='application/json')
            
            assert refund_response.status_code == 201
            
    def test_marketplace_payment_scenario(self, client):
        """Test marketplace payment with multiple vendors"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Marketplace order with multiple items from different vendors
        marketplace_payments = [
            {
                'merchant_id': 'VENDOR_ELECTRONICS',
                'customer_id': f'MARKETPLACE_BUYER_{unique_id}',
                'amount': 299.99,
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': 'Wireless Headphones',
                'card_last_four': '5555',
                'card_type': 'MASTERCARD'
            },
            {
                'merchant_id': 'VENDOR_BOOKS',
                'customer_id': f'MARKETPLACE_BUYER_{unique_id}',
                'amount': 24.99,
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': 'Programming Book',
                'card_last_four': '5555',
                'card_type': 'MASTERCARD'
            }
        ]
        
        payment_ids = []
        
        # Process each vendor payment
        for payment_data in marketplace_payments:
            create_response = client.post('/api/v1/payments',
                                         data=json.dumps(payment_data),
                                         content_type='application/json')
            
            assert create_response.status_code == 201
            payment_id = create_response.get_json()['payment']['id']
            payment_ids.append(payment_id)
            
            # Process payment
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            assert process_response.status_code == 200
        
        # Customer returns one item (electronics)
        electronics_payment_id = payment_ids[0]
        
        # Check if electronics payment was successful before refunding
        get_response = client.get(f'/api/v1/payments/{electronics_payment_id}')
        payment_status = get_response.get_json()['payment']['status']
        
        if payment_status == 'completed':
            return_refund = {
                'amount': 299.99,  # Full refund for returned item
                'reason': 'Item return - defective product'
            }
            
            refund_response = client.post(f'/api/v1/payments/{electronics_payment_id}/refund',
                                         data=json.dumps(return_refund),
                                         content_type='application/json')
            
            assert refund_response.status_code == 201
            
            # Verify payment status changed to refunded
            updated_response = client.get(f'/api/v1/payments/{electronics_payment_id}')
            updated_payment = updated_response.get_json()['payment']
            assert updated_payment['status'] == 'refunded'


class TestBusinessErrorScenarios:
    """Test business-specific error scenarios"""
    
    def test_insufficient_refund_balance(self, client):
        """Test refund request exceeding available balance"""
        unique_id = str(uuid.uuid4())[:8]
        
        payment_request = {
            'merchant_id': f'BALANCE_TEST_{unique_id}',
            'customer_id': f'BALANCE_CUSTOMER_{unique_id}',
            'amount': 100.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        # Create and process payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_request),
                                     content_type='application/json')
        payment_id = create_response.get_json()['payment']['id']
        
        # Process until successful
        for _ in range(5):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment = process_response.get_json()['payment']
                if payment['status'] == 'completed':
                    break
        
        if payment['status'] != 'completed':
            pytest.skip("Payment not completed")
        
        # Create first refund
        first_refund = {
            'amount': 60.00,
            'reason': 'Partial refund'
        }
        
        refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                     data=json.dumps(first_refund),
                                     content_type='application/json')
        
        assert refund_response.status_code == 201
        
        # Try to refund more than remaining balance
        excessive_refund = {
            'amount': 50.00,  # Only $40 remaining, requesting $50
            'reason': 'Excessive refund attempt'
        }
        
        excessive_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                        data=json.dumps(excessive_refund),
                                        content_type='application/json')
        
        assert excessive_response.status_code == 400
        error_data = excessive_response.get_json()
        assert 'exceeds available amount' in error_data['errors'][0]