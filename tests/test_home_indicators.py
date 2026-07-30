"""
tests/test_home_indicators.py
=============================
Garante que os indicadores da página inicial derivem só do conjunto de registros
recebido, e que a chave de sessão `pipeline_stats` não exista mais (issue #103).

A chave era fiação morta: gravada em `views/upload.py` com o mesmo valor nos quatro
campos e lida em `views/home.py` por quatro variáveis que nunca eram renderizadas.

A varredura do fonte é textual, como em `test_view_filter_centralization.py`, porque
o critério é a *ausência* de código. O comportamento dos indicadores é testado sobre
as agregações puras que a home delega a `core/aggregations/counters.py` — a §13 do
CLAUDE.md proíbe testar a UI diretamente.
"""

from pathlib import Path

import pytest

from core.aggregations.counters import (
    count_by_language,
    count_by_project_type,
)
from core.transforms.filtering import (
    apply_filters,
    by_language,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _python_modules() -> tuple[Path, ...]:
    """Lista os módulos Python do projeto, ignorando ambientes e caches."""
    ignored = (".venv", "__pycache__", ".cache", "site-packages")
    this_module = Path(__file__).resolve()

    return tuple(
        sorted(
            path
            for path in PROJECT_ROOT.rglob("*.py")
            if not any(part in ignored for part in path.parts)
            and path.resolve() != this_module
        )
    )


def test_project_has_modules_to_check():
    """Sanidade: a varredura precisa ter encontrado arquivos."""
    assert len(_python_modules()) > 0


@pytest.mark.parametrize("module_path", _python_modules(), ids=lambda p: p.name)
def test_module_does_not_reference_pipeline_stats(module_path: Path):
    """Nenhum módulo escreve, lê ou remove a chave de sessão `pipeline_stats`."""
    source = module_path.read_text(encoding="utf-8")

    assert "pipeline_stats" not in source, (
        f"{module_path.name} ainda referencia a chave de sessão `pipeline_stats`, "
        "removida na issue #103."
    )


def test_new_upload_still_clears_analysis_session_keys():
    """Limpar a sessão para novo upload continua descartando Análise e prontidão."""
    source = (PROJECT_ROOT / "views" / "upload.py").read_text(encoding="utf-8")

    assert "analysis_results" in source
    assert "analysis_ready" in source


def _with(record, **overrides):
    """Deriva um AnalysisResult a partir de outro, sem mutação."""
    return record._replace(**overrides)


def test_home_indicators_reflect_the_filtered_subset(sample_analysis_result):
    """Os indicadores da home derivam do recorte, não do conjunto completo."""
    records = (
        _with(sample_analysis_result, id=1, language="go", project_type="library"),
        _with(sample_analysis_result, id=2, language="python", project_type="cli"),
        _with(sample_analysis_result, id=3, language="python", project_type="web_app"),
    )

    filtered = tuple(apply_filters((by_language(("python",)),), records))

    assert len(filtered) == 2
    assert dict(count_by_language(filtered)) == {"python": 2}
    assert dict(count_by_project_type(filtered)) == {"cli": 1, "web_app": 1}
