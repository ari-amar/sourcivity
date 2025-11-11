import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

export async function POST(request: NextRequest) {
  try {
    const { searchResults } = await request.json();

    if (!searchResults) {
      return NextResponse.json(
        { error: 'Search results are required' },
        { status: 400 }
      );
    }

    const prompt = `Read this search results table carefully. Extract ONLY the manufacturer/company names that appear at the beginning of each part name in the table rows.

For example, if you see:
- "ABB 5 HP 3‑Phase Induction Motor (EM)" → extract "ABB"
- "Siemens 7.5 HP TEFC 3‑Phase Motor (EM)" → extract "Siemens"
- "WEG 10 HP Premium Efficiency Motor (EM)" → extract "WEG"

Look at each row in the table and identify the company name that starts each part description. Do NOT add any companies that are not explicitly shown in the table.

Here is the search results table:
${searchResults}

Return ONLY a valid JSON array with no explanation or additional text. Extract the unique company names from the table.

Return format: ["Company1", "Company2", "Company3"]`;

    const completion = await groq.chat.completions.create({
      model: "llama-3.1-8b-instant",
      messages: [
        {
          role: "system",
          content: "You are a JSON extractor. Return ONLY valid JSON arrays with no explanation or markdown code blocks."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0,
      max_tokens: 200
    });

    const content = completion.choices[0]?.message?.content || '';
    console.log('AI response:', content);

    let suppliers: string[] = [];
    try {
      // Remove markdown code blocks if present
      let cleanContent = content.replace(/```json\s*/g, '').replace(/```\s*/g, '');

      // Try to extract JSON array
      const jsonMatch = cleanContent.match(/\[[\s\S]*?\]/);
      if (jsonMatch) {
        let jsonStr = jsonMatch[0];

        // Fix common JSON issues
        // 1. Fix incomplete last element (missing closing quote)
        jsonStr = jsonStr.replace(/,\s*"([^"]*?)$/, ', "$1"]');
        // 2. Ensure array is properly closed
        if (!jsonStr.endsWith(']')) {
          jsonStr += '"]';
        }

        try {
          suppliers = JSON.parse(jsonStr);
          console.log('Extracted suppliers:', suppliers);
        } catch (parseError) {
          console.log('JSON parsing failed, attempting manual extraction');
          // Fallback: extract quoted strings manually
          const matches = content.match(/"([^"]+)"/g);
          if (matches) {
            suppliers = matches.map(m => m.replace(/"/g, ''));
            console.log('Manually extracted suppliers:', suppliers);
          }
        }
      } else {
        console.log('No JSON array found in response');
      }
    } catch (error) {
      console.log('JSON extraction error:', error);
      suppliers = [];
    }

    // Remove duplicates and filter out empty strings
    suppliers = Array.from(new Set(suppliers.filter(s => s && s.trim())));
    console.log('Final suppliers:', suppliers);
    return NextResponse.json({ suppliers });

  } catch (error) {
    console.error('Error extracting suppliers:', error);
    return NextResponse.json(
      { error: 'Failed to extract suppliers' },
      { status: 500 }
    );
  }
}