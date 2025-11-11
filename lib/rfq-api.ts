// API hooks for RFQ management and follow-ups

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RFQRecord, RFQDashboardStats, RFQStatus, DEFAULT_FOLLOW_UP_TEMPLATES } from './rfq-types';

// Fetch RFQs with optional filters
export const useRFQs = (status?: RFQStatus | 'all', supplier?: string) => {
  return useQuery({
    queryKey: ['rfqs', status, supplier],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (status && status !== 'all') params.append('status', status);
      if (supplier && supplier !== 'all') params.append('supplier', supplier);
      
      const response = await fetch(`/api/rfq?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch RFQs');
      }
      
      const data = await response.json();
      return data.rfqs as RFQRecord[];
    },
  });
};

// Fetch RFQ dashboard statistics
export const useRFQStats = () => {
  return useQuery({
    queryKey: ['rfq-stats'],
    queryFn: async () => {
      const response = await fetch('/api/rfq/stats');
      if (!response.ok) {
        throw new Error('Failed to fetch RFQ stats');
      }
      
      return response.json() as Promise<RFQDashboardStats>;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

// Create new RFQ record
export const useCreateRFQ = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: {
      originalQuery: string;
      partDetails: string;
      supplierName: string;
      supplierEmail: string;
      senderEmail: string;
      emailTemplate: string;
      followUpType?: 'auto' | 'manual_approval' | 'disabled';
    }) => {
      const response = await fetch('/api/rfq', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create RFQ');
      }
      
      return response.json();
    },
    onSuccess: () => {
      // Invalidate and refetch RFQ data
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
      queryClient.invalidateQueries({ queryKey: ['rfq-stats'] });
    },
  });
};

// Update RFQ status
export const useUpdateRFQStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: {
      id: string;
      status?: RFQStatus;
      notes?: string;
      responseReceivedAt?: string;
      quoteReceivedAt?: string;
    }) => {
      const response = await fetch('/api/rfq', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update RFQ');
      }
      
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
      queryClient.invalidateQueries({ queryKey: ['rfq-stats'] });
    },
  });
};

// Send manual follow-up
export const useSendFollowUp = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data: {
      rfqId: string;
      followUpType?: keyof typeof DEFAULT_FOLLOW_UP_TEMPLATES;
      customMessage?: string;
    }) => {
      const response = await fetch('/api/rfq/follow-up', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to send follow-up');
      }
      
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfqs'] });
      queryClient.invalidateQueries({ queryKey: ['rfq-stats'] });
    },
  });
};

// Get follow-up templates and rules
export const useFollowUpConfig = () => {
  return useQuery({
    queryKey: ['follow-up-config'],
    queryFn: async () => {
      const response = await fetch('/api/rfq/follow-up');
      if (!response.ok) {
        throw new Error('Failed to fetch follow-up configuration');
      }
      
      return response.json();
    },
  });
};

// Trigger manual cron job (for testing)
export const useTriggerFollowUpCron = () => {
  return useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/cron/follow-ups', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_CRON_SECRET || 'test'}`,
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to trigger cron job');
      }
      
      return response.json();
    },
  });
};