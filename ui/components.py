"""
ui/components.py
=================
Fornece widgets e elementos visuais reutilizáveis do Streamlit que
encapsulam padrões de exibição comuns ao longo do dashboard.

Responsabilidades:
    - Implementar `metric_card(label, value, delta)` para exibição de
      KPIs de alto nível (total de PRs, distribuição de clareza, etc.).
    - Implementar `data_table(records, columns)` para renderização
      interativa de subconjuntos do dataset filtrado com paginação.
    - Implementar `status_banner(message, type)` para feedback visual
      de progresso do pipeline (ingestão, classificação, exportação).
    - Implementar `download_buttons(results)` que integra com
      `exporters.py` para oferecer botões de download CSV e JSON
      diretamente na interface.
    - Todos os componentes devem receber dados já processados como
      argumento — nenhuma lógica de transformação ou acesso a estado
      global dentro deste módulo.

Não deve:
    - Chamar o pipeline, LLMs ou funções de agregação diretamente.
    - Compartilhar estado mutável entre componentes.

Relacionado a:
    - Issue 05, 06, 07 (visualizações do dashboard)
    - Issue 09 (botões de download)
    - HU 09 (exportação acessível pela interface)
    - Regra Geral 08 (interface gráfica obrigatória)
"""
