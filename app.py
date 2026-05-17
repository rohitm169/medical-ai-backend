"""
============================================
MEDAI BACKEND - FLASK MAIN APPLICATION
============================================
Entry point for the Flask application with
chat and web search integration.
"""

import os
import sys
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import config
from config import Config

# Import database
from models.database import init_supabase, get_supabase

# Import blueprints
from routes.auth_routes import auth_bp
from routes.symptom_routes import symptom_bp
from routes.image_routes import image_bp
from routes.doctor_routes import doctor_bp
from routes.admin_routes import admin_bp
from routes.chat_routes import chat_bp


# ============================================
# CREATE FLASK APP
# ============================================
def create_app():
    """Application factory pattern"""

    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Validate required env variables
    validate_environment()

    # Initialize CORS
    setup_cors(app)

    # Initialize rate limiter
    setup_rate_limiter(app)

    # Initialize Supabase
    try:
        init_supabase()
        print("[OK] Supabase initialized successfully")
    except Exception as e:
        print(f"[ERROR] Supabase initialization failed: {e}")
        sys.exit(1)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register health check routes
    register_health_routes(app)

    # Register root route
    register_root_route(app)

    return app


# ============================================
# ENVIRONMENT VALIDATION
# ============================================
def validate_environment():
    """Validate that all required environment variables are set"""

    required_vars = [
        'GEMINI_API_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY',
        'SUPABASE_SERVICE_KEY',
        'JWT_SECRET_KEY'
    ]

    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print("\n" + "=" * 50)
        print("[ERROR] Missing required environment variables:")
        print("=" * 50)
        for var in missing:
            print(f"  - {var}")
        print("\nPlease check your .env file")
        print("=" * 50)
        sys.exit(1)

    print("[OK] All environment variables loaded")


# ============================================
# CORS SETUP
# ============================================
def setup_cors(app):
    """Configure CORS for frontend access"""

    allowed_origins = [
        # Local development
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
        "http://127.0.0.1:5000",

        # Production (Vercel)
        os.getenv('FRONTEND_URL', ''),
    ]

    # Add additional production URLs from env
    extra_origins = os.getenv('ALLOWED_ORIGINS', '')
    if extra_origins:
        allowed_origins.extend(
            [origin.strip() for origin in extra_origins.split(',')]
        )

    # Remove empty strings
    allowed_origins = [origin for origin in allowed_origins if origin]

    CORS(
        app,
        origins=allowed_origins,
        supports_credentials=True,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin"
        ],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        expose_headers=["Content-Type", "Authorization"]
    )

    print(f"[OK] CORS configured for {len(allowed_origins)} origins")


# ============================================
# RATE LIMITER SETUP
# ============================================
def setup_rate_limiter(app):
    """Setup rate limiting to prevent abuse"""

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
    )

    app.limiter = limiter
    print("[OK] Rate limiter configured")


# ============================================
# REGISTER BLUEPRINTS
# ============================================
def register_blueprints(app):
    """Register all route blueprints"""

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(symptom_bp, url_prefix='/api/symptoms')
    app.register_blueprint(image_bp, url_prefix='/api/images')
    app.register_blueprint(doctor_bp, url_prefix='/api/doctors')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')

    print("[OK] All blueprints registered (including chat)")


# ============================================
# ROOT ROUTE
# ============================================
def register_root_route(app):
    """Register the root API info route"""

    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'success': True,
            'app': 'MedAI Backend API',
            'version': '2.0.0',
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'endpoints': {
                'health': '/api/health',
                'auth': '/api/auth/*',
                'symptoms': '/api/symptoms/*',
                'images': '/api/images/*',
                'doctors': '/api/doctors/*',
                'admin': '/api/admin/*',
                'chat': '/api/chat/*'
            },
            'features': [
                'Symptom Analysis',
                'Image Analysis',
                'AI-Powered Diagnosis',
                'Web-Augmented Responses',
                'Chat Conversations',
                'Doctor Recommendations'
            ],
            'documentation': 'https://github.com/your-repo/medical-ai-backend'
        }), 200


# ============================================
# HEALTH CHECK ROUTES
# ============================================
def register_health_routes(app):
    """Register health check endpoints"""

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'success': True,
            'status': 'healthy',
            'service': 'MedAI Backend',
            'timestamp': datetime.utcnow().isoformat()
        }), 200


    @app.route('/api/health/db', methods=['GET'])
    def health_db():
        try:
            supabase = get_supabase()
            response = supabase.table('users').select('id').limit(1).execute()

            return jsonify({
                'success': True,
                'status': 'connected',
                'database': 'Supabase',
                'timestamp': datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503


    @app.route('/api/health/ai', methods=['GET'])
    def health_ai():
        try:
            import google.generativeai as genai
            api_key = os.getenv('GEMINI_API_KEY')

            if not api_key:
                raise Exception('Gemini API key not found')

            genai.configure(api_key=api_key)

            return jsonify({
                'success': True,
                'status': 'configured',
                'service': 'Gemini AI',
                'timestamp': datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503


    @app.route('/api/health/storage', methods=['GET'])
    def health_storage():
        try:
            supabase = get_supabase()
            buckets = supabase.storage.list_buckets()

            return jsonify({
                'success': True,
                'status': 'connected',
                'service': 'Supabase Storage',
                'buckets_count': len(buckets) if buckets else 0,
                'timestamp': datetime.utcnow().isoformat()
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503


    @app.route('/api/health/search', methods=['GET'])
    def health_search():
        """Health check for web search service"""
        try:
            from services.web_search_service import WebSearchService
            result = WebSearchService.health_check()

            status_code = 200 if result.get('success') else 503

            return jsonify({
                'success': result.get('success', False),
                'status': result.get('status', 'unknown'),
                'service': 'Web Search (DuckDuckGo)',
                'details': result,
                'timestamp': datetime.utcnow().isoformat()
            }), status_code

        except Exception as e:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503


# ============================================
# ERROR HANDLERS
# ============================================
def register_error_handlers(app):
    """Register all error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'The request was invalid or malformed',
            'status_code': 400
        }), 400


    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'status_code': 401
        }), 401


    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource',
            'status_code': 403
        }), 403


    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': f'The requested URL {request.path} was not found',
            'status_code': 404
        }), 404


    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method Not Allowed',
            'message': f'The method {request.method} is not allowed for this endpoint',
            'status_code': 405
        }), 405


    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({
            'success': False,
            'error': 'Payload Too Large',
            'message': 'The uploaded file is too large. Maximum size is 5MB',
            'status_code': 413
        }), 413


    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later',
            'status_code': 429
        }), 429


    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later',
            'status_code': 500
        }), 500


    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            'success': False,
            'error': 'Service Unavailable',
            'message': 'The service is temporarily unavailable',
            'status_code': 503
        }), 503


    @app.errorhandler(Exception)
    def handle_exception(error):
        if hasattr(error, 'code'):
            return jsonify({
                'success': False,
                'error': error.__class__.__name__,
                'message': str(error),
                'status_code': error.code
            }), error.code

        print(f"[ERROR] Unhandled exception: {error}")

        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500


# ============================================
# REQUEST LOGGING
# ============================================
def log_request_info(app):
    """Log request information for debugging"""

    @app.before_request
    def log_request():
        if app.config.get('DEBUG'):
            print(f"[{request.method}] {request.path}")


# ============================================
# CREATE APP INSTANCE
# ============================================
app = create_app()


# ============================================
# RUN APP (Local Development)
# ============================================
if __name__ == '__main__':

    print("\n" + "=" * 50)
    print("MEDAI BACKEND SERVER v2.0")
    print("=" * 50)
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Debug Mode: {os.getenv('FLASK_DEBUG', 'False')}")
    print(f"Server: http://localhost:5000")
    print(f"Health: http://localhost:5000/api/health")
    print(f"Chat API: http://localhost:5000/api/chat")
    print("=" * 50 + "\n")

    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )