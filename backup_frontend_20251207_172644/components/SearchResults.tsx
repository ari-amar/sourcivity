import React, { useEffect, useRef, useState, useCallback } from 'react';
import { AlertCircle, Inbox, Search, Loader2, RefreshCw, Clock, AlertTriangle, Download } from 'lucide-react';
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
  onRetry?: () => void;
  retryCount?: number;
  isRetrying?: boolean;
}

export const SearchResults = ({
  isPending,
  isIdle,
  error,
  data,
  query = '',
  usSuppliersOnly = false,
  onRetry,
  retryCount = 0,
  isRetrying = false,
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
        <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
          <AlertCircle size={48} className="text-destructive" />
          <h2 className="text-xl font-semibold">Search Failed</h2>
          <p className="text-muted-foreground max-w-md">
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
        <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
          <Search size={48} className="text-primary animate-pulse" />
          <h2 className="text-xl font-semibold">
            {isRetrying ? 'Retrying Search...' : 
             retryCount > 0 ? 'Searching (Retry in progress)' :
             'Search in progress, please hold'}
          </h2>
          <p className="text-muted-foreground max-w-md">
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
      content = (
        <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
          <Inbox size={48} className="text-muted-foreground" />
          <h2 className="text-xl font-semibold">Start your search</h2>
          <p className="text-muted-foreground">Your search results will appear here as a comparison analysis.</p>
        </div>
      );
      break;

    case 'success':
      content = (
        <div ref={resultsRef} className="space-y-6">
          <div className="border-b border-border pb-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold mb-2">
                  Search Results for "{currentQuery}"
                </h2>
                <p className="text-muted-foreground">AI-powered comparison analysis</p>
                {data?.createdAt && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Generated on {new Date(data.createdAt).toLocaleString()}
                  </p>
                )}
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline">
                    Confidence: {Math.round(confidenceScore * 100)}%
                  </Badge>
                  {retryCount > 0 && (
                    <Badge variant="outline">
                      Completed after {retryCount} retry{retryCount === 1 ? '' : 'ies'}
                    </Badge>
                  )}
                </div>
              </div>
              <Button
                onClick={handleExportCSV}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <Download size={16} />
                Export CSV
              </Button>
            </div>
          </div>

          <div className="prose max-w-none w-full">
            <SearchResultsContent 
              responseText={finalContent} 
              originalQuery={currentQuery}
              usSuppliersOnly={usSuppliersOnly}
            />
          </div>
        </div>
      );
      break;

    case 'no-results':
    default:
      content = (
        <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
          <Inbox size={48} className="text-muted-foreground" />
          <h2 className="text-xl font-semibold">No results found</h2>
          <p className="text-muted-foreground">Try adjusting your search query or filters.</p>
          {onRetry && (
            <Button onClick={onRetry} variant="outline">
              <RefreshCw size={16} className="mr-2" />
              Try Again
            </Button>
          )}
        </div>
      );
      break;
  }

  return (
    <div className="mt-8 bg-surface border border-input rounded-lg p-6">
      {content}
    </div>
  );
};