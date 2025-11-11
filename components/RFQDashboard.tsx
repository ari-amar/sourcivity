import React, { useState } from 'react';
import { Button } from './Button';
import { Badge } from './Badge';
import { Input } from './Input';
import { 
  Clock, 
  AlertTriangle, 
  CheckCircle, 
  Mail, 
  Calendar, 
  Filter,
  MoreHorizontal,
  Eye,
  Send
} from 'lucide-react';
import { RFQRecord, RFQStatus, FollowUpType, RFQDashboardStats } from '../lib/rfq-types';

interface RFQDashboardProps {
  rfqs: RFQRecord[];
  stats: RFQDashboardStats;
  onStatusUpdate: (rfqId: string, status: RFQStatus) => void;
  onSendFollowUp: (rfqId: string) => void;
  onViewDetails: (rfqId: string) => void;
}

export const RFQDashboard = ({
  rfqs,
  stats,
  onStatusUpdate,
  onSendFollowUp,
  onViewDetails
}: RFQDashboardProps) => {
  const [selectedStatus, setSelectedStatus] = useState<RFQStatus | 'all'>('all');
  const [selectedSupplier, setSelectedSupplier] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const getStatusBadgeVariant = (status: RFQStatus) => {
    switch (status) {
      case 'sent':
      case 'opened':
        return 'outline';
      case 'follow_up_1':
      case 'follow_up_2':
        return 'secondary';
      case 'overdue':
      case 'final_notice':
        return 'destructive';
      case 'responded':
      case 'quote_received':
        return 'default';
      case 'completed':
        return 'default';
      case 'non_responsive':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const getStatusIcon = (status: RFQStatus) => {
    switch (status) {
      case 'sent':
        return <Mail size={14} />;
      case 'opened':
        return <Eye size={14} />;
      case 'overdue':
      case 'final_notice':
        return <AlertTriangle size={14} />;
      case 'responded':
      case 'quote_received':
      case 'completed':
        return <CheckCircle size={14} />;
      default:
        return <Clock size={14} />;
    }
  };

  const filteredRFQs = rfqs.filter(rfq => {
    const matchesStatus = selectedStatus === 'all' || rfq.status === selectedStatus;
    const matchesSupplier = selectedSupplier === 'all' || rfq.supplierName === selectedSupplier;
    const matchesSearch = searchQuery === '' || 
      rfq.originalQuery.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rfq.supplierName.toLowerCase().includes(searchQuery.toLowerCase());
    
    return matchesStatus && matchesSupplier && matchesSearch;
  });

  const uniqueSuppliers = Array.from(new Set(rfqs.map(rfq => rfq.supplierName)));

  const getDaysAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <div className="space-y-6">
      {/* Dashboard Stats */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-foreground">{stats.totalRFQs}</div>
          <div className="text-sm text-muted-foreground">Total RFQs</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-orange-600">{stats.pendingRFQs}</div>
          <div className="text-sm text-muted-foreground">Pending</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-red-600">{stats.overdueRFQs}</div>
          <div className="text-sm text-muted-foreground">Overdue</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-green-600">{Math.round(stats.responseRate)}%</div>
          <div className="text-sm text-muted-foreground">Response Rate</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-blue-600">{stats.avgResponseTime}d</div>
          <div className="text-sm text-muted-foreground">Avg Response</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-4">
          <div className="text-2xl font-bold text-purple-600">{stats.todaysFollowUps}</div>
          <div className="text-sm text-muted-foreground">Today's Follow-ups</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface border border-input rounded-lg p-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter size={16} />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="text-sm">Status:</label>
            <select 
              value={selectedStatus} 
              onChange={(e) => setSelectedStatus(e.target.value as RFQStatus | 'all')}
              className="text-sm border border-input rounded px-2 py-1"
            >
              <option value="all">All</option>
              <option value="sent">Sent</option>
              <option value="opened">Opened</option>
              <option value="follow_up_1">Follow-up 1</option>
              <option value="follow_up_2">Follow-up 2</option>
              <option value="final_notice">Final Notice</option>
              <option value="overdue">Overdue</option>
              <option value="responded">Responded</option>
              <option value="quote_received">Quote Received</option>
              <option value="completed">Completed</option>
              <option value="non_responsive">Non-responsive</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm">Supplier:</label>
            <select 
              value={selectedSupplier} 
              onChange={(e) => setSelectedSupplier(e.target.value)}
              className="text-sm border border-input rounded px-2 py-1"
            >
              <option value="all">All</option>
              {uniqueSuppliers.map(supplier => (
                <option key={supplier} value={supplier}>{supplier}</option>
              ))}
            </select>
          </div>

          <div className="flex-1">
            <Input
              placeholder="Search RFQs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="max-w-xs"
            />
          </div>
        </div>
      </div>

      {/* RFQ Table */}
      <div className="bg-surface border border-input rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Part Query</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Supplier</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Sent</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Follow-ups</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredRFQs.map((rfq) => (
                <tr 
                  key={rfq.id} 
                  className="hover:bg-muted/50 cursor-pointer"
                  onClick={() => onViewDetails(rfq.id)}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-sm">{rfq.originalQuery}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-xs">
                      {rfq.partDetails.slice(0, 100)}...
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-sm">{rfq.supplierName}</div>
                    <div className="text-xs text-muted-foreground">{rfq.supplierEmail}</div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge 
                      variant={getStatusBadgeVariant(rfq.status)}
                      className="flex items-center gap-1"
                    >
                      {getStatusIcon(rfq.status)}
                      {rfq.status.replace('_', ' ')}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">{getDaysAgo(rfq.sentAt)}d ago</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(rfq.sentAt).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm font-medium">{rfq.followUpCount}</div>
                    {rfq.lastFollowUpAt && (
                      <div className="text-xs text-muted-foreground">
                        Last: {getDaysAgo(rfq.lastFollowUpAt)}d ago
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      {(rfq.status === 'sent' || rfq.status === 'opened' || rfq.status === 'overdue') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSendFollowUp(rfq.id)}
                          className="p-1"
                          title="Send follow-up"
                        >
                          <Send size={14} />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="p-1"
                        title="More actions"
                      >
                        <MoreHorizontal size={14} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredRFQs.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No RFQs found matching your filters
          </div>
        )}
      </div>
    </div>
  );
};