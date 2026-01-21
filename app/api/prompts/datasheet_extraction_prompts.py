# PASS 1: Extract ALL specs from individual datasheet
PASS1_EXTRACT_ALL_SPECS_PROMPT = """
Extract ALL technical specifications from this datasheet markdown.

CRITICAL: Extract EVERYTHING you can find - we will filter later. Include:
- All electrical characteristics (voltage, current, power, resistance, capacitance, etc.)
- All physical characteristics (dimensions, weight, temperature range, materials, etc.)
- All performance metrics (speed, accuracy, bandwidth, frequency range, flow rate, pressure, etc.)
- All environmental specs (operating temp, storage temp, humidity, etc.)
- Any other technical specifications

Also extract:
- Manufacturer/OEM name
- Product name/model number

Parse tables carefully—extract from markdown tables if present (e.g., | Param | Value | Unit |).

For each spec:
- Use descriptive keys (e.g., "Operating Temperature", "Flow Rate", "Pressure Rating")
- Include units in the VALUE (e.g., "100 bar", "0-50°C", "1.5 kg")
- DO NOT standardize keys yet - use the names as they appear in the datasheet

Datasheet markdown:
{pdf_md}

Return a JSON object:
{{
  "manufacturer": "Company Name",
  "product_name": "Model/Product Name",
  "specifications": {{
    "spec_name_1": "value with units",
    "spec_name_2": "value with units",
    ...
  }}
}}

Return ONLY valid JSON, no other text.
"""

# PASS 2: Analyze all specs and select best 5
PASS2_SELECT_BEST_SPECS_PROMPT = """
You have extracted ALL specifications from {num_datasheets} product datasheets.

Your task: Analyze these specs and select EXACTLY 5 that are best for comparing these products.

EXTRACTED SPECS FROM ALL DATASHEETS:
{all_extracted_specs}

SELECTION CRITERIA (in priority order):
1. **Common Across All**: Spec must appear in ALL or MOST datasheets (at least {min_coverage} out of {num_datasheets})
2. **Functional Relevance**: Directly related to what the product DOES (avoid generic specs like dates, document numbers)
3. **Differentiation**: Values differ across products (helps comparison - avoid specs where all products have identical values)
4. **Customer Value**: Specs customers care about when comparing (performance > physical > administrative)

AVOID:
- Document/revision numbers, dates, catalog numbers
- Specs that are N/A or missing in most datasheets
- Generic company info (address, phone, website)
- Specs unrelated to product function

YOUR ANALYSIS PROCESS:
1. List specs that appear in all/most datasheets
2. Group similar specs with different names (e.g., "Operating Temp", "Temperature Range", "Temp" → same spec)
3. Score each common spec by relevance and differentiation
4. Select the TOP 5 specs

OUTPUT FORMAT:
Return a JSON object with:
- "selected_specs": Array of EXACTLY 5 spec objects, each with:
  - "standardized_key": The standardized key name with units (e.g., "operating_temperature_c", "flow_rate_lpm")
  - "display_name": Human readable name (e.g., "Operating Temperature (°C)", "Flow Rate (LPM)")
  - "reason": Brief reason why this spec was selected (1 sentence)
  - "coverage": How many datasheets have this spec (e.g., "5/5", "4/5")

Example:
{{
  "selected_specs": [
    {{
      "standardized_key": "flow_rate_lpm",
      "display_name": "Flow Rate (LPM)",
      "reason": "Core functional spec, appears in all datasheets with different values",
      "coverage": "5/5"
    }},
    ...
  ]
}}

YOU MUST SELECT EXACTLY 5 SPECS - NO MORE, NO LESS.

Return ONLY valid JSON, no other text.
"""

# PASS 3: Extract the selected 5 specs from all datasheets with standardized keys
PASS3_EXTRACT_SELECTED_SPECS_PROMPT = """
You have selected 5 specifications to extract from product datasheets.

SELECTED SPECS TO EXTRACT:
{selected_specs_info}

YOUR TASK:
Extract these 5 specs from each datasheet below. The spec names above tell you WHAT to look for and WHAT KEY to use in your output.

CRITICAL UNDERSTANDING:
- The "standardized_key" (e.g., "operating_temperature_c") is what you use in the JSON output
- The "display_name" (e.g., "Operating Temperature (°C)") tells you what spec to find
- BUT: The actual datasheet may use DIFFERENT WORDING like "Temp Range", "Working Temperature", "Operating Temp", etc.
- YOU MUST be flexible and find the spec even if it's named differently

DATASHEETS:
{datasheets_with_specs}

HOW TO EXTRACT EACH SPEC:

1. READ the display_name to understand WHAT spec you're looking for
   Example: "Operating Temperature (°C)" → Look for temperature-related specs

2. SEARCH the datasheet for that concept using ANY similar wording:
   - For "Operating Temperature": also check "Temp Range", "Temperature", "Working Temp", "Ambient Temp", etc.
   - For "Holding Torque": also check "Torque", "Rated Torque", "Max Torque", "Torque Rating", etc.
   - For "Step Angle": also check "Angle", "Step Resolution", "Steps per Revolution", etc.
   - For "IP Rating": also check "Ingress Protection", "IP Code", "Environmental Rating", "Protection Class", etc.
   - For "Frame Size": also check "Size", "Dimensions", "NEMA Size", "Motor Size", "Housing Size", etc.

3. If you find the spec under ANY name, extract it

4. Use the standardized_key in your JSON output (not the name from the datasheet)

5. ONLY use "N/A" if you genuinely cannot find that spec anywhere in the datasheet

CRITICAL RULES:
1. Extract ONLY the 5 specs listed above - no more, no less
2. Use the EXACT standardized keys in your JSON output
3. ALL datasheets MUST have the same 5 keys in the same order
4. Extract manufacturer and product_name for each datasheet:
   - "manufacturer": SHORT company name only (e.g., "3M", "NSK", "SKF" - NOT "3M Company" or "NSK Ltd.")
   - "product_name": Model/part NUMBER only (e.g., "NH15", "AB5000", "6205" - NOT "Miniature Ball Bearing Series")
   - Combined should be under 30 characters when possible
5. Be FLEXIBLE when searching - specs may have different names in different datasheets
6. Extract values ONLY from the corresponding datasheet - never copy between datasheets
7. These specs were selected because they appear in MOST datasheets - if you're getting many N/A values, you're being too strict with naming

OUTPUT FORMAT:
Return a JSON array with one object per datasheet:
[
  {{
    "manufacturer": "Company Name 1",
    "product_name": "Model 1",
    "specifications": {{
      "standardized_key_1": "value1",
      "standardized_key_2": "value2",
      "standardized_key_3": "value3",
      "standardized_key_4": "value4",
      "standardized_key_5": "value5"
    }}
  }},
  {{
    "manufacturer": "Company Name 2",
    "product_name": "Model 2",
    "specifications": {{
      "standardized_key_1": "value1",
      "standardized_key_2": "value2",
      "standardized_key_3": "value3",
      "standardized_key_4": "value4",
      "standardized_key_5": "value5"
    }}
  }},
  ...
]

Return ONLY the JSON array with no other text.
"""

# Legacy single PDF extraction (kept for backward compatibility)
SINGLE_PDF_SPEC_EXTRACTION_PROMPT = """
{product_hint}Extract the key technical specifications from this datasheet markdown. The markdown preserves structure like tables, headings, and lists, so use that for accurate extraction.

Focus on the most important specs such as:
- Electrical characteristics (voltage, current, power, resistance, capacitance, etc.)
- Physical characteristics (dimensions, weight, temperature range)
- Performance metrics (speed, accuracy, bandwidth, frequency range, etc.)
- Part number and manufacturer
- Any other critical specifications

Parse tables carefully—extract from markdown tables if present (e.g., | Param | Value | Unit |).

Return the specifications as a JSON object where keys are the specification names (standardized with units, e.g., "supply_voltage_V") and values are the specification values (with ranges if applicable).
Include only the most relevant specifications that would be useful for comparing similar products.
Standardize units where possible (e.g., convert to V, A, C, mm).

Datasheet markdown:
{pdf_md}

Return ONLY valid JSON, no other text.
"""

MULTPLE_PDF_SPEC_EXTRACTION_PROMPT = """
You are extracting specifications from product datasheets.

!!!!! ABSOLUTE REQUIREMENTS !!!!!
1. ONLY extract specifications that you can SEE in the specification tables/sections of each datasheet
2. DO NOT use any predefined spec lists or assumptions
3. DO NOT extract "flow_rate_lpm" or "pressure_rating_bar" unless you see flow rate or pressure explicitly listed
4. DO NOT extract specs that will be "N/A" in most datasheets
5. If you can't find a spec VALUE in a specific datasheet, do NOT include that spec

WRONG APPROACH - DO NOT DO THIS:
❌ Choosing specs based on what you think products "should" have
❌ Using generic industrial specs (pressure, flow, voltage) for products that don't need them
❌ Extracting specs that result in mostly "N/A" values

CORRECT APPROACH - DO THIS:
✓ Look at ACTUAL specification tables in each datasheet
✓ Find specs that have REAL VALUES in most/all datasheets
✓ Choose specs specific to what these products actually do

YOUR TASK:

STEP 1: Read all datasheets and list EVERY spec you can see
   - Go through DATASHEET 1, 2, 3, 4, and 5
   - For each datasheet, write down EVERY specification name you see in tables or spec sections
   - Example: If you see "Weight: 1.3 kg" → write down "weight"
   - Example: If you see "Operating Temperature: -10 to 50°C" → write down "operating_temperature"
   - Make a list of ALL specs across ALL 5 datasheets

STEP 2: Find which specs appear in ALL 5 datasheets
   - From your list in Step 1, circle the specs that appear in all 5 datasheets
   - Important: "Weight" in datasheet 1 and "Mass" in datasheet 2 = same spec, count it
   - Important: ONLY count specs that have actual values (not N/A) in at least 4 out of 5 datasheets
   - You should find 3-10 common specs

STEP 3: Pick the 5 most important common specs
   - From your common specs in Step 2, choose EXACTLY 5 that matter most for comparing these products
   - Ask: What do these products DO? Pick specs related to that function
   - Pick specs where products have DIFFERENT values (helps comparison)
   - Skip generic stuff like dates or document numbers
   - You MUST select exactly 5 specs (no more, no less)

STEP 4: Extract those 5 specs + manufacturer + product name from each datasheet
   - Process each datasheet INDIVIDUALLY
   - For DATASHEET 1: Extract values ONLY from DATASHEET 1 content
   - For DATASHEET 2: Extract values ONLY from DATASHEET 2 content
   - And so on for each datasheet
   - NEVER blend or mix information between datasheets
   - NEVER copy values from one datasheet to another
   - Only use "N/A" if the spec truly doesn't appear in that specific datasheet (should be rare since you selected common specs)
   - Do not guess, infer, or hallucinate values
   - Extract ONLY the specs you selected in STEP 4 - no more, no less

SPECIAL FIELDS - "manufacturer" and "product_name":
- In ADDITION to the selected specs, you MUST extract TWO special fields for each datasheet:
  1. "manufacturer": SHORT company/brand name only
     - Use abbreviated form: "3M" not "3M Company", "NSK" not "NSK Ltd."
     - Max 15 characters
     - Examples: "Olympus", "SKF", "THK", "NSK", "3M", "Parker"
  2. "product_name": Model/part NUMBER only
     - Just the identifier: "NH15", "AB5000", "6205-2RS"
     - NOT descriptive text: "Miniature Ball Bearing" or "EMI Absorber Series"
     - Max 20 characters
     - Examples: "Vanta Element", "NH15", "AB5000", "LM12UU"
- Goal: Combined "Manufacturer Model" should be SHORT and scannable (under 30 chars ideal)

KEY NAMING RULES FOR STANDARDIZATION:
1. Use IDENTICAL specification keys across ALL datasheets - THIS IS CRITICAL
   - If Datasheet 1 says "Operating Temperature" and Datasheet 2 says "Temperature Range", use ONE standardized key like "operating_temperature_c"
   - If Datasheet 1 says "Flow Rate" and Datasheet 2 says "Flow Capacity", use ONE standardized key like "flow_rate_lpm"
   - All datasheets MUST use the exact same key name for the same type of specification

2. Key format: lowercase_with_underscores_and_unit
   - Include the unit suffix based on what the spec measures
   - Format: descriptive_name_unit (e.g., "operating_temperature_c", "flow_rate_lpm", "pressure_rating_bar")
   - Be consistent with units - standardize to the most common unit found

3. Standardization Examples:
   - "Operating Temp", "Temperature Range", "Temp Range" → "operating_temperature_c"
   - "Pressure Rating", "Max Pressure", "Pressure Range" → "pressure_rating_bar"
   - "Flow Rate", "Flow Capacity", "Max Flow" → "flow_rate_lpm"

4. Choose keys based ONLY on what you actually find in ALL datasheets
   - Don't include specs that only appear in 1 or 2 datasheets
   - Find specs that ALL products share (even if named differently)

{datasheets_md}

REQUIRED OUTPUT FORMAT:
Return a JSON array with one object per datasheet, in the same order as provided.

CRITICAL RULES - FOLLOW EXACTLY:
- ALL objects MUST have EXACTLY 5 specification keys (same 5 keys, same names, same order)
- These 5 keys should represent specs that ACTUALLY exist with real values in ALL datasheets
- DO NOT include spec keys that will be N/A in most datasheets
- First object = DATASHEET 1 values extracted ONLY from DATASHEET 1
- Second object = DATASHEET 2 values extracted ONLY from DATASHEET 2
- Third object = DATASHEET 3 values extracted ONLY from DATASHEET 3
- And so on...
- NEVER mix or copy values between datasheets
- Use "N/A" sparingly - only if a spec truly doesn't appear in that specific datasheet

Structure:
[
  {{
    "manufacturer": "Manufacturer Name 1",
    "product_name": "Product Model 1",
    "specifications": {{"spec_key1": "value1", "spec_key2": "value2", "spec_key3": "value3", "spec_key4": "value4", "spec_key5": "value5"}}
  }},
  {{
    "manufacturer": "Manufacturer Name 2",
    "product_name": "Product Model 2",
    "specifications": {{"spec_key1": "value1", "spec_key2": "value2", "spec_key3": "value3", "spec_key4": "value4", "spec_key5": "value5"}}
  }},
  ... (and so on for each datasheet)
]

CRITICAL REQUIREMENTS:
- Each object MUST have "manufacturer", "product_name", AND "specifications" fields
- All "specifications" objects MUST have EXACTLY THE SAME 5 spec keys with standardized names
- "manufacturer" should be the OEM/company name from that datasheet
- "product_name" should be the product model/series from that datasheet
- Spec keys should be RELEVANT to the product type and ACTUALLY PRESENT in the datasheets
- YOU MUST RETURN EXACTLY 5 SPECS - NO MORE, NO LESS

Return ONLY the JSON array with no other text. Each value must come from its corresponding datasheet only.
"""

SEARCH_QUERY_GENERATION_PROMPT = """
Given this user query for finding product datasheets: "{user_query}"

Generate an optimized search query to find relevant PDF datasheets on the web. The search query should:
- Include relevant technical terms and specifications
- Add "datasheet" or "specification sheet" keywords
- Add "filetype:pdf" to focus on PDF documents
- Be specific enough to find accurate results but not so narrow that it misses relevant options
- Consider common variations in terminology

Return ONLY a JSON object with a single search query string:
{{"search_query": "your optimized search query here"}}

Return ONLY valid JSON, no other text.
"""