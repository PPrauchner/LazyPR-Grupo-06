"""
tests/test_view_filter_centralization.py
========================================
Garante que o Filtro de Visualização seja aplicado num único ponto (ADR-0003).

`main.py` recorta a Análise uma vez, no roteamento, e entrega `records` já
filtrado a todas as páginas. Nenhuma página de `views/` pode reaplicar o recorte:
duas fontes do mesmo filtro fazem toda mudança futura precisar ser feita em vários
lugares (issue #102).

A varredura é textual sobre o fonte, como em `test_core_layer_boundaries.py`, para
pegar também imports tardios dentro de funções.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIEWS_DIR = PROJECT_ROOT / "views"

FORBIDDEN_FRAGMENTS = (
    "get_active_filters",
    "apply_filters",
)


def _view_modules() -> tuple[Path, ...]:
    """Lista todos os módulos Python de views/."""
    return tuple(sorted(VIEWS_DIR.rglob("*.py")))


def test_views_have_modules_to_check():
    """Sanidade: a varredura precisa ter encontrado arquivos."""
    assert len(_view_modules()) > 0


@pytest.mark.parametrize("module_path", _view_modules(), ids=lambda p: p.name)
def test_view_module_does_not_reapply_visualization_filter(module_path: Path):
    """Nenhuma página de views/ reaplica o Filtro de Visualização."""
    source = module_path.read_text(encoding="utf-8")

    offenders = tuple(
        fragment for fragment in FORBIDDEN_FRAGMENTS if fragment in source
    )

    assert not offenders, (
        f"{module_path.name} reaplica o Filtro de Visualização: {offenders}. "
        "O recorte é feito uma única vez em main.py (ADR-0003)."
    )


def test_main_applies_the_visualization_filter():
    """main.py continua sendo o ponto que aplica o Filtro de Visualização."""
    source = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")

    assert "get_active_filters" in source
    assert "apply_filters" in source
