import httpx

def test_search_parts():
	url = "http://localhost:8000/api/search/parts"
	payload = {
		"query": "mass flow controller",
		"location_filter": None
	}
	httpx.post(url, json=payload, timeout=120)

if __name__ == "__main__":
	test_search_parts()