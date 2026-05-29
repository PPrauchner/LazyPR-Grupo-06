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

from __future__ import annotations

import json
import logging
from itertools import groupby
from operator import attrgetter
from typing import Generator, Iterable

from core.models.analysis_result import AnalysisResult
from core.models.pr_record import PRRecord
from core.transforms.normalizing import (
    calculate_char_count,
    calculate_word_count,
    normalize_label,
)

from services.llm_client import (
    classify_project_type_batch,
    classify_pr_nature_single,
    classify_clarity_single,
)
from utils.hashing import hash_record
from utils.memoization import cached_classify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_DEFAULT_PROJECT_TYPE = "other"
_DEFAULT_PR_NATURE = "other"
_DEFAULT_CLARITY_LEVEL = "other"


# ---------------------------------------------------------------------------
# Helpers Privados
# ---------------------------------------------------------------------------


def _parse_json_response(raw_response: str, field: str) -> str:
    """Extrai valor de JSON bruto do LLM com tratamento de erros."""
    try:
        parsed = json.loads(raw_response.strip())
        if isinstance(parsed, dict) and field in parsed:
            value = parsed[field]
            return str(value).strip() if value else _DEFAULT_PROJECT_TYPE
        return _DEFAULT_PROJECT_TYPE
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning(f"Falha ao parsear JSON do LLM: {raw_response[:100]}")
        return _DEFAULT_PROJECT_TYPE


def _build_analysis_result(
    record: PRRecord,
    project_type: str,
    pr_nature: str,
    clarity_level: str,
) -> AnalysisResult:
    """Constrói AnalysisResult a partir de PRRecord e classificações."""
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
        project_type=project_type,
        pr_nature=pr_nature,
        clarity_level=clarity_level,
        char_count=calculate_char_count(record.body),
        word_count=calculate_word_count(record.body),
    )


def _extract_field_from_json(
    response: str,
    field: str,
) -> str:
    """
    Extrai campo JSON retornado pelo LLM
    e normaliza para o vocabulário controlado.
    """

    raw_value = _parse_json_response(
        response,
        field,
    )

    return normalize_label(
        raw_value,
        field,
    )

# ---------------------------------------------------------------------------
# Interface Pública — Classificadores
# ---------------------------------------------------------------------------


def classify_project_type(
    records: Iterable[PRRecord],
) -> Generator[AnalysisResult, None, None]:
    """Classifica tipo de projeto para PRs agrupados por repositório."""
    # Converte para tuple para permitir groupby
    records_tuple = tuple(records)

    # Agrupa por repositório (chave funcional)
    sorted_records = sorted(records_tuple, key=attrgetter("repo"))
    grouped = groupby(sorted_records, key=attrgetter("repo"))

    # Processa cada grupo de repositório
    for repo, repo_records_iter in grouped:
        repo_records = tuple(repo_records_iter)

        # Cache key: hash do repositório (mesmo para todos PRs do repo)
        cache_key = hash_record(repo_records[0])

        # Closure com late-binding fixado
        def _llm_to_analysis_results(rcs=repo_records):
            """Closure: chama LLM e retorna uma tupla materializada de AnalysisResult."""
            raw_response = classify_project_type_batch(rcs)
            project_type = _extract_field_from_json(raw_response, "project_type")

            # FIX DO BUG: Retorna uma tupla (imutável) em vez de usar yield!
            return tuple(
                _build_analysis_result(
                    record=record,
                    project_type=project_type,
                    pr_nature=_DEFAULT_PR_NATURE,
                    clarity_level=_DEFAULT_CLARITY_LEVEL,
                )
                for record in rcs
            )

        # Usa cache (dois níveis) para obter AnalysisResults
        for cached_analysis in cached_classify(_llm_to_analysis_results, cache_key):
            yield cached_analysis


def classify_pr_nature(record: PRRecord) -> str:
    """Classifica natureza da contribuição de um PR."""
    raw_response = classify_pr_nature_single(record)
    return _extract_field_from_json(raw_response, "pr_nature")


def classify_clarity(record: PRRecord) -> str:
    """Classifica clareza da descrição do PR."""
    raw_response = classify_clarity_single(record)
    return _extract_field_from_json(raw_response, "clarity_level")
