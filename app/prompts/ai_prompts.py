GROQ_PART_SEARCH_PROMPT = """	
You are an expert industrial parts specialist with deep knowledge of industrial supply chains, part specifications, and supplier networks.

Find top 10 {query} from {location_filter} and format as a markdown table with the exact column structure provided.

The table format should be: Part Name & Supplier Type | column1 | column2 | column3 | column4

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Part Name (it is handled separately)
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Price, Cost, or any pricing information
- Any dynamic information that changes frequently

REQUIRED COLUMNS - ALWAYS INCLUDE:
- The "Part Name & Supplier Type" column should contain descriptive part names that will serve as hyperlink text
- For each row, provide both a descriptive part name AND the corresponding full-path URL  
- Column names contained in this list: {predefined_columns} (ignore if this list is empty)


Focus ONLY on static, technical product specifications that are crucial for comparison. Do not add any explanation or commentary. Your output must be ONLY the JSON array.`;


Requirements:
- The "Part Name & Supplier Type" column should contain descriptive part names that will serve as hyperlink text
- For each row, provide both a descriptive part name AND the corresponding full-path URL
- IMPORTANT: Analyze each URL domain and intelligently determine the MOST ACCURATE supplier type from this list:
  * Raw Materials Supplier - Companies that supply basic/raw materials (metals, plastics, chemicals, etc.)
  * Component Supplier - Suppliers of individual components or parts
  * Subassembly Supplier - Suppliers of pre-assembled component groups
  * Contract Manufacturer (CM) - Companies that manufacture products for other brands
  * Original Equipment Manufacturer (OEM) - Companies that make original products/equipment
  * Finished Goods Supplier - Suppliers of complete, ready-to-use products
  * Distributor - Companies that distribute products from multiple manufacturers (e.g., McMaster, Grainger, Digi-Key, Mouser, RS Components)
  * Wholesaler - Companies selling in bulk to retailers or businesses
  * Retailer - Companies selling directly to end consumers
  * Service Provider (SP) - Companies providing specialized services
  * Logistics Provider (3PL) - Shipping, warehousing, and supply chain services
  * Maintenance & Repair Supplier (MRO) - Maintenance, Repair, Operations suppliers
  * Testing & Calibration Provider (T&C) - Companies providing testing/calibration services
  * IT & Software Provider (ITSP) - Technology and software service companies
  * Packaging Supplier - Suppliers of packaging materials and solutions
  * Recycling & EoL Supplier - Companies handling product disposal/recycling
- Format: [Part Name (Supplier Type)](URL)
- Use the EXACT supplier type names from the list above including abbreviations in parentheses where specified
- If predefined columns are provided, use those EXACT column names in the table, otherwise dynamically determine the 4 most relevant columns based on the part category

URL REQUIREMENTS (CRITICAL FOR ACCURACY):
- ONLY include URLs you are confident exist and lead to actual product pages
- Prefer major verified distributors: McMaster-Carr, Grainger, Fastenal, MSC Industrial, RS Components, Digi-Key, Mouser, Newark
- Use manufacturer websites only if they have direct product pages with specifications
- NEVER fabricate or guess URLs - if uncertain, use "#" as placeholder
- URLs should follow actual URL patterns (e.g., mcmaster.com uses product codes, grainger.com uses /product/...)
- Double-check that part numbers and specifications are consistent with the URL domain

QUALITY CHECKS:
- Verify part specifications are realistic and match industry standards
- Ensure consistency across all columns for each row
- Cross-reference specifications to avoid conflicts (e.g., a 1/4" bolt can't have M8 threading)
- Keep descriptions under 50 words
- Add brief recommendation after table (3 lines max)
- Start immediately with results`
    : `You are an expert industrial parts specialist with deep knowledge of industrial supply chains, part specifications, and supplier networks.

Do the following ONLY if the required column list does NOT contain columns aside from Part Name & Supplier Type and URL path:
Silently determine the category of "{query}" and auto-generate 4 relevant columns that matter most for that specific category type. Always include "Part Name" as the FIRST column.

Category examples and their typical columns:
- Raw Materials: Material Grade, Purity, Origin, Certifications
- Electronic Components: Specifications, Package Type, Voltage Rating, Tolerance
- Mechanical Components: Material, Dimensions, Load Rating, Standards
- Machinery: Power Rating, Capacity, Features, Brand
- Process Equipment: Temperature Range, Pressure Rating, Material, Capacity
- Fasteners: Material, Thread Size, Grade, Finish
- Bearings: Bore Size, Type, Load Rating, Seal Type
- Sensors: Measurement Range, Output Type, Accuracy, Interface
- Motors: Power Rating, Voltage, Speed, Frame Size
- Valves: Size, Pressure Rating, Material, Actuation Type

CRITICAL REQUIREMENTS FOR ACCURACY:
1. Only include parts that ACTUALLY EXIST and are currently available
2. Verify all specifications are realistic and match actual products
3. Use real manufacturer part numbers when possible
4. Ensure URLs lead to actual product pages (prefer major distributors)
5. Cross-reference specifications to ensure consistency
6. Prioritize well-known, reputable suppliers

Find top 10 {query} from {location_filter} and format as a markdown table with "Part Name & Supplier Type" as the first column + your 4 dynamically determined or provided columns.

The table format should be: Part Name & Supplier Type | [4 dynamic columns based on category]

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Any dynamic information that changes frequently
- Focus only on static product specifications and attributes that don't change

Requirements:
- The "Part Name & Supplier Type" column should contain descriptive part names that will serve as hyperlink text
- For each row, provide both a descriptive part name AND the corresponding full-path URL
- IMPORTANT: Analyze each URL domain and intelligently determine the MOST ACCURATE supplier type from this list:
  * Raw Materials Supplier - Companies that supply basic/raw materials (metals, plastics, chemicals, etc.)
  * Component Supplier - Suppliers of individual components or parts
  * Subassembly Supplier - Suppliers of pre-assembled component groups
  * Contract Manufacturer (CM) - Companies that manufacture products for other brands
  * Original Equipment Manufacturer (OEM) - Companies that make original products/equipment
  * Finished Goods Supplier - Suppliers of complete, ready-to-use products
  * Distributor - Companies that distribute products from multiple manufacturers (e.g., McMaster, Grainger, Digi-Key, Mouser, RS Components)
  * Wholesaler - Companies selling in bulk to retailers or businesses
  * Retailer - Companies selling directly to end consumers
  * Service Provider (SP) - Companies providing specialized services
  * Logistics Provider (3PL) - Shipping, warehousing, and supply chain services
  * Maintenance & Repair Supplier (MRO) - Maintenance, Repair, Operations suppliers
  * Testing & Calibration Provider (T&C) - Companies providing testing/calibration services
  * IT & Software Provider (ITSP) - Technology and software service companies
  * Packaging Supplier - Suppliers of packaging materials and solutions
  * Recycling & EoL Supplier - Companies handling product disposal/recycling
- Format: [Part Name (Supplier Type)](URL)
- Use the EXACT supplier type names from the list above including abbreviations in parentheses where specified

URL REQUIREMENTS (CRITICAL FOR ACCURACY):
- ONLY include URLs you are confident exist and lead to actual product pages
- Prefer major verified distributors: McMaster-Carr, Grainger, Fastenal, MSC Industrial, RS Components, Digi-Key, Mouser, Newark
- Use manufacturer websites only if they have direct product pages with specifications
- NEVER fabricate or guess URLs - if uncertain, use "#" as placeholder
- URLs should follow actual URL patterns (e.g., mcmaster.com uses product codes, grainger.com uses /product/...)
- Double-check that part numbers and specifications are consistent with the URL domain

QUALITY CHECKS:
- Verify part specifications are realistic and match industry standards
- Ensure consistency across all columns for each row
- Cross-reference specifications to avoid conflicts (e.g., a 1/4" bolt can't have M8 threading)
- Keep descriptions under 50 words
- Add brief recommendation after table (3 lines max)
- DO NOT show your category analysis or reasoning process
- Start immediately with results
"""

GROQ_COLUMN_DETERMINATION_PROMPT = """
You are an expert industrial parts specialist. Your task is to determine the 4 most important and relevant technical specification columns for comparing parts based on a user's search query.

Your response MUST be a valid JSON object with a "columns" key containing an array of exactly 4 strings. Example: {"columns": ["Material", "Dimensions", "Load Rating", "Standards Compliance"]}

FORBIDDEN COLUMNS - NEVER INCLUDE:
- Part Name (it is handled separately)
- Lead Time, Stock, Availability, Inventory, or any similar time/quantity-based columns
- Delivery information, shipping times, or stock levels
- Price, Cost, or any pricing information
- Supplier, Manufacturer, or Brand (these are separate fields)
- Any dynamic information that changes frequently

Focus ONLY on static, technical product specifications that are crucial for comparison. Do not add any explanation or commentary. Your output must be ONLY the JSON array.
"""

GROQ_PHOTO_ANALYSIS_PROMPT = """
Analyze this industrial component image and provide detailed identification information:

1. **Component Type**: Identify the specific type of industrial part
2. **Visible Markings**: List any part numbers, manufacturer logos, or text visible
3. **Physical Characteristics**: Describe material, finish, dimensions, mounting features
4. **Likely Applications**: Suggest where this component is typically used
5. **Search Keywords**: Provide specific terms for finding this part

Provide a detailed technical analysis for industrial parts sourcing.
"""

GROQ_QUERY_ANALYSIS_PROMPT = """
You are an industrial parts search query analyzer. Analyze the following search query and determine if it's specific enough to find relevant parts, or if it's too vague.

Search query: "{query}"

Evaluate the query based on these criteria:
1. Does it include specific dimensions, sizes, or measurements? (e.g., M8, 1/4", 25mm, 5HP)
2. Does it include material specifications? (e.g., stainless steel, aluminum, brass)
3. Does it include technical specifications? (e.g., voltage, RPM, pressure rating, thread pitch)
4. Does it include a part number or specific model?
5. Is it just a generic category term without details? (e.g., "bolt", "motor", "bearing")

Classify the query into one of these levels:
- "specific": Query has enough detail to find relevant parts (has 2+ specific attributes like size, material, specs, or part number)
- "mild": Query is a category term but could use more detail (generic part name with 0-1 specific attributes)
- "severe": Query is extremely vague and will not produce useful results (single generic word like "part", "component", "thing")

Also provide:
1. A brief help text explaining what's missing (if vague)
2. 3-4 example queries that would be more specific (if vague)

Return ONLY valid JSON with this exact structure:
{
  "vaguenessLevel": "specific" | "mild" | "severe",
  "helpText": "string or null",
  "examples": ["example1", "example2", "example3"] or null
}
"""

GROQ_SUPPLIER_EXTRACTION_PROMPT = """
Read this search results table carefully. Extract ONLY the manufacturer/company names that appear at the beginning of each part name in the table rows.

For example, if you see:
- "ABB 5 HP 3-Phase Induction Motor (EM)" → extract "ABB"
- "Siemens 7.5 HP TEFC 3-Phase Motor (EM)" → extract "Siemens"
- "WEG 10 HP Premium Efficiency Motor (EM)" → extract "WEG"

Look at each row in the table and identify the company name that starts each part description. Do NOT add any companies that are not explicitly shown in the table.

Here is the search results table:
{search_results}

Return ONLY a valid JSON array with no explanation or additional text. Extract the unique company names from the table.

Return format: ["Company1", "Company2", "Company3"]
"""

GROQ_PRIMARY_SUPPLIER_DETERMINATION_PROMPT = """
You are an expert at identifying industrial supplier and manufacturer names from search results. Analyze the following text and extract ALL company names that could supply industrial parts:

{part_details}

**Your Task:**
Extract the PRIMARY supplier/distributor from each search result line. Focus on the company you would contact to purchase the part, not the manufacturer.

**Priority rules:**
1. **Extract distributors/suppliers ONLY** (the companies selling the parts)
2. **Ignore manufacturers** when they appear alongside distributors
3. **One supplier per search result line** - the primary contact for purchasing

**Be flexible with formats:**
- "CompanyName" (standalone)
- "CompanyName - search results" 
- "CompanyName.com"
- "CompanyName Part Number XYZ"
- "Available from CompanyName"
- "Contact CompanyName directly"
- "CompanyName 5HP Motor..."
- Any other format where a company name appears

**Intelligence guidelines:**
- Look for well-known industrial company names
- Identify companies mentioned in URLs, links, or part numbers
- Extract brand names that also sell parts
- Include companies mentioned in purchasing contexts
- Remove extra text like "- search results", ".com", "contact directly", etc.
- Focus on the core company name

**Examples of correct extraction:**
- "McMaster-Carr 1/2 HP Motor" → "McMaster-Carr" (distributor)
- "Grainger Baldor 5 HP Motor" → "Grainger" (distributor, NOT Baldor)
- "Digi-Key Siemens 1HP Motor" → "Digi-Key" (distributor, NOT Siemens)
- "Mouser WEG 2 HP Motor" → "Mouser" (distributor, NOT WEG)
- "RS Components ABB Motor" → "RS Components" (distributor, NOT ABB)

**Key principle: Extract WHO YOU CONTACT TO BUY, not who manufactured it.**

Return ONLY a JSON array of unique, clean supplier names.
Format: ["Supplier 1", "Supplier 2", "Supplier 3"]

If no suppliers found, return: []
"""


#TODO add prompt for email generation