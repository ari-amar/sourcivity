import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AlertCircle, Inbox, Search, Loader2, RefreshCw, Clock, AlertTriangle, Download, Settings, Factory } from 'lucide-react';
import type { SearchResultsData } from '../lib/types';
import { SearchResultsContent } from './SearchResultsContent';
import { Button } from './Button';
import { Badge } from './Badge';
import { cn } from '../lib/utils';
import { exportSearchResultsToCSV, generateConfidenceScore } from '../lib/csvExport';

interface SearchResultsProps {
  isPending: boolean;
  isIdle: boolean;
  error: Error | null;
  data: SearchResultsData | undefined;
  query?: string;
  usSuppliersOnly?: boolean;
  onUsSuppliersOnlyChange?: (value: boolean) => void;
  onRetry?: () => void;
  retryCount?: number;
  isRetrying?: boolean;
  searchMode?: 'parts' | 'services';
}

export const SearchResults = ({
  isPending,
  isIdle,
  error,
  data,
  query = '',
  usSuppliersOnly = false,
  onUsSuppliersOnlyChange,
  onRetry,
  retryCount = 0,
  isRetrying = false,
  searchMode = 'parts',
}: SearchResultsProps) => {
  const resultsRef = useRef<HTMLDivElement>(null);

  const getStatus = (): 'error' | 'success' | 'loading' | 'idle' | 'no-results' => {
    if (error) return 'error';
    if (data?.response && data.response.trim().length > 0) return 'success';
    if (isPending) return 'loading';
    if (isIdle) return 'idle';
    return 'no-results';
  };

  const status = getStatus();
  const finalContent = data?.response || '';
  const currentQuery = query || data?.query || 'your query';
  
  // Calculate confidence score for successful results
  const confidenceScore = finalContent ? generateConfidenceScore(finalContent) : 0;
  
  // CSV export handler
  const handleExportCSV = useCallback(() => {
    if (finalContent && currentQuery) {
      try {
        exportSearchResultsToCSV(finalContent, currentQuery);
      } catch (error) {
        console.error('CSV export failed:', error);
        // Could add toast notification here
      }
    }
  }, [finalContent, currentQuery]);

  let content: React.ReactNode;

  switch (status) {
    case 'error':
      content = (
        <div className="flex flex-col items-center justify-center p-4 md:p-8 text-center space-y-3 md:space-y-4">
          <AlertCircle size={40} className="md:w-12 md:h-12 text-destructive" />
          <h2 className="text-lg md:text-xl font-semibold">Search Failed</h2>
          <p className="text-sm md:text-base text-muted-foreground max-w-md">
            {error?.message || 'An unexpected error occurred during the search.'}
          </p>

          {retryCount > 0 && (
            <Badge variant="outline">
              Retry attempt {retryCount}
            </Badge>
          )}

          {onRetry && (
            <Button
              onClick={onRetry}
              disabled={isRetrying}
              variant="outline"
              className="mt-4"
              size="sm"
            >
              {isRetrying ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw size={16} className="mr-2" />
                  Try Again
                </>
              )}
            </Button>
          )}
        </div>
      );
      break;

    case 'loading':
      content = (
        <div className="flex flex-col items-center justify-center p-4 md:p-8 text-center space-y-3 md:space-y-4">
          <Search size={40} className="md:w-12 md:h-12 text-primary animate-pulse" />
          <h2 className="text-lg md:text-xl font-semibold">
            {isRetrying ? 'Retrying Search...' :
             retryCount > 0 ? 'Searching (Retry in progress)' :
             'Search in progress, please hold'}
          </h2>
          <p className="text-sm md:text-base text-muted-foreground max-w-md">
            {isRetrying ? 'Attempting to reconnect and process your search request.' :
             'Our AI is analyzing your query and generating a comprehensive comparison of matching industrial parts.'}
          </p>

          {(isRetrying || retryCount > 0) && (
            <div className="space-y-2">
              <Badge variant="outline">
                {isRetrying ? 'Retrying due to connection issues' :
                 `Processing (attempt ${retryCount + 1})`}
              </Badge>
              <div className="text-xs text-muted-foreground">
                Advanced retry logic ensures your search completes successfully
              </div>
            </div>
          )}
        </div>
      );
      break;

    case 'idle':
      const IdleIcon = searchMode === 'parts' ? Settings : Factory;
      const idleTitle = searchMode === 'parts' ? 'Find Your Components' : 'Discover Service Providers';
      const idleDescription = searchMode === 'parts'
        ? 'Search for industrial parts and components. Get detailed specifications and supplier comparisons.'
        : 'Search for manufacturing services and capabilities. Compare supplier certifications, equipment, and expertise.';
      content = (
        <div className="flex flex-col items-center justify-center p-4 md:p-8 text-center space-y-3 md:space-y-4 max-w-2xl mx-auto">
          <IdleIcon size={40} className="md:w-12 md:h-12 text-muted-foreground" />
          <h2 className="text-lg md:text-xl font-semibold">{idleTitle}</h2>
          <p className="text-sm md:text-base text-muted-foreground">{idleDescription}</p>
        </div>
      );
      break;

    case 'success':
      content = (
        <div ref={resultsRef} className="w-full">
          {/* Performance Timing Display */}
          {data?.timing && (
            <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
              <Clock size={14} />
              <span className="font-medium">Search completed in {(data.timing.total / 1000).toFixed(2)}s</span>
              <span className="text-xs">
                (Network: {(data.timing.network / 1000).toFixed(2)}s
                {data.timing.transform !== undefined && `, Processing: ${(data.timing.transform / 1000).toFixed(3)}s`})
              </span>
            </div>
          )}
          <SearchResultsContent
            responseText={finalContent}
            originalQuery={currentQuery}
            usSuppliersOnly={usSuppliersOnly}
            onUsSuppliersOnlyChange={onUsSuppliersOnlyChange}
          />
        </div>
      );
      break;

    case 'no-results':
    default:
      content = (
        <div className="flex flex-col items-center justify-center p-4 md:p-8 text-center space-y-3 md:space-y-4">
          <Inbox size={40} className="md:w-12 md:h-12 text-muted-foreground" />
          <h2 className="text-lg md:text-xl font-semibold">No results found</h2>
          <p className="text-sm md:text-base text-muted-foreground">Try adjusting your search query or filters.</p>
          {onRetry && (
            <Button onClick={onRetry} variant="outline" size="sm">
              <RefreshCw size={16} className="mr-2" />
              Try Again
            </Button>
          )}
        </div>
      );
      break;
  }

  return (
    <div className="mt-4 md:mt-8">
      {content}
    </div>
  );
};