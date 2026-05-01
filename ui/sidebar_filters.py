"""
ui/sidebar_filters.py
======================
Implementa os controles interativos de filtragem global do dashboard,
traduzindo seleções do usuário em predicados funcionais compostos.

Responsabilidades:
    - Renderizar widgets de filtragem no sidebar do Streamlit para cada
      dimensão analisável: linguagem, tipo de projeto, natureza da
      contribuição e nível de clareza.
    - Implementar `get_active_filters()` que lê o estado atual dos
      widgets e retorna uma função de filtro composta (via
      `core/transforms/filtering.py`) pronta para ser aplicada ao
      stream de dados.
    - Garantir que a mudança de qualquer filtro reaplique o pipeline
      sobre os dados já carregados em cache, sem reler o arquivo.
    - Manter os filtros sincronizados com `st.session_state` para
      preservar as seleções do analista durante a navegação entre páginas.

Não deve:
    - Conter lógica de agregação, plotagem ou acesso a LLMs.
    - Modificar diretamente os dados do dataset.

Relacionado a:
    - Issue 08 (motor de filtros dinâmicos globais)
    - HU 08 (filtrar todas as visualizações simultaneamente)
    - Conceito-Chave 07 (lambda para filtros inline)
"""
