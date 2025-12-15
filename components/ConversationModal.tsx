import React, { useState, useRef } from 'react';
import { Button } from './Button';
import { Badge } from './Badge';
import { X, Mail, Reply, Clock, User, Building, Sparkles } from 'lucide-react';
import { RFQRecord, RFQStatus } from '../lib/rfq-types';

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
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const getStatusBadgeVariant = (status: RFQStatus): 'default' | 'destructive' | 'outline' | 'secondary' | 'success' | 'warning' | 'purple' | 'orange' | 'gray' | 'darkGreen' => {
    switch (status) {
      case 'sent':
      case 'opened':
        return 'outline'; // Blue - neutral, waiting
      case 'follow_up_1':
      case 'follow_up_2':
        return 'warning'; // Orange/Yellow - needs attention
      case 'overdue':
      case 'final_notice':
        return 'destructive'; // Red - urgent
      case 'responded':
        return 'success'; // Green - positive response
      case 'quote_received':
        return 'darkGreen'; // Dark green - successful quote
      case 'completed':
        return 'darkGreen'; // Dark green - completed successfully
      case 'non_responsive':
        return 'gray'; // Gray - inactive
      default:
        return 'outline';
    }
  };

  // Mock conversation data - In production, this would come from your email API
  const mockConversation: EmailMessage[] = rfq ? (
    rfq.supplierName === 'Pfeiffer Vacuum' ? [
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
      {
        id: '2',
        from: rfq.supplierEmail,
        to: rfq.senderEmail,
        subject: `Re: RFQ - ${rfq.originalQuery}`,
        body: `Dear John,\n\nThank you for your inquiry regarding vacuum pumps. We have reviewed your requirements and can offer the following:\n\nPfeiffer HiPace 80 Turbomolecular Pump:\n- Pumping speed: 67 l/s (N₂)\n- Ultimate vacuum: < 7.5 × 10⁻⁸ mbar\n- Price: $4,850 per unit\n- MOQ: 2 units\n- Lead time: 6-8 weeks\n\nThis is our standard pricing. Please let me know if you need any technical specifications.\n\nBest regards,\nMarkus Weber\nPfeiffer Vacuum Sales Team`,
        timestamp: new Date(new Date(rfq.sentAt).getTime() + 2 * 24 * 60 * 60 * 1000).toISOString(),
        type: 'received' as const,
        isRead: true
      },
      {
        id: '3',
        from: rfq.senderEmail,
        to: rfq.supplierEmail,
        subject: `Re: RFQ - ${rfq.originalQuery}`,
        body: `Hi Markus,\n\nThank you for the quote. The HiPace 80 looks good, but I was hoping for a better price given our volume needs. We're planning to order 10 units initially, with potential for 20+ units over the next quarter.\n\nCould you provide pricing for:\n- 10 units\n- 20+ units (volume discount)\n\nAlso, is there any flexibility on the lead time? We're hoping to receive the first batch within 4 weeks.\n\nBest regards,\nJohn Doe`,
        timestamp: new Date(new Date(rfq.sentAt).getTime() + 2.5 * 24 * 60 * 60 * 1000).toISOString(),
        type: 'sent' as const,
        isRead: true
      },
      {
        id: '4',
        from: rfq.supplierEmail,
        to: rfq.senderEmail,
        subject: `Re: RFQ - ${rfq.originalQuery}`,
        body: `Hi John,\n\nThank you for clarifying your volume requirements. I've reviewed this with our sales manager and can offer the following revised pricing:\n\n10 units: $4,500 per unit (7% discount)\n20+ units: $4,250 per unit (12% discount)\n\nRegarding lead time, 4 weeks is challenging for our standard production schedule. However, if you can commit to the 10-unit order now, we may be able to expedite and deliver in 5 weeks. This would require a 50% deposit upfront.\n\nLet me know your thoughts.\n\nBest regards,\nMarkus Weber`,
        timestamp: new Date(new Date(rfq.sentAt).getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
        type: 'received' as const,
        isRead: true
      },
      {
        id: '5',
        from: rfq.senderEmail,
        to: rfq.supplierEmail,
        subject: `Re: RFQ - ${rfq.originalQuery}`,
        body: `Hi Markus,\n\nThanks for the volume pricing - that's more in line with our budget. The 12% discount for 20+ units is attractive.\n\nI discussed with our finance team, and we can commit to:\n- Initial order: 10 units at $4,500/unit\n- Follow-up order: 10 units at $4,250/unit (within 90 days)\n\nFor the initial order, we can accept the 5-week lead time and provide a 50% deposit. However, we'd need:\n1. Guaranteed 5-week delivery\n2. Standard payment terms (Net 30) for the remaining 50%\n3. Technical support for installation\n\nCan you confirm these terms?\n\nBest regards,\nJohn Doe`,
        timestamp: new Date(new Date(rfq.sentAt).getTime() + 3.5 * 24 * 60 * 60 * 1000).toISOString(),
        type: 'sent' as const,
        isRead: true
      },
      {
        id: '6',
        from: rfq.supplierEmail,
        to: rfq.senderEmail,
        subject: `Re: RFQ - ${rfq.originalQuery}`,
        body: `Hi John,\n\nExcellent! I'm pleased we could reach an agreement. I can confirm:\n\n✓ 10 units at $4,500/unit with 5-week guaranteed delivery\n✓ 50% deposit, balance on Net 30 terms\n✓ Technical support for installation (remote + 1 on-site visit)\n✓ Future order: 10 units at $4,250/unit (valid for 90 days)\n\nTotal for initial order: $45,000\nDeposit required: $22,500\n\nI'll prepare the formal quotation and order agreement today. Once you approve and send the deposit, we'll initiate production immediately.\n\nLooking forward to working with you!\n\nBest regards,\nMarkus Weber\nPfeiffer Vacuum Sales Team`,
        timestamp: new Date(new Date(rfq.sentAt).getTime() + 4 * 24 * 60 * 60 * 1000).toISOString(),
        type: 'received' as const,
        isRead: false
      }
    ] : [
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
    ]
  ) : [];

  const handleGenerateAIResponse = async () => {
    if (!rfq) return;

    setIsGeneratingAI(true);
    setReplyMessage('');

    // Simulate AI typing effect
    const aiResponse = `Hi ${rfq.supplierName} Team,\n\nThank you for your quote on ${rfq.originalQuery}. I appreciate the detailed specifications and pricing information.\n\nBefore we proceed, I have a few questions:\n\n1. What are the available warranty terms for this component?\n2. Do you offer technical support for installation and integration?\n3. Can you provide references from similar clients in our industry?\n\nI look forward to your response.\n\nBest regards,\nJohn Doe`;

    let currentText = '';
    const words = aiResponse.split(' ');

    for (let i = 0; i < words.length; i++) {
      currentText += (i > 0 ? ' ' : '') + words[i];
      setReplyMessage(currentText);

      // Random delay between 30-80ms for natural typing effect
      await new Promise(resolve => setTimeout(resolve, Math.random() * 50 + 30));
    }

    setIsGeneratingAI(false);
  };

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 md:p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full h-full md:h-auto md:max-w-4xl md:mx-4 bg-surface md:border border-input md:rounded-lg shadow-lg md:max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-3 md:p-4 border-b border-border">
          <div className="flex items-center gap-2 md:gap-3 min-w-0">
            <div className="p-1.5 md:p-2 bg-blue-100 dark:bg-blue-900 rounded flex-shrink-0">
              <Mail size={16} className="md:w-5 md:h-5 text-blue-600" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-base md:text-lg font-semibold truncate">Conversation</h3>
              <p className="text-xs md:text-sm text-muted-foreground truncate">
                {rfq.originalQuery} • {rfq.supplierName}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="p-2 flex-shrink-0"
          >
            <X size={16} />
          </Button>
        </div>

        {/* Conversation Thread */}
        <div className="flex-1 overflow-y-auto p-3 md:p-6 space-y-3 md:space-y-4 bg-gray-50">
          {mockConversation.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Mail size={48} className="mx-auto mb-4 opacity-50" />
              <p>No conversation found</p>
            </div>
          ) : (
            mockConversation.map((message) => (
              <div
                key={message.id}
                className={`flex gap-2 md:gap-3 ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-2 md:gap-3 max-w-[85%] md:max-w-[75%] ${message.type === 'sent' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`flex-shrink-0 w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center ${
                    message.type === 'sent'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-300 text-gray-700'
                  }`}>
                    {message.type === 'sent' ? <User size={14} className="md:w-4 md:h-4" /> : <Building size={14} className="md:w-4 md:h-4" />}
                  </div>

                  {/* Message bubble */}
                  <div className="flex-1 min-w-0">
                    <div className={`flex items-baseline gap-1.5 md:gap-2 mb-1 ${message.type === 'sent' ? 'justify-end' : 'justify-start'}`}>
                      <span className="text-xs md:text-sm font-medium truncate">
                        {message.type === 'sent' ? 'You' : rfq.supplierName}
                      </span>
                      <span className="text-xs text-muted-foreground flex-shrink-0">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                    <div
                      className={`p-2.5 md:p-3 rounded-2xl ${
                        message.type === 'sent'
                          ? 'bg-blue-500 text-white rounded-tr-sm'
                          : 'bg-white border border-gray-200 rounded-tl-sm'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1.5 md:mb-2 opacity-80 truncate">{message.subject}</div>
                      <pre className="text-xs md:text-sm whitespace-pre-wrap font-sans leading-relaxed">
                        {message.body}
                      </pre>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Reply Section */}
        <div className="border-t border-border p-3 md:p-4">
          {!showReplyBox ? (
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
              <Button
                onClick={() => setShowReplyBox(true)}
                className="flex items-center gap-2 w-full sm:w-auto"
                size="sm"
              >
                <Reply size={16} />
                Reply
              </Button>
              <Badge variant={getStatusBadgeVariant(rfq.status)} className="flex items-center gap-1 text-xs">
                <Clock size={12} />
                <span className="truncate">Status: {rfq.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</span>
              </Badge>
            </div>
          ) : (
            <div className="space-y-2 md:space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="text-xs md:text-sm text-muted-foreground">
                  Reply to <strong>{rfq.supplierName}</strong>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleGenerateAIResponse}
                  disabled={isGeneratingAI}
                  className="flex items-center gap-2 text-xs md:text-sm w-full sm:w-auto"
                >
                  <Sparkles size={14} className={isGeneratingAI ? 'animate-pulse' : ''} />
                  {isGeneratingAI ? 'Generating...' : 'Generate AI Response'}
                </Button>
              </div>
              <textarea
                ref={textareaRef}
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder="Type your reply or generate an AI response..."
                className="w-full h-48 md:h-64 p-2.5 md:p-3 text-sm border border-input rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                disabled={isGeneratingAI}
              />
              <div className="flex gap-2">
                <Button
                  onClick={handleSendReply}
                  disabled={!replyMessage.trim() || isReplying || isGeneratingAI}
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
                  disabled={isGeneratingAI}
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