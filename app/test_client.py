import httpx

def test_search_parts():
	url = "http://localhost:8000/api/search/parts"
	payload = {
		"query": "industrial motor",
		"us_suppliers_only": True,
		"predetermined_columns": ["Voltage", "Power", "Efficiency", "Mounting Type"]
	}
	response = httpx.post(url, json=payload, timeout=120)
	assert response.status_code == 200
	data = response.json()
	assert "parts" in data
	assert isinstance(data["parts"], list)

if __name__ == "__main__":
	test_search_parts()