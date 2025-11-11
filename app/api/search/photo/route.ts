import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { imageData, usSuppliersOnly } = await request.json();

    if (!imageData) {
      return NextResponse.json(
        { error: 'Image data is required' },
        { status: 400 }
      );
    }

    // Use Groq vision model for photo analysis
    const analysisPrompt = `Analyze this industrial component image and provide detailed identification information:

1. **Component Type**: Identify the specific type of industrial part
2. **Visible Markings**: List any part numbers, manufacturer logos, or text visible
3. **Physical Characteristics**: Describe material, finish, dimensions, mounting features
4. **Likely Applications**: Suggest where this component is typically used
5. **Search Keywords**: Provide specific terms for finding this part

Provide a detailed technical analysis for industrial parts sourcing.`;

    const completion = await groq.chat.completions.create({
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: analysisPrompt
            },
            {
              type: 'image_url',
              image_url: {
                url: imageData // Base64 data URL
              }
            }
          ],
        },
      ],
      model: 'meta-llama/llama-4-maverick-17b-128e-instruct',
      temperature: 0.3,
      max_tokens: 1500,
    });

    const analysis = completion.choices[0]?.message?.content || 'Unable to analyze image';

    return NextResponse.json({
      analysis,
    });
  } catch (error) {
    console.error('Error in photo analysis:', error);
    
    return NextResponse.json(
      { error: 'Failed to analyze photo' },
      { status: 500 }
    );
  }
}