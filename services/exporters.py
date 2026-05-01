"""
services/exporters.py
======================
Implementa a exportação dos resultados enriquecidos para formatos
portáveis consumíveis por ferramentas externas de ciência de dados.

Responsabilidades:
    - Implementar `export_csv(results, filepath)` que serializa uma coleção
      de `AnalysisResult` em CSV, incluindo tanto os campos originais do
      dataset quanto as classificações semânticas geradas pelos LLMs.
    - Implementar `export_json(results, filepath)` com comportamento
      equivalente em formato JSON Lines, preservando o schema completo.
    - Implementar `to_download_bytes(results, fmt)` que retorna os dados
      serializados como `bytes` para uso direto com `st.download_button`
      do Streamlit, sem exigir escrita em disco intermediária.
    - Garantir que o schema exportado seja consistente e autodocumentado
      (cabeçalho CSV descritivo, campos JSON com nomes canônicos).

Não deve:
    - Realizar qualquer transformação ou filtragem dos dados.
    - Chamar LLMs ou acessar o pipeline funcional.

Relacionado a:
    - Issue 09 (exportação em CSV e JSON)
    - HU 09 (exportar resultados para uso em outras ferramentas)
"""
