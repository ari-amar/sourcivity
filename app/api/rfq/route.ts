import { NextRequest, NextResponse } from 'next/server';
import { RFQRecord, RFQStatus, FollowUpType } from '../../../lib/rfq-types';

// Mock database - In production, this would be a real database
let mockRFQDatabase: RFQRecord[] = [
  {
    id: 'rfq_1726934400_abc123def',
    originalQuery: '3-phase motor',
    partDetails: 'Top 6 3-Phase Motors (static specifications only) - Industrial grade motors for manufacturing applications',
    supplierName: 'Digi-Key',
    supplierEmail: 'test@gmail.com',
    senderEmail: 'john.doe@sourcivity.com',
    emailTemplate: `Subject: Request for Quote - 3-phase motor

Dear Digi-Key Team,

I hope this email finds you well. We are reaching out to request a quote for the following industrial component:

Part: 3-phase motor
Quantity Required: 5 units
Timeline Required: 2 weeks
Additional Requirements: Industrial grade, 480V, 5HP

Could you please provide us with:
- Unit pricing and volume discounts
- Availability and lead times
- Technical specifications and datasheets
- Shipping costs and delivery options

We are currently evaluating multiple suppliers for this requirement and would appreciate your response by October 5th, 2024.

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com`,
    status: 'sent',
    sentAt: '2024-09-21T12:00:00.000Z',
    followUpCount: 0,
    followUpType: 'auto',
    notes: '',
    createdAt: '2024-09-21T12:00:00.000Z',
    updatedAt: '2024-09-21T12:00:00.000Z'
  },
  {
    id: 'rfq_1726848000_xyz789ghi',
    originalQuery: 'ceramic capacitor 10uF',
    partDetails: 'Top 6 10µF Ceramic Capacitors (static specifications only) - High quality capacitors for electronic circuits',
    supplierName: 'RS Components',
    supplierEmail: 'test@gmail.com',
    senderEmail: 'john.doe@sourcivity.com',
    emailTemplate: `Subject: Request for Quote - ceramic capacitor 10uF

Dear RS Components Team,

I hope this email finds you well. We are reaching out to request a quote for the following electronic component:

Part: ceramic capacitor 10uF
Quantity Required: 1000 pieces
Timeline Required: 1 week
Additional Requirements: X7R dielectric, 25V minimum, 1206 package

Could you please provide us with:
- Unit pricing and volume discounts
- Availability and lead times
- Technical specifications and datasheets
- Shipping costs and delivery options

We are currently evaluating multiple suppliers for this requirement and would appreciate your response by September 28th, 2024.

Best regards,
John Doe
Head of Procurement
Sourcivity Inc.
Phone: (555) 123-4567
Email: john.doe@sourcivity.com`,
    status: 'quote_received',
    sentAt: '2024-09-20T09:00:00.000Z',
    followUpCount: 1,
    followUpType: 'auto',
    lastFollowUpAt: '2024-09-23T09:00:00.000Z',
    responseReceivedAt: '2024-09-24T14:30:00.000Z',
    quoteReceivedAt: '2024-09-24T14:30:00.000Z',
    notes: '[2024-09-24T14:30:00.000Z] Supplier response received via email',
    createdAt: '2024-09-20T09:00:00.000Z',
    updatedAt: '2024-09-24T14:30:00.000Z'
  }
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get('status');
  const supplier = searchParams.get('supplier');

  console.log(`[${new Date().toISOString()}] Fetching RFQs with filters:`, { status, supplier });

  try {
    let filteredRFQs = mockRFQDatabase;

    // Apply filters
    if (status && status !== 'all') {
      filteredRFQs = filteredRFQs.filter(rfq => rfq.status === status as RFQStatus);
    }

    if (supplier && supplier !== 'all') {
      filteredRFQs = filteredRFQs.filter(rfq => rfq.supplierName === supplier);
    }

    // Sort by most recent first
    filteredRFQs.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return NextResponse.json({
      rfqs: filteredRFQs,
      total: filteredRFQs.length
    });

  } catch (error) {
    console.error('Error fetching RFQs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch RFQs' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  console.log(`[${new Date().toISOString()}] Creating new RFQ record`);

  try {
    const body = await request.json();
    const { 
      originalQuery, 
      partDetails, 
      supplierName, 
      supplierEmail, 
      senderEmail, 
      emailTemplate,
      followUpType = 'auto' as FollowUpType
    } = body;

    // Validate required fields
    if (!originalQuery || !supplierName || !supplierEmail || !senderEmail || !emailTemplate) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    const now = new Date().toISOString();
    const newRFQ: RFQRecord = {
      id: `rfq_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      originalQuery,
      partDetails: partDetails || '',
      supplierName,
      supplierEmail,
      senderEmail,
      emailTemplate,
      status: 'sent',
      sentAt: now,
      followUpCount: 0,
      followUpType,
      notes: '',
      createdAt: now,
      updatedAt: now
    };

    // Add to mock database
    mockRFQDatabase.push(newRFQ);

    console.log(`[${new Date().toISOString()}] Created RFQ:`, newRFQ.id);

    return NextResponse.json({
      success: true,
      rfq: newRFQ
    });

  } catch (error) {
    console.error('Error creating RFQ:', error);
    return NextResponse.json(
      { error: 'Failed to create RFQ record' },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  console.log(`[${new Date().toISOString()}] Updating RFQ record`);

  try {
    const body = await request.json();
    const { id, status, notes, responseReceivedAt, quoteReceivedAt } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'RFQ ID is required' },
        { status: 400 }
      );
    }

    // Find RFQ in mock database
    const rfqIndex = mockRFQDatabase.findIndex(rfq => rfq.id === id);
    
    if (rfqIndex === -1) {
      return NextResponse.json(
        { error: 'RFQ not found' },
        { status: 404 }
      );
    }

    // Update RFQ record
    const updatedRFQ = {
      ...mockRFQDatabase[rfqIndex],
      ...(status && { status }),
      ...(notes && { notes }),
      ...(responseReceivedAt && { responseReceivedAt }),
      ...(quoteReceivedAt && { quoteReceivedAt }),
      updatedAt: new Date().toISOString()
    };

    mockRFQDatabase[rfqIndex] = updatedRFQ;

    console.log(`[${new Date().toISOString()}] Updated RFQ:`, id);

    return NextResponse.json({
      success: true,
      rfq: updatedRFQ
    });

  } catch (error) {
    console.error('Error updating RFQ:', error);
    return NextResponse.json(
      { error: 'Failed to update RFQ' },
      { status: 500 }
    );
  }
}