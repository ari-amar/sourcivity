import { NextRequest, NextResponse } from 'next/server';

const PYTHON_SERVER_URL = process.env.PYTHON_SERVER_URL || 'http://localhost:5001';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query, searchMode, usSuppliersOnly } = body;

    if (!query) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    // Determine if this is a service search or datasheet search
    const isServiceSearch = searchMode === 'services';

    if (isServiceSearch) {
      // Service search flow
      return await handleServiceSearch(query, searchMode, usSuppliersOnly);
    }

    // Datasheet search flow (original logic)
    // Call Python backend for Exa search
    const searchResponse = await fetch(`${PYTHON_SERVER_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        component_name: query,
        num_results: 10,
      }),
    });

    if (!searchResponse.ok) {
      throw new Error(`Python server error: ${searchResponse.status}`);
    }

    const searchData = await searchResponse.json();

    if (!searchData.results || searchData.results.length === 0) {
      return NextResponse.json({
        response: 'No results found',
        query,
        searchMode: searchMode || 'open',
        usSuppliersOnly: usSuppliersOnly || false,
      });
    }

    // Get PDF URLs for comparison
    const pdfUrls = searchData.results
      .filter((r: any) => r.url.toLowerCase().endsWith('.pdf'))
      .slice(0, 5)
      .map((r: any) => r.url);

    if (pdfUrls.length === 0) {
      // No PDFs found, return simple results
      const markdownTable = convertToMarkdownTable(searchData.results);
      return NextResponse.json({
        response: markdownTable,
        query,
        searchMode: searchMode || 'open',
        usSuppliersOnly: usSuppliersOnly || false,
      });
    }

    // Call Python backend to scrape and compare PDFs
    const compareResponse = await fetch(`${PYTHON_SERVER_URL}/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        urls: pdfUrls,
        product_type: query,
      }),
    });

    if (!compareResponse.ok) {
      // Fallback to simple results if comparison fails
      const markdownTable = convertToMarkdownTable(searchData.results);
      return NextResponse.json({
        response: markdownTable,
        query,
        searchMode: searchMode || 'open',
        usSuppliersOnly: usSuppliersOnly || false,
      });
    }

    const compareData = await compareResponse.json();

    // Convert comparison data to markdown table with top 5 specs
    const markdownTable = await convertComparisonToMarkdown(
      compareData.comparison_data,
      compareData.scraped_results
    );

    return NextResponse.json({
      response: markdownTable,
      query,
      searchMode: searchMode || 'open',
      usSuppliersOnly: usSuppliersOnly || false,
    });
  } catch (error: any) {
    console.error('Search error:', error);
    return NextResponse.json(
      { error: error.message || 'Search failed' },
      { status: 500 }
    );
  }
}

async function handleServiceSearch(
  query: string,
  searchMode: string,
  usSuppliersOnly: boolean
): Promise<NextResponse> {
  try {
    // Call Python backend for service search
    const searchResponse = await fetch(`${PYTHON_SERVER_URL}/search-services`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        num_results: 10,
      }),
    });

    if (!searchResponse.ok) {
      throw new Error(`Python server error: ${searchResponse.status}`);
    }

    const searchData = await searchResponse.json();

    if (!searchData.results || searchData.results.length === 0) {
      return NextResponse.json({
        response: 'No service providers found',
        query,
        searchMode,
        usSuppliersOnly,
      });
    }

    // Get service page URLs (limit to top 5 for detailed analysis)
    const serviceUrls = searchData.results
      .slice(0, 5)
      .map((r: any) => r.url);

    if (serviceUrls.length === 0) {
      const markdownTable = convertToMarkdownTable(searchData.results);
      return NextResponse.json({
        response: markdownTable,
        query,
        searchMode,
        usSuppliersOnly,
      });
    }

    // Call Python backend to scrape and compare service pages
    const compareResponse = await fetch(`${PYTHON_SERVER_URL}/compare-services`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        urls: serviceUrls,
        query_context: query,
      }),
    });

    if (!compareResponse.ok) {
      // Fallback to simple results if comparison fails
      const markdownTable = convertToMarkdownTable(searchData.results);
      return NextResponse.json({
        response: markdownTable,
        query,
        searchMode,
        usSuppliersOnly,
      });
    }

    const compareData = await compareResponse.json();

    // Convert comparison data to markdown table
    const markdownTable = await convertServiceComparisonToMarkdown(
      compareData.comparison_data,
      compareData.scraped_results
    );

    return NextResponse.json({
      response: markdownTable,
      query,
      searchMode,
      usSuppliersOnly,
    });
  } catch (error: any) {
    console.error('Service search error:', error);
    throw error;
  }
}

function convertToMarkdownTable(results: any[]): string {
  let markdown = '| Part Name & Supplier | URL | Score |\n';
  markdown += '| --- | --- | --- |\n';

  results.slice(0, 10).forEach((result) => {
    const title = result.title || 'Unknown';
    const url = result.url || '#';
    const score = result.score ? result.score.toFixed(3) : 'N/A';

    markdown += `| [${title}](${url}) | ${url} | ${score} |\n`;
  });

  return markdown;
}

async function convertComparisonToMarkdown(
  comparisonData: any,
  scrapedResults: any[]
): Promise<string> {
  // Use Claude to select top 5 most important specs
  const topSpecs = await selectTopSpecs(comparisonData.spec_names);

  // Build markdown table
  let markdown = '| Part Name | ' + topSpecs.join(' | ') + ' |\n';
  markdown += '| --- | ' + topSpecs.map(() => '---').join(' | ') + ' |\n';

  comparisonData.products.forEach((product: any, index: number) => {
    const url = product.url;
    const partName = product.specs.part_number || product.specs.Part_Number || `Product ${index + 1}`;
    const manufacturer = product.specs.manufacturer || product.specs.Manufacturer || '';

    const title = manufacturer ? `${partName} (${manufacturer})` : partName;
    const specs = topSpecs.map((specKey: string) => {
      const value = product.specs[specKey];
      return value !== null && value !== undefined ? value : '-';
    });

    markdown += `| [${title}](${url}) | ${specs.join(' | ')} |\n`;
  });

  return markdown;
}

async function selectTopSpecs(allSpecs: string[]): Promise<string[]> {
  // Use Claude to intelligently select top 5 most important specs
  const anthropicApiKey = process.env.ANTHROPIC_API_KEY;

  if (!anthropicApiKey || allSpecs.length <= 5) {
    // If no API key or few specs, just return first 5
    return allSpecs.slice(0, 5);
  }

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': anthropicApiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 500,
        messages: [
          {
            role: 'user',
            content: `Given this list of technical specifications from industrial part datasheets, select the 5 MOST IMPORTANT specs that would be most useful for comparing products side-by-side.

Prioritize specifications that:
1. Are critical for product selection (voltage, current, dimensions, performance metrics)
2. Vary between products (not just manufacturer/part number)
3. Are measurable/quantitative

Available specs:
${allSpecs.join(', ')}

Return ONLY a JSON array of exactly 5 spec keys, no other text. Example: ["spec1", "spec2", "spec3", "spec4", "spec5"]`,
          },
        ],
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const content = data.content[0].text;

      // Extract JSON array from response
      const match = content.match(/\[.*\]/);
      if (match) {
        const selectedSpecs = JSON.parse(match[0]);
        if (Array.isArray(selectedSpecs) && selectedSpecs.length === 5) {
          return selectedSpecs;
        }
      }
    }
  } catch (error) {
    console.error('Error selecting top specs with Claude:', error);
  }

  // Fallback: return first 5 specs
  return allSpecs.slice(0, 5);
}

async function convertServiceComparisonToMarkdown(
  comparisonData: any,
  _scrapedResults: any[]
): Promise<string> {
  // Use Claude to select top 5 most important service fields to display
  const topFields = await selectTopServiceFields(comparisonData.fields);

  // Build markdown table
  let markdown = '| Supplier | ' + topFields.map(f => formatFieldName(f)).join(' | ') + ' |\n';
  markdown += '| --- | ' + topFields.map(() => '---').join(' | ') + ' |\n';

  comparisonData.suppliers.forEach((supplier: any) => {
    const url = supplier.url;
    const companyName = supplier.services.company_name || 'Unknown Supplier';

    const fields = topFields.map((fieldKey: string) => {
      const value = supplier.services[fieldKey];

      if (value === null || value === undefined) {
        return '-';
      } else if (Array.isArray(value)) {
        if (value.length === 0) return '-';
        // Join array items with commas, limit to 3 items for readability
        const displayItems = value.slice(0, 3);
        const display = displayItems.join(', ');
        return value.length > 3 ? display + '...' : display;
      } else {
        return String(value);
      }
    });

    markdown += `| [${companyName}](${url}) | ${fields.join(' | ')} |\n`;
  });

  return markdown;
}

async function selectTopServiceFields(allFields: string[]): Promise<string[]> {
  // Use Claude to intelligently select top 5 most important service fields
  const anthropicApiKey = process.env.ANTHROPIC_API_KEY;

  if (!anthropicApiKey || allFields.length <= 5) {
    // If no API key or few fields, return first 5 (excluding company_name which is in first column)
    return allFields.filter(f => f !== 'company_name').slice(0, 5);
  }

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': anthropicApiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 500,
        messages: [
          {
            role: 'user',
            content: `Given this list of supplier service information fields, select the 5 MOST IMPORTANT fields that would be most useful for comparing suppliers side-by-side.

Prioritize fields that:
1. Are critical for supplier selection (services offered, capabilities, certifications)
2. Provide actionable information (location, lead time, MOQ)
3. Help differentiate suppliers from each other

DO NOT include "company_name" as it's already in the first column.

Available fields:
${allFields.join(', ')}

Return ONLY a JSON array of exactly 5 field keys, no other text. Example: ["field1", "field2", "field3", "field4", "field5"]`,
          },
        ],
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const content = data.content[0].text;

      // Extract JSON array from response
      const match = content.match(/\[.*\]/);
      if (match) {
        const selectedFields = JSON.parse(match[0]);
        if (Array.isArray(selectedFields) && selectedFields.length === 5) {
          return selectedFields;
        }
      }
    }
  } catch (error) {
    console.error('Error selecting top service fields with Claude:', error);
  }

  // Fallback: return first 5 fields (excluding company_name)
  return allFields.filter(f => f !== 'company_name').slice(0, 5);
}

function formatFieldName(fieldKey: string): string {
  // Convert snake_case to Title Case
  return fieldKey
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
