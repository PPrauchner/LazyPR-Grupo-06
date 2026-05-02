"""
services/classifiers.py
========================
Orquestra as classificações semânticas realizadas pelos LLMs, gerenciando
estratégias de batching, cache e integração com o pipeline funcional.

Responsabilidades:
    - Implementar `classify_project_type(records)` que agrupa PRs do mesmo
      repositório em um único lote antes de chamar `llm_client.py`,
      evitando uma chamada por PR e reduzindo custo conforme a Dica 06.
    - Implementar `classify_pr_nature(record)` que envia título e corpo
      limpo de um PR ao LLM para determinar sua natureza
      (bug_fix, feature, refactoring, documentation).
    - Implementar `classify_clarity(record)` que instrui o LLM a avaliar
      a clareza da descrição, retornando um dos níveis do vocabulário
      controlado (insuficiente, básica, boa, excelente).
    - Verificar o cache (via utils/memoization.py) antes de qualquer
      chamada ao LLM, delegando a chamada real apenas em caso de cache miss.
    - Pós-processar a resposta JSON do LLM via funções puras de
      normalizing.py antes de construir o `AnalysisResult`.

Não deve:
    - Conter lógica de plotagem, agregação ou I/O de arquivo.
    - Substituir processamento funcional que deve ser feito no core/.

Relacionado a:
    - Issue 02 (categorização de repositórios)
    - Issue 03 (classificação da natureza do PR)
    - Issue 04 (avaliação de clareza das descrições)
    - HU 02, 03, 04 (enriquecimento semântico)
    - Regra Geral 04 (persistência para evitar recomputação)
    - Regra Geral 06 (LLM recebe dados pré-processados)
    - Dica 06 (agrupamento de PRs por repositório)
"""
