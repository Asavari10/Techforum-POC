from decimal import Decimal
import random
import time
from datetime import datetime
from src.models.payment_models import db, Payment, Refund, Transaction, PaymentStatus, PaymentMethod
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

class PaymentProcessor:
    def __init__(self):
        self.supported_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
        self.max_amount = Decimal('10000.00')
        self.min_amount = Decimal('0.01')
    
    def validate_payment_request(self, payment_data):
        """Validate payment request data"""
        errors = []
        
        # Amount validation
        try:
            amount = Decimal(str(payment_data.get('amount', 0)))
            if amount < self.min_amount:
                errors.append(f"Amount must be at least {self.min_amount}")
            if amount > self.max_amount:
                errors.append(f"Amount cannot exceed {self.max_amount}")
        except (ValueError, TypeError, decimal.InvalidOperation):
            errors.append("Invalid amount format")
        
        # Currency validation
        currency = payment_data.get('currency', 'USD').upper()
        if currency not in self.supported_currencies:
            errors.append(f"Currency {currency} not supported. Supported: {', '.join(self.supported_currencies)}")
        
        # Required fields
        required_fields = ['merchant_id', 'customer_id', 'payment_method']
        for field in required_fields:
            if not payment_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Payment method validation
        payment_method = payment_data.get('payment_method')
        try:
            PaymentMethod(payment_method)
        except ValueError:
            valid_methods = [method.value for method in PaymentMethod]
            errors.append(f"Invalid payment method: {payment_method}. Valid methods: {', '.join(valid_methods)}")
        
        return errors
    
    def create_payment(self, payment_data):
        """Create a new payment"""
        validation_errors = self.validate_payment_request(payment_data)
        if validation_errors:
            return {'success': False, 'errors': validation_errors}
        
        try:
            payment = Payment(
                merchant_id=payment_data['merchant_id'],
                customer_id=payment_data['customer_id'],
                amount=Decimal(str(payment_data['amount'])),
                currency=payment_data.get('currency', 'USD').upper(),
                payment_method=PaymentMethod(payment_data['payment_method']),
                description=payment_data.get('description', ''),
                card_last_four=payment_data.get('card_last_four'),
                card_type=payment_data.get('card_type')
            )
            
            db.session.add(payment)
            db.session.commit()
            
            return {'success': True, 'payment': payment.to_dict()}
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def process_payment(self, payment_id):
        """Process a pending payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            if payment.status != PaymentStatus.PENDING:
                return {'success': False, 'errors': [f'Payment is not in pending status. Current status: {payment.status.value}']}
            
            # Simulate payment processing
            payment.status = PaymentStatus.PROCESSING
            db.session.commit()
            
            # Simulate gateway processing time
            time.sleep(0.1)
            
            # Simulate success/failure (90% success rate for demo)
            success = random.random() > 0.1
            
            if success:
                payment.status = PaymentStatus.COMPLETED
                payment.processed_at = datetime.utcnow()
                
                # Create transaction record
                transaction = Transaction(
                    payment_id=payment.id,
                    transaction_type='charge',
                    amount=payment.amount,
                    gateway_response='SUCCESS',
                    gateway_transaction_id=f"gw_{random.randint(100000, 999999)}"
                )
                db.session.add(transaction)
            else:
                payment.status = PaymentStatus.FAILED
                
                transaction = Transaction(
                    payment_id=payment.id,
                    transaction_type='charge',
                    amount=payment.amount,
                    gateway_response='DECLINED',
                    gateway_transaction_id=f"gw_{random.randint(100000, 999999)}"
                )
                db.session.add(transaction)
            
            db.session.commit()
            return {'success': True, 'payment': payment.to_dict()}
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def refund_payment(self, payment_id, refund_data):
        """Process a refund for a payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            if payment.status != PaymentStatus.COMPLETED:
                return {'success': False, 'errors': [f'Payment is not completed. Current status: {payment.status.value}']}
            
            refund_amount = Decimal(str(refund_data.get('amount', payment.amount)))
            
            # Calculate total refunded amount
            total_refunded = db.session.query(func.sum(Refund.amount)).filter(
                Refund.payment_id == payment.id,
                Refund.status == PaymentStatus.COMPLETED
            ).scalar() or Decimal('0')
            
            if total_refunded + refund_amount > payment.amount:
                available_amount = payment.amount - total_refunded
                return {'success': False, 'errors': [f'Refund amount {refund_amount} exceeds available amount {available_amount}']}
            
            refund = Refund(
                payment_id=payment.id,
                amount=refund_amount,
                reason=refund_data.get('reason', 'Customer request'),
                status=PaymentStatus.COMPLETED,
                processed_at=datetime.utcnow()
            )
            
            db.session.add(refund)
            
            # Update payment status
            new_total_refunded = total_refunded + refund_amount
            if new_total_refunded == payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIAL_REFUNDED
            
            # Create transaction record
            transaction = Transaction(
                payment_id=payment.id,
                transaction_type='refund',
                amount=refund_amount,
                gateway_response='SUCCESS',
                gateway_transaction_id=f"ref_{random.randint(100000, 999999)}"
            )
            db.session.add(transaction)
            
            db.session.commit()
            return {'success': True, 'refund': refund.to_dict()}
        
        except SQLAlchemyError as e:
            db.session.rollback()
            return {'success': False, 'errors': [f'Database error: {str(e)}']}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errors': [str(e)]}
    
    def get_payment(self, payment_id):
        """Get payment details"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            return {'success': True, 'payment': payment.to_dict()}
        
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
    
    def get_payment_transactions(self, payment_id):
        """Get all transactions for a payment"""
        try:
            payment = Payment.query.get(payment_id)
            if not payment:
                return {'success': False, 'errors': ['Payment not found']}
            
            transactions = Transaction.query.filter_by(payment_id=payment_id).order_by(Transaction.created_at.desc()).all()
            return {
                'success': True, 
                'transactions': [t.to_dict() for t in transactions]
            }
        
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}