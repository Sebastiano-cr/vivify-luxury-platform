"""Browser automation via browser-use + SOC Gateway como LLM backend."""
import json
import logging
import os
from typing import Any, Optional

from browser_use import Agent, BrowserProfile
from browser_use.llm.openai.chat import ChatOpenAI

from ..config import SOC_GATEWAY_URL
from ..storage.hashchain import append_jewel_entry

logger = logging.getLogger("vivify.browser_agent")


class BrowserAutomationService:
    def __init__(self, headless: bool = False):
        self.llm = ChatOpenAI(
            base_url=f"{SOC_GATEWAY_URL}/v1",
            api_key="soc-gateway-proxy",
            model="qwen2.5:3b",
            temperature=0.2,
        )
        self.browser_profile = BrowserProfile(
            headless=headless,
            allowed_domains=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 1024},
            highlight_elements=False,
        )

    async def _run_agent(self, task: str, max_steps: int = 30) -> str:
        agent = Agent(
            task=task,
            llm=self.llm,
            browser_profile=self.browser_profile,
            max_steps=max_steps,
            generate_gif=False,
            use_vision=False,
        )
        history = await agent.run(max_steps=max_steps)
        result = history.final_result() or ""

        append_jewel_entry(
            event_type="vivify.browser_agent.run",
            jewel_id="browser_agent_session",
            metadata={
                "task_preview": task[:120],
                "result_length": len(result),
                "steps": max_steps,
            },
        )
        return result

    async def extract_catalog(self, url: str) -> list[dict[str, Any]]:
        task = f"""
1. Acesse o site: {url}
2. Encontre o catálogo de produtos (joias). Navegue por todas as páginas de listagem.
3. Para CADA produto, extraia: nome, preço (apenas números), metal, lista de pedras, descrição curta, URL da imagem principal, SKU.
4. Retorne APENAS um array JSON válido. NÃO coloque texto antes ou depois.
   Exemplo: [{{"name":"Anel Ouro","price":"1500.00","metal":"ouro_18k","gemstones":["diamante"],"description":"...","image_url":"...","sku":"REF-001"}}]
5. Se houver mais de 20 produtos, colete todos.
"""
        result = await self._run_agent(task, max_steps=50)
        return self._parse_json(result) or []

    async def monitor_competitor(self, url: str) -> dict[str, Any]:
        task = f"""
1. Acesse: {url}
2. Encontre os 10 produtos mais vendidos ou em destaque.
3. Para cada um, extraia: nome, preço.
4. Retorne APENAS JSON: {{"competitor":"{url}","products":[{{"name":"...","price":"..."}}]}}
"""
        result = await self._run_agent(task)
        data = self._parse_json(result)
        if data and isinstance(data, dict):
            return data
        return {"competitor": url, "products": []}

    async def test_checkout(self, url: str, product_ref: str) -> dict[str, Any]:
        task = f"""
Simule um cliente comprando em: {url}
1. Encontre o produto com referência: {product_ref}.
2. Adicione ao carrinho.
3. Vá para o checkout.
4. Preencha: Nome: Teste, CPF: 123.456.789-00, CEP: 01001-000.
5. Avance até a tela de pagamento (não finalize).
6. Retorne APENAS JSON: {{"success":true/false,"step_failed":"...","message":"..."}}
"""
        result = await self._run_agent(task)
        data = self._parse_json(result)
        if data and isinstance(data, dict):
            return data
        return {"success": False, "step_failed": "parse", "message": result[:200]}

    def _parse_json(self, text: str) -> Optional[Any]:
        for delim in ("```json", "```"):
            if delim in text:
                parts = text.split(delim)
                if len(parts) >= 2:
                    text = parts[1].split("```")[0] if "```" in parts[1] else parts[1]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from agent output: %s", text[:200])
            return None
