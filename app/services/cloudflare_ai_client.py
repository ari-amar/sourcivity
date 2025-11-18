import httpx
import json
import re
from prompts import CLOUDFLARE_SEARCH_ANALYSIS_SYSTEM_PROMPT, CLOUDFLARE_SEARCH_ANALYSIS_USER_PROMPT

class CloudflareAIClient:
	def __init__(self, account_id: str, workers_key: str):
		self.account_id = account_id
		self.workers_key = workers_key

	async def analyze_search_results(self, model: str, query: str, has_query_specs: bool, search_results: dict):

		model_path = re.sub(r'^@cf/', '', model)
		system_prefix = CLOUDFLARE_SEARCH_ANALYSIS_SYSTEM_PROMPT.strip() + "\n\n"
		user_content = system_prefix + CLOUDFLARE_SEARCH_ANALYSIS_USER_PROMPT.format(
						query=query,
						has_specs_in_query=has_query_specs,
						search_results_json=json.dumps(
    		    {"results": search_results},
    		    ensure_ascii=False,   # ← stops \u2014, \u2192, etc.
    		    indent=2              # ← makes it human-readable and model-friendly
    		)
			)
		payload = {
			"model": model,
			"messages": [
				{
					"role": "user",
					"content": user_content
				}
			],
            "response_format": { "type" : "json_object" },
        }
		headers = {"Authorization": f"Bearer {self.workers_key}"}
		print("Serialized Payload:", json.dumps(payload, indent=2))
		print("Payload Size (bytes):", len(json.dumps(payload).encode('utf-8')))
		async with httpx.AsyncClient(timeout=120) as client:
			response = await client.post(f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model}", 
										headers=headers, json=payload)
			if response.status_code != 200:
				print(f"Error Response [{response.status_code}]: {response.text}")
				response.raise_for_status()
			raw = response.json()

		text = raw["result"]["response"]
		match = re.search(r"\{.*\}", text, re.DOTALL)
		if match:
			try:
				return json.loads(match.group(0))
			except json.JSONDecodeError:
				return {"error": "json decode error", "raw": text}
		else:
			return {"error": "no json found", "raw": text}