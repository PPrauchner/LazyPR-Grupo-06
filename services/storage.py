"""
services/storage.py
====================
Gerencia a persistência dos resultados de análise em disco, evitando
recomputações custosas em execuções subsequentes sobre o mesmo dataset.

Responsabilidades:
    - Persistir a lista de `AnalysisResult` de uma sessão de análise
      em arquivo JSON ou CSV local, indexada pelo hash SHA-256 do dataset
      de origem calculado em ingestion.py.
    - Implementar `load_results(dataset_hash)` que verifica se já existe
      uma análise persistida para aquele hash e a retorna como gerador,
      permitindo que o pipeline pule todas as etapas de classificação.
    - Implementar `save_results(dataset_hash, results)` que serializa os
      resultados de forma atômica, evitando arquivos corrompidos em caso
      de interrupção.
    - Implementar `has_cached_analysis(dataset_hash)` como predicado puro
      para decisão de fluxo no runner.py.
    - Manter um índice leve dos datasets já analisados para exibição
      na interface de upload.

Não deve:
    - Conter lógica de classificação ou transformação de dados.
    - Ser confundido com a memoização de chamadas LLM
      (responsabilidade de utils/memoization.py).

Relacionado a:
    - Issue 01 (análises persistidas para evitar recomputação)
    - Regra Geral 04 (persistência obrigatória de análises)
    - Dica 02 (hashlib para identificar conteúdo do dataset)
"""

import json
import os
from pathlib import Path
from typing import Generator

from core.models.analysis_result import AnalysisResult

# Espaços de nomes do cache. Cada um vira um subdiretório de CACHE_DIR e tem a
# própria versão de esquema, para que um bump atinja só o cache afetado.
#
# - ANALYSIS_NAMESPACE: a Análise do dataset, indexada pelo hash do arquivo.
# - REPO_CLASSIFICATION_NAMESPACE: as classificações de LLM por repositório,
#   gravadas por utils/memoization.py::cached_classify().
ANALYSIS_NAMESPACE = "analysis"
REPO_CLASSIFICATION_NAMESPACE = "repo-classification"

# Versão do esquema da Análise persistida. Trocar este valor invalida as Análises
# existentes: elas passam a ser gravadas e procuradas sob outro nome de arquivo, e
# as antigas simplesmente dão miss e são reprocessadas sozinhas.
#
# "v2" invalida as Análises gravadas antes da issue #82, quando os filtros da
# sidebar podiam recortar o stream antes da persistência — uma Análise truncada
# ficava indistinguível de uma completa. Reprocessar não exige ação humana:
# basta subir o dataset de novo, que ele será analisado por inteiro.
CACHE_SCHEMA_VERSION = "v2"

# Versão do esquema das classificações por repositório. Independente da Análise:
# esse cache nunca esteve truncado (o Filtro de Visualização recortava o stream
# depois dele), e descartá-lo custa cota do Groq à toa (issue #101).
REPO_CLASSIFICATION_SCHEMA_VERSION = "v1"


def _get_cache_dir() -> Path:
    """Obtém o diretório de cache configurável.

    Lê variável de ambiente CACHE_DIR, com fallback para ".cache".

    Returns:
        Caminho do diretório de cache como Path.
    """
    cache_dir = os.getenv("CACHE_DIR", ".cache")
    return Path(cache_dir)


def _schema_version(namespace: str) -> str:
    """Obtém a versão de esquema vigente de um espaço de nomes.

    Args:
        namespace: Espaço de nomes do cache.

    Returns:
        Versão de esquema aplicada ao nome dos arquivos daquele espaço.
    """
    return (
        CACHE_SCHEMA_VERSION
        if namespace == ANALYSIS_NAMESPACE
        else REPO_CLASSIFICATION_SCHEMA_VERSION
    )


def _cache_path(
    repo_hash: str, suffix: str = "json", namespace: str = ANALYSIS_NAMESPACE
) -> Path:
    """Monta o caminho versionado do arquivo de cache num espaço de nomes.

    Args:
        repo_hash: Hash SHA-256 único do dataset ou do batch de repositório.
        suffix: Extensão do arquivo ("json" para o definitivo, "tmp.json"
            para o temporário da escrita atômica).
        namespace: Espaço de nomes do cache (subdiretório de CACHE_DIR).

    Returns:
        Caminho do arquivo, sob o subdiretório do namespace e prefixado pela
        versão de esquema daquele namespace.
    """
    version = _schema_version(namespace)
    return _get_cache_dir() / namespace / f"{version}-{repo_hash}.{suffix}"


def has_cached_analysis(repo_hash: str, namespace: str = ANALYSIS_NAMESPACE) -> bool:
    """Verifica se análise já foi persistida para um repositório.

    Args:
        repo_hash: Hash SHA-256 único do repositório.
        namespace: Espaço de nomes do cache a consultar.

    Returns:
        True se arquivo de cache existe e é válido, False caso contrário.
    """
    cache_path = _cache_path(repo_hash, namespace=namespace)
    return cache_path.exists() and cache_path.is_file()


def load_results(
    repo_hash: str, namespace: str = ANALYSIS_NAMESPACE
) -> Generator[AnalysisResult, None, None]:
    """Carrega análises persistidas de um repositório do cache.

    Lê arquivo JSON e reconstitui AnalysisResult.
    Em caso de arquivo inválido ou inexistente, retorna gerador vazio.

    Args:
        repo_hash: Hash SHA-256 único do repositório.
        namespace: Espaço de nomes do cache a consultar.

    Yields:
        AnalysisResult reconstituído do arquivo JSON.
    """
    cache_path = _cache_path(repo_hash, namespace=namespace)

    if not cache_path.exists():
        return

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            # Laço justificado: yield com **unpacking exige generator function explícita;
            # yield from map(lambda d: AnalysisResult(**d), data) seria equivalente mas menos legível.
            for item in data:
                yield AnalysisResult(**item)
    except (json.JSONDecodeError, KeyError, TypeError):
        return


def save_results(
    repo_hash: str,
    results: list[AnalysisResult],
    namespace: str = ANALYSIS_NAMESPACE,
) -> None:
    """Salva análises em arquivo JSON com escrita atômica.

    Escreve para arquivo temporário e renomeia atomicamente
    para evitar corrupção em caso de interrupção.

    Args:
        repo_hash: Hash SHA-256 único do repositório.
        results: Lista de AnalysisResult a persistir.
        namespace: Espaço de nomes do cache em que gravar.
    """
    cache_path = _cache_path(repo_hash, namespace=namespace)
    temp_path = _cache_path(repo_hash, suffix="tmp.json", namespace=namespace)

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    serialized = [result._asdict() for result in results]

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    os.replace(temp_path, cache_path)
