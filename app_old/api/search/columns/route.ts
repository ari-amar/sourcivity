import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

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

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Received search columns request`);

  try {
    const { query } = await request.json();

    if (!query) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    console.log(`[${new Date().toISOString()}] Validated input for columns search: "${query}"`);

    const systemPrompt = `You are an expert industrial parts specialist. Your task is to determine the 4 most important and relevant technical specification columns for comparing parts based on a user's search query.

Your response MUST be a valid JSON object with a "columns" key containing an array of exactly 4 strings. Example: {"columns": ["Material", "Dimensions", "Load Rating", "Standards Compliance"]}

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Part Name (it is handled separately)
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Price, Cost, or any pricing information
- Supplier, Manufacturer, or Brand (these are separate fields)
- Any dynamic information that changes frequently

Focus ONLY on static, technical product specifications that are crucial for comparison. Do not add any explanation or commentary. Your output must be ONLY the JSON array.`;

    const userPrompt = `Query: "${query}"`;

    const completion = await groq.chat.completions.create({
      model: "meta-llama/llama-4-maverick-17b-128e-instruct",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.2,
      max_tokens: 256,
      top_p: 1,
      response_format: { type: "json_object" },
    });

    const content = completion.choices[0]?.message?.content;
    if (!content) {
      throw new Error("Groq API returned an empty response.");
    }

    let parsedContent;
    try {
      parsedContent = JSON.parse(content);
    } catch (e) {
      console.error(`[${new Date().toISOString()}] Failed to parse Groq JSON response:`, content);
      throw new Error("Failed to parse column data from AI response. Invalid JSON format.");
    }

    // Extract the columns array from the "columns" key
    const columns = parsedContent?.columns;

    if (!Array.isArray(columns)) {
      console.error(`[${new Date().toISOString()}] Invalid columns format from Groq - missing or invalid 'columns' key:`, parsedContent);
      throw new Error("AI response did not contain a valid 'columns' array.");
    }

    if (columns.length !== 4) {
      console.error(`[${new Date().toISOString()}] Invalid columns count from Groq - expected 4, got ${columns.length}:`, columns);
      throw new Error(`AI response contained ${columns.length} columns instead of the required 4.`);
    }

    if (!columns.every(item => typeof item === 'string' && item.trim().length > 0)) {
      console.error(`[${new Date().toISOString()}] Invalid column types from Groq:`, columns);
      throw new Error("AI response contained invalid column names. All columns must be non-empty strings.");
    }

    const result = { columns };
    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Successfully generated columns for "${query}" in ${totalTime}ms`);

    return NextResponse.json(result);

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error(`[${new Date().toISOString()}] Error in search columns endpoint after ${totalTime}ms:`, errorMessage);
    
    if (error instanceof Error && error.message.includes('rate limit')) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again later.' },
        { status: 429 }
      );
    }

    return NextResponse.json(
      { error: `Failed to determine columns: ${errorMessage}` },
      { status: 500 }
    );
  }
}