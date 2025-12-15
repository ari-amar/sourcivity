'use client'

import { usePathname } from 'next/navigation';
import { Header } from './Header';

export const ClientHeader = () => {
  const pathname = usePathname();

  // Hide navigation on landing page
  const showNavigation = pathname !== '/';

  // Determine current page based on pathname
  let currentPage: 'search' | 'messages' = 'search';

  if (pathname?.includes('/rfq-dashboard') || pathname?.includes('/messages')) {
    currentPage = 'messages';
  } else if (pathname?.includes('/search')) {
    currentPage = 'search';
  }

  return <Header currentPage={currentPage} showNavigation={showNavigation} />;
};