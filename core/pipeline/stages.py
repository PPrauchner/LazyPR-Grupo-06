"""
core/pipeline/stages.py
=======================
Catálogo das Etapas do pipeline: funções de stream → stream que o chamador
passa como argumento para `run_pipeline` (Regra Geral 05).

Responsabilidades:
    - Expor cada Etapa como uma função de primeira classe, aplicável sobre um
      stream de registros de forma lazy.
    - Elevar as transformações registro → registro de `core/transforms/` para
      o nível de stream, que é o contrato de Etapa.
    - Oferecer o enriquecimento neutro usado quando a Classificação Semântica
      está desligada, para que o contrato de saída continue sendo
      `AnalysisResult` em qualquer combinação de Etapas.

Não deve:
    - Conter lógica de transformação própria (é de `core/transforms/`).
    - Realizar I/O, chamadas a LLM ou importar `services/`. A Etapa de
      Classificação Semântica vive em `services/classifiers.py` e é passada
      pelo chamador — é a única impura, e por isso mora fora de `core/`.

Relacionado a:
    - Regra Geral 05 (etapas como argumento, ativáveis pelo chamador)
    - ADR 0003 (o Filtro de Visualização não é Etapa do Pipeline)
    - Regra Funcional 04 (avaliação preguiçosa via geradores)
"""

from __future__ import annotations

from typing import Callable, Generator, Iterable

from core.models.analysis_result import (
    UNKNOWN_CLARITY_LEVEL,
    UNKNOWN_PR_NATURE,
    UNKNOWN_PROJECT_TYPE,
    AnalysisResult,
)
from core.models.pr_record import PRRecord
from core.transforms.cleaning import clean_pr_record
from core.transforms.filtering import Predicate, apply_filters
from core.transforms.normalizing import normalize_pr_record

# Uma Etapa consome um stream e devolve outro stream, sem materializar.
Stage = Callable[[Iterable], Iterable]


def clean_records(records: Iterable[PRRecord]) -> Generator[PRRecord, None, None]:
    """Aplica a limpeza textual a cada registro do stream.

    Args:
        records: Stream de PRRecord brutos.

    Yields:
        PRRecord com corpo e campos textuais limpos.
    """
    return (clean_pr_record(record) for record in records)


def normalize_records(records: Iterable[PRRecord]) -> Generator[PRRecord, None, None]:
    """Normaliza cada registro do stream para os valores canônicos.

    Args:
        records: Stream de PRRecord.

    Yields:
        PRRecord com `language` canônica.
    """
    return (normalize_pr_record(record) for record in records)


def enrich_without_classification(
    records: Iterable[PRRecord],
) -> Generator[AnalysisResult, None, None]:
    """Converte PRRecord em AnalysisResult sem consultar o LLM.

    É a Etapa usada quando a Classificação Semântica está desligada: as três
    classificações recebem o sentinela `unknown`, e as métricas de tamanho —
    que não são trabalho de LLM — continuam sendo calculadas.

    Args:
        records: Stream de PRRecord.

    Yields:
        AnalysisResult com classificações `unknown`.
    """
    return (
        AnalysisResult(
            **record._asdict(),
            project_type=UNKNOWN_PROJECT_TYPE,
            pr_nature=UNKNOWN_PR_NATURE,
            clarity_level=UNKNOWN_CLARITY_LEVEL,
            char_count=len(record.body),
            word_count=len(record.body.split()),
        )
        for record in records
    )


def filter_results(predicates: tuple[Predicate, ...]) -> Stage:
    """Constrói o recorte do Filtro de Visualização como Etapa.

    Os predicados chegam **por argumento**, nunca de estado global. O recorte
    não é Etapa do caminho de Análise (ADR 0003): quem o inclui na tupla de
    etapas é uma view que já trabalha sobre a Análise carregada.

    Args:
        predicates: Predicados a combinar por conjunção lógica.

    Returns:
        Etapa que filtra o stream de AnalysisResult.
    """
    return lambda records: apply_filters(predicates, records)
