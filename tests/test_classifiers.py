"""
tests/test_classifiers.py
====================================
Testes unitários para services/classifiers.py
"""

import json
from unittest.mock import patch
from dataclasses import dataclass

import pytest

from services.classifiers import (
    ClarityLevel,
    ClarityResult,
    PRNature,
    PRNatureResult,
    ProjectType,
    ProjectTypeResult,
    classify_clarity,
    classify_pr_nature,
    classify_project_type,
    _parse,
    _cached_call,
)


@dataclass
class FakeRecord:
    body: str = ""
    repo: str = "org/repo"
    title: str = "Título padrão do PR"
    path: str = "src/main.py"
    diff_hunk: str = "+ linha nova"


@pytest.fixture
def record():
    return FakeRecord(body="O botão de login não respondia em mobile.")


@pytest.fixture
def records():
    return [
        FakeRecord("Novo painel de métricas.", "org/repo"),
        FakeRecord("CSV vazio em alguns casos.", "org/repo"),
        FakeRecord("Instruções de instalação.", "org/outro"),
    ]


def test_parse_extrai_campo_corretamente():
    assert _parse(json.dumps({"nature": "bug_fix"}), "nature") == "bug_fix"


def test_parse_normaliza_para_lowercase():
    assert _parse(json.dumps({"clarity": "Excelente"}), "clarity") == "excelente"


def test_parse_espacos_viram_underscore():
    assert _parse(json.dumps({"nature": "bug fix"}), "nature") == "bug_fix"


def test_parse_json_invalido_retorna_vazio():
    assert _parse("não é json", "nature") == ""


def test_parse_campo_ausente_retorna_vazio():
    assert _parse(json.dumps({"outro": "valor"}), "nature") == ""


def test_parse_remove_bloco_markdown():
    raw = "```json\n" + json.dumps({"clarity": "boa"}) + "\n```"
    assert _parse(raw, "clarity") == "boa"


def test_cached_call_retorna_cache_sem_chamar_llm():
    with (
        patch("services.classifiers.get_cache", return_value="cached_value"),
        patch("services.classifiers.call_llm") as mock_llm,
    ):
        assert _cached_call("chave", "prompt") == "cached_value"
        mock_llm.assert_not_called()


def test_cached_call_chama_llm_em_cache_miss():
    with (
        patch("services.classifiers.get_cache", return_value=None),
        patch("services.classifiers.call_llm", return_value="llm_response"),
        patch("services.classifiers.set_cache") as mock_set,
    ):
        assert _cached_call("chave", "prompt") == "llm_response"
        mock_set.assert_called_once_with("chave", "llm_response")


@pytest.mark.parametrize(
    "value, expected",
    [
        ("bug_fix", PRNature.BUG_FIX),
        ("feature", PRNature.FEATURE),
        ("refactoring", PRNature.REFACTORING),
        ("documentation", PRNature.DOCUMENTATION),
    ],
)
def test_classify_pr_nature_mapeia_valores_validos(record, value, expected):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"nature": value})
    ):
        assert classify_pr_nature(record).nature == expected


def test_classify_pr_nature_fallback_para_unknown(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"nature": "invalido"}),
    ):
        assert classify_pr_nature(record).nature == PRNature.UNKNOWN


def test_classify_pr_nature_retorna_tipo_correto(record):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"nature": "feature"})
    ):
        assert isinstance(classify_pr_nature(record), PRNatureResult)


@pytest.mark.parametrize(
    "value, score",
    [
        ("insuficiente", 1),
        ("basica", 2),
        ("boa", 3),
        ("excelente", 4),
    ],
)
def test_classify_clarity_score_correto(record, value, score):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"clarity": value})
    ):
        assert classify_clarity(record).score == score


def test_classify_clarity_fallback_para_insuficiente(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"clarity": "invalido"}),
    ):
        assert classify_clarity(record).level == ClarityLevel.INSUFICIENTE


def test_classify_clarity_retorna_tipo_correto(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"clarity": "excelente"}),
    ):
        assert isinstance(classify_clarity(record), ClarityResult)


def test_classify_project_type_agrupa_por_repositorio(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "api"}),
    ):
        assert len(classify_project_type(records)) == 2


def test_classify_project_type_mapeia_valor_valido(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "api"}),
    ):
        assert all(
            r.project_type == ProjectType.API for r in classify_project_type(records)
        )


def test_classify_project_type_fallback_para_unknown(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "invalido"}),
    ):
        assert all(
            r.project_type == ProjectType.UNKNOWN
            for r in classify_project_type(records)
        )


def test_classify_project_type_retorna_tipo_correto(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "library"}),
    ):
        assert all(
            isinstance(r, ProjectTypeResult) for r in classify_project_type(records)
        )


def test_clarity_level_scores():
    assert ClarityLevel.INSUFICIENTE.score == 1
    assert ClarityLevel.BASICA.score == 2
    assert ClarityLevel.BOA.score == 3
    assert ClarityLevel.EXCELENTE.score == 4
