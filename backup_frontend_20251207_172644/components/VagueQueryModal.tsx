import React from 'react';
import { Button } from './Button';
import { X, AlertTriangle } from 'lucide-react';

interface VagueQueryModalProps {
  isOpen: boolean;
  onClose: () => void;
  query: string;
}

export const VagueQueryModal = ({
  isOpen,
  onClose,
  query,
}: VagueQueryModalProps) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 bg-surface border border-input rounded-lg shadow-lg">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <AlertTriangle size={20} className="text-destructive" />
            <h3 className="text-lg font-semibold">Search Too Vague</h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="p-2"
          >
            <X size={16} />
          </Button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <p className="text-foreground mb-3">
              Your search "<span className="font-semibold text-destructive">{query}</span>" is too general to find specific parts.
            </p>
          </div>

          <div className="bg-muted p-4 rounded-lg">
            <p className="text-sm font-medium mb-2">Please provide more details such as:</p>
            <ul className="text-sm text-muted-foreground space-y-1 ml-4">
              <li>• <strong>Size or dimensions</strong> (e.g., M8, 1/4", 25mm)</li>
              <li>• <strong>Material</strong> (e.g., stainless steel, aluminum, brass)</li>
              <li>• <strong>Technical specifications</strong> (e.g., voltage, RPM, pressure rating)</li>
              <li>• <strong>Part number</strong> (if you have one)</li>
              <li>• <strong>Application or use case</strong></li>
            </ul>
          </div>

          <div className="bg-primary/5 border border-primary/20 p-4 rounded-lg">
            <p className="text-sm font-medium text-primary mb-2">💡 Example searches:</p>
            <ul className="text-sm space-y-1">
              <li className="text-muted-foreground">→ "M8 x 25mm stainless steel hex bolt"</li>
              <li className="text-muted-foreground">→ "1HP 3-phase 1750 RPM motor"</li>
              <li className="text-muted-foreground">→ "6203 ball bearing"</li>
            </ul>
          </div>

          {/* Action Button */}
          <div className="pt-2">
            <Button
              onClick={onClose}
              className="w-full"
            >
              Got it, I'll be more specific
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
