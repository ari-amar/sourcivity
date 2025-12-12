#!/usr/bin/env python3
"""
Simple web server for datasheet finder.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datasheet_finder import DatasheetFinder
from pdf_scraper import PDFScraper
from spec_comparator import SpecComparator
from service_finder import ServiceFinder
from service_scraper import ServiceScraper
from service_comparator import ServiceComparator
import os

app = Flask(__name__)
CORS(app)

# Initialize finder and scraper for datasheets
finder = DatasheetFinder()
scraper = PDFScraper()
comparator = SpecComparator()

# Initialize finder and scraper for services
service_finder = ServiceFinder()
service_scraper = ServiceScraper()
service_comparator = ServiceComparator()


@app.route('/')
def index():
    """Serve the HTML page."""
    return send_file('index.html')


@app.route('/search', methods=['POST'])
def search():
    """
    Search for datasheets.

    Expected JSON body:
    {
        "component_name": "LM358",
        "manufacturer": "Texas Instruments" (optional),
        "num_results": 10 (optional)
    }
    """
    try:
        data = request.get_json()

        component_name = data.get('component_name')
        if not component_name:
            return jsonify({'error': 'component_name is required'}), 400

        manufacturer = data.get('manufacturer')
        num_results = data.get('num_results', 10)

        # Perform search
        results = finder.search_datasheet(
            component_name=component_name,
            manufacturer=manufacturer,
            num_results=num_results
        )

        return jsonify({
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/compare', methods=['POST'])
def compare():
    """
    Scrape PDFs and compare specs side by side.

    Expected JSON body:
    {
        "urls": ["url1.pdf", "url2.pdf", ...],
        "product_type": "optional product type hint"
    }
    """
    try:
        data = request.get_json()

        urls = data.get('urls', [])
        if not urls:
            return jsonify({'error': 'urls array is required'}), 400

        if len(urls) > 10:
            return jsonify({'error': 'Maximum 10 PDFs can be compared at once'}), 400

        product_type = data.get('product_type')

        # Scrape all PDFs
        print(f"Scraping {len(urls)} PDFs...")
        scraped_results = scraper.scrape_multiple(urls, product_type)

        # Create comparison
        comparison_html = comparator.compare(scraped_results, format="html")
        comparison_data = comparator.create_comparison_table(scraped_results)

        return jsonify({
            'comparison_html': comparison_html,
            'comparison_data': comparison_data,
            'scraped_results': scraped_results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/search-services', methods=['POST'])
def search_services():
    """
    Search for supplier service and capability pages.

    Expected JSON body:
    {
        "query": "CNC machining services",
        "supplier_name": "optional supplier name" (optional),
        "num_results": 10 (optional)
    }
    """
    try:
        data = request.get_json()

        query = data.get('query')
        if not query:
            return jsonify({'error': 'query is required'}), 400

        supplier_name = data.get('supplier_name')
        num_results = data.get('num_results', 10)

        # Perform service search
        results = service_finder.search_services(
            query=query,
            supplier_name=supplier_name,
            num_results=num_results
        )

        return jsonify({
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/compare-services', methods=['POST'])
def compare_services():
    """
    Scrape service pages and compare supplier capabilities side by side.

    Expected JSON body:
    {
        "urls": ["url1", "url2", ...],
        "query_context": "optional context about what user is searching for"
    }
    """
    try:
        data = request.get_json()

        urls = data.get('urls', [])
        if not urls:
            return jsonify({'error': 'urls array is required'}), 400

        if len(urls) > 10:
            return jsonify({'error': 'Maximum 10 pages can be compared at once'}), 400

        query_context = data.get('query_context')

        # Scrape all service pages
        print(f"Scraping {len(urls)} service pages...")
        scraped_results = service_scraper.scrape_multiple(urls, query_context)

        # Create comparison
        comparison_html = service_comparator.compare(scraped_results, format="html")
        comparison_data = service_comparator.create_comparison_table(scraped_results)

        return jsonify({
            'comparison_html': comparison_html,
            'comparison_data': comparison_data,
            'scraped_results': scraped_results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting datasheet finder web server...")
    print("Open http://localhost:5001 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5001)
