"""Fornece utilitários de memoização para evitar recomputações custosas.

Responsabilidades:
    - Implementar `cached_classify(fn, content_hash)` como wrapper que verifica
      persistência de cache em disco via storage.py antes de executar função.
    - Para classificações LLM, usar storage.py (has_cached_analysis, load_results, save_results)
      que persiste cache entre sessões.
    - Evitar estado global mutável. Delegar persistência a storage.py.

Não deve:
    - Conter lógica de negócio, transformação ou plotagem.
    - Manter cache em memória global mutável (usar functools.lru_cache em core/).

Relacionado a:
    - Issues 02, 03, 04 (evitar reclassificação de conteúdo idêntico)
    - Regra Geral 04 (persistência para evitar recomputação)
    - Regra Funcional 05 (memoização)
    - Conceito-Chave 02 (memoização para caching de chamadas LLM)
"""

from typing import Any, Callable, Dict, Generator, TypeVar

from services.storage import has_cached_analysis, load_results, save_results

T = TypeVar("T")


def cached_classify(
    classify_fn: Callable[[], Generator[Any, None, None]], content_hash: str
) -> Generator[Any, None, None]:
    """Memoização via cache em disco para classificações LLM (sem estado global).

    Fluxo de lookup:
    1. Verifica cache em disco via storage.py
    2. Se existe: carrega e retorna
    3. Se não existe: chama classify_fn, persiste, retorna

    Args:
        classify_fn: Função de classificação que retorna gerador.
        content_hash: Hash SHA-256 do repositório (chave de cache).

    Yields:
        Resultado de classificação (cached ou fresh).
    """
    # Verificar se já está em cache em disco
    if has_cached_analysis(content_hash):
        cached_results = list(load_results(content_hash))
        yield from cached_results
        return

    # Cache miss: executar classificação fresh
    results = list(classify_fn())

    # Persistir para próximas sessões
    save_results(content_hash, results)
    yield from results


def clear_cache() -> None:
    """Limpa todo o cache em memória.

    Nota: Não afeta arquivos persistidos em disco.
    Útil para "reset cache" na interface ou entre testes.
    """
    with _cache_lock:
        _in_memory_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """Retorna estatísticas de cache (hits, misses, total).

    Returns:
        Dict com chaves 'hits', 'misses', 'total'.
    """
    with _stats_lock:
        total = _cache_stats["hits"] + _cache_stats["misses"]
        return {
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "total": total,
        }
