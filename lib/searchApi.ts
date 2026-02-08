'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useEffect, useState } from 'react';
import type {
  SuggestionsResponse,
  SearchResultsData,
  PhotoAnalysisResponse,
  TextSearchParams,
  PhotoSearchParams,
  ServiceSearchParams,
  ServiceSearchResponse
} from './types';
import { DUMMY_SEARCH_DATA } from './dummyData';

import { getBackendUrl } from './utils';

// Backend URL - automatically handles Vercel deployment and local development
const BACKEND_URL = getBackendUrl();

// React Query configuration constants
const REACT_QUERY_CONFIG = {
  timeout: 45000,
  retryAttempts: 3,
  retryDelayMultiplier: 1000,
  staleTime: {
    suggestions: 2 * 60 * 1000,
    searchResults: 5 * 60 * 1000,
    columns: 10 * 60 * 1000,
    photo: 30 * 60 * 1000,
  },
  cacheTime: 10 * 60 * 1000,
};

// API functions
async function fetchSearchSuggestions(query: string): Promise<SuggestionsResponse> {
  // Disable suggestions in demo mode - only "precision linear bearing" is available
  await new Promise(resolve => setTimeout(resolve, 100));

  return {
    suggestions: [],
    isVague: false,
    vaguenessLevel: undefined,
    helpText: undefined
  };
}

async function fetchPartsSearch(params: TextSearchParams & { predeterminedColumns?: string[] }): Promise<SearchResultsData> {
  const response = await fetch(`${BACKEND_URL}/api/search/parts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Parts search failed: ${response.status}`);
  }

  return response.json();
}

async function fetchPhotoAnalysis(params: PhotoSearchParams): Promise<PhotoAnalysisResponse> {
  const response = await fetch(`${BACKEND_URL}/api/search/photo`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`Photo analysis failed: ${response.status}`);
  }

  return response.json();
}

async function fetchColumnDeterminationAndSearch(params: TextSearchParams): Promise<SearchResultsData> {
  const startTime = performance.now();

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🔍 PARTS SEARCH REQUEST');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`   Query: "${params.query}"`);
  console.log(`   Backend URL: ${BACKEND_URL}/api/search/parts`);

  // Call the backend API for search with AI-generated columns
  const fetchStartTime = performance.now();
  const response = await fetch(`${BACKEND_URL}/api/search/parts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: params.query,
      search_engine_client_name: 'exa',
      ai_client_name: 'anthropic',
    }),
  });
  const fetchEndTime = performance.now();
  const networkTime = fetchEndTime - fetchStartTime;

  console.log(`   Response Status: ${response.status} ${response.statusText}`);

  if (!response.ok) {
    console.error(`   ❌ Search failed: ${response.status}`);
    throw new Error(`Search failed: ${response.status}`);
  }

  const parseStartTime = performance.now();
  const data = await response.json();
  const parseEndTime = performance.now();
  const parseTime = parseEndTime - parseStartTime;

  // Transform backend response into markdown table format
  const transformStartTime = performance.now();
  const markdownTable = convertBackendResponseToMarkdown(data);
  const transformEndTime = performance.now();
  const transformTime = transformEndTime - transformStartTime;

  const totalTime = performance.now() - startTime;

  // Log detailed response data
  console.log('');
  console.log('📦 BACKEND RESPONSE:');
  console.log(`   Parts Count: ${data.parts?.length || 0}`);
  console.log(`   Spec Columns: ${data.spec_column_names?.length || 0}`);
  if (data.spec_column_names?.length > 0) {
    console.log(`   Columns: [${data.spec_column_names.slice(0, 5).join(', ')}${data.spec_column_names.length > 5 ? '...' : ''}]`);
  }

  // Log each part with specs
  console.log('');
  console.log('📋 PRODUCTS WITH SPECS:');
  data.parts?.forEach((part: any, i: number) => {
    const specsCount = Object.keys(part.specs || {}).length;
    const filledSpecs = Object.values(part.specs || {}).filter((v: any) => v && v !== 'N/A').length;
    console.log(`   ${i + 1}. ${part.manufacturer || 'Unknown'} - ${part.product_name || 'Unknown'}`);
    console.log(`      URL: ${part.url?.substring(0, 60)}...`);
    console.log(`      Specs: ${filledSpecs}/${specsCount} filled`);
    if (part.error) {
      console.log(`      ⚠️ Error: ${part.error}`);
    }
  });

  // Log performance metrics
  console.log('');
  console.log('⏱️ PERFORMANCE:');
  console.log(`   Total: ${totalTime.toFixed(0)}ms`);
  console.log(`   Network: ${networkTime.toFixed(0)}ms`);
  console.log(`   Parse: ${parseTime.toFixed(0)}ms`);
  console.log(`   Transform: ${transformTime.toFixed(0)}ms`);
  if (data.timing) {
    console.log(`   Backend Total: ${(data.timing.total * 1000).toFixed(0)}ms`);
    console.log(`   Backend Search: ${(data.timing.search_engine * 1000).toFixed(0)}ms`);
    console.log(`   Backend PDF: ${(data.timing.pdf_processing * 1000).toFixed(0)}ms`);
  }
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('');

  return {
    response: markdownTable,
    query: params.query,
    searchMode: params.searchMode || 'open',
    usSuppliersOnly: params.usSuppliersOnly || false,
    columns: data.spec_column_names || [],
    timing: {
      total: totalTime,
      network: networkTime,
      parse: parseTime,
      transform: transformTime,
      backend: data.timing
    }
  };
}

// Helper function to extract clean product name from URL
function extractProductName(url: string): string {
  try {
    // Remove query parameters
    const urlWithoutQuery = url.split('?')[0];

    // Get the filename
    let filename = urlWithoutQuery.split('/').pop() || url;

    // Remove .pdf extension
    filename = filename.replace(/\.pdf$/i, '');

    // Clean up common URL encoded characters and make readable
    filename = decodeURIComponent(filename);

    // Replace hyphens and underscores with spaces, capitalize words
    filename = filename
      .replace(/[-_]/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');

    return filename || 'Product Datasheet';
  } catch (error) {
    return 'Product Datasheet';
  }
}

// Helper function to convert backend response to markdown table format expected by ProductTable
function convertBackendResponseToMarkdown(data: any): string {
  if (!data.parts || data.parts.length === 0) {
    return 'No results found.';
  }

  const specColumns = data.spec_column_names || [];

  // Create header: "Part Name & Supplier Type" + spec columns
  const headers = ['Part Name & Supplier Type', ...specColumns];
  let markdown = '| ' + headers.join(' | ') + ' |\n';
  markdown += '| ' + headers.map(() => '---').join(' | ') + ' |\n';

  // Create table rows in ProductTable format
  for (const part of data.parts) {
    const row: string[] = [];

    // Use manufacturer and product_name from AI extraction (or fallback to URL extraction)
    const manufacturer = part.manufacturer || 'Unknown';
    const productName = part.product_name || extractProductName(part.url);
    const fullName = `${manufacturer} ${productName}`;

    // Format: [Manufacturer ProductName](url)<!--contact:contactUrl--><!--error:extractionError--><br/>🇺🇸 OEM
    // Embed contact URL and extraction error as HTML comments so they can be parsed out later
    // Using US flag and OEM as defaults for PDF datasheets
    const contactUrl = part.contact_url || part.url;
    const extractionError = part.extraction_error || '';
    const partCell = `[${fullName}](${part.url})<!--contact:${contactUrl}--><!--error:${extractionError}--><br/>🇺🇸 OEM`;
    row.push(partCell);

    // Add spec values
    for (const specColumn of specColumns) {
      const value = part.specs?.[specColumn] || 'N/A';
      row.push(String(value));
    }

    markdown += '| ' + row.join(' | ') + ' |\n';
  }

  return markdown;
}

async function fetchRfqConversation(params: {
  query: string;
  partDetails?: string;
  supplierEmails?: string[];
  usSuppliersOnly: boolean;
  rfqDetails?: {
    quantity: string;
    timeline: string;
    additionalRequirements: string;
  };
  selectedSuppliers?: string[];
}): Promise<{ rfqContent: string; suppliers: string[]; query: string; createdAt: string }> {
  const response = await fetch(`${BACKEND_URL}/api/ai/rfq-conversation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    throw new Error(`RFQ generation failed: ${response.status}`);
  }

  return response.json();
}

// Custom hooks
export function useSearchSuggestions(query: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['searchSuggestions', query],
    queryFn: () => fetchSearchSuggestions(query!),
    enabled: options?.enabled && !!query && query.length > 2,
    staleTime: REACT_QUERY_CONFIG.staleTime.suggestions,
    gcTime: REACT_QUERY_CONFIG.cacheTime,
  });
}

export function usePartsSearch() {
  return useMutation({
    mutationFn: fetchPartsSearch,
    retry: REACT_QUERY_CONFIG.retryAttempts,
  });
}

export function usePhotoAnalysis() {
  return useMutation({
    mutationFn: fetchPhotoAnalysis,
    retry: REACT_QUERY_CONFIG.retryAttempts,
  });
}

export function useColumnDeterminationAndSearch() {
  return useMutation({
    mutationFn: fetchColumnDeterminationAndSearch,
    retry: REACT_QUERY_CONFIG.retryAttempts,
  });
}

export function useRfqConversation() {
  return useMutation({
    mutationFn: fetchRfqConversation,
    retry: REACT_QUERY_CONFIG.retryAttempts,
  });
}

async function fetchServicesSearch(params: ServiceSearchParams): Promise<ServiceSearchResponse> {
  const startTime = performance.now();

  const fetchStartTime = performance.now();
  const response = await fetch(`${BACKEND_URL}/api/search/services`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: params.query,
      supplier_name: params.supplier_name,
      ai_client_name: params.ai_client_name || 'anthropic',
      search_engine_client_name: params.search_engine_client_name || 'exa',
      generate_ai_search_prompt: params.generate_ai_search_prompt || false,
    }),
  });
  const fetchEndTime = performance.now();
  const networkTime = fetchEndTime - fetchStartTime;

  if (!response.ok) {
    throw new Error(`Service search failed: ${response.status}`);
  }

  const parseStartTime = performance.now();
  const data = await response.json();
  const parseEndTime = performance.now();
  const parseTime = parseEndTime - parseStartTime;

  const totalTime = performance.now() - startTime;

  // Log performance metrics
  console.log('🏭 Services Search Performance:', {
    total: `${totalTime.toFixed(2)}ms`,
    network: `${networkTime.toFixed(2)}ms`,
    parse: `${parseTime.toFixed(2)}ms`,
    backend: data.timing || 'N/A'
  });

  return {
    ...data,
    timing: {
      total: totalTime,
      network: networkTime,
      parse: parseTime,
      backend: data.timing
    }
  };
}

export function useServicesSearch() {
  return useMutation({
    mutationFn: fetchServicesSearch,
    retry: REACT_QUERY_CONFIG.retryAttempts,
  });
}