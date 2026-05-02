"""
core/aggregations/metrics.py
=============================
Fornece funções puras para o cálculo de métricas estatísticas sobre
grupos de `AnalysisResult`, como médias, medianas e distribuições
de tamanho de descrição.

Responsabilidades:
    - Calcular média, mediana, mínimo e máximo de `char_count` e `word_count`
      sobre qualquer coleção ou subgrupo de registros, via `reduce()`.
    - Calcular a distribuição de frequência dos níveis de clareza
      (insuficiente, básica, boa, excelente) por grupo, para alimentar
      os gráficos de correlação da Issue 07.
    - Implementar `correlation_summary(groups)` que, dado um dicionário
      de grupos (saída de grouping.py), computa métricas comparativas
      entre grupos para evidenciar padrões de contribuição.
    - Todas as funções devem ser puras e operar sobre estruturas imutáveis.

Não deve:
    - Realizar I/O, chamadas a LLMs ou lógica de plotagem.
    - Depender de bibliotecas estatísticas externas (numpy/pandas);
      usar apenas a stdlib e functools para manter a pureza funcional.

Relacionado a:
    - Issue 06 (distribuição de tamanho de descrição)
    - Issue 07 (correlação entre clareza, tipo e linguagem)
    - HU 06 (distribuição de chars/palavras estratificada)
    - HU 07 (padrões de contribuição entre dimensões)
    - Regra Funcional 01 (reduce() para cálculos de agregação)
    - Conceito-Chave 03 (reduce para agregação)
"""
