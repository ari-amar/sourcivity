# Python Backend for Exa Search

This directory contains the Python backend server that handles Exa API searches and PDF datasheet scraping.

## Setup

1. Install Python dependencies:
```bash
cd python-backend
pip install -r requirements.txt
```

2. Environment variables are already configured in `.env` file

## Running the Server

```bash
cd python-backend
python web_server.py
```

The server will start on `http://localhost:5001`

## Endpoints

- `POST /search` - Search for datasheets using Exa API
- `POST /compare` - Scrape and compare PDF datasheets

## Integration

The Next.js frontend calls these endpoints via the API routes in `/app/api/search/parts/route.ts`
