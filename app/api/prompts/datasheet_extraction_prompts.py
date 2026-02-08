# Batched spec extraction + normalization prompt (all PDFs in one call)
BATCHED_SPEC_EXTRACTION_PROMPT = """
You are an expert at extracting and comparing technical specifications from product datasheets.

{product_hint}

## Task
You are extracting specs from {num_pdfs} datasheets for the SAME product category.

### Step 1: Identify Common Specs
First, scan ALL PDFs and identify which specifications appear in MULTIPLE datasheets.
Different manufacturers use different names for the same property - group them.

Example: "Output Signal", "Output", "Analog Output" → all mean the same thing
Example: "Operating Temperature", "Temp Range", "Working Temperature" → all mean the same thing
Example: "Max Pressure", "Pressure Rating", "Rated Pressure" → all mean the same thing

### Step 2: Choose Normalized Names
For each common spec, pick ONE clear name to use across all products.
Prioritize the most descriptive, industry-standard terminology.

### Step 3: Extract Using Normalized Names
Extract specs from each PDF using your normalized names.
Only include specs that appear in at least 2 PDFs.
Include units in values (e.g., "100 bar", "0-50°C").

## PDFs
{pdf_contents}

## Return Format
{{
  "common_specs": ["Spec Name 1", "Spec Name 2", ...],
  "products": [
    {{
      "pdf_index": 1,
      "manufacturer": "Company Name",
      "product_name": "Model Name",
      "specs": {{
        "Spec Name 1": "value with units",
        "Spec Name 2": "value with units"
      }}
    }}
  ]
}}

IMPORTANT:
- The "common_specs" array should list the normalized spec names you chose.
- Each product's "specs" object should ONLY use keys from "common_specs".
- Skip non-technical specs (part numbers, revision dates, ordering info).

Return ONLY valid JSON.
"""

# Per-PDF spec extraction prompt
SINGLE_PDF_SPEC_EXTRACTION_PROMPT = """
{product_hint}Extract ALL technical specifications from this datasheet markdown.

Include:
- All electrical characteristics (voltage, current, power, resistance, capacitance, etc.)
- All physical characteristics (dimensions, weight, temperature range, materials, etc.)
- All performance metrics (speed, accuracy, bandwidth, frequency range, flow rate, pressure, etc.)
- All environmental specs (operating temp, storage temp, humidity, etc.)
- Any other technical specifications

Also extract:
- Manufacturer/OEM name
- Product name/model number

Parse tables carefully - extract from markdown tables if present (e.g., | Param | Value | Unit |).

For each spec:
- Use descriptive keys as they appear in the datasheet (e.g., "Operating Temperature", "Flow Rate")
- Include units in the VALUE (e.g., "100 bar", "0-50°C", "1.5 kg")

Datasheet markdown:
{pdf_md}

Return a JSON object:
{{
  "manufacturer": "Company Name",
  "product_name": "Model/Product Name",
  "specifications": {{
    "spec_name_1": "value with units",
    "spec_name_2": "value with units"
  }}
}}

Return ONLY valid JSON, no other text.
"""

# Normalize spec keys across multiple PDFs
NORMALIZE_SPEC_KEYS_PROMPT = """
You are an expert at normalizing industrial product specifications across datasheets from different manufacturers.

Different manufacturers use different terminology for the SAME physical property. Your job is to identify specs that measure the same thing and group them together.

## Key Principle
Group by the PHYSICAL PROPERTY being measured, not the exact wording. If two specs describe the same measurable characteristic of the product, they belong in the same group.

## Common Synonym Patterns in Industrial Specs

PRESSURE specifications (group these together):
- "Maximum Pressure", "Max Pressure", "Pressure Rating", "Rated Pressure", "Working Pressure", "Operating Pressure", "Design Pressure", "Proof Pressure", "Burst Pressure", "Internal Pressure", "System Pressure", "Line Pressure", "Inlet Pressure", "Outlet Pressure", "Supply Pressure"

TEMPERATURE specifications:
- "Operating Temperature", "Working Temperature", "Ambient Temperature", "Temperature Range", "Service Temperature", "Process Temperature", "Fluid Temperature", "Media Temperature"

FLOW specifications:
- "Flow Rate", "Flow Range", "Flow Capacity", "Nominal Flow", "Max Flow", "Full Scale Flow", "Measuring Range", "Control Range", "Turndown Ratio"

ACCURACY specifications:
- "Accuracy", "Measuring Accuracy", "Control Accuracy", "Precision", "Error", "Uncertainty", "Tolerance"

ELECTRICAL specifications:
- "Supply Voltage", "Operating Voltage", "Input Voltage", "Power Supply", "Voltage Range"
- "Current Draw", "Current Consumption", "Power Consumption", "Current Rating"
- "Output Signal", "Analog Output", "Signal Output", "Output Range"

PHYSICAL specifications:
- "Dimensions", "Size", "Form Factor", "Footprint"
- "Weight", "Mass", "Net Weight"
- "Materials", "Wetted Materials", "Construction Materials", "Housing Material", "Body Material"

CONNECTION specifications:
- "Process Connection", "Port Size", "Fitting", "Thread Size", "Flange Size", "Pipe Connection"
- "Electrical Connection", "Connector Type", "Cable Entry", "Terminal"

ENVIRONMENTAL specifications:
- "IP Rating", "Ingress Protection", "Protection Class", "Enclosure Rating", "NEMA Rating"
- "Humidity", "Relative Humidity", "Humidity Range"

PERFORMANCE specifications:
- "Response Time", "Settling Time", "Time Constant", "Reaction Time"
- "Repeatability", "Reproducibility", "Precision"
- "Resolution", "Sensitivity", "Threshold"

## Modifier Prefixes (treat as same base spec)
These prefixes modify the same underlying spec - group them if they refer to the same physical property:
- Max/Maximum, Min/Minimum, Nom/Nominal, Rated, Operating, Working, Typical, Default
- Static, Dynamic, Burst, Proof, Test

## Here are the spec keys from each PDF:
{pdf_keys}

## RULES:
1. Group keys that measure the SAME physical property, even if terminology differs significantly
2. Be AGGRESSIVE in grouping - if specs could plausibly measure the same thing, group them
3. Provide a standardized key name (lowercase_with_underscores)
4. Provide a human-readable display_name
5. Map each original key to its PDF number
6. Skip non-technical keys (document numbers, revision dates, part numbers, ordering info)
7. Only include groups where at least 2 PDFs share the spec

Return a JSON object:
{{
  "standardized_key_1": {{
    "display_name": "Human Readable Name",
    "pdf_matches": {{
      "1": "Original Key Name In PDF 1",
      "3": "Original Key Name In PDF 3"
    }}
  }}
}}

Return ONLY valid JSON, no other text.
"""

# Generate category-defining phrase for search filtering
# NOTE: Exa only supports ONE phrase of up to 5 words for include_text
CATEGORY_TERMS_PROMPT = """
You are an industrial product expert. For the product type "{product_query}", create a SHORT technical phrase (2-5 words) that would ONLY appear in datasheets for this EXACT product category.

This phrase will be used to filter search results, so it must be:
1. SPECIFIC to this product type (not general terms)
2. A technical term or phrase from specification tables
3. Maximum 5 words (Exa API limit)

## Examples

Product: "mass flow controller"
Phrase: "flow rate sccm"
Reasoning: sccm (standard cubic centimeters per minute) is specific to gas flow devices

Product: "linear ball bearing"
Phrase: "dynamic load rating"
Reasoning: Load ratings are specific to bearings, not shafts or guides

Product: "servo motor"
Phrase: "torque constant"
Reasoning: Torque constant (Kt) is a servo-specific specification

Product: "pressure transmitter"
Phrase: "pressure range bar"
Reasoning: Specific to pressure measurement devices

Product: "pneumatic valve"
Phrase: "flow coefficient Cv"
Reasoning: Cv rating is specific to valves

Product: "stepper motor"
Phrase: "holding torque"
Reasoning: Holding torque is stepper-specific, not found in servo specs

## Your Task

Product: "{product_query}"

Return JSON with ONE phrase (2-5 words max):
{{
  "phrase": "your technical phrase here",
  "reasoning": "Brief explanation"
}}

Return ONLY valid JSON, no other text.
"""
