"""
services/storage.py
====================
Gerencia a persistência dos resultados de análise em disco, evitando
recomputações custosas em execuções subsequentes sobre o mesmo dataset.

Responsabilidades:
    - Persistir a lista de `AnalysisResult` de uma sessão de análise
      em arquivo JSON ou CSV local, indexada pelo hash SHA-256 do dataset
      de origem calculado em ingestion.py.
    - Implementar `load_results(dataset_hash)` que verifica se já existe
      uma análise persistida para aquele hash e a retorna como gerador,
      permitindo que o pipeline pule todas as etapas de classificação.
    - Implementar `save_results(dataset_hash, results)` que serializa os
      resultados de forma atômica, evitando arquivos corrompidos em caso
      de interrupção.
    - Implementar `has_cached_analysis(dataset_hash)` como predicado puro
      para decisão de fluxo no runner.py.
    - Manter um índice leve dos datasets já analisados para exibição
      na interface de upload.

Não deve:
    - Conter lógica de classificação ou transformação de dados.
    - Ser confundido com a memoização de chamadas LLM
      (responsabilidade de utils/memoization.py).

Relacionado a:
    - Issue 01 (análises persistidas para evitar recomputação)
    - Regra Geral 04 (persistência obrigatória de análises)
    - Dica 02 (hashlib para identificar conteúdo do dataset)
"""
