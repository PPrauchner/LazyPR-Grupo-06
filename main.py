"""
Ponto de entrada da aplicação Streamlit, responsável por orquestrar
a inicialização do sistema e o roteamento entre páginas.

Responsabilidades:
    - Configurar o layout global do Streamlit (título, ícone, sidebar).
    - Inicializar o `st.session_state` com os valores padrão necessários
      para o funcionamento dos filtros e do pipeline entre rerenders.
    - Verificar se um dataset já foi carregado/analisado e redirecionar
      o fluxo adequadamente (tela de upload vs. dashboard de análise).
    - Importar e registrar as páginas da pasta `pages/` no sistema de
      navegação do Streamlit.
    - Não deve conter lógica de negócio: apenas composição e inicialização.

Não deve:
    - Chamar LLMs, ler arquivos ou executar o pipeline diretamente.
    - Conter transformações de dados ou lógica de plotagem.

Relacionado a:
    - Todas as issues (ponto de entrada único da aplicação)
    - Regra Geral 08 (interface gráfica obrigatória)
    - Dica 04 (Streamlit como framework de interface)
"""

import streamlit as st

from pages.overview_dashboard import (
    render_overview,
)

from pages.correlation_dashboard import (
    render_correlation_dashboard,
)

records = st.session_state.get(
    "analysis_results",
    (),
)

page = st.sidebar.selectbox(
    "Selecione a página",
    (
        "Overview",
        "Correlação",
    ),
)

if page == "Overview":

    render_overview(records)

elif page == "Correlação":

    render_correlation_dashboard(records)
