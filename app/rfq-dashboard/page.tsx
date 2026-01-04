'use client'

import React, { useState } from 'react';
import { RFQDashboard } from '../../components/RFQDashboard';
import { FollowUpApprovalModal } from '../../components/FollowUpApprovalModal';
import { ConversationModal } from '../../components/ConversationModal';
import { Button } from '../../components/Button';
import { useRFQs, useRFQStats, useSendFollowUp, useUpdateRFQStatus, useTriggerFollowUpCron, useDeleteRFQ } from '../../lib/rfq-api';
import { RFQRecord, DEFAULT_FOLLOW_UP_TEMPLATES } from '../../lib/rfq-types';
import { RefreshCw, Play, AlertCircle } from 'lucide-react';

// Force dynamic rendering to prevent prerendering errors (uses window.confirm, alert)
export const dynamic = 'force-dynamic';

export default function RFQDashboardPage() {
  const [selectedRFQ, setSelectedRFQ] = useState<RFQRecord | null>(null);
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [isConversationModalOpen, setIsConversationModalOpen] = useState(false);
  const [followUpType, setFollowUpType] = useState<keyof typeof DEFAULT_FOLLOW_UP_TEMPLATES>('follow_up_1');

  // API hooks
  const { data: rfqs = [], isLoading: rfqsLoading, refetch: refetchRFQs } = useRFQs();
  const { data: stats, isLoading: statsLoading } = useRFQStats();
  const sendFollowUpMutation = useSendFollowUp();
  const updateRFQMutation = useUpdateRFQStatus();
  const triggerCronMutation = useTriggerFollowUpCron();
  const deleteRFQMutation = useDeleteRFQ();

  // Default stats if not loaded
  const dashboardStats = stats || {
    totalRFQs: rfqs.length,
    pendingRFQs: rfqs.filter(rfq => ['sent', 'opened', 'follow_up_1', 'follow_up_2'].includes(rfq.status)).length,
    overdueRFQs: rfqs.filter(rfq => rfq.status === 'overdue').length,
    responseRate: rfqs.length > 0 ? (rfqs.filter(rfq => ['responded', 'quote_received'].includes(rfq.status)).length / rfqs.length) * 100 : 0,
    avgResponseTime: 3.5,
    todaysFollowUps: 0
  };

  const handleStatusUpdate = async (rfqId: string, status: any) => {
    try {
      await updateRFQMutation.mutateAsync({ id: rfqId, status });
    } catch (error) {
      console.error('Failed to update RFQ status:', error);
    }
  };

  const handleSendFollowUp = (rfqId: string) => {
    const rfq = rfqs.find(r => r.id === rfqId);
    if (!rfq) return;

    // Determine follow-up type based on current status
    let nextFollowUpType: keyof typeof DEFAULT_FOLLOW_UP_TEMPLATES = 'follow_up_1';
    
    if (rfq.status === 'sent' || rfq.status === 'opened') {
      nextFollowUpType = 'follow_up_1';
    } else if (rfq.status === 'follow_up_1') {
      nextFollowUpType = 'follow_up_2';
    } else {
      nextFollowUpType = 'final_notice';
    }

    setSelectedRFQ(rfq);
    setFollowUpType(nextFollowUpType);
    setIsApprovalModalOpen(true);
  };

  const handleApproveFollowUp = async (rfqId: string, customMessage?: string) => {
    try {
      await sendFollowUpMutation.mutateAsync({
        rfqId,
        followUpType,
        customMessage
      });
    } catch (error) {
      console.error('Failed to send follow-up:', error);
      throw error;
    }
  };

  const handleRejectFollowUp = (rfqId: string, reason: string) => {
    console.log('Follow-up rejected:', { rfqId, reason });
    // In production, you might want to log this or update the RFQ record
  };

  const handleViewDetails = (rfqId: string) => {
    const rfq = rfqs.find(r => r.id === rfqId);
    if (rfq) {
      setSelectedRFQ(rfq);
      setIsConversationModalOpen(true);
    }
  };

  const handleReply = async (message: string) => {
    if (!selectedRFQ) return;
    
    // In production, this would send the reply via your email API
    console.log('Sending reply:', message);
    
    // Simulate sending reply
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Update RFQ status to indicate continued conversation
    await updateRFQMutation.mutateAsync({
      id: selectedRFQ.id,
      notes: `${selectedRFQ.notes}\n[${new Date().toISOString()}] Reply sent: ${message.slice(0, 50)}...`
    });
  };

  const handleTriggerCron = async () => {
    try {
      const result = await triggerCronMutation.mutateAsync();
      console.log('Cron job triggered:', result);
      // Refetch data after cron run
      refetchRFQs();
    } catch (error) {
      console.error('Failed to trigger cron job:', error);
    }
  };

  const handleDeleteRFQ = async (rfqId: string) => {
    if (!window.confirm('Are you sure you want to delete this RFQ? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteRFQMutation.mutateAsync(rfqId);
    } catch (error) {
      console.error('Failed to delete RFQ:', error);
      alert('Failed to delete RFQ. Please try again.');
    }
  };

  if (rfqsLoading || statsLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="animate-spin h-8 w-8 mx-auto mb-4" />
          <p className="text-muted-foreground">Loading RFQ Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-background min-h-screen">
      <div className="max-w-7xl mx-auto px-3 md:px-6 py-3 md:py-8">
        <header className="mb-3 md:mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 md:gap-4">
            <div>
              <h1 className="text-xl md:text-3xl font-bold text-foreground">Messages Dashboard</h1>
              <p className="text-muted-foreground text-xs md:text-base">
                RFQ conversations, follow-ups and automated reminders
              </p>
            </div>
          </div>
        </header>

        {/* Main Dashboard */}
        <RFQDashboard
          rfqs={rfqs}
          stats={dashboardStats}
          onStatusUpdate={handleStatusUpdate}
          onSendFollowUp={handleSendFollowUp}
          onViewDetails={handleViewDetails}
          onDelete={handleDeleteRFQ}
        />

        {/* Follow-up Approval Modal */}
        <FollowUpApprovalModal
          isOpen={isApprovalModalOpen}
          onClose={() => setIsApprovalModalOpen(false)}
          onApprove={handleApproveFollowUp}
          onReject={handleRejectFollowUp}
          rfq={selectedRFQ}
          followUpType={followUpType}
        />

        {/* Conversation Modal */}
        <ConversationModal
          isOpen={isConversationModalOpen}
          onClose={() => setIsConversationModalOpen(false)}
          onReply={handleReply}
          rfq={selectedRFQ}
        />
      </div>
    </div>
  );
}