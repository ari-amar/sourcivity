// RFQ tracking and follow-up types

export type RFQStatus = 
  | 'sent' 
  | 'opened' 
  | 'responded' 
  | 'quote_received' 
  | 'overdue' 
  | 'follow_up_1' 
  | 'follow_up_2' 
  | 'final_notice' 
  | 'non_responsive'
  | 'completed';

export type FollowUpType = 'auto' | 'manual_approval' | 'disabled';

export interface RFQRecord {
  id: string;
  originalQuery: string;
  partDetails: string;
  supplierName: string;
  supplierEmail: string;
  senderEmail: string;
  emailTemplate: string;
  status: RFQStatus;
  sentAt: string;
  lastFollowUpAt?: string;
  followUpCount: number;
  followUpType: FollowUpType;
  responseReceivedAt?: string;
  quoteReceivedAt?: string;
  emailTrackingId?: string; // AgentMail tracking ID
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export interface FollowUpRule {
  id: string;
  name: string;
  triggerDays: number;
  emailTemplate: string;
  isActive: boolean;
  createdAt: string;
}

export interface FollowUpSchedule {
  id: string;
  rfqId: string;
  ruleId: string;
  scheduledFor: string;
  status: 'pending' | 'sent' | 'cancelled';
  sentAt?: string;
  emailId?: string; // AgentMail email ID
  createdAt: string;
}

export interface RFQDashboardStats {
  totalRFQs: number;
  pendingRFQs: number;
  overdueRFQs: number;
  responseRate: number;
  avgResponseTime: number;
  todaysFollowUps: number;
}

export interface FollowUpEmailTemplate {
  subject: string;
  body: string;
  urgencyLevel: 'low' | 'medium' | 'high';
}

// Default follow-up templates
export const DEFAULT_FOLLOW_UP_TEMPLATES: Record<string, FollowUpEmailTemplate> = {
  follow_up_1: {
    subject: "Following up on RFQ - {partName}",
    body: `Dear {supplierName} Team,

I hope this email finds you well. I wanted to follow up on the RFQ we sent on {sentDate} for {partName}.

Could you please confirm if you received our request and provide an estimated timeline for your quote?

We're currently evaluating options and would appreciate your response by {responseDeadline}.

Thank you for your time and consideration.

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com`,
    urgencyLevel: 'low'
  },
  follow_up_2: {
    subject: "Second follow-up - RFQ for {partName}",
    body: `Dear {supplierName} Team,

This is our second follow-up regarding the RFQ for {partName} that we sent on {sentDate}.

We're in the final stages of our sourcing decision and would like to include your quote in our evaluation. 

Could you please respond by {responseDeadline} if you're able to provide a quote for this requirement?

If you're unable to provide a quote at this time, please let us know so we can update our records accordingly.

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com`,
    urgencyLevel: 'medium'
  },
  final_notice: {
    subject: "Final notice - RFQ opportunity for {partName}",
    body: `Dear {supplierName} Team,

This is our final follow-up regarding the RFQ for {partName} sent on {sentDate}.

We'll be finalizing our sourcing decision within the next 48 hours. If you're interested in providing a quote, please respond immediately.

After this period, we'll proceed with alternative suppliers and close this RFQ opportunity.

Thank you for your consideration.

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com`,
    urgencyLevel: 'high'
  }
};

// Follow-up schedule rules (days after initial RFQ)
export const DEFAULT_FOLLOW_UP_RULES = [
  { days: 3, template: 'follow_up_1', name: 'First Follow-up' },
  { days: 7, template: 'follow_up_2', name: 'Second Follow-up' },
  { days: 14, template: 'final_notice', name: 'Final Notice' }
];