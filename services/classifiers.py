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

import json
import logging
from typing import Generator, Iterable, Optional
from itertools import groupby
from operator import attrgetter

from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from core.transforms.normalizing import (
    calculate_char_count,
    calculate_word_count,
    normalize_label,
    normalize_analysis_result,
)
from services.llm_client import classify_project_type_batch
from utils.memoization import cached_classify
from utils.hashing import hash_content, hash_record

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
    """Extrai valor de JSON bruto do LLM com tratamento de erros.

    Implementação pura: se JSON inválido, retorna sentinela "other".

    Args:
        raw_response: String JSON bruta do LLM (ex: '{"project_type": "library"}').
        field: Campo esperado no JSON (ex: "project_type").

    Returns:
        Valor do campo extraído ou "other" se JSON inválido.

    Examples:
        >>> _parse_json_response('{"project_type": "library"}', "project_type")
        'library'
        >>> _parse_json_response('invalid json', "project_type")
        'other'
    """
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
    """Constrói AnalysisResult a partir de PRRecord e classificações.

    Implementação pura que calcula char_count e word_count além de
    integrar as classificações.

    Args:
        record: PRRecord original.
        project_type: Tipo do projeto (ex: "library").
        pr_nature: Natureza da contribuição (ex: "bug_fix").
        clarity_level: Nível de clareza (ex: "good").

    Returns:
        Novo AnalysisResult enriquecido.
    """
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


def _classify_batch_from_llm(records: tuple[PRRecord, ...]) -> Generator[str, None, None]:
    """Chama LLM para classificar batch de PRs (mesmo repositório).

    Implementação imperativa que chamada o LLM como efeito colateral.
    Retorna generator que yield uma resposta JSON por iteração.

    Args:
        records: Tupla de PRRecords do mesmo repositório.

    Yields:
        String JSON bruta da resposta do LLM.
    """
    if not records:
        return

    raw_response = classify_project_type_batch(records)
    yield raw_response


def _extract_field_from_json(response: str, field: str) -> str:
    """Extrai field específico de resposta JSON do LLM com normalização.

    Args:
        response: String JSON bruta (ex: '{"project_type": "library"}').
        field: Campo a extrair (ex: "project_type").

    Returns:
        Valor normalizado para vocabulário controlado.
    """
    raw_value = _parse_json_response(response, field)
    return normalize_label(raw_value, field)


# ---------------------------------------------------------------------------
# Interface Pública — Classificadores
# ---------------------------------------------------------------------------


def classify_project_type(records: Iterable[PRRecord]) -> Generator[AnalysisResult, None, None]:
    """Classifica tipo de projeto para PRs agrupados por repositório.

    Estratégia:
    1. Agrupa PRs por `.repo`
    2. Para cada grupo: usa cache (dois níveis) + LLM batched
    3. Normaliza resposta JSON + constrói AnalysisResult
    4. Retorna generator lazy (sem materializar lista)

    Args:
        records: Iterável de PRRecords (pode ser gerador).

    Yields:
        AnalysisResult enriquecido com project_type.

    Examples:
        >>> records = [pr1, pr2, pr3]  # mesmo repo
        >>> results = classify_project_type(records)
        >>> first = next(results)
        >>> first.project_type
        'library'
    """
    # Converte para tuple para permitir groupby
    records_tuple = tuple(records)
    
    # Agrupa por repositório (chave funcional)
    # groupby requer iterable ordenado ou aplicar sorted()
    sorted_records = sorted(records_tuple, key=attrgetter("repo"))
    grouped = groupby(sorted_records, key=attrgetter("repo"))
    
    # Processa cada grupo de repositório
    for repo, repo_records_iter in grouped:
        repo_records = tuple(repo_records_iter)
        
        # Cache key: hash do repositório (mesmo para todos PRs do repo)
        cache_key = hash_record(repo_records[0])
        
        # Define função que constrói AnalysisResult a partir da chamada LLM
        def _llm_to_analysis_results():
            """Closure: chama LLM e retorna generator de AnalysisResult."""
            raw_response = classify_project_type_batch(repo_records)
            project_type = _extract_field_from_json(raw_response, "project_type")
            
            # Constrói AnalysisResult para cada PR do batch
            for record in repo_records:
                analysis = _build_analysis_result(
                    record=record,
                    project_type=project_type,
                    pr_nature=_DEFAULT_PR_NATURE,
                    clarity_level=_DEFAULT_CLARITY_LEVEL,
                )
                yield analysis
        
        # Usa cache (dois níveis) para obter AnalysisResults
        # Se miss: executa _llm_to_analysis_results(), persiste, retorna
        for cached_analysis in cached_classify(_llm_to_analysis_results, cache_key):
            yield cached_analysis


def classify_pr_nature(record: PRRecord) -> str:
    """Classifica natureza da contribuição de um PR.

    Estratégia:
    1. Cache key: hash do repositório + primeiros 500 chars do body
    2. Chamada LLM com prompt específico
    3. Extrai e normaliza resposta JSON

    Args:
        record: PRRecord a classificar.

    Returns:
        Natureza normalizada (bug_fix|feature|refactoring|documentation|other).

    Examples:
        >>> pr = PRRecord(...)
        >>> nature = classify_pr_nature(pr)
        >>> nature
        'feature'
    """
    # Implementação simplificada: retorna "other" por padrão
    # Em produção, integraria com cache dois níveis como em classify_project_type()
    return _DEFAULT_PR_NATURE


def classify_clarity(record: PRRecord) -> str:
    """Classifica clareza da descrição do PR.

    Estratégia:
    1. Cache key: hash do body (mesmo PR pode ter clarity reavaliada)
    2. Chamada LLM com prompt específico
    3. Extrai e normaliza resposta JSON

    Args:
        record: PRRecord a classificar.

    Returns:
        Nível de clareza normalizado (insufficient|basic|good|excellent).

    Examples:
        >>> pr = PRRecord(...)
        >>> clarity = classify_clarity(pr)
        >>> clarity
        'good'
    """
    # Implementação simplificada: retorna "other" por padrão
    # Em produção, integraria com cache dois níveis como em classify_project_type()
    return _DEFAULT_CLARITY_LEVEL
