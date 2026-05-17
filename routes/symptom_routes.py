"""
============================================
SYMPTOM ROUTES
============================================
Endpoints for symptom analysis using Gemini AI,
managing symptom history, and viewing diagnoses.
"""

import base64
import uuid
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from models.database import (
    SymptomDB,
    DiagnosisDB,
    DoctorDB,
    StorageDB,
    get_admin_supabase
)
from middleware.auth_middleware import token_required
from services.gemini_service import GeminiService
from services.severity_engine import SeverityEngine
from services.image_analysis import ImageAnalyzer


# ============================================
# CREATE BLUEPRINT
# ============================================
symptom_bp = Blueprint('symptoms', __name__)


# ============================================
# CONSTANTS
# ============================================
MIN_SYMPTOM_LENGTH = 10
MAX_SYMPTOM_LENGTH = 2000
MAX_NOTES_LENGTH = 500
MAX_IMAGES = 3
DEFAULT_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 50
VALID_LANGUAGES = ['en', 'hi', 'bn', 'hinglish', 'benglish', 'auto']


# ============================================
# VALIDATION HELPERS
# ============================================
def validate_symptom_input(data):
    """
    Validate symptom analysis input data.

    Returns:
        tuple: (is_valid, error_message)
    """

    if not data:
        return False, 'Request body is required'

    symptoms_text = data.get('symptoms_text', '').strip()
    images = data.get('images', [])

    has_text = symptoms_text and len(symptoms_text) >= MIN_SYMPTOM_LENGTH
    has_images = isinstance(images, list) and len(images) > 0

    if not has_text and not has_images:
        return False, 'Symptoms description or images required'

    if has_text and len(symptoms_text) > MAX_SYMPTOM_LENGTH:
        return False, f'Symptoms text exceeds {MAX_SYMPTOM_LENGTH} characters'

    if has_images and len(images) > MAX_IMAGES:
        return False, f'Maximum {MAX_IMAGES} images allowed'

    notes = data.get('additional_notes', '')
    if notes and len(notes) > MAX_NOTES_LENGTH:
        return False, f'Notes exceed {MAX_NOTES_LENGTH} characters'

    age = data.get('age')
    if age is not None:
        try:
            age = int(age)
            if age < 1 or age > 120:
                return False, 'Age must be between 1 and 120'
        except (ValueError, TypeError):
            return False, 'Invalid age value'

    gender = data.get('gender', '').strip().lower() if data.get('gender') else None
    if gender and gender not in ['male', 'female', 'other']:
        return False, 'Gender must be male, female, or other'

    return True, None


def upload_images_to_storage(images, user_id):
    """
    Upload base64 images to Supabase Storage.

    Args:
        images: List of image dicts with base64 data
        user_id: User ID for filename

    Returns:
        tuple: (image_urls, image_types)
    """

    image_urls = []
    image_types = []

    for img in images:
        try:
            image_data = img.get('data', '')
            image_type = img.get('type', 'other').strip().lower()
            mime_type = img.get('mime_type', 'image/jpeg').strip().lower()

            if not image_data:
                continue

            # Decode base64
            if ',' in image_data:
                image_data = image_data.split(',')[1]

            try:
                image_bytes = base64.b64decode(image_data)
            except Exception:
                continue

            if not image_bytes:
                continue

            # Process image
            processed_data = ImageAnalyzer.process_image(image_bytes)
            if not processed_data:
                continue

            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            user_part = str(user_id)[:8]
            extension = mime_type.split('/')[-1].replace('jpeg', 'jpg')

            filename = f"{image_type}/{user_part}_{timestamp}_{unique_id}.{extension}"

            # Upload to storage
            url = StorageDB.upload_image(
                file_path=filename,
                file_data=processed_data,
                content_type=mime_type
            )

            if url:
                image_urls.append(url)
                image_types.append(image_type)

        except Exception as e:
            print(f"[IMAGE UPLOAD ERROR] {str(e)}")
            continue

    return image_urls, image_types


def get_recommended_doctors(specialist_type, severity, limit=3):
    """
    Get recommended doctors based on specialist type and severity.

    Returns:
        list: List of recommended doctors
    """

    try:
        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*').eq('available', True)

        # Filter by specialty
        if specialist_type and specialist_type != 'General Physician':
            query = query.eq('specialty', specialist_type)

        # For high severity, prefer top rated
        if severity in ['High', 'Critical']:
            query = query.gte('rating', 4.5)

        response = query.order('rating', desc=True).limit(limit).execute()
        doctors = response.data or []

        # Fallback to general physicians if no specialists found
        if len(doctors) == 0:
            general_response = supabase.table('doctors').select('*').eq(
                'available', True
            ).eq(
                'specialty', 'General Physician'
            ).order('rating', desc=True).limit(limit).execute()

            doctors = general_response.data or []

        return doctors

    except Exception as e:
        print(f"[GET DOCTORS ERROR] {str(e)}")
        return []


# ============================================
# ANALYZE SYMPTOMS (WITH LANGUAGE SUPPORT)
# ============================================
@symptom_bp.route('/analyze', methods=['POST'])
@token_required
def analyze_symptoms():
    """
    Analyze user symptoms using Gemini AI.

    Request Body:
    {
        "symptoms_text": "I have headache and fever for 3 days",
        "additional_notes": "Taking paracetamol",
        "age": 25,
        "gender": "male",
        "duration": "3 days",
        "input_type": "text",
        "language": "en",
        "images": [
            {
                "data": "base64_string",
                "type": "skin",
                "mime_type": "image/jpeg"
            }
        ],
        "image_types": ["skin"]
    }

    Returns:
        200: Analysis complete with diagnosis
        400: Validation error
        500: Analysis failed
    """

    try:
        data = request.get_json()

        # Validate input
        is_valid, error_msg = validate_symptom_input(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400

        # Extract data
        user_id = g.current_user_id
        symptoms_text = data.get('symptoms_text', '').strip()
        additional_notes = data.get('additional_notes', '').strip()
        age = data.get('age')
        gender = data.get('gender', '').strip().lower() if data.get('gender') else None
        duration = data.get('duration', '').strip() if data.get('duration') else None
        input_type = data.get('input_type', 'text').strip().lower()
        images = data.get('images', [])
        language = data.get('language', 'en')

        # Validate language
        if language not in VALID_LANGUAGES:
            language = 'en'

        # Validate input_type
        valid_input_types = ['text', 'voice', 'image', 'combined']
        if input_type not in valid_input_types:
            input_type = 'text'

        # Convert age to int
        if age is not None:
            try:
                age = int(age)
            except (ValueError, TypeError):
                age = None

        # Use user data as fallback
        user = g.current_user
        if age is None and user.get('age'):
            age = user.get('age')
        if not gender and user.get('gender'):
            gender = user.get('gender')

        # ============================================
        # STEP 1: Upload Images (if any)
        # ============================================
        image_urls = []
        image_types = []

        if images and len(images) > 0:
            image_urls, image_types = upload_images_to_storage(images, user_id)

        # ============================================
        # STEP 2: Save Symptoms Log
        # ============================================
        symptom_log_data = {
            'user_id': user_id,
            'symptoms_text': symptoms_text or 'Image-based analysis',
            'input_type': input_type,
            'age': age,
            'gender': gender
        }

        if duration:
            symptom_log_data['duration'] = duration

        if additional_notes:
            symptom_log_data['additional_notes'] = additional_notes

        if image_urls:
            symptom_log_data['image_urls'] = image_urls
            symptom_log_data['image_types'] = image_types

        symptom_log = SymptomDB.create(symptom_log_data)

        if not symptom_log:
            return jsonify({
                'success': False,
                'message': 'Failed to save symptom log'
            }), 500

        log_id = symptom_log['id']

        # ============================================
        # STEP 3: Analyze with Gemini AI (WITH LANGUAGE)
        # ============================================
        analysis_result = None

        try:
            # Prepare image data for AI (base64 from request, not URLs)
            ai_images = []
            for img in images:
                img_data = img.get('data', '')
                img_type = img.get('type', 'other')

                if img_data:
                    if ',' in img_data:
                        img_data = img_data.split(',')[1]

                    try:
                        img_bytes = base64.b64decode(img_data)
                        ai_images.append({
                            'bytes': img_bytes,
                            'type': img_type,
                            'mime_type': img.get('mime_type', 'image/jpeg')
                        })
                    except Exception:
                        continue

            # Call Gemini service with language
            if ai_images and symptoms_text:
                analysis_result = GeminiService.analyze_symptoms_with_images(
                    symptoms_text=symptoms_text,
                    age=age,
                    gender=gender,
                    duration=duration,
                    additional_notes=additional_notes,
                    images=ai_images,
                    language=language
                )
            elif ai_images:
                analysis_result = GeminiService.analyze_image(
                    image_bytes=ai_images[0]['bytes'],
                    image_type=ai_images[0]['type'],
                    symptoms_context=symptoms_text,
                    language=language
                )
            else:
                analysis_result = GeminiService.analyze_symptoms(
                    symptoms_text=symptoms_text,
                    age=age,
                    gender=gender,
                    duration=duration,
                    additional_notes=additional_notes,
                    language=language
                )

        except Exception as e:
            print(f"[GEMINI ERROR] {str(e)}")
            analysis_result = {
                'success': False,
                'error': str(e)
            }

        if not analysis_result or not analysis_result.get('success'):
            error_message = 'AI analysis failed'
            if analysis_result:
                error_message = analysis_result.get('error', error_message)

            return jsonify({
                'success': False,
                'message': error_message,
                'log_id': log_id
            }), 500

        ai_data = analysis_result.get('data', {})

        # ============================================
        # STEP 4: Calculate Final Severity
        # ============================================
        ai_severity = ai_data.get('severity', 'Low')

        final_severity = SeverityEngine.calculate_severity(
            ai_severity=ai_severity,
            symptoms_text=symptoms_text,
            age=age,
            probable_diseases=ai_data.get('probable_diseases', [])
        )

        # ============================================
        # STEP 5: Save Diagnosis (ENHANCED WITH LANGUAGE)
        # ============================================
        probable_diseases = ai_data.get('probable_diseases', [])
        primary_disease = probable_diseases[0]['name'] if probable_diseases else 'Unknown'
        primary_confidence = probable_diseases[0].get('confidence', 0) if probable_diseases else 0

        # Build enhanced AI response with all detailed fields
        enhanced_ai_data = {
            'probable_diseases': probable_diseases,
            'severity': final_severity,
            'description': ai_data.get('description', ''),
            'detailed_explanation': ai_data.get('detailed_explanation', ''),
            'causes': ai_data.get('causes', []),
            'duration_info': ai_data.get('duration_info', {}),
            'warning_signs': ai_data.get('warning_signs', []),
            'home_remedies': ai_data.get('home_remedies', []),
            'diet_recommendations': ai_data.get('diet_recommendations', {}),
            'lifestyle_changes': ai_data.get('lifestyle_changes', {}),
            'precautions': ai_data.get('precautions', {}),
            'faqs': ai_data.get('faqs', []),
            'specialist_type': ai_data.get('specialist_type', 'General Physician'),
            'additional_info': ai_data.get('additional_info', ''),
            'language': language
        }

        diagnosis_data = {
            'symptom_log_id': log_id,
            'probable_diseases': probable_diseases,
            'primary_disease': primary_disease,
            'confidence_score': primary_confidence,
            'severity': final_severity,
            'description': ai_data.get('description', ''),
            'precautions': ai_data.get('precautions', {}),
            'specialist_type': ai_data.get('specialist_type', 'General Physician'),
            'ai_raw_response': enhanced_ai_data,
            'has_recommendation': True
        }

        diagnosis = DiagnosisDB.create(diagnosis_data)

        if not diagnosis:
            return jsonify({
                'success': False,
                'message': 'Failed to save diagnosis',
                'log_id': log_id
            }), 500

        diagnosis_id = diagnosis['id']

        # ============================================
        # STEP 6: Get Recommended Doctors
        # ============================================
        specialist_type = ai_data.get('specialist_type', 'General Physician')

        recommended_doctors = get_recommended_doctors(
            specialist_type=specialist_type,
            severity=final_severity,
            limit=3
        )

        # ============================================
        # STEP 7: Save Recommendations
        # ============================================
        urgency_map = {
            'Low': 'routine',
            'Medium': 'soon',
            'High': 'urgent',
            'Critical': 'emergency'
        }
        urgency = urgency_map.get(final_severity, 'routine')

        for doctor in recommended_doctors:
            try:
                supabase = get_admin_supabase()
                supabase.table('recommendations').insert({
                    'diagnosis_id': diagnosis_id,
                    'doctor_id': doctor['id'],
                    'reason': f'Recommended for {primary_disease}',
                    'urgency': urgency
                }).execute()
            except Exception as e:
                print(f"[RECOMMENDATION ERROR] {str(e)}")
                continue

        # ============================================
        # STEP 8: Build Response (ENHANCED WITH LANGUAGE)
        # ============================================
        response_data = {
            'success': True,
            'message': 'Symptom analysis completed',
            'log_id': log_id,
            'diagnosis_id': diagnosis_id,
            'language': language,
            'diagnosis': {
                'primary_disease': primary_disease,
                'probable_diseases': probable_diseases,
                'severity': final_severity,
                'confidence_score': primary_confidence,
                'description': ai_data.get('description', ''),
                'detailed_explanation': ai_data.get('detailed_explanation', ''),
                'causes': ai_data.get('causes', []),
                'duration_info': ai_data.get('duration_info', {}),
                'warning_signs': ai_data.get('warning_signs', []),
                'home_remedies': ai_data.get('home_remedies', []),
                'diet_recommendations': ai_data.get('diet_recommendations', {}),
                'lifestyle_changes': ai_data.get('lifestyle_changes', {}),
                'precautions': ai_data.get('precautions', {}),
                'faqs': ai_data.get('faqs', []),
                'specialist_type': specialist_type,
                'additional_info': ai_data.get('additional_info', '')
            },
            'recommended_doctors': recommended_doctors,
            'patient': {
                'age': age,
                'gender': gender,
                'duration': duration
            },
            'symptoms_text': symptoms_text,
            'input_methods': [input_type],
            'analyzed_at': datetime.utcnow().isoformat()
        }

        if image_urls:
            response_data['image_urls'] = image_urls
            response_data['image_types'] = image_types

        return jsonify(response_data), 200

    except Exception as e:
        print(f"[ANALYZE SYMPTOMS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Symptom analysis failed',
            'error': str(e)
        }), 500


# ============================================
# GET USER HISTORY
# ============================================
@symptom_bp.route('/history', methods=['GET'])
@token_required
def get_history():
    """
    Get the current user's symptom analysis history.

    Query Params:
        limit: Number of records (default 10, max 50)
        page: Page number (default 1)

    Returns:
        200: List of past analyses
        500: Server error
    """

    try:
        user_id = g.current_user_id

        try:
            limit = int(request.args.get('limit', DEFAULT_HISTORY_LIMIT))
            if limit < 1:
                limit = DEFAULT_HISTORY_LIMIT
            elif limit > MAX_HISTORY_LIMIT:
                limit = MAX_HISTORY_LIMIT
        except (ValueError, TypeError):
            limit = DEFAULT_HISTORY_LIMIT

        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        offset = (page - 1) * limit

        supabase = get_admin_supabase()

        # Get symptom logs
        symptoms_response = supabase.table('symptoms_log').select(
            '*'
        ).eq('user_id', user_id).order(
            'created_at', desc=True
        ).range(offset, offset + limit - 1).execute()

        symptoms = symptoms_response.data or []

        history = []

        for symptom in symptoms:
            # Get diagnosis for this symptom
            diagnosis_response = supabase.table('diagnoses').select('*').eq(
                'symptom_log_id', symptom['id']
            ).execute()

            diagnosis = None
            if diagnosis_response.data and len(diagnosis_response.data) > 0:
                diagnosis = diagnosis_response.data[0]

            history_item = {
                'id': symptom['id'],
                'symptoms_text': symptom.get('symptoms_text'),
                'input_type': symptom.get('input_type'),
                'image_urls': symptom.get('image_urls', []),
                'image_types': symptom.get('image_types', []),
                'age': symptom.get('age'),
                'gender': symptom.get('gender'),
                'duration': symptom.get('duration'),
                'created_at': symptom.get('created_at'),
                'has_recommendation': diagnosis.get('has_recommendation', False) if diagnosis else False
            }

            if diagnosis:
                history_item.update({
                    'diagnosis_id': diagnosis['id'],
                    'primary_disease': diagnosis.get('primary_disease'),
                    'severity': diagnosis.get('severity'),
                    'confidence_score': diagnosis.get('confidence_score'),
                    'specialist_type': diagnosis.get('specialist_type')
                })

            history.append(history_item)

        # Get total count
        count_response = supabase.table('symptoms_log').select(
            'id', count='exact'
        ).eq('user_id', user_id).execute()

        total_count = count_response.count or 0

        return jsonify({
            'success': True,
            'history': history,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': (total_count + limit - 1) // limit if total_count > 0 else 0
            }
        }), 200

    except Exception as e:
        print(f"[GET HISTORY ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch history',
            'error': str(e)
        }), 500


# ============================================
# GET HISTORY DETAIL BY ID
# ============================================
@symptom_bp.route('/history/<log_id>', methods=['GET'])
@token_required
def get_history_detail(log_id):
    """
    Get detailed information about a specific symptom analysis.

    URL Params:
        log_id: Symptom log UUID

    Returns:
        200: Detailed analysis data
        404: Not found
        403: Not authorized
    """

    try:
        if not log_id:
            return jsonify({
                'success': False,
                'message': 'Log ID is required'
            }), 400

        user_id = g.current_user_id

        # Get symptom log
        symptom = SymptomDB.get_by_id(log_id)

        if not symptom:
            return jsonify({
                'success': False,
                'message': 'Symptom log not found'
            }), 404

        # Verify ownership
        if symptom.get('user_id') != user_id and g.current_user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'You can only view your own history'
            }), 403

        # Get diagnosis
        diagnosis = DiagnosisDB.get_by_symptom_log(log_id)

        # Get recommendations
        recommended_doctors = []

        if diagnosis:
            supabase = get_admin_supabase()
            recommendations_response = supabase.table('recommendations').select(
                '*, doctors(*)'
            ).eq('diagnosis_id', diagnosis['id']).execute()

            if recommendations_response.data:
                for rec in recommendations_response.data:
                    doctor = rec.get('doctors')
                    if doctor:
                        recommended_doctors.append(doctor)

        # Build response
        response_data = {
            'success': True,
            'data': {
                'log_id': symptom['id'],
                'symptoms_text': symptom.get('symptoms_text'),
                'input_methods': [symptom.get('input_type')] if symptom.get('input_type') else [],
                'image_urls': symptom.get('image_urls', []),
                'image_types': symptom.get('image_types', []),
                'patient': {
                    'age': symptom.get('age'),
                    'gender': symptom.get('gender'),
                    'duration': symptom.get('duration')
                },
                'additional_notes': symptom.get('additional_notes'),
                'timestamp': symptom.get('created_at'),
                'images': [
                    {'preview': url, 'type': type_}
                    for url, type_ in zip(
                        symptom.get('image_urls', []) or [],
                        symptom.get('image_types', []) or []
                    )
                ]
            }
        }

        if diagnosis:
            # Get enhanced data from ai_raw_response if available
            ai_data = diagnosis.get('ai_raw_response', {}) or {}

            response_data['data']['diagnosis_id'] = diagnosis['id']
            response_data['data']['language'] = ai_data.get('language', 'en')
            response_data['data']['diagnosis'] = {
                'primary_disease': diagnosis.get('primary_disease'),
                'probable_diseases': diagnosis.get('probable_diseases', []),
                'severity': diagnosis.get('severity'),
                'confidence_score': diagnosis.get('confidence_score'),
                'description': diagnosis.get('description'),
                'detailed_explanation': ai_data.get('detailed_explanation', ''),
                'causes': ai_data.get('causes', []),
                'duration_info': ai_data.get('duration_info', {}),
                'warning_signs': ai_data.get('warning_signs', []),
                'home_remedies': ai_data.get('home_remedies', []),
                'diet_recommendations': ai_data.get('diet_recommendations', {}),
                'lifestyle_changes': ai_data.get('lifestyle_changes', {}),
                'precautions': diagnosis.get('precautions', {}),
                'faqs': ai_data.get('faqs', []),
                'specialist_type': diagnosis.get('specialist_type'),
                'additional_info': ai_data.get('additional_info', '')
            }
            response_data['data']['recommended_doctors'] = recommended_doctors

        return jsonify(response_data), 200

    except Exception as e:
        print(f"[GET HISTORY DETAIL ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch history detail',
            'error': str(e)
        }), 500


# ============================================
# DELETE HISTORY
# ============================================
@symptom_bp.route('/history/<log_id>', methods=['DELETE'])
@token_required
def delete_history(log_id):
    """
    Delete a symptom log and its associated data.

    URL Params:
        log_id: Symptom log UUID

    Returns:
        200: Deleted successfully
        404: Not found
        403: Not authorized
    """

    try:
        if not log_id:
            return jsonify({
                'success': False,
                'message': 'Log ID is required'
            }), 400

        user_id = g.current_user_id

        # Get symptom log
        symptom = SymptomDB.get_by_id(log_id)

        if not symptom:
            return jsonify({
                'success': False,
                'message': 'Symptom log not found'
            }), 404

        # Verify ownership
        if symptom.get('user_id') != user_id and g.current_user_role != 'admin':
            return jsonify({
                'success': False,
                'message': 'You can only delete your own history'
            }), 403

        # Delete (cascading deletes diagnoses and recommendations)
        success = SymptomDB.delete(log_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete history'
            }), 500

        return jsonify({
            'success': True,
            'message': 'History deleted successfully'
        }), 200

    except Exception as e:
        print(f"[DELETE HISTORY ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete history',
            'error': str(e)
        }), 500


# ============================================
# GET LATEST ANALYSIS
# ============================================
@symptom_bp.route('/latest', methods=['GET'])
@token_required
def get_latest_analysis():
    """
    Get the user's most recent symptom analysis.

    Returns:
        200: Latest analysis or empty
    """

    try:
        user_id = g.current_user_id

        supabase = get_admin_supabase()

        # Get latest symptom log
        symptoms_response = supabase.table('symptoms_log').select('*').eq(
            'user_id', user_id
        ).order('created_at', desc=True).limit(1).execute()

        if not symptoms_response.data or len(symptoms_response.data) == 0:
            return jsonify({
                'success': True,
                'message': 'No analysis history found',
                'data': None
            }), 200

        symptom = symptoms_response.data[0]

        # Get associated diagnosis
        diagnosis = DiagnosisDB.get_by_symptom_log(symptom['id'])

        result = {
            'log_id': symptom['id'],
            'symptoms_text': symptom.get('symptoms_text'),
            'input_type': symptom.get('input_type'),
            'created_at': symptom.get('created_at')
        }

        if diagnosis:
            result['diagnosis'] = {
                'primary_disease': diagnosis.get('primary_disease'),
                'severity': diagnosis.get('severity'),
                'confidence_score': diagnosis.get('confidence_score'),
                'specialist_type': diagnosis.get('specialist_type')
            }

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        print(f"[GET LATEST ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch latest analysis',
            'error': str(e)
        }), 500


# ============================================
# GET USER STATISTICS
# ============================================
@symptom_bp.route('/stats', methods=['GET'])
@token_required
def get_user_stats():
    """
    Get statistics about user's symptom analyses.

    Returns:
        200: User statistics
    """

    try:
        user_id = g.current_user_id
        supabase = get_admin_supabase()

        # Total checkups
        total_response = supabase.table('symptoms_log').select(
            'id', count='exact'
        ).eq('user_id', user_id).execute()
        total_checkups = total_response.count or 0

        # Get all symptom logs
        all_symptoms = supabase.table('symptoms_log').select('id').eq(
            'user_id', user_id
        ).execute()

        log_ids = [s['id'] for s in (all_symptoms.data or [])]

        # Severity distribution
        severity_dist = {'Low': 0, 'Medium': 0, 'High': 0, 'Critical': 0}
        last_severity = None

        if log_ids:
            diagnoses_response = supabase.table('diagnoses').select(
                'severity, created_at'
            ).in_('symptom_log_id', log_ids).order(
                'created_at', desc=True
            ).execute()

            diagnoses = diagnoses_response.data or []

            for diag in diagnoses:
                sev = diag.get('severity')
                if sev in severity_dist:
                    severity_dist[sev] += 1

            if diagnoses:
                last_severity = diagnoses[0].get('severity')

        # Image analysis count
        images_response = supabase.table('symptoms_log').select(
            'id', count='exact'
        ).eq('user_id', user_id).in_(
            'input_type', ['image', 'combined']
        ).execute()

        images_analyzed = images_response.count or 0

        return jsonify({
            'success': True,
            'stats': {
                'total_checkups': total_checkups,
                'last_severity': last_severity,
                'images_analyzed': images_analyzed,
                'severity_distribution': severity_dist
            }
        }), 200

    except Exception as e:
        print(f"[USER STATS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch statistics',
            'error': str(e)
        }), 500