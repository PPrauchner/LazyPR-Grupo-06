"""
utils/hashing.py
=================
Fornece funções puras para geração de hashes determinísticos de conteúdo,
utilizados como chaves de cache e identificadores de datasets.

Responsabilidades:
    - Implementar `hash_content(text)` que retorna o digest SHA-256 de
      uma string, usado como chave de memoização para classificações LLM.
    - Implementar `hash_file_stream(stream)` que calcula o hash SHA-256
      de um arquivo em streaming (sem carregar em memória), retornando
      o digest junto com o gerador de linhas para uso em ingestion.py.
    - Implementar `hash_record(pr_record)` para identificação canônica
      de um `PRRecord` específico, permitindo lookup granular no cache.
    - Todas as funções devem ser puras e determinísticas: o mesmo conteúdo
      sempre produz o mesmo hash.

Não deve:
    - Realizar I/O de arquivo diretamente (recebe streams como argumento).
    - Depender de estado externo ou variáveis globais.

Relacionado a:
    - Issue 01 (identificação de datasets para evitar reprocessamento)
    - Issue 02 (hash de conteúdo de repositório para cache de tipo)
    - Regra Geral 04 (persistência baseada em identidade do dataset)
    - Regra Funcional 02 (funções puras)
    - Dica 02 (hashlib para identificar conteúdo enviado ao LLM)
"""
