"""
============================================
WEB SEARCH SERVICE
============================================
Searches medical information from the web using
DuckDuckGo and returns top relevant results.
"""

from duckduckgo_search import DDGS
from typing import List, Dict, Any, Optional


# ============================================
# WEB SEARCH SERVICE CLASS
# ============================================
class WebSearchService:
    """Service class for web-based medical information search"""

    # ============================================
    # CONFIGURATION
    # ============================================
    MAX_RESULTS = 10
    DEFAULT_RESULTS = 5
    TIMEOUT = 30

    # Trusted medical websites (prioritized)
    TRUSTED_MEDICAL_SITES = [
        'mayoclinic.org',
        'webmd.com',
        'nhs.uk',
        'medlineplus.gov',
        'healthline.com',
        'medicalnewstoday.com',
        'cdc.gov',
        'who.int',
        'clevelandclinic.org',
        'health.harvard.edu',
        'pubmed.ncbi.nlm.nih.gov',
        'merckmanuals.com',
        'familydoctor.org',
        'verywellhealth.com'
    ]

    # Search query templates
    QUERY_TEMPLATES = {
        'symptom': '{symptom} causes treatment medical condition',
        'disease': '{disease} symptoms causes treatment',
        'remedy': '{condition} home remedies natural treatment',
        'diet': '{condition} diet food recommendations',
        'general': '{query} medical health information'
    }


    # ============================================
    # MAIN SEARCH METHOD
    # ============================================
    @staticmethod
    def search_medical_info(
        query: str,
        max_results: int = 5,
        prefer_trusted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the web for medical information.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            prefer_trusted: Prioritize trusted medical sites

        Returns:
            List of search results with title, url, snippet
        """

        if not query or not query.strip():
            return []

        if max_results > WebSearchService.MAX_RESULTS:
            max_results = WebSearchService.MAX_RESULTS

        try:
            results = []

            # Build optimized query
            search_query = WebSearchService.build_search_query(query)

            # Perform search using DuckDuckGo
            with DDGS() as ddgs:
                search_results = list(ddgs.text(
                    keywords=search_query,
                    max_results=max_results * 2,
                    region='us-en',
                    safesearch='moderate'
                ))

            if not search_results:
                return []

            # Process results
            for result in search_results:
                processed = WebSearchService.process_result(result)
                if processed:
                    results.append(processed)

            # Prioritize trusted sites
            if prefer_trusted:
                results = WebSearchService.prioritize_trusted_sites(results)

            # Return top results
            return results[:max_results]

        except Exception as e:
            print(f"[WEB SEARCH ERROR] {str(e)}")
            return []


    # ============================================
    # SYMPTOM-BASED SEARCH
    # ============================================
    @staticmethod
    def search_symptoms(
        symptoms: str,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for symptom-related medical information.

        Args:
            symptoms: Symptoms description
            age: Patient age (optional)
            gender: Patient gender (optional)
            max_results: Max results to return

        Returns:
            List of relevant medical search results
        """

        if not symptoms:
            return []

        # Build context-aware query
        query_parts = [symptoms]

        if age:
            if age < 12:
                query_parts.append("in children")
            elif age >= 65:
                query_parts.append("in elderly")
            elif age >= 18:
                query_parts.append("in adults")

        query_parts.append("causes symptoms treatment")

        query = ' '.join(query_parts)

        return WebSearchService.search_medical_info(
            query=query,
            max_results=max_results,
            prefer_trusted=True
        )


    # ============================================
    # DISEASE-BASED SEARCH
    # ============================================
    @staticmethod
    def search_disease(
        disease_name: str,
        info_type: str = 'general',
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for specific disease information.

        Args:
            disease_name: Name of the disease
            info_type: Type of info (general/treatment/remedies/diet)
            max_results: Max results

        Returns:
            List of disease-related results
        """

        if not disease_name:
            return []

        # Build query based on info type
        query_map = {
            'general': f"{disease_name} symptoms causes treatment overview",
            'treatment': f"{disease_name} medical treatment options",
            'remedies': f"{disease_name} home remedies natural treatment",
            'diet': f"{disease_name} diet nutrition food recommendations",
            'prevention': f"{disease_name} prevention strategies",
            'complications': f"{disease_name} complications when to see doctor"
        }

        query = query_map.get(info_type, query_map['general'])

        return WebSearchService.search_medical_info(
            query=query,
            max_results=max_results
        )


    # ============================================
    # FOLLOW-UP QUESTION SEARCH
    # ============================================
    @staticmethod
    def search_followup(
        question: str,
        context: str = '',
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for answers to follow-up questions.

        Args:
            question: User's follow-up question
            context: Context (previous diagnosis/symptoms)
            max_results: Max results

        Returns:
            List of relevant results
        """

        if not question:
            return []

        # Combine question with context
        if context:
            query = f"{context} {question}"
        else:
            query = question

        # Add medical context
        query = f"{query} medical health information"

        return WebSearchService.search_medical_info(
            query=query,
            max_results=max_results
        )


    # ============================================
    # MULTI-QUERY SEARCH
    # ============================================
    @staticmethod
    def search_multiple(
        queries: List[str],
        results_per_query: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Perform multiple searches and combine results.

        Args:
            queries: List of search queries
            results_per_query: Results per individual query

        Returns:
            Combined deduplicated results
        """

        if not queries:
            return []

        all_results = []
        seen_urls = set()

        for query in queries:
            results = WebSearchService.search_medical_info(
                query=query,
                max_results=results_per_query
            )

            # Deduplicate by URL
            for result in results:
                url = result.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(result)

        return all_results


    # ============================================
    # BUILD SEARCH QUERY
    # ============================================
    @staticmethod
    def build_search_query(raw_query: str) -> str:
        """
        Build an optimized search query from raw input.

        Args:
            raw_query: Original user query

        Returns:
            Optimized search query string
        """

        if not raw_query:
            return ""

        # Clean the query
        query = raw_query.strip()

        # Remove common words that don't help search
        stop_words = ['i', 'have', 'a', 'an', 'the', 'is', 'are', 'was', 'were']
        words = query.split()
        meaningful_words = [
            w for w in words
            if w.lower() not in stop_words or len(meaningful_words := []) < 3
        ]

        if meaningful_words:
            query = ' '.join(meaningful_words)

        # Add medical context if not present
        medical_keywords = ['medical', 'health', 'symptom', 'treatment', 'disease', 'condition']
        has_medical_context = any(kw in query.lower() for kw in medical_keywords)

        if not has_medical_context:
            query += ' medical health'

        return query


    # ============================================
    # PROCESS SEARCH RESULT
    # ============================================
    @staticmethod
    def process_result(raw_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process and validate a single search result.

        Args:
            raw_result: Raw result from DuckDuckGo

        Returns:
            Processed result dictionary or None
        """

        if not raw_result:
            return None

        url = raw_result.get('href', '')
        title = raw_result.get('title', '')
        snippet = raw_result.get('body', '')

        if not url or not title:
            return None

        return {
            'title': title.strip(),
            'url': url.strip(),
            'snippet': snippet.strip() if snippet else '',
            'domain': WebSearchService.extract_domain(url),
            'is_trusted': WebSearchService.is_trusted_source(url)
        }


    # ============================================
    # EXTRACT DOMAIN
    # ============================================
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL"""

        if not url:
            return ''

        try:
            # Remove protocol
            domain = url.replace('https://', '').replace('http://', '')

            # Remove www
            domain = domain.replace('www.', '')

            # Get only domain part
            domain = domain.split('/')[0]

            return domain.lower()

        except Exception:
            return ''


    # ============================================
    # CHECK TRUSTED SOURCE
    # ============================================
    @staticmethod
    def is_trusted_source(url: str) -> bool:
        """Check if URL is from a trusted medical source"""

        if not url:
            return False

        domain = WebSearchService.extract_domain(url)

        return any(
            trusted in domain
            for trusted in WebSearchService.TRUSTED_MEDICAL_SITES
        )


    # ============================================
    # PRIORITIZE TRUSTED SITES
    # ============================================
    @staticmethod
    def prioritize_trusted_sites(
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Reorder results to prioritize trusted medical sites.

        Args:
            results: List of search results

        Returns:
            Reordered results with trusted sources first
        """

        if not results:
            return []

        trusted = [r for r in results if r.get('is_trusted')]
        untrusted = [r for r in results if not r.get('is_trusted')]

        return trusted + untrusted


    # ============================================
    # GET URLS FROM RESULTS
    # ============================================
    @staticmethod
    def get_urls(results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract URLs from search results.

        Args:
            results: List of search results

        Returns:
            List of URL strings
        """

        if not results:
            return []

        return [r.get('url', '') for r in results if r.get('url')]


    # ============================================
    # GET SNIPPETS FROM RESULTS
    # ============================================
    @staticmethod
    def get_snippets(results: List[Dict[str, Any]]) -> List[str]:
        """
        Extract text snippets from search results.

        Args:
            results: List of search results

        Returns:
            List of snippet strings
        """

        if not results:
            return []

        return [r.get('snippet', '') for r in results if r.get('snippet')]


    # ============================================
    # FORMAT RESULTS FOR DISPLAY
    # ============================================
    @staticmethod
    def format_results_for_display(
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Format search results for display or logging.

        Args:
            results: List of search results

        Returns:
            Formatted string
        """

        if not results:
            return "No results found."

        formatted = []

        for idx, result in enumerate(results, 1):
            trusted_marker = "[TRUSTED]" if result.get('is_trusted') else ""

            formatted.append(
                f"{idx}. {result.get('title', 'No title')} {trusted_marker}\n"
                f"   URL: {result.get('url', 'No URL')}\n"
                f"   {result.get('snippet', 'No snippet')[:150]}...\n"
            )

        return '\n'.join(formatted)


    # ============================================
    # GET SEARCH SUMMARY
    # ============================================
    @staticmethod
    def get_search_summary(
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get summary statistics of search results.

        Args:
            results: List of search results

        Returns:
            Summary dictionary
        """

        if not results:
            return {
                'total_results': 0,
                'trusted_sources': 0,
                'domains': []
            }

        domains = list(set([r.get('domain', '') for r in results if r.get('domain')]))
        trusted_count = sum(1 for r in results if r.get('is_trusted'))

        return {
            'total_results': len(results),
            'trusted_sources': trusted_count,
            'domains': domains,
            'trusted_percentage': round((trusted_count / len(results)) * 100, 1)
        }


    # ============================================
    # HEALTH CHECK
    # ============================================
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Check if web search service is operational.

        Returns:
            Health status dictionary
        """

        try:
            test_results = WebSearchService.search_medical_info(
                query="common cold",
                max_results=1
            )

            return {
                'success': True,
                'status': 'operational',
                'test_results_count': len(test_results),
                'service': 'DuckDuckGo'
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'service': 'DuckDuckGo'
            }