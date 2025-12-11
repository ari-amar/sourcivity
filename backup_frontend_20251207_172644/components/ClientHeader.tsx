'use client'

import { usePathname } from 'next/navigation';
import { Header } from './Header';

export const ClientHeader = () => {
  const pathname = usePathname();
  
  // Determine current page based on pathname
  let currentPage: 'search' | 'messages' = 'search';
  
  if (pathname?.includes('/rfq-dashboard') || pathname?.includes('/messages')) {
    currentPage = 'messages';
  } else if (pathname?.includes('/search') || pathname === '/') {
    currentPage = 'search';
  }

  return <Header currentPage={currentPage} />;
};