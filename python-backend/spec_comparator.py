#!/usr/bin/env python3
"""
Specification Comparator for side-by-side comparison of datasheet specs.
"""

from typing import List, Dict, Set


class SpecComparator:
    """Compare specifications from multiple datasheets side by side."""

    def __init__(self):
        pass

    def extract_all_spec_keys(self, scraped_results: List[Dict]) -> List[str]:
        """
        Extract all unique specification keys from all results.

        Args:
            scraped_results: List of scraping results from PDFScraper

        Returns:
            Sorted list of all unique spec keys
        """
        all_keys = set()
        for result in scraped_results:
            if result.get("specs") and not result["specs"].get("error"):
                all_keys.update(result["specs"].keys())

        # Sort keys alphabetically, but put common ones first
        priority_keys = ["Part Number", "Manufacturer", "part_number", "manufacturer"]
        sorted_keys = []

        # Add priority keys first
        for key in priority_keys:
            if key in all_keys:
                sorted_keys.append(key)
                all_keys.remove(key)

        # Add remaining keys alphabetically
        sorted_keys.extend(sorted(all_keys))

        return sorted_keys

    def create_comparison_table(self, scraped_results: List[Dict]) -> Dict:
        """
        Create a comparison table with specs in columns.

        Args:
            scraped_results: List of scraping results from PDFScraper

        Returns:
            Dictionary with comparison data structured for display
        """
        # Get all spec keys
        all_spec_keys = self.extract_all_spec_keys(scraped_results)

        # Build comparison table
        comparison = {
            "spec_names": all_spec_keys,
            "products": []
        }

        for result in scraped_results:
            product_data = {
                "url": result.get("url", "Unknown"),
                "error": result.get("error"),
                "specs": {}
            }

            # For each spec key, get the value from this product (or None if not present)
            if result.get("specs") and not result["specs"].get("error"):
                for spec_key in all_spec_keys:
                    product_data["specs"][spec_key] = result["specs"].get(spec_key)
            else:
                # Product had error, leave all specs as None
                for spec_key in all_spec_keys:
                    product_data["specs"][spec_key] = None

            comparison["products"].append(product_data)

        return comparison

    def format_comparison_text(self, comparison: Dict) -> str:
        """
        Format comparison table as text for CLI display.

        Args:
            comparison: Comparison data from create_comparison_table

        Returns:
            Formatted text table
        """
        output = []
        output.append("\n" + "="*100)
        output.append("SPECIFICATION COMPARISON")
        output.append("="*100 + "\n")

        # Product headers
        products = comparison["products"]
        output.append(f"\n{'Specification':<40} | " + " | ".join([f"Product {i+1:<10}" for i in range(len(products))]))
        output.append("-" * 100)

        # Add URLs
        output.append(f"{'URL':<40} | " + " | ".join([f"{p['url'][:10]}..." for p in products]))
        output.append("-" * 100)

        # Add each spec row
        for spec_name in comparison["spec_names"]:
            spec_values = []
            for product in products:
                value = product["specs"].get(spec_name)
                if value is None:
                    spec_values.append("-")
                else:
                    # Truncate long values
                    str_value = str(value)
                    if len(str_value) > 15:
                        str_value = str_value[:12] + "..."
                    spec_values.append(str_value)

            # Truncate long spec names
            display_name = spec_name if len(spec_name) <= 38 else spec_name[:35] + "..."
            output.append(f"{display_name:<40} | " + " | ".join([f"{v:<15}" for v in spec_values]))

        output.append("\n" + "="*100)

        return "\n".join(output)

    def format_comparison_html(self, comparison: Dict) -> str:
        """
        Format comparison table as HTML for web display.

        Args:
            comparison: Comparison data from create_comparison_table

        Returns:
            HTML table string
        """
        html = ['<table class="spec-comparison">']

        # Header row with product numbers
        html.append('<thead><tr><th>Specification</th>')
        for i, product in enumerate(comparison["products"]):
            html.append(f'<th>Product {i+1}</th>')
        html.append('</tr></thead>')

        # Body
        html.append('<tbody>')

        # URL row
        html.append('<tr class="url-row"><td><strong>URL</strong></td>')
        for product in comparison["products"]:
            url = product.get("url", "Unknown")
            html.append(f'<td><a href="{url}" target="_blank" title="{url}">{url[:50]}...</a></td>')
        html.append('</tr>')

        # Error row if any products have errors
        errors_exist = any(p.get("error") for p in comparison["products"])
        if errors_exist:
            html.append('<tr class="error-row"><td><strong>Status</strong></td>')
            for product in comparison["products"]:
                if product.get("error"):
                    html.append(f'<td class="error">Error: {product["error"]}</td>')
                else:
                    html.append('<td class="success">OK</td>')
            html.append('</tr>')

        # Spec rows
        for spec_name in comparison["spec_names"]:
            html.append(f'<tr><td><strong>{spec_name}</strong></td>')
            for product in comparison["products"]:
                value = product["specs"].get(spec_name)
                if value is None:
                    html.append('<td class="no-data">-</td>')
                else:
                    html.append(f'<td>{value}</td>')
            html.append('</tr>')

        html.append('</tbody></table>')

        return ''.join(html)

    def compare(self, scraped_results: List[Dict], format: str = "html") -> str:
        """
        Compare multiple scraped datasheets and format output.

        Args:
            scraped_results: List of scraping results from PDFScraper
            format: Output format ("html" or "text")

        Returns:
            Formatted comparison string
        """
        comparison = self.create_comparison_table(scraped_results)

        if format == "text":
            return self.format_comparison_text(comparison)
        else:
            return self.format_comparison_html(comparison)