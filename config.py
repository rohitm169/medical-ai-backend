"""
============================================
CONFIGURATION FILE
============================================
Loads all environment variables and provides
configuration settings for the entire application.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================
# BASE CONFIGURATION CLASS
# ============================================
class Config:
    """Base configuration class with all settings"""

    # ============================================
    # APPLICATION SETTINGS
    # ============================================
    APP_NAME = 'MedAI Backend API'
    APP_VERSION = '1.0.0'
    APP_DESCRIPTION = 'AI-Powered Medical Symptom Analysis'

    # ============================================
    # FLASK SETTINGS
    # ============================================
    SECRET_KEY = os.getenv(
        'FLASK_SECRET_KEY',
        'medai_flask_secret_change_in_production'
    )

    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    ENV = os.getenv('FLASK_ENV', 'production')

    # JSON Settings
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True

    # ============================================
    # SERVER SETTINGS
    # ============================================
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    # ============================================
    # SUPABASE DATABASE
    # ============================================
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')
    SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET', 'medical-images')

    # ============================================
    # GEMINI AI API
    # ============================================
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL_TEXT = os.getenv('GEMINI_MODEL_TEXT', 'gemini-1.5-flash')
    GEMINI_MODEL_VISION = os.getenv('GEMINI_MODEL_VISION', 'gemini-1.5-flash')
    GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.7'))
    GEMINI_MAX_TOKENS = int(os.getenv('GEMINI_MAX_TOKENS', '2048'))
    GEMINI_TIMEOUT = int(os.getenv('GEMINI_TIMEOUT', '60'))

    # ============================================
    # JWT AUTHENTICATION
    # ============================================
    JWT_SECRET_KEY = os.getenv(
        'JWT_SECRET_KEY',
        'medai_jwt_secret_change_in_production'
    )
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_ADMIN_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Token settings
    TOKEN_TYPE = 'Bearer'
    TOKEN_HEADER = 'Authorization'

    # ============================================
    # PASSWORD SETTINGS
    # ============================================
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_MAX_LENGTH = 128
    BCRYPT_ROUNDS = 12

    # ============================================
    # CORS SETTINGS
    # ============================================
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5500')
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

    # ============================================
    # FILE UPLOAD SETTINGS
    # ============================================
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB total request size
    MAX_IMAGE_SIZE = 5 * 1024 * 1024        # 5 MB per image
    MAX_IMAGES_PER_REQUEST = 3

    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    ALLOWED_IMAGE_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp'
    }

    # Image processing
    IMAGE_MAX_WIDTH = 1024
    IMAGE_MAX_HEIGHT = 1024
    IMAGE_QUALITY = 85

    # ============================================
    # IMAGE TYPES (for medical analysis)
    # ============================================
    VALID_IMAGE_TYPES = ['skin', 'eye', 'throat', 'other']

    # ============================================
    # SYMPTOM ANALYSIS SETTINGS
    # ============================================
    MIN_SYMPTOM_LENGTH = 10
    MAX_SYMPTOM_LENGTH = 2000
    MAX_NOTES_LENGTH = 500

    # ============================================
    # SEVERITY LEVELS
    # ============================================
    SEVERITY_LEVELS = ['Low', 'Medium', 'High', 'Critical']

    SEVERITY_COLORS = {
        'Low': '#10b981',
        'Medium': '#f59e0b',
        'High': '#ef4444',
        'Critical': '#dc2626'
    }

    # ============================================
    # EMERGENCY KEYWORDS
    # ============================================
    EMERGENCY_KEYWORDS = [
        'chest pain',
        'heart attack',
        'cannot breathe',
        "can't breathe",
        'difficulty breathing',
        'severe bleeding',
        'unconscious',
        'stroke',
        'seizure',
        'overdose',
        'suicidal',
        'severe head injury',
        'anaphylaxis',
        'anaphylactic',
        'paralysis',
        'severe burn',
        'choking',
        'poisoning'
    ]

    # ============================================
    # USER ROLES
    # ============================================
    ROLES = ['user', 'admin']
    DEFAULT_ROLE = 'user'

    # ============================================
    # GENDER OPTIONS
    # ============================================
    GENDER_OPTIONS = ['male', 'female', 'other']

    # ============================================
    # AGE LIMITS
    # ============================================
    MIN_AGE = 1
    MAX_AGE = 120

    # ============================================
    # PAGINATION
    # ============================================
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    # ============================================
    # RATE LIMITING
    # ============================================
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    # Specific endpoint limits
    AUTH_RATE_LIMIT = "10 per minute"
    ANALYZE_RATE_LIMIT = "20 per hour"
    UPLOAD_RATE_LIMIT = "30 per hour"

    # ============================================
    # DOCTOR SPECIALTIES
    # ============================================
    SPECIALTIES = [
        'General Physician',
        'Dermatologist',
        'Ophthalmologist',
        'ENT Specialist',
        'Neurologist',
        'Cardiologist',
        'Orthopedist',
        'Gastroenterologist',
        'Pulmonologist',
        'Psychiatrist',
        'Pediatrician',
        'Gynecologist'
    ]

    # ============================================
    # LOCATIONS
    # ============================================
    LOCATIONS = [
        'Dhaka',
        'Chittagong',
        'Sylhet',
        'Rajshahi',
        'Khulna',
        'Barisal',
        'Rangpur',
        'Mymensingh'
    ]

    # ============================================
    # GEMINI PROMPTS CONFIG
    # ============================================
    GEMINI_SYSTEM_PROMPT = """You are a medical AI assistant.
Your role is to analyze symptoms and provide educational information
about possible health conditions. You are NOT a doctor and your responses
are NOT medical diagnoses. Always recommend consulting a healthcare
professional. Be helpful, accurate, and safety-focused."""

    GEMINI_SAFETY_NOTICE = """IMPORTANT: This analysis is for educational
purposes only and does not replace professional medical advice."""

    # ============================================
    # API RESPONSE MESSAGES
    # ============================================
    MESSAGES = {
        'success': 'Operation completed successfully',
        'error': 'An error occurred',
        'unauthorized': 'Authentication required',
        'forbidden': 'Access denied',
        'not_found': 'Resource not found',
        'invalid_input': 'Invalid input provided',
        'server_error': 'Internal server error',

        # Auth messages
        'register_success': 'Account created successfully',
        'login_success': 'Login successful',
        'logout_success': 'Logout successful',
        'invalid_credentials': 'Invalid email or password',
        'user_exists': 'User with this email already exists',
        'user_not_found': 'User not found',
        'invalid_token': 'Invalid or expired token',
        'token_required': 'Authentication token is required',
        'admin_required': 'Admin access required',
        'inactive_account': 'Your account has been deactivated',

        # Profile messages
        'profile_updated': 'Profile updated successfully',
        'password_changed': 'Password changed successfully',
        'password_incorrect': 'Current password is incorrect',
        'account_deleted': 'Account deleted successfully',

        # Symptom messages
        'analysis_success': 'Symptom analysis completed',
        'analysis_failed': 'Failed to analyze symptoms',
        'symptoms_required': 'Please provide symptoms description',
        'history_loaded': 'History loaded successfully',

        # Image messages
        'image_uploaded': 'Image uploaded successfully',
        'image_too_large': 'Image size exceeds maximum limit',
        'image_invalid_type': 'Invalid image file type',
        'image_required': 'Image file is required',

        # Doctor messages
        'doctor_added': 'Doctor added successfully',
        'doctor_updated': 'Doctor information updated',
        'doctor_deleted': 'Doctor deleted successfully',
        'doctor_not_found': 'Doctor not found',
    }

    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    # ============================================
    # SESSION SETTINGS
    # ============================================
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)


# ============================================
# DEVELOPMENT CONFIGURATION
# ============================================
class DevelopmentConfig(Config):
    """Development environment configuration"""

    DEBUG = True
    TESTING = False
    ENV = 'development'

    # Less restrictive in dev
    SESSION_COOKIE_SECURE = False
    BCRYPT_ROUNDS = 4  # Faster hashing in dev


# ============================================
# PRODUCTION CONFIGURATION
# ============================================
class ProductionConfig(Config):
    """Production environment configuration"""

    DEBUG = False
    TESTING = False
    ENV = 'production'

    # Strict security in production
    SESSION_COOKIE_SECURE = True
    BCRYPT_ROUNDS = 12

    # Stricter rate limits
    AUTH_RATE_LIMIT = "5 per minute"
    ANALYZE_RATE_LIMIT = "10 per hour"


# ============================================
# TESTING CONFIGURATION
# ============================================
class TestingConfig(Config):
    """Testing environment configuration"""

    DEBUG = True
    TESTING = True
    ENV = 'testing'

    # Use test database
    SUPABASE_URL = os.getenv('TEST_SUPABASE_URL', '')

    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False


# ============================================
# CONFIGURATION SELECTOR
# ============================================
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)


# ============================================
# CONFIG VALIDATION
# ============================================
def validate_config():
    """Validate that critical configuration is set"""

    config = get_config()

    errors = []

    if not config.SUPABASE_URL:
        errors.append('SUPABASE_URL is not set')

    if not config.SUPABASE_KEY:
        errors.append('SUPABASE_KEY is not set')

    if not config.GEMINI_API_KEY:
        errors.append('GEMINI_API_KEY is not set')

    if not config.JWT_SECRET_KEY or config.JWT_SECRET_KEY == 'medai_jwt_secret_change_in_production':
        errors.append('JWT_SECRET_KEY is not set or using default value')

    if errors:
        return False, errors

    return True, []


# ============================================
# EXPORT DEFAULT
# ============================================
Config = get_config()