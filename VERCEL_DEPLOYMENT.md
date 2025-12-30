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

## Deployment Steps

### 1. Install Vercel CLI (if not already installed)

```bash
npm i -g vercel
```

### 2. Set Environment Variables

In the Vercel dashboard or via CLI, set the following environment variables:

**Required for Frontend:**
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Your Clerk publishable key (get it from https://dashboard.clerk.com)
- `CLERK_SECRET_KEY` - Your Clerk secret key (get it from https://dashboard.clerk.com)

**Required for Backend (Python API):**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `EXA_API_KEY` - Your Exa API key

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
3. Add the following variables (select "Production", "Preview", and "Development" for each):
   
   **Frontend (Next.js) - Required:**
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Get from https://dashboard.clerk.com → API Keys
   - `CLERK_SECRET_KEY` - Get from https://dashboard.clerk.com → API Keys
   
   **Backend (Python API) - Required:**
   - `ANTHROPIC_API_KEY` - Your Anthropic API key
   - `EXA_API_KEY` - Your Exa API key
   
   **Optional:**
   - `CLOUDFLARE_ACCOUNT_ID` - Cloudflare account ID (if using Cloudflare AI)
   - `CLOUDFLARE_WORKERS_KEY` - Cloudflare Workers API key (if using Cloudflare AI)
   - `NEXT_PUBLIC_BACKEND_URL` - Leave unset for same-origin requests (recommended)

**Note**: 
- Do NOT commit `app/api/config/env.config` to version control. Use Vercel's environment variables instead.
- Make sure to select all three environments (Production, Preview, Development) when adding variables
- Variables starting with `NEXT_PUBLIC_` are exposed to the browser and must be set for the build to succeed

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
2. Vercel routes to `api/index.py` serverless function
3. Mangum converts the request to ASGI format
4. FastAPI app handles the request
5. Response is returned through Mangum back to Vercel

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
4. For `NEXT_PUBLIC_*` variables, they must be set before the build runs

### Clerk Authentication Errors

**Error: "Missing publishableKey"**
- This means `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is not set in Vercel
- Go to Vercel dashboard → Project Settings → Environment Variables
- Add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` with your Clerk publishable key
- Add `CLERK_SECRET_KEY` with your Clerk secret key
- Make sure to select all environments (Production, Preview, Development)
- Redeploy after adding the variables

**Getting Clerk Keys:**
1. Go to https://dashboard.clerk.com
2. Select your application (or create one)
3. Navigate to "API Keys" in the sidebar
4. Copy the "Publishable key" (starts with `pk_test_` or `pk_live_`)
5. Copy the "Secret key" (starts with `sk_test_` or `sk_live_`)
6. Add both to Vercel environment variables

### CORS Errors

1. The CORS configuration automatically includes Vercel deployment URLs
2. If you're still seeing CORS errors, check the browser console for the exact origin
3. Verify that `VERCEL_URL` environment variable is being set by Vercel

### Import Errors

1. Ensure `PYTHONPATH` is set correctly in `vercel.json`
2. Check that all dependencies are in `app/api/requirements.txt`
3. Verify that `mangum` is included in requirements.txt

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

