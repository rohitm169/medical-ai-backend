"""
============================================
MODELS PACKAGE
============================================
This package contains database models and connections
for the MedAI application.

Database: Supabase (PostgreSQL)

Models:
- database: Supabase client initialization and connection
"""

from models.database import (
    init_supabase,
    get_supabase,
    get_admin_supabase,
    test_connection,
    close_connection
)


# ============================================
# PACKAGE METADATA
# ============================================
__version__ = '1.0.0'
__author__ = 'MedAI Team'
__description__ = 'Database models and Supabase connection'


# ============================================
# DATABASE TABLES
# ============================================
TABLES = {
    'users': 'users',
    'sessions': 'user_sessions',
    'doctors': 'doctors',
    'symptoms': 'symptoms_log',
    'diagnoses': 'diagnoses',
    'recommendations': 'recommendations'
}


# ============================================
# STORAGE BUCKETS
# ============================================
BUCKETS = {
    'medical_images': 'medical-images'
}


# ============================================
# EXPORTED FUNCTIONS
# ============================================
__all__ = [
    'init_supabase',
    'get_supabase',
    'get_admin_supabase',
    'test_connection',
    'close_connection',
    'TABLES',
    'BUCKETS'
]