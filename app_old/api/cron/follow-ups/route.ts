import { NextRequest, NextResponse } from 'next/server';
import { AgentMailClient } from 'agentmail';
import { RFQRecord, DEFAULT_FOLLOW_UP_TEMPLATES, DEFAULT_FOLLOW_UP_RULES } from '../../../../lib/rfq-types';

// Validate API key helper
const validateApiKey = (key: string | undefined, serviceName: string): string => {
  if (!key) {
    throw new Error(`${serviceName} API key not configured`);
  }
  if (key.trim() === '' || key.includes('your-api-key') || key.includes('placeholder') || key === 'undefined') {
    throw new Error(`${serviceName} API key appears to be a placeholder value. Please check your configuration.`);
  }
  return key;
};

// Mock database - In production, this would be a real database
let mockRFQDatabase: RFQRecord[] = [];

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Running automated follow-up cron job`);

  try {
    // Verify this is a legitimate cron request (in production, add proper authentication)
    const authHeader = request.headers.get('authorization');
    if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
      console.log('Unauthorized cron request');
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Check if AgentMail API key is configured
    const agentMailApiKey = process.env.AGENTMAIL_API_KEY;
    if (!agentMailApiKey) {
      console.log('AgentMail API key not configured - skipping automatic follow-ups');
      return NextResponse.json({
        success: true,
        message: 'AgentMail API key not configured. Automatic follow-ups disabled.',
        processed: 0
      });
    }

    // Initialize AgentMail client
    const agentMail = new AgentMailClient({ apiKey: validateApiKey(agentMailApiKey, 'AgentMail') });

    const now = new Date();
    let processedCount = 0;
    const results = [];

    // Find RFQs that need follow-ups
    for (const rfq of mockRFQDatabase) {
      // Only process RFQs with auto follow-up enabled
      if (rfq.followUpType !== 'auto') continue;

      // Skip if already completed, responded, or non-responsive (STOP FOLLOW-UPS)
      if (['completed', 'non_responsive', 'quote_received', 'responded'].includes(rfq.status)) {
        console.log(`[${new Date().toISOString()}] Skipping RFQ ${rfq.id} - supplier has responded (${rfq.status})`);
        continue;
      }

      const sentDate = new Date(rfq.sentAt);
      const daysSinceSent = Math.floor((now.getTime() - sentDate.getTime()) / (1000 * 60 * 60 * 24));

      // Determine which follow-up to send based on days elapsed
      let followUpToSend: string | null = null;
      let followUpRule = null;

      for (const rule of DEFAULT_FOLLOW_UP_RULES) {
        if (daysSinceSent >= rule.days && rfq.followUpCount < DEFAULT_FOLLOW_UP_RULES.indexOf(rule) + 1) {
          followUpToSend = rule.template;
          followUpRule = rule;
          break;
        }
      }

      if (!followUpToSend || !followUpRule) continue;

      // Check if we've already sent this follow-up today
      if (rfq.lastFollowUpAt) {
        const lastFollowUpDate = new Date(rfq.lastFollowUpAt);
        const hoursSinceLastFollowUp = (now.getTime() - lastFollowUpDate.getTime()) / (1000 * 60 * 60);
        if (hoursSinceLastFollowUp < 24) continue; // Don't send multiple follow-ups in same day
      }

      try {
        // Get follow-up template
        const template = DEFAULT_FOLLOW_UP_TEMPLATES[followUpToSend];
        if (!template) continue;

        // Personalize email content
        const sentDateStr = sentDate.toLocaleDateString();
        const deadlineDate = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toLocaleDateString();
        
        const personalizedSubject = template.subject
          .replace('{partName}', rfq.originalQuery)
          .replace('{supplierName}', rfq.supplierName);

        const personalizedBody = template.body
          .replace('{supplierName}', rfq.supplierName)
          .replace('{partName}', rfq.originalQuery)
          .replace('{sentDate}', sentDateStr)
          .replace('{responseDeadline}', deadlineDate);

        // Send follow-up via AgentMail
        // Note: This requires an inbox ID. In production, you'd get this from your inbox setup.
        const emailResult = await agentMail.inboxes.messages.send('default_inbox_id', {
          to: [rfq.supplierEmail],
          subject: personalizedSubject,
          text: personalizedBody
        });

        // Update RFQ record
        const updatedRFQ = {
          ...rfq,
          followUpCount: rfq.followUpCount + 1,
          lastFollowUpAt: now.toISOString(),
          status: followUpToSend as any, // Update status to follow_up_1, follow_up_2, etc.
          emailTrackingId: emailResult.messageId || undefined,
          updatedAt: now.toISOString()
        };

        // Update in mock database
        const rfqIndex = mockRFQDatabase.findIndex(r => r.id === rfq.id);
        if (rfqIndex !== -1) {
          mockRFQDatabase[rfqIndex] = updatedRFQ;
        }

        processedCount++;
        results.push({
          rfqId: rfq.id,
          supplier: rfq.supplierName,
          followUpType: followUpToSend,
          emailId: emailResult.messageId,
          success: true
        });

        console.log(`[${new Date().toISOString()}] Sent ${followUpToSend} to ${rfq.supplierName} for RFQ ${rfq.id}`);

      } catch (error) {
        console.error(`Failed to send follow-up for RFQ ${rfq.id}:`, error);
        results.push({
          rfqId: rfq.id,
          supplier: rfq.supplierName,
          followUpType: followUpToSend,
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    // Mark overdue RFQs (those that have passed final notice)
    for (const rfq of mockRFQDatabase) {
      if (rfq.followUpType !== 'auto') continue;
      if (['completed', 'non_responsive', 'quote_received', 'responded'].includes(rfq.status)) continue;

      const sentDate = new Date(rfq.sentAt);
      const daysSinceSent = Math.floor((now.getTime() - sentDate.getTime()) / (1000 * 60 * 60 * 24));

      // Mark as non-responsive after 21 days with no response
      if (daysSinceSent >= 21 && rfq.followUpCount >= 3) {
        const rfqIndex = mockRFQDatabase.findIndex(r => r.id === rfq.id);
        if (rfqIndex !== -1) {
          mockRFQDatabase[rfqIndex] = {
            ...rfq,
            status: 'non_responsive',
            updatedAt: now.toISOString()
          };
          console.log(`[${new Date().toISOString()}] Marked RFQ ${rfq.id} as non-responsive`);
        }
      }
    }

    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Cron job completed in ${totalTime}ms. Processed ${processedCount} follow-ups.`);

    return NextResponse.json({
      success: true,
      message: `Processed ${processedCount} automatic follow-ups`,
      processed: processedCount,
      results: results
    });

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error(`[${new Date().toISOString()}] Error in follow-up cron job after ${totalTime}ms:`, errorMessage);
    
    return NextResponse.json(
      { error: `Follow-up cron job failed: ${errorMessage}` },
      { status: 500 }
    );
  }
}