# SourceFlow - Industrial Parts Sourcing Platform

AI-powered industrial parts and services search and sourcing platform with vendor quality and reliability metrics

## Features

### 🔍 Smart Search
- **Natural language search** - "5HP 3-phase motor" or technical specs
- **Part number search** - Direct lookup by manufacturer part numbers
- **AI-powered column determination** - Automatically selects relevant technical specifications
- **US suppliers filter** - Option to filter by US-based suppliers only
- **Real-time suggestions** - Search suggestions as you type

### 📸 Photo-Based Search
- Upload part images for AI-powered identification
- Drag & drop or click to upload (PNG, JPG up to 10MB)
- Vision AI analyzes and identifies parts from photos

### 🤖 Multi-Model AI Architecture
- **groq/compound-mini** - Web-enabled search for parts and specifications
- **llama-4-maverick-17b** - Intelligent column determination
- **llama-3.3-70b-versatile** - RFQ email generation
- **llama-3.1-8b-instant** - Supplier extraction
- **llama-3.2-90b-vision** - Photo analysis

### 📧 Automated RFQ Management
- **Multi-supplier RFQ generation** - Create personalized emails for each supplier
- **Email tracking** - Monitor opens, clicks, and replies via AgentMail
- **Automated follow-ups** - 3-tier follow-up system (3, 7, 14 days)
- **Response detection** - Automatically stops follow-ups when supplier responds
- **Conversation dashboard** - Track all RFQ communications in one place
- **Manual approval mode** - Review follow-ups before sending

### 🎨 Modern UI
- Built with Tailwind CSS and responsive design
- Real-time loading states and error handling
- CSV export for search results
- Clickable datasheets and supplier links

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Groq API key (required)
- AgentMail API key (optional - for email functionality)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd SourceFlow_floot
```

2. **Install dependencies:**
```bash
npm install
```

3. **Set up environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
AGENTMAIL_API_KEY=your_agentmail_key_here  # Optional
AGENTMAIL_WEBHOOK_SECRET=your_webhook_secret  # Optional
```

4. **Run the development server:**
```bash
npm run dev
```

5. **Open your browser:**
Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### Searching for Parts

1. Enter a part description or number in the search box
2. Toggle "US Suppliers Only" if needed
3. Click "Search" or press Enter
4. View results in an AI-generated table with relevant specifications

### Photo Search

1. Click the camera icon in the search box
2. Upload a photo of the part
3. AI will analyze and identify the part
4. Use the analysis to refine your search

### Creating RFQs

1. After searching, view the results table
2. Select suppliers from the list
3. Click "Generate RFQ"
4. Fill in quantity, timeline, and additional requirements
5. Review AI-generated email templates for each supplier
6. Send emails directly or copy templates

### Managing RFQs

1. Navigate to the Messages Dashboard (`/rfq-dashboard`)
2. View all sent RFQs and their status
3. Track opens, responses, and quotes received
4. Send manual follow-ups or let automation handle it
5. View conversation threads and reply to suppliers

## Development

### Project Structure

```
SourceFlow_floot/
├── app/
│   ├── api/                    # API routes
│   │   ├── ai/                # AI endpoints (RFQ, supplier extraction)
│   │   ├── cron/              # Scheduled jobs (follow-ups)
│   │   ├── email/             # Email sending
│   │   ├── rfq/               # RFQ CRUD operations
│   │   ├── search/            # Search endpoints
│   │   └── webhooks/          # Email event webhooks
│   ├── rfq-dashboard/         # RFQ management page
│   ├── search/                # Main search page
│   ├── globals.css            # Global styles
│   ├── layout.tsx             # Root layout
│   └── page.tsx               # Home (redirects to /search)
├── components/                 # React components
│   ├── Button.tsx
│   ├── RFQDashboard.tsx
│   ├── SearchResults.tsx
│   ├── SearchResultsContent.tsx  # Markdown to HTML processing
│   └── ...
├── lib/                       # Utilities and hooks
│   ├── rfq-api.ts            # RFQ React Query hooks
│   ├── rfq-types.ts          # RFQ types and templates
│   ├── searchApi.ts          # Search React Query hooks
│   ├── types.ts              # Type definitions
│   └── utils.ts              # Utility functions
└── public/                    # Static assets
```

### Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Run production build
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

### Key Technologies

- **Frontend**: Next.js 14 (App Router), React 18, TypeScript
- **Styling**: Tailwind CSS, clsx, tailwind-merge
- **Forms**: React Hook Form, Zod validation
- **State**: React Query (@tanstack/react-query)
- **AI**: Groq SDK (multiple models)
- **Email**: AgentMail
- **Icons**: Lucide React

## Deployment

### Vercel (Recommended)

1. **Install Vercel CLI:**
```bash
npm i -g vercel
```

2. **Deploy:**
```bash
vercel
```

3. **Set environment variables in Vercel dashboard:**
   - `GROQ_API_KEY` - Required for all AI functionality
   - `AGENTMAIL_API_KEY` - Optional, enables email sending
   - `AGENTMAIL_WEBHOOK_SECRET` - Optional, for webhook verification

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for AI models |
| `AGENTMAIL_API_KEY` | No | AgentMail key for email sending (falls back to simulation) |
| `AGENTMAIL_WEBHOOK_SECRET` | No | Secret for webhook signature verification |

## Architecture Highlights

### Two-Step Search Process

1. **Column Determination** - AI analyzes query and determines 4 most relevant technical columns
2. **Parts Search** - Compound model searches with predetermined columns, returns structured results

### RFQ Status Flow

```
sent → opened → responded/quote_received ✓
  ↓
follow_up_1 (3 days) → follow_up_2 (7 days) → final_notice (14 days) → non_responsive
```

Webhooks automatically update status and stop follow-ups when suppliers respond.

### Multi-Model Pipeline

Different Groq models specialize in different tasks:
- Search uses web-enabled compound model
- RFQ generation uses high-context versatile model
- Column determination uses fast instruction-following model
- Each model optimized for its specific task

## Migration Notes

This project was migrated from the Floot framework to Next.js:
- ✅ Next.js 14 App Router architecture
- ✅ Tailwind CSS styling system
- ✅ Next.js API routes
- ✅ Modern component structure
- ✅ TypeScript throughout

## Troubleshooting

### Search returns empty results
- Check `GROQ_API_KEY` is set correctly
- Verify API key has sufficient quota
- Check browser console for rate limit errors

### Emails not sending
- Verify `AGENTMAIL_API_KEY` is configured
- Check dashboard shows "Email Configuration Required" warning
- Without AgentMail key, system runs in simulation mode

### RFQ follow-ups not working
- Click "Test Cron Job" button to manually trigger follow-up check
- Check RFQ status is not already `responded` or `quote_received`
- Verify follow-up count hasn't exceeded 3

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and type checking (`npm run type-check`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

[Add your license here]

## Branch Differences: `Ari-Improvements` vs `main`

The `Ari-Improvements` branch contains significant enhancements and architectural changes from the `main` branch. Here's a comprehensive breakdown:

### 🎯 Major Features Added

#### 1. **AI-Powered Query Validation System**
- **NEW**: `/api/ai/analyze-query` - Intelligent query specificity analyzer using `llama-3.1-8b-instant`
- **ENHANCED**: Search suggestions now include vagueness detection with contextual examples
- **NEW**: `VagueQueryModal` component for educational guidance (soft guidance, no blocking)
- **NEW**: Live recommendation feature with adaptive UI (mild/severe vagueness indicators)
- **RESULT**: Users get intelligent guidance toward better searches without frustration

#### 2. **RFQ Cart & Product Management System**
- **NEW**: `ProductTable` component - Interactive parts table with selection, sorting, and filtering
- **NEW**: `RFQCart` component - Shopping cart-style RFQ builder with item management
- **NEW**: `RFQSubmissionModal` - Multi-step RFQ creation with supplier selection
- **NEW**: `rfqCartContext` - Global state management for RFQ cart items
- **NEW**: `tableParser.ts` - AI markdown table to structured data parser
- **NEW**: `sampleProducts.ts` - Mock product data for testing
- **ENHANCED**: Complete RFQ workflow from search → selection → submission

#### 3. **Search History & Context Management**
- **NEW**: `SearchHistorySidebar` - Persistent search history with filtering and replay
- **NEW**: `searchHistoryContext` - Global search history state with localStorage persistence
- **ENHANCED**: Users can quickly revisit past searches and iterate on queries
- **ENHANCED**: Search history shows result counts and US-only filter status

#### 4. **Enhanced Table Processing**
- **NEW**: `tableParser.ts` - Robust markdown-to-structured-data converter
- **NEW**: Support for dynamic columns determined by AI
- **NEW**: Clickable links in table cells with proper URL extraction
- **NEW**: Data validation and normalization for consistent display
- **ENHANCED**: `SearchResultsContent` now handles complex table structures

### 🗑️ Removed Features (Deprecated/Replaced)

#### Database & Thread Management
- **REMOVED**: `lib/db.ts` - Database connection module (moved to mockRFQDatabase)
- **REMOVED**: `lib/logger.ts` - Logging utilities (simplified to console.log)
- **REMOVED**: `lib/thread-api.ts` - Thread-based conversation system
- **REMOVED**: `lib/thread-types.ts` - Thread type definitions
- **REMOVED**: `/api/threads/[id]/route.ts` - Thread detail endpoint
- **REMOVED**: `/api/threads/route.ts` - Thread list endpoint
- **REMOVED**: `components/SearchProgressStepper.tsx` - Multi-step search UI
- **REMOVED**: `middleware.ts` - Custom middleware (not needed)
- **REMOVED**: All database migration scripts in `/scripts/`

**Rationale**: Simplified architecture by using in-memory mock data instead of full database setup. Production version would replace mockRFQDatabase with real DB calls.

### 📝 Modified Files

#### API Routes
| File | Changes |
|------|---------|
| `app/api/search/parts/route.ts` | Added retry logic with dynamic columns, improved error handling, 30s idle timeout |
| `app/api/search/suggestions/route.ts` | Integrated AI vagueness detection, returns contextual examples |
| `app/api/ai/extract-suppliers/route.ts` | Enhanced JSON parsing with fallback logic |
| `app/api/rfq/route.ts` | Updated to work with mockRFQDatabase structure |

#### Components
| File | Changes |
|------|---------|
| `app/search/page.tsx` | Major refactor: removed stepper UI, added cart integration, enhanced error handling, circuit breaker retry logic |
| `components/SearchHistorySidebar.tsx` | Complete redesign with filtering, better UX, localStorage sync |
| `components/SearchResults.tsx` | Simplified, removed threading, added retry UI |
| `components/SearchResultsContent.tsx` | Enhanced table parsing with tableParser.ts, better link handling |
| `components/Badge.tsx` | Added variant styling for different statuses |
| `components/Header.tsx` | Navigation improvements, active state indicators |

#### Core Libraries
| File | Changes |
|------|---------|
| `lib/searchApi.ts` | Added `useColumnDeterminationAndSearch` hook, updated types |
| `lib/types.ts` | Added `ProductItem`, `RFQCartItem`, vagueness metadata types |
| `lib/rfq-api.ts` | Updated for mock database compatibility |
| `app/layout.tsx` | Added `RFQCartProvider` wrapper |
| `app/providers.tsx` | Added search history and RFQ cart providers |

#### Configuration
| File | Changes |
|------|---------|
| `package.json` | Removed database dependencies (pg, better-sqlite3) |
| `package-lock.json` | Updated lock file reflecting dependency changes |
| `.gitignore` | Updated patterns for build artifacts |

### 📚 New Documentation
- **`ENHANCED_TABLE_UI.md`** - Comprehensive guide to the table parsing system
- **`PRODUCT_TABLE_UI.md`** - Documentation for ProductTable component usage

### 🔧 Architecture Changes

#### Before (main branch)
```
Search → Thread-based results → Database persistence → Conversations
```

#### After (Ari-Improvements branch)
```
Search → AI Column Determination → Cart-based RFQ → Mock Database → Email Tracking
         ↓
    Query Validation → Live Recommendations
         ↓
    Search History → Quick Replay
```

### 📊 Statistics
- **+2,755 insertions** / **-2,238 deletions**
- **12 new files** created
- **11 files removed** (deprecated features)
- **18 files modified** (enhancements)
- **Net code reduction** while adding features (better architecture)

### 🚀 Performance Improvements
- Removed database overhead for faster development
- Optimized search retry logic with circuit breaker
- Client-side caching for search history
- Lazy loading for cart and modal components

### 🎨 UX Improvements
- No more blocking modals - soft guidance only
- Persistent search history across sessions
- Cart-based RFQ workflow (familiar e-commerce pattern)
- Better error messages and retry options
- Real-time vagueness detection without interruption

### 🔄 Migration Path
To merge `Ari-Improvements` into `main`:
1. Review removed database dependencies
2. Decide on mock vs. real database for production
3. Update environment variable documentation
4. Test all search and RFQ workflows
5. Update deployment configuration

### ⚠️ Breaking Changes
- Database-dependent features removed (requires migration to mockRFQDatabase or new DB)
- Thread-based conversations replaced with simpler email tracking
- Search stepper UI removed in favor of streamlined flow
- Some utility functions consolidated/simplified

---

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check existing issues for solutions
- Review CLAUDE.md for architecture details
