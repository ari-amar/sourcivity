import React, { useState } from 'react';
import { Button } from './Button';
import { Badge } from './Badge';
import { X, Mail, Reply, Clock, User, Building } from 'lucide-react';
import { RFQRecord } from '../lib/rfq-types';

interface EmailMessage {
  id: string;
  from: string;
  to: string;
  subject: string;
  body: string;
  timestamp: string;
  type: 'sent' | 'received';
  isRead: boolean;
}

interface ConversationModalProps {
  isOpen: boolean;
  onClose: () => void;
  rfq: RFQRecord | null;
  onReply: (message: string) => void;
}

export const ConversationModal = ({
  isOpen,
  onClose,
  rfq,
  onReply
}: ConversationModalProps) => {
  const [replyMessage, setReplyMessage] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [showReplyBox, setShowReplyBox] = useState(false);

  // Mock conversation data - In production, this would come from your email API
  const mockConversation: EmailMessage[] = rfq ? [
    {
      id: '1',
      from: rfq.senderEmail,
      to: rfq.supplierEmail,
      subject: `RFQ - ${rfq.originalQuery}`,
      body: rfq.emailTemplate,
      timestamp: rfq.sentAt,
      type: 'sent' as const,
      isRead: true
    },
    // Add follow-up messages if they exist
    ...(rfq.followUpCount > 0 ? [{
      id: '2',
      from: rfq.senderEmail,
      to: rfq.supplierEmail,
      subject: `Re: RFQ - ${rfq.originalQuery}`,
      body: `Dear ${rfq.supplierName} Team,\n\nI hope this email finds you well. I wanted to follow up on the RFQ we sent on ${new Date(rfq.sentAt).toLocaleDateString()} for ${rfq.originalQuery}.\n\nCould you please confirm if you received our request and provide an estimated timeline for your quote?\n\nThank you for your time and consideration.\n\nBest regards,\nJohn Doe`,
      timestamp: rfq.lastFollowUpAt || rfq.sentAt,
      type: 'sent' as const,
      isRead: true
    }] : []),
    // Add supplier response if status indicates they responded
    ...(rfq.status === 'responded' || rfq.status === 'quote_received' ? [{
      id: '3',
      from: rfq.supplierEmail,
      to: rfq.senderEmail,
      subject: `Re: RFQ - ${rfq.originalQuery}`,
      body: `Hi John,\n\nThank you for your RFQ for ${rfq.originalQuery}.\n\nWe can provide this component with the following details:\n- Unit Price: $2.85 each\n- Minimum Order Quantity: 100 pieces\n- Lead Time: 2-3 weeks\n- Shipping: FOB our facility\n\nPlease let me know if you need any additional specifications or have questions about our quote.\n\nBest regards,\n${rfq.supplierName} Sales Team`,
      timestamp: rfq.responseReceivedAt || new Date().toISOString(),
      type: 'received' as const,
      isRead: false
    }] : [])
  ] : [];

  const handleSendReply = async () => {
    if (!replyMessage.trim() || !rfq) return;

    setIsReplying(true);
    try {
      await onReply(replyMessage);
      setReplyMessage('');
      setShowReplyBox(false);
    } catch (error) {
      console.error('Failed to send reply:', error);
    } finally {
      setIsReplying(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (!isOpen || !rfq) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative w-full max-w-4xl mx-4 bg-surface border border-input rounded-lg shadow-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded">
              <Mail size={20} className="text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">Conversation</h3>
              <p className="text-sm text-muted-foreground">
                {rfq.originalQuery} • {rfq.supplierName}
              </p>
            </div>
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

        {/* Conversation Thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {mockConversation.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Mail size={48} className="mx-auto mb-4 opacity-50" />
              <p>No conversation found</p>
            </div>
          ) : (
            mockConversation.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-2xl ${message.type === 'sent' ? 'order-2' : 'order-1'}`}>
                  {/* Message header */}
                  <div className={`flex items-center gap-2 mb-2 ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex items-center gap-2 ${message.type === 'sent' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`p-1 rounded ${message.type === 'sent' ? 'bg-blue-100 dark:bg-blue-900' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        {message.type === 'sent' ? <User size={12} /> : <Building size={12} />}
                      </div>
                      <span className="text-sm font-medium">
                        {message.type === 'sent' ? 'You' : rfq.supplierName}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                  </div>
                  
                  {/* Message bubble */}
                  <div
                    className={`p-4 rounded-lg border ${
                      message.type === 'sent'
                        ? 'bg-primary text-primary-foreground ml-8'
                        : 'bg-muted mr-8'
                    }`}
                  >
                    <div className="text-sm font-medium mb-2">{message.subject}</div>
                    <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">
                      {message.body}
                    </pre>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Reply Section */}
        <div className="border-t border-border p-4">
          {!showReplyBox ? (
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setShowReplyBox(true)}
                className="flex items-center gap-2"
              >
                <Reply size={16} />
                Reply
              </Button>
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock size={12} />
                Status: {rfq.status.replace('_', ' ')}
              </Badge>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-muted-foreground">
                Reply to <strong>{rfq.supplierName}</strong>
              </div>
              <textarea
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder="Type your reply..."
                className="w-full h-32 p-3 border border-input rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleSendReply}
                  disabled={!replyMessage.trim() || isReplying}
                  className="flex items-center gap-2"
                >
                  {isReplying ? (
                    <>
                      <Clock className="w-4 h-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Reply size={16} />
                      Send Reply
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowReplyBox(false);
                    setReplyMessage('');
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};