import React, { useState } from 'react';
import { Button } from './Button';
import { Badge } from './Badge';
import { X, Clock, AlertTriangle, Send, Eye } from 'lucide-react';
import { RFQRecord, FollowUpEmailTemplate, DEFAULT_FOLLOW_UP_TEMPLATES } from '../lib/rfq-types';

interface FollowUpApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: (rfqId: string, customMessage?: string) => Promise<void>;
  onReject: (rfqId: string, reason: string) => void;
  rfq: RFQRecord | null;
  followUpType: keyof typeof DEFAULT_FOLLOW_UP_TEMPLATES;
}

export const FollowUpApprovalModal = ({
  isOpen,
  onClose,
  onApprove,
  onReject,
  rfq,
  followUpType
}: FollowUpApprovalModalProps) => {
  const [customMessage, setCustomMessage] = useState('');
  const [useCustomMessage, setUseCustomMessage] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showRejectionForm, setShowRejectionForm] = useState(false);

  const template = DEFAULT_FOLLOW_UP_TEMPLATES[followUpType];

  const handleApprove = async () => {
    if (!rfq) return;

    setIsProcessing(true);
    try {
      await onApprove(rfq.id, useCustomMessage ? customMessage : undefined);
      onClose();
      setCustomMessage('');
      setUseCustomMessage(false);
    } catch (error) {
      console.error('Failed to approve follow-up:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = () => {
    if (!rfq || !rejectionReason.trim()) return;

    onReject(rfq.id, rejectionReason);
    onClose();
    setRejectionReason('');
    setShowRejectionForm(false);
  };

  const handleClose = () => {
    if (!isProcessing) {
      onClose();
      setCustomMessage('');
      setUseCustomMessage(false);
      setRejectionReason('');
      setShowRejectionForm(false);
    }
  };

  const getDaysOverdue = () => {
    if (!rfq) return 0;
    const sentDate = new Date(rfq.sentAt);
    const now = new Date();
    const diffTime = now.getTime() - sentDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getPersonalizedTemplate = () => {
    if (!rfq || !template) return '';
    
    const sentDate = new Date(rfq.sentAt).toLocaleDateString();
    const deadlineDate = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toLocaleDateString();
    
    return template.body
      .replace('{supplierName}', rfq.supplierName)
      .replace('{partName}', rfq.originalQuery)
      .replace('{sentDate}', sentDate)
      .replace('{responseDeadline}', deadlineDate);
  };

  if (!isOpen || !rfq || !template) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />
      
      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 bg-surface border border-input rounded-lg shadow-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded">
              <Clock size={20} className="text-orange-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Approve Follow-up Email</h3>
              <p className="text-sm text-muted-foreground">
                Review and approve automated follow-up
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            disabled={isProcessing}
            className="p-2"
          >
            <X size={16} />
          </Button>
        </div>

        <div className="p-4 space-y-4">
          {/* RFQ Info */}
          <div className="bg-muted p-3 rounded-lg">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h4 className="font-medium">{rfq.originalQuery}</h4>
                <p className="text-sm text-muted-foreground">To: {rfq.supplierName}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  {getDaysOverdue()} days ago
                </Badge>
                <Badge 
                  variant={template.urgencyLevel === 'high' ? 'destructive' : 
                          template.urgencyLevel === 'medium' ? 'secondary' : 'outline'}
                >
                  {template.urgencyLevel} priority
                </Badge>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Follow-up #{rfq.followUpCount + 1} • {followUpType.replace('_', ' ')}
            </p>
          </div>

          {/* Email Preview */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Eye size={16} />
              <label className="text-sm font-medium">Email Preview</label>
            </div>
            
            <div className="border border-input rounded-lg">
              <div className="bg-muted p-3 border-b border-border">
                <div className="text-sm">
                  <strong>Subject:</strong> {template.subject.replace('{partName}', rfq.originalQuery)}
                </div>
                <div className="text-sm text-muted-foreground mt-1">
                  <strong>To:</strong> {rfq.supplierEmail} | <strong>From:</strong> {rfq.senderEmail}
                </div>
              </div>
              <div className="p-3">
                {useCustomMessage ? (
                  <textarea
                    value={customMessage}
                    onChange={(e) => setCustomMessage(e.target.value)}
                    className="w-full h-40 p-2 border border-input rounded text-sm font-mono"
                    placeholder="Enter your custom message..."
                  />
                ) : (
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {getPersonalizedTemplate()}
                  </pre>
                )}
              </div>
            </div>
          </div>

          {/* Custom Message Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="useCustomMessage"
              checked={useCustomMessage}
              onChange={(e) => setUseCustomMessage(e.target.checked)}
              disabled={isProcessing}
            />
            <label htmlFor="useCustomMessage" className="text-sm">
              Use custom message instead of template
            </label>
          </div>

          {/* Rejection Form */}
          {showRejectionForm && (
            <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-800">
              <h4 className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
                Reject Follow-up
              </h4>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Reason for rejecting this follow-up..."
                className="w-full h-20 p-2 border border-input rounded text-sm"
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            {!showRejectionForm ? (
              <>
                <Button
                  onClick={() => setShowRejectionForm(true)}
                  variant="outline"
                  disabled={isProcessing}
                  className="flex items-center gap-2"
                >
                  <X size={16} />
                  Reject
                </Button>
                <Button
                  onClick={handleApprove}
                  disabled={isProcessing || (useCustomMessage && !customMessage.trim())}
                  className="flex-1 flex items-center gap-2"
                >
                  {isProcessing ? (
                    <>
                      <Clock className="w-4 h-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      Approve & Send Follow-up
                    </>
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button
                  onClick={() => setShowRejectionForm(false)}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleReject}
                  variant="destructive"
                  disabled={!rejectionReason.trim()}
                  className="flex-1 flex items-center gap-2"
                >
                  <AlertTriangle size={16} />
                  Confirm Rejection
                </Button>
              </>
            )}
          </div>

          {/* Warning */}
          <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
            <strong>Note:</strong> This follow-up will be sent immediately upon approval. 
            The supplier will receive this email and the RFQ status will be updated automatically.
          </div>
        </div>
      </div>
    </div>
  );
};