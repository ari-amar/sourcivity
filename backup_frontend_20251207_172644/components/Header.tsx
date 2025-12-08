import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { cn } from '../lib/utils';

interface HeaderProps {
  currentPage?: 'search' | 'messages';
}

export const Header = ({ currentPage = 'search' }: HeaderProps) => {
  const router = useRouter();

  const navigationItems = [
    {
      key: 'search',
      label: 'Search',
      href: '/search',
      description: 'Find industrial parts'
    },
    {
      key: 'messages',
      label: 'Messages',
      href: '/rfq-dashboard',
      description: 'RFQ tracking & reminders'
    }
  ];

  return (
    <header className="border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/60">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/search" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-primary-foreground font-bold text-sm">S</span>
              </div>
              <span className="font-bold text-xl text-foreground">Sourcivity</span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            {navigationItems.map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className={cn(
                  "relative px-6 py-2 text-sm font-medium transition-colors duration-200 rounded-lg",
                  currentPage === item.key
                    ? "text-foreground bg-muted"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                {item.label}
                {/* Active indicator */}
                {currentPage === item.key && (
                  <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-12 h-0.5 bg-primary rounded-full" />
                )}
              </Link>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center space-x-2">
            {/* Future: User profile, notifications, etc. */}
          </div>
        </div>
      </div>
    </header>
  );
};