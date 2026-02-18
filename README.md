# Sourcivity - Industrial Parts & Services Sourcing Platform

AI-powered industrial parts and manufacturing services search platform with intelligent supplier discovery

## Overview

Sourcivity is a dual-search platform that helps procurement professionals find:
- **Industrial Parts**: Technical components with AI-extracted specifications from manufacturer datasheets
- **Manufacturing Services**: CNC machining, 3D printing, injection molding, and other contract manufacturing capabilities

The platform uses AI to understand natural language queries, scrape relevant technical information, and present structured results for easy comparison.

## Features

### 🔍 Dual Search Modes

#### Parts Search
- **PDF Datasheet Analysis**: Automatically downloads and extracts specs from manufacturer PDFs using Docling-based conversion
- **Parallel PDF Processing**: Downloads and processes multiple PDFs concurrently for faster results
- **AI-Powered Specification Extraction**: Uses Claude AI to identify relevant technical parameters
- **Spec Normalization**: AI-driven normalization of specification names across products for consistent comparison
- **Structured Results**: Presents parts in comparable tables with consistent specifications
- **Direct Datasheet Links**: One-click access to source documentation
- **Contact URL Discovery**: Automatically finds supplier contact pages
- **US Supplier Filtering**: Option to show only US-based suppliers

#### Services Search
- **Manufacturing Capability Discovery**: Finds CNC machining, injection molding, 3D printing, and more
- **Web Page Scraping**: Extracts capabilities, certifications, and equipment from supplier websites
- **Structured Service Data**: Standardized format for services offered, certifications (ISO 9001, AS9100), and equipment
- **Company Information**: Direct links to supplier capability pages

### 🤖 AI Architecture

The platform uses a modular AI architecture supporting multiple providers:

**Current Providers:**
- **Anthropic Claude** (claude-3-haiku-20240307) - Primary AI for specification and service extraction
- **Cloudflare AI** - Alternative AI provider (configurable)
- **Exa Search** - Intelligent web search for finding datasheets and supplier pages

**AI Tasks:**
- Natural language query understanding
- PDF-to-markdown conversion via Docling
- Technical specification extraction from datasheets
- Specification name normalization across products
- Manufacturing capability extraction from web pages
- Result filtering and quality assessment
- Structured JSON data generation

For a detailed walkthrough of the search pipeline, see [`docs/search-process.md`](docs/search-process.md).

### 🎨 Modern UI Features

- **Search Mode Toggle**: Switch between Parts and Services search
- **Rotating Suggestions**: Auto-rotating search suggestions (5-second intervals)
- **Real-time Loading States**: Progress indicators during search operations
- **Markdown-to-HTML Rendering**: AI responses rendered with proper formatting
- **Responsive Design**: Built with Tailwind CSS for all screen sizes
- **Search History**: Track and replay previous searches

## Architecture

### Frontend (Next.js 14)
- **Framework**: Next.js 14 with App Router
- **UI**: React 18, TypeScript, Tailwind CSS
- **State Management**: React Query for server state
- **Authentication**: Clerk (user authentication)

### Backend (Python FastAPI)
- **Framework**: FastAPI with async support
- **AI Clients**: Anthropic SDK, Cloudflare SDK
- **Search**: Exa Python SDK for intelligent web search
- **PDF Processing**: Docling (pdf2markdown4llm) for PDF-to-markdown conversion, PyMuPDF for page count validation
- **Web Scraping**: BeautifulSoup4 for HTML parsing

### Data Flow

```
User Query → Frontend (Next.js)
    ↓
    POST /api/search/parts or /api/search/services
    ↓
Backend (FastAPI) → AI Query Generation
    ↓
Exa Search → Find PDFs (parts) or Web Pages (services)
    ↓
Parallel Download & Scrape Content (concurrent PDF/page processing)
    ↓
Batched AI Extraction (Semaphore-limited) → Structured JSON
    ↓
Spec Normalization & Filtering
    ↓
Response → Frontend → Rendered Results
```

## Getting Started

### Prerequisites

- **Node.js**: 18+ (for frontend)
- **Python**: 3.9+ (for backend)
- **API Keys**:
  - Anthropic API key (required)
  - Exa API key (required)
  - Cloudflare credentials (optional)
  - Clerk publishable/secret keys (for auth)

### Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd sourcivity
```

#### 2. Frontend Setup

```bash
# Install Node.js dependencies
npm install

# Create environment file
cp .env.example .env.local
```

Edit `.env.local`:
```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Backend API URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

#### 3. Backend Setup

```bash
# Navigate to backend directory
cd app/api

# Install Python dependencies
pip install -r requirements.txt

# Create environment config
mkdir -p config
touch config/env.config
```

Edit `app/api/config/env.config`:
```env
# AI Provider Keys
ANTHROPIC_API_KEY=sk-ant-...
EXA_API_KEY=...

# Optional: Cloudflare AI
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_WORKERS_KEY=...

# Server Configuration
PORT=8000
```

#### 4. Start Development Servers

**Option A: Run Both Servers Separately**

Terminal 1 (Frontend):
```bash
npm run dev
```

Terminal 2 (Backend):
```bash
cd app/api
python3 main.py
```

**Option B: Run Both Together**

```bash
npm run dev:all
```

This runs `start-dev.sh`, which automatically handles port cleanup, environment validation, and starts both servers with colored logging.

#### 5. Open the Application

Navigate to [http://localhost:3000](http://localhost:3000)

## Usage

### Searching for Parts

1. Select **"Parts"** mode in the search interface
2. Enter a part description:
   - Natural language: "5HP 3-phase motor"
   - Technical specs: "ball bearing 6mm ID 12mm OD"
   - Part numbers: "SKF 6001-2RS"
3. Toggle **"US Suppliers Only"** if needed
4. Click **"Search"**
5. View results in a structured table with extracted specifications

**Example Query:** `precision ball bearings for aerospace`

### Searching for Services

1. Select **"Services"** mode in the search interface
2. Enter a manufacturing capability:
   - Process: "CNC machining titanium"
   - Capability: "injection molding medical grade plastic"
   - Material: "carbon fiber composite fabrication"
3. Click **"Search"**
4. View suppliers with their capabilities, certifications, and equipment

**Example Query:** `ISO 9001 certified CNC machine shop`

## Project Structure

```
sourcivity/
├── app/
│   ├── api/                          # Python FastAPI Backend
│   │   ├── config/
│   │   │   └── env.config           # Backend environment variables
│   │   ├── prompts/
│   │   │   ├── datasheet_extraction_prompts.py
│   │   │   └── service_extraction_prompts.py
│   │   ├── search/
│   │   │   ├── parts.py             # Parts search logic
│   │   │   └── services.py          # Services search logic
│   │   ├── services/
│   │   │   ├── ai_clients/          # Anthropic, Cloudflare clients
│   │   │   └── search_engine_clients/  # Exa client
│   │   ├── utils/
│   │   │   ├── pdf_scraper.py       # PDF datasheet scraping (Docling-based)
│   │   │   └── service_scraper.py   # Web page scraping
│   │   ├── local_testing/           # Local testing utilities
│   │   ├── archive/                 # Archived old implementations
│   │   ├── app.py                   # FastAPI application
│   │   ├── main.py                  # Server entry point
│   │   ├── models.py                # Pydantic models
│   │   ├── enums.py                 # Client name enums
│   │   └── requirements.txt         # Python dependencies
│   ├── search/
│   │   └── page.tsx                 # Main search page
│   ├── layout.tsx                   # Root layout
│   ├── page.tsx                     # Home page (redirects to search)
│   └── globals.css                  # Global styles
├── components/
│   ├── SearchResults.tsx            # Search results container
│   ├── SearchResultsContent.tsx     # Markdown rendering
│   ├── ProductTable.tsx             # Parts table display
│   ├── RFQCart.tsx                  # RFQ cart (if enabled)
│   ├── ClientHeader.tsx             # Navigation header
│   └── ...
├── docs/                            # Internal documentation
│   └── search-process.md           # Detailed search pipeline docs
├── lib/
│   ├── searchApi.ts                 # React Query hooks for search
│   ├── types.ts                     # TypeScript type definitions
│   ├── searchHistoryContext.tsx    # Search history state
│   └── utils.ts                     # Utility functions
├── start-dev.sh                     # Dev startup script (used by npm run dev:all)
└── public/                          # Static assets
```

## Available Scripts

### Frontend Scripts

```bash
npm run dev          # Start Next.js dev server (port 3000)
npm run build        # Build for production
npm run start        # Run production build
npm run lint         # Run ESLint
npm run type-check   # TypeScript type checking
```

### Backend Scripts

```bash
# From app/api directory
python3 main.py      # Start FastAPI server (port 8000)

# Or from project root
npm run dev:backend  # Start backend server
npm run dev:all      # Start both frontend and backend
```

## Environment Variables

### Frontend (.env.local)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Yes | Clerk public key for authentication |
| `CLERK_SECRET_KEY` | Yes | Clerk secret key |
| `NEXT_PUBLIC_BACKEND_URL` | Yes | Backend API URL (default: http://localhost:8000) |

### Backend (app/api/config/env.config)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic Claude API key |
| `EXA_API_KEY` | Yes | Exa search engine API key |
| `CLOUDFLARE_ACCOUNT_ID` | No | Cloudflare account ID (optional provider) |
| `CLOUDFLARE_WORKERS_KEY` | No | Cloudflare Workers AI key (optional provider) |
| `PORT` | No | Backend server port (default: 8000) |

## Key Technologies

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Server state management
- **Clerk** - User authentication
- **Lucide React** - Icon library

### Backend
- **FastAPI** - Modern Python web framework
- **Anthropic SDK** - Claude AI integration
- **Exa Python** - Intelligent web search
- **pdf2markdown4llm** - Docling-based PDF to markdown conversion
- **PyMuPDF** - PDF page count validation
- **BeautifulSoup4** - HTML parsing
- **Pydantic** - Data validation

## Development

### Adding New AI Providers

1. Create a new client class in `app/api/services/ai_clients/`
2. Implement the `AiClientBase` interface
3. Register in `app/api/app.py` AI_CLIENTS dictionary
4. Add corresponding enum value to `enums.py`

### Adding New Search Engines

1. Create a new client class in `app/api/services/search_engine_clients/`
2. Implement the `SearchEngineClientBase` interface
3. Register in `app/api/app.py` SEARCH_ENGINE_CLIENTS dictionary
4. Add corresponding enum value to `enums.py`

### Modifying Extraction Prompts

- **Parts extraction**: Edit `app/api/prompts/datasheet_extraction_prompts.py`
- **Services extraction**: Edit `app/api/prompts/service_extraction_prompts.py`

## Deployment

### Vercel (Frontend)

```bash
npm i -g vercel
vercel
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `NEXT_PUBLIC_BACKEND_URL` (your backend URL)

### Backend Deployment Options

**Option 1: Railway/Render**
1. Connect repository
2. Set build command: `cd app/api && pip install -r requirements.txt`
3. Set start command: `cd app/api && python main.py`
4. Configure environment variables

**Option 2: AWS EC2/GCP Compute**
1. SSH into instance
2. Install Python 3.9+
3. Clone repository
4. Run: `cd app/api && pip install -r requirements.txt && python main.py`

**Option 3: Docker**
```dockerfile
FROM python:3.9
WORKDIR /app
COPY app/api/requirements.txt .
RUN pip install -r requirements.txt
COPY app/api/ .
CMD ["python", "main.py"]
```

## Troubleshooting

### Search Returns Empty Results

- Verify `ANTHROPIC_API_KEY` and `EXA_API_KEY` are set correctly
- Check API key quotas and rate limits
- Review backend logs: `cd app/api && python main.py`
- Check browser console for CORS errors

### Backend Connection Failed

- Ensure backend is running: `cd app/api && python main.py`
- Check backend URL in `.env.local` matches actual backend port
- Verify CORS settings in `app/api/app.py` include your frontend origin

### PDF Extraction Fails

- Check if PDF URLs are accessible (not behind paywalls)
- Verify `pdf2markdown4llm` and `pymupdf` are installed
- PDFs with more than 20 pages are automatically skipped
- If a URL returns HTML instead of a PDF, the scraper will attempt to find linked PDFs
- Review extraction prompts for compatibility with PDF content

### Service Extraction Returns No Data

- Verify target websites are accessible (not blocking scrapers)
- Check `BeautifulSoup4` is properly parsing HTML
- Review service extraction prompts in `service_extraction_prompts.py`

## API Endpoints

### Backend API (FastAPI)

#### GET /api/health
Health check endpoint.

**Response:** `"OK"`

#### POST /api/search/parts
Search for industrial parts from datasheets.

**Request Body:**
```json
{
  "query": "precision ball bearings",
  "ai_client_name": "anthropic",
  "search_engine_client_name": "exa",
  "generate_ai_search_prompt": true,
  "max_results": 10
}
```

**Response:**
```json
{
  "query": "precision ball bearings",
  "spec_column_names": ["Material", "ID", "OD", "Load Rating"],
  "parts": [
    {
      "url": "https://...",
      "title": "SKF 6001-2RS Deep Groove Ball Bearing",
      "specs": {
        "Material": "Chrome Steel",
        "ID": "12mm",
        "OD": "28mm",
        "Load Rating": "5000N"
      }
    }
  ]
}
```

#### POST /api/search/services
Search for manufacturing services.

**Request Body:**
```json
{
  "query": "CNC machining titanium",
  "ai_client_name": "anthropic",
  "search_engine_client_name": "exa",
  "supplier_name": null,
  "max_results": 10
}
```

**Response:**
```json
{
  "query": "CNC machining titanium",
  "services": [
    {
      "title": "Precision CNC Machining Services",
      "url": "https://...",
      "extracted_services": {
        "company_name": "Precision Manufacturing Inc.",
        "services_offered": "CNC Milling, CNC Turning, Wire EDM",
        "capabilities": "Titanium, Stainless Steel, Aluminum",
        "certifications": "ISO 9001:2015, AS9100D",
        "equipment": "5-axis CNC mills, Swiss-style lathes"
      }
    }
  ]
}
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests and type checking: `npm run type-check`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## License

[Add your license here]

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Review existing issues for solutions
- Check backend logs for detailed error messages
