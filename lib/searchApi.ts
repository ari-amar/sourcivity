'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useEffect, useState } from 'react';
import type { 
  SuggestionsResponse, 
  SearchResultsData, 
  PhotoAnalysisResponse,
  TextSearchParams,
  PhotoSearchParams 
} from './types';

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
  const response = await fetch(`/api/search/suggestions?query=${encodeURIComponent(query)}`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error(`Search suggestions failed: ${response.status}`);
  }

  return response.json();
}

async function fetchPartsSearch(params: TextSearchParams & { predeterminedColumns?: string[] }): Promise<SearchResultsData> {
  const response = await fetch('/api/search/parts', {
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
  const response = await fetch('/api/search/photo', {
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
  // Step 1: Determine optimal columns
  const columnsResponse = await fetch('/api/search/columns', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: params.query }),
  });

  if (!columnsResponse.ok) {
    throw new Error(`Column determination failed: ${columnsResponse.status}`);
  }

  const columnsData = await columnsResponse.json();
  const predeterminedColumns = columnsData.columns;

  // Step 2: Search with predetermined columns
  const searchResponse = await fetch('/api/search/parts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...params,
      predeterminedColumns
    }),
  });

  if (!searchResponse.ok) {
    throw new Error(`Parts search failed: ${searchResponse.status}`);
  }

  return searchResponse.json();
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
  const response = await fetch('/api/ai/rfq-conversation', {
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