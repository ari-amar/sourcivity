import { NextRequest, NextResponse } from 'next/server';
import { DEFAULT_FOLLOW_UP_TEMPLATES, DEFAULT_FOLLOW_UP_RULES } from '../../../../lib/rfq-types';

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Processing follow-up request`);

  try {
    const { rfqId, followUpType = 'follow_up_1' } = await request.json();

    if (!rfqId) {
      return NextResponse.json(
        { error: 'RFQ ID is required' },
        { status: 400 }
      );
    }

    // Get the follow-up template
    const template = DEFAULT_FOLLOW_UP_TEMPLATES[followUpType];
    if (!template) {
      return NextResponse.json(
        { error: 'Invalid follow-up type' },
        { status: 400 }
      );
    }

    console.log(`[${new Date().toISOString()}] Preparing ${followUpType} follow-up for RFQ: ${rfqId}`);

    // In production, you would:
    // 1. Fetch the original RFQ record from database
    // 2. Generate personalized email content
    // 3. Send via AgentMail
    // 4. Update RFQ status and follow-up count
    // 5. Schedule next follow-up if needed

    // For now, simulate the process
    const simulatedEmailContent = template.body
      .replace('{supplierName}', 'PLACEHOLDER_SUPPLIER')
      .replace('{partName}', 'PLACEHOLDER_PART')
      .replace('{sentDate}', 'PLACEHOLDER_DATE')
      .replace('{responseDeadline}', 'PLACEHOLDER_DEADLINE');

    // Check if AgentMail API key is configured
    const agentMailApiKey = process.env.AGENTMAIL_API_KEY;
    
    if (!agentMailApiKey) {
      console.log('AgentMail API key not configured - simulating follow-up send');
      
      // Return success with simulation message
      return NextResponse.json({
        success: true,
        message: 'Follow-up email prepared. Configure AGENTMAIL_API_KEY to enable actual sending.',
        mockSend: true,
        emailContent: simulatedEmailContent,
        template: template
      });
    }

    // TODO: Implement actual AgentMail sending when API key is available
    // const agentMail = new AgentMail(agentMailApiKey);
    // const emailResult = await agentMail.emails.send({
    //   to: rfq.supplierEmail,
    //   from: rfq.senderEmail,
    //   subject: template.subject,
    //   body: simulatedEmailContent
    // });

    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Follow-up processed in ${totalTime}ms`);

    return NextResponse.json({
      success: true,
      message: 'Follow-up email sent successfully',
      followUpType,
      urgencyLevel: template.urgencyLevel
    });

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error(`[${new Date().toISOString()}] Error in follow-up endpoint after ${totalTime}ms:`, errorMessage);
    
    return NextResponse.json(
      { error: `Failed to send follow-up: ${errorMessage}` },
      { status: 500 }
    );
  }
}

// Get follow-up rules and templates
export async function GET(request: NextRequest) {
  console.log(`[${new Date().toISOString()}] Fetching follow-up configuration`);

  try {
    return NextResponse.json({
      templates: DEFAULT_FOLLOW_UP_TEMPLATES,
      rules: DEFAULT_FOLLOW_UP_RULES
    });

  } catch (error) {
    console.error('Error fetching follow-up configuration:', error);
    return NextResponse.json(
      { error: 'Failed to fetch follow-up configuration' },
      { status: 500 }
    );
  }
}