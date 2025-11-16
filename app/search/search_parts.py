from services.groq_client import GroqClient
from models import PartsSearchRequest, PartsSearchResponse, PartResponse
from prompts import GROQ_PART_SEARCH_PROMPT
from constants import GROQ_COMPOUND_MINI

temperature: float = 0.3
max_tokens: int = 2048
top_p: float = 0.95	
stream: bool = False
model: str = GROQ_COMPOUND_MINI

def groq_part_search(client: GroqClient, query: str, predefined_columns: str, location_filter: str) -> dict:

	system_prompt_string = GROQ_PART_SEARCH_PROMPT.format(query=query, 
												predefined_columns=predefined_columns,
												location_filter=location_filter)
	user_prompt_string = f"Provide a detailed parts search for: {query}"
	
	response_format = {
		"type": "json_object",
		"properties": {
			"parts": {
				"type": "array",
				"items": {
					"type": "object",
					"properties": {
						"partNumber": {"type": "string"},
						"description": {"type": "string"},
						"supplier": {"type": "string"},
						"price": {"type": "string"},
						"availability": {"type": "string"}
					}
				}
			}
		}
	}
	
	return client.query(
		model=model,
		system_prompt_content=system_prompt_string,
		user_prompt_content=user_prompt_string,
		temp=temperature,
		max_tokens=max_tokens,
		top_p=top_p,
		response_format=response_format,
		stream=stream
	 )