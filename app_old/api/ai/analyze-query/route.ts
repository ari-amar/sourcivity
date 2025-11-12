import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json();

    if (!query || query.trim().length === 0) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    const prompt = `You are an industrial parts search query analyzer. Analyze the following search query and determine if it's specific enough to find relevant parts, or if it's too vague.

Search query: "${query}"

Evaluate the query based on these criteria:
1. Does it include specific dimensions, sizes, or measurements? (e.g., M8, 1/4", 25mm, 5HP)
2. Does it include material specifications? (e.g., stainless steel, aluminum, brass)
3. Does it include technical specifications? (e.g., voltage, RPM, pressure rating, thread pitch)
4. Does it include a part number or specific model?
5. Is it just a generic category term without details? (e.g., "bolt", "motor", "bearing")

Classify the query into one of these levels:
- "specific": Query has enough detail to find relevant parts (has 2+ specific attributes like size, material, specs, or part number)
- "mild": Query is a category term but could use more detail (generic part name with 0-1 specific attributes)
- "severe": Query is extremely vague and will not produce useful results (single generic word like "part", "component", "thing")

Also provide:
1. A brief help text explaining what's missing (if vague)
2. 3-4 example queries that would be more specific (if vague)

Return ONLY valid JSON with this exact structure:
{
  "vaguenessLevel": "specific" | "mild" | "severe",
  "helpText": "string or null",
  "examples": ["example1", "example2", "example3"] or null
}`;

    const completion = await groq.chat.completions.create({
      model: "llama-3.1-8b-instant",
      messages: [
        {
          role: "system",
          content: "You are a JSON analyzer. Return ONLY valid JSON with no explanation, markdown, or additional text."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0.1,
      max_tokens: 500,
      response_format: { type: "json_object" }
    });

    const content = completion.choices[0]?.message?.content || '{}';
    console.log('AI query analysis response:', content);

    let analysis;
    try {
      analysis = JSON.parse(content);
    } catch (parseError) {
      console.error('Failed to parse AI response:', parseError);
      // Fallback to basic analysis
      analysis = {
        vaguenessLevel: 'specific',
        helpText: null,
        examples: null
      };
    }

    // Ensure response has correct structure
    const result = {
      vaguenessLevel: analysis.vaguenessLevel || 'specific',
      helpText: analysis.helpText || null,
      examples: Array.isArray(analysis.examples) ? analysis.examples.slice(0, 4) : null
    };

    console.log('Query analysis result:', result);
    return NextResponse.json(result);

  } catch (error) {
    console.error('Error analyzing query:', error);
    // On error, default to allowing the search
    return NextResponse.json({
      vaguenessLevel: 'specific',
      helpText: null,
      examples: null
    });
  }
}
