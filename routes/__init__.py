"""
============================================
ROUTES PACKAGE
============================================
This package contains all API route blueprints
for the MedAI application.

API Endpoints Structure:
- /api/auth/*       -> Authentication routes
- /api/symptoms/*   -> Symptom analysis routes
- /api/images/*     -> Image upload and analysis routes
- /api/doctors/*    -> Doctor information routes
- /api/admin/*      -> Admin panel routes
"""

from routes.auth_routes import auth_bp
from routes.symptom_routes import symptom_bp
from routes.image_routes import image_bp
from routes.doctor_routes import doctor_bp
from routes.admin_routes import admin_bp


# ============================================
# PACKAGE METADATA
# ============================================
__version__ = '1.0.0'
__author__ = 'MedAI Team'
__description__ = 'API route blueprints for MedAI backend'


# ============================================
# BLUEPRINT REGISTRY
# ============================================
BLUEPRINTS = {
    'auth': {
        'blueprint': auth_bp,
        'url_prefix': '/api/auth',
        'description': 'User authentication and authorization'
    },
    'symptoms': {
        'blueprint': symptom_bp,
        'url_prefix': '/api/symptoms',
        'description': 'Symptom analysis and history'
    },
    'images': {
        'blueprint': image_bp,
        'url_prefix': '/api/images',
        'description': 'Medical image upload and analysis'
    },
    'doctors': {
        'blueprint': doctor_bp,
        'url_prefix': '/api/doctors',
        'description': 'Doctor information and search'
    },
    'admin': {
        'blueprint': admin_bp,
        'url_prefix': '/api/admin',
        'description': 'Admin panel operations'
    }
}


# ============================================
# API ENDPOINT DOCUMENTATION
# ============================================
API_ENDPOINTS = {
    'auth': [
        'POST   /api/auth/register',
        'POST   /api/auth/login',
        'POST   /api/auth/admin-login',
        'POST   /api/auth/logout',
        'GET    /api/auth/me',
        'PUT    /api/auth/profile',
        'POST   /api/auth/change-password',
        'DELETE /api/auth/delete-account'
    ],
    'symptoms': [
        'POST   /api/symptoms/analyze',
        'GET    /api/symptoms/history',
        'GET    /api/symptoms/history/<id>',
        'DELETE /api/symptoms/history/<id>'
    ],
    'images': [
        'POST   /api/images/upload',
        'POST   /api/images/upload-base64',
        'POST   /api/images/analyze',
        'DELETE /api/images/<id>'
    ],
    'doctors': [
        'GET    /api/doctors',
        'GET    /api/doctors/<id>',
        'GET    /api/doctors/specialty/<specialty>'
    ],
    'admin': [
        'GET    /api/admin/stats',
        'GET    /api/admin/users',
        'GET    /api/admin/users/<id>',
        'PUT    /api/admin/users/<id>',
        'DELETE /api/admin/users/<id>',
        'GET    /api/admin/users/<id>/history',
        'GET    /api/admin/doctors',
        'POST   /api/admin/doctors',
        'PUT    /api/admin/doctors/<id>',
        'DELETE /api/admin/doctors/<id>',
        'GET    /api/admin/diagnoses',
        'GET    /api/admin/activity'
    ]
}


# ============================================
# EXPORTED ITEMS
# ============================================
__all__ = [
    'auth_bp',
    'symptom_bp',
    'image_bp',
    'doctor_bp',
    'admin_bp',
    'BLUEPRINTS',
    'API_ENDPOINTS'
]