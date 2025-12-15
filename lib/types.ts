// Type definitions for the application

export interface Suggestion {
  suggestion: string;
  category?: string;
}

export interface SearchResultsData {
  response: string;
  query?: string;
  createdAt?: string;
  columns?: string[];
}

// API Response types
export interface SuggestionsResponse {
  suggestions: Suggestion[];
  isVague?: boolean;
  vaguenessLevel?: 'mild' | 'severe';
  helpText?: string;
}

export interface PhotoAnalysisResponse {
  analysis: string;
}

// Search API types
export interface SearchParamsBase {
  usSuppliersOnly: boolean;
}

export interface TextSearchParams extends SearchParamsBase {
  query: string;
  searchMode: 'open' | 'specific';
}

export interface PhotoSearchParams extends SearchParamsBase {
  imageData: string;
}

// Product Table & RFQ Cart types
export interface ProductItem {
  id: string;
  partName: string;
  partUrl: string;
  supplierType: string;
  supplierFlag: string;
  hasSpecSheet: boolean;
  datasheetUrl?: string; // URL to the datasheet PDF
  isVerified?: boolean; // Verified supplier indicator
  rating?: number; // Supplier rating (1-5)
  // Dynamic column data - key is column name, value is the cell content
  columnData: Record<string, string>;
}

export interface RFQCartItem extends ProductItem {
  addedAt: string;
}