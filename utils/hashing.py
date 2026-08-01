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

import hashlib
from typing import Generator, IO, Tuple

from core.models.pr_record import PRRecord


def hash_content(text: str) -> str:
    """Gera chave SHA-256 de uma string de conteúdo.

    Args:
        text: Conteúdo a hashear (ex: corpo de PR, descrição).

    Returns:
        Hex digest SHA-256 do conteúdo (64 caracteres).
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file_stream(stream: IO[str]) -> Tuple[str, Generator[str, None, None]]:
    """Calcula hash SHA-256 de arquivo em streaming sem materializar em memória.

    Percorre o stream uma vez para acumular o digest SHA-256 e, em seguida,
    reposiciona o ponteiro para o início via seek(0), retornando um novo
    gerador independente sobre o mesmo stream. Nenhuma lista de linhas é
    criada em nenhum momento.

    Args:
        stream: File object aberto em modo texto que suporte seek(0).

    Returns:
        Tupla (hex_digest, line_generator) onde line_generator produz as
        mesmas linhas do arquivo em ordem, de forma lazy.
    """
    sha256 = hashlib.sha256()
    for line in stream:
        if isinstance(line, bytes):
            sha256.update(line)
        else:
            sha256.update(line.encode("utf-8"))

    digest = sha256.hexdigest()

    stream.seek(0)

    return digest, (line for line in stream)


def hash_record(pr_record: PRRecord) -> str:
    """Gera chave SHA-256 única de um PRRecord.

    Identifica unicamente um repositório usando apenas o campo 'repo',
    permitindo cache compartilhado de análises por repo.

    Args:
        pr_record: Registro de PR a hashear.

    Returns:
        Hex digest SHA-256 que identifica o repositório de forma única.
    """
    return hash_content(pr_record.repo)
