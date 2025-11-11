// CSV Export utility for search results

export function exportSearchResultsToCSV(searchResults: string, query: string) {
  try {
    // Parse markdown table from search results
    const lines = searchResults.split('\n');
    const tableLines = lines.filter(line => line.includes('|') && !line.includes('---'));
    
    if (tableLines.length < 2) {
      throw new Error('No table data found in search results');
    }

    // Extract headers and rows
    const headers = tableLines[0].split('|').map(h => h.trim()).filter(h => h);
    const rows = tableLines.slice(1).map(line => 
      line.split('|').map(cell => cell.trim()).filter(cell => cell)
    );

    // Create CSV content
    const csvHeaders = headers.join(',');
    const csvRows = rows.map(row => 
      row.map(cell => {
        // Escape quotes and wrap in quotes if contains comma or quote
        const escaped = cell.replace(/"/g, '""');
        return escaped.includes(',') || escaped.includes('"') || escaped.includes('\n') 
          ? `"${escaped}"` 
          : escaped;
      }).join(',')
    ).join('\n');

    const csvContent = `${csvHeaders}\n${csvRows}`;

    // Create and trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `search-results-${query.replace(/[^a-z0-9]/gi, '-')}-${new Date().getTime()}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  } catch (error) {
    console.error('CSV export failed:', error);
    throw new Error('Failed to export search results to CSV');
  }
}

export function generateConfidenceScore(searchResults: string): number {
  // Simple confidence scoring based on content quality indicators
  let score = 0.5; // Base score
  
  // Check for real URLs (major suppliers)
  const hasRealUrls = /mcmaster-carr|grainger|fastenal|msc|rs-components|digi-key|mouser/i.test(searchResults);
  if (hasRealUrls) score += 0.2;
  
  // Check for specific part numbers
  const hasPartNumbers = /[A-Z0-9]+-[A-Z0-9]+|[A-Z]+\d+|\d+[A-Z]+/i.test(searchResults);
  if (hasPartNumbers) score += 0.15;
  
  // Check for technical specifications
  const hasSpecs = /\d+\s*(mm|in|kg|lb|v|a|w|mpa|psi)/i.test(searchResults);
  if (hasSpecs) score += 0.1;
  
  // Check for material information
  const hasMaterials = /steel|aluminum|brass|copper|plastic|ceramic|rubber/i.test(searchResults);
  if (hasMaterials) score += 0.05;
  
  // Ensure score doesn't exceed 1.0
  return Math.min(score, 1.0);
}