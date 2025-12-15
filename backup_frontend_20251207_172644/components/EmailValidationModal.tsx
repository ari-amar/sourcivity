import React, { useState } from 'react';
import { Button } from './Button';
import { Input } from './Input';
import { X, Mail, AlertCircle, CheckCircle } from 'lucide-react';

interface EmailValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendEmail: (recipientEmail: string, senderEmail: string) => Promise<void>;
  supplierName: string;
  emailTemplate: string;
}

export const EmailValidationModal = ({
  isOpen,
  onClose,
  onSendEmail,
  supplierName,
  emailTemplate
}: EmailValidationModalProps) => {
  const [recipientEmail, setRecipientEmail] = useState('');
  const [senderEmail] = useState('john.doe@sourcivity.com'); // Fixed sender email from template
  const [isValid, setIsValid] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendStatus, setSendStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Email validation regex
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  React.useEffect(() => {
    const recipientValid = emailRegex.test(recipientEmail);
    setIsValid(recipientValid); // Only validate recipient email
  }, [recipientEmail]);

  const handleSendEmail = async () => {
    if (!isValid) return;

    setIsSending(true);
    setSendStatus('idle');

    try {
      await onSendEmail(recipientEmail, senderEmail);
      setSendStatus('success');
      // Auto-close after 2 seconds on success
      setTimeout(() => {
        onClose();
        setSendStatus('idle');
        setRecipientEmail('');
      }, 2000);
    } catch (error) {
      console.error('Email send failed:', error);
      setSendStatus('error');
    } finally {
      setIsSending(false);
    }
  };

  const handleClose = () => {
    if (!isSending) {
      onClose();
      setSendStatus('idle');
      setRecipientEmail('');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50" 
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 bg-surface border border-input rounded-lg shadow-lg">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Mail size={20} className="text-primary" />
            <h3 className="text-lg font-semibold">Send RFQ Email</h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            disabled={isSending}
            className="p-2"
          >
            <X size={16} />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-3">
              Send RFQ email to <span className="font-medium">{supplierName}</span>
            </p>
          </div>

          {/* Recipient Email - Manual for now, AI search later */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Supplier Email * (Manual for now)
            </label>
            <Input
              type="email"
              placeholder="supplier@company.com"
              value={recipientEmail}
              onChange={(e) => setRecipientEmail(e.target.value)}
              className="w-full"
              disabled={isSending}
            />
            {recipientEmail && !emailRegex.test(recipientEmail) && (
              <p className="text-xs text-destructive mt-1">Please enter a valid email address</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Future: AI will automatically find supplier emails
            </p>
          </div>

          {/* Sender Email - Fixed from template */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Sender Email (From Template)
            </label>
            <Input
              type="email"
              value={senderEmail}
              className="w-full bg-muted"
              disabled={true}
              readOnly
            />
            <p className="text-xs text-muted-foreground mt-1">
              Using John Doe's email from RFQ template
            </p>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Email Preview
            </label>
            <div className="max-h-32 overflow-y-auto bg-muted p-3 rounded text-xs text-muted-foreground">
              {emailTemplate.slice(0, 200)}...
            </div>
          </div>

          {/* Status Messages */}
          {sendStatus === 'success' && (
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <CheckCircle size={16} />
              Email sent successfully!
            </div>
          )}

          {sendStatus === 'error' && (
            <div className="flex items-center gap-2 text-destructive text-sm">
              <AlertCircle size={16} />
              Failed to send email. Please check your AgentMail configuration.
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isSending}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendEmail}
              disabled={!isValid || isSending}
              className="flex-1"
            >
              {isSending ? 'Sending...' : 'Send Email'}
            </Button>
          </div>

        </div>
      </div>
    </div>
  );
};