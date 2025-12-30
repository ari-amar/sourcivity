import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)',
  '/sign-up(.*)',
]);

export default clerkMiddleware(async (auth: any, request: NextRequest) => {
  const pathname = request.nextUrl.pathname;
  
  // Protect API routes with authentication
  if (pathname.startsWith('/api/')) {
    // Check if user is authenticated
    const { userId } = await auth();
    
    if (!userId) {
      // User is not authenticated - return 401 Unauthorized
      return new NextResponse(
        JSON.stringify({ error: 'Unauthorized', message: 'Authentication required' }),
        { 
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }
    
    // User is authenticated - pass request through to Vercel routing
    // This allows the request to reach the Python serverless function
    return NextResponse.next();
  }
  
  // For non-API routes, use standard protection
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Include /api routes for authentication check
    '/(api|trpc)(.*)',
  ],
};
