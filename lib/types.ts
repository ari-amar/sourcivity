// Type definitions for the application

export interface Suggestion {
  suggestion: string;
  category?: string;
}

export interface TimingData {
  total: number;
  network: number;
  parse: number;
  transform?: number;
  backend?: any;
}

export interface SearchResultsData {
  response: string;
  query?: string;
  searchMode?: string;
  usSuppliersOnly?: boolean;
  createdAt?: string;
  columns?: string[];
  timing?: TimingData;
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
  searchMode: 'open' | 'refined';
}

export interface PhotoSearchParams extends SearchParamsBase {
  imageData: string;
}

// Product Table & RFQ Cart types
export interface ProductItem {
  id: string;
  partName: string;
  manufacturer?: string; // Manufacturer/OEM name
  productName?: string; // Product model/name
  partUrl: string;
  contactUrl?: string; // URL to supplier's contact/inquiry page
  supplierType: string;
  supplierFlag: string;
  hasSpecSheet: boolean;
  datasheetUrl?: string; // URL to the datasheet PDF
  isVerified?: boolean; // Verified supplier indicator
  rating?: number; // Supplier rating (1-5)
  extractionError?: string; // Error message if AI extraction failed
  // Dynamic column data - key is column name, value is the cell content
  columnData: Record<string, string>;
}

export interface RFQCartItem extends ProductItem {
  addedAt: string;
}

// Service Search types
export interface ServiceSearchParams {
  query: string;
  supplier_name?: string;
  ai_client_name?: string;
  search_engine_client_name?: string;
  generate_ai_search_prompt?: boolean;
}

export interface ServiceResult {
  title: string;
  url: string;
  score: number | null;
  is_likely_service_page?: boolean;
  extracted_services?: Record<string, any>;
  extraction_error?: string | null;
}

export interface ServiceSearchResponse {
  query: string;
  services: ServiceResult[];
  timing?: TimingData;
}