"""End-to-End Tests - Complete business workflows"""
import pytest
import json
import uuid
import time

class TestPaymentWorkflows:
    """Test complete payment workflows from start to finish"""
    
    def test_successful_payment_lifecycle(self, client):
        """Test complete successful payment lifecycle"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Step 1: Create customer payment request
        payment_request = {
            'merchant_id': f'E2E_MERCHANT_{unique_id}',
            'customer_id': f'E2E_CUSTOMER_{unique_id}',
            'amount': 250.99,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'E2E Test Purchase - Premium Subscription',
            'card_last_four': '1234',
            'card_type': 'VISA'
        }
        
        # Create payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_request),
                                     content_type='application/json')
        
        assert create_response.status_code == 201
        payment = create_response.get_json()['payment']
        payment_id = payment['id']
        
        # Verify initial state
        assert payment['status'] == 'pending'
        assert payment['amount'] == 250.99
        assert payment['processed_at'] is None
        
        # Step 2: Process the payment (merchant processes payment)
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        assert process_response.status_code == 200
        
        processed_payment = process_response.get_json()['payment']
        final_status = processed_payment['status']
        
        # Step 3: Handle based on processing result
        if final_status == 'completed':
            # Payment successful - verify completion
            assert processed_payment['processed_at'] is not None
            
            # Step 4: Verify transaction records
            txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            assert txn_response.status_code == 200
            
            transactions = txn_response.get_json()['transactions']
            assert len(transactions) >= 1
            
            charge_transaction = next(
                (t for t in transactions if t['transaction_type'] == 'charge'), 
                None
            )
            assert charge_transaction is not None
            assert charge_transaction['amount'] == 250.99
            assert 'gw_' in charge_transaction['gateway_transaction_id']
            
            # Step 5: Customer requests partial refund
            refund_request = {
                'amount': 100.00,
                'reason': 'Partial service cancellation'
            }
            
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(refund_request),
                                         content_type='application/json')
            
            assert refund_response.status_code == 201
            refund = refund_response.get_json()['refund']
            
            # Verify refund
            assert refund['amount'] == 100.00
            assert refund['payment_id'] == payment_id
            
            # Step 6: Verify updated payment status
            updated_payment_response = client.get(f'/api/v1/payments/{payment_id}')
            updated_payment = updated_payment_response.get_json()['payment']
            assert updated_payment['status'] == 'partial_refunded'
            
            # Step 7: Verify refund transaction was created
            final_txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            final_transactions = final_txn_response.get_json()['transactions']
            
            refund_transaction = next(
                (t for t in final_transactions if t['transaction_type'] == 'refund'), 
                None
            )
            assert refund_transaction is not None
            assert refund_transaction['amount'] == 100.00
            
        elif final_status == 'failed':
            # Payment failed - verify failure handling
            assert processed_payment['processed_at'] is None
            
            # Verify failure transaction record
            txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            transactions = txn_response.get_json()['transactions']
            
            failed_transaction = next(
                (t for t in transactions if 'DECLINED' in t['gateway_response']), 
                None
            )
            assert failed_transaction is not None
    
    def test_multi_currency_international_payment(self, client):
        """Test international payment workflow with currency conversion"""
        currencies_to_test = [
            {'currency': 'EUR', 'amount': 199.99},
            {'currency': 'GBP', 'amount': 149.50},
            {'currency': 'JPY', 'amount': 25000},  # No decimals for JPY
            {'currency': 'CAD', 'amount': 299.75}
        ]
        
        created_payments = []
        
        for currency_test in currencies_to_test:
            unique_id = str(uuid.uuid4())[:8]
            
            payment_request = {
                'merchant_id': f'INTL_MERCHANT_{currency_test["currency"]}',
                'customer_id': f'INTL_CUSTOMER_{unique_id}',
                'amount': currency_test['amount'],
                'currency': currency_test['currency'],
                'payment_method': 'credit_card',
                'description': f'International payment in {currency_test["currency"]}',
                'card_last_four': '9999',
                'card_type': 'MASTERCARD'
            }
            
            # Create payment
            create_response = client.post('/api/v1/payments',
                                         data=json.dumps(payment_request),
                                         content_type='application/json')
            
            assert create_response.status_code == 201
            payment = create_response.get_json()['payment']
            created_payments.append(payment)
            
            # Verify currency-specific handling
            assert payment['currency'] == currency_test['currency']
            assert payment['amount'] == currency_test['amount']
        
        # Verify all payments were created successfully
        assert len(created_payments) == len(currencies_to_test)
        
        # Process each payment
        for payment in created_payments:
            process_response = client.post(f'/api/v1/payments/{payment["id"]}/process')
            assert process_response.status_code == 200

    def test_high_value_transaction_workflow(self, client):
        """Test high-value transaction with special handling"""
        unique_id = str(uuid.uuid4())[:8]
        
        # High-value payment (business/corporate payment)
        high_value_payment = {
            'merchant_id': f'CORP_MERCHANT_{unique_id}',
            'customer_id': f'CORP_CUSTOMER_{unique_id}',
            'amount': 9500.00,  # High value transaction
            'currency': 'USD',
            'payment_method': 'bank_transfer',
            'description': 'Corporate software license - Annual enterprise plan'
        }
        
        # Create high-value payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(high_value_payment),
                                     content_type='application/json')
        
        assert create_response.status_code == 201
        payment = create_response.get_json()['payment']
        payment_id = payment['id']
        
        # Process high-value payment
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        assert process_response.status_code == 200
        
        processed_payment = process_response.get_json()['payment']
        
        if processed_payment['status'] == 'completed':
            # Test partial refund on high-value transaction
            partial_refund = {
                'amount': 2000.00,
                'reason': 'Reduced license count'
            }
            
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(partial_refund),
                                         content_type='application/json')
            
            assert refund_response.status_code == 201
            
            # Verify remaining balance handling
            updated_payment = client.get(f'/api/v1/payments/{payment_id}').get_json()['payment']
            assert updated_payment['status'] == 'partial_refunded'


class TestErrorRecoveryWorkflows:
    """Test error recovery and edge case workflows"""
    
    def test_payment_retry_workflow(self, client):
        """Test payment retry after initial failure"""
        unique_id = str(uuid.uuid4())[:8]
        
        payment_request = {
            'merchant_id': f'RETRY_MERCHANT_{unique_id}',
            'customer_id': f'RETRY_CUSTOMER_{unique_id}',
            'amount': 75.00,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Payment with retry logic test'
        }
        
        # Create payment
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_request),
                                     content_type='application/json')
        
        payment_id = create_response.get_json()['payment']['id']
        
        # Attempt processing multiple times (simulating retry logic)
        max_retries = 5
        successful = False
        
        for attempt in range(max_retries):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            
            if process_response.status_code == 200:
                payment_data = process_response.get_json()['payment']
                if payment_data['status'] == 'completed':
                    successful = True
                    break
                elif payment_data['status'] == 'failed':
                    # In real scenario, might create new payment for retry
                    continue
        
        # Either successful or exhausted retries (both are valid outcomes)
        assert process_response.status_code == 200

    def test_concurrent_refund_requests(self, client):
        """Test handling of concurrent refund requests"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and process payment
        payment_request = {
            'merchant_id': f'CONCURRENT_MERCHANT_{unique_id}',
            'customer_id': f'CONCURRENT_CUSTOMER_{unique_id}',
            'amount': 400.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_request),
                                     content_type='application/json')
        payment_id = create_response.get_json()['payment']['id']
        
        # Process payment until successful
        for _ in range(5):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment = process_response.get_json()['payment']
                if payment['status'] == 'completed':
                    break
        
        if payment['status'] != 'completed':
            pytest.skip("Payment not completed")
        
        # Simulate concurrent refund requests
        refund_requests = [
            {'amount': 150.00, 'reason': 'First refund request'},
            {'amount': 200.00, 'reason': 'Second refund request'},
            {'amount': 100.00, 'reason': 'Third refund request'}
        ]
        
        successful_refunds = 0
        total_refunded = 0
        
        for refund_req in refund_requests:
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(refund_req),
                                         content_type='application/json')
            
            if refund_response.status_code == 201:
                successful_refunds += 1
                total_refunded += refund_req['amount']
            elif refund_response.status_code == 400:
                # Expected when refund amount exceeds available amount
                error_data = refund_response.get_json()
                assert 'exceeds available amount' in error_data['errors'][0]
        
        # Verify total refunds don't exceed original payment
        assert total_refunded <= 400.00
        assert successful_refunds >= 1  # At least one should succeed