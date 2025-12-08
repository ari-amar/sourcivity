import React, { useCallback, useState } from 'react';
import { Upload, X } from 'lucide-react';
import { Button } from './Button';
import { cn } from '../lib/utils';

export interface FileDropzoneProps {
  className?: string;
  accept?: string;
  maxFiles?: number;
  maxSize?: number; // in bytes
  onFilesSelected?: (files: File[]) => void;
  disabled?: boolean;
  icon?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  className = '',
  accept,
  maxFiles = 1,
  maxSize = 10 * 1024 * 1024, // 10MB default
  onFilesSelected,
  disabled = false,
  icon = <Upload size={32} />,
  title = 'Drop files here',
  subtitle = 'or click to select files',
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  }, []);

  const validateFiles = useCallback((files: FileList) => {
    const fileArray = Array.from(files);
    
    if (fileArray.length > maxFiles) {
      setError(`Maximum ${maxFiles} file(s) allowed`);
      return [];
    }

    const oversizedFiles = fileArray.filter(file => file.size > maxSize);
    if (oversizedFiles.length > 0) {
      setError(`File size must be less than ${(maxSize / (1024 * 1024)).toFixed(1)}MB`);
      return [];
    }

    setError(null);
    return fileArray;
  }, [maxFiles, maxSize]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = validateFiles(e.dataTransfer.files);
    if (files.length > 0 && onFilesSelected) {
      onFilesSelected(files);
    }
  }, [disabled, validateFiles, onFilesSelected]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled || !e.target.files) return;

    const files = validateFiles(e.target.files);
    if (files.length > 0 && onFilesSelected) {
      onFilesSelected(files);
    }
  }, [disabled, validateFiles, onFilesSelected]);

  return (
    <div className={cn('relative', className)}>
      <label
        className={cn(
          'relative flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer transition-colors',
          isDragging 
            ? 'border-primary bg-primary/5' 
            : 'border-input bg-background hover:bg-muted/50',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          onChange={handleFileInput}
          accept={accept}
          multiple={maxFiles > 1}
          disabled={disabled}
          aria-label="File upload"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        
        <div className="flex flex-col items-center gap-4">
          <span className="text-muted-foreground">{icon}</span>
          <div className="text-center">
            <span className="text-lg font-medium text-foreground block">{title}</span>
            {subtitle && (
              <span className="text-sm text-muted-foreground mt-1 block">{subtitle}</span>
            )}
          </div>
        </div>
      </label>

      {error && (
        <div className="mt-2 p-3 bg-destructive/10 border border-destructive/20 rounded-md">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}
    </div>
  );
};