import sys
from bs4 import BeautifulSoup
import httpx
from urllib.parse import quote_plus, urlparse, unquote, parse_qs, quote

class DuckDuckGoClient():

	def __init__(self):

		pass

	def _extract_duckduckgo_url(self, redirect_url):
		"""Extract actual URL from DuckDuckGo redirect."""
		try:
			if 'uddg=' in redirect_url:
				parsed = urlparse(redirect_url if redirect_url.startswith('http') else 'https:' + redirect_url)
				params = parse_qs(parsed.query)
				if 'uddg' in params:
					return unquote(params['uddg'][0])
		except:
			pass
		return redirect_url
	
	def search_duckduckgo(self, query, num_results=10):
		"""Search DuckDuckGo for PDF results using the optimized query."""
		search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

		headers = {
		    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
		    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		    'Accept-Language': 'en-US,en;q=0.5',
		    'Accept-Encoding': 'gzip, deflate, br',
		    'DNT': '1',
		    'Connection': 'keep-alive',
		    'Upgrade-Insecure-Requests': '1'
		}

		pdf_links = []

		try:
			# Use POST instead of GET (DuckDuckGo prefers POST for HTML interface)
			with httpx.client(timeout=120) as client:
				response = client.post(
				    'https://html.duckduckgo.com/html/',
				    data={'q': query, 'b': '', 'kl': 'us-en'},
				    headers=headers,
				    timeout=15
				)

				# Check if we got a valid response
				if response.status_code == 202:
					# 202 means DuckDuckGo is processing - might be rate limiting
					# Fall back to GET method
					response = client.get(search_url, headers=headers, timeout=15)

			soup = BeautifulSoup(response.text, 'html.parser')

			# Try both possible result link classes
			result_links = soup.find_all('a', class_='result__url')
			if not result_links:
				result_links = soup.find_all('a', class_='result__a')

			for result in result_links:
				href = result.get('href', '')
				if '.pdf' in href.lower():
					actual_url = self._extract_duckduckgo_url(href)
					pdf_links.append(actual_url)
					if len(pdf_links) >= num_results:
						break

		except Exception as e:
			if '--verbose' in sys.argv or '-v' in sys.argv:
				print(f"DuckDuckGo search error: {e}", file=sys.stderr)

		return pdf_links