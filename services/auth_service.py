"""
============================================
AUTHENTICATION SERVICE
============================================
Handles password hashing, JWT token generation,
and token verification for user authentication.
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


# ============================================
# AUTH SERVICE CLASS
# ============================================
class AuthService:
    """Service class for authentication operations"""

    # ============================================
    # CONSTANTS
    # ============================================
    BCRYPT_ROUNDS = 12
    JWT_ALGORITHM = 'HS256'

    USER_TOKEN_EXPIRY_HOURS = 24
    ADMIN_TOKEN_EXPIRY_HOURS = 8
    REFRESH_TOKEN_EXPIRY_DAYS = 30


    # ============================================
    # PASSWORD HASHING
    # ============================================
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password string

        Raises:
            ValueError: If password is empty or invalid
        """

        if not password:
            raise ValueError('Password cannot be empty')

        if not isinstance(password, str):
            raise ValueError('Password must be a string')

        if len(password) < 6:
            raise ValueError('Password must be at least 6 characters')

        try:
            # Convert password to bytes
            password_bytes = password.encode('utf-8')

            # Generate salt
            salt = bcrypt.gensalt(rounds=AuthService.BCRYPT_ROUNDS)

            # Hash password
            hashed = bcrypt.hashpw(password_bytes, salt)

            # Return as string
            return hashed.decode('utf-8')

        except Exception as e:
            print(f"[HASH PASSWORD ERROR] {str(e)}")
            raise Exception(f'Failed to hash password: {str(e)}')


    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Stored hashed password

        Returns:
            bool: True if password matches, False otherwise
        """

        if not plain_password or not hashed_password:
            return False

        if not isinstance(plain_password, str):
            return False

        if not isinstance(hashed_password, str):
            return False

        try:
            # Convert to bytes
            plain_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')

            # Verify
            return bcrypt.checkpw(plain_bytes, hashed_bytes)

        except Exception as e:
            print(f"[VERIFY PASSWORD ERROR] {str(e)}")
            return False


    # ============================================
    # JWT TOKEN GENERATION
    # ============================================
    @staticmethod
    def generate_token(
        user_id: str,
        email: str,
        role: str = 'user',
        token_type: str = 'user',
        expires_in_hours: Optional[int] = None
    ) -> str:
        """
        Generate a JWT token for a user.

        Args:
            user_id: User's unique ID
            email: User's email address
            role: User's role (user/admin)
            token_type: Type of token (user/admin/refresh)
            expires_in_hours: Custom expiration time

        Returns:
            str: JWT token string

        Raises:
            Exception: If token generation fails
        """

        if not user_id:
            raise ValueError('User ID is required')

        if not email:
            raise ValueError('Email is required')

        try:
            # Get JWT secret
            jwt_secret = os.getenv('JWT_SECRET_KEY')

            if not jwt_secret:
                raise Exception('JWT_SECRET_KEY not configured')

            # Determine expiration
            if expires_in_hours is not None:
                expiry_delta = timedelta(hours=expires_in_hours)
            elif token_type == 'admin':
                expiry_delta = timedelta(hours=AuthService.ADMIN_TOKEN_EXPIRY_HOURS)
            elif token_type == 'refresh':
                expiry_delta = timedelta(days=AuthService.REFRESH_TOKEN_EXPIRY_DAYS)
            else:
                expiry_delta = timedelta(hours=AuthService.USER_TOKEN_EXPIRY_HOURS)

            # Build payload
            now = datetime.utcnow()

            payload = {
                'user_id': str(user_id),
                'email': email,
                'role': role,
                'type': token_type,
                'iat': now,
                'exp': now + expiry_delta,
                'iss': 'medai-backend'
            }

            # Generate token
            token = jwt.encode(
                payload,
                jwt_secret,
                algorithm=AuthService.JWT_ALGORITHM
            )

            # PyJWT returns bytes in older versions, string in newer
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            return token

        except Exception as e:
            print(f"[GENERATE TOKEN ERROR] {str(e)}")
            raise Exception(f'Failed to generate token: {str(e)}')


    # ============================================
    # JWT TOKEN VERIFICATION
    # ============================================
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            dict: Token payload if valid
            None: If token is invalid or expired
        """

        if not token:
            return None

        if not isinstance(token, str):
            return None

        try:
            jwt_secret = os.getenv('JWT_SECRET_KEY')

            if not jwt_secret:
                print("[VERIFY TOKEN ERROR] JWT_SECRET_KEY not configured")
                return None

            # Decode and verify
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=[AuthService.JWT_ALGORITHM]
            )

            # Validate required fields
            if not payload.get('user_id'):
                return None

            return payload

        except jwt.ExpiredSignatureError:
            print("[VERIFY TOKEN] Token has expired")
            return None

        except jwt.InvalidTokenError as e:
            print(f"[VERIFY TOKEN] Invalid token: {str(e)}")
            return None

        except Exception as e:
            print(f"[VERIFY TOKEN ERROR] {str(e)}")
            return None


    @staticmethod
    def decode_token(token: str, verify: bool = True) -> Optional[Dict[str, Any]]:
        """
        Decode a JWT token (with or without verification).

        Args:
            token: JWT token string
            verify: Whether to verify the signature

        Returns:
            dict: Decoded payload or None
        """

        if not token:
            return None

        try:
            if verify:
                jwt_secret = os.getenv('JWT_SECRET_KEY')
                if not jwt_secret:
                    return None

                return jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=[AuthService.JWT_ALGORITHM]
                )
            else:
                # Decode without verification (use carefully)
                return jwt.decode(
                    token,
                    options={'verify_signature': False}
                )

        except Exception as e:
            print(f"[DECODE TOKEN ERROR] {str(e)}")
            return None


    # ============================================
    # TOKEN UTILITIES
    # ============================================
    @staticmethod
    def get_token_expiry(token: str) -> Optional[datetime]:
        """
        Get the expiration datetime of a token.

        Args:
            token: JWT token string

        Returns:
            datetime: Expiration time or None
        """

        try:
            payload = AuthService.decode_token(token, verify=False)

            if not payload:
                return None

            exp_timestamp = payload.get('exp')

            if not exp_timestamp:
                return None

            return datetime.utcfromtimestamp(exp_timestamp)

        except Exception as e:
            print(f"[GET EXPIRY ERROR] {str(e)}")
            return None


    @staticmethod
    def is_token_expired(token: str) -> bool:
        """
        Check if a token is expired.

        Args:
            token: JWT token string

        Returns:
            bool: True if expired, False otherwise
        """

        try:
            expiry = AuthService.get_token_expiry(token)

            if not expiry:
                return True

            return datetime.utcnow() >= expiry

        except Exception:
            return True


    @staticmethod
    def get_token_remaining_time(token: str) -> Optional[int]:
        """
        Get remaining time in seconds before token expires.

        Args:
            token: JWT token string

        Returns:
            int: Seconds remaining or None
        """

        try:
            expiry = AuthService.get_token_expiry(token)

            if not expiry:
                return None

            remaining = (expiry - datetime.utcnow()).total_seconds()

            return max(0, int(remaining))

        except Exception:
            return None


    # ============================================
    # TOKEN REFRESH
    # ============================================
    @staticmethod
    def refresh_token(old_token: str) -> Optional[str]:
        """
        Generate a new token from an existing valid token.

        Args:
            old_token: Existing valid JWT token

        Returns:
            str: New JWT token or None if old token is invalid
        """

        try:
            payload = AuthService.verify_token(old_token)

            if not payload:
                return None

            return AuthService.generate_token(
                user_id=payload.get('user_id'),
                email=payload.get('email'),
                role=payload.get('role', 'user'),
                token_type=payload.get('type', 'user')
            )

        except Exception as e:
            print(f"[REFRESH TOKEN ERROR] {str(e)}")
            return None


    # ============================================
    # PASSWORD STRENGTH VALIDATION
    # ============================================
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """
        Check the strength of a password.

        Args:
            password: Password to check

        Returns:
            dict: Password strength analysis
        """

        if not password:
            return {
                'is_strong': False,
                'score': 0,
                'level': 'none',
                'feedback': ['Password is required']
            }

        score = 0
        feedback = []
        criteria = {
            'min_length': len(password) >= 6,
            'recommended_length': len(password) >= 10,
            'has_uppercase': any(c.isupper() for c in password),
            'has_lowercase': any(c.islower() for c in password),
            'has_number': any(c.isdigit() for c in password),
            'has_special': any(not c.isalnum() for c in password)
        }

        # Calculate score
        if criteria['min_length']:
            score += 1
        else:
            feedback.append('Password must be at least 6 characters')

        if criteria['recommended_length']:
            score += 1
        else:
            feedback.append('Use 10+ characters for better security')

        if criteria['has_uppercase']:
            score += 1
        else:
            feedback.append('Add uppercase letters')

        if criteria['has_lowercase']:
            score += 1

        if criteria['has_number']:
            score += 1
        else:
            feedback.append('Add numbers')

        if criteria['has_special']:
            score += 1
        else:
            feedback.append('Add special characters')

        # Determine level
        if score <= 2:
            level = 'weak'
        elif score == 3:
            level = 'fair'
        elif score == 4:
            level = 'good'
        else:
            level = 'strong'

        return {
            'is_strong': score >= 4,
            'score': score,
            'max_score': 6,
            'level': level,
            'criteria': criteria,
            'feedback': feedback
        }


    # ============================================
    # GENERATE RANDOM PASSWORD
    # ============================================
    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """
        Generate a random secure password.

        Args:
            length: Length of password (default 16)

        Returns:
            str: Random password
        """

        import secrets
        import string

        if length < 8:
            length = 8

        if length > 128:
            length = 128

        # Character set
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'

        # Generate password
        password = ''.join(secrets.choice(alphabet) for _ in range(length))

        return password


    # ============================================
    # GENERATE API KEY
    # ============================================
    @staticmethod
    def generate_api_key(prefix: str = 'medai') -> str:
        """
        Generate a random API key.

        Args:
            prefix: Prefix for the key

        Returns:
            str: Random API key
        """

        import secrets

        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"


    # ============================================
    # COMPARE TOKENS SAFELY
    # ============================================
    @staticmethod
    def compare_tokens(token1: str, token2: str) -> bool:
        """
        Compare two tokens in constant time to prevent timing attacks.

        Args:
            token1: First token
            token2: Second token

        Returns:
            bool: True if tokens match
        """

        if not token1 or not token2:
            return False

        if len(token1) != len(token2):
            return False

        import hmac
        return hmac.compare_digest(token1.encode(), token2.encode())


    # ============================================
    # EXTRACT TOKEN FROM HEADER
    # ============================================
    @staticmethod
    def extract_token_from_header(auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header.

        Args:
            auth_header: Full Authorization header value

        Returns:
            str: Token string or None
        """

        if not auth_header:
            return None

        if not isinstance(auth_header, str):
            return None

        parts = auth_header.split()

        if len(parts) != 2:
            return None

        if parts[0].lower() != 'bearer':
            return None

        return parts[1]


    # ============================================
    # VALIDATE EMAIL FORMAT
    # ============================================
    @staticmethod
    def is_valid_email_format(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address

        Returns:
            bool: True if valid format
        """

        if not email or not isinstance(email, str):
            return False

        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        return bool(re.match(pattern, email.strip()))


    # ============================================
    # SANITIZE INPUT
    # ============================================
    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Sanitize email address.

        Args:
            email: Email address

        Returns:
            str: Sanitized lowercase email
        """

        if not email:
            return ''

        return email.strip().lower()


    @staticmethod
    def sanitize_name(name: str) -> str:
        """
        Sanitize user name.

        Args:
            name: User name

        Returns:
            str: Sanitized name
        """

        if not name:
            return ''

        # Remove leading/trailing whitespace
        sanitized = name.strip()

        # Replace multiple spaces with single space
        sanitized = ' '.join(sanitized.split())

        return sanitized