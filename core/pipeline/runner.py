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
    - ADR 0003 (filtragem é recorte de visualização, não etapa do upload)
    - Regra Geral 05 (pipeline configurável com funções de ordem superior)
    - Regra Funcional 04 (avaliação preguiçosa via geradores)
    - Conceito-Chave 01 (lazy evaluation)
"""

from __future__ import annotations

from typing import Callable, Iterable, NamedTuple, Generator

from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from core.pipeline.composer import pipe
from core.transforms.filtering import Predicate, apply_filters

# ---------------------------------------------------------------------------
# Métricas de Execução (Imutável)
# ---------------------------------------------------------------------------


class PipelineMetrics(NamedTuple):
    """Métricas da execução do pipeline.

    Attributes:
        records_processed: Registros que atravessaram o pipeline.
        records_filtered: Registros descartados pelos predicados recebidos em
            `PipelineConfig.filter_predicates`. Vale 0 no caminho de análise
            do upload, que nunca passa predicados — o Filtro de Visualização
            da sidebar recorta a Análise já carregada e não conta aqui
            (ADR 0003).
        stages_applied: Nomes das etapas habilitadas, em ordem.
        total_time_ms: Tempo total de execução em milissegundos.
    """

    records_processed: int
    records_filtered: int
    stages_applied: tuple[str, ...]
    total_time_ms: float


# ---------------------------------------------------------------------------
# Tipos de Etapa
# ---------------------------------------------------------------------------

# Etapa de transformação: PRRecord → PRRecord (pode filtrar com StopIteration)
TransformStage = Callable[[Iterable[PRRecord]], Generator[PRRecord, None, None]]

# Etapa de enriquecimento: PRRecord → AnalysisResult
EnrichmentStage = Callable[[Iterable[PRRecord]], Generator[AnalysisResult, None, None]]


# ---------------------------------------------------------------------------
# Configuração de Pipeline
# ---------------------------------------------------------------------------


class PipelineConfig(NamedTuple):
    """Configuração do pipeline com etapas ativáveis.

    Attributes:
        enable_cleaning: Habilita a limpeza textual dos registros.
        enable_normalization: Habilita a normalização de campos canônicos.
        filter_predicates: Predicados de filtragem recebidos **por argumento**.
            A etapa de filtragem roda apenas quando esta tupla não é vazia;
            o padrão vazio garante que a Análise persistida cubra o dataset
            inteiro (ADR 0003 e Regra Geral 04).
        enable_classification: Habilita o enriquecimento semântico via LLM.
        enable_aggregation: Agregação é opcional (feita nas views).
    """

    enable_cleaning: bool = True
    enable_normalization: bool = True
    filter_predicates: tuple[Predicate, ...] = ()
    enable_classification: bool = True
    enable_aggregation: bool = False  # Agregação é opcional (para views)


# ---------------------------------------------------------------------------
# Execução do Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(
    source: Iterable[PRRecord],
    config: PipelineConfig = PipelineConfig(),
) -> Generator[AnalysisResult, None, None]:
    """Executa o pipeline de análise semântica sobre um stream de PRRecords.

    Sequência de etapas (ativáveis via config):
    1. **Normalização** (core/transforms/normalizing.py)
       - Normaliza language
       - Calcula char_count e word_count
    2. **Classificação** (services/classifiers.py)
       - Batching por repositório
       - Cache dois níveis (memória + disco)
       - Retorna AnalysisResult enriquecido
    3. **Filtragem** (core/transforms/filtering.py)
       - Só roda se `config.filter_predicates` não for vazia
       - Predicados chegam por argumento, nunca de estado global
       - Não é usada no caminho do upload: o recorte da sidebar é Filtro de
         Visualização, aplicado sobre a Análise já carregada (ADR 0003)

    Implementação pura via composição funcional:
    - Lazy evaluation com generators
    - Sem materialização de listas intermediárias
    - Configurável por etapa

    Args:
        source: Iterável de PRRecord (gerador ou lista).
        config: PipelineConfig com etapas ativáveis.

    Yields:
        AnalysisResult com todas as classificações aplicadas.

    Example:
        >>> from services.ingestion import ingest_csv
        >>> source = ingest_csv("data.csv")
        >>> config = PipelineConfig(enable_classification=True)
        >>> results = run_pipeline(source, config)
        >>> first = next(results)  # Lazy!
        >>> first.project_type
        'library'
    """
    # Importar aqui para evitar ciclos (core modules são puras)
    from core.transforms.cleaning import (
        clean_pr_record,
    )

    from core.transforms.normalizing import (
        normalize_pr_record,
    )
    from services.classifiers import classify_project_type

    # Pipeline configurável: cada etapa opcional
    stream = source

    # Etapa 1: Limpeza
    if config.enable_cleaning:

        stream = (clean_pr_record(record) for record in stream)

    # Etapa 2: Normalização (sempre ativa se habilitada)
    if config.enable_normalization:
        # Mapeia normalize_pr_record sobre cada PR
        # (nota: normalize_pr_record não filtra, então não precisa ser generator)
        stream = (normalize_pr_record(record) for record in stream)

    # Etapa 3: Classificação (core da Phase 2/3)
    if config.enable_classification:
        # Aplicar classificadores via composição
        # classify_project_type já retorna Generator[AnalysisResult]
        stream = classify_project_type(stream)
    else:
        # Se classification desabilitada, converter PRRecord para stub AnalysisResult
        # (com classifications vazias)

        def _stub_analysis_result(record: PRRecord) -> AnalysisResult:
            return AnalysisResult(
                id=record.id,
                html_url=record.html_url,
                repo=record.repo,
                path=record.path,
                body=record.body,
                diff_hunk=record.diff_hunk,
                author=record.author,
                author_association=record.author_association,
                commit_id=record.commit_id,
                line=record.line,
                language=record.language,
                created_at=record.created_at,
                project_type="other",
                pr_nature="other",
                clarity_level="unknown",
                char_count=len(record.body),
                word_count=len(record.body.split()),
            )

        stream = (_stub_analysis_result(record) for record in stream)

    # Etapa 4: Filtragem — só quando o chamador passa predicados por argumento.
    # Roda depois da classificação porque Predicate avalia AnalysisResult.
    if config.filter_predicates:
        stream = apply_filters(
            config.filter_predicates,
            stream,
        )

    # Etapa 5: Agregação (opcional, apenas para views específicas)
    # Se habilitada, seria aplicada aqui via core/aggregations/*
    if config.enable_aggregation:
        # Placeholder: agregação é opcional, feita no nivel de UI
        pass

    # Retornar stream final como generator (lazy)
    yield from stream


# ---------------------------------------------------------------------------
# Helpers para Construção de Pipelines Customizados
# ---------------------------------------------------------------------------


def build_pipeline(
    *stages: TransformStage | EnrichmentStage,
) -> Callable[[Iterable[PRRecord]], Generator]:
    """Constrói um pipeline customizado via composição de etapas.

    Implementa composição funcional: pipe(etapa1, etapa2, etapa3).

    Args:
        *stages: Funções de transformação/enriquecimento em ordem.

    Returns:
        Função que aceita Iterable[PRRecord] e retorna gerador do resultado final.

    Example:
        >>> from core.transforms.normalizing import normalize_pr_record
        >>> from services.classifiers import classify_project_type
        >>> pipeline = build_pipeline(
        ...     lambda records: (normalize_pr_record(r) for r in records),
        ...     classify_project_type,
        ... )
        >>> source = [pr1, pr2, pr3]
        >>> results = pipeline(source)
        >>> next(results).project_type
        'library'
    """
    return pipe(*stages)


# ---------------------------------------------------------------------------
# Aliases para Compatibilidade
# ---------------------------------------------------------------------------

# run_pipeline é a interface pública
# Para pipelines simples, usar config padrão
default_pipeline = run_pipeline
