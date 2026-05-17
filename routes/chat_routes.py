"""
============================================
CHAT ROUTES
============================================
API endpoints for chat conversations with
web search integration and AI responses.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime

from middleware.auth_middleware import token_required
from services.chat_service import ChatService
from services.web_search_service import WebSearchService
from services.scraper_service import ScraperService
from services.content_cleaner import ContentCleaner
from services.gemini_service import GeminiService


# ============================================
# CREATE BLUEPRINT
# ============================================
chat_bp = Blueprint('chat', __name__)


# ============================================
# CONSTANTS
# ============================================
MIN_MESSAGE_LENGTH = 2
MAX_MESSAGE_LENGTH = 1000
MAX_WEB_RESULTS = 5
MAX_SCRAPE_RESULTS = 3


# ============================================
# CREATE OR GET SESSION
# ============================================
@chat_bp.route('/session', methods=['POST'])
@token_required
def create_or_get_session():
    """
    Create new chat session or get existing one for a diagnosis.

    Request Body:
    {
        "diagnosis_id": "uuid",
        "symptom_log_id": "uuid" (optional)
    }

    Returns:
        200: Session info
        400: Validation error
        500: Server error
    """

    try:
        data = request.get_json() or {}
        user_id = g.current_user_id

        diagnosis_id = data.get('diagnosis_id')
        symptom_log_id = data.get('symptom_log_id')

        # Check if session exists for this diagnosis
        existing_session = None
        if diagnosis_id:
            existing_session = ChatService.get_session_by_diagnosis(
                diagnosis_id=diagnosis_id,
                user_id=user_id
            )

        if existing_session:
            # Return existing session
            messages = ChatService.get_session_messages(
                session_id=existing_session['id']
            )

            return jsonify({
                'success': True,
                'session': existing_session,
                'messages': messages,
                'is_new': False
            }), 200

        # Create new session
        diagnosis_context = None
        title = "New Health Chat"

        if diagnosis_id:
            diagnosis_context = ChatService.get_diagnosis_context(diagnosis_id)

            if diagnosis_context and diagnosis_context.get('primary_disease'):
                title = f"Chat: {diagnosis_context['primary_disease']}"

        new_session = ChatService.create_session(
            user_id=user_id,
            diagnosis_id=diagnosis_id,
            symptom_log_id=symptom_log_id,
            title=title
        )

        if not new_session:
            return jsonify({
                'success': False,
                'message': 'Failed to create chat session'
            }), 500

        # Add welcome message
        welcome_message = generate_welcome_message(diagnosis_context)

        ChatService.add_message(
            session_id=new_session['id'],
            user_id=user_id,
            role='assistant',
            content=welcome_message
        )

        # Get suggested questions
        suggested_questions = ChatService.get_quick_questions(
            diagnosis_context=diagnosis_context
        )

        # Get fresh messages list
        messages = ChatService.get_session_messages(
            session_id=new_session['id']
        )

        return jsonify({
            'success': True,
            'session': new_session,
            'messages': messages,
            'suggested_questions': suggested_questions,
            'is_new': True
        }), 200

    except Exception as e:
        print(f"[CREATE SESSION ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create session',
            'error': str(e)
        }), 500


# ============================================
# SEND MESSAGE (WITH LANGUAGE SUPPORT)
# ============================================
@chat_bp.route('/message', methods=['POST'])
@token_required
def send_message():
    """
    Send a message and get AI response.

    Request Body:
    {
        "session_id": "uuid",
        "message": "user question",
        "use_web_search": true (optional, default: true),
        "language": "en" (optional, default: "en")
    }

    Returns:
        200: AI response
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

        user_id = g.current_user_id
        session_id = data.get('session_id')
        message = data.get('message', '').strip()
        use_web_search = data.get('use_web_search', True)
        language = data.get('language', 'en')

        # Validate language
        valid_languages = ['en', 'hi', 'bn', 'hinglish', 'benglish', 'auto']
        if language not in valid_languages:
            language = 'en'

        # Validate
        if not session_id:
            return jsonify({
                'success': False,
                'message': 'Session ID is required'
            }), 400

        if not message:
            return jsonify({
                'success': False,
                'message': 'Message is required'
            }), 400

        if len(message) < MIN_MESSAGE_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Message too short (min {MIN_MESSAGE_LENGTH} characters)'
            }), 400

        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                'success': False,
                'message': f'Message too long (max {MAX_MESSAGE_LENGTH} characters)'
            }), 400

        # Get session and verify ownership
        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to session'
            }), 403

        # Save user message
        user_message = ChatService.add_message(
            session_id=session_id,
            user_id=user_id,
            role='user',
            content=message
        )

        if not user_message:
            return jsonify({
                'success': False,
                'message': 'Failed to save message'
            }), 500

        # Get diagnosis context
        diagnosis_id = session.get('diagnosis_id')
        diagnosis_context = None

        if diagnosis_id:
            diagnosis_context = ChatService.get_diagnosis_context(diagnosis_id)

        # Get conversation history
        conversation_history = ChatService.get_conversation_context(
            session_id=session_id,
            max_messages=10
        )

        # Perform web search if enabled
        web_context = None
        web_sources = []

        if use_web_search:
            try:
                web_context, web_sources = perform_web_search(
                    query=message,
                    diagnosis_context=diagnosis_context
                )
            except Exception as e:
                print(f"[WEB SEARCH ERROR] {str(e)}")
                # Continue without web search

        # Build chat prompt
        prompt = ChatService.build_chat_prompt(
            user_question=message,
            diagnosis_context=diagnosis_context,
            conversation_history=conversation_history[:-1],
            web_context=web_context
        )

        # Get AI response with language support
        ai_response = GeminiService.chat_response(
            prompt=prompt,
            temperature=0.8,
            language=language
        )

        if not ai_response.get('success'):
            error_msg = ai_response.get('error', 'AI response failed')

            ChatService.add_message(
                session_id=session_id,
                user_id=user_id,
                role='assistant',
                content=f"I apologize, but I'm having trouble processing your question right now. Please try again. Error: {error_msg}"
            )

            return jsonify({
                'success': False,
                'message': 'AI response failed',
                'error': error_msg
            }), 500

        ai_content = ai_response.get('content', '')
        tokens_used = ai_response.get('tokens_used', 0)

        # Save AI message
        ai_message = ChatService.add_message(
            session_id=session_id,
            user_id=user_id,
            role='assistant',
            content=ai_content,
            web_sources=web_sources if web_sources else None,
            metadata={
                'tokens_used': tokens_used,
                'used_web_search': use_web_search,
                'language': language,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        return jsonify({
            'success': True,
            'user_message': user_message,
            'ai_message': ai_message,
            'web_sources': web_sources,
            'tokens_used': tokens_used,
            'language': language
        }), 200

    except Exception as e:
        print(f"[SEND MESSAGE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to send message',
            'error': str(e)
        }), 500


# ============================================
# GET SESSION MESSAGES
# ============================================
@chat_bp.route('/session/<session_id>/messages', methods=['GET'])
@token_required
def get_messages(session_id):
    """
    Get all messages in a chat session.

    Returns:
        200: List of messages
        404: Session not found
    """

    try:
        user_id = g.current_user_id

        # Verify session ownership
        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        # Get messages
        limit = int(request.args.get('limit', 50))
        order = request.args.get('order', 'asc')

        messages = ChatService.get_session_messages(
            session_id=session_id,
            limit=limit,
            order=order
        )

        return jsonify({
            'success': True,
            'session': session,
            'messages': messages,
            'count': len(messages)
        }), 200

    except Exception as e:
        print(f"[GET MESSAGES ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch messages',
            'error': str(e)
        }), 500


# ============================================
# GET USER SESSIONS
# ============================================
@chat_bp.route('/sessions', methods=['GET'])
@token_required
def get_user_sessions():
    """
    Get all chat sessions for current user.

    Returns:
        200: List of sessions
    """

    try:
        user_id = g.current_user_id

        limit = int(request.args.get('limit', 20))
        active_only = request.args.get('active_only', 'true').lower() == 'true'

        sessions = ChatService.get_user_sessions(
            user_id=user_id,
            limit=limit,
            active_only=active_only
        )

        # Add message count to each session
        for session in sessions:
            summary = ChatService.get_session_summary(session['id'])
            session['message_count'] = summary.get('message_count', 0)

        return jsonify({
            'success': True,
            'sessions': sessions,
            'count': len(sessions)
        }), 200

    except Exception as e:
        print(f"[GET SESSIONS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch sessions',
            'error': str(e)
        }), 500


# ============================================
# DELETE SESSION
# ============================================
@chat_bp.route('/session/<session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    """
    Delete a chat session and all messages.

    Returns:
        200: Deleted successfully
        404: Session not found
    """

    try:
        user_id = g.current_user_id

        # Verify ownership
        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        # Delete session
        success = ChatService.delete_session(session_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to delete session'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Chat session deleted'
        }), 200

    except Exception as e:
        print(f"[DELETE SESSION ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete session',
            'error': str(e)
        }), 500


# ============================================
# ARCHIVE SESSION
# ============================================
@chat_bp.route('/session/<session_id>/archive', methods=['POST'])
@token_required
def archive_session(session_id):
    """
    Archive a chat session (mark as inactive).

    Returns:
        200: Archived successfully
    """

    try:
        user_id = g.current_user_id

        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        success = ChatService.archive_session(session_id)

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to archive session'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Session archived'
        }), 200

    except Exception as e:
        print(f"[ARCHIVE ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to archive session',
            'error': str(e)
        }), 500


# ============================================
# GET SUGGESTED QUESTIONS
# ============================================
@chat_bp.route('/suggestions/<session_id>', methods=['GET'])
@token_required
def get_suggested_questions(session_id):
    """
    Get suggested follow-up questions for a session.

    Returns:
        200: List of suggested questions
    """

    try:
        user_id = g.current_user_id

        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        # Get diagnosis context
        diagnosis_id = session.get('diagnosis_id')
        diagnosis_context = None

        if diagnosis_id:
            diagnosis_context = ChatService.get_diagnosis_context(diagnosis_id)

        # Get suggestions
        suggestions = ChatService.get_quick_questions(
            diagnosis_context=diagnosis_context
        )

        return jsonify({
            'success': True,
            'suggestions': suggestions
        }), 200

    except Exception as e:
        print(f"[SUGGESTIONS ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get suggestions',
            'error': str(e)
        }), 500


# ============================================
# CLEAR SESSION MESSAGES
# ============================================
@chat_bp.route('/session/<session_id>/clear', methods=['POST'])
@token_required
def clear_session(session_id):
    """
    Clear all messages but keep session.

    Returns:
        200: Cleared successfully
    """

    try:
        user_id = g.current_user_id

        session = ChatService.get_session(session_id)

        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        if session.get('user_id') != user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized'
            }), 403

        # Delete and recreate session
        ChatService.delete_session(session_id)

        # Create new session with same diagnosis
        new_session = ChatService.create_session(
            user_id=user_id,
            diagnosis_id=session.get('diagnosis_id'),
            symptom_log_id=session.get('symptom_log_id'),
            title=session.get('title', 'Health Chat')
        )

        if not new_session:
            return jsonify({
                'success': False,
                'message': 'Failed to clear session'
            }), 500

        # Add welcome message
        diagnosis_context = None
        if session.get('diagnosis_id'):
            diagnosis_context = ChatService.get_diagnosis_context(
                session['diagnosis_id']
            )

        welcome_message = generate_welcome_message(diagnosis_context)

        ChatService.add_message(
            session_id=new_session['id'],
            user_id=user_id,
            role='assistant',
            content=welcome_message
        )

        messages = ChatService.get_session_messages(
            session_id=new_session['id']
        )

        return jsonify({
            'success': True,
            'session': new_session,
            'messages': messages
        }), 200

    except Exception as e:
        print(f"[CLEAR ERROR] {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to clear session',
            'error': str(e)
        }), 500


# ============================================
# HELPER FUNCTIONS
# ============================================
def perform_web_search(query, diagnosis_context=None):
    """
    Perform web search and prepare context for AI.

    Args:
        query: Search query
        diagnosis_context: Diagnosis information

    Returns:
        Tuple of (web_context, web_sources)
    """

    try:
        # Enhance query with disease context
        enhanced_query = query

        if diagnosis_context and diagnosis_context.get('primary_disease'):
            enhanced_query = f"{diagnosis_context['primary_disease']} {query}"

        # Search the web
        search_results = WebSearchService.search_medical_info(
            query=enhanced_query,
            max_results=MAX_WEB_RESULTS,
            prefer_trusted=True
        )

        if not search_results:
            return None, []

        # Get URLs
        urls = WebSearchService.get_urls(search_results)

        # Scrape top results
        scraped_results = ScraperService.scrape_multiple(
            urls=urls[:MAX_SCRAPE_RESULTS],
            max_results=MAX_SCRAPE_RESULTS,
            parallel=True
        )

        if not scraped_results:
            # Fallback: use search snippets
            snippets = []
            for result in search_results[:3]:
                snippet_text = (
                    f"Source: {result.get('title', 'Unknown')}\n"
                    f"URL: {result.get('url', '')}\n"
                    f"Summary: {result.get('snippet', '')}"
                )
                snippets.append(snippet_text)

            web_context = '\n\n'.join(snippets)

            web_sources = [
                {
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'is_trusted': r.get('is_trusted', False)
                }
                for r in search_results[:3]
            ]

            return web_context, web_sources

        # Add trust information to scraped results
        for scraped in scraped_results:
            for original in search_results:
                if scraped.get('url') == original.get('url'):
                    scraped['is_trusted'] = original.get('is_trusted', False)
                    break

        # Prepare for AI
        web_context = ContentCleaner.prepare_for_ai(
            scraped_results=scraped_results,
            max_total_length=6000
        )

        # Build sources list
        web_sources = [
            {
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'is_trusted': r.get('is_trusted', False)
            }
            for r in scraped_results
        ]

        return web_context, web_sources

    except Exception as e:
        print(f"[WEB SEARCH HELPER ERROR] {str(e)}")
        return None, []


def generate_welcome_message(diagnosis_context=None):
    """
    Generate a personalized welcome message.

    Args:
        diagnosis_context: Diagnosis information

    Returns:
        Welcome message string
    """

    if not diagnosis_context:
        return (
            "Hello! I'm your medical AI assistant. "
            "I'm here to answer any questions you have about your health. "
            "Feel free to ask me anything, and I'll provide helpful information "
            "based on the latest medical research.\n\n"
            "Please remember that I'm not a doctor, and my responses are for "
            "educational purposes only. Always consult a healthcare professional "
            "for medical advice."
        )

    primary_disease = diagnosis_context.get('primary_disease', 'your condition')
    severity = diagnosis_context.get('severity', '')

    message = f"Hello! I've reviewed your symptom analysis regarding **{primary_disease}**. "

    if severity:
        message += f"Your assessment indicates a **{severity}** severity level. "

    message += (
        "\n\nI'm here to answer any follow-up questions you may have. "
        "You can ask me about:\n\n"
        "• Causes and risk factors\n"
        "• Treatment options and home remedies\n"
        "• Diet and lifestyle recommendations\n"
        "• When to see a doctor\n"
        "• Prevention strategies\n"
        "• Any other concerns\n\n"
        "I'll search trusted medical sources to provide accurate, up-to-date information. "
        "What would you like to know?"
    )

    return message


# ============================================
# HEALTH CHECK
# ============================================
@chat_bp.route('/health', methods=['GET'])
def health_check():
    """Check chat service health"""

    try:
        chat_health = ChatService.health_check()
        search_health = WebSearchService.health_check()

        return jsonify({
            'success': True,
            'status': 'operational',
            'services': {
                'chat': chat_health,
                'web_search': search_health
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 500