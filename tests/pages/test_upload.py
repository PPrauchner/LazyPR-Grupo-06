import pytest
from unittest.mock import MagicMock, patch
from views.upload import _validate_schema


@patch("views.upload.st")
@patch("views.upload.get_missing_columns")
@patch("views.upload.read_header_lazily")
def test_validate_schema_with_missing_columns(
    mock_read_header, mock_get_missing, mock_st
):
    """
    Verifica se a validação falha e aciona o erro no Streamlit
    quando o dataset não possui as colunas necessárias.
    """
    # Simulando um dataset inválido
    mock_read_header.return_value = ["id", "body"]
    mock_get_missing.return_value = ["html_url", "author"]

    # Criando um arquivo mockado para testar o comportamento do ponteiro
    mock_file = MagicMock()

    is_valid = _validate_schema(mock_file)

    # Verifica se falhou como esperado
    assert is_valid is False
    # Verifica se a mensagem de erro foi exibida na interface
    mock_st.error.assert_called_once()
    # Verifica se a sua lógica de rebobinar o ponteiro do arquivo foi chamada
    mock_file.seek.assert_called_with(0)


@patch("views.upload.st")
@patch("views.upload.get_missing_columns")
@patch("views.upload.read_header_lazily")
def test_validate_schema_success(mock_read_header, mock_get_missing, mock_st):
    """
    Verifica se o schema passa corretamente e não emite erros
    quando o dataset está completo.
    """
    # Simulando um dataset perfeitamente válido
    mock_read_header.return_value = ["id", "html_url", "repo", "author", "body"]
    mock_get_missing.return_value = []  # Retorna vazio, ou seja, nada falta

    mock_file = MagicMock()
    is_valid = _validate_schema(mock_file)

    # Verifica se passou
    assert is_valid is True
    # Garante que nenhum erro foi jogado na tela
    mock_st.error.assert_not_called()
