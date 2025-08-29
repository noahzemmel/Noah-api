# models.py - Data models for Daily Noah business system
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum
import uuid

class SubscriptionTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"

class User:
    def __init__(self, email: str, password_hash: str, subscription_tier: SubscriptionTier = SubscriptionTier.FREE):
        self.id = str(uuid.uuid4())
        self.email = email
        self.password_hash = password_hash
        self.subscription_tier = subscription_tier
        self.created_at = datetime.now(timezone.utc)
        self.last_login = None
        self.is_active = True
        self.preferences = {
            "default_language": "English",
            "default_voice": "21m00Tcm4TlvDq8ikWAM",
            "default_duration": 5,
            "favorite_topics": []
        }
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "subscription_tier": self.subscription_tier,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "preferences": self.preferences
        }

class Subscription:
    def __init__(self, user_id: str, tier: SubscriptionTier, start_date: datetime):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.tier = tier
        self.start_date = start_date
        self.end_date = None
        self.is_active = True
        self.payment_status = "active"
        self.price = 7.99 if tier == SubscriptionTier.PREMIUM else 0.0
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_active": self.is_active,
            "payment_status": self.payment_status,
            "price": self.price
        }

class UserSession:
    def __init__(self, user_id: str, session_token: str):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_token = session_token
        self.created_at = datetime.now(timezone.utc)
        # Fix: Use proper datetime arithmetic for 24-hour expiry
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        self.is_active = True
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_token": self.session_token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active
        }
