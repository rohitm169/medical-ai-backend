"""
============================================
DATABASE - SUPABASE CONNECTION
============================================
Manages Supabase client initialization and provides
helper functions for database operations.
"""

import os
from supabase import create_client, Client
from typing import Optional


# ============================================
# GLOBAL CLIENT INSTANCES
# ============================================
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


# ============================================
# INITIALIZE SUPABASE
# ============================================
def init_supabase():
    """
    Initialize Supabase client connections.
    Creates both public (anon) and admin (service role) clients.

    Raises:
        ValueError: If required environment variables are missing
        Exception: If connection fails
    """

    global _supabase_client, _supabase_admin_client

    # Get credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

    # Validate credentials
    if not supabase_url:
        raise ValueError('SUPABASE_URL is not set in environment variables')

    if not supabase_key:
        raise ValueError('SUPABASE_KEY is not set in environment variables')

    if not supabase_service_key:
        raise ValueError('SUPABASE_SERVICE_KEY is not set in environment variables')

    try:
        # Create public client (uses anon key)
        _supabase_client = create_client(
            supabase_url,
            supabase_key
        )

        # Create admin client (uses service role key - bypasses RLS)
        _supabase_admin_client = create_client(
            supabase_url,
            supabase_service_key
        )

        # Test connection
        test_response = _supabase_admin_client.table('users').select('id').limit(1).execute()

        print(f"[OK] Supabase connected successfully")
        print(f"[OK] Database URL: {supabase_url[:30]}...")

        return True

    except Exception as e:
        print(f"[ERROR] Supabase initialization failed: {str(e)}")
        raise Exception(f'Failed to initialize Supabase: {str(e)}')


# ============================================
# GET CLIENTS
# ============================================
def get_supabase() -> Client:
    """
    Get the public Supabase client (uses anon key).
    Subject to Row Level Security (RLS) policies.

    Returns:
        Client: Supabase client instance

    Raises:
        Exception: If client is not initialized
    """

    global _supabase_client

    if _supabase_client is None:
        init_supabase()

    return _supabase_client


def get_admin_supabase() -> Client:
    """
    Get the admin Supabase client (uses service role key).
    Bypasses Row Level Security - use carefully!

    Returns:
        Client: Supabase admin client instance

    Raises:
        Exception: If client is not initialized
    """

    global _supabase_admin_client

    if _supabase_admin_client is None:
        init_supabase()

    return _supabase_admin_client


# ============================================
# TEST CONNECTION
# ============================================
def test_connection() -> dict:
    """
    Test the Supabase connection by querying a table.

    Returns:
        dict: Connection status with details
    """

    try:
        client = get_admin_supabase()
        response = client.table('users').select('id').limit(1).execute()

        return {
            'success': True,
            'status': 'connected',
            'message': 'Supabase connection is healthy'
        }

    except Exception as e:
        return {
            'success': False,
            'status': 'error',
            'message': f'Connection failed: {str(e)}'
        }


# ============================================
# CLOSE CONNECTION
# ============================================
def close_connection():
    """
    Close Supabase connections and reset clients.
    Useful for cleanup during testing or app shutdown.
    """

    global _supabase_client, _supabase_admin_client

    _supabase_client = None
    _supabase_admin_client = None

    print("[OK] Supabase connections closed")


# ============================================
# USER OPERATIONS
# ============================================
class UserDB:
    """Database operations for users table"""

    @staticmethod
    def get_by_id(user_id: str):
        """Get user by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('users').select('*').eq('id', user_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_id: {str(e)}")
            return None


    @staticmethod
    def get_by_email(email: str):
        """Get user by email"""
        try:
            client = get_admin_supabase()
            response = client.table('users').select('*').eq('email', email.lower()).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_email: {str(e)}")
            return None


    @staticmethod
    def create(user_data: dict):
        """Create new user"""
        try:
            client = get_admin_supabase()
            response = client.table('users').insert(user_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] create user: {str(e)}")
            raise


    @staticmethod
    def update(user_id: str, update_data: dict):
        """Update user data"""
        try:
            client = get_admin_supabase()
            response = client.table('users').update(update_data).eq('id', user_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] update user: {str(e)}")
            raise


    @staticmethod
    def delete(user_id: str):
        """Delete user by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('users').delete().eq('id', user_id).execute()
            return True

        except Exception as e:
            print(f"[ERROR] delete user: {str(e)}")
            return False


    @staticmethod
    def get_all(limit: int = 100, offset: int = 0):
        """Get all users with pagination"""
        try:
            client = get_admin_supabase()
            response = client.table('users').select(
                'id, name, email, age, gender, role, is_active, created_at, last_login'
            ).order('created_at', desc=True).range(offset, offset + limit - 1).execute()

            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_all users: {str(e)}")
            return []


    @staticmethod
    def count():
        """Get total user count"""
        try:
            client = get_admin_supabase()
            response = client.table('users').select('id', count='exact').execute()
            return response.count or 0

        except Exception as e:
            print(f"[ERROR] count users: {str(e)}")
            return 0


# ============================================
# DOCTOR OPERATIONS
# ============================================
class DoctorDB:
    """Database operations for doctors table"""

    @staticmethod
    def get_all(filters: dict = None):
        """Get all doctors with optional filters"""
        try:
            client = get_admin_supabase()
            query = client.table('doctors').select('*')

            if filters:
                if filters.get('specialty'):
                    query = query.eq('specialty', filters['specialty'])
                if filters.get('location'):
                    query = query.eq('location', filters['location'])
                if 'available' in filters:
                    query = query.eq('available', filters['available'])

            response = query.order('rating', desc=True).execute()
            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_all doctors: {str(e)}")
            return []


    @staticmethod
    def get_by_id(doctor_id: str):
        """Get doctor by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').select('*').eq('id', doctor_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_id doctor: {str(e)}")
            return None


    @staticmethod
    def get_by_specialty(specialty: str, limit: int = 5):
        """Get doctors by specialty"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').select('*').eq(
                'specialty', specialty
            ).eq('available', True).order(
                'rating', desc=True
            ).limit(limit).execute()

            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_by_specialty: {str(e)}")
            return []


    @staticmethod
    def create(doctor_data: dict):
        """Create new doctor"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').insert(doctor_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] create doctor: {str(e)}")
            raise


    @staticmethod
    def update(doctor_id: str, update_data: dict):
        """Update doctor data"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').update(update_data).eq('id', doctor_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] update doctor: {str(e)}")
            raise


    @staticmethod
    def delete(doctor_id: str):
        """Delete doctor by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').delete().eq('id', doctor_id).execute()
            return True

        except Exception as e:
            print(f"[ERROR] delete doctor: {str(e)}")
            return False


    @staticmethod
    def count():
        """Get total doctor count"""
        try:
            client = get_admin_supabase()
            response = client.table('doctors').select('id', count='exact').execute()
            return response.count or 0

        except Exception as e:
            print(f"[ERROR] count doctors: {str(e)}")
            return 0


# ============================================
# SYMPTOM LOG OPERATIONS
# ============================================
class SymptomDB:
    """Database operations for symptoms_log table"""

    @staticmethod
    def create(symptom_data: dict):
        """Create new symptom log entry"""
        try:
            client = get_admin_supabase()
            response = client.table('symptoms_log').insert(symptom_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] create symptom: {str(e)}")
            raise


    @staticmethod
    def get_by_id(log_id: str):
        """Get symptom log by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('symptoms_log').select('*').eq('id', log_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_id symptom: {str(e)}")
            return None


    @staticmethod
    def get_user_history(user_id: str, limit: int = 10, offset: int = 0):
        """Get symptom history for a user"""
        try:
            client = get_admin_supabase()
            response = client.table('symptoms_log').select(
                '*'
            ).eq('user_id', user_id).order(
                'created_at', desc=True
            ).range(offset, offset + limit - 1).execute()

            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_user_history: {str(e)}")
            return []


    @staticmethod
    def delete(log_id: str):
        """Delete symptom log by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('symptoms_log').delete().eq('id', log_id).execute()
            return True

        except Exception as e:
            print(f"[ERROR] delete symptom: {str(e)}")
            return False


# ============================================
# DIAGNOSIS OPERATIONS
# ============================================
class DiagnosisDB:
    """Database operations for diagnoses table"""

    @staticmethod
    def create(diagnosis_data: dict):
        """Create new diagnosis entry"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').insert(diagnosis_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] create diagnosis: {str(e)}")
            raise


    @staticmethod
    def get_by_id(diagnosis_id: str):
        """Get diagnosis by ID"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').select('*').eq('id', diagnosis_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_id diagnosis: {str(e)}")
            return None


    @staticmethod
    def get_by_symptom_log(symptom_log_id: str):
        """Get diagnosis by symptom log ID"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').select('*').eq(
                'symptom_log_id', symptom_log_id
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] get_by_symptom_log: {str(e)}")
            return None


    @staticmethod
    def get_recent(limit: int = 10):
        """Get recent diagnoses"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').select(
                '*'
            ).order('created_at', desc=True).limit(limit).execute()

            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_recent diagnoses: {str(e)}")
            return []


    @staticmethod
    def get_severity_distribution():
        """Get count of diagnoses by severity"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').select('severity').execute()

            distribution = {
                'Low': 0,
                'Medium': 0,
                'High': 0,
                'Critical': 0
            }

            if response.data:
                for item in response.data:
                    sev = item.get('severity')
                    if sev in distribution:
                        distribution[sev] += 1

            return distribution

        except Exception as e:
            print(f"[ERROR] get_severity_distribution: {str(e)}")
            return {'Low': 0, 'Medium': 0, 'High': 0, 'Critical': 0}


    @staticmethod
    def count():
        """Get total diagnosis count"""
        try:
            client = get_admin_supabase()
            response = client.table('diagnoses').select('id', count='exact').execute()
            return response.count or 0

        except Exception as e:
            print(f"[ERROR] count diagnoses: {str(e)}")
            return 0


# ============================================
# RECOMMENDATION OPERATIONS
# ============================================
class RecommendationDB:
    """Database operations for recommendations table"""

    @staticmethod
    def create(recommendation_data: dict):
        """Create new recommendation"""
        try:
            client = get_admin_supabase()
            response = client.table('recommendations').insert(recommendation_data).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"[ERROR] create recommendation: {str(e)}")
            raise


    @staticmethod
    def get_by_diagnosis(diagnosis_id: str):
        """Get recommendations for a diagnosis"""
        try:
            client = get_admin_supabase()
            response = client.table('recommendations').select(
                '*, doctors(*)'
            ).eq('diagnosis_id', diagnosis_id).execute()

            return response.data or []

        except Exception as e:
            print(f"[ERROR] get_by_diagnosis: {str(e)}")
            return []


# ============================================
# STORAGE OPERATIONS
# ============================================
class StorageDB:
    """Database operations for Supabase Storage"""

    BUCKET_NAME = 'medical-images'


    @staticmethod
    def upload_image(file_path: str, file_data: bytes, content_type: str = 'image/jpeg'):
        """
        Upload image to Supabase Storage.

        Args:
            file_path: Path/name for the file in bucket
            file_data: Binary file data
            content_type: MIME type

        Returns:
            str: Public URL of uploaded image or None
        """
        try:
            client = get_admin_supabase()

            response = client.storage.from_(StorageDB.BUCKET_NAME).upload(
                path=file_path,
                file=file_data,
                file_options={
                    'content-type': content_type,
                    'upsert': 'true'
                }
            )

            # Get public URL
            url = client.storage.from_(StorageDB.BUCKET_NAME).get_public_url(file_path)
            return url

        except Exception as e:
            print(f"[ERROR] upload_image: {str(e)}")
            return None


    @staticmethod
    def delete_image(file_path: str):
        """Delete image from storage"""
        try:
            client = get_admin_supabase()
            response = client.storage.from_(StorageDB.BUCKET_NAME).remove([file_path])
            return True

        except Exception as e:
            print(f"[ERROR] delete_image: {str(e)}")
            return False


    @staticmethod
    def get_signed_url(file_path: str, expires_in: int = 3600):
        """Get signed URL for private image (expires after time)"""
        try:
            client = get_admin_supabase()
            response = client.storage.from_(StorageDB.BUCKET_NAME).create_signed_url(
                file_path,
                expires_in
            )
            return response.get('signedURL') if response else None

        except Exception as e:
            print(f"[ERROR] get_signed_url: {str(e)}")
            return None