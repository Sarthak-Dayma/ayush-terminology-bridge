"""
ABHA (Ayushman Bharat Health Account) OAuth2 Authentication
Simulated authentication for demo purposes - can be connected to real ABDM APIs
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
import os

class ABHAAuthService:
    def __init__(self, config_path: str = 'config/abha_config.json'):
        """Initialize ABHA authentication service"""
        self.config = {} # ADDED: Initialize config
        self.load_config(config_path)
        
        # CHANGED: Use secret key from the loaded config file for consistency
        self.secret_key = os.environ.get('JWT_SECRET_KEY', self.config.get('jwt_settings', {}).get('secret_key', 'your-secret-key-change-in-production'))
        
        # ADDED: Load users from the config file, not a hardcoded list
        # This converts the list of users from JSON into a dictionary keyed by user_id
        self.users_db = {user['user_id']: user for user in self.config.get('mock_users', [])}
        if not self.users_db:
             print("⚠️  Warning: No mock users found in abha_config.json")
    
    def load_config(self, config_path: str):
        """Load ABHA configuration"""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            # Default config for demo if file is missing
            print(f"⚠️  Warning: {config_path} not found. Using default demo config.")
            self.config = {
                'jwt_settings': {
                    'secret_key': 'your-secret-key-change-in-production',
                    'access_token_expire_minutes': 60
                },
                'mock_users': [{
                    'user_id': 'DR001',
                    'password': 'demo_password',
                    'name': 'Default User',
                    'role': 'practitioner',
                    'abha_id': '00-0000-0000-0000',
                    'email': 'default@example.com',
                    'facility': 'Default Facility'
                }]
            }
            
    def generate_mock_abha_token(self, user_id: str, password: str) -> Optional[Dict]:
        """
        Generate mock ABHA token for demo
        In production, this would call ABDM APIs
        """
        user = self.users_db.get(user_id)
        
        # Mock authentication: check if user exists and password matches
        if not user or user.get('password') != password:
            return None
        
        # Fetch token expiration from the nested jwt_settings object
        expire_minutes = self.config['jwt_settings']['access_token_expire_minutes']

        # Generate JWT token
        token_data = {
            'user_id': user_id,
            'abha_id': user['abha_id'],
            'name': user['name'],
            'role': user['role'],
            'facility': user.get('facility', 'N/A'),
            'email': user.get('email'),
            'permissions': user.get('permissions', []), # ADDED permissions
            'iat': datetime.utcnow(),
            # CHANGED: Use the correct nested key from your config
            'exp': datetime.utcnow() + timedelta(minutes=expire_minutes)
        }
        
        access_token = jwt.encode(token_data, self.secret_key, algorithm=self.config['jwt_settings']['algorithm'])
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(32)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            # CHANGED: Use the correct nested key from your config
            'expires_in': expire_minutes * 60,
            'user_info': {
                'user_id': user_id,
                'abha_id': user['abha_id'],
                'name': user['name'],
                'role': user['role'],
                'facility': user.get('facility', 'N/A'),
                'specialization': user.get('specialization', 'N/A'),
                'email': user.get('email')
            }
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user info"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.config['jwt_settings']['algorithm']]
            )
            # No need for manual expiration check, pyjwt does it automatically
            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Any other token error
            return None
    
    def get_user_info(self, token: str) -> Optional[Dict]:
        """Get user information from token"""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        user_id = payload.get('user_id')
        return self.users_db.get(user_id)
    
    def check_permission(self, token: str, required_role: str) -> bool:
        """Check if user has required role/permission"""
        payload = self.verify_token(token)
        if not payload:
            return False
        
        user_role = payload.get('role')
        
        # Using role_permissions from config if available, otherwise fallback
        role_config = self.config.get('role_permissions', {}).get(user_role)
        if role_config:
            # A more dynamic permission check could be added here if needed
            # For now, we stick to a simple role hierarchy
            pass

        role_levels = {
            'admin': 4,
            'auditor': 3,
            'researcher': 2,
            'practitioner': 1
        }
        
        user_level = role_levels.get(user_role, 0)
        required_level = role_levels.get(required_role, 999) # Default to a high number
        
        return user_level >= required_level
    
    def create_session(self, user_id: str) -> str:
        """Create session ID for tracking"""
        session_data = f"{user_id}-{datetime.utcnow().isoformat()}-{secrets.token_hex(8)}"
        session_id = hashlib.sha256(session_data.encode()).hexdigest()[:16]
        return session_id
    
    # ... (register_user and validate_abha_id methods can remain as they are) ...
    def register_user(self, user_data: Dict) -> Dict:
        """
        Register new user (mock implementation) - Note: This only adds to the in-memory DB.
        """
        user_id = f"DR{secrets.randbelow(1000):03d}"
        
        self.users_db[user_id] = {
            'user_id': user_id,
            'password': user_data.get('password', 'password'), # Added default password
            'abha_id': user_data.get('abha_id'),
            'name': user_data.get('name'),
            'role': user_data.get('role', 'practitioner'),
            'facility': user_data.get('facility'),
            'specialization': user_data.get('specialization'),
            'license': user_data.get('license'),
            'email': user_data.get('email'),
            'phone': user_data.get('phone')
        }
        
        return {
            'user_id': user_id,
            'status': 'registered',
            'message': 'User registered successfully (session only)'
        }
    
    def validate_abha_id(self, abha_id: str) -> bool:
        """Validate ABHA ID format using regex from config"""
        import re
        validation_config = self.config.get('abha_validation', {})
        if not validation_config.get('validate_abha_format', True):
            return True # Skip validation if disabled
        
        pattern = validation_config.get('abha_regex', r'^\d{2}-\d{4}-\d{4}-\d{4}$')
        return bool(re.match(pattern, abha_id))


class AuthMiddleware:
    """Middleware for FastAPI/Flask to handle authentication"""
    
    def __init__(self, auth_service: ABHAAuthService):
        self.auth_service = auth_service
    
    def authenticate_request(self, authorization_header: Optional[str]) -> Optional[Dict]:
        """
        Extract and verify token from Authorization header
        
        Args:
            authorization_header: "Bearer <token>"
        
        Returns:
            User payload if valid, None otherwise
        """
        if not authorization_header:
            return None
        
        try:
            scheme, token = authorization_header.split()
            if scheme.lower() != 'bearer':
                return None
            
            return self.auth_service.verify_token(token)
        except ValueError:
            return None
    
    def require_role(self, user_payload: Optional[Dict], required_role: str) -> bool:
        """Check if user has required role"""
        if not user_payload:
            return False
        
        # Let the auth service handle the logic
        user_role = user_payload.get('role')
        
        role_levels = {
            'admin': 4,
            'auditor': 3,
            'researcher': 2,
            'practitioner': 1
        }
        
        user_level = role_levels.get(user_role, 0)
        required_level = role_levels.get(required_role, 999)
        
        return user_level >= required_level

# Example usage
if __name__ == "__main__":
    # Point to the actual config for testing
    auth = ABHAAuthService(config_path='../config/abha_config.json')
    
    # Mock login with a user from the JSON file
    test_user = "ADMIN001"
    test_pass = "admin_password"
    result = auth.generate_mock_abha_token(test_user, test_pass)

    if result:
        print("✅ Login successful!")
        print(f"Access Token: {result['access_token'][:50]}...")
        print(f"User: {result['user_info']['name']}")
        print(f"Role: {result['user_info']['role']}")
        
        # Verify token
        access_token = result['access_token']
        payload = auth.verify_token(access_token)
        print(f"\n✅ Token verified for: {payload['name']}")
        
        # Check permission
        has_admin_perm = auth.check_permission(access_token, 'admin')
        print(f"Has admin permission: {has_admin_perm}")

        has_practitioner_perm = auth.check_permission(access_token, 'practitioner')
        print(f"Has practitioner permission: {has_practitioner_perm}")

    else:
        print(f"❌ Login failed for user: {test_user}")