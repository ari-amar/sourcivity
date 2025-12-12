# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SourceFlow is an AI-powered industrial parts sourcing platform that combines intelligent search using Exa.ai with automated RFQ (Request for Quote) management. Built with Next.js 14 App Router and Python backend.

**Architecture:** Next.js frontend + Python backend (Flask) + Exa.ai API + Claude for spec analysis

## Development Commands

```bash
# Python Backend (Terminal 1)
cd python-backend
pip install -r requirements.txt  # First time only
python web_server.py             # Starts on localhost:5001

# Next.js Frontend (Terminal 2)
npm run dev              # Start development server (localhost:3000)
npm run build            # Build for production
npm run start            # Run production build
npm run lint             # Run ESLint
npm run type-check       # TypeScript compilation check (no output)
```

## Environment Variables

Required in `.env.local`:
- `PYTHON_SERVER_URL` - Python backend URL (default: http://localhost:5001)
- `ANTHROPIC_API_KEY` - Claude API key for selecting top 5 specs from PDFs

Python backend uses `.env` in `python-backend/` directory:
- `EXA_API_KEY` - Exa.ai API key for searching datasheets
- `ANTHROPIC_API_KEY` - Claude API key for extracting specs from PDFs

## Architecture

### Exa.ai + Claude Search Pipeline

The application uses a sophisticated multi-step search and analysis pipeline:

1. **Exa Search** (`/api/search/parts` → Python backend `/search`)
   - User enters industrial part query (e.g., "mass flow controller")
   - Next.js API calls Python Flask backend
   - Python uses Exa.ai API to find top 10 datasheet PDFs
   - Filters for actual PDF files

2. **PDF Scraping & Spec Extraction** (Python backend `/compare`)
   - Downloads up to 5 PDF datasheets
   - Uses PyPDF to extract text from first 10 pages
   - Claude (Sonnet 4.5) extracts standardized technical specs
   - Returns specs with consistent keys across all datasheets

3. **Top 5 Spec Selection** (`/api/search/parts` route)
   - Claude analyzes all extracted specs
   - Selects 5 most important/comparable specs
   - Prioritizes: voltage, current, dimensions, performance metrics
   - Filters out redundant specs like manufacturer/part number

4. **Markdown Table Generation**
   - Converts comparison data to markdown table
   - Columns: Part Name + Top 5 Specs
   - Each row links to original PDF datasheet
   - Displayed in frontend with clickable links

### Search Flow

```
User Query
  ↓
Next.js API (/api/search/parts)
  ↓
Python Backend (/search) - Exa.ai API
  ↓
Find Top 10 PDF Datasheets
  ↓
Python Backend (/compare) - Claude PDF Analysis
  ↓
Extract Specs from 5 PDFs (standardized keys)
  ↓
Claude Selects Top 5 Most Important Specs
  ↓
Markdown Table with Specs
  ↓
Frontend Display
```

### RFQ Management System

RFQs flow through multiple states tracked in `mockRFQDatabase` in-memory array (`lib/rfq-api.ts`):

**Status Flow:**
```
sent → opened → responded/quote_received
  ↓
follow_up_1 (3 days) → follow_up_2 (7 days) → final_notice (14 days) → non_responsive
```

**Key Components:**
- **Dashboard** (`/rfq-dashboard`) - Central monitoring interface
- **In-Memory Database** (`lib/rfq-api.ts`) - All RFQ operations use mock in-memory storage
- **Mock Cron Job** - Simulated follow-up processing (no actual emails sent)
- **Follow-up Templates** (`lib/rfq-types.ts`) - Three escalating urgency levels

**Mock Follow-up Logic:**
- All email operations are simulated
- Status changes update in-memory database only
- Manual trigger via "Test Cron Job" button demonstrates workflow

### Component Architecture

**Search Page Flow** (`app/search/page.tsx`):
1. User enters query "precision linear bearing"
2. Suggestions disabled in demo mode
3. Submit triggers `useColumnDeterminationAndSearch` hook
4. `SearchResults` component shows loading/error/data states
5. `SearchResultsContent` processes markdown tables to HTML with clickable links
6. Suppliers extracted from mock data
7. User selects suppliers → generates RFQ → fills details → creates mock email templates
8. Email modal validates recipient/sender → simulates sending → creates RFQ record in-memory

**RFQ Dashboard Flow** (`app/rfq-dashboard/page.tsx`):
1. Loads RFQs and stats from in-memory database via React Query hooks
2. User actions: view conversation, send follow-up, update status (all simulated)
3. `FollowUpApprovalModal` - Review before "sending" (no actual emails)
4. `ConversationModal` - View simulated email thread
5. All mutations update in-memory database and invalidate queries to refresh data

### State Management

React Query handles all mock data operations:
- **Queries**: parts search, RFQ list, stats from in-memory database
- **Mutations**: create RFQ, update status, send follow-up, trigger mock cron
- **Invalidation**: Mutations auto-invalidate related queries to refresh data from in-memory storage

Local component state:
- Search: sidebar visibility, retry state with circuit breaker
- RFQ: modal open/closed, selected RFQ, follow-up type

**In-Memory Database** (`lib/rfq-api.ts`):
- `mockRFQDatabase` - Array storing all RFQ records during session
- Data persists only while app is running - refreshing page clears all RFQs
- No persistence layer or backend storage

### Markdown to HTML Processing

`SearchResultsContent` (components/SearchResultsContent.tsx) converts AI-generated markdown tables to interactive HTML:

1. **Table Detection**: Scans for pipe-delimited rows, skips separator lines
2. **Header Enhancement**: Injects "Datasheets" as second column
3. **Link Processing**: Converts `[text](url)` to clickable `<a>` tags
4. **Datasheet Column**: Adds clickable 📄 emoji (placeholder for future feature)
5. **Row Filtering**: Removes empty rows and separator lines

Critical: First column is "Part Name & Supplier Type" with format `[PartName (Type)](URL)` where Type is determined by AI analyzing the domain (EM, Distributor, etc.)

### Error Handling & Retry Logic

**Search Retry** (app/search/page.tsx):
- Tracks consecutive failures and retry count
- Circuit breaker threshold: 3 consecutive failures
- Max retry attempts: 3 per search
- Reset on success or new search
- User can manually retry if available

**Mock Data Handling**:
- Only "precision linear bearing" query returns results
- All other queries return helpful error message
- No actual API calls or timeouts

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

**Adding new mock search data:**
- Add new entries to `DUMMY_SEARCH_DATA` in `lib/dummyData.ts`
- Include query, response markdown table, and columns

**Changing RFQ workflow:**
- Modify status types in `lib/rfq-types.ts`
- Update mock mutation logic in `lib/rfq-api.ts`
- Adjust follow-up rules and templates in `lib/rfq-types.ts`

**Styling changes:**
- Global styles: `app/globals.css`
- Tailwind config: `tailwind.config.js`
- Component variants: individual component files

**Converting to Full-Stack:**
To add backend functionality back:
1. Create Next.js API routes in `app/api/` directory
2. Replace mock functions in `lib/rfq-api.ts` and `lib/searchApi.ts` with real API calls
3. Add database (PostgreSQL, MongoDB, etc.)
4. Replace `mockRFQDatabase` in-memory array with database queries
5. Add authentication and proper security
6. Restore removed dependencies: `groq-sdk`, `agentmail`

## Key Features

- **Real-time Datasheet Search**: Powered by Exa.ai neural search
- **Automated Spec Extraction**: Claude extracts and standardizes specs from PDFs
- **Intelligent Comparison**: Claude selects the 5 most relevant specs for comparison
- **Side-by-Side Analysis**: Compare multiple industrial parts automatically
- **RFQ Management**: Track quotes and follow-ups (in-memory for demo)

## Limitations

- RFQ data stored in-memory only (no database persistence)
- Email sending simulated (no actual emails sent)
- PDF scraping limited to first 10 pages per datasheet
- Maximum 5 PDFs compared per search
- Requires both Python backend and Next.js frontend running
