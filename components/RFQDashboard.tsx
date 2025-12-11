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
  Send,
  Trash2,
  X
} from 'lucide-react';
import { RFQRecord, RFQStatus, FollowUpType, RFQDashboardStats } from '../lib/rfq-types';

interface RFQDashboardProps {
  rfqs: RFQRecord[];
  stats: RFQDashboardStats;
  onStatusUpdate: (rfqId: string, status: RFQStatus) => void;
  onSendFollowUp: (rfqId: string) => void;
  onViewDetails: (rfqId: string) => void;
  onDelete: (rfqId: string) => void;
}

export const RFQDashboard = ({
  rfqs,
  stats,
  onStatusUpdate,
  onSendFollowUp,
  onViewDetails,
  onDelete
}: RFQDashboardProps) => {
  const [selectedStatus, setSelectedStatus] = useState<RFQStatus | 'all'>('all');
  const [selectedSupplier, setSelectedSupplier] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [openDropdownId, setOpenDropdownId] = useState<string | null>(null);

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
    <div className="space-y-4 md:space-y-6">
      {/* Dashboard Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4">
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{stats.totalRFQs}</div>
          <div className="text-xs md:text-sm text-muted-foreground">Total RFQs</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{stats.pendingRFQs}</div>
          <div className="text-xs md:text-sm text-muted-foreground">Pending</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{stats.overdueRFQs}</div>
          <div className="text-xs md:text-sm text-muted-foreground">Overdue</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{Math.round(stats.responseRate)}%</div>
          <div className="text-xs md:text-sm text-muted-foreground">Response Rate</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{stats.avgResponseTime}d</div>
          <div className="text-xs md:text-sm text-muted-foreground">Avg Response</div>
        </div>
        <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
          <div className="text-xl md:text-2xl font-bold bg-gradient-to-r from-blue-500 to-blue-600 bg-clip-text text-transparent">{stats.todaysFollowUps}</div>
          <div className="text-xs md:text-sm text-muted-foreground">Today's Follow-ups</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface border border-input rounded-lg p-3 md:p-4">
        <div className="flex flex-col md:flex-row md:items-center gap-3 md:gap-4">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <label className="text-xs md:text-sm whitespace-nowrap">Status:</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as RFQStatus | 'all')}
              className="text-xs md:text-sm border border-input rounded px-2 py-1 flex-1 min-w-0"
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

          <div className="flex items-center gap-2 flex-1 min-w-0">
            <label className="text-xs md:text-sm whitespace-nowrap">Supplier:</label>
            <select
              value={selectedSupplier}
              onChange={(e) => setSelectedSupplier(e.target.value)}
              className="text-xs md:text-sm border border-input rounded px-2 py-1 flex-1 min-w-0"
            >
              <option value="all">All</option>
              {uniqueSuppliers.map(supplier => (
                <option key={supplier} value={supplier}>{supplier}</option>
              ))}
            </select>
          </div>

          <div className="w-full md:flex-1">
            <Input
              placeholder="Search RFQs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full md:max-w-xs text-sm"
            />
          </div>
        </div>
      </div>

      {/* RFQ Table - Desktop */}
      <div className="hidden md:block bg-surface border border-input rounded-lg overflow-hidden">
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
              {filteredRFQs.map((rfq) => {
                // Extract just the part names from partDetails
                const extractPartNames = (partDetails: string) => {
                  const lines = partDetails.split('\n').filter(p => p.trim());
                  const partNames: string[] = [];
                  
                  lines.forEach(line => {
                    // Look for lines that start with "- " (part name format)
                    if (line.startsWith('- ')) {
                      const partName = line.substring(2).split('\n')[0]; // Remove "- " and take first line
                      partNames.push(partName);
                    }
                  });
                  
                  return partNames.length > 0 ? partNames : [partDetails.slice(0, 50) + '...'];
                };

                const partNames = extractPartNames(rfq.partDetails);
                const displayParts = partNames.slice(0, 3);

                return (
                  <tr
                    key={rfq.id}
                    className="hover:bg-muted/50 cursor-pointer"
                    onClick={() => onViewDetails(rfq.id)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">{rfq.originalQuery}</div>
                      {partNames.length > 1 ? (
                        <ul className="text-xs text-muted-foreground mt-1 list-disc list-inside">
                          {displayParts.map((part, idx) => (
                            <li key={idx} className="truncate max-w-xs">{part}</li>
                          ))}
                          {partNames.length > 3 && (
                            <li className="text-muted-foreground/70">+{partNames.length - 3} more...</li>
                          )}
                        </ul>
                      ) : (
                        <div className="text-xs text-muted-foreground truncate max-w-xs">
                          {partNames[0]}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">{rfq.supplierName}</div>
                      <div className="text-xs text-muted-foreground">{rfq.supplierEmail}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={getStatusBadgeVariant(rfq.status)}
                        className="inline-flex items-center gap-1.5"
                      >
                        <span className="flex items-center">{getStatusIcon(rfq.status)}</span>
                        <span>{rfq.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</span>
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
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSendFollowUp(rfq.id)}
                          className="p-1"
                          title="Send follow-up"
                        >
                          <Send size={14} />
                        </Button>
                        <div className="relative">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="p-1"
                            title="More actions"
                            onClick={() => setOpenDropdownId(openDropdownId === rfq.id ? null : rfq.id)}
                          >
                            <MoreHorizontal size={14} />
                          </Button>
                          {openDropdownId === rfq.id && (
                            <>
                              <div
                                className="fixed inset-0 z-10"
                                onClick={() => setOpenDropdownId(null)}
                              />
                              <div className="absolute right-0 top-8 z-20 bg-surface border border-input rounded-lg shadow-lg py-1 min-w-[160px]">
                                <button
                                  onClick={() => {
                                    setOpenDropdownId(null);
                                    onDelete(rfq.id);
                                  }}
                                  className="w-full px-4 py-2 text-left text-sm hover:bg-muted flex items-center gap-2 text-destructive"
                                >
                                  <Trash2 size={14} />
                                  Delete RFQ
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {filteredRFQs.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No RFQs found matching your filters
          </div>
        )}
      </div>

      {/* RFQ Cards - Mobile */}
      <div className="md:hidden space-y-3">
        {filteredRFQs.map((rfq) => {
          const extractPartNames = (partDetails: string) => {
            const lines = partDetails.split('\n').filter(p => p.trim());
            const partNames: string[] = [];

            lines.forEach(line => {
              if (line.startsWith('- ')) {
                const partName = line.substring(2).split('\n')[0];
                partNames.push(partName);
              }
            });

            return partNames.length > 0 ? partNames : [partDetails.slice(0, 50) + '...'];
          };

          const partNames = extractPartNames(rfq.partDetails);
          const displayParts = partNames.slice(0, 2);

          return (
            <div
              key={rfq.id}
              onClick={() => onViewDetails(rfq.id)}
              className="bg-surface border border-input rounded-lg p-4 space-y-3"
            >
              {/* Header with Query and Status */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm truncate">{rfq.originalQuery}</h3>
                  {partNames.length > 1 ? (
                    <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                      {displayParts.map((part, idx) => (
                        <li key={idx} className="truncate">• {part}</li>
                      ))}
                      {partNames.length > 2 && (
                        <li className="text-muted-foreground/70">+{partNames.length - 2} more...</li>
                      )}
                    </ul>
                  ) : (
                    <div className="text-xs text-muted-foreground truncate mt-0.5">
                      {partNames[0]}
                    </div>
                  )}
                </div>
                <Badge
                  variant={getStatusBadgeVariant(rfq.status)}
                  className="inline-flex items-center gap-1 text-xs flex-shrink-0"
                >
                  <span className="flex items-center">{getStatusIcon(rfq.status)}</span>
                  <span className="hidden sm:inline">{rfq.status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</span>
                </Badge>
              </div>

              {/* Supplier Info */}
              <div className="pt-2 border-t border-border">
                <div className="text-xs text-muted-foreground">Supplier</div>
                <div className="font-medium text-sm">{rfq.supplierName}</div>
                <div className="text-xs text-muted-foreground truncate">{rfq.supplierEmail}</div>
              </div>

              {/* Stats Row */}
              <div className="flex items-center justify-between pt-2 border-t border-border text-xs">
                <div>
                  <div className="text-muted-foreground">Sent</div>
                  <div className="font-medium">{getDaysAgo(rfq.sentAt)}d ago</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Follow-ups</div>
                  <div className="font-medium">{rfq.followUpCount}</div>
                </div>
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onSendFollowUp(rfq.id)}
                    className="p-1.5"
                    title="Send follow-up"
                  >
                    <Send size={14} />
                  </Button>
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="p-1.5"
                      title="More actions"
                      onClick={() => setOpenDropdownId(openDropdownId === rfq.id ? null : rfq.id)}
                    >
                      <MoreHorizontal size={14} />
                    </Button>
                    {openDropdownId === rfq.id && (
                      <>
                        <div
                          className="fixed inset-0 z-10"
                          onClick={() => setOpenDropdownId(null)}
                        />
                        <div className="absolute right-0 top-8 z-20 bg-surface border border-input rounded-lg shadow-lg py-1 min-w-[160px]">
                          <button
                            onClick={() => {
                              setOpenDropdownId(null);
                              onDelete(rfq.id);
                            }}
                            className="w-full px-4 py-2 text-left text-sm hover:bg-muted flex items-center gap-2 text-destructive"
                          >
                            <Trash2 size={14} />
                            Delete RFQ
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {filteredRFQs.length === 0 && (
          <div className="text-center py-8 text-muted-foreground bg-surface border border-input rounded-lg">
            No RFQs found matching your filters
          </div>
        )}
      </div>
    </div>
  );
};