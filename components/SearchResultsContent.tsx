import React, { useMemo, useState, useEffect } from 'react';
import { Button } from './Button';
import { Badge } from './Badge';
import { Input } from './Input';
import { EmailValidationModal } from './EmailValidationModal';
import { ProductTable } from './ProductTable';
import { RFQCart } from './RFQCart';
import { useRfqConversation } from '../lib/searchApi';
import { useCreateRFQ } from '../lib/rfq-api';
import { parseTableToProducts, hasTableStructure, extractColumnNames } from '../lib/tableParser';
import { getDatasheetLink } from '../lib/dummyData';

interface SearchResultsContentProps {
  responseText: string;
  originalQuery?: string;
  usSuppliersOnly?: boolean;
  onUsSuppliersOnlyChange?: (value: boolean) => void;
}

export const SearchResultsContent = ({ responseText, originalQuery, usSuppliersOnly = false, onUsSuppliersOnlyChange }: SearchResultsContentProps) => {
  const [rfqStep, setRfqStep] = useState<'prompt' | 'recommendations' | 'suppliers' | 'details' | 'templates'>('prompt');
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([]);
  const [rfqDetails, setRfqDetails] = useState({
    quantity: '',
    timeline: '',
    additionalRequirements: ''
  });
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
  // Enhanced markdown-to-HTML conversion with proper table support
  const convertMarkdownToHtml = (text: string) => {
    // First handle tables
    let processed = text;
    
    // Split into lines and process tables
    const lines = processed.split('\n');
    const result: string[] = [];
    let inTable = false;
    let tableRows: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Check if this is a table row (contains |)
      if (line.includes('|') && !line.match(/^-+$/)) {
        if (!inTable) {
          inTable = true;
          tableRows = [];
        }
        tableRows.push(line);
      } else if (line.match(/^[-\s|]+$/) || line.includes('---')) {
        // Table separator line or line with dashes, skip it
        continue;
      } else {
        // Not a table line
        if (inTable) {
          // Process the collected table
          if (tableRows.length > 0) {
            const tableHtml = processTable(tableRows);
            result.push(tableHtml);
          }
          inTable = false;
          tableRows = [];
        }
        result.push(line);
      }
    }
    
    // Handle any remaining table
    if (inTable && tableRows.length > 0) {
      const tableHtml = processTable(tableRows);
      result.push(tableHtml);
    }
    
    processed = result.join('\n');
    
    // Apply other markdown formatting
    return processed
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
      .replace(/\n\n/g, '</p><p class="mb-4">')
      .replace(/\n/g, '<br>');
  };
  
  const processTable = (tableRows: string[]): string => {
    if (tableRows.length === 0) return '';

    const [headerRow, ...dataRows] = tableRows;

    // Process header and add Datasheets as second column
    const headers = headerRow.split('|').map(h => h.trim()).filter(h => h);
    const enhancedHeaders = [headers[0], 'Datasheets', ...headers.slice(1)];
    const headerHtml = enhancedHeaders.map(h => `<th class="border border-gray-300 px-4 py-2 bg-gray-50 font-semibold text-left">${h}</th>`).join('');

    // Process data rows and filter out empty rows
    const rowsHtml = dataRows
      .filter(row => {
        const cells = row.split('|').map(c => c.trim()).filter(c => c);
        // Skip rows where first cell is just "---" or empty
        return cells.length > 0 && cells[0] !== '---' && cells[0] !== '';
      })
      .map(row => {
        const cells = row.split('|').map(c => c.trim()).filter(c => c);

        // Process all cells normally first
        const processedCells = cells.map(cell => {
          const urlMatch = cell.match(/\[(.*?)\]\((.*?)\)/);
          if (urlMatch) {
            const [, linkText, url] = urlMatch;
            // Check if there's content after the link (like <br/>🇺🇸 OEM)
            let afterLink = cell.substring(cell.indexOf(')') + 1);

            // Add tooltips to country flag emojis
            const countryMap: { [key: string]: string } = {
              '🇺🇸': 'United States',
              '🇨🇦': 'Canada',
              '🇬🇧': 'United Kingdom',
              '🇩🇪': 'Germany',
              '🇫🇷': 'France',
              '🇮🇹': 'Italy',
              '🇪🇸': 'Spain',
              '🇯🇵': 'Japan',
              '🇨🇳': 'China',
              '🇰🇷': 'South Korea',
              '🇮🇳': 'India',
              '🇦🇺': 'Australia',
              '🇧🇷': 'Brazil',
              '🇲🇽': 'Mexico',
              '🇳🇱': 'Netherlands',
              '🇸🇪': 'Sweden',
              '🇨🇭': 'Switzerland',
              '🇸🇬': 'Singapore',
              '🇹🇼': 'Taiwan',
            };

            // Replace country emojis with tooltip-wrapped versions
            Object.entries(countryMap).forEach(([emoji, country]) => {
              const regex = new RegExp(emoji, 'g');
              afterLink = afterLink.replace(regex, `<span class="country-flag-tooltip" data-country="${country}">${emoji}</span>`);
            });

            const linkHtml = `<a href="${url}" target="_blank" class="text-blue-600 hover:text-blue-800 underline">${linkText}</a>`;
            return `<td class="border border-gray-300 px-4 py-2">${linkHtml}${afterLink}</td>`;
          }
          return `<td class="border border-gray-300 px-4 py-2">${cell}</td>`;
        });

        // Extract part name from first cell and get datasheet link
        const firstCell = cells[0];
        const partNameMatch = firstCell.match(/\[([^\]]+)\]/);
        let datasheetLink = '#';

        if (partNameMatch) {
          const partName = partNameMatch[1].trim();
          const link = getDatasheetLink(partName);
          if (link) {
            datasheetLink = link;
          }
        }

        // Insert datasheet emoji as clickable link with consistent sizing
        const datasheetCell = datasheetLink !== '#'
          ? `<td class="border border-gray-300 px-4 py-2 text-center align-middle" style="vertical-align: middle;">
              <a href="${datasheetLink}" target="_blank" rel="noopener noreferrer" class="inline-block cursor-pointer hover:opacity-70" style="font-size: 24px; line-height: 1; text-decoration: none;" title="View Datasheet">📄</a>
            </td>`
          : `<td class="border border-gray-300 px-4 py-2 text-center align-middle" style="vertical-align: middle;">
              <span class="inline-block cursor-not-allowed opacity-50" style="font-size: 24px; line-height: 1;" title="Datasheet not available">📄</span>
            </td>`;

        const enhancedCells = [
          processedCells[0], // First cell (Part Name)
          datasheetCell, // Datasheet emoji
          ...processedCells.slice(1) // Rest of cells
        ];

        return `<tr>${enhancedCells.join('')}</tr>`;
      }).join('');

    return `<table class="w-full border-collapse border border-gray-300 my-4 min-w-full">
      <thead><tr>${headerHtml}</tr></thead>
      <tbody>${rowsHtml}</tbody>
    </table>`;
  };

  const processedContent = useMemo(() => {
    if (!responseText) return '';

    // Convert basic markdown to HTML
    let processed = convertMarkdownToHtml(responseText);

    // Wrap in paragraphs
    if (!processed.includes('<p>')) {
      processed = '<p class="mb-4">' + processed + '</p>';
    }

    return processed;
  }, [responseText]);

  // Parse products from table if available
  const products = useMemo(() => {
    if (!responseText) return [];

    const hasTable = hasTableStructure(responseText);
    if (!hasTable) return [];

    return parseTableToProducts(responseText);
  }, [responseText]);

  // Extract dynamic column names from AI response
  const columns = useMemo(() => {
    if (!responseText) return [];

    const hasTable = hasTableStructure(responseText);
    if (!hasTable) return [];

    return extractColumnNames(responseText);
  }, [responseText]);

  const shouldShowProductTable = products.length > 0;

  // Extract suppliers using AI - DISABLED IN DEMO MODE
  const [extractedSuppliers, setExtractedSuppliers] = useState<string[]>([]);
  const [isExtractingSuppliers, setIsExtractingSuppliers] = useState(false);

  useEffect(() => {
    if (!responseText) return;

    // Demo mode: No supplier extraction needed
    // RFQ functionality is disabled for this demo
    setExtractedSuppliers([]);
    setIsExtractingSuppliers(false);
  }, [responseText]);

  const availableSuppliers = extractedSuppliers;

  const handleGenerateRfq = async () => {
    if (!originalQuery || selectedSuppliers.length === 0) return;
    
    try {
      await rfqMutation.mutateAsync({
        query: originalQuery,
        partDetails: responseText,
        usSuppliersOnly: true,
        selectedSuppliers: selectedSuppliers
      });
      setRfqStep('details'); // Go to RFQ details after suppliers selected
      
      // Auto-scroll to bottom after RFQ generation
      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: 'smooth'
        });
      }, 100); // Small delay to ensure content has rendered
    } catch (error) {
      console.error('RFQ generation failed:', error);
    }
  };


  const handleSupplierToggle = (supplier: string) => {
    setSelectedSuppliers(prev => 
      prev.includes(supplier) 
        ? prev.filter(s => s !== supplier)
        : [...prev, supplier]
    );
  };

  const handleProceedToDetails = () => {
    setRfqStep('details');
  };

  const handleGenerateTemplates = async () => {
    if (!rfqDetails.quantity || !rfqDetails.timeline) {
      alert('Please fill in all required fields');
      return;
    }
    
    try {
      await rfqMutation.mutateAsync({
        query: originalQuery || '',
        partDetails: responseText,
        usSuppliersOnly: usSuppliersOnly,
        rfqDetails: rfqDetails,
        selectedSuppliers: selectedSuppliers
      });
      setRfqStep('templates');
    } catch (error) {
      console.error('RFQ generation failed:', error);
      if (error instanceof Error && error.message.includes('rate limit')) {
        alert('Rate limit exceeded. Please try again in a few minutes or upgrade your Groq plan.');
      } else {
        alert(`RFQ generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
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
    // AgentMail will handle the actual email sending via the API route
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
    if (result.success && originalQuery) {
      try {
        await createRFQMutation.mutateAsync({
          originalQuery,
          partDetails: responseText,
          supplierName: emailModalState.supplierName,
          supplierEmail: recipientEmail,
          senderEmail,
          emailTemplate: emailModalState.emailTemplate,
          followUpType: 'auto' // Enable automatic follow-ups
        });
        console.log('RFQ tracking record created successfully');
      } catch (error) {
        console.error('Failed to create RFQ tracking record:', error);
        // Don't throw - email was sent successfully, tracking is optional
      }
    }

    return result;
  };

  if (!responseText) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No content to display</p>
      </div>
    );
  }


  return (
    <div className="prose max-w-none w-full">
      {/* Professional Product Table - Show if we have parsed products */}
      {shouldShowProductTable ? (
        <div className="mb-8">
          <ProductTable
            products={products}
            columns={columns}
            usSuppliersOnly={usSuppliersOnly}
            onUsSuppliersOnlyChange={onUsSuppliersOnlyChange}
          />
          <RFQCart />
        </div>
      ) : (
        // Fallback to original HTML table rendering
        <div
          className="text-foreground leading-relaxed"
          dangerouslySetInnerHTML={{ __html: processedContent }}
        />
      )}

      {/* Supplier Selection Section */}
      {originalQuery && !isExtractingSuppliers && availableSuppliers.length > 0 && !shouldShowProductTable && (
        <div className="mt-8 p-6 border border-border rounded-lg bg-surface">
          <h3 className="text-xl font-bold mb-4">Select Suppliers to Contact</h3>
          <p className="text-muted-foreground mb-4">
            Choose which suppliers you'd like to request quotes from:
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-6">
            {availableSuppliers.map((supplier) => (
              <Button
                key={supplier}
                variant={selectedSuppliers.includes(supplier) ? "default" : "outline"}
                onClick={() => handleSupplierToggle(supplier)}
                className="text-left justify-start"
              >
                {supplier}
              </Button>
            ))}
          </div>
          {selectedSuppliers.length > 0 && (
            <Button 
              onClick={handleGenerateRfq}
              disabled={rfqMutation.isPending}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {rfqMutation.isPending ? 'Generating...' : `Generate RFQ (${selectedSuppliers.length} suppliers)`}
            </Button>
          )}
        </div>
      )}

      {/* RFQ Section - Only show after suppliers selected and RFQ generated */}
      {originalQuery && rfqStep !== 'prompt' && (
        <div className="mt-8 p-6 border border-border rounded-lg bg-surface">
          <h3 className="text-xl font-bold mb-4">Request for Quote (RFQ)</h3>


          {rfqStep === 'suppliers' && availableSuppliers.length === 0 && (
            <div className="space-y-4">
              <h4 className="font-semibold">No Suppliers Found</h4>
              <p className="text-sm text-muted-foreground">
                No suppliers were detected in the search results. You may need to search for more specific parts or contact suppliers directly.
              </p>
              <Button 
                onClick={() => setRfqStep('prompt')}
                variant="outline"
              >
                Back to Search
              </Button>
            </div>
          )}

          {rfqStep === 'suppliers' && availableSuppliers.length > 0 && (
            <div className="space-y-4">
              <h4 className="font-semibold">Select Suppliers to Contact</h4>
              <p className="text-sm text-muted-foreground">
                Choose which suppliers you'd like to request quotes from:
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {availableSuppliers.map((supplier) => (
                  <Button
                    key={supplier}
                    variant={selectedSuppliers.includes(supplier) ? "default" : "outline"}
                    onClick={() => handleSupplierToggle(supplier)}
                    className="text-left justify-start"
                  >
                    {supplier}
                  </Button>
                ))}
              </div>
              {selectedSuppliers.length > 0 && (
                <div className="pt-4">
                  <Button 
                    onClick={handleProceedToDetails}
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Continue to RFQ Details ({selectedSuppliers.length} suppliers)
                  </Button>
                </div>
              )}
            </div>
          )}

          {rfqStep === 'details' && (
            <div className="space-y-6">
              <h4 className="font-semibold">RFQ Details</h4>
              <p className="text-sm text-muted-foreground">
                Please provide the following information to generate personalized RFQ emails:
              </p>
              
              <div className="grid gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
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
                  <label className="block text-sm font-medium mb-2">
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
                  <label className="block text-sm font-medium mb-2">
                    Additional Requirements (Optional)
                  </label>
                  <textarea
                    placeholder="e.g., Certifications needed, specific mounting requirements, testing documentation..."
                    value={rfqDetails.additionalRequirements}
                    onChange={(e) => setRfqDetails(prev => ({ ...prev, additionalRequirements: e.target.value }))}
                    className="w-full min-h-[80px] px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
              
              <div className="flex gap-4">
                <Button
                  onClick={() => setRfqStep('suppliers')}
                  variant="outline"
                >
                  Back to Suppliers
                </Button>
                <Button
                  onClick={handleGenerateTemplates}
                  disabled={!rfqDetails.quantity || !rfqDetails.timeline || rfqMutation.isPending}
                  className="bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  {rfqMutation.isPending ? 'Generating...' : `Generate RFQ Emails (${selectedSuppliers.length} suppliers)`}
                </Button>
              </div>
            </div>
          )}

          {rfqStep === 'templates' && rfqMutation.data && (
            <div className="space-y-6">
              <h4 className="font-semibold">AI-Generated RFQ Email Templates</h4>
              <p className="text-sm text-muted-foreground">
                AI-generated email templates for each selected supplier:
              </p>
              
              {selectedSuppliers.map((supplier) => {
                // Extract individual email template for this specific supplier
                const fullContent = rfqMutation.data?.rfqContent || '';
                
                // Look for this supplier's specific template using the === SupplierName Email Template === format
                const supplierRegex = new RegExp(`=== ${supplier} Email Template ===[\\s\\S]*?(?====|$)`, 'i');
                const supplierMatch = fullContent.match(supplierRegex);
                
                let emailTemplate = '';
                if (supplierMatch) {
                  // Extract content between the === markers
                  emailTemplate = supplierMatch[0]
                    .replace(`=== ${supplier} Email Template ===`, '')
                    .replace(/===$/, '')
                    .trim();
                } else {
                  // Fallback: use generic template and personalize it
                  const genericMatch = fullContent.match(/=== Email Template ===[\\s\\S]*?(?====|$)/);
                  if (genericMatch) {
                    emailTemplate = genericMatch[0]
                      .replace('=== Email Template ===', '')
                      .replace(/===$/, '')
                      .replace(/Dear Supplier/g, `Dear ${supplier} Team`)
                      .trim();
                  } else {
                    // Last fallback: use full content
                    emailTemplate = fullContent;
                  }
                }
                
                const personalizedTemplate = emailTemplate;
                
                return (
                  <div key={supplier} className="border border-border rounded-lg p-4">
                    <div className="mb-3">
                      <Badge variant="outline">{supplier}</Badge>
                    </div>
                    <pre className="text-sm bg-muted p-3 rounded whitespace-pre-wrap overflow-x-auto mb-3">
                      {personalizedTemplate || 'Template not available'}
                    </pre>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(personalizedTemplate)}
                      >
                        Copy Template
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleSendEmail(supplier, personalizedTemplate)}
                        className="bg-primary text-primary-foreground hover:bg-primary/90"
                      >
                        Send Email
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Email Validation Modal */}
      <EmailValidationModal
        isOpen={emailModalState.isOpen}
        onClose={handleEmailModalClose}
        onSendEmail={sendEmailViaAgentMail}
        supplierName={emailModalState.supplierName}
        emailTemplate={emailModalState.emailTemplate}
      />
    </div>
  );
};