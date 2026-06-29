"""Bridge para o SOC Gateway — LLM via SmartRouter com fallback."""
import httpx
import logging
import os
from typing import Optional

from ..config import SOC_GATEWAY_URL

logger = logging.getLogger("vivify.llm")

TRAMA_API_KEY = os.getenv("TRAMA_SERVICE_API_KEY", "")

DESCRIPTION_TEMPLATES = {
    "default": "Jóia em {metal}, peça exclusiva com design artesanal. Peso: {weight}g.",
    "com_gemas": "Jóia em {metal} com {gemstones}, peso {weight}g. Edição limitada com certificado digital de proveniência imutável.",
}


class SOCLLMService:
    def __init__(self):
        self.gateway_url = SOC_GATEWAY_URL
        self.timeout = httpx.Timeout(45.0, connect=5.0)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> dict:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "openrouter/auto",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if TRAMA_API_KEY:
            headers["X-API-Key"] = TRAMA_API_KEY

        client = await self._get_client()
        for attempt in range(2):
            try:
                resp = await client.post(
                    f"{self.gateway_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    usage = data.get("usage", {})
                    model_used = data.get("model", "unknown")
                    logger.info(
                        "LLM OK model=%s tokens=%s", model_used, usage
                    )
                    return {"success": True, "content": content, "model": model_used}
                logger.warning(
                    "SOC Gateway HTTP %s: %s", resp.status_code, resp.text[:200]
                )
            except httpx.ConnectError:
                logger.warning(
                    "SOC Gateway connection refused (attempt %d/2)", attempt + 1
                )
            except Exception as e:
                logger.warning("SOC Gateway error: %s", e)

            if attempt == 0:
                logger.info("Retrying SOC Gateway...")

        return {"success": False, "content": "", "model": "fallback"}

    async def describe_jewel(
        self, name: str, metal: str, gemstones: list[str], weight: float
    ) -> str:
        system = (
            "Você é um redator de luxo para joalheria de alto padrão. "
            "Suas descrições são sofisticadas, poéticas, destacam o brilho, "
            "a exclusividade e a arte da peça. Máximo 100 palavras. "
            "Responda em português do Brasil."
        )
        gem_part = f" com {' e '.join(gemstones)}" if gemstones else ""
        user = (
            f"Crie uma descrição de luxo para: {name}, "
            f"em {metal}{gem_part}, peso {weight}g."
        )
        result = await self.generate(prompt=user, system_prompt=system, temperature=0.8)
        if result["success"]:
            return result["content"]
        template_key = "com_gemas" if gemstones else "default"
        return DESCRIPTION_TEMPLATES[template_key].format(
            metal=metal, weight=weight, gemstones=" e ".join(gemstones)
        )

    async def generate_trend_narrative(self, summary_data: dict) -> str:
        system = (
            "Você é um analista de mercado especializado em joalheria. "
            "Gere um relatório conciso (3-5 frases) interpretando as tendências. "
            "Responda em português do Brasil."
        )
        user = f"Resuma estas tendências de joalheria: {summary_data}"
        result = await self.generate(
            prompt=user, system_prompt=system, temperature=0.7
        )
        if result["success"]:
            return result["content"]
        return (
            "Mercado joalheiro estável. "
            "Acompanhe os sinais fracos no dashboard de tendências para "
            "identificar movimentos emergentes."
        )
