"""
Página responsável pelo upload e ingestão de datasets CSV/JSON.

Esta interface permite que o usuário carregue arquivos contendo
pull requests públicos do GitHub. Após o upload, o pipeline
funcional inicia o processamento lazy dos registros utilizando
geradores Python, evitando carregamento completo em memória.

Responsabilidades:
- Upload de arquivos CSV/JSON
- Validação inicial do dataset
- Inicialização do pipeline funcional
- Disparo do processo de classificação e enriquecimento
- Persistência do hash da análise para cache posterior
"""
import csv
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from core.transforms.cleaning import get_missing_columns


def _read_header_lazily(uploaded_file: UploadedFile) -> tuple[str, ...]:
    """Lê apenas a primeira linha do CSV e rebobina o ponteiro do arquivo.

    Usa `readline()` para consumir somente os bytes necessários para o
    cabeçalho, sem carregar o restante do arquivo em memória. Após a leitura,
    o ponteiro é resetado via `seek(0)` diretamente no `BytesIO` interno do
    Streamlit, garantindo que o pipeline de ingestão leia o arquivo do início.

    Args:
        uploaded_file (UploadedFile): Objeto de arquivo carregado via
            `st.file_uploader`. Comporta-se como `BytesIO` internamente.

    Returns:
        tuple[str, ...]: Tupla imutável com os nomes das colunas lidos da
        primeira linha do CSV. Retorna tupla vazia se o arquivo estiver vazio
        ou se ocorrer erro de decodificação.
    """
    try:
        first_line_bytes = uploaded_file.readline()
        if not first_line_bytes:
            return ()

        first_line = first_line_bytes.decode("utf-8", errors="replace")
        header = tuple(next(csv.reader([first_line])))
    except (StopIteration, UnicodeDecodeError):
        header = ()
    finally:
        uploaded_file.seek(0)

    return header


def _validate_schema(uploaded_file: UploadedFile) -> bool:
    """Valida o schema do dataset e exibe feedback ao usuário via Streamlit.

    Lê apenas o cabeçalho do arquivo e delega a verificação de colunas
    obrigatórias à função pura `get_missing_columns` de
    `core/transforms/cleaning.py`, mantendo a separação entre lógica de
    negócio (core) e apresentação (ui).

    Args:
        uploaded_file (UploadedFile): Objeto de arquivo carregado via
            `st.file_uploader`, com ponteiro posicionado no início.

    Returns:
        bool: True quando todas as colunas obrigatórias estão presentes,
        False quando o arquivo está vazio ou faltam colunas.
    """
    header = _read_header_lazily(uploaded_file)

    if not header:
        st.error("O arquivo enviado está vazio ou é inválido.")
        return False

    missing = get_missing_columns(header)
    if missing:
        st.error(f"Faltam colunas obrigatórias: **{', '.join(missing)}**")
        return False

    return True


def render() -> None:
    """Renderiza a página de upload e dispara o pipeline quando um arquivo válido é enviado.

    Exibe o componente de upload, executa a validação de schema (Issue #10)
    e, quando aprovado, deixa o arquivo posicionado no início para que
    `services/ingestion.py` inicie a leitura lazy dos registros.
    """
    st.title("📂 Carregar Dataset")

    uploaded_file = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

    if uploaded_file is None:
        st.info("Aguardando upload...")
        return

    if not _validate_schema(uploaded_file):
        st.stop()

    st.success("Schema validado! O arquivo está pronto para o processamento lazy.")
    st.info("Ponteiro do arquivo resetado. Pronto para ingestão.")


render()