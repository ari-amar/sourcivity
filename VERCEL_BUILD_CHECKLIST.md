# Vercel Build Checklist

This document lists all potential issues that could cause Vercel build failures and their fixes.

## ✅ Fixed Issues

### 1. TypeScript Type Errors
- **Fixed**: `middleware.ts` - Added proper type annotations for `auth` and `request` parameters
- **Status**: ✅ Resolved

### 2. Missing Clerk Environment Variables
- **Issue**: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` must be set
- **Fix**: Add both variables in Vercel dashboard → Settings → Environment Variables
- **Status**: ⚠️ Requires manual configuration

### 3. Requirements.txt Format
- **Fixed**: Changed from `-r app/api/requirements.txt` to direct dependency listing
- **Reason**: Vercel may not support the `-r` flag for including other requirements files
- **Status**: ✅ Resolved

### 4. SearchResultsData Type Mismatch
- **Fixed**: Removed `searchMode` and `usSuppliersOnly` from return value in `fetchColumnDeterminationAndSearch`
- **Status**: ✅ Resolved

### 5. ProductItem Type Mismatch
- **Fixed**: Updated `sampleProducts.ts` to use `columnData` instead of direct properties
- **Status**: ✅ Resolved

## ⚠️ Required Environment Variables

Make sure these are set in Vercel before deploying:

### Frontend (Next.js)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - **REQUIRED**
- `CLERK_SECRET_KEY` - **REQUIRED**
- `NEXT_PUBLIC_BACKEND_URL` - Optional (leave unset for same-origin)

### Backend (Python API)
- `ANTHROPIC_API_KEY` - **REQUIRED**
- `EXA_API_KEY` - **REQUIRED**
- `CLOUDFLARE_ACCOUNT_ID` - Optional
- `CLOUDFLARE_WORKERS_KEY` - Optional

## 🔍 Potential Runtime Issues

### File System Writes
- **Status**: ✅ Safe
- **Details**: File writes are only in:
  - `local_testing/` directory (not used in production)
  - Debug mode (conditional on `self.debug` flag)
  - Test files (`__main__` blocks won't run in serverless)

### Import Paths
- **Status**: ✅ Verified
- **Details**: All imports use relative paths that work in serverless environment

### CORS Configuration
- **Status**: ✅ Configured
- **Details**: Automatically includes Vercel deployment URLs via `VERCEL_URL` environment variable

## 📋 Pre-Deployment Checklist

- [ ] All environment variables set in Vercel dashboard
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is set (required for build)
- [ ] `CLERK_SECRET_KEY` is set (required for build)
- [ ] `ANTHROPIC_API_KEY` is set (required for API)
- [ ] `EXA_API_KEY` is set (required for API)
- [ ] All variables are set for Production, Preview, and Development environments
- [ ] `vercel.json` is properly configured
- [ ] `api/index.py` exists and exports `handler`
- [ ] `requirements.txt` at root contains all dependencies
- [ ] `runtime.txt` specifies Python version (3.11)

## 🚨 Known Limitations

1. **Cold Starts**: First request after inactivity may be slower
2. **Execution Time**: Vercel free tier has 10-second execution limit
3. **File System**: Read-only except `/tmp` directory
4. **Package Size**: Maximum function size limits apply

## 🔧 Build Commands

Vercel will automatically:
1. Run `npm install` for Next.js dependencies
2. Run `npm run build` for Next.js build
3. Install Python dependencies from `requirements.txt`
4. Deploy Python serverless function from `api/index.py`

## 📝 Notes

- TypeScript errors shown locally are expected if `node_modules` isn't installed
- Vercel will install dependencies during build
- The build will fail if `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is not set
- All `NEXT_PUBLIC_*` variables must be set before the build runs

