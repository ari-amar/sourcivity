'use client'

import React, { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, FileText, ExternalLink, CheckCircle2 } from 'lucide-react';
import { Badge } from './Badge';
import { useRFQCart } from '../lib/rfqCartContext';
import type { ProductItem } from '../lib/types';
import { cn } from '../lib/utils';

interface ProductTableProps {
  products: ProductItem[];
  columns?: string[];
}

type SortField = 'partName' | string; // Can be partName or any column name
type SortDirection = 'asc' | 'desc';

// Default column names if not provided
const DEFAULT_COLUMNS = ['Material', 'Thread Size', 'Load Rating', 'Operating Temperature'];

export const ProductTable = ({ products, columns = DEFAULT_COLUMNS }: ProductTableProps) => {
  const { addToCart, removeFromCart, isInCart } = useRFQCart();
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('partName');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  // Sort products
  const sortedProducts = useMemo(() => {
    return [...products].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      if (sortField === 'partName') {
        aVal = a.partName;
        bVal = b.partName;
      } else {
        // Sort by column data
        aVal = a.columnData[sortField] || '';
        bVal = b.columnData[sortField] || '';
      }

      // Try to parse as numbers if possible
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);

      if (!isNaN(aNum) && !isNaN(bNum)) {
        return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
      }

      // String comparison
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return 0;
    });
  }, [products, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleSelectAll = () => {
    if (selectedRows.size === products.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(products.map(p => p.id)));
    }
  };

  const handleRowSelect = (id: string) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedRows(newSelected);
  };

  const handleToggleRFQ = (product: ProductItem) => {
    if (isInCart(product.id)) {
      removeFromCart(product.id);
    } else {
      addToCart(product);
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    const isActive = sortField === field;
    const Icon = isActive && sortDirection === 'desc' ? ChevronDown : ChevronUp;

    return (
      <Icon
        size={14}
        className={cn(
          "transition-all duration-200",
          isActive ? "text-blue-600 opacity-100" : "text-gray-400 opacity-0 group-hover:opacity-50"
        )}
      />
    );
  };

  if (products.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 bg-white rounded-xl border border-gray-200">
        <p className="text-lg font-medium">No products to display</p>
        <p className="text-sm mt-1">Try adjusting your search criteria</p>
      </div>
    );
  }

  const allSelected = selectedRows.size === products.length && products.length > 0;
  const someSelected = selectedRows.size > 0 && selectedRows.size < products.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Selection Summary Bar (appears when items are selected) */}
      {selectedRows.size > 0 && (
        <div className="bg-blue-50 border-b border-blue-100 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 size={16} className="text-blue-600" />
            <span className="font-medium text-blue-900">
              {selectedRows.size} {selectedRows.size === 1 ? 'item' : 'items'} selected
            </span>
          </div>
          <button
            onClick={() => setSelectedRows(new Set())}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
          >
            Clear selection
          </button>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50/50">
              <th className="w-12 px-6 py-4 text-left">
                <div className="relative inline-flex items-center">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(input) => {
                      if (input) {
                        input.indeterminate = someSelected;
                      }
                    }}
                    onChange={handleSelectAll}
                    className={cn(
                      "w-4 h-4 rounded border-gray-300 transition-all duration-200 cursor-pointer",
                      "text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                      "hover:border-blue-400"
                    )}
                    aria-label="Select all products"
                  />
                </div>
              </th>
              <th className="px-6 py-4 text-left">
                <button
                  onClick={() => handleSort('partName')}
                  className="group flex items-center gap-2 text-xs font-semibold text-gray-700 uppercase tracking-wider hover:text-gray-900 transition-colors"
                >
                  Part Name & Supplier
                  <SortIcon field="partName" />
                </button>
              </th>
              {/* Dynamic Columns */}
              {columns.map((column, index) => (
                <th key={index} className="px-6 py-4 text-left">
                  <button
                    onClick={() => handleSort(column)}
                    className="group flex items-center gap-2 text-xs font-semibold text-gray-700 uppercase tracking-wider hover:text-gray-900 transition-colors"
                  >
                    {column}
                    <SortIcon field={column} />
                  </button>
                </th>
              ))}
              <th className="px-6 py-4 text-center w-32">
                <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sortedProducts.map((product) => {
              const isSelected = selectedRows.has(product.id);
              const isHovered = hoveredRow === product.id;
              const inCart = isInCart(product.id);

              return (
                <tr
                  key={product.id}
                  onMouseEnter={() => setHoveredRow(product.id)}
                  onMouseLeave={() => setHoveredRow(null)}
                  className={cn(
                    "transition-all duration-150",
                    isSelected && "bg-blue-50/50",
                    !isSelected && isHovered && "bg-gray-50",
                    "group"
                  )}
                >
                  <td className="px-6 py-4">
                    <div className="relative inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleRowSelect(product.id)}
                        className={cn(
                          "w-4 h-4 rounded border-gray-300 transition-all duration-200 cursor-pointer",
                          "text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
                          "hover:border-blue-400"
                        )}
                        aria-label={`Select ${product.partName}`}
                      />
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <a
                          href={product.partUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={cn(
                            "text-sm font-medium text-gray-900 hover:text-blue-600 transition-colors",
                            "inline-flex items-center gap-1.5 group/link"
                          )}
                        >
                          {product.partName}
                          <ExternalLink
                            size={14}
                            className="opacity-0 group-hover/link:opacity-100 transition-opacity text-blue-600"
                          />
                        </a>
                        {product.hasSpecSheet && (
                          <FileText
                            size={14}
                            className="text-gray-400 hover:text-blue-600 cursor-pointer transition-colors"
                          />
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg leading-none">{product.supplierFlag}</span>
                        <Badge
                          variant="secondary"
                          className="text-xs font-normal whitespace-nowrap"
                        >
                          {product.supplierType}
                        </Badge>
                      </div>
                    </div>
                  </td>
                  {/* Dynamic column data cells */}
                  {columns.map((column, colIndex) => (
                    <td key={colIndex} className="px-6 py-4">
                      <span className="text-sm text-gray-700">
                        {product.columnData[column] || 'N/A'}
                      </span>
                    </td>
                  ))}
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => handleToggleRFQ(product)}
                      className={cn(
                        "inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200",
                        "focus:outline-none focus:ring-2 focus:ring-offset-2",
                        inCart
                          ? "bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 hover:border-green-300 active:scale-95 focus:ring-green-500"
                          : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md active:scale-95 focus:ring-blue-500"
                      )}
                    >
                      {inCart ? (
                        <>
                          <CheckCircle2 size={14} />
                          Added
                        </>
                      ) : (
                        'RFQ'
                      )}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer with stats */}
      <div className="border-t border-gray-200 bg-gray-50/30 px-6 py-3">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Showing <span className="font-semibold text-gray-900">{products.length}</span> {products.length === 1 ? 'result' : 'results'}
          </span>
          {selectedRows.size > 0 && (
            <span>
              <span className="font-semibold text-gray-900">{selectedRows.size}</span> selected
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
