import { NextRequest, NextResponse } from 'next/server';
import { AgentMailClient } from 'agentmail';

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

export async function POST(request: NextRequest) {
  const requestStartTime = Date.now();
  console.log(`[${new Date().toISOString()}] Received AgentMail send request`);

  try {
    const { recipientEmail, senderEmail, emailTemplate, supplierName, subject } = await request.json();

    // Validate required fields
    if (!recipientEmail || !senderEmail || !emailTemplate) {
      return NextResponse.json(
        { error: 'Missing required fields: recipientEmail, senderEmail, emailTemplate' },
        { status: 400 }
      );
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(recipientEmail) || !emailRegex.test(senderEmail)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    console.log(`[${new Date().toISOString()}] Validated input for RFQ email send`);

    // Check if AgentMail API key is configured
    const agentMailApiKey = process.env.AGENTMAIL_API_KEY;
    if (!agentMailApiKey) {
      console.log('AgentMail API key not configured - showing validation popup only');
      
      // Return success with a message indicating email validation only
      return NextResponse.json({
        success: true,
        message: 'Email validation successful. Configure AGENTMAIL_API_KEY to enable actual sending.',
        mockSend: true,
        recipientEmail,
        senderEmail,
        supplierName: supplierName || 'Unknown Supplier'
      });
    }

    // Initialize AgentMail client
    const agentMail = new AgentMailClient({ apiKey: validateApiKey(agentMailApiKey, 'AgentMail') });

    // Extract subject from template if not provided
    let emailSubject = subject;
    if (!emailSubject) {
      const subjectMatch = emailTemplate.match(/Subject:\s*(.+)/i);
      emailSubject = subjectMatch ? subjectMatch[1].trim() : `RFQ - ${supplierName || 'Parts Request'}`;
    }

    // Extract email body (remove subject line if present)
    let emailBody = emailTemplate;
    if (emailTemplate.includes('Subject:')) {
      const bodyStartIndex = emailTemplate.indexOf('\n', emailTemplate.indexOf('Subject:'));
      if (bodyStartIndex !== -1) {
        emailBody = emailTemplate.substring(bodyStartIndex + 1).trim();
      }
    }

    // Send email via AgentMail
    // Note: This requires an inbox ID. In production, you'd get this from your inbox setup.
    const emailResult = await agentMail.inboxes.messages.send('default_inbox_id', {
      to: [recipientEmail],
      subject: emailSubject,
      text: emailBody,
      // You can add additional AgentMail options here as needed
    });

    const totalTime = Date.now() - requestStartTime;
    console.log(`[${new Date().toISOString()}] Successfully sent RFQ email via AgentMail in ${totalTime}ms`);

    return NextResponse.json({
      success: true,
      message: 'RFQ email sent successfully via AgentMail',
      emailId: emailResult.messageId || 'unknown',
      recipientEmail,
      senderEmail,
      supplierName: supplierName || 'Unknown Supplier'
    });

  } catch (error) {
    const totalTime = Date.now() - requestStartTime;
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
    console.error(`[${new Date().toISOString()}] Error in AgentMail send endpoint after ${totalTime}ms:`, errorMessage);
    
    // Handle rate limiting
    if (error instanceof Error && error.message.includes('rate limit')) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again later.' },
        { status: 429 }
      );
    }

    // Handle AgentMail specific errors
    if (error instanceof Error && error.message.includes('AgentMail')) {
      return NextResponse.json(
        { error: `AgentMail error: ${errorMessage}` },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { error: `Failed to send email: ${errorMessage}` },
      { status: 500 }
    );
  }
}