import sys
from enum import Enum

# StrEnum is only available in Python 3.11+
if sys.version_info >= (3, 11):
	from enum import StrEnum
else:
	class StrEnum(str, Enum):
		"""Compatibility StrEnum for Python < 3.11"""
		pass

class AiClientName(StrEnum):
	CLOUDFLARE="cloudflare"
	ANTHROPIC="anthropic"

class SearchEngineClientName(StrEnum):
	DUCKDUCKGO="duckduckgo"
	EXA="exa"
	TAVILY="tavily"