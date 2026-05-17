"""
============================================
ADMIN ROUTES
============================================
Admin panel endpoints for managing users, doctors,
viewing diagnoses, and system statistics.
All routes require admin authentication.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import re

from models.database import (
    get_admin_supabase,
    UserDB,
    DoctorDB,
    DiagnosisDB,
    SymptomDB
)
from middleware.auth_middleware import admin_required
from services.auth_service import AuthService


# ============================================
# CREATE BLUEPRINT
# ============================================
admin_bp = Blueprint('admin', __name__)


# ============================================
# CONSTANTS
# ============================================
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


# ============================================
# VALIDATION HELPERS
# ============================================
def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_user(user):
    """Remove sensitive fields from user object"""
    if not user:
        return None
    sensitive_fields = ['password_hash', 'password']
    return {k: v for k, v in user.items() if k not in sensitive_fields}


def get_pagination_params():
    """Get pagination parameters from query string"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', DEFAULT_PAGE_SIZE))

        if page < 1:
            page = 1

        if limit < 1:
            limit = DEFAULT_PAGE_SIZE
        elif limit > MAX_PAGE_SIZE:
            limit = MAX_PAGE_SIZE

        offset = (page - 1) * limit
        return page, limit, offset

    except (ValueError, TypeError):
        return 1, DEFAULT_PAGE_SIZE, 0


# ============================================
# DASHBOARD STATISTICS
# ============================================
@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """
    Get admin dashboard statistics.

    Returns:
        200: Dashboard statistics
        401: Not authenticated
        403: Not an admin
    """

    try:
        supabase = get_admin_supabase()

        # Get total counts
        total_users = UserDB.count()
        total_doctors = DoctorDB.count()
        total_diagnoses = DiagnosisDB.count()

        # Get critical cases count
        critical_response = supabase.table('diagnoses').select(
            'id', count='exact'
        ).eq('severity', 'Critical').execute()
        critical_cases = critical_response.count or 0

        # Get severity distribution
        severity_distribution = DiagnosisDB.get_severity_distribution()

        # Get today's diagnoses
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        today_response = supabase.table('diagnoses').select(
            'id', count='exact'
        ).gte('created_at', today_start).execute()
        today_diagnoses = today_response.count or 0

        # Get this week's new users
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        new_users_response = supabase.table('users').select(
            'id', count='exact'
        ).gte('created_at', week_ago).execute()
        new_users_week = new_users_response.count or 0

        # Get specialty distribution from diagnoses
        specialty_response = supabase.table('diagnoses').select(
            'specialist_type'
        ).execute()

        specialty_distribution = {}
        if specialty_response.data:
            for item in specialty_response.data:
                spec = item.get('specialist_type')
                if spec:
                    specialty_distribution[spec] = specialty_distribution.get(spec, 0) + 1

        # Get active vs inactive users
        active_users_response = supabase.table('users').select(
            'id', count='exact'
        ).eq('is_active', True).execute()
        active_users = active_users_response.count or 0

        # Get available doctors
        available_doctors_response = supabase.table('doctors').select(
            'id', count='exact'
        ).eq('available', True).execute()
        available_doctors = available_doctors_response.count or 0

        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'total_doctors': total_doctors,
                'total_diagnoses': total_diagnoses,
                'critical_cases': critical_cases,
                'today_diagnoses': today_diagnoses,
                'new_users_week': new_users_week,
                'active_users': active_users,
                'available_doctors': available_doctors,
                'severity_distribution': severity_distribution,
                'specialty_distribution': specialty_distribution
            },
            'generated_at': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        print(f"[ADMIN STATS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch statistics',
            'error': str(e)
        }), 500


# ============================================
# GET ALL USERS
# ============================================
@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """
    Get list of all users with pagination and filters.

    Query Params:
        page: Page number (default 1)
        limit: Items per page (default 10, max 100)
        role: Filter by role (user/admin)
        status: Filter by is_active (true/false)
        search: Search by name or email

    Returns:
        200: List of users
        401: Not authenticated
        403: Not an admin
    """

    try:
        page, limit, offset = get_pagination_params()

        role = request.args.get('role', '').strip()
        status = request.args.get('status', '').strip()
        search = request.args.get('search', '').strip()

        supabase = get_admin_supabase()
        query = supabase.table('users').select('*')

        # Apply filters
        if role and role in ['user', 'admin']:
            query = query.eq('role', role)

        if status in ['true', 'false']:
            query = query.eq('is_active', status == 'true')

        if search:
            query = query.or_(f'name.ilike.%{search}%,email.ilike.%{search}%')

        # Get total count
        count_query = supabase.table('users').select('id', count='exact')

        if role and role in ['user', 'admin']:
            count_query = count_query.eq('role', role)
        if status in ['true', 'false']:
            count_query = count_query.eq('is_active', status == 'true')
        if search:
            count_query = count_query.or_(
                f'name.ilike.%{search}%,email.ilike.%{search}%'
            )

        count_response = count_query.execute()
        total_count = count_response.count or 0

        # Apply pagination and ordering
        response = query.order(
            'created_at', desc=True
        ).range(offset, offset + limit - 1).execute()

        users = response.data or []

        # Get checkup count for each user
        for user in users:
            checkup_response = supabase.table('symptoms_log').select(
                'id', count='exact'
            ).eq('user_id', user['id']).execute()
            user['checkup_count'] = checkup_response.count or 0

        # Sanitize users
        safe_users = [sanitize_user(u) for u in users]

        return jsonify({
            'success': True,
            'users': safe_users,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        print(f"[GET USERS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch users',
            'error': str(e)
        }), 500


# ============================================
# GET USER BY ID
# ============================================
@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
def get_user_by_id(user_id):
    """
    Get a specific user by ID with detailed information.

    Returns:
        200: User details
        404: User not found
    """

    try:
        user = UserDB.get_by_id(user_id)

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Get checkup count
        supabase = get_admin_supabase()
        checkup_response = supabase.table('symptoms_log').select(
            'id', count='exact'
        ).eq('user_id', user_id).execute()
        user['checkup_count'] = checkup_response.count or 0

        safe_user = sanitize_user(user)

        return jsonify({
            'success': True,
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[GET USER ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch user',
            'error': str(e)
        }), 500


# ============================================
# UPDATE USER
# ============================================
@admin_bp.route('/users/<user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """
    Update a user's information.

    Request Body:
    {
        "name": "Updated Name",
        "age": 30,
        "gender": "male",
        "role": "user",
        "is_active": true
    }

    Returns:
        200: User updated
        400: Validation error
        404: User not found
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        # Check if user exists
        existing_user = UserDB.get_by_id(user_id)
        if not existing_user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Prevent admin from deactivating themselves
        if user_id == g.current_user_id:
            if 'is_active' in data and not data['is_active']:
                return jsonify({
                    'success': False,
                    'message': 'You cannot deactivate your own account'
                }), 400

            if 'role' in data and data['role'] != 'admin':
                return jsonify({
                    'success': False,
                    'message': 'You cannot change your own admin role'
                }), 400

        update_data = {}

        if 'name' in data:
            name = data['name'].strip() if data['name'] else ''
            if name and len(name) >= 2:
                update_data['name'] = name

        if 'age' in data and data['age'] is not None:
            try:
                age = int(data['age'])
                if 1 <= age <= 120:
                    update_data['age'] = age
            except (ValueError, TypeError):
                pass

        if 'gender' in data and data['gender']:
            gender = data['gender'].strip().lower()
            if gender in ['male', 'female', 'other']:
                update_data['gender'] = gender

        if 'role' in data and data['role'] in ['user', 'admin']:
            update_data['role'] = data['role']

        if 'is_active' in data:
            update_data['is_active'] = bool(data['is_active'])

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
                'message': 'Failed to update user'
            }), 500

        safe_user = sanitize_user(updated_user)

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': safe_user
        }), 200

    except Exception as e:
        print(f"[UPDATE USER ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update user',
            'error': str(e)
        }), 500


# ============================================
# DELETE USER
# ============================================
@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """
    Permanently delete a user and all their data.

    Returns:
        200: User deleted
        400: Cannot delete self
        404: User not found
    """

    try:
        # Prevent self-deletion
        if user_id == g.current_user_id:
            return jsonify({
                'success': False,
                'message': 'You cannot delete your own account'
            }), 400

        # Check if user exists
        user = UserDB.get_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Delete user (cascading deletes related data)
        success = UserDB.delete(user_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete user'
            }), 500

        return jsonify({
            'success': True,
            'message': f'User {user.get("name", "")} has been deleted'
        }), 200

    except Exception as e:
        print(f"[DELETE USER ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete user',
            'error': str(e)
        }), 500


# ============================================
# GET USER HISTORY (Admin View)
# ============================================
@admin_bp.route('/users/<user_id>/history', methods=['GET'])
@admin_required
def get_user_history(user_id):
    """
    Get a user's diagnosis history.

    Returns:
        200: User history
        404: User not found
    """

    try:
        # Check if user exists
        user = UserDB.get_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        supabase = get_admin_supabase()

        # Get user's symptom logs with diagnoses
        symptoms_response = supabase.table('symptoms_log').select(
            '*'
        ).eq('user_id', user_id).order('created_at', desc=True).execute()

        symptoms = symptoms_response.data or []

        history = []

        for symptom in symptoms:
            # Get diagnosis for this symptom
            diagnosis_response = supabase.table('diagnoses').select(
                '*'
            ).eq('symptom_log_id', symptom['id']).execute()

            diagnosis = None
            if diagnosis_response.data and len(diagnosis_response.data) > 0:
                diagnosis = diagnosis_response.data[0]

            history.append({
                'id': symptom['id'],
                'symptoms_text': symptom.get('symptoms_text'),
                'input_type': symptom.get('input_type'),
                'created_at': symptom.get('created_at'),
                'primary_disease': diagnosis.get('primary_disease') if diagnosis else None,
                'severity': diagnosis.get('severity') if diagnosis else None,
                'confidence_score': diagnosis.get('confidence_score') if diagnosis else None,
                'specialist_type': diagnosis.get('specialist_type') if diagnosis else None
            })

        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_name': user.get('name'),
            'history': history,
            'total': len(history)
        }), 200

    except Exception as e:
        print(f"[GET USER HISTORY ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch user history',
            'error': str(e)
        }), 500


# ============================================
# GET ALL DOCTORS (Admin View)
# ============================================
@admin_bp.route('/doctors', methods=['GET'])
@admin_required
def get_all_doctors():
    """
    Get all doctors with admin details.

    Returns:
        200: List of all doctors
    """

    try:
        page, limit, offset = get_pagination_params()

        doctors = DoctorDB.get_all()

        return jsonify({
            'success': True,
            'doctors': doctors,
            'total': len(doctors)
        }), 200

    except Exception as e:
        print(f"[GET ADMIN DOCTORS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctors',
            'error': str(e)
        }), 500


# ============================================
# ADD NEW DOCTOR
# ============================================
@admin_bp.route('/doctors', methods=['POST'])
@admin_required
def add_doctor():
    """
    Add a new doctor.

    Request Body:
    {
        "name": "Dr. Name",
        "specialty": "Cardiologist",
        "location": "Dhaka",
        "rating": 4.5,
        "contact": "+880-1XXX-XXXXXX",
        "email": "doctor@example.com",
        "experience_years": 10,
        "available": true
    }

    Returns:
        201: Doctor created
        400: Validation error
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        # Validate required fields
        name = data.get('name', '').strip()
        specialty = data.get('specialty', '').strip()
        location = data.get('location', '').strip()

        if not name or len(name) < 2:
            return jsonify({
                'success': False,
                'message': 'Doctor name is required'
            }), 400

        if not specialty:
            return jsonify({
                'success': False,
                'message': 'Specialty is required'
            }), 400

        if not location:
            return jsonify({
                'success': False,
                'message': 'Location is required'
            }), 400

        # Build doctor data
        doctor_data = {
            'name': name,
            'specialty': specialty,
            'location': location,
            'available': True
        }

        # Optional fields
        if 'email' in data and data['email']:
            email = data['email'].strip().lower()
            if is_valid_email(email):
                doctor_data['email'] = email

        if 'contact' in data and data['contact']:
            doctor_data['contact'] = data['contact'].strip()

        if 'rating' in data and data['rating'] is not None:
            try:
                rating = float(data['rating'])
                if 0 <= rating <= 5:
                    doctor_data['rating'] = rating
            except (ValueError, TypeError):
                pass

        if 'experience_years' in data and data['experience_years'] is not None:
            try:
                exp = int(data['experience_years'])
                if 0 <= exp <= 60:
                    doctor_data['experience_years'] = exp
            except (ValueError, TypeError):
                pass

        if 'available' in data:
            doctor_data['available'] = bool(data['available'])

        if 'image_url' in data and data['image_url']:
            doctor_data['image_url'] = data['image_url']

        # Create doctor
        new_doctor = DoctorDB.create(doctor_data)

        if not new_doctor:
            return jsonify({
                'success': False,
                'message': 'Failed to create doctor'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Doctor added successfully',
            'doctor': new_doctor
        }), 201

    except Exception as e:
        print(f"[ADD DOCTOR ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to add doctor',
            'error': str(e)
        }), 500


# ============================================
# UPDATE DOCTOR
# ============================================
@admin_bp.route('/doctors/<doctor_id>', methods=['PUT'])
@admin_required
def update_doctor(doctor_id):
    """
    Update doctor information.

    Returns:
        200: Doctor updated
        404: Doctor not found
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        # Check if doctor exists
        existing_doctor = DoctorDB.get_by_id(doctor_id)
        if not existing_doctor:
            return jsonify({
                'success': False,
                'message': 'Doctor not found'
            }), 404

        update_data = {}

        if 'name' in data and data['name']:
            update_data['name'] = data['name'].strip()

        if 'specialty' in data and data['specialty']:
            update_data['specialty'] = data['specialty'].strip()

        if 'location' in data and data['location']:
            update_data['location'] = data['location'].strip()

        if 'email' in data:
            email = data['email'].strip().lower() if data['email'] else None
            if email and is_valid_email(email):
                update_data['email'] = email
            elif not email:
                update_data['email'] = None

        if 'contact' in data:
            update_data['contact'] = data['contact'].strip() if data['contact'] else None

        if 'rating' in data and data['rating'] is not None:
            try:
                rating = float(data['rating'])
                if 0 <= rating <= 5:
                    update_data['rating'] = rating
            except (ValueError, TypeError):
                pass

        if 'experience_years' in data and data['experience_years'] is not None:
            try:
                exp = int(data['experience_years'])
                if 0 <= exp <= 60:
                    update_data['experience_years'] = exp
            except (ValueError, TypeError):
                pass

        if 'available' in data:
            update_data['available'] = bool(data['available'])

        if 'image_url' in data:
            update_data['image_url'] = data['image_url']

        if not update_data:
            return jsonify({
                'success': False,
                'message': 'No valid fields to update'
            }), 400

        # Update doctor
        updated_doctor = DoctorDB.update(doctor_id, update_data)

        if not updated_doctor:
            return jsonify({
                'success': False,
                'message': 'Failed to update doctor'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Doctor updated successfully',
            'doctor': updated_doctor
        }), 200

    except Exception as e:
        print(f"[UPDATE DOCTOR ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update doctor',
            'error': str(e)
        }), 500


# ============================================
# DELETE DOCTOR
# ============================================
@admin_bp.route('/doctors/<doctor_id>', methods=['DELETE'])
@admin_required
def delete_doctor(doctor_id):
    """
    Delete a doctor permanently.

    Returns:
        200: Doctor deleted
        404: Doctor not found
    """

    try:
        # Check if doctor exists
        doctor = DoctorDB.get_by_id(doctor_id)
        if not doctor:
            return jsonify({
                'success': False,
                'message': 'Doctor not found'
            }), 404

        # Delete doctor
        success = DoctorDB.delete(doctor_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete doctor'
            }), 500

        return jsonify({
            'success': True,
            'message': f'Doctor {doctor.get("name", "")} has been deleted'
        }), 200

    except Exception as e:
        print(f"[DELETE DOCTOR ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete doctor',
            'error': str(e)
        }), 500


# ============================================
# GET ALL DIAGNOSES
# ============================================
@admin_bp.route('/diagnoses', methods=['GET'])
@admin_required
def get_all_diagnoses():
    """
    Get all diagnoses with patient information.

    Query Params:
        limit: Number of diagnoses (default 10)
        page: Page number (default 1)
        severity: Filter by severity

    Returns:
        200: List of diagnoses
    """

    try:
        page, limit, offset = get_pagination_params()
        severity = request.args.get('severity', '').strip()

        supabase = get_admin_supabase()

        # Build query for symptoms_log with related data
        query = supabase.table('symptoms_log').select(
            '*, users(id, name, email), diagnoses(*)'
        ).order('created_at', desc=True)

        response = query.range(offset, offset + limit - 1).execute()

        symptoms = response.data or []

        diagnoses_list = []

        for symptom in symptoms:
            user = symptom.get('users') or {}
            diagnoses = symptom.get('diagnoses') or []
            diagnosis = diagnoses[0] if diagnoses else {}

            # Apply severity filter
            if severity and diagnosis.get('severity') != severity:
                continue

            diagnoses_list.append({
                'id': diagnosis.get('id') or symptom['id'],
                'symptom_log_id': symptom['id'],
                'user_id': symptom.get('user_id'),
                'user_name': user.get('name', 'Anonymous'),
                'user_email': user.get('email', ''),
                'symptoms_text': symptom.get('symptoms_text'),
                'input_type': symptom.get('input_type'),
                'primary_disease': diagnosis.get('primary_disease'),
                'severity': diagnosis.get('severity'),
                'confidence_score': diagnosis.get('confidence_score'),
                'description': diagnosis.get('description'),
                'specialist_type': diagnosis.get('specialist_type'),
                'created_at': symptom.get('created_at')
            })

        # Get total count
        count_response = supabase.table('symptoms_log').select(
            'id', count='exact'
        ).execute()
        total_count = count_response.count or 0

        return jsonify({
            'success': True,
            'diagnoses': diagnoses_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count
            }
        }), 200

    except Exception as e:
        print(f"[GET DIAGNOSES ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch diagnoses',
            'error': str(e)
        }), 500


# ============================================
# GET ACTIVITY LOG
# ============================================
@admin_bp.route('/activity', methods=['GET'])
@admin_required
def get_activity():
    """
    Get recent system activity.

    Query Params:
        limit: Number of activities (default 10)

    Returns:
        200: List of recent activities
    """

    try:
        limit = int(request.args.get('limit', 10))
        if limit < 1 or limit > 50:
            limit = 10

        supabase = get_admin_supabase()
        activities = []

        # Recent registrations
        users_response = supabase.table('users').select(
            'id, name, email, created_at, role'
        ).order('created_at', desc=True).limit(5).execute()

        for user in (users_response.data or []):
            activities.append({
                'type': 'user_registered',
                'icon': 'user-plus',
                'color': 'green',
                'message': f"<strong>{user.get('name')}</strong> registered as {user.get('role', 'user')}",
                'created_at': user.get('created_at')
            })

        # Recent diagnoses
        diagnoses_response = supabase.table('diagnoses').select(
            '*, symptoms_log(user_id, users(name))'
        ).order('created_at', desc=True).limit(5).execute()

        for diag in (diagnoses_response.data or []):
            symptom_log = diag.get('symptoms_log') or {}
            user = symptom_log.get('users') or {}

            severity = diag.get('severity', 'Low')
            color_map = {
                'Low': 'green',
                'Medium': 'orange',
                'High': 'red',
                'Critical': 'red'
            }

            activities.append({
                'type': 'diagnosis_created',
                'icon': 'stethoscope',
                'color': color_map.get(severity, 'blue'),
                'message': f"New <strong>{severity}</strong> severity diagnosis for <strong>{user.get('name', 'Anonymous')}</strong>",
                'created_at': diag.get('created_at')
            })

        # Recent doctor additions
        doctors_response = supabase.table('doctors').select(
            'id, name, specialty, created_at'
        ).order('created_at', desc=True).limit(3).execute()

        for doctor in (doctors_response.data or []):
            activities.append({
                'type': 'doctor_added',
                'icon': 'user-md',
                'color': 'blue',
                'message': f"<strong>{doctor.get('name')}</strong> ({doctor.get('specialty')}) added",
                'created_at': doctor.get('created_at')
            })

        # Sort all activities by date
        activities.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )

        # Limit results
        activities = activities[:limit]

        return jsonify({
            'success': True,
            'activities': activities,
            'total': len(activities)
        }), 200

    except Exception as e:
        print(f"[GET ACTIVITY ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch activity',
            'error': str(e)
        }), 500


# ============================================
# CREATE ADMIN USER (Super Admin only)
# ============================================
@admin_bp.route('/create-admin', methods=['POST'])
@admin_required
def create_admin():
    """
    Create a new admin user.

    Request Body:
    {
        "name": "Admin Name",
        "email": "admin@example.com",
        "password": "SecurePass123"
    }

    Returns:
        201: Admin created
        400: Validation error
        409: Email exists
    """

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'message': 'Request body is required'
            }), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not name or len(name) < 2:
            return jsonify({
                'success': False,
                'message': 'Name is required (min 2 characters)'
            }), 400

        if not is_valid_email(email):
            return jsonify({
                'success': False,
                'message': 'Valid email is required'
            }), 400

        if not password or len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400

        # Check if email exists
        existing = UserDB.get_by_email(email)
        if existing:
            return jsonify({
                'success': False,
                'message': 'Email already exists'
            }), 409

        # Hash password
        password_hash = AuthService.hash_password(password)

        # Create admin
        admin_data = {
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'role': 'admin',
            'is_active': True
        }

        new_admin = UserDB.create(admin_data)

        if not new_admin:
            return jsonify({
                'success': False,
                'message': 'Failed to create admin'
            }), 500

        safe_admin = sanitize_user(new_admin)

        return jsonify({
            'success': True,
            'message': 'Admin created successfully',
            'admin': safe_admin
        }), 201

    except Exception as e:
        print(f"[CREATE ADMIN ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create admin',
            'error': str(e)
        }), 500