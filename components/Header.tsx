'use client'

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { cn } from '../lib/utils';
import { Menu, X } from 'lucide-react';
import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';

interface HeaderProps {
  currentPage?: 'search';
  showNavigation?: boolean;
}

export const Header = ({ currentPage = 'search', showNavigation = true }: HeaderProps) => {
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navigationItems: any[] = [];

  return (
    <header className="relative border-b border-border/30 bg-gray-50">
      {/* Header gradient background - confined to header only */}
      <div className="header-gradient-background"></div>

      <div className="w-full relative z-10">
        <div className="flex items-center h-16 px-4 md:pr-6 md:pl-6">
          {/* Logo */}
          <Link href="/" className="flex items-center group md:ml-4">
            <span className="font-bold text-xl md:text-2xl bg-gradient-to-r from-primary via-blue-600 to-purple-600 bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient transition-all duration-300 group-hover:scale-105 group-hover:tracking-wide">
              Sourcivity
            </span>
          </Link>

          {/* Desktop Navigation - Centered */}
          {showNavigation && (
            <nav className="hidden md:flex items-center space-x-1 absolute left-1/2 transform -translate-x-1/2">
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
          )}

          {/* Mobile Actions */}
          <div className="md:hidden ml-auto flex items-center gap-2">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  Sign In
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
            {showNavigation && (
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="p-2 text-foreground hover:bg-muted rounded-lg transition-colors"
                aria-label="Toggle menu"
              >
                {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
            )}
          </div>

          {/* Actions - Right side */}
          <div className="hidden md:flex items-center gap-4 ml-auto">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  Sign In
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button className="bg-primary text-primary-foreground rounded-full font-medium text-sm h-10 px-5 hover:bg-primary/90 transition-all">
                  Sign Up
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {showNavigation && isMobileMenuOpen && (
          <div className="md:hidden border-t border-border/30 bg-gray-50">
            <nav className="flex flex-col py-2">
              {navigationItems.map((item) => (
                <Link
                  key={item.key}
                  href={item.href}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={cn(
                    "px-4 py-3 text-base font-medium transition-colors duration-200",
                    currentPage === item.key
                      ? "text-foreground bg-muted border-l-4 border-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <div className="flex flex-col">
                    <span>{item.label}</span>
                    <span className="text-xs text-muted-foreground mt-0.5">{item.description}</span>
                  </div>
                </Link>
              ))}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
};