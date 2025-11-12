import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

// Initialize Groq client with validation
const validateApiKey = (key: string | undefined, serviceName: string): string => {
  if (!key) {
    throw new Error(`${serviceName} API key not configured`);
  }
  if (key.trim() === '' || key.includes('your-api-key') || key.includes('placeholder') || key === 'undefined') {
    throw new Error(`${serviceName} API key appears to be a placeholder value. Please check your configuration.`);
  }
  return key;
};

const groq = new Groq({
  apiKey: validateApiKey(process.env.GROQ_API_KEY, 'Groq')
});

// Simplified timeout configuration
const TIMEOUT_CONFIG = {
  serverIdleTimeoutMs: 30000,  // 30s for server-side idle timeout
};

// Fallback response for malformed queries only
function createFallbackResponse(query: string) {
  console.log("Creating fallback response for malformed query:", query);
  
  return {
    response: `# Parts Search Results

Your search query "${query}" appears to be malformed or unclear. Please try a more specific search.

| Manufacturer | Description | Supplier Type | US Supplier | Sources |
|--------------|-------------|---------------|-------------|---------|
| Various | Please refine your search query | Multiple | Yes/No | Try more specific terms |

**Recommendation**: Please provide a more specific part name, model number, or clear description of what you're looking for.`,
    query: query,
    createdAt: new Date(),
  };
}

// Single-step compound search with Groq
async function performCompoundSearch(query: string, usSuppliersOnly: boolean, predeterminedColumns: string[] | undefined, isRetry: boolean = false): Promise<string> {
  const startTime = Date.now();
  console.log(`[${new Date().toISOString()}] Starting compound search for: "${query}"`);

  const locationFilter = usSuppliersOnly ? "US suppliers only" : "global suppliers";
  
  // System prompt - use predetermined columns if provided, otherwise use dynamic column generation
  // On retry, remove predeterminedColumns from systemPrompt
  const systemPrompt = (predeterminedColumns && !isRetry)
    ? `You are an expert industrial parts specialist with deep knowledge of industrial supply chains, part specifications, and supplier networks.

Find top 10 ${query} from ${locationFilter} and format as a markdown table with the exact column structure provided.

The table format should be: Part Name & Supplier Type | ${predeterminedColumns.join(' | ')}

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Any dynamic information that changes frequently
- Focus only on static product specifications and attributes that don't change

Requirements:
- The "Part Name & Supplier Type" column should contain descriptive part names that will serve as hyperlink text
- For each row, provide both a descriptive part name AND the corresponding full-path URL
- IMPORTANT: Analyze each URL domain and intelligently determine the MOST ACCURATE supplier type from this list:
  * Raw Materials Supplier - Companies that supply basic/raw materials (metals, plastics, chemicals, etc.)
  * Component Supplier - Suppliers of individual components or parts
  * Subassembly Supplier - Suppliers of pre-assembled component groups
  * Contract Manufacturer (CM) - Companies that manufacture products for other brands
  * Original Equipment Manufacturer (OEM) - Companies that make original products/equipment
  * Finished Goods Supplier - Suppliers of complete, ready-to-use products
  * Distributor - Companies that distribute products from multiple manufacturers (e.g., McMaster, Grainger, Digi-Key, Mouser, RS Components)
  * Wholesaler - Companies selling in bulk to retailers or businesses
  * Retailer - Companies selling directly to end consumers
  * Service Provider (SP) - Companies providing specialized services
  * Logistics Provider (3PL) - Shipping, warehousing, and supply chain services
  * Maintenance & Repair Supplier (MRO) - Maintenance, Repair, Operations suppliers
  * Testing & Calibration Provider (T&C) - Companies providing testing/calibration services
  * IT & Software Provider (ITSP) - Technology and software service companies
  * Packaging Supplier - Suppliers of packaging materials and solutions
  * Recycling & EoL Supplier - Companies handling product disposal/recycling
- Format: [Part Name (Supplier Type)](URL)
- Use the EXACT supplier type names from the list above including abbreviations in parentheses where specified

URL REQUIREMENTS (CRITICAL FOR ACCURACY):
- ONLY include URLs you are confident exist and lead to actual product pages
- Prefer major verified distributors: McMaster-Carr, Grainger, Fastenal, MSC Industrial, RS Components, Digi-Key, Mouser, Newark
- Use manufacturer websites only if they have direct product pages with specifications
- NEVER fabricate or guess URLs - if uncertain, use "#" as placeholder
- URLs should follow actual URL patterns (e.g., mcmaster.com uses product codes, grainger.com uses /product/...)
- Double-check that part numbers and specifications are consistent with the URL domain

QUALITY CHECKS:
- Verify part specifications are realistic and match industry standards
- Ensure consistency across all columns for each row
- Cross-reference specifications to avoid conflicts (e.g., a 1/4" bolt can't have M8 threading)
- Keep descriptions under 50 words
- Add brief recommendation after table (3 lines max)
- Start immediately with results`
    : `You are an expert industrial parts specialist with deep knowledge of industrial supply chains, part specifications, and supplier networks.

Silently determine the category of "${query}" and auto-generate 4 relevant columns that matter most for that specific category type. Always include "Part Name" as the FIRST column.

Category examples and their typical columns:
- Raw Materials: Material Grade, Purity, Origin, Certifications
- Electronic Components: Specifications, Package Type, Voltage Rating, Tolerance
- Mechanical Components: Material, Dimensions, Load Rating, Standards
- Machinery: Power Rating, Capacity, Features, Brand
- Process Equipment: Temperature Range, Pressure Rating, Material, Capacity
- Fasteners: Material, Thread Size, Grade, Finish
- Bearings: Bore Size, Type, Load Rating, Seal Type
- Sensors: Measurement Range, Output Type, Accuracy, Interface
- Motors: Power Rating, Voltage, Speed, Frame Size
- Valves: Size, Pressure Rating, Material, Actuation Type

CRITICAL REQUIREMENTS FOR ACCURACY:
1. Only include parts that ACTUALLY EXIST and are currently available
2. Verify all specifications are realistic and match actual products
3. Use real manufacturer part numbers when possible
4. Ensure URLs lead to actual product pages (prefer major distributors)
5. Cross-reference specifications to ensure consistency
6. Prioritize well-known, reputable suppliers

Find top 10 ${query} from ${locationFilter} and format as a markdown table with "Part Name & Supplier Type" as the first column + your 4 dynamically determined columns.

The table format should be: Part Name & Supplier Type | [4 dynamic columns based on category]

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Any dynamic information that changes frequently
- Focus only on static product specifications and attributes that don't change

Requirements:
- The "Part Name & Supplier Type" column should contain descriptive part names that will serve as hyperlink text
- For each row, provide both a descriptive part name AND the corresponding full-path URL
- IMPORTANT: Analyze each URL domain and intelligently determine the MOST ACCURATE supplier type from this list:
  * Raw Materials Supplier - Companies that supply basic/raw materials (metals, plastics, chemicals, etc.)
  * Component Supplier - Suppliers of individual components or parts
  * Subassembly Supplier - Suppliers of pre-assembled component groups
  * Contract Manufacturer (CM) - Companies that manufacture products for other brands
  * Original Equipment Manufacturer (OEM) - Companies that make original products/equipment
  * Finished Goods Supplier - Suppliers of complete, ready-to-use products
  * Distributor - Companies that distribute products from multiple manufacturers (e.g., McMaster, Grainger, Digi-Key, Mouser, RS Components)
  * Wholesaler - Companies selling in bulk to retailers or businesses
  * Retailer - Companies selling directly to end consumers
  * Service Provider (SP) - Companies providing specialized services
  * Logistics Provider (3PL) - Shipping, warehousing, and supply chain services
  * Maintenance & Repair Supplier (MRO) - Maintenance, Repair, Operations suppliers
  * Testing & Calibration Provider (T&C) - Companies providing testing/calibration services
  * IT & Software Provider (ITSP) - Technology and software service companies
  * Packaging Supplier - Suppliers of packaging materials and solutions
  * Recycling & EoL Supplier - Companies handling product disposal/recycling
- Format: [Part Name (Supplier Type)](URL)
- Use the EXACT supplier type names from the list above including abbreviations in parentheses where specified

URL REQUIREMENTS (CRITICAL FOR ACCURACY):
- ONLY include URLs you are confident exist and lead to actual product pages
- Prefer major verified distributors: McMaster-Carr, Grainger, Fastenal, MSC Industrial, RS Components, Digi-Key, Mouser, Newark
- Use manufacturer websites only if they have direct product pages with specifications
- NEVER fabricate or guess URLs - if uncertain, use "#" as placeholder
- URLs should follow actual URL patterns (e.g., mcmaster.com uses product codes, grainger.com uses /product/...)
- Double-check that part numbers and specifications are consistent with the URL domain

QUALITY CHECKS:
- Verify part specifications are realistic and match industry standards
- Ensure consistency across all columns for each row
- Cross-reference specifications to avoid conflicts (e.g., a 1/4" bolt can't have M8 threading)
- Keep descriptions under 50 words
- Add brief recommendation after table (3 lines max)
- DO NOT show your category analysis or reasoning process
- Start immediately with results`;

  const userPrompt = `Find me top 10 ${query} with verified product URLs and accurate specifications`;

  // Create timeout controller for idle timer (30 seconds of inactivity)
  const timeoutController = new AbortController();
  let idleTimeoutId: NodeJS.Timeout | null = null;

  const resetIdleTimer = () => {
    if (idleTimeoutId) {
      clearTimeout(idleTimeoutId);
    }
    idleTimeoutId = setTimeout(() => {
      timeoutController.abort();
    }, TIMEOUT_CONFIG.serverIdleTimeoutMs);
  };

  // Start the initial idle timer
  resetIdleTimer();

  try {
    console.log(`[${new Date().toISOString()}] Making Groq compound API request with timeout`);

    const completion = await groq.chat.completions.create({
      model: "groq/compound-mini",
      messages: [
        {
          role: "system",
          content: systemPrompt
        },
        {
          role: "user",
          content: userPrompt
        }
      ],
      temperature: 0.3,  // Lower temperature = more focused, accurate results
      max_tokens: 2048,  // Increased for more complete results
      top_p: 0.95,       // Slightly lower for better quality
      stream: true
    }, {
      headers: {
        "Groq-Model-Version": "latest"
      },
      signal: timeoutController.signal
    });

    let resultContent = "";
    
    // Handle streaming response by iterating through chunks
    for await (const chunk of completion) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) {
        resultContent += content;
        // Reset idle timer on every chunk received
        resetIdleTimer();
      }
    }

    // Clear idle timer on successful completion
    if (idleTimeoutId) {
      clearTimeout(idleTimeoutId);
    }

    if (!resultContent || resultContent.trim().length === 0) {
      console.error(`[${new Date().toISOString()}] Groq compound model returned empty content`);
      throw new Error("Groq API returned empty response - please try again");
    }

    const totalTime = Date.now() - startTime;
    console.log(`[${new Date().toISOString()}] Compound search completed successfully in ${totalTime}ms, output length: ${resultContent.length}`);

    return resultContent;

  } catch (error) {
    // Clear idle timer on error
    if (idleTimeoutId) {
      clearTimeout(idleTimeoutId);
    }
    
    // Log the original error for debugging
    console.error(`[${new Date().toISOString()}] Original Groq error:`, error);
    
    // Enhance error messages based on error type
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error(`Search timed out after ${TIMEOUT_CONFIG.serverIdleTimeoutMs/1000} seconds of inactivity - Groq API stopped responding`);
      } else if (error.message.includes('quota')) {
        throw new Error("API quota exceeded - search service temporarily unavailable");
      } else if (error.message.includes('rate limit') || error.message.includes('429')) {
        throw new Error("Rate limit exceeded - API quota may be exhausted");  
      } else if (error.message.includes('network') || error.message.includes('ECONNREFUSED')) {
        throw new Error("Network error connecting to Groq API - please check your connection");
      }
    }
    
    throw error;
  }
}

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Received parts search request`);

  try {
    const { query, searchMode, usSuppliersOnly, predeterminedColumns } = await request.json();

    if (!query) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    console.log(`[${new Date().toISOString()}] Processing search request for query: "${query}"`);

    // Check for obviously malformed queries first
    const trimmedQuery = query.trim().toLowerCase();
    if (trimmedQuery.length < 2 || trimmedQuery === 'test' || trimmedQuery === 'hello' || /^[^a-z0-9\s\-\.]/i.test(trimmedQuery)) {
      console.log(`[${new Date().toISOString()}] Detected malformed query, using fallback response`);
      const fallbackResponse = createFallbackResponse(query);
      const totalTime = Date.now() - requestStartTime;
      console.log(`[${new Date().toISOString()}] Request completed with fallback in ${totalTime}ms`);
      
      return NextResponse.json(fallbackResponse);
    }

    // Single compound search phase with adaptive fallback
    console.log(`[${new Date().toISOString()}] Starting compound search phase`);
    let formattedResponse: string;
    
    try {
      formattedResponse = await performCompoundSearch(query, usSuppliersOnly || false, predeterminedColumns);
    } catch (error) {
      // Check if this is an "empty response" error AND we have predeterminedColumns
      if (error instanceof Error && 
          error.message.includes("empty response") && 
          predeterminedColumns && 
          predeterminedColumns.length > 0) {
        
        console.log(`[${new Date().toISOString()}] Empty response with predetermined columns, retrying without them`);
        
        // Retry without predeterminedColumns
        formattedResponse = await performCompoundSearch(query, usSuppliersOnly || false, undefined, true);
      } else {
        // Re-throw the error if it's not the specific case we handle
        throw error;
      }
    }

    const result = {
      response: formattedResponse,
      query: query,
      createdAt: new Date().toISOString(),
    };

    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Request completed successfully in ${totalTime}ms`);

    return NextResponse.json(result);

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    console.error(`[${new Date().toISOString()}] Error in parts search after ${totalTime}ms:`, error);
    
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    
    if (error instanceof Error && error.message.includes('rate limit')) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again later.' },
        { status: 429 }
      );
    }

    return NextResponse.json(
      { error: `Parts search failed: ${errorMessage}` },
      { status: 500 }
    );
  }
}