import { NextRequest, NextResponse } from 'next/server';
import { RFQRecord } from '../../../../lib/rfq-types';

// Mock database - In production, this would be a real database
// This should be the same reference as in other API routes
let mockRFQDatabase: RFQRecord[] = [];

interface AgentMailWebhookPayload {
  event_type: 'email_received' | 'email_opened' | 'email_clicked' | 'email_replied';
  email_id: string;
  from: string;
  to: string;
  subject: string;
  body?: string;
  timestamp: string;
  metadata?: {
    original_email_id?: string;
    thread_id?: string;
  };
}

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Received AgentMail webhook`);

  try {
    // Verify webhook authenticity (AgentMail should provide signature verification)
    const signature = request.headers.get('x-agentmail-signature');
    const webhookSecret = process.env.AGENTMAIL_WEBHOOK_SECRET;
    
    if (webhookSecret && signature) {
      // TODO: Implement proper signature verification
      // const expectedSignature = crypto.createHmac('sha256', webhookSecret)
      //   .update(body)
      //   .digest('hex');
      // if (signature !== expectedSignature) {
      //   return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
      // }
    }

    const payload: AgentMailWebhookPayload = await request.json();
    console.log(`[${new Date().toISOString()}] Processing webhook event:`, payload.event_type);

    // Handle different webhook events
    switch (payload.event_type) {
      case 'email_received':
      case 'email_replied':
        await handleSupplierResponse(payload);
        break;
      
      case 'email_opened':
        await handleEmailOpened(payload);
        break;
      
      case 'email_clicked':
        await handleEmailClicked(payload);
        break;
      
      default:
        console.log(`Unknown event type: ${payload.event_type}`);
    }

    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Webhook processed in ${totalTime}ms`);

    return NextResponse.json({ 
      success: true, 
      message: 'Webhook processed successfully' 
    });

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error(`[${new Date().toISOString()}] Webhook error after ${totalTime}ms:`, errorMessage);
    
    return NextResponse.json(
      { error: `Webhook processing failed: ${errorMessage}` },
      { status: 500 }
    );
  }
}

async function handleSupplierResponse(payload: AgentMailWebhookPayload) {
  console.log(`[${new Date().toISOString()}] Supplier response received from: ${payload.from}`);

  // Find RFQ by supplier email
  const rfqIndex = mockRFQDatabase.findIndex(rfq => 
    rfq.supplierEmail.toLowerCase() === payload.from.toLowerCase() &&
    !['responded', 'quote_received', 'completed', 'non_responsive'].includes(rfq.status)
  );

  if (rfqIndex === -1) {
    console.log(`No active RFQ found for supplier: ${payload.from}`);
    return;
  }

  const rfq = mockRFQDatabase[rfqIndex];
  const now = new Date().toISOString();

  // Determine response type based on email content
  let newStatus: RFQRecord['status'] = 'responded';
  
  if (payload.body) {
    const bodyLower = payload.body.toLowerCase();
    // Look for quote-related keywords
    if (bodyLower.includes('quote') || bodyLower.includes('price') || bodyLower.includes('$') || 
        bodyLower.includes('cost') || bodyLower.includes('pricing')) {
      newStatus = 'quote_received';
    }
  }

  // Update RFQ record - STOP FOLLOW-UPS by changing status
  const updatedRFQ: RFQRecord = {
    ...rfq,
    status: newStatus,
    responseReceivedAt: now,
    ...(newStatus === 'quote_received' && { quoteReceivedAt: now }),
    notes: rfq.notes + `\n[${now}] Supplier response received via email`,
    updatedAt: now
  };

  mockRFQDatabase[rfqIndex] = updatedRFQ;

  console.log(`[${new Date().toISOString()}] RFQ ${rfq.id} updated to status: ${newStatus}. Follow-ups STOPPED.`);

  // TODO: In production, you might want to:
  // 1. Send notification to procurement team
  // 2. Parse quote details from email
  // 3. Update CRM/ERP systems
  // 4. Trigger quote evaluation workflow
}

async function handleEmailOpened(payload: AgentMailWebhookPayload) {
  console.log(`[${new Date().toISOString()}] Email opened by: ${payload.from}`);

  // Find RFQ and update status to 'opened' if currently 'sent'
  const rfqIndex = mockRFQDatabase.findIndex(rfq => 
    rfq.supplierEmail.toLowerCase() === payload.from.toLowerCase() &&
    rfq.status === 'sent'
  );

  if (rfqIndex !== -1) {
    mockRFQDatabase[rfqIndex] = {
      ...mockRFQDatabase[rfqIndex],
      status: 'opened',
      updatedAt: new Date().toISOString()
    };
    
    console.log(`[${new Date().toISOString()}] RFQ ${mockRFQDatabase[rfqIndex].id} status updated to 'opened'`);
  }
}

async function handleEmailClicked(payload: AgentMailWebhookPayload) {
  console.log(`[${new Date().toISOString()}] Email link clicked by: ${payload.from}`);
  
  // Track engagement but don't change follow-up schedule
  // This shows supplier is engaged but hasn't responded yet
}

// GET endpoint to manually trigger webhook processing (for testing)
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const testEvent = searchParams.get('test');
  
  if (testEvent === 'response') {
    // Simulate a supplier response for testing
    const mockPayload: AgentMailWebhookPayload = {
      event_type: 'email_replied',
      email_id: 'test_email_123',
      from: 'supplier@example.com',
      to: 'john.doe@sourcivity.com',
      subject: 'Re: RFQ for ceramic capacitor 10uF',
      body: 'Thank you for your RFQ. We can provide this part at $2.50 each for quantities of 100+. Quote attached.',
      timestamp: new Date().toISOString()
    };

    await handleSupplierResponse(mockPayload);
    
    return NextResponse.json({
      success: true,
      message: 'Test supplier response processed'
    });
  }

  return NextResponse.json({
    message: 'AgentMail webhook endpoint',
    supportedEvents: ['email_received', 'email_replied', 'email_opened', 'email_clicked'],
    testUrl: '/api/webhooks/agentmail?test=response'
  });
}