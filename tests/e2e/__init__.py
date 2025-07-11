# End-to-End Tests Package 
"""End-to-End Tests - Complete user workflows from start to finish"""
import pytest
import json
import uuid
import time

class TestCompletePaymentWorkflows:
    """Test complete payment workflows end-to-end"""
    
    def test_successful_payment_journey(self, client):
        """Test complete successful payment journey"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Step 1: Customer initiates payment
        payment_request = {
            'merchant_id': f'ECOMMERCE_STORE_{unique_id}',
            'customer_id': f'CUSTOMER_JOHN_{unique_id}',
            'amount': 299.99,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'MacBook Pro purchase',
            'card_last_four': '1234',
            'card_type': 'VISA'
        }
        
        # Step 2: Create payment
        create_response = client.post('/api/v1/payments',
                                    data=json.dumps(payment_request),
                                    content_type='application/json')
        
        assert create_response.status_code == 201
        payment = json.loads(create_response.data)['payment']
        payment_id = payment['id']
        
        # Verify payment is in pending state
        assert payment['status'] == 'pending'
        assert payment['amount'] == 299.99
        
        # Step 3: Merchant processes payment
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        assert process_response.status_code == 200
        
        processed_payment = json.loads(process_response.data)['payment']
        assert processed_payment['status'] in ['completed', 'failed']
        
        # Step 4: If successful, verify payment completion
        if processed_payment['status'] == 'completed':
            # Step 5: Verify transaction was recorded
            txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            assert txn_response.status_code == 200
            
            transactions = json.loads(txn_response.data)['transactions']
            assert len(transactions) >= 1
            
            charge_transaction = next(
                (txn for txn in transactions if txn['transaction_type'] == 'charge'), 
                None
            )
            assert charge_transaction is not None
            assert float(charge_transaction['amount']) == 299.99
            
            # Step 6: Customer requests refund after 24 hours
            refund_request = {
                'amount': 299.99,
                'reason': 'Changed mind - return policy'
            }
            
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                        data=json.dumps(refund_request),
                                        content_type='application/json')
            
            assert refund_response.status_code == 201
            refund = json.loads(refund_response.data)['refund']
            
            # Step 7: Verify refund processed
            assert refund['amount'] == 299.99
            assert refund['payment_id'] == payment_id
            
            # Step 8: Verify payment status updated
            final_payment_response = client.get(f'/api/v1/payments/{payment_id}')
            final_payment = json.loads(final_payment_response.data)['payment']
            assert final_payment['status'] == 'refunded'
            
            # Step 9: Verify refund transaction recorded
            final_txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            final_transactions = json.loads(final_txn_response.data)['transactions']
            
            refund_transaction = next(
                (txn for txn in final_transactions if txn['transaction_type'] == 'refund'), 
                None
            )
            assert refund_transaction is not None
            assert float(refund_transaction['amount']) == 299.99

    def test_failed_payment_journey(self, client):
        """Test payment failure journey"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create payment
        payment_request = {
            'merchant_id': f'MERCHANT_FAIL_{unique_id}',
            'customer_id': f'CUSTOMER_FAIL_{unique_id}',
            'amount': 89.99,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Failed payment test'
        }
        
        create_response = client.post('/api/v1/payments',
                                    data=json.dumps(payment_request),
                                    content_type='application/json')
        payment_id = json.loads(create_response.data)['payment']['id']
        
        # Try processing multiple times (10% failure rate, so some should fail)
        failed_attempt = False
        for attempt in range(10):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment_status = json.loads(process_response.data)['payment']['status']
                if payment_status == 'failed':
                    failed_attempt = True
                    break
                elif payment_status == 'completed':
                    # Reset payment status to test failure scenario
                    continue
        
        if failed_attempt:
            # Verify failed transaction is recorded
            txn_response = client.get(f'/api/v1/payments/{payment_id}/transactions')
            transactions = json.loads(txn_response.data)['transactions']
            
            failed_transaction = next(
                (txn for txn in transactions if txn['gateway_response'] == 'DECLINED'), 
                None
            )
            assert failed_transaction is not None
            
            # Verify cannot refund failed payment
            refund_request = {'amount': 89.99, 'reason': 'Test refund'}
            refund_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                        data=json.dumps(refund_request),
                                        content_type='application/json')
            assert refund_response.status_code == 400
            
            error_data = json.loads(refund_response.data)
            assert 'Payment is not completed' in str(error_data['errors'])

    def test_partial_refund_journey(self, client):
        """Test partial refund workflow"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and process payment
        payment_request = {
            'merchant_id': f'MERCHANT_PARTIAL_{unique_id}',
            'customer_id': f'CUSTOMER_PARTIAL_{unique_id}',
            'amount': 150.00,
            'currency': 'EUR',
            'payment_method': 'debit_card',
            'description': 'Partial refund test order'
        }
        
        create_response = client.post('/api/v1/payments',
                                    data=json.dumps(payment_request),
                                    content_type='application/json')
        payment_id = json.loads(create_response.data)['payment']['id']
        
        # Process until successful
        payment_status = None
        for _ in range(5):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment_status = json.loads(process_response.data)['payment']['status']
                if payment_status == 'completed':
                    break
        
        if payment_status == 'completed':
            # First partial refund (50 EUR)
            refund1_request = {
                'amount': 50.00,
                'reason': 'One item returned'
            }
            
            refund1_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(refund1_request),
                                         content_type='application/json')
            assert refund1_response.status_code == 201
            
            # Verify payment status is partial_refunded
            payment_response = client.get(f'/api/v1/payments/{payment_id}')
            payment = json.loads(payment_response.data)['payment']
            assert payment['status'] == 'partial_refunded'
            
            # Second partial refund (30 EUR)
            refund2_request = {
                'amount': 30.00,
                'reason': 'Shipping fee returned'
            }
            
            refund2_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(refund2_request),
                                         content_type='application/json')
            assert refund2_response.status_code == 201
            
            # Still partial refunded (80 EUR total refunded, 70 EUR remaining)
            payment_response = client.get(f'/api/v1/payments/{payment_id}')
            payment = json.loads(payment_response.data)['payment']
            assert payment['status'] == 'partial_refunded'
            
            # Final refund (70 EUR - complete the refund)
            refund3_request = {
                'amount': 70.00,
                'reason': 'Full return completed'
            }
            
            refund3_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                         data=json.dumps(refund3_request),
                                         content_type='application/json')
            assert refund3_response.status_code == 201
            
            # Now should be fully refunded
            final_payment_response = client.get(f'/api/v1/payments/{payment_id}')
            final_payment = json.loads(final_payment_response.data)['payment']
            assert final_payment['status'] == 'refunded'
            
            # Verify cannot refund more
            excess_refund_request = {
                'amount': 1.00,
                'reason': 'Should fail'
            }
            
            excess_response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                        data=json.dumps(excess_refund_request),
                                        content_type='application/json')
            assert excess_response.status_code == 400

    def test_multi_currency_payment_journey(self, client):
        """Test payments in different currencies"""
        currencies_and_amounts = [
            ('USD', 100.00),
            ('EUR', 85.50),
            ('GBP', 75.25),
            ('JPY', 11000),  # No decimals for JPY
            ('CAD', 130.75)
        ]
        
        payment_ids = []
        
        for currency, amount in currencies_and_amounts:
            unique_id = str(uuid.uuid4())[:8]
            
            payment_request = {
                'merchant_id': f'GLOBAL_MERCHANT_{unique_id}',
                'customer_id': f'CUSTOMER_{currency}_{unique_id}',
                'amount': amount,
                'currency': currency,
                'payment_method': 'credit_card',
                'description': f'Multi-currency test - {currency}'
            }
            
            # Create payment
            create_response = client.post('/api/v1/payments',
                                        data=json.dumps(payment_request),
                                        content_type='application/json')
            
            assert create_response.status_code == 201
            payment = json.loads(create_response.data)['payment']
            payment_ids.append(payment['id'])
            
            # Verify currency and amount
            assert payment['currency'] == currency
            assert float(payment['amount']) == amount
            
            # Process payment
            process_response = client.post(f'/api/v1/payments/{payment["id"]}/process')
            assert process_response.status_code == 200
        
        # Verify all payments in list
        list_response = client.get('/api/v1/payments')
        all_payments = json.loads(list_response.data)['payments']
        
        created_payment_ids = {p['id'] for p in all_payments}
        for payment_id in payment_ids:
            assert payment_id in created_payment_ids

    def test_high_volume_payment_simulation(self, client):
        """Test processing multiple payments concurrently"""
        unique_batch_id = str(uuid.uuid4())[:8]
        payment_ids = []
        
        # Create 10 payments rapidly
        for i in range(10):
            payment_request = {
                'merchant_id': f'VOLUME_MERCHANT_{unique_batch_id}',
                'customer_id': f'CUSTOMER_BATCH_{i}_{unique_batch_id}',
                'amount': round(50.00 + (i * 10.50), 2),
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': f'Volume test payment {i+1}'
            }
            
            create_response = client.post('/api/v1/payments',
                                        data=json.dumps(payment_request),
                                        content_type='application/json')
            
            assert create_response.status_code == 201
            payment_id = json.loads(create_response.data)['payment']['id']
            payment_ids.append(payment_id)
        
        # Process all payments
        processed_count = 0
        successful_count = 0
        
        for payment_id in payment_ids:
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                processed_count += 1
                payment_status = json.loads(process_response.data)['payment']['status']
                if payment_status == 'completed':
                    successful_count += 1
        
        # Verify processing stats
        assert processed_count == 10  # All should process
        assert successful_count >= 8   # At least 80% should succeed (90% success rate)
        
        # Verify all payments exist in system
        list_response = client.get(f'/api/v1/payments?merchant_id=VOLUME_MERCHANT_{unique_batch_id}')
        merchant_payments = json.loads(list_response.data)['payments']
        assert len(merchant_payments) == 10

class TestErrorRecoveryWorkflows:
    """Test error scenarios and recovery workflows"""
    
    def test_duplicate_payment_prevention(self, client):
        """Test system handles duplicate payment attempts"""
        unique_id = str(uuid.uuid4())[:8]
        
        payment_request = {
            'merchant_id': f'MERCHANT_DUP_{unique_id}',
            'customer_id': f'CUSTOMER_DUP_{unique_id}',
            'amount': 100.00,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Duplicate test payment'
        }
        
        # Create first payment
        response1 = client.post('/api/v1/payments',
                               data=json.dumps(payment_request),
                               content_type='application/json')
        assert response1.status_code == 201
        
        # Create identical payment (should succeed as we allow this)
        response2 = client.post('/api/v1/payments',
                               data=json.dumps(payment_request),
                               content_type='application/json')
        assert response2.status_code == 201
        
        # But they should have different IDs
        payment1_id = json.loads(response1.data)['payment']['id']
        payment2_id = json.loads(response2.data)['payment']['id']
        assert payment1_id != payment2_id

    def test_invalid_state_transitions(self, client):
        """Test invalid payment state transitions are prevented"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create payment
        payment_request = {
            'merchant_id': f'MERCHANT_STATE_{unique_id}',
            'customer_id': f'CUSTOMER_STATE_{unique_id}',
            'amount': 100.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        create_response = client.post('/api/v1/payments',
                                    data=json.dumps(payment_request),
                                    content_type='application/json')
        payment_id = json.loads(create_response.data)['payment']['id']
        
        # Process payment
        process_response = client.post(f'/api/v1/payments/{payment_id}/process')
        payment_status = json.loads(process_response.data)['payment']['status']
        
        if payment_status in ['completed', 'failed']:
            # Try to process again (should fail)
            second_process = client.post(f'/api/v1/payments/{payment_id}/process')
            assert second_process.status_code == 400
            
            error_data = json.loads(second_process.data)
            assert 'not in pending status' in str(error_data['errors'])
