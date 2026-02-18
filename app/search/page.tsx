'use client'

import React, { useState, useEffect, useCallback, useRef, Suspense } from 'react';
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

// Animated placeholder suggestions - 50 Niche Industrial Components
const PARTS_SUGGESTIONS = [
  'Micro ball bearings',
  'Titanium aerospace fasteners',
  'High-temperature gaskets',
  'Precision robotic gears',
  'Ceramic electrical insulators',
  'Carbon fiber structural brackets',
  'Cryogenic seals',
  'Laser-grade optical lenses',
  'Custom wire harness assemblies',
  'Microfluidic chips',
  'Tungsten carbide cutting inserts',
  'Precision-ground steel shafts',
  'Miniature electric motors',
  'High-voltage capacitors',
  'Chemical-resistant tubing',
  'Low-friction polymer bushings',
  'Aerospace composite panels',
  'Precision spray nozzles',
  'High-pressure industrial valves',
  'Corrosion-resistant pumps',
  'Ultra-thin metal foil',
  'Industrial thermocouples',
  'Heavy-duty industrial bearings',
  'Medical-grade plastic housings',
  'Magnetic sensor cores',
  'Precision cam mechanisms',
  'Aerospace-grade specialty springs',
  'High-vacuum flanges',
  'Custom heat sinks',
  'Miniature linear actuators',
  'Precision metal bellows',
  'EMI shielding components',
  'Sapphire or quartz windows',
  'Specialty O-rings (FKM, FFKM)',
  'Micro screws and fasteners',
  'High-temperature insulation boards',
  'Ceramic bearings',
  'Precision shims and spacers',
  'Industrial glass tubing',
  'Battery current collectors',
  'High-frequency RF connectors',
  'Precision rollers',
  'Custom impellers',
  'Vacuum-compatible lubricants',
  'Abrasion-resistant liners',
  'Precision lead screws',
  'High-strength chain links',
  'Optical filters',
  'Micro valves',
  'Encapsulated electronic modules',
];

// 50 Niche Industrial Manufacturing Services
const SERVICES_SUGGESTIONS = [
  'Micro-machining (sub-millimeter tolerances)',
  'CNC machining for exotic alloys',
  'Precision injection molding (medical/aerospace)',
  'Metal additive manufacturing (industrial 3D printing)',
  'Vacuum or plasma coating services',
  'Ceramic component manufacturing',
  'Cleanroom manufacturing services',
  'Tool & die fabrication for legacy equipment',
  'Composite layup and curing services',
  'Custom gasket and sealing fabrication',
  'Powder metallurgy services',
  'Ultra-precision grinding and polishing',
  'Electron beam or laser welding',
  'High-vacuum component fabrication',
  'Cryogenic-rated component manufacturing',
  'Precision sheet metal fabrication',
  'Surface hardening and wear-resistant coatings',
  'Custom heat treatment services',
  'Industrial glass forming and machining',
  'Specialty polymer extrusion',
  'Low-volume, high-mix production runs',
  'Optical component fabrication',
  'Electromagnetic component manufacturing',
  'Chemical-resistant lining and coating',
  'Aerospace-qualified manufacturing (AS9100)',
  'Medical device manufacturing (ISO 13485)',
  'Rapid functional prototyping',
  'Precision assembly of micro components',
  'Specialty fastening system manufacturing',
  'High-temperature furnace processing',
  'Custom bearing manufacturing',
  'Precision stamping and fine blanking',
  'Cleanroom injection molding',
  'Additive manufacturing with titanium',
  'Plasma nitriding and carburizing',
  'Industrial anodizing (hard coat)',
  'High-speed balancing services',
  'Precision metrology and inspection',
  'Custom fixture and jig fabrication',
  'Specialty spring manufacturing',
  'Advanced composite machining',
  'High-pressure testing services',
  'Hermetic sealing services',
  'Industrial encapsulation and potting',
  'Failure analysis and materials testing',
  'Prototype-to-production scaling',
  'Vacuum brazing services',
  'Specialty surface texturing',
  'EMI/RFI shielding application',
  'Industrial component refurbishment',
];

function SearchPageContent() {
  const searchParams = useSearchParams();
  const [searchMode, setSearchMode] = useState<SearchMode>('parts');
  const { addToHistory } = useSearchHistory();
  const hasAutoSearchedRef = useRef(false);

  // Animated suggestions state
  const [visibleSuggestions, setVisibleSuggestions] = useState<string[]>([]);
  const [suggestionStartIndex, setSuggestionStartIndex] = useState(0);
  const [animationKey, setAnimationKey] = useState(0);

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

  // Rotate through all suggestions every 5 seconds - show 4 unique items
  useEffect(() => {
    const suggestions = searchMode === 'parts' ? PARTS_SUGGESTIONS : SERVICES_SUGGESTIONS;
    const numToShow = 4; // Show 4 suggestions at a time

    // Initialize with first 4 suggestions
    setVisibleSuggestions(suggestions.slice(0, numToShow));
    setAnimationKey(prev => prev + 1); // Trigger animation

    const rotateInterval = setInterval(() => {
      setSuggestionStartIndex((prev) => {
        // Jump by 4 to show completely new suggestions each time
        const newIndex = (prev + numToShow) % suggestions.length;
        const endIndex = newIndex + numToShow;

        // Handle wrapping around
        if (endIndex > suggestions.length) {
          const firstPart = suggestions.slice(newIndex);
          const secondPart = suggestions.slice(0, endIndex - suggestions.length);
          setVisibleSuggestions([...firstPart, ...secondPart]);
        } else {
          setVisibleSuggestions(suggestions.slice(newIndex, endIndex));
        }

        // Trigger re-animation
        setAnimationKey(prev => prev + 1);
        return newIndex;
      });
    }, 3000); // Rotate every 3 seconds

    return () => clearInterval(rotateInterval);
  }, [searchMode]);

  // Reset suggestions when search mode changes
  useEffect(() => {
    const suggestions = searchMode === 'parts' ? PARTS_SUGGESTIONS : SERVICES_SUGGESTIONS;
    setSuggestionStartIndex(0);
    setVisibleSuggestions(suggestions.slice(0, 4));
    setAnimationKey(prev => prev + 1); // Re-trigger animations on mode change
  }, [searchMode]);

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

  // Handle suggestion click
  const handleSuggestionClick = useCallback(async (suggestion: string) => {
    setValue('query', suggestion);

    const searchData = {
      query: suggestion,
      supplierName: undefined,
      searchMode: 'open' as const,
      usSuppliersOnly
    };
    setLastSearchParams(searchData);

    try {
      await performSearch(searchData);
    } catch (error) {
      console.error('Suggestion search failed:', error);
    }
  }, [setValue, usSuppliersOnly, performSearch]);

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
                      placeholder={searchMode === 'parts' ? 'Search for components...' : 'Search for services...'}
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

        {/* Animated Suggestion Buttons */}
        {!query && visibleSuggestions.length > 0 && (
          <div className="mt-4 md:mt-6">
            <p className="text-xs md:text-sm text-muted-foreground mb-3 text-center animate-pulse-subtle">
              <span className="inline-block">✨</span> Try searching for{' '}
              <span className="text-primary font-medium">these popular items</span>{' '}
              <span className="inline-block">👇</span>
            </p>
            <div className="flex flex-wrap justify-center items-center gap-2 md:gap-3 max-w-4xl mx-auto min-h-[120px]">
              {visibleSuggestions.map((suggestion, index) => (
                <button
                  key={`${suggestion}-${animationKey}-${index}`}
                  type="button"
                  onClick={() => handleSuggestionClick(suggestion)}
                  disabled={isProcessing}
                  className="suggestion-button group relative px-3 md:px-4 py-2 md:py-2.5 text-xs md:text-sm font-medium text-foreground bg-white border border-gray-200 rounded-full hover:border-primary hover:text-primary hover:shadow-md transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed animate-fade-in-up"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <span className="relative z-10">{suggestion}</span>
                  <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-primary/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                </button>
              ))}
            </div>
          </div>
        )}

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
                const contactUrl = extracted.contact_url || service.url; // Use extracted contact URL or fallback to service page

                // Format company name with link to contact page
                const companyLink = `[${companyName}](${contactUrl})`;

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

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="bg-gray-50 min-h-screen flex items-center justify-center"><p className="text-gray-500">Loading...</p></div>}>
      <SearchPageContent />
    </Suspense>
  );
}
