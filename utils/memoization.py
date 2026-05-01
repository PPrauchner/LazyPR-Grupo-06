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
