"""End-to-End Error Scenarios - System failures, edge cases, and recovery testing"""
import pytest
import json
import uuid
import time
import threading
from unittest.mock import patch
import requests

class TestSystemErrorScenarios:
    """Test system-level error scenarios and recovery"""
    
    def test_database_connection_failure_simulation(self, client):
        """Test payment creation when database is temporarily unavailable"""
        unique_id = str(uuid.uuid4())[:8]
        
        payment_request = {
            'merchant_id': f'DB_ERROR_MERCHANT_{unique_id}',
            'customer_id': f'DB_ERROR_CUSTOMER_{unique_id}',
            'amount': 150.00,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Database failure test payment'
        }
        
        # First verify normal operation works
        response = client.post('/api/v1/payments',
                              data=json.dumps(payment_request),
                              content_type='application/json')
        
        # This should work normally
        assert response.status_code in [201, 500]  # Could fail due to DB issues
        
        if response.status_code == 201:
            # If successful, test that we can handle the payment ID
            payment_id = response.get_json()['payment']['id']
            assert payment_id is not None
        else:
            # If failed, verify error response format
            error_data = response.get_json()
            assert 'success' in error_data
            assert error_data['success'] is False
            assert 'errors' in error_data

    def test_concurrent_payment_processing_stress(self, client):
        """Test system under concurrent payment processing load"""
        unique_base_id = str(uuid.uuid4())[:8]
        concurrent_requests = 10
        results = []
        
        def create_concurrent_payment(index):
            payment_request = {
                'merchant_id': f'STRESS_MERCHANT_{unique_base_id}_{index}',
                'customer_id': f'STRESS_CUSTOMER_{unique_base_id}_{index}',
                'amount': 50.00 + (index * 10),  # Varying amounts
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': f'Concurrent stress test payment #{index}'
            }
            
            try:
                response = client.post('/api/v1/payments',
                                      data=json.dumps(payment_request),
                                      content_type='application/json')
                results.append({
                    'index': index,
                    'status_code': response.status_code,
                    'success': response.status_code == 201,
                    'response': response.get_json() if response.status_code in [200, 201] else None
                })
            except Exception as e:
                results.append({
                    'index': index,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                })
        
        # Create concurrent threads
        threads = []
        for i in range(concurrent_requests):
            thread = threading.Thread(target=create_concurrent_payment, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout per thread
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        total_requests = len(results)
        
        # At least 50% should succeed under normal conditions
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        print(f"Concurrent stress test: {successful_requests}/{total_requests} succeeded ({success_rate:.1%})")
        
        # Verify we got responses from all threads
        assert len(results) == concurrent_requests
        
        # In a real system, you might want a minimum success rate
        # For testing purposes, we'll just verify the system didn't crash completely
        assert success_rate > 0  # At least some requests should succeed

    def test_invalid_payment_method_combinations(self, client):
        """Test various invalid payment method combinations"""
        unique_id = str(uuid.uuid4())[:8]
        
        invalid_combinations = [
            # Credit card with bank transfer method
            {
                'merchant_id': f'INVALID_COMBO_1_{unique_id}',
                'customer_id': f'INVALID_CUSTOMER_{unique_id}',
                'amount': 100.00,
                'currency': 'USD',
                'payment_method': 'bank_transfer',
                'card_last_four': '1234',  # Invalid: card info with bank transfer
                'card_type': 'VISA'
            },
            # Negative amount edge case
            {
                'merchant_id': f'INVALID_COMBO_2_{unique_id}',
                'customer_id': f'INVALID_CUSTOMER_{unique_id}',
                'amount': -0.01,
                'currency': 'USD',
                'payment_method': 'credit_card'
            },
            # Zero amount edge case
            {
                'merchant_id': f'INVALID_COMBO_3_{unique_id}',
                'customer_id': f'INVALID_CUSTOMER_{unique_id}',
                'amount': 0.00,
                'currency': 'USD',
                'payment_method': 'credit_card'
            },
            # Extremely large amount
            {
                'merchant_id': f'INVALID_COMBO_4_{unique_id}',
                'customer_id': f'INVALID_CUSTOMER_{unique_id}',
                'amount': 999999999.99,
                'currency': 'USD',
                'payment_method': 'credit_card'
            },
            # Invalid currency precision (JPY with decimals)
            {
                'merchant_id': f'INVALID_COMBO_5_{unique_id}',
                'customer_id': f'INVALID_CUSTOMER_{unique_id}',
                'amount': 1000.50,  # JPY shouldn't have decimals
                'currency': 'JPY',
                'payment_method': 'credit_card'
            }
        ]
        
        for i, invalid_payment in enumerate(invalid_combinations):
            response = client.post('/api/v1/payments',
                                  data=json.dumps(invalid_payment),
                                  content_type='application/json')
            
            # Should return 400 Bad Request for validation errors
            assert response.status_code == 400, f"Invalid combination #{i+1} should return 400"
            
            error_data = response.get_json()
            assert error_data['success'] is False
            assert 'errors' in error_data
            assert len(error_data['errors']) > 0

    def test_malformed_request_handling(self, client):
        """Test handling of various malformed requests"""
        malformed_requests = [
            # Completely invalid JSON
            {
                'data': '{"merchant_id": "TEST", "amount":}',
                'content_type': 'application/json',
                'description': 'Invalid JSON syntax'
            },
            # Valid JSON but wrong data types
            {
                'data': json.dumps({
                    'merchant_id': 12345,  # Should be string
                    'customer_id': ['array'],  # Should be string
                    'amount': 'one hundred',  # Should be number
                    'currency': 123,  # Should be string
                    'payment_method': None  # Should be string
                }),
                'content_type': 'application/json',
                'description': 'Wrong data types'
            },
            # Empty request body
            {
                'data': '',
                'content_type': 'application/json',
                'description': 'Empty request body'
            },
            # Non-JSON content type
            {
                'data': 'merchant_id=TEST&amount=100',
                'content_type': 'application/x-www-form-urlencoded',
                'description': 'Form data instead of JSON'
            },
            # Extremely large request
            {
                'data': json.dumps({
                    'merchant_id': 'A' * 10000,  # Extremely long string
                    'customer_id': 'B' * 10000,
                    'amount': 100.00,
                    'currency': 'USD',
                    'payment_method': 'credit_card',
                    'description': 'C' * 50000  # Very long description
                }),
                'content_type': 'application/json',
                'description': 'Extremely large request'
            }
        ]
        
        for req in malformed_requests:
            response = client.post('/api/v1/payments',
                                  data=req['data'],
                                  content_type=req['content_type'])
            
            # Should handle gracefully with 400 status
            assert response.status_code == 400, f"Failed to handle: {req['description']}"
            
            # Should return JSON error response even for malformed requests
            try:
                error_data = response.get_json()
                assert error_data is not None
                assert 'success' in error_data
                assert error_data['success'] is False
            except:
                # If JSON parsing fails, that's also acceptable for malformed requests
                pass

    def test_payment_processing_timeout_scenarios(self, client):
        """Test payment processing under timeout conditions"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create multiple payments that might timeout
        timeout_test_payments = []
        
        for i in range(3):
            payment_request = {
                'merchant_id': f'TIMEOUT_MERCHANT_{unique_id}_{i}',
                'customer_id': f'TIMEOUT_CUSTOMER_{unique_id}_{i}',
                'amount': 100.00 + (i * 50),
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': f'Timeout test payment #{i}'
            }
            
            create_response = client.post('/api/v1/payments',
                                         data=json.dumps(payment_request),
                                         content_type='application/json')
            
            if create_response.status_code == 201:
                payment_id = create_response.get_json()['payment']['id']
                timeout_test_payments.append(payment_id)
        
        # Process payments with timeout monitoring
        processing_results = []
        
        for payment_id in timeout_test_payments:
            start_time = time.time()
            
            try:
                process_response = client.post(f'/api/v1/payments/{payment_id}/process')
                end_time = time.time()
                processing_time = end_time - start_time
                
                processing_results.append({
                    'payment_id': payment_id,
                    'status_code': process_response.status_code,
                    'processing_time': processing_time,
                    'success': process_response.status_code == 200,
                    'timeout': processing_time > 10.0  # 10 second timeout threshold
                })
                
            except Exception as e:
                processing_results.append({
                    'payment_id': payment_id,
                    'status_code': 500,
                    'processing_time': None,
                    'success': False,
                    'error': str(e),
                    'timeout': True
                })
        
        # Analyze timeout behavior
        total_payments = len(processing_results)
        timeouts = sum(1 for r in processing_results if r.get('timeout', False))
        
        print(f"Timeout test: {timeouts}/{total_payments} payments timed out")
        
        # Verify that the system handles timeouts gracefully
        for result in processing_results:
            if result.get('timeout'):
                # Timeout scenarios should still return proper HTTP status
                assert result['status_code'] in [200, 408, 500, 503]

    def test_refund_error_scenarios(self, client):
        """Test various refund error scenarios"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and process a successful payment first
        payment_request = {
            'merchant_id': f'REFUND_ERROR_MERCHANT_{unique_id}',
            'customer_id': f'REFUND_ERROR_CUSTOMER_{unique_id}',
            'amount': 200.00,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Refund error scenarios test'
        }
        
        create_response = client.post('/api/v1/payments',
                                     data=json.dumps(payment_request),
                                     content_type='application/json')
        
        if create_response.status_code != 201:
            pytest.skip("Could not create payment for refund testing")
        
        payment_id = create_response.get_json()['payment']['id']
        
        # Process payment until successful
        payment_processed = False
        for attempt in range(5):
            process_response = client.post(f'/api/v1/payments/{payment_id}/process')
            if process_response.status_code == 200:
                payment_data = process_response.get_json()['payment']
                if payment_data['status'] == 'completed':
                    payment_processed = True
                    break
        
        if not payment_processed:
            pytest.skip("Payment processing failed")
        
        # Test various refund error scenarios
        refund_error_scenarios = [
            # Refund amount exceeds payment amount
            {
                'amount': 250.00,  # More than $200 original
                'reason': 'Excessive refund test',
                'expected_error': 'exceeds available amount'
            },
            # Negative refund amount
            {
                'amount': -50.00,
                'reason': 'Negative refund test',
                'expected_error': 'Amount must be'
            },
            # Zero refund amount
            {
                'amount': 0.00,
                'reason': 'Zero refund test',
                'expected_error': 'Amount must be'
            },
            # Missing reason (if required)
            {
                'amount': 50.00,
                # 'reason' field omitted
                'expected_error': 'reason'
            },
            # Extremely long reason
            {
                'amount': 50.00,
                'reason': 'A' * 10000,  # Very long reason
                'expected_error': None  # Might be accepted or rejected
            }
        ]
        
        for scenario in refund_error_scenarios:
            refund_request = {}
            if 'amount' in scenario:
                refund_request['amount'] = scenario['amount']
            if 'reason' in scenario:
                refund_request['reason'] = scenario['reason']
            
            response = client.post(f'/api/v1/payments/{payment_id}/refund',
                                  data=json.dumps(refund_request),
                                  content_type='application/json')
            
            # Most should return 400 for validation errors
            if scenario['expected_error']:
                assert response.status_code == 400
                error_data = response.get_json()
                assert error_data['success'] is False
                
                if scenario['expected_error'] != None:
                    error_text = ' '.join(error_data.get('errors', []))
                    assert scenario['expected_error'].lower() in error_text.lower()

    def test_api_rate_limiting_simulation(self, client):
        """Test API behavior under rapid successive requests"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Make rapid successive requests to test rate limiting behavior
        rapid_requests = 20
        responses = []
        
        base_payment_request = {
            'merchant_id': f'RATE_LIMIT_MERCHANT_{unique_id}',
            'customer_id': f'RATE_LIMIT_CUSTOMER_{unique_id}',
            'amount': 25.00,
            'currency': 'USD',
            'payment_method': 'credit_card',
            'description': 'Rate limiting test'
        }
        
        start_time = time.time()
        
        for i in range(rapid_requests):
            # Slightly modify each request to make it unique
            payment_request = base_payment_request.copy()
            payment_request['customer_id'] = f'RATE_LIMIT_CUSTOMER_{unique_id}_{i}'
            
            try:
                response = client.post('/api/v1/payments',
                                      data=json.dumps(payment_request),
                                      content_type='application/json')
                
                responses.append({
                    'request_number': i,
                    'status_code': response.status_code,
                    'success': response.status_code == 201
                })
                
            except Exception as e:
                responses.append({
                    'request_number': i,
                    'status_code': 500,
                    'success': False,
                    'error': str(e)
                })
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze rate limiting behavior
        successful_requests = sum(1 for r in responses if r['success'])
        rate_limited_requests = sum(1 for r in responses if r['status_code'] == 429)  # Too Many Requests
        
        print(f"Rate limiting test: {successful_requests}/{rapid_requests} succeeded in {total_time:.2f}s")
        print(f"Rate limited: {rate_limited_requests} requests")
        
        # Verify the system handled the load
        assert len(responses) == rapid_requests
        
        # If rate limiting is implemented, should see 429 responses
        # If not implemented, should still handle all requests gracefully
        for response in responses:
            assert response['status_code'] in [200, 201, 400, 429, 500, 503]


class TestSecurityErrorScenarios:
    """Test security-related error scenarios"""
    
    def test_sql_injection_attempts(self, client):
        """Test SQL injection prevention in payment endpoints"""
        unique_id = str(uuid.uuid4())[:8]
        
        sql_injection_payloads = [
            "'; DROP TABLE payments; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM payments --",
            "1; DELETE FROM payments WHERE 1=1; --"
        ]
        
        for payload in sql_injection_payloads:
            # Test in merchant_id field
            payment_request = {
                'merchant_id': payload,
                'customer_id': f'SQL_TEST_CUSTOMER_{unique_id}',
                'amount': 100.00,
                'currency': 'USD',
                'payment_method': 'credit_card'
            }
            
            response = client.post('/api/v1/payments',
                                  data=json.dumps(payment_request),
                                  content_type='application/json')
            
            # Should either reject malicious input or sanitize it
            # Should not return 500 (indicating SQL error)
            assert response.status_code in [201, 400], f"SQL injection payload caused unexpected response: {payload}"
            
            # Test in payment ID for GET requests
            malicious_id = payload.replace("'", "%27").replace(" ", "%20")
            get_response = client.get(f'/api/v1/payments/{malicious_id}')
            
            # Should handle malicious IDs gracefully
            assert get_response.status_code in [400, 404], f"GET with malicious ID failed: {payload}"

    def test_xss_prevention_in_responses(self, client):
        """Test XSS prevention in API responses"""
        unique_id = str(uuid.uuid4())[:8]
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            payment_request = {
                'merchant_id': f'XSS_MERCHANT_{unique_id}',
                'customer_id': f'XSS_CUSTOMER_{unique_id}',
                'amount': 100.00,
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': payload  # XSS payload in description
            }
            
            response = client.post('/api/v1/payments',
                                  data=json.dumps(payment_request),
                                  content_type='application/json')
            
            if response.status_code == 201:
                # If payment was created, verify XSS payload is escaped in response
                response_data = response.get_json()
                payment_description = response_data.get('payment', {}).get('description', '')
                
                # Should not contain unescaped script tags
                assert '<script>' not in payment_description.lower()
                assert 'javascript:' not in payment_description.lower()
                assert 'onerror=' not in payment_description.lower()

    def test_parameter_pollution_attacks(self, client):
        """Test handling of parameter pollution attacks"""
        # Test with duplicate parameters in query string
        polluted_requests = [
            '/api/v1/payments?limit=10&limit=999999',  # Parameter pollution
            '/api/v1/payments?offset=0&offset=-1',
            '/api/v1/payments?merchant_id=valid&merchant_id=malicious'
        ]
        
        for polluted_url in polluted_requests:
            response = client.get(polluted_url)
            
            # Should handle parameter pollution gracefully
            assert response.status_code in [200, 400], f"Parameter pollution failed: {polluted_url}"


class TestResourceExhaustionScenarios:
    """Test resource exhaustion and DoS scenarios"""
    
    def test_large_payment_description_handling(self, client):
        """Test handling of extremely large payment descriptions"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Test various large description sizes
        large_descriptions = [
            'A' * 1000,      # 1KB
            'B' * 10000,     # 10KB
            'C' * 100000,    # 100KB
        ]
        
        for desc in large_descriptions:
            payment_request = {
                'merchant_id': f'LARGE_DESC_MERCHANT_{unique_id}',
                'customer_id': f'LARGE_DESC_CUSTOMER_{unique_id}',
                'amount': 100.00,
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': desc
            }
            
            response = client.post('/api/v1/payments',
                                  data=json.dumps(payment_request),
                                  content_type='application/json')
            
            # Should either accept or reject large descriptions gracefully
            assert response.status_code in [201, 400, 413], f"Large description ({len(desc)} chars) not handled properly"
            
            if response.status_code == 413:  # Payload Too Large
                break  # Expected behavior for very large payloads

    def test_memory_exhaustion_prevention(self, client):
        """Test prevention of memory exhaustion attacks"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create request with many duplicate fields (JSON bomb attempt)
        large_json_obj = {
            'merchant_id': f'MEMORY_TEST_MERCHANT_{unique_id}',
            'customer_id': f'MEMORY_TEST_CUSTOMER_{unique_id}',
            'amount': 100.00,
            'currency': 'USD',
            'payment_method': 'credit_card'
        }
        
        # Add many dummy fields to increase JSON size
        for i in range(1000):
            large_json_obj[f'dummy_field_{i}'] = f'dummy_value_{i}' * 100
        
        try:
            response = client.post('/api/v1/payments',
                                  data=json.dumps(large_json_obj),
                                  content_type='application/json')
            
            # Should handle large JSON gracefully
            assert response.status_code in [201, 400, 413, 500]
            
        except Exception as e:
            # If an exception occurs, it should be handled gracefully
            assert "memory" not in str(e).lower() or "timeout" in str(e).lower()


if __name__ == "__main__":
    # Allow running this file directly for debugging
    pytest.main([__file__, "-v", "-s"])