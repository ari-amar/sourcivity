# Professional Product Search & RFQ Cart UI

## Overview

This document describes the new professional product table and RFQ cart interface added to Sourcivity. The UI provides an enterprise-grade B2B experience for browsing industrial parts and managing quote requests.

## Components

### 1. ProductTable Component

**Location**: `components/ProductTable.tsx`

A full-width, sortable data table that displays industrial parts with the following features:

#### Columns
1. **Selection** (40px) - Checkbox for row selection
2. **Part Name & Supplier Type** (~300px) - Part name as clickable link + supplier info
3. **Material** (~200px) - Material specification
4. **Thread Size** (~120px) - Thread dimensions
5. **Load Rating** (~150px) - Dual format (lb/N)
6. **Operating Temperature** (~250px) - Temperature range (F/C)
7. **Actions** (~100px) - RFQ button

#### Features
- **Sortable columns** - Click headers to sort (with visual indicators)
- **Row selection** - Individual checkboxes + "Select All" header checkbox
- **Hover states** - Subtle background color on hover
- **Selected state** - Blue tint for selected rows
- **RFQ button states**:
  - Default: Blue "RFQ" button
  - Added: Green "Added" button (disabled)
- **Accessibility**: ARIA labels, keyboard navigation, semantic HTML

#### Styling
- Clean borders (#E9ECEF)
- Header background (#F1F3F5)
- Primary blue (#1976D2) for links and actions
- Success green (#28A745) for "Added" state
- Responsive with horizontal scroll on small screens

### 2. RFQCart Component

**Location**: `components/RFQCart.tsx`

A slide-up drawer that appears from the bottom when items are added to the cart.

#### Features
- **Auto-open**: Slides up when first item is added
- **Header**:
  - Shopping cart icon in blue circle
  - Title with item count
  - "Clear Cart" and "Proceed to RFQ" buttons
- **Cart Items**:
  - Scrollable list (max 70vh height)
  - Each item shows: part name, supplier, material, thread size, load rating, temperature
  - Remove button (X) for each item
- **Footer**:
  - Summary message
  - Primary "Continue" button with item count
- **Animations**:
  - Smooth 300ms slide-in/out
  - Semi-transparent backdrop
  - Click outside to close

#### Styling
- White background with shadow
- Border-top for separation
- Gray-50 footer background
- 3-column grid for item details

### 3. RFQ Cart Context

**Location**: `lib/rfqCartContext.tsx`

Global state management for the RFQ cart using React Context.

#### API
```typescript
const {
  cartItems,      // RFQCartItem[]
  addToCart,      // (product: ProductItem) => void
  removeFromCart, // (productId: string) => void
  clearCart,      // () => void
  isInCart,       // (productId: string) => boolean
  cartCount       // number
} = useRFQCart();
```

#### Setup
Wrap your app with `<RFQCartProvider>` in `app/providers.tsx`

### 4. Table Parser Utility

**Location**: `lib/tableParser.ts`

Converts AI-generated markdown tables into structured ProductItem objects.

#### Functions
- `parseTableToProducts(markdownTable: string): ProductItem[]` - Main parser
- `hasTableStructure(text: string): boolean` - Detects if text contains a table

#### Parsing Logic
1. Splits markdown by lines
2. Identifies table rows (containing `|`)
3. Extracts data from each cell:
   - Part name & URL from `[Name (Type)](url)` format
   - Load rating from `XXX lb (YYY N)` format
   - Temperature from `-XX°F to YY°F (-XX°C to YY°C)` format
4. Generates unique IDs for each product
5. Determines country flag from URL domain

## Integration

### SearchResultsContent Component

The ProductTable is automatically shown when the AI response contains a parseable table structure.

**Flow**:
1. AI generates markdown table in response
2. `hasTableStructure()` detects table presence
3. `parseTableToProducts()` converts to ProductItem array
4. ProductTable renders with parsed data
5. RFQCart mounts (hidden until items added)
6. User interactions update cart state via context

**Fallback**: If no table detected, original HTML rendering is used.

## Type Definitions

**Location**: `lib/types.ts`

```typescript
interface ProductItem {
  id: string;
  partName: string;
  partUrl: string;
  supplierType: string;
  supplierFlag: string;
  hasSpecSheet: boolean;
  material: string;
  threadSize: string;
  loadRating: { lb: number; n: number };
  tempRange: {
    min: { f: number; c: number };
    max: { f: number; c: number };
  };
}

interface RFQCartItem extends ProductItem {
  addedAt: string;
}
```

## Color Palette

Following the design specification:

- **Primary Blue**: #1976D2 (buttons, links)
- **Secondary Blue**: #E3F2FD (hover, selections)
- **Success Green**: #28A745 ("Added" state)
- **Grays**:
  - #F8F9FA (page background)
  - #F1F3F5 (table header)
  - #E9ECEF (borders)
  - #6C757D (secondary text)
- **Text**: #212529 (primary)
- **White**: #FFFFFF (surfaces)

## Accessibility Features

✅ **WCAG AA Compliant**
- Semantic HTML structure (`<table>`, `<th>`, `<td>`)
- ARIA labels on all interactive elements
- Keyboard navigation support:
  - Tab/Shift+Tab: Navigate between elements
  - Space/Enter: Toggle checkboxes and buttons
  - Escape: Close cart drawer
- Focus visible states on all interactive elements
- Sufficient color contrast ratios
- Screen reader friendly labels

## Sample Data

**Location**: `lib/sampleProducts.ts`

Contains:
- `sampleProducts` - Array of ProductItem objects for testing
- `sampleMarkdownTable` - Example AI-generated markdown table

Use these for development and testing the UI without hitting the AI API.

## Usage Example

```tsx
import { ProductTable } from '@/components/ProductTable';
import { RFQCart } from '@/components/RFQCart';
import { parseTableToProducts } from '@/lib/tableParser';

function SearchResults({ aiResponse }: { aiResponse: string }) {
  const products = parseTableToProducts(aiResponse);

  return (
    <>
      <ProductTable products={products} />
      <RFQCart />
    </>
  );
}
```

## Testing Checklist

- [ ] Table renders correctly with all columns
- [ ] Sorting works on all sortable columns
- [ ] Row selection (individual and "select all") works
- [ ] RFQ button adds items to cart
- [ ] Cart slides up when items added
- [ ] Cart displays correct item count and details
- [ ] Remove from cart works
- [ ] Clear cart empties all items
- [ ] Backdrop click closes cart
- [ ] Animations are smooth
- [ ] Keyboard navigation works
- [ ] Screen reader announces changes
- [ ] Mobile responsive (table scrolls horizontally)
- [ ] Works with real AI-generated tables

## Future Enhancements

1. **Datasheet Integration** - Make 📄 icon link to actual spec sheets
2. **Bulk Actions** - Use selected rows for batch operations
3. **Persist Cart** - Save cart to localStorage
4. **Export Cart** - Download cart as CSV/PDF
5. **Compare Products** - Side-by-side comparison view
6. **Filters** - Add column filters for advanced search
7. **Pagination** - Handle large result sets
8. **Virtual Scrolling** - Optimize performance for 100+ rows

## Notes

- The ProductTable only renders when `hasTableStructure()` returns true
- Original HTML table rendering is maintained as fallback
- Cart state is managed globally via React Context
- All animations use CSS transitions for performance
- Component uses existing Button and Input components for consistency
