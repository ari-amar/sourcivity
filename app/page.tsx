'use client'

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Camera } from 'lucide-react';

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadedPhoto, setUploadedPhoto] = useState<File | null>(null);
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // Navigate to search page with the query
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedPhoto(file);
      // Navigate to search page with photo indicator
      router.push(`/search?photo=true`);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 md:px-6 min-h-[calc(100vh-4rem)] pt-4 md:-mt-24 relative">
      <div className="w-full max-w-3xl space-y-4 md:space-y-8 relative z-10">
        {/* Main heading */}
        <div className="text-center space-y-2 md:space-y-4">
          <h1 className="text-2xl sm:text-3xl md:text-5xl font-bold text-foreground leading-tight">
            Intelligent Parts Search
          </h1>
        </div>

        {/* Search bar with enhanced glassmorphism */}
        <form onSubmit={handleSearch} className="relative">
          <div className="relative search-bar-glass rounded-full">
            <input
              type="text"
              value={searchQuery}
              onChange={handleChange}
              placeholder="Search for components..."
              className="w-full px-4 md:px-6 py-3 md:py-5 pr-20 md:pr-32 text-sm md:text-lg bg-transparent rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400/50 border-0 transition-all placeholder:text-sm md:placeholder:text-base"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 md:gap-2">
              <label
                htmlFor="photo-upload"
                className="p-2 md:p-3 bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 cursor-pointer transition-all"
                title="Upload photo"
              >
                <Camera size={20} className="md:w-6 md:h-6" />
                <input
                  id="photo-upload"
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </label>
              <button
                type="submit"
                disabled={!searchQuery.trim()}
                className="p-2 md:p-3 bg-primary text-primary-foreground rounded-full hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <Search size={20} className="md:w-6 md:h-6" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
