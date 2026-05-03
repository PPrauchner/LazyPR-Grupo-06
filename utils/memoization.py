"""
utils/memoization.py
=====================
Fornece utilitários de memoização para evitar recomputações custosas,
especialmente chamadas repetidas a LLMs com entradas idênticas.

Responsabilidades:
    - Implementar `memoize(fn)` como decorador de memoização manual
      usando dicionário imutável por chave, como alternativa configurável
      ao `functools.lru_cache` para funções com argumentos não-hashable.
    - Expor `cached_classify(classify_fn, content_hash)` que verifica
      o cache em memória antes de delegar ao classificador real,
      utilizando o hash do conteúdo como chave de lookup.
    - Integrar com `storage.py` para persistência cross-sessão do cache
      de classificações, garantindo que a Regra Geral 04 seja atendida
      mesmo após reinicialização da aplicação.
    - Registrar estatísticas de cache hit/miss para exibição opcional
      na interface de progresso.

Não deve:
    - Conter lógica de negócio, transformação ou plotagem.
    - Armazenar dados sensíveis ou o conteúdo completo dos PRs no cache.

Relacionado a:
    - Issues 02, 03, 04 (evitar reclassificação de conteúdo idêntico)
    - Regra Geral 04 (persistência para evitar computações repetidas)
    - Regra Funcional 05 (memoização com lru_cache ou manual)
    - Conceito-Chave 02 (memoização para caching de chamadas LLM)
    - Dica 02 (hashlib + lru_cache)
"""

import threading
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from services.storage import has_cached_analysis, load_results, save_results

T = TypeVar("T")

# Cache em memória global: content_hash -> resultado classificado
_in_memory_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()

# Estatísticas de cache
_cache_stats = {"hits": 0, "misses": 0}
_stats_lock = threading.Lock()


def _update_stats(hit: bool) -> None:
    """Atualiza contadores de cache hit/miss (thread-safe)."""
    with _stats_lock:
        if hit:
            _cache_stats["hits"] += 1
        else:
            _cache_stats["misses"] += 1


def cached_classify(
    classify_fn: Callable[..., Generator[Any, None, None]], content_hash: str
) -> Generator[Any, None, None]:
    """
    Memoização em dois níveis para classificações LLM:
    1. Cache em memória (L1) — para reutilização dentro da mesma sessão
    2. Cache em disco (L2) — para reutilização entre sessões

    Fluxo:
    - Se content_hash está em memória → retorna valor (HIT L1)
    - Elif arquivo de cache existe em disco → carrega (HIT L2)
    - Else → chama classify_fn (MISS) e persiste resultado

    Args:
        classify_fn: Função real de classificação que retorna
                     gerador de resultados.
        content_hash: Hash SHA-256 do repositório (chave de cache).

    Yields:
        Resultado de classificação (em memória ou do LLM).
    """
    # Lookup L1 (memória)
    with _cache_lock:
        if content_hash in _in_memory_cache:
            _update_stats(hit=True)
            # Faz yield from para produzir itens individuais
            yield from _in_memory_cache[content_hash]
            return

    # Lookup L2 (disco)
    if has_cached_analysis(content_hash):
        _update_stats(hit=True)
        # Carrega e materializa resultados
        cached_results = list(load_results(content_hash))
        # Armazena em memória para próximas chamadas
        with _cache_lock:
            _in_memory_cache[content_hash] = cached_results
        # Faz yield from para produzir itens individuais
        yield from cached_results
        return

    # Miss — chama função real e materializa resultado
    _update_stats(hit=False)
    results = list(classify_fn())  # Materializa gerador

    # Armazena em memória
    with _cache_lock:
        _in_memory_cache[content_hash] = results

    # Persiste em disco (async seria ideal, mas mantém síncrono por segurança)
    save_results(content_hash, results)

    # Faz yield from para produzir itens individuais
    yield from results


def clear_cache() -> None:
    """
    Limpa todo o cache em memória.

    Útil para "reset cache" na interface ou entre testes.
    Não afeta arquivos persistidos em disco.
    """
    with _cache_lock:
        _in_memory_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """
    Retorna estatísticas de cache (hits, misses, total).

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
