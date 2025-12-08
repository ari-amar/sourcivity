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
{product_hint}I need to extract specifications from multiple datasheets (provided as markdown) for side-by-side comparison.

CRITICAL: Use IDENTICAL specification keys across all datasheets so they can be compared. For example:
- If one says "Supply Voltage" and another says "Input Voltage", use the SAME key like "supply_voltage_V"
- If one says "Operating Temperature" and another says "Temperature Range", use "temperature_range_C"
- Always include units in the key name (e.g., "_V" for volts, "_A" for amps, "_C" for celsius)
- Parse markdown tables accurately (e.g., | Param | Value | Unit |)

Extract from these datasheets and return a JSON array where each element corresponds to one datasheet's specs.

Focus on the most important comparable specifications:
- Electrical (voltage, current, power)
- Performance (accuracy, bandwidth, flow rate, speed)
- Physical (dimensions, temperature range, weight)
- Identification (manufacturer, part_number, model)

{datasheets_md}

Return ONLY a JSON array with one object per datasheet. Use IDENTICAL keys across all objects for comparable specs.
Example format:
[
  {{"manufacturer": "Company A", "supply_voltage_V": "3-5", "max_current_A": "2"}},
  {{"manufacturer": "Company B", "supply_voltage_V": "5", "max_current_A": "1.5"}}
]

Return ONLY valid JSON array, no other text.
"""