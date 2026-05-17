"""
============================================
AUTHENTICATION MIDDLEWARE
============================================
JWT token validation and role-based access control.
Provides decorators to protect routes and verify
user permissions.
"""

from functools import wraps
from flask import request, jsonify, g
from datetime import datetime

from services.auth_service import AuthService
from models.database import get_supabase, get_admin_supabase


# ============================================
# CONSTANTS
# ============================================
TOKEN_PREFIX = 'Bearer'
TOKEN_HEADER = 'Authorization'


# ============================================
# EXTRACT TOKEN FROM REQUEST
# ============================================
def extract_token():
    """
    Extract JWT token from Authorization header.

    Returns:
        str: Token string or None if not found
    """

    auth_header = request.headers.get(TOKEN_HEADER, '')

    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2:
        return None

    if parts[0] != TOKEN_PREFIX:
        return None

    return parts[1]


# ============================================
# TOKEN REQUIRED DECORATOR
# ============================================
def token_required(f):
    """
    Decorator to protect routes that require authentication.

    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            user_id = g.current_user_id
            return jsonify({'user': g.current_user})

    Returns:
        401 if no token, invalid token, or expired token
        403 if user is inactive
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Extract token
        token = extract_token()

        if not token:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Authentication token is required'
            }), 401

        # Verify token
        try:
            payload = AuthService.verify_token(token)

            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Invalid or expired token'
                }), 401

            user_id = payload.get('user_id')

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Invalid token payload'
                }), 401

            # Check token type
            token_type = payload.get('type', 'user')

            # Get user from database (use admin client to bypass RLS)
            supabase = get_admin_supabase()

            print(f"[DEBUG TOKEN] Looking for user_id: {user_id}")

            response = supabase.table('users').select(
                'id, name, email, age, gender, role, is_active, created_at'
            ).eq('id', str(user_id)).execute()

            print(f"[DEBUG TOKEN] Response data: {response.data}")

            if not response.data or len(response.data) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'User not found'
                }), 401

            user = response.data[0]

            # Check if user is active
            if not user.get('is_active', True):
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'Your account has been deactivated'
                }), 403

            # Store user info in Flask's g object
            g.current_user = user
            g.current_user_id = user_id
            g.current_user_role = user.get('role', 'user')
            g.token_payload = payload

            return f(*args, **kwargs)

        except Exception as e:
            print(f"[AUTH ERROR] {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Token verification failed'
            }), 401

    return decorated_function


# ============================================
# ADMIN REQUIRED DECORATOR
# ============================================
def admin_required(f):
    """
    Decorator to protect routes that require admin access.

    Usage:
        @app.route('/admin/users')
        @admin_required
        def admin_route():
            return jsonify({'admins': []})

    Returns:
        401 if not authenticated
        403 if not an admin
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Extract token
        token = extract_token()

        if not token:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Authentication token is required'
            }), 401

        # Verify token
        try:
            payload = AuthService.verify_token(token)

            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Invalid or expired token'
                }), 401

            user_id = payload.get('user_id')
            token_role = payload.get('role', 'user')

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Invalid token payload'
                }), 401

            # Quick check from token
            if token_role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'Admin access required'
                }), 403

            # Get admin user from database (use admin client to bypass RLS)
            supabase = get_admin_supabase()

            response = supabase.table('users').select(
                'id, name, email, role, is_active, created_at'
            ).eq('id', str(user_id)).execute()

            if not response.data or len(response.data) == 0:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Admin user not found'
                }), 401

            user = response.data[0]

            # Verify admin role from database
            if user.get('role') != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'Admin access required'
                }), 403

            # Check if admin is active
            if not user.get('is_active', True):
                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'Admin account has been deactivated'
                }), 403

            # Store admin info in Flask's g object
            g.current_user = user
            g.current_user_id = user_id
            g.current_user_role = 'admin'
            g.is_admin = True
            g.token_payload = payload

            return f(*args, **kwargs)

        except Exception as e:
            print(f"[ADMIN AUTH ERROR] {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Admin authentication failed'
            }), 401

    return decorated_function


# ============================================
# OPTIONAL AUTH DECORATOR
# ============================================
def optional_auth(f):
    """
    Decorator for routes where authentication is optional.
    If token is provided, user info is loaded.
    If no token, route still works but without user context.

    Usage:
        @app.route('/public-or-private')
        @optional_auth
        def flexible_route():
            if g.current_user:
                return jsonify({'authenticated': True})
            return jsonify({'authenticated': False})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):

        token = extract_token()

        # Initialize defaults
        g.current_user = None
        g.current_user_id = None
        g.current_user_role = None
        g.is_authenticated = False

        if token:
            try:
                payload = AuthService.verify_token(token)

                if payload:
                    user_id = payload.get('user_id')

                    if user_id:
                        # Use admin client to bypass RLS
                        supabase = get_admin_supabase()
                        response = supabase.table('users').select(
                            'id, name, email, age, gender, role, is_active'
                        ).eq('id', str(user_id)).execute()

                        if response.data and len(response.data) > 0:
                            user = response.data[0]

                            if user.get('is_active', True):
                                g.current_user = user
                                g.current_user_id = user_id
                                g.current_user_role = user.get('role', 'user')
                                g.is_authenticated = True
                                g.token_payload = payload

            except Exception as e:
                print(f"[OPTIONAL AUTH WARN] {str(e)}")

        return f(*args, **kwargs)

    return decorated_function


# ============================================
# OWNER OR ADMIN DECORATOR
# ============================================
def owner_or_admin_required(user_id_param='user_id'):
    """
    Decorator for routes where user can access their own data
    OR admin can access any data.

    Usage:
        @app.route('/users/<user_id>/data')
        @owner_or_admin_required('user_id')
        def get_user_data(user_id):
            return jsonify({'data': 'user_data'})
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            token = extract_token()

            if not token:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Authentication required'
                }), 401

            try:
                payload = AuthService.verify_token(token)

                if not payload:
                    return jsonify({
                        'success': False,
                        'error': 'Unauthorized',
                        'message': 'Invalid token'
                    }), 401

                current_user_id = payload.get('user_id')
                current_user_role = payload.get('role', 'user')

                # Get target user_id from URL params
                target_user_id = kwargs.get(user_id_param)

                # Allow if user is admin or accessing own data
                if current_user_role == 'admin':
                    g.current_user_id = current_user_id
                    g.current_user_role = 'admin'
                    g.is_admin = True
                    return f(*args, **kwargs)

                if str(current_user_id) == str(target_user_id):
                    g.current_user_id = current_user_id
                    g.current_user_role = current_user_role
                    return f(*args, **kwargs)

                return jsonify({
                    'success': False,
                    'error': 'Forbidden',
                    'message': 'You can only access your own data'
                }), 403

            except Exception as e:
                print(f"[OWNER AUTH ERROR] {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Authentication failed'
                }), 401

        return decorated_function

    return decorator


# ============================================
# RATE LIMIT BY USER DECORATOR
# ============================================
def rate_limit_by_user(max_requests=10, window_seconds=60):
    """
    Custom rate limiting by user ID instead of IP.

    Usage:
        @app.route('/expensive-operation')
        @token_required
        @rate_limit_by_user(max_requests=5, window_seconds=60)
        def limited_route():
            return jsonify({'data': 'expensive'})
    """

    def decorator(f):
        request_log = {}

        @wraps(f)
        def decorated_function(*args, **kwargs):

            user_id = getattr(g, 'current_user_id', None)

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Authentication required for rate limiting'
                }), 401

            now = datetime.utcnow().timestamp()

            # Clean old entries
            if user_id in request_log:
                request_log[user_id] = [
                    timestamp for timestamp in request_log[user_id]
                    if now - timestamp < window_seconds
                ]
            else:
                request_log[user_id] = []

            # Check rate limit
            if len(request_log[user_id]) >= max_requests:
                return jsonify({
                    'success': False,
                    'error': 'Too Many Requests',
                    'message': f'Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds'
                }), 429

            # Add current request
            request_log[user_id].append(now)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ============================================
# HELPER FUNCTIONS
# ============================================
def get_current_user():
    """
    Get current authenticated user from Flask's g object.

    Returns:
        dict: User object or None
    """
    return getattr(g, 'current_user', None)


def get_current_user_id():
    """
    Get current authenticated user ID from Flask's g object.

    Returns:
        str: User ID or None
    """
    return getattr(g, 'current_user_id', None)


def get_current_user_role():
    """
    Get current authenticated user role from Flask's g object.

    Returns:
        str: User role or None
    """
    return getattr(g, 'current_user_role', None)


def is_authenticated():
    """
    Check if current request is authenticated.

    Returns:
        bool: True if authenticated, False otherwise
    """
    return getattr(g, 'is_authenticated', False) or \
           getattr(g, 'current_user_id', None) is not None


def is_admin():
    """
    Check if current user is admin.

    Returns:
        bool: True if admin, False otherwise
    """
    role = get_current_user_role()
    return role == 'admin'


def get_token_payload():
    """
    Get JWT token payload from Flask's g object.

    Returns:
        dict: Token payload or None
    """
    return getattr(g, 'token_payload', None)


# ============================================
# REQUEST CONTEXT HELPERS
# ============================================
def require_authentication():
    """
    Manual authentication check (without decorator).
    Useful inside route handlers.

    Returns:
        tuple: (is_valid, error_response)
    """
    token = extract_token()

    if not token:
        return False, (jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentication token required'
        }), 401)

    payload = AuthService.verify_token(token)

    if not payload:
        return False, (jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Invalid or expired token'
        }), 401)

    return True, None


def require_admin():
    """
    Manual admin check (without decorator).

    Returns:
        tuple: (is_valid, error_response)
    """
    is_valid, error = require_authentication()

    if not is_valid:
        return False, error

    if not is_admin():
        return False, (jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'Admin access required'
        }), 403)

    return True, None