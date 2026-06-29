import pytest
from unittest.mock import patch, AsyncMock

from backend.api.onboard import _create_jewel_from_dict


def test_create_jewel_from_dict_minimal():
    result = _create_jewel_from_dict({
        "name": "Anel Teste",
        "metal": "ouro_18k",
        "weight_grams": 5.0,
    })
    assert result["name"] == "Anel Teste"
    assert result["metal"] == "ouro_18k"
    assert result["weight_grams"] == 5.0
    assert result["status"] == "cadastrada"
    assert result["origin"] == ""
    assert result["description"] == ""


def test_create_jewel_from_dict_full():
    result = _create_jewel_from_dict({
        "name": "Anel Safira",
        "metal": "platina",
        "gemstones": ["safira", "diamante"],
        "weight_grams": 4.5,
        "origin": "REF-001",
        "description": "Anel luxuoso com safira azul",
        "price": "12500.00",
        "source_url": "https://joalheriax.com",
    })
    assert result["name"] == "Anel Safira"
    assert result["metal"] == "platina"
    assert "safira" in result["gemstones"]
    assert "diamante" in result["gemstones"]
    assert result["weight_grams"] == 4.5
    assert result["description"] == "Anel luxuoso com safira azul"


def test_create_jewel_from_dict_invalid_metal_fallback():
    result = _create_jewel_from_dict({
        "name": "Teste",
        "metal": "metal_inexistente",
        "weight_grams": 1.0,
    })
    assert result["metal"] == "ouro_18k"


def test_create_jewel_from_dict_invalid_gemstone_ignored():
    result = _create_jewel_from_dict({
        "name": "Teste",
        "metal": "prata_925",
        "gemstones": ["diamante", "pedra_fake"],
        "weight_grams": 2.0,
    })
    assert "diamante" in result["gemstones"]
    assert "pedra_fake" not in result["gemstones"]


def test_create_jewel_from_dict_gemstones_as_string():
    result = _create_jewel_from_dict({
        "name": "Teste",
        "metal": "ouro_18k",
        "gemstones": "diamante, rubi, safira",
        "weight_grams": 3.0,
    })
    assert "diamante" in result["gemstones"]
    assert "rubi" in result["gemstones"]
    assert "safira" in result["gemstones"]
