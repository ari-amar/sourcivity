from typing import Dict, Any, Optional

from anthropic import AsyncAnthropic
from services.interfaces import AiClientBase
class AnthropicAiClient(AiClientBase):
    """
    Anthropic Claude implementation of AiClientBase
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
    ):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        enforce_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 500,
    ) -> str:
        """
        Anthropic text generation implementation
        """

        user_content = self._build_user_prompt(
            user_prompt=user_prompt,
            enforce_json=enforce_json,
            json_schema=json_schema,
        )

        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_content}
            ],
            max_tokens=max_tokens,
        )

        return self._extract_text(response)

    def _build_user_prompt(
        self,
        user_prompt: str,
        enforce_json: bool,
        json_schema: Optional[Dict[str, Any]],
    ) -> str:
        """
        Augment user prompt for JSON enforcement
        """
        if not enforce_json:
            return user_prompt

        schema_text = ""
        if json_schema:
            schema_text = (
                "\n\nReturn JSON that strictly matches this schema:\n"
                f"{json_schema}"
            )

        return (
            user_prompt
            + "\n\nIMPORTANT: Respond ONLY with valid JSON."
            + schema_text
        )

    def _extract_text(self, response) -> str:
        """
        Normalize Anthropic response format
        """
        # response.content is a list of blocks
        # usually one block of type "text"
        try:
            return "".join(
                block.text
                for block in response.content
                if block.type == "text"
            )
        except Exception:
            raise RuntimeError(f"Unexpected Anthropic response: {response}")