import asyncio
from typing import Dict, Any, Optional

from cloudflare import Cloudflare
from services.interfaces import AiClientBase

class CloudflareAiClient(AiClientBase):
    """
    Cloudflare Workers AI implementation of AiClientBase
    """

    def __init__(
        self,
        api_token: str,
        account_id: str,
        model: str = "@cf/meta/llama-3-8b-instruct"
    ):
        self.client = Cloudflare(api_token=api_token)
        self.account_id = account_id
        self.model = model

    async def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        enforce_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 500,
    ) -> Any:
        """
        Cloudflare Workers AI text generation
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_user_prompt(
                user_prompt,
                enforce_json,
                json_schema
            )}
        ]

        # Workers AI Python SDK is sync → run in thread
        response = await asyncio.to_thread(
            self.client.workers.ai.run,
            self.model,
            account_id=self.account_id,
            messages=messages,
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
        Augment user prompt for JSON enforcement if requested
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

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """
        Normalize Workers AI response format
        """
        # Typical response shape:
        # { "result": { "response": "text..." } }
        try:
            return response["result"]["response"]
        except (KeyError, TypeError):
            raise RuntimeError(f"Unexpected Cloudflare response: {response}")
