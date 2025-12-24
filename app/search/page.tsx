'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams } from 'next/navigation';
import { Search } from 'lucide-react';

import { Input } from '../../components/Input';
import { Button } from '../../components/Button';
import { Switch } from '../../components/Switch';
import { SearchResults } from '../../components/SearchResults';
import { usePartsSearch, useColumnDeterminationAndSearch, useServicesSearch } from '../../lib/searchApi';
import { useSearchHistory } from '../../lib/searchHistoryContext';
import { exportSearchResultsToCSV } from '../../lib/csvExport';
import type { ServiceResult } from '../../lib/types';

const searchFormSchema = z.object({
  query: z.string().optional(),
  supplierName: z.string().optional(),
  usSuppliersOnly: z.boolean(),
});

type SearchFormValues = z.infer<typeof searchFormSchema>;
type SearchMode = 'parts' | 'services';

export default function SearchPage() {
  const searchParams = useSearchParams();
  const [searchMode, setSearchMode] = useState<SearchMode>('parts');
  const { addToHistory } = useSearchHistory();
  const hasAutoSearchedRef = useRef(false);

  // Retry state management
  const [retryCount, setRetryCount] = useState(0);
  const [isManualRetrying, setIsManualRetrying] = useState(false);
  const [lastSearchParams, setLastSearchParams] = useState<{
    query: string;
    supplierName?: string;
    searchMode: 'open' | 'refined';
    usSuppliersOnly: boolean;
  } | null>(null);

  // Circuit breaker respect - track consecutive failures
  const consecutiveFailuresRef = useRef(0);
  const maxRetryAttempts = 3;
  const circuitBreakerThreshold = 3;

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<SearchFormValues>({
    resolver: zodResolver(searchFormSchema),
    defaultValues: {
      query: '',
      supplierName: '',
      usSuppliersOnly: false,
    },
  });

  const query = watch('query');
  const supplierName = watch('supplierName');
  const usSuppliersOnly = watch('usSuppliersOnly');

  const partsSearch = usePartsSearch();
  const columnSearch = useColumnDeterminationAndSearch();
  const servicesSearch = useServicesSearch();

  // Auto-search if query param is present
  useEffect(() => {
    const urlQuery = searchParams.get('q');
    if (urlQuery && !hasAutoSearchedRef.current) {
      hasAutoSearchedRef.current = true;
      setValue('query', urlQuery);
      // Trigger search with a small delay to ensure form is ready
      setTimeout(() => {
        if (searchMode === 'parts') {
          columnSearch.mutate({
            query: urlQuery,
            searchMode: 'open',
            usSuppliersOnly: false,
          });
        }
      }, 100);
    }
  }, [searchParams, setValue, columnSearch, searchMode]);

  // Reset retry state when operations start
  useEffect(() => {
    if (partsSearch.isPending || columnSearch.isPending || servicesSearch.isPending) {
      setIsManualRetrying(false);
    }
  }, [partsSearch.isPending, columnSearch.isPending, servicesSearch.isPending]);

  // Reset retry count on successful operations and add to history
  useEffect(() => {
    if (columnSearch.isSuccess && query && searchMode === 'parts') {
      setRetryCount(0);
      consecutiveFailuresRef.current = 0;
      setIsManualRetrying(false);

      // Add successful search to history
      addToHistory({
        query,
        searchMode: 'open',
        usSuppliersOnly: usSuppliersOnly || false,
        resultCount: columnSearch.data?.response ? 1 : 0
      });
    } else if (partsSearch.isSuccess) {
      setRetryCount(0);
      consecutiveFailuresRef.current = 0;
      setIsManualRetrying(false);
    } else if (servicesSearch.isSuccess && searchMode === 'services') {
      setRetryCount(0);
      consecutiveFailuresRef.current = 0;
      setIsManualRetrying(false);
    }
  }, [partsSearch.isSuccess, columnSearch.isSuccess, servicesSearch.isSuccess, query, usSuppliersOnly, addToHistory, columnSearch.data, searchMode]);

  // Track failures for circuit breaker logic
  useEffect(() => {
    if (partsSearch.isError || columnSearch.isError || servicesSearch.isError) {
      consecutiveFailuresRef.current++;
    }
  }, [partsSearch.isError, columnSearch.isError, servicesSearch.isError]);

  const performSearch = useCallback(async (searchData: { query: string; supplierName?: string; searchMode: 'open' | 'refined'; usSuppliersOnly: boolean }) => {
    console.log('Performing search:', searchData, 'mode:', searchMode);
    if (searchMode === 'parts') {
      return columnSearch.mutateAsync(searchData);
    } else {
      return servicesSearch.mutateAsync({
        query: searchData.query,
        supplier_name: searchData.supplierName,
        ai_client_name: 'anthropic',
        search_engine_client_name: 'exa',
      });
    }
  }, [columnSearch, servicesSearch, searchMode]);

  const onSubmit = async (data: SearchFormValues) => {
    // Prevent double-submits
    if (isProcessing) return;

    console.log('Submitting search:', data, 'mode:', searchMode);
    const { query, supplierName, usSuppliersOnly } = data;

    // Reset retry state for new search
    setRetryCount(0);
    setIsManualRetrying(false);

    if (query) {
      const searchData = { query, supplierName, searchMode: 'open' as const, usSuppliersOnly };
      setLastSearchParams(searchData);

      try {
        await performSearch(searchData);
      } catch (error) {
        console.error('Search failed:', error);
      }
    }
  };

  const handleClearSearch = () => {
    reset();
    partsSearch.reset();
    columnSearch.reset();
    servicesSearch.reset();

    // Reset retry state
    setRetryCount(0);
    setIsManualRetrying(false);
    setLastSearchParams(null);
    consecutiveFailuresRef.current = 0;
  };

  // Retry handler that respects circuit breaker
  const handleRetry = useCallback(async () => {
    if (!lastSearchParams) {
      console.error('No previous search params to retry');
      return;
    }

    // Check if we should respect circuit breaker
    if (consecutiveFailuresRef.current >= circuitBreakerThreshold) {
      console.log('Circuit breaker threshold reached, not retrying');
      return;
    }

    // Check max retry attempts
    if (retryCount >= maxRetryAttempts) {
      console.log('Max retry attempts reached');
      return;
    }

    console.log(`Retrying search (attempt ${retryCount + 1}/${maxRetryAttempts})`);
    setRetryCount(prev => prev + 1);
    setIsManualRetrying(true);

    try {
      await performSearch(lastSearchParams);
      console.log('Retry successful');
    } catch (error) {
      console.error('Retry failed:', error);
    }
  }, [lastSearchParams, retryCount, maxRetryAttempts, performSearch]);

  const hasSearchContent = query && query.length > 0;

  // Determine the current operation state based on search mode
  const isProcessing = searchMode === 'parts'
    ? (partsSearch.isPending || columnSearch.isPending)
    : servicesSearch.isPending;

  // Combine errors from all operations
  const currentError = searchMode === 'parts'
    ? (partsSearch.error || columnSearch.error)
    : servicesSearch.error;

  // Get the current search data based on mode
  const currentSearchData = searchMode === 'parts'
    ? (columnSearch.data || partsSearch.data)
    : undefined; // Services use custom display

  const currentSearchIsPending = searchMode === 'parts'
    ? (partsSearch.isPending || columnSearch.isPending)
    : servicesSearch.isPending;

  const currentSearchIsIdle = searchMode === 'parts'
    ? (partsSearch.isIdle && columnSearch.isIdle)
    : servicesSearch.isIdle;

  // Determine if retry is available (not if circuit breaker is open)
  const canRetry = lastSearchParams !== null &&
                  retryCount < maxRetryAttempts &&
                  consecutiveFailuresRef.current < circuitBreakerThreshold;

  return (
    <div className="bg-gray-50 min-h-screen">
      <div className="flex-1 w-full px-3 md:px-6 py-3 md:py-8 max-w-7xl mx-auto">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 md:space-y-6">
          {/* Search Mode Toggle */}
          <div className="flex items-center justify-center gap-2 mb-4">
            <button
              type="button"
              onClick={() => {
                setSearchMode('parts');
                handleClearSearch();
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                searchMode === 'parts'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Parts Search
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchMode('services');
                handleClearSearch();
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                searchMode === 'services'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Services Search
            </button>
          </div>

          <div className="flex items-center gap-2 md:gap-4">
            <div className="search-wrapper relative flex-1 min-w-0">
              <div className="relative search-bar-glass rounded-full">
                <Controller
                  name="query"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder={searchMode === 'parts' ? 'Search components (e.g., precision linear bearing)...' : 'Search for services (e.g., CNC machining)...'}
                      className="w-full px-3 md:px-5 py-2 md:py-3 pr-16 md:pr-28 text-xs md:text-base bg-transparent rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400/50 border-0 transition-all placeholder:text-xs md:placeholder:text-base"
                      autoComplete="off"
                    />
                  )}
                />
                <div className="absolute right-1 md:right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5 md:gap-2">
                  <Button
                    type="submit"
                    size="sm"
                    disabled={isProcessing || !hasSearchContent}
                    className="p-1 md:p-2 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 disabled:opacity-50 transition-all min-w-0 h-auto"
                    title={isProcessing ? 'Searching...' : 'Search'}
                  >
                    <Search size={14} className="md:w-[18px] md:h-[18px] text-white" />
                  </Button>
                </div>
              </div>
            </div>
          </div>


          {errors.query && (
            <p className="text-destructive text-sm">{errors.query.message}</p>
          )}

          
        </form>

        {/* Results Display - Same location for both modes */}
        {searchMode === 'parts' ? (
          <SearchResults
            isPending={currentSearchIsPending}
            isIdle={currentSearchIsIdle}
            error={currentError}
            data={currentSearchData}
            query={query}
            usSuppliersOnly={usSuppliersOnly}
            onUsSuppliersOnlyChange={(value) => setValue('usSuppliersOnly', value)}
            onRetry={canRetry ? handleRetry : undefined}
            retryCount={retryCount}
            isRetrying={isManualRetrying}
            searchMode="parts"
          />
        ) : (
          <SearchResults
            isPending={servicesSearch.isPending}
            isIdle={servicesSearch.isIdle}
            error={servicesSearch.error}
            data={(() => {
              // Convert service results to markdown table format
              if (!servicesSearch.data) return undefined;

              const services = servicesSearch.data.services;
              if (services.length === 0) {
                return { response: 'No services found.', query: servicesSearch.data.query };
              }

              // Build markdown table
              const header = '| Supplier | Services Offered | Capabilities | Certifications | Equipment |';
              const separator = '|----------|------------------|--------------|----------------|-----------|';

              const rows = services.map((service: ServiceResult) => {
                const extracted = service.extracted_services || {};
                const companyName = extracted.company_name || service.title || 'Unknown';
                const servicesOffered = extracted.services_offered || '';
                const capabilities = extracted.capabilities || '';
                const certifications = extracted.certifications || '';
                const equipment = extracted.equipment || '';

                // Format company name with link
                const companyLink = `[${companyName}](${service.url})`;

                return `| ${companyLink} | ${servicesOffered} | ${capabilities} | ${certifications} | ${equipment} |`;
              });

              const tableMarkdown = [header, separator, ...rows].join('\n');

              return {
                response: `Found ${services.length} suppliers for "${servicesSearch.data.query}":\n\n${tableMarkdown}`,
                query: servicesSearch.data.query
              };
            })()}
            query={query}
            onRetry={canRetry ? handleRetry : undefined}
            retryCount={retryCount}
            isRetrying={isManualRetrying}
            searchMode="services"
          />
        )}
      </div>
    </div>
  );
}
