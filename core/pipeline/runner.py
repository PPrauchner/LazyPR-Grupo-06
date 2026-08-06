"""
core/pipeline/runner.py
========================
Centraliza a execução do pipeline funcional sobre o stream de registros.

Responsabilidades:
    - Implementar `run_pipeline(steps, source)` onde:
        · `steps` é a tupla de Etapas (funções de stream → stream) recebida
          **por argumento**, o que permite ao chamador incluir ou excluir
          Etapas sem alterar código.
        · `source` é um gerador/iterável de `PRRecord` produzido pela ingestão.
    - Compor as Etapas recebidas de forma lazy sobre o stream, sem materializar
      todos os registros em memória simultaneamente.
    - Retornar um gerador do resultado final para consumo downstream pelas
      camadas de agregação e visualização.

Não deve:
    - Conhecer quais Etapas existem — o catálogo vive em `core/pipeline/stages.py`
      e a escolha é do chamador (`views/upload.py`).
    - Conter lógica de transformação ou limpeza (responsabilidade de transforms/).
    - Realizar chamadas a LLMs ou I/O de arquivo.

Relacionado a:
    - Issue 01 (processamento sob demanda do dataset)
    - ADR 0003 (o Filtro de Visualização não é Etapa do Pipeline)
    - Regra Geral 05 (pipeline configurável com funções de ordem superior)
    - Regra Funcional 04 (avaliação preguiçosa via geradores)
    - Conceito-Chave 01 (lazy evaluation)
"""

from __future__ import annotations

from typing import Generator, Iterable

from core.models.pr_record import PRRecord
from core.pipeline.composer import pipe
from core.pipeline.stages import Stage


def run_pipeline(
    steps: Iterable[Stage],
    source: Iterable[PRRecord],
) -> Generator:
    """Executa o pipeline compondo as Etapas recebidas como argumento.

    As Etapas são aplicadas na ordem em que chegam, cada uma consumindo o
    stream produzido pela anterior. Uma Etapa desligada pelo usuário
    simplesmente não está na tupla — não há flag nem ramificação aqui dentro.
    Uma tupla vazia devolve o stream de origem inalterado.

    Args:
        steps: Etapas do catálogo (`core/pipeline/stages.py`) ou qualquer
            função de stream → stream, na ordem de aplicação.
        source: Iterável de PRRecord (gerador ou tupla).

    Yields:
        Os registros produzidos pela última Etapa — `AnalysisResult` quando o
        chamador inclui uma Etapa de enriquecimento.

    Example:
        >>> from core.pipeline.stages import clean_records, normalize_records
        >>> from services.classifiers import classify_project_type
        >>> steps = (clean_records, normalize_records, classify_project_type)
        >>> results = run_pipeline(steps, stream_csv(arquivo))
        >>> next(results).project_type  # Lazy!
        'library'
    """
    yield from pipe(*steps)(source)
