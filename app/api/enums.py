from enum import StrEnum

class AiClientName(StrEnum):
	CLOUDFLARE="cloudflare"
	ANTHROPIC="anthropic"

class SearchEngineClientName(StrEnum):
	DUCKDUCKGO="duckduckgo"
	EXA="exa"
	TAVILY="tavily"