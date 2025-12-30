from typing import Optional, List
from pydantic import BaseModel
from enums import AiClientName, SearchEngineClientName

class SearchEngineResult(BaseModel):
	title: str
	url: str
	text: Optional[str] = None
	score: Optional[float] = None
	published_date: Optional[str] = None
	author: Optional[str] = None

class SearchEngineClientResponse(BaseModel):
	prompt: str
	results: List[SearchEngineResult] = []

class AvailableClientResponse(BaseModel):
	ai_client_names: List[str]
	search_engine_client_names: List[str]

class PartSearchRequest(BaseModel):
	query: str
	generate_ai_search_prompt: Optional[bool] = False
	search_engine_client_name: Optional[str] = SearchEngineClientName.EXA
	ai_client_name: Optional[str] = AiClientName.CLOUDFLARE
	debug: Optional[bool] = False

class PartResponse(BaseModel):
	url: str
	contact_url: Optional[str] = None
	md: Optional[str] = None
	specs: Optional[dict] = None
	manufacturer: Optional[str] = None
	product_name: Optional[str] = None
	error: Optional[str] = None

class PartSearchResponse(BaseModel):
	query: str
	spec_column_names: List[str]
	parts: List[PartResponse]
	timing: Optional[dict] = None

class ServiceSearchRequest(BaseModel):
	query: str
	supplier_name: Optional[str] = None
	generate_ai_search_prompt: Optional[bool] = False
	search_engine_client_name: Optional[str] = SearchEngineClientName.EXA
	ai_client_name: Optional[str] = AiClientName.CLOUDFLARE

class ServiceSearchResponse(BaseModel):
	query: str
	services: List[dict]

# TODO: define ServiceResponse model if needed