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
    classify_pr_nature_and_clarity_single,
)
from utils.hashing import hash_content
from utils.memoization import cached_classify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_DEFAULT_PROJECT_TYPE = "other"
_DEFAULT_PR_NATURE = "other"
_DEFAULT_CLARITY_LEVEL = "unknown"


# ---------------------------------------------------------------------------
# Helpers Privados
# ---------------------------------------------------------------------------


def _extract_field_from_json(raw_response: str, field: str) -> str:
    """Extrai e normaliza valor do JSON retornado pelo LLM.

    Parse JSON bruto, extrai campo específico e normaliza via normalize_label().
    Se parsing falhar ou campo não existir, retorna valor default apropriado.

    Args:
        raw_response: String JSON bruta do LLM
        field: Campo a extrair ("project_type", "pr_nature", "clarity_level")

    Returns:
        Valor normalizado ou default se falhar
    """
    try:
        parsed = json.loads(raw_response.strip())
        if not isinstance(parsed, dict) or field not in parsed:
            value = _get_default_for_field(field)
            logger.warning(
                f"Campo '{field}' não encontrado em JSON. Usando default: {value}"
            )
            return value

        raw_value = parsed[field]
        if not raw_value:
            return _get_default_for_field(field)

        # Normalizar via normalize_label
        normalized = normalize_label(str(raw_value).strip(), field)
        return normalized

    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        default = _get_default_for_field(field)
        logger.warning(
            f"Erro ao parsear JSON para '{field}': {str(e)[:100]}. Usando default: {default}"
        )
        return default


def _get_default_for_field(field: str) -> str:
    """Retorna valor default apropriado para cada campo."""
    if field == "project_type":
        return _DEFAULT_PROJECT_TYPE
    elif field == "pr_nature":
        return _DEFAULT_PR_NATURE
    elif field == "clarity_level":
        return _DEFAULT_CLARITY_LEVEL
    return "other"


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


# ---------------------------------------------------------------------------
# Interface Pública — Classificadores
# ---------------------------------------------------------------------------


def classify_project_type(
    records: Iterable[PRRecord],
) -> Generator[AnalysisResult, None, None]:
    """Classifica tipo de projeto para PRs agrupados por repositório.

    Estratégia: agrupa PRs por repo, faz uma chamada LLM por repo (não por PR),
    cache em dois níveis (memória + disco), retorna AnalysisResult via lazy generator.

    Args:
        records: Stream lazy de PRRecord

    Yields:
        AnalysisResult com project_type classificado
    """
    from core.aggregations.grouping import group_by

    def get_repo(record: PRRecord) -> str:
        return record.repo

    # Agrupa por repo via reduce() sobre o stream completo — materialização necessária porque
    # groupby lazy (itertools) exige stream pré-ordenado que também materializaria via sorted().
    # Trade-off documentado: classificação por repo impõe O(n) memória neste ponto do pipeline.
    repo_groups = group_by(get_repo, records)

    for repo, repo_records in repo_groups.items():
        # repo_records já é tupla de group_by
        if not repo_records:
            continue

        # Cache key inclui repo + IDs ordenados para distinguir batches de datasets distintos
        batch_ids = "".join(str(r.id) for r in sorted(repo_records, key=lambda r: r.id))
        cache_key = hash_content(f"{repo_records[0].repo}:{batch_ids}")

        def _llm_to_analysis_results(rcs=repo_records):
            """Closure: chama LLM e retorna tupla materializada de AnalysisResult."""
            raw_response = classify_project_type_batch(rcs)
            project_type = _extract_field_from_json(raw_response, "project_type")

            def _classify_record(record: PRRecord) -> AnalysisResult:
                # Uma única chamada LLM por PR para pr_nature + clarity_level (reduz RPM)
                combined = classify_pr_nature_and_clarity_single(record)
                return _build_analysis_result(
                    record=record,
                    project_type=project_type,
                    pr_nature=_extract_field_from_json(combined, "pr_nature"),
                    clarity_level=_extract_field_from_json(combined, "clarity_level"),
                )

            return tuple(map(_classify_record, rcs))

        # Lookup por ID para reatribuir language e created_at do PRRecord atual ao resultado do cache
        records_by_id = {r.id: r for r in repo_records}

        # Usa cache (dois níveis) para obter AnalysisResults
        for cached_analysis in cached_classify(_llm_to_analysis_results, cache_key):
            record = records_by_id.get(cached_analysis.id)
            if record is not None:
                # language e created_at sempre refletem o dado atual (não o valor congelado no cache)
                yield cached_analysis._replace(
                    language=record.language,
                    created_at=record.created_at,
                )
            else:
                yield cached_analysis


def classify_pr_nature(record: PRRecord) -> str:
    """Classifica natureza da contribuição de um PR."""
    raw_response = classify_pr_nature_single(record)
    return _extract_field_from_json(raw_response, "pr_nature")


def classify_clarity(record: PRRecord) -> str:
    """Classifica clareza da descrição do PR."""
    raw_response = classify_clarity_single(record)
    return _extract_field_from_json(raw_response, "clarity_level")
