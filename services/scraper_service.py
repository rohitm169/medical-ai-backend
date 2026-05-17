"""
============================================
WEB SCRAPER SERVICE
============================================
Scrapes content from web URLs and extracts
clean, readable medical information.
"""

import requests
import trafilatura
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


# ============================================
# SCRAPER SERVICE CLASS
# ============================================
class ScraperService:
    """Service class for web scraping medical content"""

    # ============================================
    # CONFIGURATION
    # ============================================
    REQUEST_TIMEOUT = 15
    MAX_CONTENT_LENGTH = 10000
    MIN_CONTENT_LENGTH = 100
    MAX_PARALLEL_REQUESTS = 5

    # User agent to avoid blocks
    USER_AGENT = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )

    # Headers for requests
    DEFAULT_HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # Sites to skip (require login/paywall)
    SKIP_DOMAINS = [
        'sciencedirect.com',
        'nature.com',
        'springer.com',
        'wiley.com',
        'jstor.org'
    ]


    # ============================================
    # MAIN SCRAPE METHOD
    # ============================================
    @staticmethod
    def scrape_url(url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape content from a single URL.

        Args:
            url: URL to scrape

        Returns:
            Dictionary with scraped content or None
        """

        if not url or not ScraperService.is_valid_url(url):
            return None

        # Skip paywalled sites
        if ScraperService.should_skip_url(url):
            return None

        try:
            # Fetch the page
            response = requests.get(
                url,
                headers=ScraperService.DEFAULT_HEADERS,
                timeout=ScraperService.REQUEST_TIMEOUT,
                allow_redirects=True
            )

            if response.status_code != 200:
                return None

            html_content = response.text

            if not html_content:
                return None

            # Extract content using trafilatura (best for articles)
            extracted = ScraperService.extract_with_trafilatura(html_content)

            # Fallback to BeautifulSoup if trafilatura fails
            if not extracted or len(extracted) < ScraperService.MIN_CONTENT_LENGTH:
                extracted = ScraperService.extract_with_bs4(html_content)

            if not extracted or len(extracted) < ScraperService.MIN_CONTENT_LENGTH:
                return None

            # Get metadata
            metadata = ScraperService.extract_metadata(html_content, url)

            # Truncate if too long
            if len(extracted) > ScraperService.MAX_CONTENT_LENGTH:
                extracted = extracted[:ScraperService.MAX_CONTENT_LENGTH] + "..."

            return {
                'url': url,
                'content': extracted,
                'title': metadata.get('title', ''),
                'description': metadata.get('description', ''),
                'word_count': len(extracted.split()),
                'success': True
            }

        except requests.exceptions.Timeout:
            print(f"[SCRAPER TIMEOUT] {url}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"[SCRAPER REQUEST ERROR] {url}: {str(e)}")
            return None

        except Exception as e:
            print(f"[SCRAPER ERROR] {url}: {str(e)}")
            return None


    # ============================================
    # BATCH SCRAPE METHOD
    # ============================================
    @staticmethod
    def scrape_multiple(
        urls: List[str],
        max_results: int = 5,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            max_results: Maximum successful results to return
            parallel: Use parallel scraping (faster)

        Returns:
            List of successfully scraped content
        """

        if not urls:
            return []

        results = []

        if parallel:
            # Parallel scraping (faster)
            with ThreadPoolExecutor(
                max_workers=ScraperService.MAX_PARALLEL_REQUESTS
            ) as executor:

                # Submit all scraping tasks
                future_to_url = {
                    executor.submit(ScraperService.scrape_url, url): url
                    for url in urls[:max_results * 2]
                }

                # Collect results as they complete
                for future in as_completed(future_to_url):
                    url = future_to_url[future]

                    try:
                        result = future.result(
                            timeout=ScraperService.REQUEST_TIMEOUT + 5
                        )

                        if result and result.get('success'):
                            results.append(result)

                        if len(results) >= max_results:
                            break

                    except Exception as e:
                        print(f"[BATCH SCRAPER ERROR] {url}: {str(e)}")
                        continue

        else:
            # Sequential scraping (slower but more stable)
            for url in urls[:max_results * 2]:
                if len(results) >= max_results:
                    break

                result = ScraperService.scrape_url(url)

                if result and result.get('success'):
                    results.append(result)

                # Small delay between requests
                time.sleep(0.5)

        return results


    # ============================================
    # EXTRACT WITH TRAFILATURA
    # ============================================
    @staticmethod
    def extract_with_trafilatura(html_content: str) -> Optional[str]:
        """
        Extract main content using trafilatura.
        Best for article/blog extraction.

        Args:
            html_content: Raw HTML

        Returns:
            Extracted text or None
        """

        if not html_content:
            return None

        try:
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_links=False,
                include_images=False,
                deduplicate=True,
                favor_recall=True
            )

            return extracted

        except Exception as e:
            print(f"[TRAFILATURA ERROR] {str(e)}")
            return None


    # ============================================
    # EXTRACT WITH BEAUTIFULSOUP
    # ============================================
    @staticmethod
    def extract_with_bs4(html_content: str) -> Optional[str]:
        """
        Fallback extraction using BeautifulSoup.

        Args:
            html_content: Raw HTML

        Returns:
            Extracted text or None
        """

        if not html_content:
            return None

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # Remove unwanted elements
            unwanted_tags = [
                'script', 'style', 'nav', 'footer', 'header',
                'aside', 'form', 'button', 'iframe', 'noscript'
            ]

            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            # Try to find main content area
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', {'class': ['content', 'main-content', 'article-content']}) or
                soup.find('div', {'id': ['content', 'main', 'main-content']}) or
                soup.body
            )

            if not main_content:
                return None

            # Extract text
            text = main_content.get_text(separator='\n', strip=True)

            # Clean up
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned = '\n'.join(lines)

            return cleaned

        except Exception as e:
            print(f"[BS4 ERROR] {str(e)}")
            return None


    # ============================================
    # EXTRACT METADATA
    # ============================================
    @staticmethod
    def extract_metadata(html_content: str, url: str) -> Dict[str, str]:
        """
        Extract metadata from HTML (title, description, etc.).

        Args:
            html_content: Raw HTML
            url: Source URL

        Returns:
            Dictionary with metadata
        """

        metadata = {
            'title': '',
            'description': '',
            'author': '',
            'published_date': ''
        }

        if not html_content:
            return metadata

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # Title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text(strip=True)[:200]

            # Open Graph title (fallback)
            if not metadata['title']:
                og_title = soup.find('meta', {'property': 'og:title'})
                if og_title:
                    metadata['title'] = og_title.get('content', '')[:200]

            # Description
            desc_tag = soup.find('meta', {'name': 'description'})
            if desc_tag:
                metadata['description'] = desc_tag.get('content', '')[:500]

            # Open Graph description (fallback)
            if not metadata['description']:
                og_desc = soup.find('meta', {'property': 'og:description'})
                if og_desc:
                    metadata['description'] = og_desc.get('content', '')[:500]

            # Author
            author_tag = soup.find('meta', {'name': 'author'})
            if author_tag:
                metadata['author'] = author_tag.get('content', '')[:100]

            # Published date
            date_tag = (
                soup.find('meta', {'property': 'article:published_time'}) or
                soup.find('meta', {'name': 'publish-date'}) or
                soup.find('meta', {'name': 'date'})
            )
            if date_tag:
                metadata['published_date'] = date_tag.get('content', '')[:50]

        except Exception as e:
            print(f"[METADATA ERROR] {str(e)}")

        return metadata


    # ============================================
    # CHECK VALID URL
    # ============================================
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        Check if URL is valid for scraping.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """

        if not url or not isinstance(url, str):
            return False

        # Basic URL validation
        if not (url.startswith('http://') or url.startswith('https://')):
            return False

        # Check for valid structure
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)

            if not parsed.netloc:
                return False

            return True

        except Exception:
            return False


    # ============================================
    # CHECK SKIP URL
    # ============================================
    @staticmethod
    def should_skip_url(url: str) -> bool:
        """
        Check if URL should be skipped (paywalled, etc.).

        Args:
            url: URL to check

        Returns:
            True if should skip
        """

        if not url:
            return True

        url_lower = url.lower()

        for skip_domain in ScraperService.SKIP_DOMAINS:
            if skip_domain in url_lower:
                return True

        # Skip non-HTML resources
        skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip']
        for ext in skip_extensions:
            if url_lower.endswith(ext):
                return True

        return False


    # ============================================
    # SCRAPE WITH RETRY
    # ============================================
    @staticmethod
    def scrape_with_retry(
        url: str,
        max_retries: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape URL with retry logic.

        Args:
            url: URL to scrape
            max_retries: Maximum retry attempts

        Returns:
            Scraped content or None
        """

        for attempt in range(max_retries + 1):
            try:
                result = ScraperService.scrape_url(url)

                if result and result.get('success'):
                    return result

                # Wait before retry
                if attempt < max_retries:
                    time.sleep(1)

            except Exception as e:
                print(f"[RETRY ERROR] Attempt {attempt + 1}: {str(e)}")

                if attempt < max_retries:
                    time.sleep(2)

        return None


    # ============================================
    # GET CONTENT SUMMARY
    # ============================================
    @staticmethod
    def get_content_summary(
        scraped_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get summary of scraped content.

        Args:
            scraped_results: List of scraped results

        Returns:
            Summary dictionary
        """

        if not scraped_results:
            return {
                'total_pages': 0,
                'total_words': 0,
                'average_words': 0,
                'sources': []
            }

        total_words = sum(r.get('word_count', 0) for r in scraped_results)
        sources = [r.get('url', '') for r in scraped_results]

        return {
            'total_pages': len(scraped_results),
            'total_words': total_words,
            'average_words': total_words // len(scraped_results) if scraped_results else 0,
            'sources': sources,
            'success_rate': 100.0
        }


    # ============================================
    # COMBINE CONTENT FROM MULTIPLE PAGES
    # ============================================
    @staticmethod
    def combine_content(
        scraped_results: List[Dict[str, Any]],
        max_total_length: int = 15000
    ) -> str:
        """
        Combine content from multiple scraped pages.

        Args:
            scraped_results: List of scraped results
            max_total_length: Maximum total length

        Returns:
            Combined text content
        """

        if not scraped_results:
            return ""

        combined = []
        current_length = 0

        for idx, result in enumerate(scraped_results, 1):
            content = result.get('content', '')
            title = result.get('title', f'Source {idx}')
            url = result.get('url', '')

            if not content:
                continue

            # Format with source attribution
            section = f"\n\n=== Source {idx}: {title} ===\nURL: {url}\n\n{content}\n"

            if current_length + len(section) > max_total_length:
                # Truncate to fit
                remaining = max_total_length - current_length
                if remaining > 200:
                    section = section[:remaining] + "..."
                    combined.append(section)
                break

            combined.append(section)
            current_length += len(section)

        return '\n'.join(combined)


    # ============================================
    # HEALTH CHECK
    # ============================================
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Check if scraper service is operational.

        Returns:
            Health status
        """

        try:
            # Test with a reliable URL
            test_url = "https://www.mayoclinic.org/diseases-conditions/common-cold/symptoms-causes/syc-20351605"

            result = ScraperService.scrape_url(test_url)

            if result and result.get('success'):
                return {
                    'success': True,
                    'status': 'operational',
                    'test_word_count': result.get('word_count', 0)
                }

            return {
                'success': False,
                'status': 'no_content',
                'error': 'Could not extract content'
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }