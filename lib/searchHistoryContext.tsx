'use client'

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react';

export interface SearchHistoryItem {
  id: string;
  query: string;
  searchMode: 'open' | 'refined';
  usSuppliersOnly: boolean;
  timestamp: string;
  resultCount?: number;
}

interface SearchHistoryContextType {
  history: SearchHistoryItem[];
  addToHistory: (item: Omit<SearchHistoryItem, 'id' | 'timestamp'>) => void;
  clearHistory: () => void;
  removeFromHistory: (id: string) => void;
}

const SearchHistoryContext = createContext<SearchHistoryContextType | undefined>(undefined);

export const useSearchHistory = () => {
  const context = useContext(SearchHistoryContext);
  if (!context) {
    throw new Error('useSearchHistory must be used within SearchHistoryProvider');
  }
  return context;
};

interface SearchHistoryProviderProps {
  children: ReactNode;
}

const STORAGE_KEY = 'sourceflow_search_history';
const MAX_HISTORY_ITEMS = 50;

export const SearchHistoryProvider = ({ children }: SearchHistoryProviderProps) => {
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const storedHistory = localStorage.getItem(STORAGE_KEY);
      if (storedHistory) {
        const parsed = JSON.parse(storedHistory);
        setHistory(parsed);
      }
    } catch (error) {
      console.error('Failed to load search history from localStorage:', error);
    }
  }, []);

  // Save history to localStorage whenever it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      console.error('Failed to save search history to localStorage:', error);
    }
  }, [history]);

  const addToHistory = useCallback((item: Omit<SearchHistoryItem, 'id' | 'timestamp'>) => {
    setHistory(prev => {
      // Check if this exact query already exists (avoid duplicates)
      const isDuplicate = prev.some(
        h => h.query.toLowerCase() === item.query.toLowerCase() &&
             h.searchMode === item.searchMode &&
             h.usSuppliersOnly === item.usSuppliersOnly
      );

      if (isDuplicate) {
        // Move existing item to top by removing and re-adding with new timestamp
        const filtered = prev.filter(
          h => !(h.query.toLowerCase() === item.query.toLowerCase() &&
                 h.searchMode === item.searchMode &&
                 h.usSuppliersOnly === item.usSuppliersOnly)
        );

        const newItem: SearchHistoryItem = {
          ...item,
          id: Date.now().toString(),
          timestamp: new Date().toISOString()
        };

        return [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);
      }

      const newItem: SearchHistoryItem = {
        ...item,
        id: Date.now().toString(),
        timestamp: new Date().toISOString()
      };

      // Add to beginning and limit to MAX_HISTORY_ITEMS
      return [newItem, ...prev].slice(0, MAX_HISTORY_ITEMS);
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear search history from localStorage:', error);
    }
  }, []);

  const removeFromHistory = useCallback((id: string) => {
    setHistory(prev => prev.filter(item => item.id !== id));
  }, []);

  const value: SearchHistoryContextType = {
    history,
    addToHistory,
    clearHistory,
    removeFromHistory
  };

  return (
    <SearchHistoryContext.Provider value={value}>
      {children}
    </SearchHistoryContext.Provider>
  );
};
