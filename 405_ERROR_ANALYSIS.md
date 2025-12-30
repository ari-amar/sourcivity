# 405 Method Not Allowed Error - Root Cause Analysis

## Request Flow Analysis

1. **Frontend** → `fetch('${BACKEND_URL}/api/search/parts', { method: 'POST' })`
   - In production: `fetch('/api/search/parts', { method: 'POST' })` (relative URL)
   - Request: `POST /api/search/parts`

2. **Vercel Routing** → `vercel.json` routes `/api/(.*)` to `api/index.py`
   - Pattern: `/api/(.*)` captures `search/parts`
   - Destination: `api/index.py`

3. **Python Handler** → `api/index.py` uses Mangum to wrap FastAPI
   - Mangum receives the request event
   - Converts it to ASGI format
   - Passes to FastAPI app

4. **FastAPI** → Routes defined as:
   - `@app.post('/api/search/parts')`
   - `@app.post('/search/parts')` (fallback)

## Potential Causes

### 1. **Path Format Mismatch** ⚠️ MOST LIKELY
When Vercel routes `/api/(.*)` to a Python function, the path that reaches Mangum might be:
- **Full path**: `/api/search/parts` ✅ Should match `/api/search/parts` route
- **Captured group only**: `search/parts` ✅ Should match `/search/parts` route
- **Different format**: `/api/search/parts/` (with trailing slash) ❌ Won't match
- **Query string issues**: Path might include query params that break matching

**Solution**: We have both routes, but need to verify what path Mangum actually receives.

### 2. **Vercel Route Pattern Issue**
The pattern `/api/(.*)` might not be matching correctly, or the `methods` array might be too restrictive.

**Solution**: Try removing the `methods` array or using a different routing pattern.

### 3. **Next.js Interception**
Even though middleware skips `/api/*`, Next.js might still try to handle it as a Next.js API route before Vercel routing.

**Solution**: Ensure no Next.js API routes exist in `app/api/` directory (they don't).

### 4. **Mangum Path Handling**
Mangum might be receiving the path in a format that doesn't match FastAPI routes.

**Solution**: Add debugging to see the actual path received.

### 5. **CORS Preflight Issue**
The OPTIONS preflight request might be failing, causing the browser to reject the POST.

**Solution**: We have OPTIONS handlers, but need to verify they work.

### 6. **Route Order in vercel.json**
The catch-all route `/(.*)` might be matching before the `/api/(.*)` route.

**Solution**: The order is correct (specific before catch-all), but worth verifying.

### 7. **Function Export Issue**
The Python function might not be exporting the handler correctly for Vercel.

**Solution**: Verify the handler export format matches Vercel's expectations.

## Recommended Fixes

1. **Add path debugging** to see what path Mangum receives
2. **Try alternative routing patterns** in vercel.json
3. **Remove methods array** from vercel.json to see if it's too restrictive
4. **Add a catch-all route** in FastAPI to see unmatched requests
5. **Check Vercel function logs** for actual request details

