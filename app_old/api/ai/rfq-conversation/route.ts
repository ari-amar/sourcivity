import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY,
});

export async function POST(request: NextRequest) {
  try {
    const { query, partDetails, supplierEmails, usSuppliersOnly, rfqDetails, selectedSuppliers } = await request.json();

    if (!query) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    // First, extract suppliers from the part details
    const supplierExtractionPrompt = `You are an expert at identifying industrial supplier and manufacturer names from search results. Analyze the following text and extract ALL company names that could supply industrial parts:

${partDetails || 'No part details provided'}

**Your Task:**
Extract the PRIMARY supplier/distributor from each search result line. Focus on the company you would contact to purchase the part, not the manufacturer.

**Priority rules:**
1. **Extract distributors/suppliers ONLY** (the companies selling the parts)
2. **Ignore manufacturers** when they appear alongside distributors
3. **One supplier per search result line** - the primary contact for purchasing

**Be flexible with formats:**
- "CompanyName" (standalone)
- "CompanyName – search results" 
- "CompanyName.com"
- "CompanyName Part Number XYZ"
- "Available from CompanyName"
- "Contact CompanyName directly"
- "CompanyName 5HP Motor..."
- Any other format where a company name appears

**Intelligence guidelines:**
- Look for well-known industrial company names
- Identify companies mentioned in URLs, links, or part numbers
- Extract brand names that also sell parts
- Include companies mentioned in purchasing contexts
- Remove extra text like "– search results", ".com", "contact directly", etc.
- Focus on the core company name

**Examples of correct extraction:**
- "McMaster-Carr 1/2 HP Motor" → "McMaster-Carr" (distributor)
- "Grainger Baldor 5 HP Motor" → "Grainger" (distributor, NOT Baldor)
- "Digi-Key Siemens 1HP Motor" → "Digi-Key" (distributor, NOT Siemens)
- "Mouser WEG 2 HP Motor" → "Mouser" (distributor, NOT WEG)
- "RS Components ABB Motor" → "RS Components" (distributor, NOT ABB)

**Key principle: Extract WHO YOU CONTACT TO BUY, not who manufactured it.**

Return ONLY a JSON array of unique, clean supplier names.
Format: ["Supplier 1", "Supplier 2", "Supplier 3"]

If no suppliers found, return: []`;

    const supplierCompletion = await groq.chat.completions.create({
      messages: [
        {
          role: 'user',
          content: supplierExtractionPrompt,
        },
      ],
      model: 'llama-3.3-70b-versatile',
      temperature: 0.1,
      max_tokens: 500,
    });

    let extractedSuppliers: string[] = [];
    try {
      const supplierResponse = supplierCompletion.choices[0]?.message?.content || '[]';
      extractedSuppliers = JSON.parse(supplierResponse);
    } catch (error) {
      console.log('Failed to parse supplier extraction response, using empty array');
      extractedSuppliers = [];
    }

    const prompt = `Generate individual RFQ (Request for Quote) email templates for each supplier. Create separate, complete email templates that can be copied individually.

**Part Query**: "${query}"
${partDetails ? `**Part Details**: ${partDetails}` : ''}
${usSuppliersOnly ? '**Supplier Constraint**: US-based suppliers only' : ''}

**Selected Suppliers**: ${selectedSuppliers && selectedSuppliers.length > 0 ? selectedSuppliers.join(', ') : (extractedSuppliers.length > 0 ? extractedSuppliers.join(', ') : 'Generic suppliers')}

**RFQ Requirements:**
- Quantity Needed: ${rfqDetails?.quantity || 'Not specified'}
- Timeline Required: ${rfqDetails?.timeline || 'Not specified'}
${rfqDetails?.additionalRequirements ? `- Additional Requirements: ${rfqDetails.additionalRequirements}` : ''}

**Sender Information:**
- Name: John Doe
- Title: Head of Procurement  
- Company: Sourcivity Inc.
- Email: john.doe@sourcivity.com
- Phone: (555) 123-4567

Create one complete email template for EACH supplier. Use this exact format:

### ${selectedSuppliers && selectedSuppliers.length > 0 ? selectedSuppliers.map((supplier: string) => `
=== ${supplier} Email Template ===

Subject: Request for Quote - [Specific Part Description]

Dear ${supplier} Team,

[Complete professional email body with all details]

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com

===`).join('\n\n') : (extractedSuppliers.length > 0 ? extractedSuppliers.map(supplier => `
=== ${supplier} Email Template ===

Subject: Request for Quote - [Specific Part Description]

Dear ${supplier} Team,

[Complete professional email body with all details]

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com

===`).join('\n\n') : `
=== Email Template ===

Subject: Request for Quote - [Specific Part Description]

Dear Supplier,

[Complete professional email body with all details]

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com

===`)}

**Email Content Requirements:**
- Professional greeting addressing the specific supplier by name
- Company introduction (Sourcivity Inc. - industrial parts sourcing)
- Specific part details from search results
- Exact quantity: "${rfqDetails?.quantity}"
- Required timeline: "${rfqDetails?.timeline}"
${rfqDetails?.additionalRequirements ? `- Additional requirements: "${rfqDetails.additionalRequirements}"` : ''}
- Request for pricing, availability, lead times, shipping costs
- Professional closing with complete contact information
- NO placeholder text - use actual provided information`;

    const completion = await groq.chat.completions.create({
      messages: [
        {
          role: 'user',
          content: prompt,
        },
      ],
      model: 'llama-3.3-70b-versatile',
      temperature: 0.4,
      max_tokens: 2500,
    });

    const rfqContent = completion.choices[0]?.message?.content || 'Unable to generate RFQ';

    console.log('RFQ generation completed:', {
      rfqContentLength: rfqContent.length,
      suppliersCount: extractedSuppliers.length,
      selectedSuppliersCount: selectedSuppliers?.length || 0,
      usSuppliersOnly,
      query
    });

    return NextResponse.json({
      rfqContent,
      suppliers: extractedSuppliers,
      query,
      createdAt: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error in RFQ generation:', error);
    
    if (error instanceof Error && error.message.includes('rate limit')) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again later.' },
        { status: 429 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to generate RFQ conversation' },
      { status: 500 }
    );
  }
}