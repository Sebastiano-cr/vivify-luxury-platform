import pytest
from backend.services.browser_agent import BrowserAutomationService


@pytest.fixture
def service():
    return BrowserAutomationService(headless=True)


def test_parse_json_plain(service):
    text = '{"name": "Anel", "price": "1500.00"}'
    result = service._parse_json(text)
    assert result == {"name": "Anel", "price": "1500.00"}


def test_parse_json_with_markdown(service):
    text = '```json\n{"name": "Anel", "price": "1500.00"}\n```'
    result = service._parse_json(text)
    assert result == {"name": "Anel", "price": "1500.00"}


def test_parse_json_with_triple_backtick(service):
    text = '```\n{"name": "Anel"}\n```'
    result = service._parse_json(text)
    assert result == {"name": "Anel"}


def test_parse_json_array(service):
    text = '[{"name": "Anel"}, {"name": "Colar"}]'
    result = service._parse_json(text)
    assert isinstance(result, list)
    assert len(result) == 2


def test_parse_json_with_text_before(service):
    text = 'Aqui está o resultado:\n```json\n{"product": "Anel Ouro", "price": 2500}\n```'
    result = service._parse_json(text)
    assert result == {"product": "Anel Ouro", "price": 2500}


def test_parse_json_invalid_returns_none(service):
    text = "Não consegui extrair os dados. O site está bloqueado."
    result = service._parse_json(text)
    assert result is None


def test_parse_json_empty_returns_none(service):
    assert service._parse_json("") is None
    assert service._parse_json("   ") is None
