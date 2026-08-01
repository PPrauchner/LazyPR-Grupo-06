"""
tests/pages/test_export.py
==========================
Garante que a guarda de `views/export.py` verifique o que a página exporta.

A página consome `records` — a Análise já recortada pelo Filtro de Visualização
em `main.py` (ADR-0003). Checar `st.session_state` no lugar de `records` deixava
passar o caso "sessão populada, recorte vazio", que renderizava KPIs zerados e
botões de download de um CSV vazio.

Responsabilidades:
    - Cobrir recorte vazio com Análise carregada (mensagem de filtro).
    - Cobrir ausência de Análise (mensagem de upload).
    - Garantir que o caminho feliz continua renderizando os downloads.
"""

from unittest.mock import MagicMock, patch

import pytest

from views.export import render_export_page


@pytest.fixture
def mock_columns() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Três colunas Streamlit utilizáveis como context manager."""
    return (MagicMock(), MagicMock(), MagicMock())


@patch("views.export.download_buttons")
@patch("views.export.data_table")
@patch("views.export.status_banner")
@patch("views.export.st")
def test_render_export_page_empty_records_with_analysis_warns_about_filter(
    mock_st: MagicMock,
    mock_status_banner: MagicMock,
    mock_data_table: MagicMock,
    mock_download_buttons: MagicMock,
    sample_analysis_result,
) -> None:
    """Recorte vazio com Análise carregada aponta o Filtro de Visualização."""
    mock_st.session_state = {"analysis_results": (sample_analysis_result,)}

    render_export_page(())

    mock_status_banner.assert_called_once()
    message, kwargs = mock_status_banner.call_args[0][0], (
        mock_status_banner.call_args[1]
    )
    assert "Filtro de Visualização" in message
    assert kwargs["status_type"] == "info"

    mock_data_table.assert_not_called()
    mock_download_buttons.assert_not_called()


@patch("views.export.download_buttons")
@patch("views.export.data_table")
@patch("views.export.status_banner")
@patch("views.export.st")
def test_render_export_page_without_analysis_points_to_upload(
    mock_st: MagicMock,
    mock_status_banner: MagicMock,
    mock_data_table: MagicMock,
    mock_download_buttons: MagicMock,
) -> None:
    """Sem Análise na sessão, a mensagem manda o Analista ao Upload."""
    mock_st.session_state = {}

    render_export_page(())

    mock_status_banner.assert_called_once()
    message, kwargs = mock_status_banner.call_args[0][0], (
        mock_status_banner.call_args[1]
    )
    assert "Upload" in message
    assert kwargs["status_type"] == "warning"

    mock_data_table.assert_not_called()
    mock_download_buttons.assert_not_called()


@patch("views.export.download_buttons")
@patch("views.export.data_table")
@patch("views.export.metric_card")
@patch("views.export.status_banner")
@patch("views.export.st")
def test_render_export_page_with_records_renders_downloads(
    mock_st: MagicMock,
    mock_status_banner: MagicMock,
    mock_metric_card: MagicMock,
    mock_data_table: MagicMock,
    mock_download_buttons: MagicMock,
    mock_columns: tuple[MagicMock, MagicMock, MagicMock],
    sample_analysis_result,
) -> None:
    """Com recorte não vazio, a página exporta em vez de exibir banner."""
    mock_st.session_state = {"analysis_results": (sample_analysis_result,)}
    mock_st.columns.return_value = mock_columns

    render_export_page((sample_analysis_result,))

    mock_status_banner.assert_not_called()
    mock_st.stop.assert_not_called()
    mock_data_table.assert_called_once_with((sample_analysis_result,))
    mock_download_buttons.assert_called_once_with((sample_analysis_result,))
