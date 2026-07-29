"""
tests/test_core_layer_boundaries.py
===================================
Garante que o Functional Core não alcance a camada de UI (Regra Específica 02).

A varredura é textual sobre o fonte, e não sobre os imports resolvidos, de
propósito: o defeito da issue #82 era um import **tardio** dentro de uma função
(`from ui.sidebar_filters import get_active_filters`), invisível para qualquer
checagem baseada em importar o módulo.
"""

from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent / "core"

FORBIDDEN_FRAGMENTS = (
    "import streamlit",
    "from ui.",
    "from ui ",
    "import ui",
    "session_state",
)


def _core_modules() -> tuple[Path, ...]:
    """Lista todos os módulos Python de core/."""
    return tuple(sorted(CORE_DIR.rglob("*.py")))


def test_core_has_modules_to_check():
    """Sanidade: a varredura precisa ter encontrado arquivos."""
    assert len(_core_modules()) > 0


@pytest.mark.parametrize("module_path", _core_modules(), ids=lambda p: p.name)
def test_core_module_does_not_reach_ui_layer(module_path: Path):
    """Nenhum módulo de core/ menciona streamlit, ui/ ou session_state."""
    source = module_path.read_text(encoding="utf-8")

    offenders = tuple(
        fragment for fragment in FORBIDDEN_FRAGMENTS if fragment in source
    )

    assert not offenders, (
        f"{module_path.name} referencia a camada de UI: {offenders}. "
        "core/ deve ser puro (Regra Específica 02)."
    )
