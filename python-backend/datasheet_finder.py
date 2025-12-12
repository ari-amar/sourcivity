#!/usr/bin/env python3
"""
Exa.ai Simple Search Tool
Bare bones search with no filtering.
"""

import os
import sys
from typing import Optional, List
import click
from exa_py import Exa
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatasheetFinder:
    """Simple search using Exa API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the finder.

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

    def search_datasheet(
        self,
        component_name: str,
        manufacturer: Optional[str] = None,
        num_results: int = 10
    ) -> List[dict]:
        """
        Simple search for component datasheets.

        Args:
            component_name: Name or part number of the component
            manufacturer: Optional manufacturer name to narrow search
            num_results: Number of results to return (default: 10)

        Returns:
            List of search results with URLs and metadata
        """
        # Build simple query
        query_parts = [component_name]
        if manufacturer:
            query_parts.append(manufacturer)
        query_parts.append("datasheet filetype:pdf")

        query = " ".join(query_parts)

        print(f"\nSearching: {query}")

        try:
            # Simple search without contents (saves credits)
            results = self.exa.search(
                query,
                type="auto",
                num_results=num_results
            )

            # Return all results without filtering
            all_results = []
            for result in results.results:
                all_results.append({
                    'title': result.title,
                    'url': result.url,
                    'score': getattr(result, 'score', None)
                })

            return all_results

        except Exception as e:
            raise Exception(f"Error searching: {str(e)}")


@click.group()
def cli():
    """Exa.ai Simple Search Tool"""
    pass


@cli.command()
@click.argument('component_name')
@click.option('--manufacturer', '-m', help='Manufacturer name to narrow search')
@click.option('--num-results', '-n', default=10, help='Number of results to return (default: 10)')
@click.option('--api-key', '-k', envvar='EXA_API_KEY', help='Exa API key (or set EXA_API_KEY env var)')
def search(component_name: str, manufacturer: Optional[str], num_results: int, api_key: Optional[str]):
    """
    Simple search with no filtering.

    Example:
        python datasheet_finder.py search "mass flow controller"
        python datasheet_finder.py search LM358 --manufacturer "Texas Instruments"
    """
    try:
        finder = DatasheetFinder(api_key=api_key)

        results = finder.search_datasheet(
            component_name=component_name,
            manufacturer=manufacturer,
            num_results=num_results
        )

        if not results:
            click.echo("No results found.")
            return

        click.echo(f"\nFound {len(results)} result(s):\n")

        for i, result in enumerate(results, 1):
            click.echo(f"{i}. {result['title']}")
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

        finder = DatasheetFinder(api_key=api_key)
        click.echo("Testing connection to Exa API...")

        results = finder.search_datasheet("LM358", num_results=1)

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
