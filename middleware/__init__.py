"""
============================================
MIDDLEWARE PACKAGE
============================================
This package contains middleware functions for
request processing, authentication checks, and
authorization decorators.

Middleware Components:
- auth_middleware: JWT token validation and role-based access control
"""

from middleware.auth_middleware import (
    token_required,
    admin_required,
    optional_auth,
    get_current_user,
    get_current_user_id,
    get_current_user_role
)


# ============================================
# PACKAGE METADATA
# ============================================
__version__ = '1.0.0'
__author__ = 'MedAI Team'
__description__ = 'Authentication and authorization middleware'


# ============================================
# EXPORTED FUNCTIONS
# ============================================
__all__ = [
    'token_required',
    'admin_required',
    'optional_auth',
    'get_current_user',
    'get_current_user_id',
    'get_current_user_role'
]