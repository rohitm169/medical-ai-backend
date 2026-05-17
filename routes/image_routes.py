"""
============================================
IMAGE ROUTES
============================================
Endpoints for medical image upload, analysis,
and management. Handles file uploads, base64
images, and Gemini Vision AI analysis.
"""

import os
import base64
import uuid
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from werkzeug.utils import secure_filename

from models.database import StorageDB, get_admin_supabase
from middleware.auth_middleware import token_required, optional_auth
from services.image_analysis import ImageAnalyzer
from services.gemini_service import GeminiService


# ============================================
# CREATE BLUEPRINT
# ============================================
image_bp = Blueprint('images', __name__)


# ============================================
# CONSTANTS
# ============================================
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp'
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
VALID_IMAGE_TYPES = ['skin', 'eye', 'throat', 'other']


# ============================================
# HELPER FUNCTIONS
# ============================================
def is_allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def is_allowed_mime(mime_type):
    """Check if MIME type is allowed"""
    return mime_type in ALLOWED_MIME_TYPES


def is_valid_image_type(image_type):
    """Validate medical image type"""
    return image_type in VALID_IMAGE_TYPES


def generate_unique_filename(user_id, original_filename, image_type='other'):
    """Generate unique filename for storage"""
    extension = 'jpg'

    if original_filename and '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1].lower()
        if extension not in ALLOWED_EXTENSIONS:
            extension = 'jpg'

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]

    user_part = str(user_id)[:8] if user_id else 'anonymous'

    filename = f"{image_type}/{user_part}_{timestamp}_{unique_id}.{extension}"

    return filename


def get_mime_from_extension(filename):
    """Get MIME type from filename extension"""
    if not filename or '.' not in filename:
        return 'image/jpeg'

    extension = filename.rsplit('.', 1)[1].lower()

    mime_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp'
    }

    return mime_map.get(extension, 'image/jpeg')


def decode_base64_image(base64_string):
    """Decode base64 string to bytes"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]

        # Decode
        image_bytes = base64.b64decode(base64_string)
        return image_bytes

    except Exception as e:
        print(f"[BASE64 DECODE ERROR] {str(e)}")
        return None


# ============================================
# UPLOAD IMAGE (Multipart Form)
# ============================================
@image_bp.route('/upload', methods=['POST'])
@token_required
def upload_image():
    """
    Upload a medical image via multipart form data.

    Form Data:
        image: Image file
        image_type: Type of image (skin, eye, throat, other)

    Returns:
        201: Upload successful with URL
        400: Validation error
        413: File too large
        500: Server error
    """

    try:
        # Check if file is in request
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No image file provided'
            }), 400

        file = request.files['image']

        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400

        # Validate filename
        if not is_allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': 'Invalid file type. Only JPG, PNG, and WEBP are allowed'
            }), 400

        # Validate MIME type
        if not is_allowed_mime(file.mimetype):
            return jsonify({
                'success': False,
                'message': f'Invalid MIME type: {file.mimetype}'
            }), 400

        # Get image type
        image_type = request.form.get('image_type', 'other').strip().lower()

        if not is_valid_image_type(image_type):
            image_type = 'other'

        # Read file data
        file_data = file.read()
        file_size = len(file_data)

        # Validate file size
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB'
            }), 413

        if file_size == 0:
            return jsonify({
                'success': False,
                'message': 'File is empty'
            }), 400

        # Process image (resize, optimize)
        processed_data = ImageAnalyzer.process_image(file_data)

        if not processed_data:
            return jsonify({
                'success': False,
                'message': 'Failed to process image'
            }), 500

        # Generate unique filename
        user_id = g.current_user_id
        filename = generate_unique_filename(
            user_id,
            file.filename,
            image_type
        )

        # Get content type
        content_type = file.mimetype or get_mime_from_extension(file.filename)

        # Upload to Supabase Storage
        upload_url = StorageDB.upload_image(
            file_path=filename,
            file_data=processed_data,
            content_type=content_type
        )

        if not upload_url:
            return jsonify({
                'success': False,
                'message': 'Failed to upload image to storage'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'image': {
                'url': upload_url,
                'filename': filename,
                'image_type': image_type,
                'size': file_size,
                'content_type': content_type,
                'uploaded_at': datetime.utcnow().isoformat()
            }
        }), 201

    except Exception as e:
        print(f"[UPLOAD IMAGE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to upload image',
            'error': str(e)
        }), 500


# ============================================
# UPLOAD IMAGE (Base64)
# ============================================
@image_bp.route('/upload-base64', methods=['POST'])
@token_required
def upload_image_base64():
    """
    Upload a medical image via base64 string.

    Request Body:
    {
        "image_data": "base64_encoded_string",
        "image_type": "skin",
        "mime_type": "image/jpeg"
    }

    Returns:
        201: Upload successful
        400: Validation error
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        image_data = data.get('image_data', '')
        image_type = data.get('image_type', 'other').strip().lower()
        mime_type = data.get('mime_type', 'image/jpeg').strip().lower()

        # Validate input
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Image data is required'
            }), 400

        if not is_valid_image_type(image_type):
            image_type = 'other'

        if not is_allowed_mime(mime_type):
            mime_type = 'image/jpeg'

        # Decode base64
        image_bytes = decode_base64_image(image_data)

        if not image_bytes:
            return jsonify({
                'success': False,
                'message': 'Invalid base64 image data'
            }), 400

        # Validate size
        file_size = len(image_bytes)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'Image too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB'
            }), 413

        if file_size == 0:
            return jsonify({
                'success': False,
                'message': 'Image data is empty'
            }), 400

        # Process image
        processed_data = ImageAnalyzer.process_image(image_bytes)

        if not processed_data:
            return jsonify({
                'success': False,
                'message': 'Failed to process image'
            }), 500

        # Generate filename
        user_id = g.current_user_id
        extension = mime_type.split('/')[-1].replace('jpeg', 'jpg')
        original_filename = f"image.{extension}"
        filename = generate_unique_filename(
            user_id,
            original_filename,
            image_type
        )

        # Upload to storage
        upload_url = StorageDB.upload_image(
            file_path=filename,
            file_data=processed_data,
            content_type=mime_type
        )

        if not upload_url:
            return jsonify({
                'success': False,
                'message': 'Failed to upload image'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'image': {
                'url': upload_url,
                'filename': filename,
                'image_type': image_type,
                'size': file_size,
                'content_type': mime_type,
                'uploaded_at': datetime.utcnow().isoformat()
            }
        }), 201

    except Exception as e:
        print(f"[UPLOAD BASE64 ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to upload image',
            'error': str(e)
        }), 500


# ============================================
# ANALYZE IMAGE
# ============================================
@image_bp.route('/analyze', methods=['POST'])
@token_required
def analyze_image():
    """
    Analyze a medical image using Gemini Vision AI.

    Request Body:
    {
        "image_data": "base64_string",
        "image_type": "skin",
        "symptoms_context": "Optional text describing symptoms"
    }

    Returns:
        200: Analysis result
        400: Validation error
        500: Analysis failed
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        image_data = data.get('image_data', '')
        image_type = data.get('image_type', 'other').strip().lower()
        symptoms_context = data.get('symptoms_context', '').strip()

        # Validate input
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Image data is required'
            }), 400

        if not is_valid_image_type(image_type):
            image_type = 'other'

        # Decode base64
        image_bytes = decode_base64_image(image_data)

        if not image_bytes:
            return jsonify({
                'success': False,
                'message': 'Invalid image data'
            }), 400

        # Validate size
        if len(image_bytes) > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': 'Image too large for analysis'
            }), 413

        # Get image dimensions and validate
        is_valid, validation_msg = ImageAnalyzer.validate_image(image_bytes)

        if not is_valid:
            return jsonify({
                'success': False,
                'message': f'Invalid image: {validation_msg}'
            }), 400

        # Call Gemini Vision API
        analysis_result = GeminiService.analyze_image(
            image_bytes=image_bytes,
            image_type=image_type,
            symptoms_context=symptoms_context
        )

        if not analysis_result or not analysis_result.get('success'):
            return jsonify({
                'success': False,
                'message': 'Image analysis failed',
                'error': analysis_result.get('error') if analysis_result else 'Unknown error'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Image analyzed successfully',
            'analysis': analysis_result.get('data', {}),
            'image_type': image_type,
            'analyzed_at': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        print(f"[ANALYZE IMAGE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to analyze image',
            'error': str(e)
        }), 500


# ============================================
# DELETE IMAGE
# ============================================
@image_bp.route('/<path:filename>', methods=['DELETE'])
@token_required
def delete_image(filename):
    """
    Delete an uploaded image from storage.

    URL Params:
        filename: Path/name of file in storage

    Returns:
        200: Image deleted
        404: Image not found
        500: Server error
    """

    try:
        if not filename:
            return jsonify({
                'success': False,
                'message': 'Filename is required'
            }), 400

        # Verify user owns this image (basic check)
        user_id = str(g.current_user_id)[:8]

        if user_id not in filename and g.current_user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'You can only delete your own images'
            }), 403

        # Delete from storage
        success = StorageDB.delete_image(filename)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete image'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Image deleted successfully'
        }), 200

    except Exception as e:
        print(f"[DELETE IMAGE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete image',
            'error': str(e)
        }), 500


# ============================================
# GET SIGNED URL FOR PRIVATE IMAGE
# ============================================
@image_bp.route('/signed-url', methods=['POST'])
@token_required
def get_signed_url():
    """
    Get a signed URL for accessing a private image.

    Request Body:
    {
        "filename": "path/to/image.jpg",
        "expires_in": 3600
    }

    Returns:
        200: Signed URL
        400: Validation error
        500: Server error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        filename = data.get('filename', '').strip()

        if not filename:
            return jsonify({
                'success': False,
                'message': 'Filename is required'
            }), 400

        try:
            expires_in = int(data.get('expires_in', 3600))
            if expires_in < 60 or expires_in > 86400:
                expires_in = 3600
        except (ValueError, TypeError):
            expires_in = 3600

        # Generate signed URL
        signed_url = StorageDB.get_signed_url(filename, expires_in)

        if not signed_url:
            return jsonify({
                'success': False,
                'message': 'Failed to generate signed URL'
            }), 500

        return jsonify({
            'success': True,
            'signed_url': signed_url,
            'expires_in_seconds': expires_in,
            'filename': filename
        }), 200

    except Exception as e:
        print(f"[SIGNED URL ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to generate signed URL',
            'error': str(e)
        }), 500


# ============================================
# VALIDATE IMAGE
# ============================================
@image_bp.route('/validate', methods=['POST'])
@optional_auth
def validate_image_endpoint():
    """
    Validate an image without uploading it.
    Useful for client-side validation feedback.

    Request Body:
    {
        "image_data": "base64_string",
        "mime_type": "image/jpeg"
    }

    Returns:
        200: Validation result
        400: Invalid image
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        image_data = data.get('image_data', '')
        mime_type = data.get('mime_type', '').lower()

        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Image data is required'
            }), 400

        # Validate MIME type
        if mime_type and not is_allowed_mime(mime_type):
            return jsonify({
                'success': False,
                'message': f'Invalid MIME type: {mime_type}',
                'allowed_types': list(ALLOWED_MIME_TYPES)
            }), 400

        # Decode and validate
        image_bytes = decode_base64_image(image_data)

        if not image_bytes:
            return jsonify({
                'success': False,
                'message': 'Invalid base64 data'
            }), 400

        file_size = len(image_bytes)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'File too large: {file_size} bytes. Max: {MAX_FILE_SIZE} bytes',
                'size_bytes': file_size,
                'max_size_bytes': MAX_FILE_SIZE
            }), 413

        # Validate image content
        is_valid, validation_msg = ImageAnalyzer.validate_image(image_bytes)

        if not is_valid:
            return jsonify({
                'success': False,
                'message': validation_msg
            }), 400

        # Get image info
        image_info = ImageAnalyzer.get_image_info(image_bytes)

        return jsonify({
            'success': True,
            'message': 'Image is valid',
            'image_info': image_info,
            'size_bytes': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2)
        }), 200

    except Exception as e:
        print(f"[VALIDATE IMAGE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to validate image',
            'error': str(e)
        }), 500


# ============================================
# GET ALLOWED IMAGE TYPES
# ============================================
@image_bp.route('/allowed-types', methods=['GET'])
def get_allowed_types():
    """
    Get list of allowed image types and constraints.

    Returns:
        200: Allowed types and constraints
    """

    try:
        return jsonify({
            'success': True,
            'allowed_extensions': list(ALLOWED_EXTENSIONS),
            'allowed_mime_types': list(ALLOWED_MIME_TYPES),
            'medical_image_types': VALID_IMAGE_TYPES,
            'max_file_size_bytes': MAX_FILE_SIZE,
            'max_file_size_mb': MAX_FILE_SIZE // (1024 * 1024),
            'recommendations': {
                'optimal_resolution': '1024x1024 or smaller',
                'optimal_format': 'JPEG or PNG',
                'tips': [
                    'Use good lighting',
                    'Focus on affected area',
                    'Avoid blurry images',
                    'Use neutral background'
                ]
            }
        }), 200

    except Exception as e:
        print(f"[ALLOWED TYPES ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch allowed types',
            'error': str(e)
        }), 500


# ============================================
# BATCH UPLOAD IMAGES
# ============================================
@image_bp.route('/upload-batch', methods=['POST'])
@token_required
def upload_batch():
    """
    Upload multiple images at once.

    Request Body:
    {
        "images": [
            {
                "image_data": "base64",
                "image_type": "skin",
                "mime_type": "image/jpeg"
            },
            ...
        ]
    }

    Returns:
        200: Batch upload results
        400: Validation error
    """

    try:
        data = request.get_json()

        if not data or 'images' not in data:
            return jsonify({
                'success': False,
                'message': 'Images array is required'
            }), 400

        images = data.get('images', [])

        if not isinstance(images, list) or len(images) == 0:
            return jsonify({
                'success': False,
                'message': 'At least one image is required'
            }), 400

        if len(images) > 5:
            return jsonify({
                'success': False,
                'message': 'Maximum 5 images per batch'
            }), 400

        user_id = g.current_user_id
        results = []

        for index, img in enumerate(images):
            try:
                image_data = img.get('image_data', '')
                image_type = img.get('image_type', 'other').strip().lower()
                mime_type = img.get('mime_type', 'image/jpeg').strip().lower()

                if not image_data:
                    results.append({
                        'index': index,
                        'success': False,
                        'message': 'Image data missing'
                    })
                    continue

                if not is_valid_image_type(image_type):
                    image_type = 'other'

                # Decode
                image_bytes = decode_base64_image(image_data)

                if not image_bytes:
                    results.append({
                        'index': index,
                        'success': False,
                        'message': 'Invalid base64 data'
                    })
                    continue

                # Process
                processed = ImageAnalyzer.process_image(image_bytes)

                if not processed:
                    results.append({
                        'index': index,
                        'success': False,
                        'message': 'Image processing failed'
                    })
                    continue

                # Upload
                extension = mime_type.split('/')[-1].replace('jpeg', 'jpg')
                filename = generate_unique_filename(
                    user_id,
                    f"image.{extension}",
                    image_type
                )

                url = StorageDB.upload_image(
                    file_path=filename,
                    file_data=processed,
                    content_type=mime_type
                )

                if url:
                    results.append({
                        'index': index,
                        'success': True,
                        'url': url,
                        'filename': filename,
                        'image_type': image_type
                    })
                else:
                    results.append({
                        'index': index,
                        'success': False,
                        'message': 'Upload failed'
                    })

            except Exception as e:
                results.append({
                    'index': index,
                    'success': False,
                    'message': str(e)
                })

        successful = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'message': f'Uploaded {successful} of {len(images)} images',
            'total': len(images),
            'successful': successful,
            'failed': len(images) - successful,
            'results': results
        }), 200

    except Exception as e:
        print(f"[BATCH UPLOAD ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Batch upload failed',
            'error': str(e)
        }), 500