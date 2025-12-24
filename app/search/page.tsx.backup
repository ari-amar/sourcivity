'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams } from 'next/navigation';
import { Search as SearchIcon, X, PanelLeft, Lightbulb, Info } from 'lucide-react';

import { Input } from '../../components/Input';
import { Button } from '../../components/Button';
import { Switch } from '../../components/Switch';
import { SearchResults } from '../../components/SearchResults';
import { SearchHistorySidebar } from '../../components/SearchHistorySidebar';
import { usePartsSearch, useColumnDeterminationAndSearch } from '../../lib/searchApi';
import { useSearchHistory } from '../../lib/searchHistoryContext';
import { exportSearchResultsToCSV } from '../../lib/csvExport';

const searchFormSchema = z.object({
  query: z.string().optional(),
  usSuppliersOnly: z.boolean(),
});

type SearchFormValues = z.infer<typeof searchFormSchema>;

export default function SearchPage() {
  const searchParams = useSearchParams();
  const [isSidebarVisible, setSidebarVisible] = useState(false);
  const { addToHistory } = useSearchHistory();
  const hasAutoSearchedRef = useRef(false);

  // Retry state management
  const [retryCount, setRetryCount] = useState(0);
  const [isManualRetrying, setIsManualRetrying] = useState(false);
  const [lastSearchParams, setLastSearchParams] = useState<{
    query: string;
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
      query: 'precision linear bearing',
      usSuppliersOnly: false,
    },
  });

  const query = watch('query');
  const usSuppliersOnly = watch('usSuppliersOnly');

  const partsSearch = usePartsSearch();
  const columnSearch = useColumnDeterminationAndSearch();

  // Auto-search if query param is present
  useEffect(() => {
    const urlQuery = searchParams.get('q');
    if (urlQuery && !hasAutoSearchedRef.current) {
      hasAutoSearchedRef.current = true;
      setValue('query', urlQuery);
      // Trigger search with a small delay to ensure form is ready
      setTimeout(() => {
        columnSearch.mutate({
          query: urlQuery,
          searchMode: 'open',
          usSuppliersOnly: false,
        });
      }, 100);
    }
  }, [searchParams, setValue, columnSearch]);

  // Reset retry state when operations start
  useEffect(() => {
    if (partsSearch.isPending || columnSearch.isPending) {
      setIsManualRetrying(false);
    }
  }, [partsSearch.isPending, columnSearch.isPending]);

  // Reset retry count on successful operations and add to history
  useEffect(() => {
    if (columnSearch.isSuccess && query) {
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
    }
  }, [partsSearch.isSuccess, columnSearch.isSuccess, query, usSuppliersOnly, addToHistory, columnSearch.data]);

  // Track failures for circuit breaker logic
  useEffect(() => {
    if (partsSearch.isError || columnSearch.isError) {
      consecutiveFailuresRef.current++;
    }
  }, [partsSearch.isError, columnSearch.isError]);

  const performSearch = useCallback(async (searchData: { query: string; searchMode: 'open' | 'refined'; usSuppliersOnly: boolean }) => {
    console.log('Performing search:', searchData);
    return columnSearch.mutateAsync(searchData);
  }, [columnSearch]);

  const onSubmit = async (data: SearchFormValues) => {
    // Prevent double-submits
    if (isProcessing) return;

    console.log('Submitting search:', data);
    const { query, usSuppliersOnly } = data;

    // Reset retry state for new search
    setRetryCount(0);
    setIsManualRetrying(false);

    if (query) {
      const searchData = { query, searchMode: 'open' as const, usSuppliersOnly };
      setLastSearchParams(searchData);

      try {
        await performSearch(searchData);
      } catch (error) {
        console.error('Search failed:', error);
      }
    }
  };

  const handleHistorySearchSelect = useCallback((searchQuery: string, searchMode: 'open' | 'refined', usOnly: boolean) => {
    // Set form values
    setValue('query', searchQuery);
    setValue('usSuppliersOnly', usOnly);

    // Trigger search
    setTimeout(() => {
      handleSubmit(onSubmit)();
    }, 100); // Small delay to ensure form values are updated
  }, [setValue, handleSubmit, onSubmit]);

  const handleClearSearch = () => {
    reset();
    partsSearch.reset();
    columnSearch.reset();

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

  // Determine the current operation state
  const isProcessing = partsSearch.isPending || columnSearch.isPending;

  // Combine errors from all operations
  const currentError = partsSearch.error || columnSearch.error;

  // Get the current search data (prefer column search result, then fallback data)
  const currentSearchData = columnSearch.data || partsSearch.data;
  const currentSearchIsPending = partsSearch.isPending || columnSearch.isPending;
  const currentSearchIsIdle = partsSearch.isIdle && columnSearch.isIdle;
  
  // Determine if retry is available (not if circuit breaker is open)
  const canRetry = lastSearchParams !== null && 
                  retryCount < maxRetryAttempts && 
                  consecutiveFailuresRef.current < circuitBreakerThreshold;

  return (
    <div className="bg-gray-50 min-h-screen">
      {isSidebarVisible && (
        <SearchHistorySidebar
          onClose={() => setSidebarVisible(false)}
          onSearchSelect={handleHistorySearchSelect}
        />
      )}
      <div className="flex-1 w-full px-3 md:px-6 py-3 md:py-8 max-w-7xl mx-auto">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 md:space-y-6">
          <div className="flex items-center gap-2 md:gap-4">
            {!isSidebarVisible && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSidebarVisible(true)}
                className="p-2 flex-shrink-0"
                title="Search History"
              >
                <PanelLeft size={16} />
              </Button>
            )}
            <div className="search-wrapper relative flex-1 min-w-0">
              <div className="relative search-bar-glass rounded-full">
                <Controller
                  name="query"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="Search components..."
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
                    title={columnSearch.isPending ? 'Searching...' : 'Search'}
                  >
                    <SearchIcon size={14} className="md:w-[18px] md:h-[18px] text-white" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {errors.query && (
            <p className="text-destructive text-sm">{errors.query.message}</p>
          )}

          {/* AI Recommendation Section - Only show when query is "precision linear bearing" */}
          {query === 'precision linear bearing' && (
            <div className="mt-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 md:p-5 shadow-sm">
              <div className="flex items-start gap-2 md:gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <div className="w-7 h-7 md:w-8 md:h-8 bg-blue-500 rounded-full flex items-center justify-center">
                    <Lightbulb size={16} className="md:w-[18px] md:h-[18px] text-white" />
                  </div>
                </div>
                <div className="flex-1 space-y-2 md:space-y-2.5">
                  <div className="flex items-start gap-1.5 md:gap-2">
                    <Info size={14} className="md:w-4 md:h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-xs md:text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Key Specs to Consider:</strong> Load capacity, bore diameter, outer diameter, accuracy class (P0-P4), and seal type
                    </p>
                  </div>
                  <div className="flex items-start gap-1.5 md:gap-2">
                    <Info size={14} className="md:w-4 md:h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-xs md:text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Common Applications:</strong> CNC machines, 3D printers, linear motion systems, robotics, and precision automation
                    </p>
                  </div>
                  <div className="flex items-start gap-1.5 md:gap-2">
                    <Info size={14} className="md:w-4 md:h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-xs md:text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Pro Tip:</strong> Toggle "US Suppliers Only" filter below to narrow results by region, or specify size (e.g., "12mm linear bearing") for faster sourcing
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </form>

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
        />
      </div>
    </div>
  );
}