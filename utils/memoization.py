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

from typing import Any, Callable, Generator, TypeVar

from services.storage import (
    REPO_CLASSIFICATION_NAMESPACE,
    read_results,
    save_results,
)

T = TypeVar("T")


def cached_classify(
    classify_fn: Callable[[], Generator[Any, None, None]], content_hash: str
) -> Generator[Any, None, None]:
    """Memoização via cache em disco para classificações LLM (sem estado global).

    Fluxo de lookup:
    1. Lê o cache em disco via storage.py
    2. Se legível por inteiro: retorna o que estava persistido
    3. Se ausente ou corrompido: chama classify_fn, persiste, retorna

    Args:
        classify_fn: Função de classificação que retorna gerador.
        content_hash: Hash SHA-256 do repositório (chave de cache).

    Yields:
        Resultado de classificação (cached ou fresh).
    """
    # Uma leitura só decide o hit: perguntar "existe?" e depois "é legível?" em
    # chamadas separadas deixava um cache corrompido virar hit vazio. O namespace
    # mantém estas classificações fora do espaço da Análise do dataset:
    # versionar uma não invalida a outra (issue #101).
    cached_results = read_results(content_hash, namespace=REPO_CLASSIFICATION_NAMESPACE)
    if cached_results is not None:
        yield from cached_results
        return

    # Cache miss: executar classificação fresh
    results = list(classify_fn())

    # Persistir para próximas sessões
    save_results(content_hash, results, namespace=REPO_CLASSIFICATION_NAMESPACE)
    yield from results


def clear_cache() -> None:
    """Limpa caches LRU de funções puras (normalize_language, normalize_label).

    Não afeta arquivos persistidos em disco (storage.py).
    Utilizado em testes para garantir estado limpo entre execuções.
    """
    from core.transforms.normalizing import normalize_language, normalize_label

    normalize_language.cache_clear()
    normalize_label.cache_clear()
