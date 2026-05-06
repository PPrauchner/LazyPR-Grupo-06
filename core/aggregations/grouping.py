"""
core/aggregations/grouping.py
==============================
Fornece funções puras de agrupamento que organizam coleções de
`AnalysisResult` em estruturas indexadas por chaves compostas,
habilitando análises multidimensionais.

Responsabilidades:
    - Implementar `group_by(key_fn, records)` como função de ordem superior
      que agrupa registros de acordo com qualquer função de chave fornecida
      pelo chamador, sem assumir critério fixo.
    - Produzir agrupamentos por combinações de dimensões: (linguagem, tipo),
      (tipo, natureza), (linguagem, natureza, clareza), cobrindo os cruzamentos
      exigidos pelas visualizações das Issues 05, 06 e 07.
    - Retornar estruturas imutáveis mapeando chave → tupla de registros,
      nunca listas mutáveis.
    - Compor com `counters.py` e `metrics.py` para produzir sumarizações
      por grupo sem duplicar lógica.

Não deve:
    - Realizar I/O, chamadas a LLMs ou lógica de plotagem.
    - Modificar os registros agrupados.

Relacionado a:
    - Issue 05 (estratificação multidimensional)
    - Issue 07 (cruzamento de clareza, tipo e linguagem)
    - HU 07 (relação entre clareza, tipo de projeto, natureza e linguagem)
    - Regra Funcional 06 (composição de funções menores)
    - Conceito-Chave 09 (composição como mecanismo de pipeline)
"""
