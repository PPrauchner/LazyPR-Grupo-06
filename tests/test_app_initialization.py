"""
Smoke test da inicialização principal
da aplicação Streamlit.

Responsabilidades:
    - Validar imports principais
    - Garantir ausência de ImportError
    - Verificar inicialização dos módulos
"""

from views.correlations_dashboard import (
    render_correlation_dashboard,
)

from views.export import (
    render_export_page,
)

from views.overview import (
    render_overview,
)

from views.upload import (
    render_upload_page,
)

from ui.sidebar_filters import (
    render_sidebar,
)


def test_imports():
    """
    Valida importação dos módulos principais.
    """

    assert render_overview is not None

    assert render_correlation_dashboard is not None

    assert render_upload_page is not None

    assert render_export_page is not None

    assert render_sidebar is not None
