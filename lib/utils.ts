import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Get the backend URL for API calls.
 * - If NEXT_PUBLIC_BACKEND_URL is set, use it
 * - In browser production (non-localhost), use relative URLs (empty string)
 * - Otherwise, default to localhost:8000 for local development
 */
export function getBackendUrl(): string {
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  
  // In browser, check if we're on localhost
  if (typeof window !== 'undefined') {
    const isLocalhost = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1';
    return isLocalhost ? 'http://localhost:8000' : '';
  }
  
  // Server-side: default to localhost for development
  return 'http://localhost:8000';
}