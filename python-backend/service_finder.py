#!/usr/bin/env python3
"""
Exa.ai Service Search Tool
Searches for supplier service and capability pages.
"""

import os
import sys
from typing import Optional, List
import click
from exa_py import Exa
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ServiceFinder:
    """Search for supplier service and capability pages using Exa API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the service finder.

        Args:
            api_key: Exa API key. If not provided, will look for EXA_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('EXA_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Exa API key not found. Please set EXA_API_KEY environment variable "
                "or pass it as an argument."
            )
        self.exa = Exa(api_key=self.api_key)

    def search_services(
        self,
        query: str,
        supplier_name: Optional[str] = None,
        num_results: int = 10
    ) -> List[dict]:
        """
        Search for supplier service and capability pages.

        Args:
            query: Search query (e.g., "CNC machining", "injection molding")
            supplier_name: Optional supplier name to narrow search
            num_results: Number of results to return (default: 10)

        Returns:
            List of search results with URLs and metadata
        """
        # Build query targeting service/capability pages
        query_parts = []

        if supplier_name:
            query_parts.append(supplier_name)

        query_parts.append(query)
        query_parts.append("capabilities services manufacturing")

        # Target pages that describe services, not product datasheets
        search_query = " ".join(query_parts)

        print(f"\nSearching for services: {search_query}")

        try:
            # Search for HTML pages about services/capabilities
            # Use "auto" type to let Exa determine best search method
            results = self.exa.search(
                search_query,
                type="auto",
                num_results=num_results,
                # Exclude PDFs to focus on service pages
                exclude_domains=[]  # Can add specific domains to exclude if needed
            )

            # Filter results to prioritize service/capability pages
            filtered_results = []
            for result in results.results:
                # Look for service-related keywords in URL or title
                url_lower = result.url.lower()
                title_lower = result.title.lower()

                service_keywords = [
                    'services', 'capabilities', 'about', 'manufacturing',
                    'products', 'solutions', 'what-we-do', 'expertise'
                ]

                # Check if URL or title contains service keywords
                is_service_page = any(
                    keyword in url_lower or keyword in title_lower
                    for keyword in service_keywords
                )

                # Exclude PDFs
                is_pdf = url_lower.endswith('.pdf')

                if not is_pdf:
                    filtered_results.append({
                        'title': result.title,
                        'url': result.url,
                        'score': getattr(result, 'score', None),
                        'is_likely_service_page': is_service_page
                    })

            # Sort by relevance (service pages first, then by score)
            filtered_results.sort(
                key=lambda x: (x['is_likely_service_page'], x['score'] or 0),
                reverse=True
            )

            return filtered_results

        except Exception as e:
            raise Exception(f"Error searching for services: {str(e)}")


@click.group()
def cli():
    """Exa.ai Service Search Tool"""
    pass


@cli.command()
@click.argument('query')
@click.option('--supplier', '-s', help='Supplier name to narrow search')
@click.option('--num-results', '-n', default=10, help='Number of results to return (default: 10)')
@click.option('--api-key', '-k', envvar='EXA_API_KEY', help='Exa API key (or set EXA_API_KEY env var)')
def search(query: str, supplier: Optional[str], num_results: int, api_key: Optional[str]):
    """
    Search for supplier services and capabilities.

    Example:
        python service_finder.py search "CNC machining services"
        python service_finder.py search "injection molding" --supplier "ProtoLabs"
    """
    try:
        finder = ServiceFinder(api_key=api_key)

        results = finder.search_services(
            query=query,
            supplier_name=supplier,
            num_results=num_results
        )

        if not results:
            click.echo("No results found.")
            return

        click.echo(f"\nFound {len(results)} result(s):\n")

        for i, result in enumerate(results, 1):
            service_indicator = " [SERVICE PAGE]" if result['is_likely_service_page'] else ""
            click.echo(f"{i}. {result['title']}{service_indicator}")
            click.echo(f"   URL: {result['url']}")
            if result.get('score'):
                click.echo(f"   Score: {result['score']:.4f}")
            click.echo()

    except ValueError as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo("\nPlease set your Exa API key:")
        click.echo("  export EXA_API_KEY='your-api-key-here'")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def test():
    """Test the connection to Exa API."""
    try:
        api_key = os.getenv('EXA_API_KEY')
        if not api_key:
            click.echo("Error: EXA_API_KEY not set", err=True)
            sys.exit(1)

        finder = ServiceFinder(api_key=api_key)
        click.echo("Testing connection to Exa API...")

        results = finder.search_services("CNC machining", num_results=3)

        click.echo("Connection successful!")
        if results:
            click.echo(f"Test search returned {len(results)} result(s)")
        else:
            click.echo("Connection works, but test search returned no results")

    except Exception as e:
        click.echo(f"Connection test failed: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
