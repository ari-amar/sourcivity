import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
os.environ.setdefault("BRAVE_API_KEY", "dummy")
os.environ.setdefault("EMAIL_ADDRESS", "dummy@example.com")
os.environ.setdefault("GMAIL_ADDRESS", "dummy@example.com")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from handlers import search
from services import scraper, settings as user_settings


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

    def test_named_manufacturer_query_ranks_direct_supplier_first(self):
        suppliers = [
            {"name": "Omega Engineering", "website": "https://omega.com"},
            {"name": "Brooks Instrument", "website": "https://www.brooksinstrument.com"},
            {"name": "MKS Instruments", "website": "https://www.mks.com"},
        ]

        ranked = search._rank_suppliers_for_query(suppliers, "Brooks Instrument mass flow controller")

        self.assertEqual(ranked[0]["name"], "Brooks Instrument")

        ranked = search._rank_suppliers_for_query(suppliers, "MKS mass flow controller")
        self.assertEqual(ranked[0]["name"], "MKS Instruments")

    def test_generic_query_preserves_supplier_order(self):
        suppliers = [
            {"name": "Omega Engineering", "website": "https://omega.com"},
            {"name": "Brooks Instrument", "website": "https://www.brooksinstrument.com"},
        ]

        ranked = search._rank_suppliers_for_query(suppliers, "mass flow controller")

        self.assertEqual([s["name"] for s in ranked], ["Omega Engineering", "Brooks Instrument"])

    def test_official_website_resolution_only_checks_suspicious_sites(self):
        self.assertFalse(search._needs_official_website_resolution(
            {"name": "Brooks Instrument", "website": "https://www.brooksinstrument.com"}
        ))
        self.assertFalse(search._needs_official_website_resolution(
            {"name": "Ultra Precision Machining", "website": "https://ultramachining.com"}
        ))
        self.assertTrue(search._needs_official_website_resolution(
            {"name": "SSP (Stainless Steel Products)", "website": "https://shopbvv.com/products/ssp-duolok"}
        ))
        self.assertTrue(search._needs_official_website_resolution(
            {"name": "Air-Way Manufacturing Company", "website": ""}
        ))

    def test_official_website_scoring_prefers_source_domain_over_reseller(self):
        supplier = {
            "name": "SSP (Stainless Steel Products)",
            "products": "Duolok stainless steel tube fittings",
            "website": "https://shopbvv.com/products/ssp-union-elbow-3-8-duolok",
        }
        official = search._score_official_website_candidate(
            supplier,
            {
                "url": "https://www.myssp.com/products/fittings/tube-fittings/instrumentation/duolok",
                "title": "Stainless Steel Tube Fittings | Duolok | SSP",
                "description": "SSP Corporation manufactures instrumentation valves and fittings.",
            },
            "stainless steel compression fittings",
        )
        lookalike = search._score_official_website_candidate(
            supplier,
            {
                "url": "https://sspsteel.com/",
                "title": "Hygienic and Industrial Stainless Steel Products",
                "description": "Stainless steel products supplier.",
            },
            "stainless steel compression fittings",
        )
        reseller = search._score_official_website_candidate(
            supplier,
            {
                "url": "https://shopbvv.com/products/ssp-union-elbow-3-8-duolok",
                "title": "SSP Union Elbow - BVV",
                "description": "Shop SSP fittings online.",
            },
            "stainless steel compression fittings",
        )

        self.assertGreaterEqual(official, search._OFFICIAL_WEBSITE_MIN_SCORE)
        self.assertGreater(official, lookalike)
        self.assertGreater(official, reseller)

    def test_official_website_scoring_rejects_non_us_tld_for_us_search(self):
        supplier = {
            "name": "Pacific Plastics Injection Molding",
            "products": "Plastic Injection Molding",
            "website": "",
        }
        score = search._score_official_website_candidate(
            supplier,
            {
                "url": "https://pacificplastics.com.au/",
                "title": "Pacific Plastics",
                "description": "Plastic injection molding company.",
            },
            "medical injection molding",
            "north_america",
        )

        self.assertLess(score, search._OFFICIAL_WEBSITE_MIN_SCORE)

    def test_invalid_email_rejects_asset_domains(self):
        self.assertFalse(scraper._is_valid_email("service-prototyping@400x400-150x150.webp"))
        self.assertFalse(scraper._extract_emails("email service-prototyping@400x400-150x150.webp"))
        self.assertTrue(scraper._is_valid_email("sales@example-industrial.com"))
        self.assertEqual(
            scraper._extract_emails('mailto:%20customer.service@myssp.com'),
            ["customer.service@myssp.com"],
        )
        self.assertEqual(
            scraper._pick_best_email(["sales@measurement-plus.com.au"], "https://www.brooksinstrument.com"),
            "",
        )
        self.assertEqual(
            scraper._pick_best_email(["customer.service@myssp.com"], "https://www.myssp.com"),
            "customer.service@myssp.com",
        )

    def test_location_filter_keeps_matching_state_and_pending(self):
        suppliers = [
            {"name": "CA Supplier", "state": "CA"},
            {"name": "MA Supplier", "state": "MA"},
            {"name": "Pending Supplier", "state": ""},
        ]

        filtered = search._filter_suppliers_for_region(
            suppliers,
            "north_america",
            "bearings",
            allow_pending=True,
            location="California",
        )

        self.assertEqual([s["name"] for s in filtered], ["CA Supplier", "Pending Supplier"])

    def test_international_location_switches_to_global_region(self):
        self.assertEqual(search._resolve_region_for_location("north_america", "Germany"), "global")
        self.assertEqual(search._resolve_region_for_location("global", "California"), "north_america")

    def test_customer_settings_persist_and_sanitize_rfq_style(self):
        original_path = user_settings.SETTINGS_JSON
        with tempfile.TemporaryDirectory() as tmpdir:
            user_settings.SETTINGS_JSON = str(Path(tmpdir) / "settings.json")
            try:
                updated = user_settings.update_rfq_settings({
                    "buyer_name": "Ari Amar",
                    "buyer_title": "Founder",
                    "buyer_company": "Sourcivity",
                    "rfq_company_intro": "I'm sourcing this for Sourcivity.",
                    "rfq_tone": "technical",
                    "rfq_length": "standard",
                    "rfq_urgency": "high",
                    "rfq_repeat_orders": True,
                    "rfq_vendor_deadline": True,
                    "rfq_casual": False,
                    "rfq_requirements": ["pricing", "lead_time", "datasheet", "bad_key"],
                    "rfq_signature": "Ari\nSourcivity",
                    "rfq_default_deadline": "We are selecting vendors this week.",
                    "rfq_buyer_notes": "Do not promise repeat orders.\r\nAsk for availability.",
                })
                loaded = user_settings.get_rfq_settings()
            finally:
                user_settings.SETTINGS_JSON = original_path

        self.assertEqual(updated["rfq_tone"], "technical")
        self.assertEqual(updated["rfq_length"], "standard")
        self.assertEqual(updated["rfq_urgency"], "high")
        self.assertTrue(updated["rfq_repeat_orders"])
        self.assertEqual(loaded["rfq_requirements"], ["pricing", "lead_time", "datasheet"])
        self.assertEqual(loaded["rfq_signature"], "Ari\nSourcivity")
        self.assertEqual(loaded["rfq_buyer_notes"], "Do not promise repeat orders.\nAsk for availability.")


if __name__ == "__main__":
    unittest.main()
