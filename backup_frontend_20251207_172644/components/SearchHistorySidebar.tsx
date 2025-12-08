import React from 'react';
import { History, PanelLeftClose, Trash2, Clock } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../lib/utils';
import { useSearchHistory } from '../lib/searchHistoryContext';

interface SearchHistorySidebarProps {
  onClose?: () => void;
  onSearchSelect?: (query: string, searchMode: 'open' | 'refined', usSuppliersOnly: boolean) => void;
}

export const SearchHistorySidebar = ({ onClose, onSearchSelect }: SearchHistorySidebarProps) => {
  const { history, clearHistory, removeFromHistory } = useSearchHistory();

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const handleSearchClick = (query: string, searchMode: 'open' | 'refined', usSuppliersOnly: boolean) => {
    if (onSearchSelect) {
      onSearchSelect(query, searchMode, usSuppliersOnly);
    }
    if (onClose) {
      onClose();
    }
  };
  return (
    <aside className="fixed inset-y-0 left-0 w-80 bg-sidebar border-r border-border p-6 z-nav overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <History size={20} />
          <span className="text-lg font-semibold">Search History</span>
        </div>
        {onClose && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
          >
            <PanelLeftClose size={16} />
          </Button>
        )}
      </div>
      
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          {history.length === 0 ? 'No search history yet' : `${history.length} recent searches`}
        </p>
        {history.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearHistory}
            className="text-xs text-destructive hover:text-destructive"
          >
            Clear All
          </Button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="text-center py-12">
          <History size={48} className="mx-auto text-muted-foreground opacity-20 mb-3" />
          <p className="text-sm text-muted-foreground">
            Your search history will appear here
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {history.map((item) => (
            <li
              key={item.id}
              className="group relative p-3 bg-surface rounded-lg border border-input cursor-pointer hover:bg-muted transition-colors"
              onClick={() => handleSearchClick(item.query, item.searchMode, item.usSuppliersOnly)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground truncate">
                    {item.query}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-muted-foreground">
                      {item.searchMode} search
                    </span>
                    {item.usSuppliersOnly && (
                      <>
                        <span className="text-xs text-muted-foreground">•</span>
                        <span className="text-xs text-muted-foreground">US only</span>
                      </>
                    )}
                    {item.resultCount !== undefined && (
                      <>
                        <span className="text-xs text-muted-foreground">•</span>
                        <span className="text-xs text-muted-foreground">
                          {item.resultCount} results
                        </span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                    <Clock size={12} />
                    {formatTimestamp(item.timestamp)}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFromHistory(item.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 size={14} className="text-destructive" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
};