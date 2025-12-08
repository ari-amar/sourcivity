'use client'

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { ProductItem, RFQCartItem } from './types';

interface RFQCartContextType {
  cartItems: RFQCartItem[];
  addToCart: (product: ProductItem) => void;
  removeFromCart: (productId: string) => void;
  clearCart: () => void;
  isInCart: (productId: string) => boolean;
  cartCount: number;
}

const RFQCartContext = createContext<RFQCartContextType | undefined>(undefined);

export const useRFQCart = () => {
  const context = useContext(RFQCartContext);
  if (!context) {
    throw new Error('useRFQCart must be used within RFQCartProvider');
  }
  return context;
};

interface RFQCartProviderProps {
  children: ReactNode;
}

export const RFQCartProvider = ({ children }: RFQCartProviderProps) => {
  const [cartItems, setCartItems] = useState<RFQCartItem[]>([]);

  const addToCart = useCallback((product: ProductItem) => {
    setCartItems(prev => {
      // Check if item already exists
      if (prev.some(item => item.id === product.id)) {
        return prev;
      }

      const cartItem: RFQCartItem = {
        ...product,
        addedAt: new Date().toISOString()
      };

      return [...prev, cartItem];
    });
  }, []);

  const removeFromCart = useCallback((productId: string) => {
    setCartItems(prev => prev.filter(item => item.id !== productId));
  }, []);

  const clearCart = useCallback(() => {
    setCartItems([]);
  }, []);

  const isInCart = useCallback((productId: string) => {
    return cartItems.some(item => item.id === productId);
  }, [cartItems]);

  const value: RFQCartContextType = {
    cartItems,
    addToCart,
    removeFromCart,
    clearCart,
    isInCart,
    cartCount: cartItems.length
  };

  return (
    <RFQCartContext.Provider value={value}>
      {children}
    </RFQCartContext.Provider>
  );
};
