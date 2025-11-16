from typing import Optional, List
from pydantic import BaseModel

class PartsSearchRequest(BaseModel):
	query: str
	us_suppliers_only: Optional[bool] = False
	predetermined_columns: Optional[List[str]] = None
	page: Optional[int] = 1
	pageSize: Optional[int] = 50

class PartResponse(BaseModel):
	partNumber: str
	description: str
	supplier: str
	price: str
	availability: str
class PartsSearchResponse(BaseModel):
	parts: List[PartResponse] = []

class ColumnDeterminationRequest(BaseModel):
	query: str

class PhotoSearchRequest(BaseModel):
	imageUrl: Optional[str] = None
	# Optionally accept base64 or multipart file in a different handler

class AnalyzeQueryRequest(BaseModel):
	query: str

class ExtractSuppliersRequest(BaseModel):
	text: str

class RfqConversationRequest(BaseModel):
	query: str
	partDetails: Optional[str] = None
	supplierEmails: Optional[List[str]] = None
	usSuppliersOnly: Optional[bool] = False
	rfqDetails: Optional[dict] = None
	selectedSuppliers: Optional[List[str]] = None

class SendRfqRequest(BaseModel):
	rfqId: Optional[str] = None
	to: List[str]
	subject: str
	body: str

class CronTriggerRequest(BaseModel):
	# optional payload; you can also rely on header secret
	pass