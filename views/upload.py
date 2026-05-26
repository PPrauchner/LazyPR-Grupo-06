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
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from core.transforms.cleaning import get_missing_columns
from services.ingestion import read_header_lazily


def _validate_schema(uploaded_file: UploadedFile) -> bool:
    """
    Valida o schema do dataset e exibe o feedback visual correspondente.

    Consome a estrutura de cabeçalho obtida de forma lazy pela camada de 
    ingestão e delega a verificação de conformidade de colunas para uma 
    função pura de transformação, isolando efeitos colaterais de I/O 
    da renderização de erros na interface.

    Args:
        uploaded_file: Objeto de arquivo binário interceptado pelo Streamlit.

    Returns:
        bool: True se o schema for estritamente válido e contiver todas as 
        colunas obrigatórias; False caso contrário.
    """
    header = read_header_lazily(uploaded_file)

    if not header:
        st.error("O arquivo enviado está vazio ou é inválido.")
        return False

    missing = get_missing_columns(header)
    if missing:
        st.error(f"Faltam colunas obrigatórias: **{', '.join(missing)}**")
        return False

    return True


def render_upload_page() -> None:
    """
    Renderiza os componentes visuais da página e gerencia o estado do fluxo.

    Disponibiliza o seletor de arquivos, aciona a esteira de validação de
    schema e intercepta o fluxo em caso de falha estrutural. Havendo sucesso,
    estabiliza o ponteiro do arquivo no escopo de sessão para permitir
    a avaliação lazy nas etapas subsequentes do pipeline.
    """
    st.title("📂 Carregar Dataset")

    uploaded_file = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

    if uploaded_file is None:
        st.info("Aguardando upload...")
        return

    if not _validate_schema(uploaded_file):
        st.stop()

    st.success("Schema validado! O arquivo está pronto para o processamento.")

    if st.button("Iniciar Análise 🚀"):
        st.session_state["dataset_file"] = uploaded_file
        st.switch_page("pages/correlations.py")
