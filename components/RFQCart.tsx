'use client';

import React, { useState } from 'react';
import { ShoppingCart, X, ChevronDown } from 'lucide-react';
import { RFQSubmissionModal } from './RFQSubmissionModal';
import { useRFQCart } from '../lib/rfqCartContext';

export const RFQCart = () => {
  const { cartItems, removeFromCart, clearCart, cartCount } = useRFQCart();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRFQModalOpen, setIsRFQModalOpen] = useState(false);

  const handleProceed = () => {
    setIsRFQModalOpen(true);
    setIsExpanded(false); // Minimize cart when opening RFQ modal
  };

  if (cartCount === 0) {
    return null;
  }

  return (
    <>
      {/* Floating Cart Button - Bottom Right */}
      <div className="fixed bottom-6 right-6 z-[900]">
        {!isExpanded ? (
          // Collapsed: Floating Button
          <button
            onClick={() => setIsExpanded(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-2xl transition-all duration-200 hover:scale-105 flex items-center gap-3 px-6 py-4"
          >
            <div className="relative">
              <ShoppingCart size={24} />
              <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                {cartCount}
              </span>
            </div>
            <span className="font-semibold">RFQ Cart</span>
          </button>
        ) : (
          // Expanded: Mini Cart Panel
          <div className="bg-white rounded-2xl shadow-2xl w-96 max-h-[70vh] flex flex-col border border-gray-200">
            {/* Header */}
            <div className="border-b border-gray-200 px-5 py-4 bg-gradient-to-r from-blue-600 to-blue-700 rounded-t-2xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-white">
                  <ShoppingCart size={20} />
                  <div>
                    <h3 className="font-semibold">RFQ Cart</h3>
                    <p className="text-xs text-blue-100">{cartCount} item{cartCount === 1 ? '' : 's'}</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="text-white hover:bg-white/20 rounded-lg p-1.5 transition-colors"
                >
                  <ChevronDown size={20} />
                </button>
              </div>
            </div>

            {/* Cart Items */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
              {cartItems.map((item) => (
                <div
                  key={item.id}
                  className="bg-gray-50 rounded-lg p-3 relative hover:bg-gray-100 transition-colors"
                >
                  <button
                    onClick={() => removeFromCart(item.id)}
                    className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
                    aria-label={`Remove ${item.partName} from cart`}
                  >
                    <X size={16} />
                  </button>

                  <div className="pr-6">
                    <a
                      href={item.partUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium text-sm hover:underline block mb-2"
                    >
                      {item.partName}
                    </a>

                    <div className="flex items-center gap-2 mb-2 text-xs">
                      <span>{item.supplierFlag}</span>
                      <span className="text-gray-600">{item.supplierType}</span>
                    </div>

                    {/* Show first 2 specs */}
                    <div className="text-xs text-gray-600">
                      {Object.entries(item.columnData).slice(0, 2).map(([key, value]) => (
                        <div key={key} className="truncate">
                          <span className="font-medium">{key}:</span> {value}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer Actions */}
            <div className="border-t border-gray-200 px-5 py-4 bg-gray-50 rounded-b-2xl">
              <div className="flex gap-3">
                <button
                  onClick={clearCart}
                  className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  Clear All
                </button>
                <button
                  onClick={handleProceed}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <ShoppingCart size={16} />
                  Submit RFQ ({cartCount})
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* RFQ Submission Modal */}
      <RFQSubmissionModal
        isOpen={isRFQModalOpen}
        onClose={() => setIsRFQModalOpen(false)}
        cartItems={cartItems}
      />
    </>
  );
};
