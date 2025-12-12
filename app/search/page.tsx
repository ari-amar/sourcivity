'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams } from 'next/navigation';
import { Search as SearchIcon, X, Camera, Upload, Image, PanelLeft, Download, Lightbulb, Info } from 'lucide-react';
import { useDebounce } from '../../lib/useDebounce';

import { Input } from '../../components/Input';
import { Button } from '../../components/Button';
import { Switch } from '../../components/Switch';
import { FileDropzone } from '../../components/FileDropzone';
import { SearchResults } from '../../components/SearchResults';
import { SearchHistorySidebar } from '../../components/SearchHistorySidebar';
import { useSearchSuggestions, usePartsSearch, usePhotoAnalysis, useColumnDeterminationAndSearch } from '../../lib/searchApi';
import { useSearchHistory } from '../../lib/searchHistoryContext';
import type { Suggestion } from '../../lib/types';
import { exportSearchResultsToCSV } from '../../lib/csvExport';

const searchFormSchema = z.object({
  query: z.string().optional(),
  usSuppliersOnly: z.boolean(),
  searchMode: z.enum(['datasheets', 'services']),
});

type SearchFormValues = z.infer<typeof searchFormSchema>;

export default function SearchPage() {
  const searchParams = useSearchParams();
  const [isSuggestionsVisible, setSuggestionsVisible] = useState(false);
  const [isPhotoUploadOpen, setPhotoUploadOpen] = useState(false);
  const [uploadedPhoto, setUploadedPhoto] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [isSidebarVisible, setSidebarVisible] = useState(false);
  const { addToHistory } = useSearchHistory();
  const hasAutoSearchedRef = useRef(false);
  
  // Retry state management
  const [retryCount, setRetryCount] = useState(0);
  const [isManualRetrying, setIsManualRetrying] = useState(false);
  const [lastSearchParams, setLastSearchParams] = useState<{
    type: 'text' | 'photo';
    data: any;
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
      searchMode: 'datasheets',
    },
  });

  const query = watch('query');
  const usSuppliersOnly = watch('usSuppliersOnly');
  const searchMode = watch('searchMode');
  const debouncedQuery = useDebounce(query, 300);

  const { data: suggestionsData } = useSearchSuggestions(debouncedQuery, {
    enabled: (debouncedQuery?.length ?? 0) > 2,
  });

  const partsSearch = usePartsSearch();
  const photoAnalysis = usePhotoAnalysis();
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
    if (partsSearch.isPending || photoAnalysis.isPending || columnSearch.isPending) {
      setIsManualRetrying(false);
    }
  }, [partsSearch.isPending, photoAnalysis.isPending, columnSearch.isPending]);
  
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
    } else if (partsSearch.isSuccess || photoAnalysis.isSuccess) {
      setRetryCount(0);
      consecutiveFailuresRef.current = 0;
      setIsManualRetrying(false);
    }
  }, [partsSearch.isSuccess, photoAnalysis.isSuccess, columnSearch.isSuccess, query, usSuppliersOnly, addToHistory, columnSearch.data]);
  
  // Track failures for circuit breaker logic
  useEffect(() => {
    if (partsSearch.isError || photoAnalysis.isError || columnSearch.isError) {
      consecutiveFailuresRef.current++;
    }
  }, [partsSearch.isError, photoAnalysis.isError, columnSearch.isError]);

  const performSearch = useCallback(async (searchParams: { type: 'text' | 'photo', data: any }) => {
    console.log('Performing search:', searchParams);
    
    if (searchParams.type === 'photo') {
      const { imageData, usSuppliersOnly } = searchParams.data;
      return photoAnalysis.mutateAsync({
        imageData,
        usSuppliersOnly,
      });
    } else {
      const { query, searchMode, usSuppliersOnly } = searchParams.data;
      return columnSearch.mutateAsync({
        query,
        searchMode,
        usSuppliersOnly,
      });
    }
  }, [photoAnalysis, columnSearch]);

  const onSubmit = async (data: SearchFormValues) => {
    // Prevent double-submits
    if (isProcessing) return;

    console.log('Submitting search:', data);
    const { query, usSuppliersOnly, searchMode } = data;

    // Validate that we have either a query or a photo
    if (!query && !uploadedPhoto) {
      console.log('No search content provided');
      return;
    }

    // Reset retry state for new search
    setRetryCount(0);
    setIsManualRetrying(false);

    let searchParams: { type: 'text' | 'photo', data: any };

    if (uploadedPhoto) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target?.result as string;
        console.log('Photo search initiated with file:', uploadedPhoto.name);

        searchParams = {
          type: 'photo',
          data: { imageData: base64Data, usSuppliersOnly }
        };
        setLastSearchParams(searchParams);

        try {
          await performSearch(searchParams);
          console.log('Photo analysis complete');
        } catch (error) {
          console.error('Photo analysis failed:', error);
        }
      };
      reader.readAsDataURL(uploadedPhoto);
    } else if (query) {
      searchParams = {
        type: 'text',
        data: { query, searchMode, usSuppliersOnly }
      };
      setLastSearchParams(searchParams);

      try {
        await performSearch(searchParams);
      } catch (error) {
        console.error('Search failed:', error);
      }
    }

    setSuggestionsVisible(false);
    setPhotoUploadOpen(false);
  };

  const handleSuggestionClick = (suggestion: Suggestion) => {
    setValue('query', suggestion.suggestion);
    setSuggestionsVisible(false);
    handleSubmit(onSubmit)();
  };

  const handleHistorySearchSelect = useCallback((searchQuery: string, searchMode: 'open' | 'refined', usOnly: boolean) => {
    // Clear any uploaded photos first
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
      setPhotoPreviewUrl(null);
    }
    setUploadedPhoto(null);

    // Set form values
    setValue('query', searchQuery);
    setValue('usSuppliersOnly', usOnly);

    // Trigger search
    setTimeout(() => {
      handleSubmit(onSubmit)();
    }, 100); // Small delay to ensure form values are updated
  }, [setValue, handleSubmit, onSubmit, photoPreviewUrl]);

  const handleClearSearch = () => {
    reset();
    partsSearch.reset();
    photoAnalysis.reset();
    columnSearch.reset();
    
    // Reset retry state
    setRetryCount(0);
    setIsManualRetrying(false);
    setLastSearchParams(null);
    consecutiveFailuresRef.current = 0;
    
    handleClearPhoto();
  };

  const handleInputFocus = () => {
    if ((query?.length ?? 0) > 0) {
      setSuggestionsVisible(true);
    }
  };

  const handlePhotoUpload = useCallback((files: File[]) => {
    const file = files[0];
    if (file) {
      setUploadedPhoto(file);
      const url = URL.createObjectURL(file);
      setPhotoPreviewUrl(url);
      setPhotoUploadOpen(false);
      
      // Clear text query when photo is uploaded
      setValue('query', '');
      setSuggestionsVisible(false);
    }
  }, [setValue]);

  const handleClearPhoto = useCallback(() => {
    setUploadedPhoto(null);
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
      setPhotoPreviewUrl(null);
    }
  }, [photoPreviewUrl]);
  
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

  // Clean up photo URL on unmount
  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl);
      }
    };
  }, [photoPreviewUrl]);

  useEffect(() => {
    if ((debouncedQuery?.length ?? 0) > 2) {
      setSuggestionsVisible(true);
    } else {
      setSuggestionsVisible(false);
    }
  }, [debouncedQuery]);

  const handleWrapperClick = useCallback((event: any) => {
    const target = event.target as HTMLElement;
    if (!target.closest('.search-wrapper') && !target.closest('.photo-upload-modal')) {
      setSuggestionsVisible(false);
      setPhotoUploadOpen(false);
    }
  }, []);

  useEffect(() => {
    document.addEventListener('mousedown', handleWrapperClick);
    return () => {
      document.removeEventListener('mousedown', handleWrapperClick);
    };
  }, [handleWrapperClick]);

  const hasSearchContent = (query && query.length > 0) || uploadedPhoto;
  
  // Determine the current operation state
  const isPhotoAnalyzing = photoAnalysis.isPending;
  const isProcessing = isPhotoAnalyzing || partsSearch.isPending || columnSearch.isPending;
  
  // Combine errors from all operations
  const currentError = photoAnalysis.error || partsSearch.error || columnSearch.error;
  
  // Get the current search data (prefer column search result, then fallback data)
  const currentSearchData = columnSearch.data || partsSearch.data;
  const currentSearchIsPending = partsSearch.isPending || columnSearch.isPending;
  const currentSearchIsIdle = partsSearch.isIdle && photoAnalysis.isIdle && columnSearch.isIdle;
  
  // Determine if retry is available (not if circuit breaker is open)
  const canRetry = lastSearchParams !== null && 
                  retryCount < maxRetryAttempts && 
                  consecutiveFailuresRef.current < circuitBreakerThreshold;

  return (
    <div className="bg-gray-50">
      {isSidebarVisible && (
        <SearchHistorySidebar
          onClose={() => setSidebarVisible(false)}
          onSearchSelect={handleHistorySearchSelect}
        />
      )}
      <div className="flex-1 w-full px-6 py-8">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="flex items-center gap-4">
            {!isSidebarVisible && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSidebarVisible(true)}
                className="p-2"
                title="Search History"
              >
                <PanelLeft size={16} />
              </Button>
            )}
            <div className="search-wrapper relative flex-1">
              <div className="relative search-bar-glass rounded-full">
                <Controller
                  name="query"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder={uploadedPhoto ? "Photo uploaded - ready to search" : "Search for components, specifications, or upload a photo..."}
                      className={`w-full px-5 py-3 pr-28 text-base bg-transparent rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400/50 border-0 transition-all ${uploadedPhoto ? 'bg-muted' : ''}`}
                      autoComplete="off"
                      onFocus={handleInputFocus}
                      disabled={!!uploadedPhoto}
                    />
                  )}
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setPhotoUploadOpen(!isPhotoUploadOpen)}
                    className="p-2 bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-all"
                    title="Upload photo"
                  >
                    <Camera size={18} className="text-gray-600" />
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={isProcessing}
                    className="p-2 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 disabled:opacity-50 transition-all"
                    title={isPhotoAnalyzing ? 'Analyzing Photo...' : columnSearch.isPending ? 'Searching...' : (uploadedPhoto ? 'Analyze Photo' : 'Search')}
                  >
                    <SearchIcon size={18} className="text-white" />
                  </Button>
                </div>
              </div>

            {/* Photo Preview */}
            {uploadedPhoto && photoPreviewUrl && (
              <div className="mt-4 p-4 bg-surface border border-input rounded-lg">
                <div className="flex items-center gap-4">
                  <img 
                    src={photoPreviewUrl} 
                    alt="Uploaded part" 
                    className="w-16 h-16 object-cover rounded-lg"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-sm text-foreground">
                      <Image size={16} />
                      <span>{uploadedPhoto.name}</span>
                      <span className="text-primary font-medium">AI Analysis Ready</span>
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleClearPhoto}
                    className="p-2"
                  >
                    <X size={16} />
                  </Button>
                </div>
              </div>
            )}

            {/* Photo Upload Modal */}
            {isPhotoUploadOpen && (
              <div className="photo-upload-modal absolute top-full mt-2 w-full bg-popup border border-input rounded-lg shadow-lg p-4 z-overlay">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Upload Component Photo</h3>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setPhotoUploadOpen(false)}
                    className="p-2"
                  >
                    <X size={16} />
                  </Button>
                </div>
                <FileDropzone
                  accept="image/*"
                  maxFiles={1}
                  maxSize={10 * 1024 * 1024} // 10MB
                  onFilesSelected={handlePhotoUpload}
                  icon={<Upload size={32} />}
                  title="Drop your part photo here"
                  subtitle="PNG, JPG up to 10MB - AI will analyze and find matching parts"
                />
              </div>
            )}

            {isSuggestionsVisible &&
              !uploadedPhoto &&
              suggestionsData &&
              suggestionsData.suggestions &&
              suggestionsData.suggestions.length > 0 && (
                <div className="absolute top-full mt-1 w-full bg-popup border border-input rounded-lg shadow-lg z-content-high">
                  <ul className="py-2">
                    {suggestionsData.suggestions.map((s: Suggestion, i: number) => (
                      <li
                        key={i}
                        onClick={() => handleSuggestionClick(s)}
                        onMouseDown={(e) => e.preventDefault()}
                        className="px-4 py-2 hover:bg-muted cursor-pointer flex items-center justify-between"
                      >
                        <span className="text-foreground">{s.suggestion}</span>
                        {s.category && (
                          <span className={`text-sm ${
                            s.category === 'Example'
                              ? 'text-primary font-medium'
                              : 'text-muted-foreground'
                          }`}>
                            {s.category === 'Example' ? '→ Example' : `in ${s.category}`}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Search Mode Toggle */}
          <div className="flex items-center gap-6 px-2">
            <span className="text-sm font-medium text-foreground">Search Type:</span>
            <Controller
              name="searchMode"
              control={control}
              render={({ field }) => (
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="datasheets"
                      checked={field.value === 'datasheets'}
                      onChange={() => field.onChange('datasheets')}
                      className="w-4 h-4 text-primary focus:ring-primary"
                    />
                    <span className={`text-sm ${field.value === 'datasheets' ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                      Product Datasheets
                    </span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="services"
                      checked={field.value === 'services'}
                      onChange={() => field.onChange('services')}
                      className="w-4 h-4 text-primary focus:ring-primary"
                    />
                    <span className={`text-sm ${field.value === 'services' ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                      Supplier Services
                    </span>
                  </label>
                </div>
              )}
            />
          </div>

          {errors.query && (
            <p className="text-destructive text-sm">{errors.query.message}</p>
          )}

          {/* AI Recommendation Section - Only show when query is "precision linear bearing" */}
          {query === 'precision linear bearing' && !uploadedPhoto && (
            <div className="mt-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                    <Lightbulb size={18} className="text-white" />
                  </div>
                </div>
                <div className="flex-1 space-y-2.5">
                  <div className="flex items-start gap-2">
                    <Info size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Key Specs to Consider:</strong> Load capacity, bore diameter, outer diameter, accuracy class (P0-P4), and seal type
                    </p>
                  </div>
                  <div className="flex items-start gap-2">
                    <Info size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Common Applications:</strong> CNC machines, 3D printers, linear motion systems, robotics, and precision automation
                    </p>
                  </div>
                  <div className="flex items-start gap-2">
                    <Info size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-700">
                      <strong className="font-medium text-gray-900">Pro Tip:</strong> Toggle "US Suppliers Only" filter below to narrow results by region, or specify size (e.g., "12mm linear bearing") for faster sourcing
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </form>

        {/* Show photo analysis results */}
        {photoAnalysis.data && (
          <div className="mt-8 p-6 bg-surface border border-input rounded-lg">
            <h3 className="text-xl font-semibold mb-4">AI Photo Analysis</h3>
            <div className="prose max-w-none">
              <p className="text-foreground">{photoAnalysis.data.analysis}</p>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Based on this analysis, you can now search for specific parts or refine your query in the search box above.
            </p>
          </div>
        )}

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