import httpx

def test_search_parts():
	url = "http://localhost:8000/api/search/parts"
	payload = {
		"query": "industrial motor 3-phase 400V 50Hz IP55 TEFC 15 kW 1500 rpm foot-mounted IEC frame 160L flange B5",
		"location_filter": None
	}
	httpx.post(url, json=payload, timeout=120)

if __name__ == "__main__":
	test_search_parts()