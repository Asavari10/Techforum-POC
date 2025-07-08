from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from enum import Enum
from sqlalchemy import func
from decimal import Decimal

db = SQLAlchemy()

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"

class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = db.Column(db.String(100), nullable=False, index=True)
    customer_id = db.Column(db.String(100), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    description = db.Column(db.Text)
    
    # Card details (simplified for demo)
    card_last_four = db.Column(db.String(4))
    card_type = db.Column(db.String(20))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime)
    
    # Relationships
    refunds = db.relationship('Refund', backref='payment', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='payment', lazy=True, cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_merchant_customer', 'merchant_id', 'customer_id'),
        db.Index('idx_status_created', 'status', 'created_at'),
        db.Index('idx_amount_currency', 'amount', 'currency'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'merchant_id': self.merchant_id,
            'customer_id': self.customer_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method.value,
            'status': self.status.value,
            'description': self.description,
            'card_last_four': self.card_last_four,
            'card_type': self.card_type,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class Refund(db.Model):
    __tablename__ = 'refunds'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = db.Column(db.String(36), db.ForeignKey('payments.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.String(200))
    status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    processed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'amount': float(self.amount),
            'reason': self.reason,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = db.Column(db.String(36), db.ForeignKey('payments.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False, index=True)  # charge, refund, void
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    gateway_response = db.Column(db.Text)
    gateway_transaction_id = db.Column(db.String(100), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'gateway_response': self.gateway_response,
            'gateway_transaction_id': self.gateway_transaction_id,
            'created_at': self.created_at.isoformat()
        }