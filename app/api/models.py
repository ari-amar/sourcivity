from typing import Optional, List
from pydantic import BaseModel
from enums import AiClientName, SearchEngineClientName


class AvailableClientResponse(BaseModel):
	ai_client_names: List[str]
	search_engine_client_names: List[str]
class PartSearchRequest(BaseModel):
	query: str
	generate_ai_search_prompt: Optional[bool] = False
	search_engine_client_name: Optional[str] = SearchEngineClientName.EXA
	ai_client_name: Optional[str] = AiClientName.CLOUDFLARE

class PartResponse(BaseModel):
	url: str
	md: Optional[str] = None
	specs: Optional[dict] = None
	error: Optional[str] = None

class PartSearchResponse(BaseModel):
	query: str
	spec_column_names: List[str]
	parts: List[PartResponse]