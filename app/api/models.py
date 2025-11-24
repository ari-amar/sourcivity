from typing import Optional, List
from pydantic import BaseModel

class PartsSearchRequest(BaseModel):
	query: str
	location_filter: Optional[str] = "global suppliers"

class DatasheetSearchRequest(BaseModel):
	component_description: str
	max_results: Optional[int] = 5
	
class ServicesSearchRequest(BaseModel):
	query: str
	location_filter: Optional[str] = "global providers"

class VendorQualityRequest(BaseModel):
	vendor_name: str
	industry: Optional[str] = None