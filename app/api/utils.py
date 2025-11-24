import re

SPEC_PATTERNS = [
	r'\d+\s*(kW|HP|Watt|Volt|V|Amp|A|Hz|RPM|rpm|Pole|pole)',     # power, voltage, current, frequency, speed, poles
	r'\b(IP\d{2}|IEC\s*\d+[LMB]?)',                               # IP rating, IEC frame
	r'\b(B3|B5|B14|B35|V1|V5|TEFC|TENV|ODP)\b',                    # mounting, cooling
	r'\bIE[1-4]\b',                                               # efficiency class
	r'\d{3,4}\s*(V|Volt)',                                        # voltage standalone
	r'\b\d{2,3}\s*(kW|HP)\b',                                     # power standalone
	r'frame\s*\d+[LMB]?',                                         # IEC frame size
	r'\b\d{1,4}\s*(rpm|RPM)\b',                                   # speed
	r'\b[1-8]\s*-?\s*pole\b',                                     # poles
	r'\b(ATEX|Ex\s*d|Ex\s*e|Class\s*I{1,2}\s*Div\s*[1-2])\b',     # hazardous location
]

def contains_technical_specifications(text):
	"""
	Check if the input text contains technical specifications based on predefined patterns.
	"""
	text = text.lower()
	for pattern in SPEC_PATTERNS:
		if re.search(pattern, text, re.IGNORECASE):
			return True
	return False