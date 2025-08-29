# auth_service.py - Authentication and user management service
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models import User, Subscription, UserSession, SubscriptionTier

class AuthService:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        self._load_data()
    
    def _load_data(self):
        """Load user data from file (simple JSON storage for MVP)"""
        try:
            with open("users.json", "r") as f:
                data = json.load(f)
                # Reconstruct users from saved data
                for user_data in data.get("users", []):
                    user = User(
                        email=user_data["email"],
                        password_hash=user_data["password_hash"],
                        subscription_tier=SubscriptionTier(user_data["subscription_tier"])
                    )
                    user.id = user_data["id"]
                    user.created_at = datetime.fromisoformat(user_data["created_at"])
                    user.last_login = datetime.fromisoformat(user_data["last_login"]) if user_data["last_login"] else None
                    user.is_active = user_data["is_active"]
                    user.preferences = user_data["preferences"]
                    self.users[user.id] = user
        except FileNotFoundError:
            pass
    
    def _save_data(self):
        """Save user data to file"""
        data = {
            "users": [user.to_dict() for user in self.users.values()],
            "sessions": [session.to_dict() for session in self.sessions.values()],
            "subscriptions": [sub.to_dict() for sub in self.subscriptions.values()]
        }
        with open("users.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password) == password_hash
    
    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        # Check if email already exists
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return {"success": False, "error": "Email already registered"}
        
        # Create new user
        password_hash = self._hash_password(password)
        user = User(email=email, password_hash=password_hash)
        
        # Create free subscription
        subscription = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.FREE,
            start_date=datetime.utcnow()
        )
        
        # Store user and subscription
        self.users[user.id] = user
        self.subscriptions[subscription.id] = subscription
        
        # Save data
        self._save_data()
        
        return {
            "success": True,
            "user_id": user.id,
            "message": "User registered successfully"
        }
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and create session"""
        # Find user by email
        user = None
        for u in self.users.values():
            if u.email.lower() == email.lower():
                user = u
                break
        
        if not user:
            return {"success": False, "error": "Invalid email or password"}
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            return {"success": False, "error": "Invalid email or password"}
        
        # Check if user is active
        if not user.is_active:
            return {"success": False, "error": "Account is deactivated"}
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Create session
        session_token = self._generate_session_token()
        session = UserSession(user_id=user.id, session_token=session_token)
        self.sessions[session.id] = session
        
        # Save data
        self._save_data()
        
        return {
            "success": True,
            "session_token": session_token,
            "user": user.to_dict(),
            "subscription": self._get_user_subscription(user.id)
        }
    
    def _get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's subscription details"""
        for sub in self.subscriptions.values():
            if sub.user_id == user_id and sub.is_active:
                return sub.to_dict()
        return None
    
    def validate_session(self, session_token: str) -> Optional[User]:
        """Validate session token and return user if valid"""
        for session in self.sessions.values():
            if (session.session_token == session_token and 
                session.is_active and 
                session.expires_at > datetime.utcnow()):
                return self.users.get(session.user_id)
        return None
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session"""
        for session in self.sessions.values():
            if session.session_token == session_token:
                session.is_active = False
                self._save_data()
                return True
        return False
    
    def upgrade_subscription(self, user_id: str) -> Dict[str, Any]:
        """Upgrade user to premium subscription"""
        # Find current subscription
        current_sub = None
        for sub in self.subscriptions.values():
            if sub.user_id == user_id and sub.is_active:
                current_sub = sub
                break
        
        if current_sub:
            # Deactivate current subscription
            current_sub.is_active = False
            current_sub.end_date = datetime.utcnow()
        
        # Create new premium subscription
        new_subscription = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.PREMIUM,
            start_date=datetime.utcnow()
        )
        
        self.subscriptions[new_subscription.id] = new_subscription
        
        # Update user preferences
        user = self.users.get(user_id)
        if user:
            user.subscription_tier = SubscriptionTier.PREMIUM
        
        self._save_data()
        
        return {
            "success": True,
            "subscription": new_subscription.to_dict(),
            "message": "Upgraded to premium successfully"
        }
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences"""
        user = self.users.get(user_id)
        if user:
            return user.preferences
        return {}
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences"""
        user = self.users.get(user_id)
        if user:
            user.preferences.update(preferences)
            self._save_data()
            return True
        return False
