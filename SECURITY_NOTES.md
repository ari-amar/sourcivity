# Security Notes for Clerk Keys

## Key Types and Security

### ✅ Publishable Key (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
- **Security Level**: SAFE to expose publicly
- **Purpose**: Used in client-side code (browser)
- **Format**: Starts with `pk_test_` or `pk_live_`
- **Why it's safe**: 
  - Designed to be public (that's why it has `NEXT_PUBLIC_` prefix)
  - Can only be used for client-side authentication
  - Cannot be used to access sensitive data or perform admin operations
  - Similar to a public API endpoint URL

### ⚠️ Secret Key (`CLERK_SECRET_KEY`)
- **Security Level**: MUST be kept secret
- **Purpose**: Used in server-side code only
- **Format**: Starts with `sk_test_` or `sk_live_`
- **Why it's dangerous**:
  - Can perform admin operations
  - Can access user data
  - Can modify authentication settings
  - **NEVER** expose in client-side code or commit to git

## Current Configuration

### Local Development
Your `app/api/config/env.config` file contains both keys. This is **OK for local development** because:
- ✅ The file is in `.gitignore` (line 20: `env.config`)
- ✅ It won't be committed to git
- ✅ It's only used locally

### Vercel Deployment
**DO NOT** put these keys in config files for Vercel. Instead:
- ✅ Use Vercel's Environment Variables dashboard
- ✅ Set them in Project Settings → Environment Variables
- ✅ They will be securely stored and injected at build/runtime

## Vercel's Warning

Vercel is warning you because:
1. It detected a secret key in your codebase
2. Even though it's in `.gitignore`, Vercel scans for security issues
3. It wants to ensure you're using environment variables, not config files

**This is a good warning** - it means Vercel is protecting you!

## Best Practices

### ✅ DO:
- Use environment variables in Vercel dashboard
- Keep `env.config` in `.gitignore` (already done)
- Use `.env.local` for Next.js local development
- Rotate keys if they're ever exposed

### ❌ DON'T:
- Commit secret keys to git
- Put secret keys in client-side code
- Share secret keys publicly
- Use the same keys for development and production

## Recommended Setup

### For Local Development (Next.js)
Create `.env.local` in the project root:
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

### For Local Development (Python Backend)
Keep using `app/api/config/env.config` (already in `.gitignore`):
```env
ANTHROPIC_API_KEY=...
EXA_API_KEY=...
# Don't put Clerk keys here - they're for Next.js only
```

### For Vercel Deployment
Set in Vercel Dashboard → Environment Variables:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (safe to expose)
- `CLERK_SECRET_KEY` (keep secret)

## Summary

**The publishable key is safe** - it's designed to be public.  
**The secret key must be protected** - never commit it or expose it.

Vercel's warning is a safety measure. As long as:
1. Your `env.config` is in `.gitignore` ✅ (it is)
2. You're using Vercel environment variables for deployment ✅
3. You're not committing the secret key to git ✅

You're following security best practices!

