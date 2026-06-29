"""HTTP scraper for competitor price intelligence — lightweight alternative to browser-use."""
import json
import logging
import re
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup

from ..storage.hashchain import append_jewel_entry

logger = logging.getLogger("vivify.http_scraper")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

TIMEOUT = 30.0


def _parse_price(text: str) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"[R$\s\.]", "", text)
    cleaned = cleaned.replace(",", ".")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
    if match:
        return match.group(1)
    cleaned2 = re.sub(r"[^0-9,]", "", text).replace(",", ".")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned2)
    return match.group(1) if match else None


def _product_from_jsonld(item: dict) -> dict[str, Any]:
    offers = item.get("offers") or {}
    if isinstance(offers, dict):
        if offers.get("@type") == "AggregateOffer":
            price_val = str(offers.get("lowPrice", ""))
        else:
            price_val = str(offers.get("price", ""))
    else:
        price_val = ""
    return {
        "name": item.get("name"),
        "price": _parse_price(price_val),
        "description": item.get("description"),
        "image_url": (
            item.get("image")[0]
            if isinstance(item.get("image"), list)
            else item.get("image")
        ),
        "sku": item.get("sku"),
        "source": "jsonld",
    }


def _extract_jsonld(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    products = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") in ("Product", "ItemList"):
                if item["@type"] == "ItemList" and "itemListElement" in item:
                    for entry in item["itemListElement"]:
                        p = entry.get("item") or entry
                        if isinstance(p, dict) and p.get("@type") == "Product":
                            products.append(_product_from_jsonld(p))
                elif item["@type"] == "Product":
                    products.append(_product_from_jsonld(item))
    return products


def _extract_html(html: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    products = []
    seen = set()

    containers = soup.select(
        "div.product, li.product-item, div[class*='product'], "
        "div[class*='card'], article, div[class*='item'], "
        "div[class*='produto'], li[class*='produto'], "
        "li[class*='product']"
    )
    if not containers:
        containers = soup.find_all(["div", "li", "article"], class_=re.compile(r"(product|card|item|produto|jewel)", re.I))
    if not containers:
        containers = [soup]

    for container in containers:
        name_el = (
            container.select_one("h2 a")
            or container.select_one("h3 a")
            or container.select_one("h2")
            or container.select_one("h3")
            or container.select_one("a[class*='name']")
            or container.select_one("span[class*='name']")
            or container.select_one("div[class*='name']")
            or container.select_one("a[class*='title']")
            or container.select_one("img[alt]")
        )
        name = None
        if name_el:
            name = name_el.get("alt") or name_el.get_text(strip=True)
        if not name or len(name) < 3:
            continue

        price_el = (
            container.select_one("span[class*='price']")
            or container.select_one("div[class*='price']")
            or container.select_one("ins")
            or container.select_one("span[class*='preco']")
            or container.select_one("div[class*='preco']")
            or container.select_one("meta[itemprop='price']")
            or container.select_one("span[itemprop='price']")
        )
        price = None
        if price_el:
            val = price_el.get("content") or price_el.get_text(strip=True)
            price = _parse_price(val)

        img_el = (
            container.select_one("img[class*='product']")
            or container.select_one("img[class*='card']")
            or container.select_one("img[src*='product']")
            or container.select_one("img:not([src*='logo']):not([src*='icon'])")
        )
        image_url = None
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src") or ""
            if image_url and image_url.startswith("/"):
                from urllib.parse import urljoin
                image_url = urljoin(base_url, image_url)

        desc_el = container.select_one(
            "p[class*='desc'], div[class*='desc'], span[class*='desc'], "
            "p[class*='description'], div[class*='description']"
        )
        description = desc_el.get_text(strip=True) if desc_el else None

        dedup_key = f"{name}|{price or ''}"
        if dedup_key not in seen:
            seen.add(dedup_key)
            products.append({
                "name": name,
                "price": price,
                "image_url": image_url,
                "description": description,
                "sku": None,
                "source": "html",
            })

    return products


class HttpScraperService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_page(self, url: str) -> Optional[str]:
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    async def monitor_competitor(self, url: str) -> dict[str, Any]:
        html = await self.fetch_page(url)
        if not html:
            append_jewel_entry(
                event_type="vivify.http_scraper.failed",
                jewel_id="http_scraper",
                metadata={"url": url, "error": "fetch_failed"},
            )
            return {"competitor": url, "products": []}

        products = _extract_jsonld(html)
        if not products:
            logger.info("No JSON-LD found at %s, trying HTML parsing", url)
            products = _extract_html(html, url)

        logger.info("Scraped %d products from %s", len(products), url)

        append_jewel_entry(
            event_type="vivify.http_scraper.scan",
            jewel_id="http_scraper",
            metadata={"url": url, "products_found": len(products)},
        )
        return {"competitor": url, "products": products}

    async def extract_catalog(self, url: str) -> list[dict[str, Any]]:
        result = await self.monitor_competitor(url)
        return result.get("products", [])
