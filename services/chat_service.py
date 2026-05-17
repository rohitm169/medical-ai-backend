"""
============================================
CHAT SERVICE
============================================
Manages chat sessions, conversation history,
and context for follow-up questions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from models.database import get_admin_supabase


# ============================================
# CHAT SERVICE CLASS
# ============================================
class ChatService:
    """Service class for chat conversation management"""

    # ============================================
    # CONFIGURATION
    # ============================================
    MAX_MESSAGES_PER_SESSION = 50
    MAX_CONTEXT_MESSAGES = 10
    MAX_MESSAGE_LENGTH = 2000
    DEFAULT_SESSION_LIMIT = 20


    # ============================================
    # CREATE CHAT SESSION
    # ============================================
    @staticmethod
    def create_session(
        user_id: str,
        diagnosis_id: Optional[str] = None,
        symptom_log_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new chat session.

        Args:
            user_id: User UUID
            diagnosis_id: Related diagnosis UUID (optional)
            symptom_log_id: Related symptom log UUID (optional)
            title: Session title (auto-generated if None)

        Returns:
            Created session dictionary or None
        """

        if not user_id:
            return None

        try:
            supabase = get_admin_supabase()

            # Auto-generate title if not provided
            if not title:
                title = f"Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

            session_data = {
                'user_id': str(user_id),
                'title': title,
                'is_active': True
            }

            if diagnosis_id:
                session_data['diagnosis_id'] = str(diagnosis_id)

            if symptom_log_id:
                session_data['symptom_log_id'] = str(symptom_log_id)

            response = supabase.table('chat_sessions').insert(
                session_data
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"[CREATE SESSION ERROR] {str(e)}")
            return None


    # ============================================
    # GET CHAT SESSION
    # ============================================
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chat session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session dictionary or None
        """

        if not session_id:
            return None

        try:
            supabase = get_admin_supabase()

            response = supabase.table('chat_sessions').select('*').eq(
                'id', str(session_id)
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"[GET SESSION ERROR] {str(e)}")
            return None


    # ============================================
    # GET USER SESSIONS
    # ============================================
    @staticmethod
    def get_user_sessions(
        user_id: str,
        limit: int = 20,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a user.

        Args:
            user_id: User UUID
            limit: Maximum sessions to return
            active_only: Only return active sessions

        Returns:
            List of session dictionaries
        """

        if not user_id:
            return []

        try:
            supabase = get_admin_supabase()

            query = supabase.table('chat_sessions').select('*').eq(
                'user_id', str(user_id)
            )

            if active_only:
                query = query.eq('is_active', True)

            response = query.order(
                'updated_at', desc=True
            ).limit(limit).execute()

            return response.data or []

        except Exception as e:
            print(f"[GET USER SESSIONS ERROR] {str(e)}")
            return []


    # ============================================
    # GET SESSION BY DIAGNOSIS
    # ============================================
    @staticmethod
    def get_session_by_diagnosis(
        diagnosis_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get existing session for a diagnosis.

        Args:
            diagnosis_id: Diagnosis UUID
            user_id: User UUID

        Returns:
            Session dictionary or None
        """

        if not diagnosis_id or not user_id:
            return None

        try:
            supabase = get_admin_supabase()

            response = supabase.table('chat_sessions').select('*').eq(
                'diagnosis_id', str(diagnosis_id)
            ).eq('user_id', str(user_id)).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"[GET SESSION BY DIAGNOSIS ERROR] {str(e)}")
            return None


    # ============================================
    # UPDATE SESSION
    # ============================================
    @staticmethod
    def update_session(
        session_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update session information.

        Args:
            session_id: Session UUID
            update_data: Fields to update

        Returns:
            Updated session or None
        """

        if not session_id or not update_data:
            return None

        try:
            supabase = get_admin_supabase()

            # Always update timestamp
            update_data['updated_at'] = datetime.utcnow().isoformat()

            response = supabase.table('chat_sessions').update(
                update_data
            ).eq('id', str(session_id)).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print(f"[UPDATE SESSION ERROR] {str(e)}")
            return None


    # ============================================
    # DELETE SESSION
    # ============================================
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete a chat session (and all its messages).

        Args:
            session_id: Session UUID

        Returns:
            True if successful
        """

        if not session_id:
            return False

        try:
            supabase = get_admin_supabase()

            supabase.table('chat_sessions').delete().eq(
                'id', str(session_id)
            ).execute()

            return True

        except Exception as e:
            print(f"[DELETE SESSION ERROR] {str(e)}")
            return False


    # ============================================
    # ADD MESSAGE
    # ============================================
    @staticmethod
    def add_message(
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        web_sources: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add a message to a chat session.

        Args:
            session_id: Session UUID
            user_id: User UUID
            role: 'user', 'assistant', or 'system'
            content: Message content
            web_sources: Web sources used (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created message or None
        """

        if not session_id or not user_id or not content:
            return None

        if role not in ['user', 'assistant', 'system']:
            return None

        # Validate content length
        if len(content) > ChatService.MAX_MESSAGE_LENGTH * 5:
            content = content[:ChatService.MAX_MESSAGE_LENGTH * 5]

        try:
            supabase = get_admin_supabase()

            message_data = {
                'session_id': str(session_id),
                'user_id': str(user_id),
                'role': role,
                'content': content
            }

            if web_sources:
                message_data['web_sources'] = web_sources

            if metadata:
                message_data['metadata'] = metadata

            response = supabase.table('chat_messages').insert(
                message_data
            ).execute()

            if response.data and len(response.data) > 0:
                # Update session timestamp
                ChatService.update_session(session_id, {})
                return response.data[0]

            return None

        except Exception as e:
            print(f"[ADD MESSAGE ERROR] {str(e)}")
            return None


    # ============================================
    # GET SESSION MESSAGES
    # ============================================
    @staticmethod
    def get_session_messages(
        session_id: str,
        limit: int = 50,
        order: str = 'asc'
    ) -> List[Dict[str, Any]]:
        """
        Get all messages in a session.

        Args:
            session_id: Session UUID
            limit: Maximum messages
            order: 'asc' or 'desc'

        Returns:
            List of messages
        """

        if not session_id:
            return []

        try:
            supabase = get_admin_supabase()

            response = supabase.table('chat_messages').select('*').eq(
                'session_id', str(session_id)
            ).order(
                'created_at',
                desc=(order == 'desc')
            ).limit(limit).execute()

            return response.data or []

        except Exception as e:
            print(f"[GET MESSAGES ERROR] {str(e)}")
            return []


    # ============================================
    # GET CONVERSATION CONTEXT
    # ============================================
    @staticmethod
    def get_conversation_context(
        session_id: str,
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get conversation context for AI (recent messages only).

        Args:
            session_id: Session UUID
            max_messages: Maximum messages to include

        Returns:
            List of formatted messages for AI context
        """

        if not session_id:
            return []

        try:
            messages = ChatService.get_session_messages(
                session_id=session_id,
                limit=max_messages,
                order='desc'
            )

            # Reverse to chronological order
            messages = list(reversed(messages))

            # Format for AI
            context = []
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')

                if content:
                    context.append({
                        'role': role,
                        'content': content
                    })

            return context

        except Exception as e:
            print(f"[GET CONTEXT ERROR] {str(e)}")
            return []


    # ============================================
    # GET DIAGNOSIS CONTEXT
    # ============================================
    @staticmethod
    def get_diagnosis_context(
        diagnosis_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get diagnosis information for chat context.

        Args:
            diagnosis_id: Diagnosis UUID

        Returns:
            Diagnosis context dictionary or None
        """

        if not diagnosis_id:
            return None

        try:
            supabase = get_admin_supabase()

            # Get diagnosis
            diag_response = supabase.table('diagnoses').select(
                '*'
            ).eq('id', str(diagnosis_id)).execute()

            if not diag_response.data or len(diag_response.data) == 0:
                return None

            diagnosis = diag_response.data[0]

            # Get related symptom log
            symptom_log_id = diagnosis.get('symptom_log_id')
            symptom_log = None

            if symptom_log_id:
                symp_response = supabase.table('symptoms_log').select(
                    '*'
                ).eq('id', str(symptom_log_id)).execute()

                if symp_response.data and len(symp_response.data) > 0:
                    symptom_log = symp_response.data[0]

            # Build context
            context = {
                'primary_disease': diagnosis.get('primary_disease', ''),
                'severity': diagnosis.get('severity', ''),
                'description': diagnosis.get('description', ''),
                'specialist_type': diagnosis.get('specialist_type', ''),
                'symptoms_text': symptom_log.get('symptoms_text', '') if symptom_log else '',
                'age': symptom_log.get('age') if symptom_log else None,
                'gender': symptom_log.get('gender') if symptom_log else None
            }

            # Add AI raw response for more context
            ai_data = diagnosis.get('ai_raw_response', {}) or {}
            if ai_data:
                context['detailed_explanation'] = ai_data.get('detailed_explanation', '')
                context['causes'] = ai_data.get('causes', [])
                context['warning_signs'] = ai_data.get('warning_signs', [])

            return context

        except Exception as e:
            print(f"[GET DIAGNOSIS CONTEXT ERROR] {str(e)}")
            return None


    # ============================================
    # GENERATE SESSION TITLE
    # ============================================
    @staticmethod
    def generate_session_title(
        first_message: str,
        max_length: int = 60
    ) -> str:
        """
        Generate a title from the first message.

        Args:
            first_message: First user message
            max_length: Maximum title length

        Returns:
            Generated title
        """

        if not first_message:
            return f"Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

        # Clean and truncate
        title = first_message.strip()

        # Remove newlines
        title = ' '.join(title.split())

        # Truncate
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + '...'

        return title


    # ============================================
    # BUILD CHAT PROMPT
    # ============================================
    @staticmethod
    def build_chat_prompt(
        user_question: str,
        diagnosis_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        web_context: Optional[str] = None
    ) -> str:
        """
        Build a comprehensive prompt for AI chat response.

        Args:
            user_question: Current user question
            diagnosis_context: Original diagnosis info
            conversation_history: Previous messages
            web_context: Web search context

        Returns:
            Complete prompt for AI
        """

        prompt_parts = []

        # System role
        prompt_parts.append(
            "You are a knowledgeable medical AI assistant having a conversation with a patient. "
            "Provide helpful, accurate, and empathetic responses. "
            "Remember: You are NOT a doctor and cannot diagnose. "
            "Always recommend professional medical consultation for serious concerns."
        )

        # Add diagnosis context
        if diagnosis_context:
            prompt_parts.append("\n=== PATIENT'S CONDITION ===")

            if diagnosis_context.get('primary_disease'):
                prompt_parts.append(
                    f"Initial Assessment: {diagnosis_context['primary_disease']}"
                )

            if diagnosis_context.get('severity'):
                prompt_parts.append(
                    f"Severity Level: {diagnosis_context['severity']}"
                )

            if diagnosis_context.get('symptoms_text'):
                prompt_parts.append(
                    f"Original Symptoms: {diagnosis_context['symptoms_text']}"
                )

            if diagnosis_context.get('age'):
                prompt_parts.append(
                    f"Patient Age: {diagnosis_context['age']} years"
                )

            if diagnosis_context.get('gender'):
                prompt_parts.append(
                    f"Patient Gender: {diagnosis_context['gender']}"
                )

        # Add web search context
        if web_context:
            prompt_parts.append("\n=== LATEST MEDICAL INFORMATION FROM WEB ===")
            prompt_parts.append(web_context)
            prompt_parts.append("\nUse this information to provide accurate, up-to-date answers.")

        # Add conversation history
        if conversation_history and len(conversation_history) > 0:
            prompt_parts.append("\n=== PREVIOUS CONVERSATION ===")

            for msg in conversation_history[-6:]:  # Last 6 messages
                role = msg.get('role', 'user')
                content = msg.get('content', '')

                if role == 'user':
                    prompt_parts.append(f"\nPatient: {content}")
                elif role == 'assistant':
                    prompt_parts.append(f"\nAssistant: {content[:300]}...")

        # Current question
        prompt_parts.append("\n=== CURRENT QUESTION ===")
        prompt_parts.append(f"Patient: {user_question}")

        # Instructions
        prompt_parts.append(
            "\n=== INSTRUCTIONS ==="
            "\nProvide a helpful response that:"
            "\n1. Directly answers the patient's question"
            "\n2. Uses the medical context provided"
            "\n3. References web information when relevant"
            "\n4. Is empathetic and clear"
            "\n5. Recommends professional consultation when needed"
            "\n6. Is well-structured and easy to read"
            "\n7. Includes specific, actionable advice"
            "\n8. Cites sources if web information is used"
            "\n\nProvide your response now:"
        )

        return '\n'.join(prompt_parts)


    # ============================================
    # GET SESSION SUMMARY
    # ============================================
    @staticmethod
    def get_session_summary(session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics of a chat session.

        Args:
            session_id: Session UUID

        Returns:
            Summary dictionary
        """

        if not session_id:
            return {
                'message_count': 0,
                'user_messages': 0,
                'assistant_messages': 0
            }

        try:
            messages = ChatService.get_session_messages(session_id, limit=1000)

            user_count = sum(1 for m in messages if m.get('role') == 'user')
            assistant_count = sum(1 for m in messages if m.get('role') == 'assistant')

            return {
                'message_count': len(messages),
                'user_messages': user_count,
                'assistant_messages': assistant_count,
                'has_web_sources': any(
                    m.get('web_sources') for m in messages
                )
            }

        except Exception as e:
            print(f"[SESSION SUMMARY ERROR] {str(e)}")
            return {
                'message_count': 0,
                'user_messages': 0,
                'assistant_messages': 0
            }


    # ============================================
    # ARCHIVE SESSION
    # ============================================
    @staticmethod
    def archive_session(session_id: str) -> bool:
        """
        Archive a chat session (mark as inactive).

        Args:
            session_id: Session UUID

        Returns:
            True if successful
        """

        if not session_id:
            return False

        try:
            result = ChatService.update_session(
                session_id=session_id,
                update_data={'is_active': False}
            )

            return result is not None

        except Exception as e:
            print(f"[ARCHIVE ERROR] {str(e)}")
            return False


    # ============================================
    # GET RECENT QUESTIONS
    # ============================================
    @staticmethod
    def get_quick_questions(
        diagnosis_context: Optional[Dict] = None
    ) -> List[str]:
        """
        Generate quick question suggestions for users.

        Args:
            diagnosis_context: Diagnosis info for personalized questions

        Returns:
            List of suggested questions
        """

        default_questions = [
            "Why is this happening to me?",
            "How long will it take to recover?",
            "What foods should I eat?",
            "What should I avoid?",
            "When should I see a doctor?",
            "Can I continue my daily activities?",
            "Is this condition contagious?",
            "What medications can help?",
            "How can I prevent this in the future?",
            "Are there any complications I should worry about?"
        ]

        if not diagnosis_context:
            return default_questions[:6]

        # Personalized questions based on diagnosis
        disease = diagnosis_context.get('primary_disease', '')
        severity = diagnosis_context.get('severity', '')

        personalized = []

        if disease:
            personalized.extend([
                f"What causes {disease}?",
                f"How is {disease} typically treated?",
                f"What are the best home remedies for {disease}?",
                f"Are there any natural treatments for {disease}?"
            ])

        if severity == 'High' or severity == 'Critical':
            personalized.append("When should I go to the emergency room?")
            personalized.append("What are the warning signs I should watch for?")

        # Combine and return
        all_questions = personalized + default_questions
        return all_questions[:6]


    # ============================================
    # HEALTH CHECK
    # ============================================
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Check if chat service is operational.

        Returns:
            Health status
        """

        try:
            supabase = get_admin_supabase()

            # Test session count
            response = supabase.table('chat_sessions').select(
                'id', count='exact'
            ).execute()

            session_count = response.count or 0

            # Test message count
            msg_response = supabase.table('chat_messages').select(
                'id', count='exact'
            ).execute()

            message_count = msg_response.count or 0

            return {
                'success': True,
                'status': 'operational',
                'total_sessions': session_count,
                'total_messages': message_count
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }