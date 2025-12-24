SERVICE_EXTRACTION_PROMPT: str = """
{supplier_hint}Extract key information about this supplier's manufacturing services and capabilities.

Focus on extracting:
1. **Company Name**: The name of the company/supplier
2. **Services Offered**: What manufacturing services do they provide? (e.g., CNC machining, injection molding, sheet metal fabrication, etc.)
3. **Capabilities**: Specific capabilities, processes, or technologies (e.g., 5-axis CNC, precision tolerances, materials worked with)
4. **Certifications**: Quality certifications (ISO 9001, AS9100, ITAR, etc.)
5. **Equipment**: Major equipment or machinery mentioned

Return the information as a JSON object with these keys ONLY:
- company_name: string
- services_offered: string (comma-separated list)
- capabilities: string (comma-separated list)
- certifications: string (comma-separated list)
- equipment: string (comma-separated list)

Page text:
{page_text}

Return ONLY valid JSON, no other text.
"""

STANDARDIZED_SERVICE_PROMPT: str = """
{context_hint}I need to extract supplier service information from multiple web pages for side-by-side comparison.

CRITICAL: Use IDENTICAL keys across all suppliers so they can be compared. Be consistent with:
- String formatting (always use comma-separated strings for lists)
- Empty values (use empty string "" if information not found, don't omit the key)
- Standardized naming (use same service names across suppliers)

Extract these pages and return a JSON array where each element corresponds to one supplier's info.

Focus on ONLY these fields:
1. **Company Name**: The name of the company/supplier
2. **Services Offered**: Manufacturing services (CNC machining, injection molding, 3D printing, etc.) as comma-separated string
3. **Capabilities**: Specific processes, technologies, materials, tolerances as comma-separated string
4. **Certifications**: ISO 9001, AS9100, ITAR, ISO 13485, etc. as comma-separated string
5. **Equipment**: Major machinery or technology platforms as comma-separated string

{pages_text}

Return ONLY a JSON array with one object per supplier. Use IDENTICAL keys across all objects.
Example format:
[
  {{
	"company_name": "ABC Manufacturing",
	"services_offered": "CNC machining, Sheet metal fabrication, Welding",
	"capabilities": "5-axis CNC, ±0.001\" tolerance, Aluminum and steel",
	"certifications": "ISO 9001, AS9100",
	"equipment": "Haas VF-4, DMG Mori NLX 2500"
  }},
  {{
	"company_name": "XYZ Services",
	"services_offered": "CNC machining, Injection molding",
	"capabilities": "3-axis CNC, Thermoplastics, ±0.005\" tolerance",
	"certifications": "ISO 9001",
	"equipment": "Toshiba EC340H, Engel Victory 200"
  }}
]

Return ONLY valid JSON array, no other text.
"""