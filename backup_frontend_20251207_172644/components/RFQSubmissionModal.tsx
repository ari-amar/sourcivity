'use client'

import React, { useState, useMemo } from 'react';
import { X, ShoppingCart, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from './Button';
import { Input } from './Input';
import { Badge } from './Badge';
import { EmailValidationModal } from './EmailValidationModal';
import { useRfqConversation } from '../lib/searchApi';
import { useCreateRFQ } from '../lib/rfq-api';
import type { RFQCartItem } from '../lib/types';

interface RFQSubmissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  cartItems: RFQCartItem[];
}

type Step = 'details' | 'templates';

export const RFQSubmissionModal = ({ isOpen, onClose, cartItems }: RFQSubmissionModalProps) => {
  const [step, setStep] = useState<Step>('details');
  const [rfqDetails, setRfqDetails] = useState({
    quantity: '',
    timeline: '',
    additionalRequirements: ''
  });
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([]);
  const [emailModalState, setEmailModalState] = useState<{
    isOpen: boolean;
    supplierName: string;
    emailTemplate: string;
  }>({
    isOpen: false,
    supplierName: '',
    emailTemplate: ''
  });

  const rfqMutation = useRfqConversation();
  const createRFQMutation = useCreateRFQ();

  // Extract unique suppliers from cart items
  const availableSuppliers = useMemo(() => {
    const suppliersSet = new Set<string>();

    cartItems.forEach(item => {
      // Extract supplier name from the part name or URL
      // The part name format is typically "[PartName (Type)](URL)"
      // We need to extract the domain or supplier info from the URL or supplier type

      // For now, we'll use a combination of supplier type and extract from URL
      try {
        const url = new URL(item.partUrl);
        const domain = url.hostname.replace('www.', '');

        // Clean up domain to get supplier name (e.g., 'mcmaster.com' -> 'McMaster-Carr')
        let supplierName = domain.split('.')[0];

        // Capitalize first letter
        supplierName = supplierName.charAt(0).toUpperCase() + supplierName.slice(1);

        suppliersSet.add(supplierName);
      } catch {
        // If URL parsing fails, use supplier type as fallback
        if (item.supplierType) {
          suppliersSet.add(item.supplierType);
        }
      }
    });

    return Array.from(suppliersSet).sort();
  }, [cartItems]);

  // Generate part details summary for AI
  const partDetailsSummary = useMemo(() => {
    return cartItems.map(item => {
      const specs = Object.entries(item.columnData)
        .map(([key, value]) => `  ${key}: ${value}`)
        .join('\n');

      return `- ${item.partName}\n${specs}\n  Supplier: ${item.supplierType} (${item.partUrl})`;
    }).join('\n\n');
  }, [cartItems]);

  // Build search query from cart items
  const searchQuery = useMemo(() => {
    if (cartItems.length === 1) {
      return cartItems[0].partName;
    }
    return `${cartItems.length} industrial parts: ${cartItems.map(i => i.partName).join(', ')}`;
  }, [cartItems]);

  const handleGenerateTemplates = async () => {
    if (!rfqDetails.quantity || !rfqDetails.timeline) {
      alert('Please fill in quantity and timeline');
      return;
    }

    // Auto-select all available suppliers
    const suppliersToUse = availableSuppliers.length > 0 ? availableSuppliers : ['Unknown Supplier'];
    setSelectedSuppliers(suppliersToUse);

    try {
      await rfqMutation.mutateAsync({
        query: searchQuery,
        partDetails: partDetailsSummary,
        usSuppliersOnly: true,
        rfqDetails: rfqDetails,
        selectedSuppliers: suppliersToUse
      });
      setStep('templates');
    } catch (error) {
      console.error('RFQ generation failed:', error);
      if (error instanceof Error && error.message.includes('rate limit')) {
        alert('Rate limit exceeded. Please try again in a few minutes or upgrade your Groq plan.');
      } else {
        alert(`RFQ generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }
  };

  const handleSendEmail = (supplierName: string, emailTemplate: string) => {
    setEmailModalState({
      isOpen: true,
      supplierName,
      emailTemplate
    });
  };

  const handleEmailModalClose = () => {
    setEmailModalState({
      isOpen: false,
      supplierName: '',
      emailTemplate: ''
    });
  };

  const sendEmailViaAgentMail = async (recipientEmail: string, senderEmail: string) => {
    const response = await fetch('/api/email/send-rfq', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        recipientEmail,
        senderEmail,
        emailTemplate: emailModalState.emailTemplate,
        supplierName: emailModalState.supplierName,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to send email via AgentMail');
    }

    const result = await response.json();

    // Create RFQ tracking record after successful email send
    if (result.success && searchQuery) {
      try {
        await createRFQMutation.mutateAsync({
          originalQuery: searchQuery,
          partDetails: partDetailsSummary,
          supplierName: emailModalState.supplierName,
          supplierEmail: recipientEmail,
          senderEmail,
          emailTemplate: emailModalState.emailTemplate,
          followUpType: 'auto'
        });
        console.log('RFQ tracking record created successfully');
      } catch (error) {
        console.error('Failed to create RFQ tracking record:', error);
      }
    }

    return result;
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const handleClose = () => {
    // Reset state when closing
    setStep('details');
    setRfqDetails({ quantity: '', timeline: '', additionalRequirements: '' });
    setSelectedSuppliers([]);
    rfqMutation.reset();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

        {/* Modal */}
        <div className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-xl shadow-2xl overflow-hidden flex flex-col">
          {/* Header */}
          <div className="border-b border-gray-200 px-6 py-4 bg-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center">
                  <ShoppingCart size={20} className="text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Submit RFQ</h2>
                  <p className="text-sm text-gray-600">
                    {step === 'details' && 'Enter RFQ details'}
                    {step === 'templates' && 'Review and send RFQ emails'}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClose}
                className="p-2"
              >
                <X size={20} />
              </Button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {/* Step 1: RFQ Details */}
            {step === 'details' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-4">Parts in RFQ ({cartItems.length})</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-4">
                    {cartItems.map((item) => (
                      <div key={item.id} className="flex items-start gap-3 text-sm">
                        <span className="text-gray-400">•</span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{item.partName}</div>
                          <div className="text-xs text-gray-600 mt-1">
                            {Object.values(item.columnData).slice(0, 3).join(' • ')}
                          </div>
                        </div>
                        <Badge variant="secondary" className="text-xs font-normal whitespace-nowrap">
                          {item.supplierType}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-900">
                      Quantity Required *
                    </label>
                    <Input
                      type="text"
                      placeholder="e.g., 50 units, 10-20 pieces"
                      value={rfqDetails.quantity}
                      onChange={(e) => setRfqDetails(prev => ({ ...prev, quantity: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-900">
                      Timeline Required *
                    </label>
                    <Input
                      type="text"
                      placeholder="e.g., 2-3 weeks, ASAP, End of Q1"
                      value={rfqDetails.timeline}
                      onChange={(e) => setRfqDetails(prev => ({ ...prev, timeline: e.target.value }))}
                      className="w-full"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-900">
                      Additional Requirements (Optional)
                    </label>
                    <textarea
                      placeholder="e.g., Certifications needed, specific mounting requirements, testing documentation..."
                      value={rfqDetails.additionalRequirements}
                      onChange={(e) => setRfqDetails(prev => ({ ...prev, additionalRequirements: e.target.value }))}
                      className="w-full min-h-[100px] px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Email Templates */}
            {step === 'templates' && rfqMutation.data && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">AI-Generated RFQ Emails</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Review the personalized email templates generated for each supplier:
                  </p>
                </div>

                {selectedSuppliers.map((supplier) => {
                  const fullContent = rfqMutation.data?.rfqContent || '';

                  // Extract email template for this supplier
                  const supplierRegex = new RegExp(`=== ${supplier} Email Template ===[\\s\\S]*?(?====|$)`, 'i');
                  const supplierMatch = fullContent.match(supplierRegex);

                  let emailTemplate = '';
                  if (supplierMatch) {
                    emailTemplate = supplierMatch[0]
                      .replace(`=== ${supplier} Email Template ===`, '')
                      .replace(/===$/, '')
                      .trim();
                  } else {
                    const genericMatch = fullContent.match(/=== Email Template ===[\\s\\S]*?(?====|$)/);
                    if (genericMatch) {
                      emailTemplate = genericMatch[0]
                        .replace('=== Email Template ===', '')
                        .replace(/===$/, '')
                        .replace(/Dear Supplier/g, `Dear ${supplier} Team`)
                        .trim();
                    } else {
                      emailTemplate = fullContent;
                    }
                  }

                  return (
                    <div key={supplier} className="border border-gray-200 rounded-lg p-4 bg-white">
                      <div className="mb-3 flex items-center justify-between">
                        <Badge variant="outline">{supplier}</Badge>
                      </div>
                      <pre className="text-sm bg-gray-50 p-3 rounded whitespace-pre-wrap overflow-x-auto mb-3 max-h-64 overflow-y-auto border border-gray-200">
                        {emailTemplate || 'Template not available'}
                      </pre>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(emailTemplate)}
                        >
                          Copy Template
                        </Button>
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleSendEmail(supplier, emailTemplate)}
                          className="bg-blue-600 text-white hover:bg-blue-700"
                        >
                          Send Email
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Loading state */}
            {rfqMutation.isPending && (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
                  <p className="text-sm text-gray-600">Generating personalized RFQ emails...</p>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {step === 'details' && (
                  <>
                    {`${cartItems.length} item${cartItems.length === 1 ? '' : 's'} in RFQ`}
                    {availableSuppliers.length > 0 && ` • ${availableSuppliers.length} supplier${availableSuppliers.length === 1 ? '' : 's'} detected`}
                  </>
                )}
                {step === 'templates' && `${selectedSuppliers.length} email template${selectedSuppliers.length === 1 ? '' : 's'} generated`}
              </div>
              <div className="flex gap-3">
                {step === 'details' && (
                  <Button
                    onClick={handleGenerateTemplates}
                    disabled={!rfqDetails.quantity || !rfqDetails.timeline || rfqMutation.isPending}
                    className="bg-blue-600 text-white hover:bg-blue-700"
                  >
                    {rfqMutation.isPending ? 'Generating RFQ Emails...' : 'Generate RFQ Emails'}
                    <ChevronRight size={16} className="ml-1" />
                  </Button>
                )}
                {step === 'templates' && (
                  <Button
                    variant="outline"
                    onClick={handleClose}
                  >
                    Done
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Email Validation Modal */}
      <EmailValidationModal
        isOpen={emailModalState.isOpen}
        onClose={handleEmailModalClose}
        onSendEmail={sendEmailViaAgentMail}
        supplierName={emailModalState.supplierName}
        emailTemplate={emailModalState.emailTemplate}
      />
    </>
  );
};
