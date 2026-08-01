"""
services/ingestion.py
======================
Implementa a camada de ingestão do dataset como efeito colateral isolado,
expondo geradores que produzem registros sob demanda sem carregar o arquivo
inteiro em memória.

Responsabilidades:
    - Implementar `stream_csv(filepath)` como gerador que lê o dataset do
      Kaggle (github-public-pull-request-comments) linha a linha, produzindo
      um `PRRecord` por iteração via `yield`.
    - Implementar `stream_json(filepath)` com comportamento equivalente para
      datasets em formato JSON Lines.
    - Aceitar upload de arquivo via interface Streamlit e redirecionar o
      stream para os geradores, sem exigir que o arquivo seja salvo em disco
      integralmente antes do processamento.
    - Calcular o hash SHA-256 do arquivo durante a leitura (sem segunda
      passagem), expondo-o para que `storage.py` determine se o dataset
      já foi analisado anteriormente.
    - Isolar completamente o I/O de arquivo: nenhuma outra camada deve
      abrir arquivos diretamente.

Não deve:
    - Conter lógica de limpeza, normalização ou classificação.
    - Chamar LLMs.

Relacionado a:
    - Issue 01 (upload e ingestão de datasets)
    - HU 01 (fazer upload de datasets para análise)
    - Regra Geral 02 (geradores para lazy evaluation)
    - Regra Funcional 04 (yield, expressões geradoras, itertools)
    - Conceito-Chave 01 (lazy evaluation via geradores)
    - Dica 01 (módulos csv/json com geradores linha a linha)
"""

import csv
import json
import hashlib
from typing import BinaryIO, Iterator, Union, Any
from contextlib import contextmanager
from urllib.parse import urlparse

from core.models.pr_record import PRRecord

# Mapeamento de extensão de arquivo → linguagem canônica (mesma forma usada por normalize_language)
_EXTENSION_TO_LANGUAGE: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "java": "java",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "rs": "rust",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "c": "c",
    "cs": "csharp",
    "dart": "dart",
    "kt": "kotlin",
    "jsx": "javascript",
    "tsx": "typescript",
    "swift": "swift",
    "scala": "scala",
}


def _infer_language_from_path(path: str) -> str | None:
    """Infere linguagem de programação a partir da extensão do arquivo no campo path.

    O dataset do Kaggle não possui coluna 'language'; esta função deriva a linguagem
    da extensão do arquivo comentado (ex: "src/main.go" → "go").

    Args:
        path: Caminho do arquivo no repositório (ex: "src/math/rand/rand.go").

    Returns:
        Linguagem canônica (ex: "go", "python") ou None se extensão desconhecida.
    """
    if not path or "." not in path:
        return None
    ext = path.rsplit(".", 1)[-1].lower()
    return _EXTENSION_TO_LANGUAGE.get(ext)


@contextmanager
def _get_file_buffer(file_target: Union[str, BinaryIO]) -> Iterator[BinaryIO]:
    """
    Gerencia o contexto de buffers de arquivo isolando operações de I/O.

    Suporta tanto caminhos de arquivos físicos locais quanto buffers alocados
    em memória, delegando o controle de ciclo de vida do recurso de forma
    agnóstica à interface de chamada.

    Args:
        file_target: Caminho do arquivo físico (str) ou buffer binário em memória.

    Yields:
        Um iterador contendo o buffer binário aberto pronto para leitura.
    """
    if isinstance(file_target, str):
        with open(file_target, "rb") as f:
            yield f
    else:
        yield file_target


def _extract_repo_from_url(html_url: str) -> str:
    """Extrai o campo 'repo' no formato 'owner/name' da html_url do GitHub.

    Args:
        html_url: URL completa do comentário (ex: "https://github.com/golang/go/pull/...").

    Returns:
        String no formato "owner/name", ou string vazia se a URL for inválida.
    """
    try:
        parts = urlparse(html_url).path.strip("/").split("/")
        return f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else ""
    except Exception:
        return ""


def _map_csv_row(row: dict) -> PRRecord:
    """Converte linha bruta do CSV do Kaggle para PRRecord com mapeamento explícito.

    O dataset usa 'user' onde PRRecord espera 'author'. Os campos 'repo' e
    'language' não existem no dataset e são derivados ou preenchidos com None.
    Os tipos numéricos 'id' e 'line' são convertidos de str para int.

    Args:
        row: Dicionário com os campos da linha CSV (schema real do Kaggle).

    Returns:
        PRRecord imutável com campos corretamente mapeados e tipados.
    """
    html_url = row.get("html_url", "")
    raw_line = row.get("line", None)

    return PRRecord(
        id=int(row.get("id", 0)),
        html_url=html_url,
        repo=_extract_repo_from_url(html_url),
        path=row.get("path", ""),
        body=row.get("body", ""),
        diff_hunk=row.get("diff_hunk", ""),
        author=row.get("user", ""),
        author_association=row.get("author_association", ""),
        commit_id=row.get("commit_id", ""),
        line=int(raw_line) if raw_line else 0,
        language=row.get("language")
        or _infer_language_from_path(row.get("path", ""))
        or None,
        created_at=row.get("created_at") or None,
    )


def read_header_lazily(file_target: Union[str, BinaryIO]) -> tuple[str, ...]:
    """
    Lê a primeira linha de um arquivo CSV sob demanda para extração do cabeçalho.

    Consome estritamente os bytes necessários para identificar as colunas,
    garantindo eficiência de memória. Em buffers mutáveis em memória, o ponteiro
    de leitura é redefinido para a posição inicial após a extração, garantindo
    integridade para consumos futuros.

    Args:
        file_target: Caminho do arquivo físico ou buffer binário em memória.

    Returns:
        Tupla imutável contendo os nomes das colunas identificadas no cabeçalho.
        Retorna uma tupla vazia em caso de falha de decodificação ou arquivo vazio.
    """
    with _get_file_buffer(file_target) as file_buffer:
        try:
            first_line_bytes = file_buffer.readline()
            if not first_line_bytes:
                return ()

            first_line = first_line_bytes.decode("utf-8", errors="replace")
            header = tuple(next(csv.reader([first_line])))
        except (StopIteration, UnicodeDecodeError):
            header = ()
        finally:
            if not isinstance(file_target, str):
                file_buffer.seek(0)

    return header


def stream_csv(
    file_target: Union[str, BinaryIO], hasher: Any = None
) -> Iterator[PRRecord]:
    """
    Itera sobre um arquivo CSV de forma lazy produzindo instâncias de PRRecord.

    Implementa decodificação sob demanda acoplada ao cálculo simultâneo
    do hash SHA-256, garantindo o processamento completo e a assinatura
    digital do arquivo em uma única passagem de I/O.

    Args:
        file_target: Caminho do arquivo físico ou buffer binário em memória.
        hasher: Instância opcional de `hashlib.sha256` para acúmulo do hash
            durante o percurso dos bytes brutos.

    Yields:
        Instâncias brutas de `PRRecord` mapeadas a partir das linhas do CSV.
    """
    if hasher is None:
        hasher = hashlib.sha256()

    with _get_file_buffer(file_target) as file_buffer:

        def lazy_decoder_and_hasher() -> Iterator[str]:
            for line_bytes in file_buffer:
                hasher.update(line_bytes)
                yield line_bytes.decode("utf-8", errors="replace")

        reader = csv.DictReader(lazy_decoder_and_hasher())

        yield from map(_map_csv_row, reader)


def stream_json(
    file_target: Union[str, BinaryIO], hasher: Any = None
) -> Iterator[PRRecord]:
    """
    Itera sobre um arquivo JSON Lines de forma lazy produzindo PRRecords.

    O processo de decodificação converte bytes diretamente para dicionários
    enquanto acumula o hash SHA-256 do arquivo original simultaneamente,
    ignorando linhas estruturalmente vazias durante a varredura.

    Args:
        file_target: Caminho do arquivo físico ou buffer binário em memória.
        hasher: Instância opcional de `hashlib.sha256` para acúmulo do hash
            durante o percurso dos bytes brutos.

    Yields:
        Instâncias brutas de `PRRecord` mapeadas a partir das linhas JSON.
    """
    if hasher is None:
        hasher = hashlib.sha256()

    with _get_file_buffer(file_target) as file_buffer:
        for line_bytes in file_buffer:
            hasher.update(line_bytes)

            if not line_bytes.strip():
                continue

            row_data = json.loads(line_bytes.decode("utf-8", errors="replace"))
            yield _map_csv_row(row_data)


def ingest_dataset(
    uploaded_file,
):
    """
    Executa pipeline principal de ingestão, retornando gerador lazy.
    """

    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        return stream_csv(uploaded_file)

    elif filename.endswith(".json"):
        return stream_json(uploaded_file)

    else:

        raise ValueError("Formato de arquivo não suportado.")
