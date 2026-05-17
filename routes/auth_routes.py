"""
============================================
AUTHENTICATION ROUTES
============================================
Handles user registration, login, logout,
profile management, and password operations.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import re

from services.auth_service import AuthService
from models.database import get_admin_supabase, UserDB
from middleware.auth_middleware import token_required


# ============================================
# CREATE BLUEPRINT
# ============================================
auth_bp = Blueprint('auth', __name__)


# ============================================
# CONSTANTS
# ============================================
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128
NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 100


# ============================================
# VALIDATION HELPERS
# ============================================
def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_password(password):
    """Validate password strength"""
    if not password:
        return False, 'Password is required'

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f'Password must be at least {PASSWORD_MIN_LENGTH} characters'

    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f'Password must be less than {PASSWORD_MAX_LENGTH} characters'

    return True, None


def is_valid_age(age):
    """Validate age value"""
    try:
        age = int(age)
        if age < 1 or age > 120:
            return False, 'Age must be between 1 and 120'
        return True, age
    except (ValueError, TypeError):
        return False, 'Invalid age value'


def is_valid_gender(gender):
    """Validate gender value"""
    valid_genders = ['male', 'female', 'other']
    if gender and gender.lower() not in valid_genders:
        return False, 'Gender must be male, female, or other'
    return True, gender


def sanitize_user_response(user):
    """Remove sensitive fields from user object"""
    if not user:
        return None

    sensitive_fields = ['password_hash', 'password']
    return {k: v for k, v in user.items() if k not in sensitive_fields}


# ============================================
# REGISTER ENDPOINT
# ============================================
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user account.

    Request Body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123",
        "age": 25,
        "gender": "male"
    }

    Returns:
        201: User created successfully with token
        400: Validation error
        409: Email already exists
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        # Extract fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        age = data.get('age')
        gender = data.get('gender', '').strip().lower() if data.get('gender') else None

        # Validate name
        if not name or len(name) < NAME_MIN_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Name must be at least {NAME_MIN_LENGTH} characters'
            }), 400

        if len(name) > NAME_MAX_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Name must be less than {NAME_MAX_LENGTH} characters'
            }), 400

        # Validate email
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400

        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        # Validate password
        password_valid, password_error = is_valid_password(password)
        if not password_valid:
            return jsonify({
                'success': False,
                'message': password_error
            }), 400

        # Validate age (optional)
        if age is not None:
            age_valid, age_result = is_valid_age(age)
            if not age_valid:
                return jsonify({
                    'success': False,
                    'message': age_result
                }), 400
            age = age_result

        # Validate gender (optional)
        if gender:
            gender_valid, gender_error = is_valid_gender(gender)
            if not gender_valid:
                return jsonify({
                    'success': False,
                    'message': gender_error
                }), 400

        # Check if user already exists
        existing_user = UserDB.get_by_email(email)
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'An account with this email already exists'
            }), 409

        # Hash password
        password_hash = AuthService.hash_password(password)

        # Create user data
        user_data = {
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'role': 'user',
            'is_active': True
        }

        if age is not None:
            user_data['age'] = age

        if gender:
            user_data['gender'] = gender

        # Save user to database
        new_user = UserDB.create(user_data)

        if not new_user:
            return jsonify({
                'success': False,
                'message': 'Failed to create user account'
            }), 500

        # Generate JWT token
        token = AuthService.generate_token(
            user_id=new_user['id'],
            email=new_user['email'],
            role='user',
            token_type='user'
        )

        # Update last login
        UserDB.update(new_user['id'], {
            'last_login': datetime.utcnow().isoformat()
        })

        # Sanitize user data
        safe_user = sanitize_user_response(new_user)

        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'token': token,
            'user': safe_user
        }), 201

    except Exception as e:
        print(f"[REGISTER ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration',
            'error': str(e)
        }), 500


# ============================================
# LOGIN ENDPOINT
# ============================================
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email and password.

    Request Body:
    {
        "email": "john@example.com",
        "password": "SecurePass123"
    }

    Returns:
        200: Login successful with token
        400: Validation error
        401: Invalid credentials
        403: Account deactivated
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        # Validate input
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400

        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        # Get user from database
        user = UserDB.get_by_email(email)

        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401

        # Verify password
        password_valid = AuthService.verify_password(
            password,
            user.get('password_hash', '')
        )

        if not password_valid:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401

        # Check if account is active
        if not user.get('is_active', True):
            return jsonify({
                'success': False,
                'message': 'Your account has been deactivated. Please contact support.'
            }), 403

        # Check role - regular users only here
        if user.get('role') == 'admin':
            return jsonify({
                'success': False,
                'message': 'Please use the admin login page'
            }), 403

        # Generate token
        token = AuthService.generate_token(
            user_id=user['id'],
            email=user['email'],
            role=user.get('role', 'user'),
            token_type='user'
        )

        # Update last login
        UserDB.update(user['id'], {
            'last_login': datetime.utcnow().isoformat()
        })

        # Sanitize user response
        safe_user = sanitize_user_response(user)

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[LOGIN ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during login',
            'error': str(e)
        }), 500


# ============================================
# ADMIN LOGIN ENDPOINT
# ============================================
@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    """
    Admin login with email and password.

    Request Body:
    {
        "email": "admin@medai.com",
        "password": "AdminPass123"
    }

    Returns:
        200: Admin login successful
        400: Validation error
        401: Invalid credentials
        403: Not an admin or deactivated
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        # Validate input
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400

        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400

        # Get user from database
        user = UserDB.get_by_email(email)

        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid admin credentials'
            }), 401

        # Verify password
        password_valid = AuthService.verify_password(
            password,
            user.get('password_hash', '')
        )

        if not password_valid:
            return jsonify({
                'success': False,
                'message': 'Invalid admin credentials'
            }), 401

        # Check admin role
        if user.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin access required'
            }), 403

        # Check if account is active
        if not user.get('is_active', True):
            return jsonify({
                'success': False,
                'message': 'Admin account has been deactivated'
            }), 403

        # Generate admin token
        token = AuthService.generate_token(
            user_id=user['id'],
            email=user['email'],
            role='admin',
            token_type='admin'
        )

        # Update last login
        UserDB.update(user['id'], {
            'last_login': datetime.utcnow().isoformat()
        })

        # Sanitize user response
        safe_user = sanitize_user_response(user)

        return jsonify({
            'success': True,
            'message': 'Admin login successful',
            'token': token,
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[ADMIN LOGIN ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during admin login',
            'error': str(e)
        }), 500


# ============================================
# LOGOUT ENDPOINT
# ============================================
@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Logout the current user.
    Note: JWT tokens are stateless, so this is mostly for client-side cleanup.

    Returns:
        200: Logout successful
        401: Not authenticated
    """

    try:
        return jsonify({
            'success': True,
            'message': 'Logout successful. Please clear your token.'
        }), 200

    except Exception as e:
        print(f"[LOGOUT ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout',
            'error': str(e)
        }), 500


# ============================================
# GET CURRENT USER ENDPOINT
# ============================================
@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """
    Get the currently authenticated user's information.

    Returns:
        200: User information
        401: Not authenticated
    """

    try:
        user = g.current_user

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        safe_user = sanitize_user_response(user)

        return jsonify({
            'success': True,
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[GET ME ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch user information',
            'error': str(e)
        }), 500


# ============================================
# UPDATE PROFILE ENDPOINT
# ============================================
@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """
    Update the current user's profile.

    Request Body:
    {
        "name": "Updated Name",
        "age": 26,
        "gender": "male"
    }

    Returns:
        200: Profile updated successfully
        400: Validation error
        401: Not authenticated
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        user_id = g.current_user_id
        update_data = {}

        # Validate and add name
        if 'name' in data:
            name = data['name'].strip() if data['name'] else ''

            if not name or len(name) < NAME_MIN_LENGTH:
                return jsonify({
                    'success': False,
                    'message': f'Name must be at least {NAME_MIN_LENGTH} characters'
                }), 400

            if len(name) > NAME_MAX_LENGTH:
                return jsonify({
                    'success': False,
                    'message': f'Name must be less than {NAME_MAX_LENGTH} characters'
                }), 400

            update_data['name'] = name

        # Validate and add age
        if 'age' in data and data['age'] is not None:
            age_valid, age_result = is_valid_age(data['age'])
            if not age_valid:
                return jsonify({
                    'success': False,
                    'message': age_result
                }), 400
            update_data['age'] = age_result

        # Validate and add gender
        if 'gender' in data and data['gender']:
            gender = data['gender'].strip().lower()
            gender_valid, gender_error = is_valid_gender(gender)
            if not gender_valid:
                return jsonify({
                    'success': False,
                    'message': gender_error
                }), 400
            update_data['gender'] = gender

        # Add profile image if provided
        if 'profile_image' in data:
            update_data['profile_image'] = data['profile_image']

        if not update_data:
            return jsonify({
                'success': False,
                'message': 'No valid fields to update'
            }), 400

        # Update user
        updated_user = UserDB.update(user_id, update_data)

        if not updated_user:
            return jsonify({
                'success': False,
                'message': 'Failed to update profile'
            }), 500

        safe_user = sanitize_user_response(updated_user)

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[UPDATE PROFILE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update profile',
            'error': str(e)
        }), 500


# ============================================
# CHANGE PASSWORD ENDPOINT
# ============================================
@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """
    Change the current user's password.

    Request Body:
    {
        "current_password": "OldPass123",
        "new_password": "NewPass456"
    }

    Returns:
        200: Password changed successfully
        400: Validation error
        401: Current password incorrect
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        # Validate input
        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Current and new passwords are required'
            }), 400

        # Validate new password
        password_valid, password_error = is_valid_password(new_password)
        if not password_valid:
            return jsonify({
                'success': False,
                'message': password_error
            }), 400

        # Check if same as old password
        if current_password == new_password:
            return jsonify({
                'success': False,
                'message': 'New password must be different from current password'
            }), 400

        # Get user with password hash
        user_id = g.current_user_id
        user = UserDB.get_by_id(user_id)

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Verify current password
        password_correct = AuthService.verify_password(
            current_password,
            user.get('password_hash', '')
        )

        if not password_correct:
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 401

        # Hash new password
        new_password_hash = AuthService.hash_password(new_password)

        # Update password
        updated_user = UserDB.update(user_id, {
            'password_hash': new_password_hash
        })

        if not updated_user:
            return jsonify({
                'success': False,
                'message': 'Failed to change password'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200

    except Exception as e:
        print(f"[CHANGE PASSWORD ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to change password',
            'error': str(e)
        }), 500


# ============================================
# DELETE ACCOUNT ENDPOINT
# ============================================
@auth_bp.route('/delete-account', methods=['DELETE'])
@token_required
def delete_account():
    """
    Delete the current user's account permanently.
    All associated data will be removed.

    Returns:
        200: Account deleted successfully
        401: Not authenticated
        500: Server error
    """

    try:
        user_id = g.current_user_id

        # Delete user (cascading will handle related records)
        success = UserDB.delete(user_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete account'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Your account has been permanently deleted'
        }), 200

    except Exception as e:
        print(f"[DELETE ACCOUNT ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete account',
            'error': str(e)
        }), 500


# ============================================
# VERIFY TOKEN ENDPOINT
# ============================================
@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token_endpoint():
    """
    Verify if the current token is valid.

    Returns:
        200: Token is valid
        401: Token is invalid or expired
    """

    try:
        return jsonify({
            'success': True,
            'message': 'Token is valid',
            'user_id': g.current_user_id,
            'role': g.current_user_role
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Token verification failed',
            'error': str(e)
        }), 401


# ============================================
# REFRESH TOKEN ENDPOINT
# ============================================
@auth_bp.route('/refresh', methods=['POST'])
@token_required
def refresh_token():
    """
    Refresh the JWT token (issue a new one).

    Returns:
        200: New token issued
        401: Not authenticated
    """

    try:
        user = g.current_user
        token_payload = g.token_payload

        # Generate new token
        new_token = AuthService.generate_token(
            user_id=user['id'],
            email=user['email'],
            role=user.get('role', 'user'),
            token_type=token_payload.get('type', 'user')
        )

        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'token': new_token
        }), 200

    except Exception as e:
        print(f"[REFRESH TOKEN ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to refresh token',
            'error': str(e)
        }), 500