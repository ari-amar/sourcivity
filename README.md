# SourceFlow - Industrial Parts Sourcing Platform

AI-powered industrial parts search and sourcing platform with automated RFQ management. Built with Next.js 14, TypeScript, and Groq AI.

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

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check existing issues for solutions
- Review CLAUDE.md for architecture details
