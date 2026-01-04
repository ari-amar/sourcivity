# Vercel Deployment Guide

This guide explains how to deploy the Sourcivity application to Vercel's free hosting tier.

## Overview

The application has been refactored to work with Vercel's serverless function architecture:
- **Frontend**: Next.js application (deployed as standard Next.js app)
- **Backend**: FastAPI application (deployed as Python serverless function)

## Key Changes Made

1. **Serverless Function Handler** (`api/index.py`): Wraps the FastAPI app using Mangum to work with Vercel's serverless runtime
2. **Lazy Initialization**: AI and search engine clients are now initialized lazily to improve cold start performance
3. **CORS Configuration**: Updated to work with Vercel deployment URLs
4. **Vercel Configuration** (`vercel.json`): Routes API requests to the Python serverless function
5. **Clerk Middleware Configuration** (`middleware.ts`): Configured to exclude `/api/*` routes to prevent conflicts with Python serverless functions

## Deployment Steps

### 1. Install Vercel CLI (if not already installed)

```bash
npm i -g vercel
```

### 2. Set Environment Variables

In the Vercel dashboard or via CLI, set the following environment variables:

**Required:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `EXA_API_KEY` - Your Exa API key
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Clerk public key for authentication
- `CLERK_SECRET_KEY` - Clerk secret key

**Optional:**
- `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account ID (if using Cloudflare AI)
- `CLOUDFLARE_WORKERS_KEY` - Cloudflare Workers API key (if using Cloudflare AI)
- `NEXT_PUBLIC_BACKEND_URL` - Leave empty or unset to use same-origin requests (recommended for Vercel)

### 3. Deploy

```bash
vercel
```

Or connect your GitHub repository to Vercel for automatic deployments.

## Environment Variables in Vercel

1. Go to your project settings in Vercel dashboard
2. Navigate to "Environment Variables"
3. Add the following variables:
   - `ANTHROPIC_API_KEY` (Production, Preview, Development)
   - `EXA_API_KEY` (Production, Preview, Development)
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (Production, Preview, Development)
   - `CLERK_SECRET_KEY` (Production, Preview, Development)
   - `CLOUDFLARE_ACCOUNT_ID` (optional, if needed)
   - `CLOUDFLARE_WORKERS_KEY` (optional, if needed)

**Note**: Do NOT commit `app/api/config/env.config` to version control. Use Vercel's environment variables instead.

## Frontend Configuration

The frontend uses `NEXT_PUBLIC_BACKEND_URL` to determine the backend URL. For Vercel deployments:

- **Option 1 (Recommended)**: Leave `NEXT_PUBLIC_BACKEND_URL` unset. The frontend will default to `http://localhost:8000` for local development, but in production on Vercel, you should update `lib/searchApi.ts` and `lib/rfq-api.ts` to use relative URLs or detect the environment.

- **Option 2**: Set `NEXT_PUBLIC_BACKEND_URL` to your Vercel deployment URL (e.g., `https://your-app.vercel.app`)

## Local Development

Local development remains unchanged:
- Backend: `python3 app/api/main.py` (runs on port 8000)
- Frontend: `npm run dev` (runs on port 3000)
- The `env.config` file is still used for local development

## Architecture

### Request Flow

1. Client makes request to `/api/*`
2. **Clerk Middleware** (`middleware.ts`) skips `/api/*` routes (excluded from matcher)
3. Vercel routes to `api/index.py` serverless function
4. Mangum converts the request to ASGI format
5. FastAPI app handles the request
6. Response is returned through Mangum back to Vercel

### Authentication Flow

- **Next.js Routes**: Protected by Clerk middleware (sign-in/sign-up pages are public)
- **API Routes** (`/api/*`): Excluded from Clerk middleware, handled by Python serverless function
- This separation prevents routing conflicts and 405 errors

### Serverless Considerations

- **Cold Starts**: The first request after inactivity may be slower due to cold starts
- **Lazy Initialization**: Clients are initialized on first use, not at module load time
- **State**: Each request is handled independently (stateless)
- **Timeouts**: Vercel free tier has execution time limits (10 seconds for Hobby plan)

## Troubleshooting

### API Routes Not Working

1. Check that `vercel.json` is properly configured
2. Verify that `api/index.py` exists and is correct
3. Check Vercel function logs in the dashboard

### Environment Variables Not Loading

1. Ensure variables are set in Vercel dashboard
2. Redeploy after adding new environment variables
3. Check that variable names match exactly (case-sensitive)

### CORS Errors

1. The CORS configuration automatically includes Vercel deployment URLs
2. If you're still seeing CORS errors, check the browser console for the exact origin
3. Verify that `VERCEL_URL` environment variable is being set by Vercel

### Import Errors

1. Ensure `PYTHONPATH` is set correctly in `vercel.json`
2. Check that all dependencies are in `app/api/requirements.txt`
3. Verify that `mangum` is included in requirements.txt

### 405 Method Not Allowed Errors

If you're seeing 405 errors on `/api/*` routes:

1. **Check Clerk Middleware Configuration**: Ensure `middleware.ts` excludes `/api/*` routes from the matcher. The matcher should not include `'/(api|trpc)(.*)'` or should explicitly exclude `api` in the negative lookahead pattern.

2. **Verify Path Prefix Matching**: 
   - FastAPI routes are defined with `/api` prefix (e.g., `@app.post('/api/search/parts')`)
   - Vercel routes `/api/(.*)` to the serverless function
   - Ensure Mangum is correctly forwarding the full path to FastAPI
   - If paths don't match, you may need to adjust either the Vercel routing or FastAPI route definitions

3. **Check Vercel Function Logs**: Look for errors in the Vercel dashboard under Functions → Logs to see if the request is reaching the Python function

4. **Verify HTTP Method**: Ensure the client is using the correct HTTP method (POST for `/api/search/parts`, GET for `/api/health`, etc.)

5. **Test Locally**: Run the FastAPI server locally (`python3 app/api/main.py`) and test the endpoints directly to verify they work outside of Vercel

## File Structure

```
.
├── api/
│   └── index.py              # Vercel serverless function handler
├── app/
│   └── api/
│       ├── app.py            # FastAPI application (refactored for serverless)
│       ├── requirements.txt  # Python dependencies
│       └── ...
├── middleware.ts             # Clerk middleware (excludes /api/* routes)
├── vercel.json               # Vercel configuration
├── requirements.txt          # Root requirements (references app/api/requirements.txt)
└── runtime.txt              # Python version specification
```

## Performance Tips

1. **Keep dependencies minimal**: Only include what's needed
2. **Use lazy initialization**: Already implemented for AI/search clients
3. **Optimize imports**: Avoid heavy imports at module level
4. **Monitor cold starts**: Use Vercel's analytics to track performance

## Limitations

- Vercel free tier has execution time limits
- Cold starts can add latency to first request
- File system is read-only (except `/tmp`)
- Maximum function size limits apply

