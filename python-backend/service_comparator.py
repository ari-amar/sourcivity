#!/usr/bin/env python3
"""
Service Comparator - Create comparison tables for supplier services.
"""

from typing import List, Dict


class ServiceComparator:
    """Create comparison tables for supplier service information."""

    def create_comparison_table(self, scraped_results: List[Dict]) -> Dict:
        """
        Create a structured comparison table from scraped service data.

        Args:
            scraped_results: List of results from ServiceScraper.scrape_multiple()

        Returns:
            Dictionary with comparison data structure
        """
        # Collect all unique field names across all suppliers
        all_fields = set()
        valid_results = []

        for result in scraped_results:
            if result.get("error") is None and result.get("services"):
                services = result["services"]
                if isinstance(services, dict) and "error" not in services:
                    all_fields.update(services.keys())
                    valid_results.append(result)

        if not valid_results:
            return {
                "fields": [],
                "suppliers": []
            }

        # Sort fields in a logical order
        field_order = [
            "company_name",
            "location",
            "services_offered",
            "capabilities",
            "certifications",
            "equipment",
            "industries_served",
            "lead_time",
            "moq",
            "year_established",
            "employees"
        ]

        # Keep fields in preferred order, then add any extra fields
        ordered_fields = [f for f in field_order if f in all_fields]
        extra_fields = sorted(all_fields - set(ordered_fields))
        ordered_fields.extend(extra_fields)

        # Build comparison data
        suppliers = []
        for result in valid_results:
            services = result["services"]
            supplier_data = {
                "url": result["url"],
                "services": services
            }
            suppliers.append(supplier_data)

        return {
            "fields": ordered_fields,
            "suppliers": suppliers
        }

    def compare(self, scraped_results: List[Dict], format: str = "text") -> str:
        """
        Create a comparison of supplier services.

        Args:
            scraped_results: List of results from ServiceScraper.scrape_multiple()
            format: Output format ("text" or "html")

        Returns:
            Formatted comparison string
        """
        comparison_data = self.create_comparison_table(scraped_results)

        if not comparison_data["suppliers"]:
            return "No valid supplier data to compare."

        if format == "html":
            return self._format_html(comparison_data)
        else:
            return self._format_text(comparison_data)

    def _format_text(self, comparison_data: Dict) -> str:
        """Format comparison as plain text."""
        output = []
        output.append("=" * 80)
        output.append("SUPPLIER SERVICE COMPARISON")
        output.append("=" * 80)

        for i, supplier in enumerate(comparison_data["suppliers"], 1):
            output.append(f"\n{'=' * 80}")
            output.append(f"SUPPLIER {i}")
            output.append(f"URL: {supplier['url']}")
            output.append(f"{'=' * 80}\n")

            services = supplier["services"]
            for field in comparison_data["fields"]:
                value = services.get(field)
                field_display = field.replace("_", " ").title()

                if value is None:
                    value_display = "Not specified"
                elif isinstance(value, list):
                    if value:
                        value_display = "\n  - " + "\n  - ".join(str(v) for v in value)
                    else:
                        value_display = "None listed"
                else:
                    value_display = str(value)

                output.append(f"{field_display}:")
                output.append(f"  {value_display}\n")

        return "\n".join(output)

    def _format_html(self, comparison_data: Dict) -> str:
        """Format comparison as HTML table."""
        if not comparison_data["suppliers"]:
            return "<p>No suppliers to compare</p>"

        html = ['<table border="1" style="border-collapse: collapse; width: 100%;">']

        # Header row with supplier names
        html.append('<tr style="background-color: #f0f0f0;">')
        html.append('<th style="padding: 8px;">Field</th>')

        for supplier in comparison_data["suppliers"]:
            company_name = supplier["services"].get("company_name", "Unknown Supplier")
            html.append(f'<th style="padding: 8px;">{company_name}</th>')

        html.append('</tr>')

        # Data rows
        for field in comparison_data["fields"]:
            if field == "company_name":  # Skip company name since it's in header
                continue

            field_display = field.replace("_", " ").title()
            html.append('<tr>')
            html.append(f'<td style="padding: 8px; font-weight: bold;">{field_display}</td>')

            for supplier in comparison_data["suppliers"]:
                value = supplier["services"].get(field)

                if value is None:
                    value_display = '<em>Not specified</em>'
                elif isinstance(value, list):
                    if value:
                        items = "".join(f"<li>{v}</li>" for v in value)
                        value_display = f'<ul style="margin: 0; padding-left: 20px;">{items}</ul>'
                    else:
                        value_display = '<em>None listed</em>'
                else:
                    value_display = str(value)

                html.append(f'<td style="padding: 8px;">{value_display}</td>')

            html.append('</tr>')

        html.append('</table>')
        return "".join(html)
