'use client'

import React, { useState, useMemo } from 'react';
import { ExternalLink, CheckCircle2 } from 'lucide-react';
import { Badge } from './Badge';
import { Switch } from './Switch';
import { useRFQCart } from '../lib/rfqCartContext';
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
  const { addToCart, removeFromCart, isInCart } = useRFQCart();
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

  const handleToggleRFQ = (product: ProductItem) => {
    if (isInCart(product.id)) {
      removeFromCart(product.id);
    } else {
      addToCart(product);
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
          const inCart = isInCart(product.id);

          return (
            <div
              key={product.id}
              className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Unified Row Layout */}
              <div className="space-y-4">
                {/* Product Info Column */}
                <div className="pb-4 border-b border-gray-200">
                  <a
                    href={product.partUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-base font-semibold text-gray-900 hover:text-blue-600 transition-colors flex items-center gap-2 group mb-2"
                  >
                    {product.partName}
                    <ExternalLink
                      size={14}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-600 shrink-0"
                    />
                  </a>

                  {/* Supplier Metadata */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {product.rating && (
                      <span className="text-sm text-gray-600 flex items-center gap-0.5">
                        {product.rating}★
                      </span>
                    )}
                    <span
                      className="text-lg leading-none"
                      title={getCountryName(product.supplierFlag)}
                    >
                      {product.supplierFlag}
                    </span>
                    <Badge
                      variant="secondary"
                      className="text-xs font-normal whitespace-nowrap"
                      title={getSupplierTypeDescription(product.supplierType) || undefined}
                    >
                      {product.supplierType}
                    </Badge>
                    {product.datasheetUrl && (
                      <a
                        href={product.datasheetUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Badge
                          variant="secondary"
                          className="text-xs font-normal whitespace-nowrap bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors cursor-pointer"
                        >
                          Datasheet
                        </Badge>
                      </a>
                    )}
                  </div>
                </div>

                {/* Specifications Row - Horizontal Side-by-Side */}
                <div className="flex items-center gap-4 flex-wrap">
                  {columns.map((column, index) => (
                    <div key={index} className="flex flex-col min-w-[120px]">
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-1">
                        {column}
                      </div>
                      <div className="text-sm font-medium text-gray-900">
                        {product.columnData[column] || 'N/A'}
                      </div>
                    </div>
                  ))}

                  {/* RFQ Button Column */}
                  <div className="ml-auto">
                    <button
                      onClick={() => handleToggleRFQ(product)}
                      className={cn(
                        "px-4 py-2 rounded-lg font-medium text-sm transition-all",
                        inCart
                          ? "bg-green-100 text-green-700 border border-green-300"
                          : "bg-blue-600 text-white hover:bg-blue-700"
                      )}
                    >
                      {inCart ? (
                        <>
                          <CheckCircle2 size={16} className="inline mr-1" />
                          Added
                        </>
                      ) : (
                        'RFQ'
                      )}
                    </button>
                  </div>
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
