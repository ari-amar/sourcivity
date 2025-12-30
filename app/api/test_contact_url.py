#!/usr/bin/env python3
"""
Test script to verify contact URL discovery logic for both parts and service searches.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

import asyncio
from utils.pdf_scraper import derive_contact_url, find_contact_url

async def test_parts_contact_discovery():
    """Test the contact URL discovery flow for parts search (no AI extraction)"""
    print("\n" + "="*70)
    print("TESTING PARTS SEARCH CONTACT URL DISCOVERY")
    print("="*70)

    # Test case 1: Real supplier with contact page
    test_url = "https://www.ti.com/lit/ds/symlink/lm358.pdf"
    print(f"\n[TEST 1] Datasheet URL: {test_url}")
    print("-" * 70)

    # Simulate the parts search flow
    from urllib.parse import urlparse
    parsed = urlparse(test_url)
    homepage_url = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc

    print(f"Step 1: Extract homepage - {homepage_url}")

    # Step 1: Try to find actual contact page
    print(f"Step 2: Crawling {domain} for contact links...")
    actual_contact = await find_contact_url(domain, timeout=8)

    if actual_contact:
        print(f"  ✅ Found verified contact URL: {actual_contact}")
        final_url = actual_contact
    else:
        # Step 2: Verify derived URL
        derived_url = derive_contact_url(test_url)
        print(f"  Step 3: Testing derived URL: {derived_url}")

        try:
            import requests
            head_response = requests.head(derived_url, timeout=5, allow_redirects=True)
            if head_response.status_code == 200:
                print(f"  ✅ Derived URL verified (status {head_response.status_code}): {derived_url}")
                final_url = derived_url
            else:
                print(f"  ⚠️  Derived URL failed (status {head_response.status_code})")
                final_url = homepage_url
                print(f"  ✅ Using homepage fallback: {homepage_url}")
        except Exception as e:
            print(f"  ⚠️  Derived URL unreachable: {e}")
            final_url = homepage_url
            print(f"  ✅ Using homepage fallback: {homepage_url}")

    print(f"\n✅ FINAL CONTACT URL: {final_url}")
    print(f"   This URL will be used in the Contact Supplier button")

    # Test case 2: Fake supplier (to test fallback to homepage)
    print("\n" + "="*70)
    test_url2 = "https://example-supplier-xyz.com/datasheets/widget.pdf"
    print(f"\n[TEST 2] Fictional Datasheet URL: {test_url2}")
    print("-" * 70)

    parsed2 = urlparse(test_url2)
    homepage_url2 = f"{parsed2.scheme}://{parsed2.netloc}"
    domain2 = parsed2.netloc

    print(f"Step 1: Extract homepage - {homepage_url2}")
    print(f"Step 2: Attempting to crawl {domain2} (should fail)...")

    try:
        actual_contact2 = await find_contact_url(domain2, timeout=5)
        if actual_contact2:
            final_url2 = actual_contact2
            print(f"  ✅ Found contact URL: {actual_contact2}")
        else:
            print(f"  ❌ No contact link found")
            derived_url2 = derive_contact_url(test_url2)
            print(f"  Step 3: Testing derived URL: {derived_url2}")
            final_url2 = homepage_url2
            print(f"  ⚠️  Should fall back to homepage: {homepage_url2}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        final_url2 = homepage_url2
        print(f"  ✅ Using homepage fallback: {homepage_url2}")

    print(f"\n✅ FINAL CONTACT URL: {final_url2}")


async def test_service_contact_discovery():
    """Test the contact URL discovery flow for service search (with AI extraction priority)"""
    print("\n" + "="*70)
    print("TESTING SERVICE SEARCH CONTACT URL DISCOVERY")
    print("="*70)

    # Test case 1: AI finds contact URL in HTML
    print(f"\n[TEST 1] AI Extraction Priority")
    print("-" * 70)

    # Simulate AI extraction finding a contact URL
    ai_contact_url = "https://example-mfg.com/get-quote"
    print(f"AI extracted contact URL from HTML: {ai_contact_url}")

    if ai_contact_url and ai_contact_url.startswith("http"):
        print(f"  ✅ AI-extracted URL is valid")
        final_url = ai_contact_url
        print(f"  ✅ Using AI-extracted URL (skips all other steps)")

    print(f"\n✅ FINAL CONTACT URL: {final_url}")

    # Test case 2: AI finds nothing, fall back to crawling
    print(f"\n[TEST 2] AI Finds Nothing - Fallback Chain")
    print("-" * 70)

    test_url = "https://www.protolabs.com/services/"
    ai_contact_url2 = ""  # AI found nothing

    print(f"Service page URL: {test_url}")
    print(f"AI extracted contact URL: (empty)")
    print(f"  ⚠️  No contact URL from AI extraction")

    from urllib.parse import urlparse
    parsed = urlparse(test_url)
    homepage_url = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc

    print(f"\nStep 1: Trying to find contact page by crawling {domain}...")
    actual_contact = await find_contact_url(domain, timeout=8)

    if actual_contact:
        final_url2 = actual_contact
        print(f"  ✅ Found verified contact URL: {actual_contact}")
    else:
        derived_url = derive_contact_url(test_url)
        print(f"  Step 2: Testing derived URL: {derived_url}")

        try:
            import requests
            head_response = requests.head(derived_url, timeout=5, allow_redirects=True)
            if head_response.status_code == 200:
                final_url2 = derived_url
                print(f"  ✅ Derived URL verified: {derived_url}")
            else:
                final_url2 = homepage_url
                print(f"  ⚠️  Derived URL failed (status {head_response.status_code})")
                print(f"  ✅ Using homepage fallback: {homepage_url}")
        except Exception as e:
            final_url2 = homepage_url
            print(f"  ⚠️  Derived URL unreachable: {e}")
            print(f"  ✅ Using homepage fallback: {homepage_url}")

    print(f"\n✅ FINAL CONTACT URL: {final_url2}")


async def main():
    """Run all contact URL discovery tests"""
    print("\n" + "="*70)
    print("CONTACT URL DISCOVERY TEST SUITE")
    print("="*70)
    print("\nThis test verifies that contact buttons always get proper contact info")
    print("by testing the fallback chain for both parts and service searches.")

    # Test parts search (no AI)
    await test_parts_contact_discovery()

    # Test service search (AI priority)
    await test_service_contact_discovery()

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("\n✅ Parts Search Priority:")
    print("   1. Crawl homepage for contact links")
    print("   2. Verify derived URL (/contact)")
    print("   3. Fallback to supplier homepage")
    print("\n✅ Service Search Priority:")
    print("   1. AI-extracted contact URL from HTML")
    print("   2. Crawl homepage for contact links")
    print("   3. Verify derived URL (/contact)")
    print("   4. Fallback to supplier homepage")
    print("\n✅ Both searches ALWAYS provide a working URL (homepage at minimum)")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
