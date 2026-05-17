"""
============================================
SERVICES PACKAGE
============================================
This package contains business logic services
for the MedAI application.

Services:
- auth_service: Authentication and password management
- gemini_service: Gemini AI integration for symptom analysis
- image_analysis: Image processing and validation
- severity_engine: Severity calculation and classification
"""

from services.auth_service import AuthService
from services.gemini_service import GeminiService
from services.image_analysis import ImageAnalyzer
from services.severity_engine import SeverityEngine


# ============================================
# PACKAGE METADATA
# ============================================
__version__ = '1.0.0'
__author__ = 'MedAI Team'
__description__ = 'Business logic services for MedAI backend'


# ============================================
# SERVICE REGISTRY
# ============================================
SERVICES = {
    'auth': {
        'name': 'Authentication Service',
        'class': AuthService,
        'description': 'Password hashing and JWT token management'
    },
    'gemini': {
        'name': 'Gemini AI Service',
        'class': GeminiService,
        'description': 'AI-powered symptom and image analysis'
    },
    'image': {
        'name': 'Image Analysis Service',
        'class': ImageAnalyzer,
        'description': 'Image processing and validation'
    },
    'severity': {
        'name': 'Severity Engine',
        'class': SeverityEngine,
        'description': 'Symptom severity calculation'
    }
}


# ============================================
# SERVICE CAPABILITIES
# ============================================
SERVICE_CAPABILITIES = {
    'auth_service': [
        'hash_password',
        'verify_password',
        'generate_token',
        'verify_token',
        'decode_token'
    ],
    'gemini_service': [
        'analyze_symptoms',
        'analyze_image',
        'analyze_symptoms_with_images',
        'build_prompt',
        'parse_response'
    ],
    'image_analysis': [
        'process_image',
        'validate_image',
        'resize_image',
        'compress_image',
        'get_image_info'
    ],
    'severity_engine': [
        'calculate_severity',
        'check_emergency_keywords',
        'get_urgency_level',
        'apply_age_factor',
        'get_severity_action'
    ]
}


# ============================================
# EXPORTED ITEMS
# ============================================
__all__ = [
    'AuthService',
    'GeminiService',
    'ImageAnalyzer',
    'SeverityEngine',
    'SERVICES',
    'SERVICE_CAPABILITIES'
]