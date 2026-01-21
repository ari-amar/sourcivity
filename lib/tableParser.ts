import type { ProductItem } from './types';
import { getDatasheetLink } from './dummyData';

/**
 * Parses AI-generated markdown table into ProductItem array with dynamic columns
 * Expected format from AI:
 * | Part Name & Supplier Type | Column1 | Column2 | Column3 | Column4 |
 * | [PartName (Type)](url) | Value1 | Value2 | Value3 | Value4 |
 */
export function parseTableToProducts(markdownTable: string): ProductItem[] {
  const products: ProductItem[] = [];

  // Split into lines and filter out empty lines
  const lines = markdownTable.split('\n').filter(line => line.trim());

  // Find table rows (lines with |)
  const tableRows = lines.filter(line => line.includes('|'));

  if (tableRows.length < 2) {
    return products; // Need at least header + 1 data row
  }

  // Extract header row to get column names
  const headerRow = tableRows[0];
  const headers = headerRow.split('|').map(h => h.trim()).filter(h => h);

  // First column is always "Part Name & Supplier Type", rest are dynamic
  const columnNames = headers.slice(1);

  // Skip header and separator rows to get data rows
  const dataRows = tableRows.slice(1).filter(row => {
    // Filter out separator rows (contain only -, |, and spaces)
    return !row.match(/^[\s|-]+$/);
  });

  dataRows.forEach((row, index) => {
    try {
      const cells = row.split('|').map(c => c.trim()).filter(c => c);

      if (cells.length < 2) {
        return; // Skip incomplete rows (need at least part name + 1 column)
      }

      // Parse Part Name & Supplier Type: [PartName](url)<!--contact:contactUrl--><br/>🏳️ OEM
      const partCell = cells[0];
      const partMatch = partCell.match(/\[(.*?)\]\((.*?)\)/);

      if (!partMatch) {
        return; // Skip if no valid link found
      }

      const [, partNameWithType, partUrl] = partMatch;

      // Extract contact URL from HTML comment if present
      const contactMatch = partCell.match(/<!--contact:(.*?)-->/);
      const contactUrl = contactMatch ? contactMatch[1] : undefined;

      // Extract extraction error from HTML comment if present
      const errorMatch = partCell.match(/<!--error:(.*?)-->/);
      const extractionError = errorMatch && errorMatch[1] ? errorMatch[1] : undefined;

      // Extract part name (before any emoji or type info)
      let partName = partNameWithType.trim();

      // Try to split into manufacturer and product name
      // Format is typically "Manufacturer ProductName" or "Manufacturer Product Name Series"
      const nameParts = partName.split(' ');
      let manufacturer = nameParts[0] || partName;
      let productName = nameParts.slice(1).join(' ') || '';

      // Check for content after the link (like <br/>🇺🇸 OEM<br/>✓ 4.8★)
      const afterLinkMatch = partCell.match(/\]\(.*?\)(.+)/);
      let supplierType = 'OEM'; // Default to OEM
      let supplierFlag = '🇺🇸'; // Default flag
      let isVerified = false;
      let rating: number | undefined;

      if (afterLinkMatch) {
        const afterLinkContent = afterLinkMatch[1];

        // Extract emoji (flag) - match specific flag emojis
        if (afterLinkContent.includes('🇺🇸')) {
          supplierFlag = '🇺🇸';
        } else if (afterLinkContent.includes('🇳🇱')) {
          supplierFlag = '🇳🇱';
        } else if (afterLinkContent.includes('🇯🇵')) {
          supplierFlag = '🇯🇵';
        } else if (afterLinkContent.includes('🇬🇧')) {
          supplierFlag = '🇬🇧';
        } else if (afterLinkContent.includes('🇩🇪')) {
          supplierFlag = '🇩🇪';
        } else if (afterLinkContent.includes('🇨🇳')) {
          supplierFlag = '🇨🇳';
        }

        // Extract supplier type (OEM, Distributor, etc.)
        const typeMatch = afterLinkContent.match(/\b(OEM|Distributor|EM|Manufacturer)\b/i);
        if (typeMatch) {
          supplierType = typeMatch[1];
        }

        // Extract verification status (✓ checkmark)
        isVerified = afterLinkContent.includes('✓');

        // Extract rating (e.g., "4.8★" or "4.8 ★")
        const ratingMatch = afterLinkContent.match(/([\d.]+)\s*★/);
        if (ratingMatch) {
          rating = parseFloat(ratingMatch[1]);
        }
      }

      // Parse dynamic column data
      const columnData: Record<string, string> = {};

      // Map each column name to its corresponding cell value
      columnNames.forEach((columnName, colIndex) => {
        const cellIndex = colIndex + 1; // +1 because first cell is part name
        const cellValue = cells[cellIndex] || 'N/A';
        columnData[columnName] = cellValue;
      });

      // Get datasheet URL for this part
      const datasheetUrl = getDatasheetLink(partName);

      const product: ProductItem = {
        id: `product-${index}-${Date.now()}`,
        partName,
        manufacturer,
        productName,
        partUrl,
        contactUrl,
        supplierType,
        supplierFlag,
        hasSpecSheet: !!datasheetUrl, // Has spec sheet if we have a datasheet URL
        datasheetUrl,
        isVerified,
        rating,
        extractionError,
        columnData
      };

      products.push(product);
    } catch (error) {
      console.error('Error parsing table row:', row, error);
    }
  });

  return products;
}

/**
 * Detects if the response contains a table structure
 */
export function hasTableStructure(text: string): boolean {
  const lines = text.split('\n');
  const tableLines = lines.filter(line => line.includes('|'));

  // Check if we have at least 2 rows with pipes (header + data)
  if (tableLines.length < 2) {
    return false;
  }

  // Check if there's a separator row
  const hasSeparator = tableLines.some(line => line.match(/^[\s|-]+$/));

  return hasSeparator || tableLines.length >= 3;
}

/**
 * Extracts column names from the markdown table header
 */
export function extractColumnNames(markdownTable: string): string[] {
  const lines = markdownTable.split('\n').filter(line => line.trim());
  const tableRows = lines.filter(line => line.includes('|'));

  if (tableRows.length < 1) {
    return [];
  }

  // Get header row (first row with pipes)
  const headerRow = tableRows[0];
  const headers = headerRow.split('|').map(h => h.trim()).filter(h => h);

  // Skip first column (Part Name & Supplier Type) and return the rest
  return headers.slice(1);
}
