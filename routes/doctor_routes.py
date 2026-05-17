"""
============================================
DOCTOR ROUTES
============================================
Public endpoints for searching and viewing doctors.
Used by symptom checker results and dashboard.
"""

from flask import Blueprint, request, jsonify

from models.database import DoctorDB, get_admin_supabase
from middleware.auth_middleware import optional_auth, token_required


# ============================================
# CREATE BLUEPRINT
# ============================================
doctor_bp = Blueprint('doctors', __name__)


# ============================================
# CONSTANTS
# ============================================
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


# ============================================
# HELPERS
# ============================================
def get_pagination_params():
    """Extract pagination parameters from query string"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', DEFAULT_LIMIT))

        if page < 1:
            page = 1

        if limit < 1:
            limit = DEFAULT_LIMIT
        elif limit > MAX_LIMIT:
            limit = MAX_LIMIT

        offset = (page - 1) * limit
        return page, limit, offset

    except (ValueError, TypeError):
        return 1, DEFAULT_LIMIT, 0


def parse_filters():
    """Parse filter parameters from query string"""
    filters = {}

    specialty = request.args.get('specialty', '').strip()
    location = request.args.get('location', '').strip()
    available = request.args.get('available', '').strip().lower()
    min_rating = request.args.get('min_rating', '').strip()

    if specialty:
        filters['specialty'] = specialty

    if location:
        filters['location'] = location

    if available in ['true', 'false']:
        filters['available'] = available == 'true'

    if min_rating:
        try:
            filters['min_rating'] = float(min_rating)
        except (ValueError, TypeError):
            pass

    return filters


# ============================================
# GET ALL DOCTORS
# ============================================
@doctor_bp.route('', methods=['GET'])
@doctor_bp.route('/', methods=['GET'])
@optional_auth
def get_doctors():
    """
    Get list of doctors with optional filters.

    Query Params:
        specialty: Filter by specialty (e.g., Dermatologist)
        location: Filter by location (e.g., Dhaka)
        available: Filter by availability (true/false)
        min_rating: Minimum rating filter (0.0 - 5.0)
        page: Page number (default 1)
        limit: Results per page (default 20, max 100)
        sort: Sort field (rating, name, experience_years)
        order: Sort order (asc, desc)

    Returns:
        200: List of doctors
        500: Server error

    Example:
        GET /api/doctors?specialty=Dermatologist&location=Dhaka&available=true
    """

    try:
        page, limit, offset = get_pagination_params()
        filters = parse_filters()

        # Get sort parameters
        sort_field = request.args.get('sort', 'rating').strip()
        sort_order = request.args.get('order', 'desc').strip().lower()

        # Validate sort field
        valid_sort_fields = [
            'rating', 'name', 'experience_years',
            'created_at', 'specialty', 'location'
        ]

        if sort_field not in valid_sort_fields:
            sort_field = 'rating'

        # Validate sort order
        descending = sort_order != 'asc'

        # Build query
        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*')

        # Apply filters
        if filters.get('specialty'):
            query = query.eq('specialty', filters['specialty'])

        if filters.get('location'):
            query = query.eq('location', filters['location'])

        if 'available' in filters:
            query = query.eq('available', filters['available'])

        if filters.get('min_rating') is not None:
            query = query.gte('rating', filters['min_rating'])

        # Get total count for pagination
        count_query = supabase.table('doctors').select('id', count='exact')

        if filters.get('specialty'):
            count_query = count_query.eq('specialty', filters['specialty'])
        if filters.get('location'):
            count_query = count_query.eq('location', filters['location'])
        if 'available' in filters:
            count_query = count_query.eq('available', filters['available'])
        if filters.get('min_rating') is not None:
            count_query = count_query.gte('rating', filters['min_rating'])

        count_response = count_query.execute()
        total_count = count_response.count or 0

        # Apply sorting and pagination
        response = query.order(
            sort_field,
            desc=descending
        ).range(offset, offset + limit - 1).execute()

        doctors = response.data or []

        return jsonify({
            'success': True,
            'doctors': doctors,
            'count': len(doctors),
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': (total_count + limit - 1) // limit if total_count > 0 else 0,
                'has_next': offset + limit < total_count,
                'has_prev': page > 1
            },
            'filters': filters
        }), 200

    except Exception as e:
        print(f"[GET DOCTORS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctors',
            'error': str(e)
        }), 500


# ============================================
# GET DOCTOR BY ID
# ============================================
@doctor_bp.route('/<doctor_id>', methods=['GET'])
@optional_auth
def get_doctor_by_id(doctor_id):
    """
    Get detailed information about a specific doctor.

    URL Params:
        doctor_id: UUID of the doctor

    Returns:
        200: Doctor details
        404: Doctor not found
        500: Server error
    """

    try:
        if not doctor_id:
            return jsonify({
                'success': False,
                'message': 'Doctor ID is required'
            }), 400

        doctor = DoctorDB.get_by_id(doctor_id)

        if not doctor:
            return jsonify({
                'success': False,
                'message': 'Doctor not found'
            }), 404

        return jsonify({
            'success': True,
            'doctor': doctor
        }), 200

    except Exception as e:
        print(f"[GET DOCTOR BY ID ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctor details',
            'error': str(e)
        }), 500


# ============================================
# GET DOCTORS BY SPECIALTY
# ============================================
@doctor_bp.route('/specialty/<specialty>', methods=['GET'])
@optional_auth
def get_doctors_by_specialty(specialty):
    """
    Get doctors filtered by specialty.

    URL Params:
        specialty: Specialty name (e.g., Dermatologist)

    Query Params:
        location: Optional location filter
        limit: Number of results (default 10)

    Returns:
        200: List of doctors in specialty
        500: Server error
    """

    try:
        if not specialty:
            return jsonify({
                'success': False,
                'message': 'Specialty is required'
            }), 400

        # Get optional parameters
        location = request.args.get('location', '').strip()

        try:
            limit = int(request.args.get('limit', 10))
            if limit < 1 or limit > MAX_LIMIT:
                limit = 10
        except (ValueError, TypeError):
            limit = 10

        # Build query
        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*').eq(
            'specialty', specialty
        ).eq('available', True)

        if location:
            query = query.eq('location', location)

        response = query.order(
            'rating', desc=True
        ).limit(limit).execute()

        doctors = response.data or []

        return jsonify({
            'success': True,
            'specialty': specialty,
            'location': location if location else 'All',
            'doctors': doctors,
            'count': len(doctors)
        }), 200

    except Exception as e:
        print(f"[GET BY SPECIALTY ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctors by specialty',
            'error': str(e)
        }), 500


# ============================================
# GET DOCTORS BY LOCATION
# ============================================
@doctor_bp.route('/location/<location>', methods=['GET'])
@optional_auth
def get_doctors_by_location(location):
    """
    Get doctors filtered by location.

    URL Params:
        location: Location name (e.g., Dhaka)

    Query Params:
        specialty: Optional specialty filter
        limit: Number of results (default 10)

    Returns:
        200: List of doctors in location
        500: Server error
    """

    try:
        if not location:
            return jsonify({
                'success': False,
                'message': 'Location is required'
            }), 400

        specialty = request.args.get('specialty', '').strip()

        try:
            limit = int(request.args.get('limit', 10))
            if limit < 1 or limit > MAX_LIMIT:
                limit = 10
        except (ValueError, TypeError):
            limit = 10

        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*').eq(
            'location', location
        ).eq('available', True)

        if specialty:
            query = query.eq('specialty', specialty)

        response = query.order(
            'rating', desc=True
        ).limit(limit).execute()

        doctors = response.data or []

        return jsonify({
            'success': True,
            'location': location,
            'specialty': specialty if specialty else 'All',
            'doctors': doctors,
            'count': len(doctors)
        }), 200

    except Exception as e:
        print(f"[GET BY LOCATION ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctors by location',
            'error': str(e)
        }), 500


# ============================================
# GET TOP RATED DOCTORS
# ============================================
@doctor_bp.route('/top-rated', methods=['GET'])
@optional_auth
def get_top_rated_doctors():
    """
    Get top rated available doctors.

    Query Params:
        limit: Number of doctors (default 5, max 20)
        specialty: Optional specialty filter

    Returns:
        200: List of top rated doctors
        500: Server error
    """

    try:
        try:
            limit = int(request.args.get('limit', 5))
            if limit < 1 or limit > 20:
                limit = 5
        except (ValueError, TypeError):
            limit = 5

        specialty = request.args.get('specialty', '').strip()

        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*').eq(
            'available', True
        ).gte('rating', 4.0)

        if specialty:
            query = query.eq('specialty', specialty)

        response = query.order(
            'rating', desc=True
        ).limit(limit).execute()

        doctors = response.data or []

        return jsonify({
            'success': True,
            'doctors': doctors,
            'count': len(doctors)
        }), 200

    except Exception as e:
        print(f"[GET TOP RATED ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch top rated doctors',
            'error': str(e)
        }), 500


# ============================================
# SEARCH DOCTORS
# ============================================
@doctor_bp.route('/search', methods=['GET'])
@optional_auth
def search_doctors():
    """
    Search doctors by name or specialty.

    Query Params:
        q: Search query (required)
        limit: Number of results (default 20)

    Returns:
        200: Search results
        400: Missing query
        500: Server error
    """

    try:
        query_text = request.args.get('q', '').strip()

        if not query_text or len(query_text) < 2:
            return jsonify({
                'success': False,
                'message': 'Search query must be at least 2 characters'
            }), 400

        try:
            limit = int(request.args.get('limit', 20))
            if limit < 1 or limit > MAX_LIMIT:
                limit = 20
        except (ValueError, TypeError):
            limit = 20

        supabase = get_admin_supabase()

        # Search in name, specialty, and location
        response = supabase.table('doctors').select('*').or_(
            f'name.ilike.%{query_text}%,'
            f'specialty.ilike.%{query_text}%,'
            f'location.ilike.%{query_text}%'
        ).order('rating', desc=True).limit(limit).execute()

        doctors = response.data or []

        return jsonify({
            'success': True,
            'query': query_text,
            'doctors': doctors,
            'count': len(doctors)
        }), 200

    except Exception as e:
        print(f"[SEARCH DOCTORS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to search doctors',
            'error': str(e)
        }), 500


# ============================================
# GET SPECIALTIES LIST
# ============================================
@doctor_bp.route('/specialties', methods=['GET'])
def get_specialties():
    """
    Get list of all unique specialties available.

    Returns:
        200: List of specialties with counts
        500: Server error
    """

    try:
        supabase = get_admin_supabase()
        response = supabase.table('doctors').select(
            'specialty'
        ).execute()

        specialties_count = {}

        if response.data:
            for item in response.data:
                spec = item.get('specialty')
                if spec:
                    specialties_count[spec] = specialties_count.get(spec, 0) + 1

        # Convert to list of objects
        specialties = [
            {'name': name, 'count': count}
            for name, count in specialties_count.items()
        ]

        # Sort by count descending
        specialties.sort(key=lambda x: x['count'], reverse=True)

        return jsonify({
            'success': True,
            'specialties': specialties,
            'total': len(specialties)
        }), 200

    except Exception as e:
        print(f"[GET SPECIALTIES ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch specialties',
            'error': str(e)
        }), 500


# ============================================
# GET LOCATIONS LIST
# ============================================
@doctor_bp.route('/locations', methods=['GET'])
def get_locations():
    """
    Get list of all unique locations.

    Returns:
        200: List of locations with counts
        500: Server error
    """

    try:
        supabase = get_admin_supabase()
        response = supabase.table('doctors').select(
            'location'
        ).execute()

        locations_count = {}

        if response.data:
            for item in response.data:
                loc = item.get('location')
                if loc:
                    locations_count[loc] = locations_count.get(loc, 0) + 1

        locations = [
            {'name': name, 'count': count}
            for name, count in locations_count.items()
        ]

        locations.sort(key=lambda x: x['count'], reverse=True)

        return jsonify({
            'success': True,
            'locations': locations,
            'total': len(locations)
        }), 200

    except Exception as e:
        print(f"[GET LOCATIONS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch locations',
            'error': str(e)
        }), 500


# ============================================
# GET RECOMMENDED DOCTORS FOR DIAGNOSIS
# ============================================
@doctor_bp.route('/recommend', methods=['POST'])
@token_required
def recommend_doctors():
    """
    Get recommended doctors based on diagnosis criteria.

    Request Body:
    {
        "specialist_type": "Dermatologist",
        "severity": "Medium",
        "location": "Dhaka",
        "limit": 3
    }

    Returns:
        200: Recommended doctors
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

        specialist_type = data.get('specialist_type', '').strip()
        severity = data.get('severity', 'Low').strip()
        location = data.get('location', '').strip()

        try:
            limit = int(data.get('limit', 3))
            if limit < 1 or limit > 10:
                limit = 3
        except (ValueError, TypeError):
            limit = 3

        supabase = get_admin_supabase()
        query = supabase.table('doctors').select('*').eq('available', True)

        # Filter by specialty if provided
        if specialist_type and specialist_type != 'General Physician':
            query = query.eq('specialty', specialist_type)

        # Filter by location if provided
        if location:
            query = query.eq('location', location)

        # For high/critical severity, prefer top rated doctors
        if severity in ['High', 'Critical']:
            query = query.gte('rating', 4.5)

        response = query.order(
            'rating', desc=True
        ).limit(limit).execute()

        doctors = response.data or []

        # If no doctors found with strict criteria, broaden search
        if len(doctors) == 0:
            fallback_query = supabase.table('doctors').select('*').eq(
                'available', True
            )

            if specialist_type and specialist_type != 'General Physician':
                fallback_query = fallback_query.eq('specialty', specialist_type)

            fallback_response = fallback_query.order(
                'rating', desc=True
            ).limit(limit).execute()

            doctors = fallback_response.data or []

        # Final fallback to general physicians
        if len(doctors) == 0:
            general_response = supabase.table('doctors').select('*').eq(
                'available', True
            ).eq(
                'specialty', 'General Physician'
            ).order('rating', desc=True).limit(limit).execute()

            doctors = general_response.data or []

        return jsonify({
            'success': True,
            'doctors': doctors,
            'count': len(doctors),
            'criteria': {
                'specialist_type': specialist_type,
                'severity': severity,
                'location': location
            }
        }), 200

    except Exception as e:
        print(f"[RECOMMEND DOCTORS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to recommend doctors',
            'error': str(e)
        }), 500


# ============================================
# GET DOCTOR STATISTICS
# ============================================
@doctor_bp.route('/stats', methods=['GET'])
def get_doctor_stats():
    """
    Get general statistics about doctors.

    Returns:
        200: Doctor statistics
        500: Server error
    """

    try:
        supabase = get_admin_supabase()

        # Total doctors
        total_response = supabase.table('doctors').select(
            'id', count='exact'
        ).execute()
        total_doctors = total_response.count or 0

        # Available doctors
        available_response = supabase.table('doctors').select(
            'id', count='exact'
        ).eq('available', True).execute()
        available_doctors = available_response.count or 0

        # All doctors for calculations
        all_response = supabase.table('doctors').select(
            'rating, specialty, location, experience_years'
        ).execute()

        doctors_data = all_response.data or []

        # Calculate average rating
        ratings = [d['rating'] for d in doctors_data if d.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        # Count specialties
        specialties = set()
        locations = set()
        total_experience = 0

        for doctor in doctors_data:
            if doctor.get('specialty'):
                specialties.add(doctor['specialty'])
            if doctor.get('location'):
                locations.add(doctor['location'])
            if doctor.get('experience_years'):
                total_experience += doctor['experience_years']

        avg_experience = total_experience / len(doctors_data) if doctors_data else 0

        return jsonify({
            'success': True,
            'stats': {
                'total_doctors': total_doctors,
                'available_doctors': available_doctors,
                'unavailable_doctors': total_doctors - available_doctors,
                'unique_specialties': len(specialties),
                'unique_locations': len(locations),
                'average_rating': round(avg_rating, 2),
                'average_experience_years': round(avg_experience, 1)
            }
        }), 200

    except Exception as e:
        print(f"[GET DOCTOR STATS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch doctor statistics',
            'error': str(e)
        }), 500