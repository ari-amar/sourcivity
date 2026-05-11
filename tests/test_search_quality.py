import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("BRAVE_API_KEY", "dummy")
os.environ.setdefault("EMAIL_ADDRESS", "dummy@example.com")
os.environ.setdefault("GMAIL_ADDRESS", "dummy@example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handlers import search
from services import scraper


class SearchQualityTests(unittest.TestCase):
    def test_certification_cleanup_rejects_product_marks(self):
        self.assertEqual(
            scraper._extract_certifications(
                "ISO9001 certified quality system and ISO 9001:2015 certificate",
                require_context=True,
            ),
            ["ISO 9001:2015"],
        )
        self.assertEqual(
            scraper._extract_certifications("FDA approved products and RoHS compliant parts", require_context=True),
            [],
        )
        self.assertEqual(
            scraper._extract_certifications("Certifications: FDA, CE mark, and ISO 9001 certified", require_context=True),
            ["ISO 9001"],
        )
        self.assertEqual(
            scraper._filter_unverified_certifications(
                scraper._extract_certifications("FDA, ITAR, ISO9001, ISO 9001:2015, ASME SECTION, RoHS")
            ),
            ["ISO 9001:2015"],
        )

    def test_supplier_level_context_keeps_registration_certs(self):
        self.assertEqual(
            scraper._extract_certifications(
                "Our facility is FDA registered and ISO13485 certified. ITAR registered manufacturer.",
                require_context=True,
            ),
            ["FDA REGISTERED", "ISO 13485", "ITAR REGISTERED"],
        )

    def test_demo_enrichment_skips_known_supplier_network_work(self):
        calls = []
        original_fetch = scraper._fetch_page

        def fake_fetch(*args, **kwargs):
            calls.append((args, kwargs))
            return ""

        scraper._fetch_page = fake_fetch
        try:
            result = scraper._enrich_single(
                {
                    "name": "Known Co",
                    "website": "https://example.com",
                    "state": "CA",
                    "certifications": "ISO9001, FDA, ITAR",
                },
                skip_email=True,
            )
        finally:
            scraper._fetch_page = original_fetch

        self.assertEqual(calls, [])
        self.assertEqual(result["state"], "CA")
        self.assertEqual(result["certifications"], "ISO 9001")

    def test_conflicting_enriched_location_keeps_card_visible(self):
        supplier = {
            "name": "Brooks Instrument",
            "website": "https://example.com",
            "state": "Germany",
            "_non_us": True,
        }

        interim = search._prepare_visible_suppliers([supplier], "north_america", "mass flow controller")
        final = search._prepare_visible_suppliers([supplier], "north_america", "mass flow controller", final=True)

        self.assertEqual(len(interim), 1)
        self.assertEqual(interim[0]["state"], "")
        self.assertEqual(len(final), 1)
        self.assertEqual(final[0]["state"], "N/A")


if __name__ == "__main__":
    unittest.main()
