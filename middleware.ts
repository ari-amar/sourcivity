import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import type { NextRequest } from 'next/server';

const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)',
  '/sign-up(.*)',
]);

export default clerkMiddleware(async (auth: any, request: NextRequest) => {
  // Skip authentication for API routes (handled by Python backend)
  const pathname = request.nextUrl.pathname;
  if (pathname.startsWith('/api/')) {
    return;
  }
  
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Exclude /api routes - they're handled by Python serverless function
    // Only match non-API routes for authentication
  ],
};
