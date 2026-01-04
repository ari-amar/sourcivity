'use client'

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Force dynamic rendering to prevent prerendering errors (uses useRouter for redirect)
export const dynamic = 'force-dynamic';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.push('/search');
  }, [router]);

  return null;
}
