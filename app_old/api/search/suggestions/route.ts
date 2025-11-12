import { NextRequest, NextResponse } from 'next/server';

// Mark this route as dynamic
export const dynamic = 'force-dynamic';

async function analyzeQueryVagueness(query: string): Promise<{ isVague: boolean; level?: 'mild' | 'severe'; helpText?: string; examples?: string[] }> {
  try {
    // Call AI analyzer
    const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/ai/analyze-query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      console.error('AI analyzer failed, defaulting to not vague');
      return { isVague: false };
    }

    const analysis = await response.json();
    console.log('AI vagueness analysis:', analysis);

    // Map AI response to our format
    if (analysis.vaguenessLevel === 'specific') {
      return { isVague: false };
    }

    return {
      isVague: true,
      level: analysis.vaguenessLevel === 'severe' ? 'severe' : 'mild',
      helpText: analysis.helpText,
      examples: analysis.examples,
    };
  } catch (error) {
    console.error('Error analyzing query vagueness:', error);
    // On error, default to allowing the query
    return { isVague: false };
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('query');

    if (!query || query.length < 3) {
      return NextResponse.json({ suggestions: [] });
    }

    // Analyze query vagueness with AI
    const vaguenessAnalysis = await analyzeQueryVagueness(query);

    // Database lookup for suggestions - ordered by popularity
    // This simulates the original database query with ILIKE for case-insensitive search
    const mockDatabaseSuggestions = [
      { suggestion: 'ceramic capacitor 10uF 50V', category: 'Capacitors', popularityScore: 95 },
      { suggestion: 'stainless steel hex bolt M8x20', category: 'Fasteners', popularityScore: 88 },
      { suggestion: 'ball bearing 6205-2RS', category: 'Bearings', popularityScore: 82 },
      { suggestion: 'O-ring Viton 2-010', category: 'Seals', popularityScore: 79 },
      { suggestion: 'pneumatic fitting 1/4 NPT', category: 'Fittings', popularityScore: 75 },
      { suggestion: 'aluminum heat sink TO-220', category: 'Thermal', popularityScore: 71 },
      { suggestion: 'copper wire 18AWG stranded', category: 'Wire', popularityScore: 68 },
      { suggestion: 'spring washer M10', category: 'Fasteners', popularityScore: 65 },
      { suggestion: 'carbon resistor 1K ohm 1/4W', category: 'Resistors', popularityScore: 62 },
      { suggestion: 'rubber gasket 3mm thickness', category: 'Seals', popularityScore: 58 },
    ];

    // If query is vague, return example suggestions instead of database matches
    if (vaguenessAnalysis.isVague && vaguenessAnalysis.examples) {
      const exampleSuggestions = vaguenessAnalysis.examples.map(example => ({
        suggestion: example,
        category: 'Example',
      }));

      return NextResponse.json({
        suggestions: exampleSuggestions,
        isVague: true,
        vaguenessLevel: vaguenessAnalysis.level,
        helpText: vaguenessAnalysis.helpText,
      });
    }

    // Filter suggestions using ILIKE-style matching (case-insensitive contains)
    const filteredSuggestions = mockDatabaseSuggestions
      .filter(s => s.suggestion.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => b.popularityScore - a.popularityScore) // Order by popularity
      .slice(0, 10) // Limit to 10 results
      .map(({ suggestion, category }) => ({ suggestion, category })); // Remove popularity from response

    return NextResponse.json({
      suggestions: filteredSuggestions,
      isVague: vaguenessAnalysis.isVague,
      vaguenessLevel: vaguenessAnalysis.level,
      helpText: vaguenessAnalysis.helpText,
    });
  } catch (error) {
    console.error('Error fetching search suggestions:', error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    return NextResponse.json({ error: errorMessage }, { status: 400 });
  }
}