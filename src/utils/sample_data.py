"""Script to populate database with sample payment data for testing"""
import os
import sys
from pathlib import Path
import requests
import random
import time
import json
from decimal import Decimal

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# Fixed API base URL - use localhost instead of 0.0.0.0
API_BASE = f"http://localhost:{os.getenv('API_PORT', '5000')}/api/v1"

class SampleDataGenerator:
    def __init__(self):
        self.merchants = [
            'MERCHANT_001', 'MERCHANT_002', 'MERCHANT_003', 
            'MERCHANT_004', 'MERCHANT_005'
        ]
        self.customers = [
            'CUSTOMER_001', 'CUSTOMER_002', 'CUSTOMER_003', 
            'CUSTOMER_004', 'CUSTOMER_005', 'CUSTOMER_006',
            'CUSTOMER_007', 'CUSTOMER_008', 'CUSTOMER_009', 
            'CUSTOMER_010'
        ]
        self.currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
        self.payment_methods = ['credit_card', 'debit_card', 'bank_transfer', 'digital_wallet']
        self.card_types = ['VISA', 'MASTERCARD', 'AMEX', 'DISCOVER']
        self.descriptions = [
            'Online purchase', 'Subscription payment', 'Invoice payment',
            'Service fee', 'Product purchase', 'Monthly subscription',
            'Annual membership', 'Digital service', 'Consulting fee',
            'Software license'
        ]

    def generate_card_details(self):
        """Generate random card details"""
        return {
            'card_last_four': f"{random.randint(1000, 9999)}",
            'card_type': random.choice(self.card_types)
        }

    def generate_amount(self, currency='USD'):
        """Generate realistic payment amounts based on currency"""
        if currency == 'JPY':
            # JPY doesn't use decimals
            return random.randint(100, 50000)
        elif currency in ['USD', 'EUR', 'GBP', 'CAD']:
            # Standard decimal currencies
            amounts = [9.99, 19.99, 29.99, 49.99, 99.99, 149.99, 199.99, 299.99, 499.99, 999.99]
            return random.choice(amounts) + random.uniform(0, 50)
        else:
            return random.uniform(10, 1000)

    def create_payment_data(self):
        """Generate a single payment data object"""
        currency = random.choice(self.currencies)
        payment_method = random.choice(self.payment_methods)
        
        payment_data = {
            'merchant_id': random.choice(self.merchants),
            'customer_id': random.choice(self.customers),
            'amount': round(self.generate_amount(currency), 2),
            'currency': currency,
            'payment_method': payment_method,
            'description': random.choice(self.descriptions)
        }
        
        # Add card details for card payments
        if payment_method in ['credit_card', 'debit_card']:
            payment_data.update(self.generate_card_details())
        
        return payment_data

    def test_api_connection(self):
        """Test if API is accessible"""
        try:
            health_url = API_BASE.replace('/api/v1', '/health')
            print(f"Testing connection to: {health_url}")
            
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✓ API is healthy: {health_data}")
                return True
            else:
                print(f"✗ API health check failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Cannot connect to API: {e}")
            print(f"Make sure the API is running and try:")
            print(f"  1. Check if server is running: http://localhost:5000/health")
            print(f"  2. If server shows 0.0.0.0, use localhost in browser")
            print(f"  3. Try: curl http://localhost:5000/health")
            return False

    def create_payment(self, payment_data):
        """Create a single payment via API"""
        try:
            response = requests.post(f"{API_BASE}/payments", json=payment_data, timeout=10)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create payment: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error creating payment: {e}")
            return None

    def process_payment(self, payment_id):
        """Process a payment"""
        try:
            response = requests.post(f"{API_BASE}/payments/{payment_id}/process", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to process payment {payment_id}: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error processing payment {payment_id}: {e}")
            return None

    def create_refund(self, payment_id, refund_amount, reason="Customer request"):
        """Create a refund for a payment"""
        try:
            refund_data = {
                'amount': refund_amount,
                'reason': reason
            }
            response = requests.post(f"{API_BASE}/payments/{payment_id}/refund", json=refund_data, timeout=10)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"Failed to create refund for {payment_id}: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error creating refund for {payment_id}: {e}")
            return None

    def generate_sample_data(self, num_payments=20):
        """Generate comprehensive sample data"""
        if not self.test_api_connection():
            return {
                'created': [],
                'processed': [],
                'refunded': []
            }

        print(f"\nGenerating {num_payments} sample payments...")
        created_payments = []
        processed_payments = []
        refunded_payments = []

        # Create payments
        for i in range(num_payments):
            payment_data = self.create_payment_data()
            print(f"Creating payment {i+1}/{num_payments}: {payment_data['amount']} {payment_data['currency']}")
            
            result = self.create_payment(payment_data)
            if result and result.get('success'):
                payment = result['payment']
                created_payments.append(payment)
                print(f"  ✓ Created payment: {payment['id']}")
                
                # Process 80% of payments
                if random.random() > 0.2:
                    time.sleep(0.1)  # Small delay to simulate real-world timing
                    process_result = self.process_payment(payment['id'])
                    if process_result and process_result.get('success'):
                        processed_payment = process_result['payment']
                        processed_payments.append(processed_payment)
                        print(f"  ✓ Processed payment: {payment['id']} - Status: {processed_payment['status']}")
                        
                        # Create refunds for 20% of successful payments
                        if processed_payment['status'] == 'completed' and random.random() > 0.8:
                            time.sleep(0.1)
                            refund_amount = round(float(processed_payment['amount']) * random.uniform(0.3, 1.0), 2)
                            refund_reasons = [
                                "Customer request", "Product defect", "Service issue", 
                                "Billing error", "Duplicate charge", "Cancelled order"
                            ]
                            refund_result = self.create_refund(
                                payment['id'], 
                                refund_amount, 
                                random.choice(refund_reasons)
                            )
                            if refund_result and refund_result.get('success'):
                                refunded_payments.append(refund_result['refund'])
                                print(f"  ✓ Created refund: {refund_amount} for payment {payment['id']}")
            else:
                print(f"  ✗ Failed to create payment")

        return {
            'created': created_payments,
            'processed': processed_payments,
            'refunded': refunded_payments
        }

    def create_specific_test_scenarios(self):
        """Create specific test scenarios for comprehensive testing"""
        print("\nCreating specific test scenarios...")
        scenarios = []

        # Only proceed if API is accessible
        health_url = API_BASE.replace('/api/v1', '/health')
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code != 200:
                print("API not accessible, skipping scenarios")
                return []
        except:
            print("API not accessible, skipping scenarios")
            return []

        # Scenario 1: Large payment
        large_payment = {
            'merchant_id': 'MERCHANT_001',
            'customer_id': 'CUSTOMER_VIP',
            'amount': 5000.00,
            'currency': 'USD',
            'payment_method': 'bank_transfer',
            'description': 'Large corporate payment'
        }
        scenarios.append(('Large Payment', large_payment))

        # Scenario 2: Multi-currency payments
        currencies = ['USD', 'EUR', 'GBP', 'JPY']
        for currency in currencies:
            payment = {
                'merchant_id': 'MERCHANT_GLOBAL',
                'customer_id': f'CUSTOMER_{currency}',
                'amount': self.generate_amount(currency),
                'currency': currency,
                'payment_method': 'credit_card',
                'description': f'Multi-currency test - {currency}',
                **self.generate_card_details()
            }
            scenarios.append((f'{currency} Payment', payment))

        # Scenario 3: Edge case amounts
        edge_amounts = [0.01, 0.99, 1.00, 999.99, 9999.99]
        for amount in edge_amounts:
            payment = {
                'merchant_id': 'MERCHANT_EDGE',
                'customer_id': 'CUSTOMER_EDGE',
                'amount': amount,
                'currency': 'USD',
                'payment_method': 'credit_card',
                'description': f'Edge case amount: {amount}',
                **self.generate_card_details()
            }
            scenarios.append((f'Edge Amount ${amount}', payment))

        # Execute scenarios
        scenario_results = []
        for scenario_name, payment_data in scenarios:
            print(f"Creating scenario: {scenario_name}")
            result = self.create_payment(payment_data)
            if result and result.get('success'):
                scenario_results.append((scenario_name, result['payment']))
                print(f"  ✓ Created: {result['payment']['id']}")
            else:
                print(f"  ✗ Failed to create scenario: {scenario_name}")

        return scenario_results

    def print_summary(self, results):
        """Print summary of created data"""
        print("\n" + "="*60)
        print("SAMPLE DATA GENERATION SUMMARY")
        print("="*60)
        
        print(f"Total Payments Created: {len(results['created'])}")
        print(f"Total Payments Processed: {len(results['processed'])}")
        print(f"Total Refunds Created: {len(results['refunded'])}")
        
        # Payment status breakdown
        if results['processed']:
            status_counts = {}
            for payment in results['processed']:
                status = payment['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("\nPayment Status Breakdown:")
            for status, count in status_counts.items():
                print(f"  {status.upper()}: {count}")

        # Currency breakdown
        if results['created']:
            currency_counts = {}
            total_amounts = {}
            for payment in results['created']:
                currency = payment['currency']
                amount = float(payment['amount'])
                currency_counts[currency] = currency_counts.get(currency, 0) + 1
                total_amounts[currency] = total_amounts.get(currency, 0) + amount
            
            print("\nCurrency Breakdown:")
            for currency in sorted(currency_counts.keys()):
                print(f"  {currency}: {currency_counts[currency]} payments, Total: {total_amounts[currency]:.2f}")

        print("\nAPI Endpoints to test:")
        health_url = API_BASE.replace('/api/v1', '/health')
        print(f"  Health Check: {health_url}")
        print(f"  List Payments: {API_BASE}/payments")
        print(f"  Payment Details: {API_BASE}/payments/{{payment_id}}")
        print(f"  Payment Transactions: {API_BASE}/payments/{{payment_id}}/transactions")


def main():
    """Main function to generate sample data"""
    print("Payment System Sample Data Generator")
    print("=" * 50)
    
    generator = SampleDataGenerator()
    
    # Generate main sample data
    results = generator.generate_sample_data(num_payments=25)
    
    # Create specific test scenarios
    scenarios = generator.create_specific_test_scenarios()
    
    # Print summary
    generator.print_summary(results)
    
    print(f"\nScenario Results: {len(scenarios)} scenarios created")
    
    if results['created']:
        print("\n✓ Sample data generation complete!")
        print("\nYou can now test the API endpoints or run the test suite.")
    else:
        print("\n✗ No data was created. Please check API connection.")
        print("\nTroubleshooting steps:")
        print("1. Make sure the server is running: python run_server.py")
        print("2. Test manually: curl http://localhost:5000/health")
        print("3. Check .env file for correct port configuration")


if __name__ == "__main__":
    main()