'use client'

import { usePathname } from 'next/navigation';

export const LayoutContent = ({ children }: { children: React.ReactNode }) => {
  const pathname = usePathname();
  const isHomePage = pathname === '/';

  return (
    <>
      {/* Gradient background layers - only on home page */}
      {isHomePage && (
        <>
          <div className="gradient-background"></div>
          <div className="gradient-blur"></div>
        </>
      )}

      <div className="min-h-screen relative z-10">
        {children}
      </div>
    </>
  );
};
