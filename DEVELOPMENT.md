# Development Guide

This guide explains how to run the Sourcivity application locally with the frontend and backend connected.

## Prerequisites

- Node.js (v18 or higher)
- Python 3.8 or higher
- npm or yarn

## Project Structure

- **Frontend**: Next.js application (root directory)
- **Backend**: FastAPI application (`app/api/`)

## Quick Start (Automated)

Run both frontend and backend together. First navigate to the project directory:

```bash
cd /Users/ariamar/Documents/Sourcivity/sourcivity
./start-dev.sh
```

Or run it from anywhere:

```bash
bash /Users/ariamar/Documents/Sourcivity/sourcivity/start-dev.sh
```

This will:
1. Install frontend dependencies
2. Install backend dependencies
3. Start the backend server on `http://localhost:8000`
4. Start the frontend server on `http://localhost:3000`

Press `Ctrl+C` to stop both servers.

## Manual Setup

### 1. Backend Setup

#### Install Dependencies

```bash
cd app/api
pip3 install -r requirements.txt
```

#### Configure Environment

Create `app/api/config/env.config` file with your API keys:

```
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_WORKERS_KEY=your_cloudflare_workers_key
ANTHROPIC_API_KEY=your_anthropic_api_key
EXA_API_KEY=your_exa_api_key
PORT=8000
```

#### Start Backend Server

```bash
cd app/api
python3 main.py
```

The backend will run on `http://localhost:8000`

### 2. Frontend Setup

#### Install Dependencies

```bash
npm install
```

#### Configure Environment

Create `.env.local` file in the root directory:

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

#### Start Frontend Server

```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Available npm Scripts

- `npm run dev` - Start frontend only
- `npm run dev:backend` - Start backend only
- `npm run dev:all` - Start both frontend and backend (uses start-dev.sh)
- `npm run build` - Build frontend for production
- `npm run start` - Start production frontend server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## API Endpoints

The backend provides the following endpoints:

- `GET /api/health` - Health check
- `GET /api/available_client_names` - Get available AI and search clients
- `POST /api/search/parts` - Search for parts
- `POST /api/search/services` - Search for services

## CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:3000`
- `http://localhost:3001`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`

## Troubleshooting

### Backend won't start
- Ensure Python 3 is installed: `python3 --version`
- Check that all dependencies are installed: `pip3 install -r app/api/requirements.txt`
- Verify the `env.config` file exists with proper API keys

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check `.env.local` has `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000`
- Verify CORS is properly configured in `app/api/app.py`
- Check browser console for CORS errors

### Port already in use
- Backend (8000): Change `PORT` in `app/api/config/env.config`
- Frontend (3000): Run `npm run dev -- -p 3001` to use a different port
  - Update `NEXT_PUBLIC_BACKEND_URL` if needed
  - Update CORS settings in backend if using different frontend port
