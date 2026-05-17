"""
============================================
CONTENT CLEANER SERVICE
============================================
Cleans and processes scraped web content for
optimal use with AI models.
"""

import re
import html2text
from typing import List, Dict, Any, Optional


# ============================================
# CONTENT CLEANER CLASS
# ============================================
class ContentCleaner:
    """Service class for cleaning and processing web content"""

    # ============================================
    # CONFIGURATION
    # ============================================
    MAX_SUMMARY_LENGTH = 500
    MAX_CHUNK_LENGTH = 2000
    MIN_SENTENCE_LENGTH = 20

    # Common junk phrases to remove
    JUNK_PHRASES = [
        'cookie policy',
        'privacy policy',
        'terms of service',
        'all rights reserved',
        'subscribe to our newsletter',
        'sign up for our newsletter',
        'follow us on',
        'share this article',
        'related articles',
        'recommended for you',
        'advertisement',
        'sponsored content',
        'click here to',
        'read more',
        'continue reading',
        'leave a comment',
        'comments are closed',
        'previous post',
        'next post',
        'about the author',
        'similar articles',
        'you may also like',
        'trending now',
        'popular articles',
        'top stories',
        'breaking news',
        'sign in to',
        'log in to',
        'create account',
        'forgot password',
        'newsletter signup',
        'email address',
        'first name',
        'last name'
    ]

    # Promotional/marketing phrases
    PROMO_PHRASES = [
        'buy now',
        'limited time offer',
        'special discount',
        'free shipping',
        'click to purchase',
        'order today',
        'get yours now',
        'available now',
        'on sale',
        'best price'
    ]

    # Sections to remove
    REMOVE_SECTIONS = [
        'comments',
        'footer',
        'header',
        'navigation',
        'sidebar',
        'related',
        'advertisement',
        'social',
        'newsletter'
    ]


    # ============================================
    # MAIN CLEAN METHOD
    # ============================================
    @staticmethod
    def clean_content(content: str) -> str:
        """
        Main method to clean web content.

        Args:
            content: Raw scraped content

        Returns:
            Cleaned content
        """

        if not content:
            return ""

        # Step 1: Remove HTML if any remains
        cleaned = ContentCleaner.remove_html_tags(content)

        # Step 2: Remove URLs
        cleaned = ContentCleaner.remove_urls(cleaned)

        # Step 3: Remove email addresses
        cleaned = ContentCleaner.remove_emails(cleaned)

        # Step 4: Remove phone numbers
        cleaned = ContentCleaner.remove_phone_numbers(cleaned)

        # Step 5: Remove junk phrases
        cleaned = ContentCleaner.remove_junk_phrases(cleaned)

        # Step 6: Remove promotional content
        cleaned = ContentCleaner.remove_promotional(cleaned)

        # Step 7: Remove excessive whitespace
        cleaned = ContentCleaner.normalize_whitespace(cleaned)

        # Step 8: Remove special characters (selective)
        cleaned = ContentCleaner.clean_special_chars(cleaned)

        # Step 9: Remove very short lines (likely navigation)
        cleaned = ContentCleaner.remove_short_lines(cleaned)

        return cleaned.strip()


    # ============================================
    # REMOVE HTML TAGS
    # ============================================
    @staticmethod
    def remove_html_tags(text: str) -> str:
        """Remove any remaining HTML tags"""

        if not text:
            return ""

        try:
            # Convert HTML to text
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.ignore_emphasis = True
            h.body_width = 0

            # Check if has HTML
            if '<' in text and '>' in text:
                return h.handle(text)

            # Fallback regex removal
            text = re.sub(r'<[^>]+>', '', text)

            return text

        except Exception as e:
            print(f"[HTML CLEAN ERROR] {str(e)}")
            return re.sub(r'<[^>]+>', '', text)


    # ============================================
    # REMOVE URLS
    # ============================================
    @staticmethod
    def remove_urls(text: str) -> str:
        """Remove URLs from text"""

        if not text:
            return ""

        # Remove http/https URLs
        text = re.sub(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            '',
            text
        )

        # Remove www URLs
        text = re.sub(r'www\.\S+', '', text)

        return text


    # ============================================
    # REMOVE EMAILS
    # ============================================
    @staticmethod
    def remove_emails(text: str) -> str:
        """Remove email addresses"""

        if not text:
            return ""

        return re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '',
            text
        )


    # ============================================
    # REMOVE PHONE NUMBERS
    # ============================================
    @staticmethod
    def remove_phone_numbers(text: str) -> str:
        """Remove phone numbers"""

        if not text:
            return ""

        # Various phone number patterns
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'
        ]

        for pattern in patterns:
            text = re.sub(pattern, '', text)

        return text


    # ============================================
    # REMOVE JUNK PHRASES
    # ============================================
    @staticmethod
    def remove_junk_phrases(text: str) -> str:
        """Remove common junk phrases"""

        if not text:
            return ""

        text_lower = text.lower()

        for phrase in ContentCleaner.JUNK_PHRASES:
            # Find phrase and remove the entire line containing it
            pattern = re.compile(
                r'^.*' + re.escape(phrase) + r'.*$',
                re.MULTILINE | re.IGNORECASE
            )
            text = pattern.sub('', text)

        return text


    # ============================================
    # REMOVE PROMOTIONAL CONTENT
    # ============================================
    @staticmethod
    def remove_promotional(text: str) -> str:
        """Remove promotional/marketing content"""

        if not text:
            return ""

        for phrase in ContentCleaner.PROMO_PHRASES:
            pattern = re.compile(
                r'^.*' + re.escape(phrase) + r'.*$',
                re.MULTILINE | re.IGNORECASE
            )
            text = pattern.sub('', text)

        return text


    # ============================================
    # NORMALIZE WHITESPACE
    # ============================================
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Clean up whitespace"""

        if not text:
            return ""

        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove tabs
        text = text.replace('\t', ' ')

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text


    # ============================================
    # CLEAN SPECIAL CHARACTERS
    # ============================================
    @staticmethod
    def clean_special_chars(text: str) -> str:
        """Clean special characters while preserving important punctuation"""

        if not text:
            return ""

        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)

        # Remove excessive special characters
        text = re.sub(r'[•·▪▫◦‣⁃]', '-', text)

        # Normalize quotes
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')

        # Remove excessive punctuation
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'-{4,}', '---', text)
        text = re.sub(r'={4,}', '===', text)

        return text


    # ============================================
    # REMOVE SHORT LINES
    # ============================================
    @staticmethod
    def remove_short_lines(text: str, min_length: int = 20) -> str:
        """Remove very short lines (likely navigation/menu)"""

        if not text:
            return ""

        lines = text.split('\n')
        meaningful_lines = []

        for line in lines:
            stripped = line.strip()

            # Keep if line is long enough
            if len(stripped) >= min_length:
                meaningful_lines.append(line)

            # Keep if line ends with punctuation (likely a sentence)
            elif stripped and stripped[-1] in '.!?:':
                meaningful_lines.append(line)

            # Keep paragraph breaks
            elif not stripped:
                meaningful_lines.append(line)

        return '\n'.join(meaningful_lines)


    # ============================================
    # SUMMARIZE CONTENT
    # ============================================
    @staticmethod
    def summarize_content(
        content: str,
        max_length: int = 500
    ) -> str:
        """
        Create a summary of content (extractive).

        Args:
            content: Cleaned content
            max_length: Maximum summary length

        Returns:
            Summary text
        """

        if not content:
            return ""

        # If already short, return as is
        if len(content) <= max_length:
            return content

        # Split into sentences
        sentences = ContentCleaner.split_into_sentences(content)

        if not sentences:
            return content[:max_length] + "..."

        # Take first few sentences that fit within max_length
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) > max_length:
                break
            summary += sentence + " "

        summary = summary.strip()

        if summary and not summary.endswith(('.', '!', '?')):
            summary += "..."

        return summary


    # ============================================
    # SPLIT INTO SENTENCES
    # ============================================
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences"""

        if not text:
            return []

        # Pattern for sentence splitting
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'

        sentences = re.split(sentence_pattern, text)

        # Filter out very short sentences
        meaningful_sentences = [
            s.strip() for s in sentences
            if len(s.strip()) >= ContentCleaner.MIN_SENTENCE_LENGTH
        ]

        return meaningful_sentences


    # ============================================
    # EXTRACT KEY SENTENCES
    # ============================================
    @staticmethod
    def extract_key_sentences(
        content: str,
        keywords: List[str],
        max_sentences: int = 10
    ) -> List[str]:
        """
        Extract sentences containing specific keywords.

        Args:
            content: Cleaned content
            keywords: List of keywords to search
            max_sentences: Maximum sentences to return

        Returns:
            List of key sentences
        """

        if not content or not keywords:
            return []

        sentences = ContentCleaner.split_into_sentences(content)
        key_sentences = []

        # Score sentences by keyword matches
        scored = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for kw in keywords if kw.lower() in sentence_lower)

            if score > 0:
                scored.append((score, sentence))

        # Sort by score and take top sentences
        scored.sort(key=lambda x: x[0], reverse=True)
        key_sentences = [s for _, s in scored[:max_sentences]]

        return key_sentences


    # ============================================
    # CLEAN AND SUMMARIZE BATCH
    # ============================================
    @staticmethod
    def clean_and_summarize_batch(
        scraped_results: List[Dict[str, Any]],
        summary_length: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Clean and summarize multiple scraped pages.

        Args:
            scraped_results: List of scraped results
            summary_length: Length per summary

        Returns:
            List of cleaned and summarized results
        """

        if not scraped_results:
            return []

        processed = []

        for result in scraped_results:
            try:
                content = result.get('content', '')

                if not content:
                    continue

                # Clean content
                cleaned = ContentCleaner.clean_content(content)

                if not cleaned or len(cleaned) < 100:
                    continue

                # Create summary
                summary = ContentCleaner.summarize_content(
                    cleaned,
                    max_length=summary_length
                )

                processed.append({
                    'url': result.get('url', ''),
                    'title': result.get('title', ''),
                    'cleaned_content': cleaned,
                    'summary': summary,
                    'word_count': len(cleaned.split()),
                    'is_trusted': result.get('is_trusted', False)
                })

            except Exception as e:
                print(f"[BATCH CLEAN ERROR] {str(e)}")
                continue

        return processed


    # ============================================
    # CHUNK CONTENT
    # ============================================
    @staticmethod
    def chunk_content(
        content: str,
        chunk_size: int = 2000,
        overlap: int = 200
    ) -> List[str]:
        """
        Split content into manageable chunks.

        Args:
            content: Full content
            chunk_size: Size of each chunk
            overlap: Character overlap between chunks

        Returns:
            List of content chunks
        """

        if not content:
            return []

        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence end within last 100 chars
                last_period = content.rfind('.', start, end)
                last_question = content.rfind('?', start, end)
                last_exclaim = content.rfind('!', start, end)

                last_sentence_end = max(last_period, last_question, last_exclaim)

                if last_sentence_end > start + chunk_size - 200:
                    end = last_sentence_end + 1

            chunk = content[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks


    # ============================================
    # EXTRACT MEDICAL TERMS
    # ============================================
    @staticmethod
    def extract_medical_terms(content: str) -> List[str]:
        """
        Extract potential medical terms from content.

        Args:
            content: Cleaned content

        Returns:
            List of medical terms found
        """

        if not content:
            return []

        # Common medical term patterns
        patterns = [
            r'\b[A-Z][a-z]+(?:itis|osis|emia|opathy|algia|ectomy|ostomy|otomy)\b',
            r'\b(?:syndrome|disease|disorder|infection|inflammation|cancer)\b',
            r'\b(?:diagnosis|prognosis|treatment|therapy|medication|prescription)\b',
            r'\b(?:symptom|sign|complication|side effect)\b'
        ]

        medical_terms = set()

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            medical_terms.update(matches)

        return list(medical_terms)


    # ============================================
    # PREPARE FOR AI
    # ============================================
    @staticmethod
    def prepare_for_ai(
        scraped_results: List[Dict[str, Any]],
        max_total_length: int = 8000
    ) -> str:
        """
        Prepare cleaned content for AI consumption.

        Args:
            scraped_results: List of scraped results
            max_total_length: Maximum total content length

        Returns:
            Formatted string ready for AI prompt
        """

        if not scraped_results:
            return ""

        # Clean and summarize
        processed = ContentCleaner.clean_and_summarize_batch(
            scraped_results,
            summary_length=800
        )

        if not processed:
            return ""

        # Format for AI
        ai_context = []
        current_length = 0

        for idx, item in enumerate(processed, 1):
            url = item.get('url', '')
            title = item.get('title', f'Source {idx}')
            summary = item.get('summary', '')
            trusted = " [TRUSTED MEDICAL SOURCE]" if item.get('is_trusted') else ""

            section = (
                f"\n--- Source {idx}: {title}{trusted} ---\n"
                f"URL: {url}\n"
                f"Content: {summary}\n"
            )

            if current_length + len(section) > max_total_length:
                break

            ai_context.append(section)
            current_length += len(section)

        return '\n'.join(ai_context)


    # ============================================
    # GET CLEAN STATISTICS
    # ============================================
    @staticmethod
    def get_clean_statistics(
        original: str,
        cleaned: str
    ) -> Dict[str, Any]:
        """
        Get statistics about cleaning operation.

        Args:
            original: Original content
            cleaned: Cleaned content

        Returns:
            Statistics dictionary
        """

        if not original:
            return {
                'original_length': 0,
                'cleaned_length': 0,
                'reduction_percent': 0
            }

        original_len = len(original)
        cleaned_len = len(cleaned) if cleaned else 0
        reduction = original_len - cleaned_len
        reduction_percent = round((reduction / original_len) * 100, 1) if original_len > 0 else 0

        return {
            'original_length': original_len,
            'cleaned_length': cleaned_len,
            'reduction': reduction,
            'reduction_percent': reduction_percent,
            'original_words': len(original.split()),
            'cleaned_words': len(cleaned.split()) if cleaned else 0
        }


    # ============================================
    # HEALTH CHECK
    # ============================================
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Check if content cleaner is working.

        Returns:
            Health status
        """

        try:
            test_content = """
            <html><body>
            <p>This is a test article about medical conditions.</p>
            <p>Click here to read more. Subscribe to our newsletter.</p>
            <p>The patient experienced symptoms including fever and headache.</p>
            <p>Visit https://example.com for more info or email contact@example.com</p>
            </body></html>
            """

            cleaned = ContentCleaner.clean_content(test_content)
            summary = ContentCleaner.summarize_content(cleaned, max_length=100)

            return {
                'success': True,
                'status': 'operational',
                'original_length': len(test_content),
                'cleaned_length': len(cleaned),
                'summary_length': len(summary)
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }