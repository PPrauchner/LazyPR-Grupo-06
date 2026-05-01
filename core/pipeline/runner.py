"""
core/pipeline/runner.py
========================
Orquestra a execução do pipeline funcional sobre o stream de registros,
permitindo ativar ou desativar etapas de análise de forma configurável.

Responsabilidades:
    - Implementar `run_pipeline(steps, source)` onde:
        · `steps` é uma lista de funções de transformação (etapas ativáveis),
          permitindo que o chamador inclua ou exclua etapas sem alterar o código.
        · `source` é um gerador/iterável de `PRRecord` produzido pela ingestão.
    - Aplicar cada etapa habilitada de forma lazy sobre o stream, sem
      materializar todos os registros em memória simultaneamente.
    - Retornar um gerador de `AnalysisResult` para consumo downstream
      pelas camadas de agregação e visualização.
    - Registrar métricas de execução (registros processados, etapas aplicadas)
      sem introduzir estado mutável global.

Não deve:
    - Conter lógica de transformação ou limpeza (responsabilidade de transforms/).
    - Realizar chamadas a LLMs ou I/O de arquivo.

Relacionado a:
    - Issue 01 (processamento sob demanda do dataset)
    - Issue 08 (ativação/desativação de filtros por etapa)
    - Regra Geral 05 (pipeline configurável com funções de ordem superior)
    - Regra Funcional 04 (avaliação preguiçosa via geradores)
    - Conceito-Chave 01 (lazy evaluation)
"""
