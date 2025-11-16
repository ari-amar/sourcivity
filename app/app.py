import os
from fastapi import Request, FastAPI, Response, UploadFile, File, Header, HTTPException
from models import *
from services import GroqClient
from search import groq_part_search

app = FastAPI()
groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))

@app.get("/api/health")
async def health_check():
	return Response(content="OK", media_type="text/plain")

@app.post('/api/search/parts')
async def search_parts(payload: PartsSearchRequest):

	if payload.us_suppliers_only:
		location_filter = "US suppliers only"
	else:
		location_filter = "global suppliers"

	if payload.predetermined_columns:
		columns_str = ", ".join(payload.predetermined_columns)
	else:
		columns_str = ""

	part_search_response = groq_part_search(client=groq_client, 
										 query=payload.query, 
										 predefined_columns=columns_str,
										 location_filter=location_filter)
	return part_search_response.read()

@app.post('/api/search/photo')
async def search_photo(file: UploadFile = File(None), payload: PhotoSearchRequest = None):
	return {"results": []}	

@app.get('/api/search/suggestions')
async def search_suggestions(query: str):
	return {"query": query, "results": []}	

@app.post('/api/ai/analyze-query')
async def ai_analyze_query(payload: AnalyzeQueryRequest):
	return {"query": payload.query, "results": []}	

@app.post('/api/ai/extract-suppliers')
async def ai_extract_suppliers(payload: ExtractSuppliersRequest):
	return {"results": []}	

@app.post('/api/ai/generate-supplier-review-summary')
async def ai_generate_supplier_review_summary(payload: ExtractSuppliersRequest):
	return {"summary": "This is a generated summary."}

@app.post('/api/ai/rfq-conversation')
async def ai_rfq_conversation(payload: RfqConversationRequest):
	return {"rfqContent": "...", "suppliers": [], "query": payload.query}

@app.post("/api/ai/rfq")
async def ai_rfq(payload: RfqConversationRequest):
	return {"created": True, "id": "new-rfq-id"}

@app.post("/api/ai/rfq-follow-up")
async def ai_rfq_follow_up(payload: RfqConversationRequest):
	return {"followUp": "Generated follow-up text"}

@app.get("/api/ai/rfq-stats")
async def ai_rfq_stats():
	return {"stats": {}}

@app.post("/api/email/send-rfq")
async def email_send_rfq(payload: SendRfqRequest):
	# send via AgentMail or simulate
	return {"sent": True, "mock": True}

@app.post("/api/webhooks/agentmail")
async def webhooks_agentmail(request: Request):
	body = await request.json()
	# validate signature headers, etc.
	return {"ok": True}	

@app.post('/api/cron/follow-ups')
async def cron_follow_ups(authorization: Optional[str] = Header(None)):
	# check 'Authorization' header equals expected secret
    if authorization != "Bearer " + ( "EXPECTED_SECRET" ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # perform follow-up scheduling/sending logic
    return {"processed": 0}