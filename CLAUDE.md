# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SourceFlow is an AI-powered industrial parts sourcing platform that combines intelligent search with automated RFQ (Request for Quote) management. Built with Next.js 14 App Router, it uses multiple Groq AI models for different specialized tasks.

## Development Commands

```bash
# Development
npm run dev              # Start development server (localhost:3000)
npm run build            # Build for production
npm run start            # Run production build
npm run lint             # Run ESLint
npm run type-check       # TypeScript compilation check (no output)

# Deployment
vercel                   # Deploy to Vercel
```

## Environment Variables

Required:
- `GROQ_API_KEY` - Groq API key for all AI functionality

Optional:
- `AGENTMAIL_API_KEY` - Email sending via AgentMail (falls back to simulation mode)
- `AGENTMAIL_WEBHOOK_SECRET` - Webhook signature verification

## Architecture

### Multi-Model AI Pipeline

The application uses a specialized multi-model architecture where different Groq models handle specific tasks:

1. **Column Determination** (`/api/search/columns`)
   - Model: `llama-4-maverick-17b-128e-instruct`
   - Analyzes query and determines 4 most relevant technical specification columns
   - Returns JSON: `{"columns": ["Col1", "Col2", "Col3", "Col4"]}`

2. **Parts Search** (`/api/search/parts`)
   - Model: `groq/compound-mini` (web search enabled)
   - Takes query + predetermined columns from step 1
   - Returns markdown table with parts, specs, and supplier links
   - Streams response with 30-second idle timeout
   - Retry logic: Falls back to dynamic columns if empty response with predetermined columns

3. **Supplier Extraction** (`/api/ai/extract-suppliers`)
   - Model: `llama-3.1-8b-instant`
   - Extracts distributor/supplier names from search results table
   - Focuses on who to contact for purchasing (not manufacturers)

4. **RFQ Generation** (`/api/ai/rfq-conversation`)
   - Model: `llama-3.3-70b-versatile`
   - Creates personalized email templates per supplier
   - Two-step process: extract suppliers, then generate emails

5. **Photo Analysis** (`/api/search/photo`)
   - Model: `llama-3.2-90b-vision-preview`
   - Analyzes part images for identification

### Two-API Search Flow

The search workflow is orchestrated by `useColumnDeterminationAndSearch` hook (lib/searchApi.ts:72-106):

```
User Query → Column Determination API → Parts Search API (with columns) → Results
```

This ensures:
- Relevant technical specs are shown for each query type
- Consistent column structure across similar queries
- Optimized token usage by pre-determining table structure

### RFQ Management System

RFQs flow through multiple states tracked in `mockRFQDatabase` (production would use real DB):

**Status Flow:**
```
sent → opened → responded/quote_received
  ↓
follow_up_1 (3 days) → follow_up_2 (7 days) → final_notice (14 days) → non_responsive
```

**Key Components:**
- **Dashboard** (`/rfq-dashboard`) - Central monitoring interface
- **Webhook Handler** (`/api/webhooks/agentmail`) - Processes email events, automatically stops follow-ups when supplier responds
- **Cron Job** (`/api/cron/follow-ups`) - Checks for overdue RFQs and sends automated follow-ups
- **Follow-up Templates** (`lib/rfq-types.ts:74-135`) - Three escalating urgency levels

**Follow-up Logic:**
- When webhook receives supplier response → status changes to `responded`/`quote_received` → follow-ups stop
- Manual trigger via "Test Cron Job" button for testing
- AgentMail tracks opens, clicks, and replies

### Component Architecture

**Search Page Flow** (`app/search/page.tsx`):
1. User enters query or uploads photo
2. Debounced suggestions appear (>2 chars)
3. Submit triggers `useColumnDeterminationAndSearch` hook
4. `SearchResults` component shows loading/error/data states
5. `SearchResultsContent` processes markdown tables to HTML with clickable links
6. AI extracts suppliers automatically after results load
7. User selects suppliers → generates RFQ → fills details → creates email templates
8. Email modal validates recipient/sender → sends via AgentMail → creates RFQ tracking record

**RFQ Dashboard Flow** (`app/rfq-dashboard/page.tsx`):
1. Loads RFQs and stats via React Query hooks
2. User actions: view conversation, send follow-up, update status
3. `FollowUpApprovalModal` - Review before sending (manual approval mode)
4. `ConversationModal` - View email thread and reply
5. All mutations invalidate queries to refresh data

### State Management

React Query handles all server state:
- **Queries**: suggestions, parts search, RFQ list, stats (with stale times)
- **Mutations**: create RFQ, update status, send follow-up, trigger cron
- **Invalidation**: Mutations auto-invalidate related queries for fresh data

Local component state:
- Search: photo upload, sidebar visibility, retry state with circuit breaker
- RFQ: modal open/closed, selected RFQ, follow-up type

### Markdown to HTML Processing

`SearchResultsContent` (components/SearchResultsContent.tsx) converts AI-generated markdown tables to interactive HTML:

1. **Table Detection**: Scans for pipe-delimited rows, skips separator lines
2. **Header Enhancement**: Injects "Datasheets" as second column
3. **Link Processing**: Converts `[text](url)` to clickable `<a>` tags
4. **Datasheet Column**: Adds clickable 📄 emoji (placeholder for future feature)
5. **Row Filtering**: Removes empty rows and separator lines

Critical: First column is "Part Name & Supplier Type" with format `[PartName (Type)](URL)` where Type is determined by AI analyzing the domain (EM, Distributor, etc.)

### Error Handling & Retry Logic

**Search Retry** (app/search/page.tsx:216-244):
- Tracks consecutive failures and retry count
- Circuit breaker threshold: 3 consecutive failures
- Max retry attempts: 3 per search
- Reset on success or new search
- User can manually retry if available

**API Timeout Handling**:
- Groq streaming responses have 30s idle timeout
- AbortController cancels request on timeout
- Clear error messages distinguish timeout vs rate limit vs network errors

### UI Patterns

**Tailwind Configuration**:
- Custom colors: `background`, `foreground`, `surface`, `muted`, `primary`, etc.
- Semantic tokens instead of raw colors for easy theming
- Border utilities use `border-input` and `border-border`

**Component Variants**:
- Buttons: `default`, `outline`, `ghost` (see components/Button.tsx)
- Sizes: `sm`, `md`, `lg`
- Composed with `clsx` and `tailwind-merge` for conflict resolution

**Sidebar State**:
- Search history sidebar defaults to closed (`useState(false)`)
- Toggle with "Show Sidebar" button or close icon

## Key Files to Modify

**Adding new AI models:**
- Update model name in respective `/api/` route
- Adjust `max_tokens` and `temperature` as needed
- For streaming: handle chunks in async iterator

**Changing RFQ workflow:**
- Modify status types in `lib/rfq-types.ts`
- Update webhook handler logic in `/api/webhooks/agentmail/route.ts`
- Adjust follow-up rules and templates in `lib/rfq-types.ts:138-142`

**Styling changes:**
- Global styles: `app/globals.css`
- Tailwind config: `tailwind.config.js`
- Component variants: individual component files

**Database migration:**
- Replace `mockRFQDatabase` arrays with real DB calls in all `/api/rfq/*` routes
- Keep same interface types from `lib/rfq-types.ts`
- Update webhook handler to use DB queries

## Notes on Groq Models

- **Compound models** require `groq/` prefix and support web search
- **Vision models** accept base64 image data
- **Rate limits**: Handle 429 errors gracefully with user-facing messages
- **Streaming**: Always reset idle timer on chunk receipt to prevent premature timeouts
- **JSON mode**: Use `response_format: { type: "json_object" }` for structured outputs
