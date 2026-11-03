import os
import time
import logging
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("procureqa.groq_service")


class GroqService:
    """
    Modular service handling direct communication with the Groq API.
    Provides async chat completion, timeout management, error classification,
    and latency measurement.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.timeout = timeout
        self._async_client = None

        if self.api_key and self.api_key != "your_groq_api_key_here":
            try:
                from groq import AsyncGroq
                self._async_client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq Async client: {e}")
                self._async_client = None

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid Groq client is configured."""
        return bool(self._async_client and self.api_key and self.api_key != "your_groq_api_key_here")

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 600,
    ) -> Tuple[str, float]:
        """
        Sends system and user messages to Groq API and tracks execution latency.
        Returns: (response_text, latency_ms)
        """
        if not self.is_configured:
            raise RuntimeError("Groq API key not configured or client initialization failed.")

        import groq

        start_time = time.perf_counter()
        try:
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            content = response.choices[0].message.content or ""
            return content.strip(), latency_ms

        except groq.RateLimitError as rle:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Groq Rate Limit Exceeded: {rle}")
            raise RuntimeError(f"Groq Rate Limit Exceeded: Please retry later. ({rle})")

        except groq.APIConnectionError as ace:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Groq Connection Error: {ace}")
            raise RuntimeError(f"Unable to connect to Groq API: {ace}")

        except groq.APIStatusError as ase:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Groq API Error {ase.status_code}: {ase.message}")
            raise RuntimeError(f"Groq API returned error {ase.status_code}: {ase.message}")

        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Unexpected Groq execution error: {e}")
            raise RuntimeError(f"Groq execution failure: {str(e)}")

