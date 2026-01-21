'use client'

import React, { useState, useMemo } from 'react';
import { ExternalLink } from 'lucide-react';
import { Badge } from './Badge';
import { Switch } from './Switch';
import type { ProductItem } from '../lib/types';
import { cn } from '../lib/utils';

interface ProductTableProps {
  products: ProductItem[];
  columns?: string[];
  usSuppliersOnly?: boolean;
  onUsSuppliersOnlyChange?: (value: boolean) => void;
}

// Default column names if not provided
const DEFAULT_COLUMNS = ['Material', 'Thread Size', 'Load Rating', 'Operating Temperature'];

// Country flag to name mapping
const getCountryName = (flag: string): string => {
  const countryMap: { [key: string]: string } = {
    '🇺🇸': 'United States',
    '🇨🇦': 'Canada',
    '🇬🇧': 'United Kingdom',
    '🇩🇪': 'Germany',
    '🇫🇷': 'France',
    '🇮🇹': 'Italy',
    '🇪🇸': 'Spain',
    '🇯🇵': 'Japan',
    '🇨🇳': 'China',
    '🇰🇷': 'South Korea',
    '🇮🇳': 'India',
    '🇦🇺': 'Australia',
    '🇧🇷': 'Brazil',
    '🇲🇽': 'Mexico',
    '🇳🇱': 'Netherlands',
    '🇸🇪': 'Sweden',
    '🇨🇭': 'Switzerland',
    '🇸🇬': 'Singapore',
    '🇹🇼': 'Taiwan',
  };
  return countryMap[flag] || 'Unknown';
};

// Supplier type to full description mapping (only for abbreviated types)
const getSupplierTypeDescription = (type: string): string | null => {
  const typeMap: { [key: string]: string} = {
    'OEM': 'Original Equipment Manufacturer',
    'CM': 'Contract Manufacturer',
    'SP': 'Service Provider',
    '3PL': 'Logistics Provider',
    'MRO': 'Maintenance & Repair Supplier',
    'T&C': 'Testing & Calibration Provider',
    'ITSP': 'IT & Software Provider',
  };
  return typeMap[type] || null;
};

export const ProductTable = ({ products, columns = DEFAULT_COLUMNS, usSuppliersOnly = false, onUsSuppliersOnlyChange }: ProductTableProps) => {
  const [sortColumn, setSortColumn] = useState<string | null>('Part Name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Filter and sort products
  const filteredProducts = useMemo(() => {
    let filtered = usSuppliersOnly
      ? products.filter(product => product.supplierFlag === '🇺🇸')
      : products;

    // Apply sorting if a column is selected
    if (sortColumn) {
      filtered = [...filtered].sort((a, b) => {
        let aVal = sortColumn === 'Part Name' ? a.partName : a.columnData[sortColumn];
        let bVal = sortColumn === 'Part Name' ? b.partName : b.columnData[sortColumn];

        // Handle N/A values
        if (!aVal || aVal === 'N/A') return 1;
        if (!bVal || bVal === 'N/A') return -1;

        // Convert to strings for comparison
        aVal = String(aVal);
        bVal = String(bVal);

        const comparison = aVal.localeCompare(bVal, undefined, { numeric: true });
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    return filtered;
  }, [products, usSuppliersOnly, sortColumn, sortDirection]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      // Toggle direction or clear sort
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else {
        setSortColumn(null);
        setSortDirection('asc');
      }
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  if (filteredProducts.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 bg-white rounded-xl border border-gray-200">
        <p className="text-lg font-medium">No products to display</p>
        <p className="text-sm mt-1">{usSuppliersOnly ? 'No US suppliers found. Try disabling the "US Suppliers Only" filter.' : 'Try adjusting your search criteria'}</p>
      </div>
    );
  }

  // All available sort options
  const sortOptions = ['Part Name', ...columns];

  return (
    <div className="space-y-4">
      {/* Controls Row - Sort By and US Suppliers Only */}
      <div className="flex items-center justify-end gap-6 mb-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700">Sort by:</label>
          <select
            value={sortColumn || 'Part Name'}
            onChange={(e) => {
              const value = e.target.value;
              setSortColumn(value);
              setSortDirection('asc');
            }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          >
            {sortOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          {sortColumn && (
            <button
              onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors"
              title={sortDirection === 'asc' ? 'Sort descending' : 'Sort ascending'}
            >
              {sortDirection === 'asc' ? '↑ Ascending' : '↓ Descending'}
            </button>
          )}
        </div>
        {onUsSuppliersOnlyChange && (
          <div className="flex items-center gap-2">
            <label htmlFor="usSuppliersOnly" className="text-sm font-medium text-gray-700">
              US Suppliers Only
            </label>
            <Switch
              id="usSuppliersOnly"
              checked={usSuppliersOnly}
              onCheckedChange={onUsSuppliersOnlyChange}
            />
          </div>
        )}
      </div>

      {/* Card Grid Container */}
      <div className="grid grid-cols-1 gap-4">
        {filteredProducts.map((product) => {
          return (
            <div
              key={product.id}
              className="bg-white rounded-xl border border-gray-200 py-5 px-6 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Single Row Layout: Product Info | Specs */}
              <div className="flex items-center">
                {/* Left: Product Info */}
                <div className="w-[280px] shrink-0 pr-6 border-r border-gray-200">
                  <div className="flex items-center gap-1.5 mb-2">
                    <a
                      href={product.partUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-bold text-gray-900 hover:text-blue-600 transition-colors whitespace-nowrap overflow-hidden text-ellipsis"
                      title={product.partName}
                    >
                      {product.partName}
                    </a>
                    {product.extractionError && (
                      <span
                        className="text-amber-500 cursor-help flex-shrink-0"
                        title={`Extraction failed: ${product.extractionError}`}
                      >
                        ⚠️
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      --%
                    </span>
                    <span className="text-sm leading-none text-gray-400" title="Country">
                      🏳️
                    </span>
                    <Badge
                      variant="secondary"
                      className="text-xs font-normal whitespace-nowrap px-1.5 py-0.5"
                      title={getSupplierTypeDescription(product.supplierType) || undefined}
                    >
                      {product.supplierType}
                    </Badge>
                    <a
                      href={product.contactUrl || product.partUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-base hover:opacity-70 transition-opacity"
                      title="Contact Supplier"
                    >
                      💬
                    </a>
                  </div>
                </div>

                {/* Right: Specifications - Horizontal Grid */}
                <div className="flex-1 flex gap-6 px-8 overflow-hidden">
                  {columns.slice(0, 5).map((column, index) => (
                    <div key={index} className="flex-1 flex flex-col min-w-0">
                      <div className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1 truncate" title={column}>
                        {column.replace(/_/g, ' ')}
                      </div>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2" title={product.columnData[column] || 'N/A'}>
                        {product.columnData[column] || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer with stats */}
      <div className="bg-white rounded-lg border border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing <span className="font-semibold text-gray-900">{filteredProducts.length}</span> {filteredProducts.length === 1 ? 'result' : 'results'}
            {usSuppliersOnly && products.length > filteredProducts.length && (
              <span className="ml-2 text-blue-600">
                (filtered from {products.length} total)
              </span>
            )}
          </span>
        </div>
      </div>
    </div>
  );
};
