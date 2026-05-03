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
from dataclasses import asdict
from pathlib import Path
from typing import Generator, Iterable

from core.models.analysis_result import AnalysisResult


def _get_cache_dir() -> Path:
    """
    Obtém o diretório de cache configurável.

    Lê CACHE_DIR do ambiente (.env ou variável de sistema).
    Padrão: ".cache" na raiz do projeto.

    Returns:
        Caminho do diretório de cache como Path.
    """
    cache_dir = os.getenv("CACHE_DIR", ".cache")
    return Path(cache_dir)


def has_cached_analysis(repo_hash: str) -> bool:
    """
    Verifica se análise já foi persistida para um repositório.

    Args:
        repo_hash: Hash SHA-256 único do repositório.

    Returns:
        True se arquivo de cache existe e é válido, False caso contrário.
    """
    cache_path = _get_cache_dir() / f"{repo_hash}.json"
    return cache_path.exists() and cache_path.is_file()


def load_results(repo_hash: str) -> Generator[AnalysisResult, None, None]:
    """
    Carrega análises persistidas de um repositório do cache.

    Args:
        repo_hash: Hash SHA-256 único do repositório.

    Yields:
        AnalysisResult reconstituído do arquivo JSON.

    Raises:
        FileNotFoundError: Se arquivo de cache não existe (esperado para miss).
    """
    cache_path = _get_cache_dir() / f"{repo_hash}.json"

    if not cache_path.exists():
        return

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Espera lista de dicts (um por AnalysisResult)
        if isinstance(data, list):
            for item in data:
                # Reconstrói AnalysisResult a partir do dict serializado
                yield AnalysisResult(**item)
    except (json.JSONDecodeError, KeyError, TypeError):
        # Arquivo corrompido ou inválido — retorna gerador vazio
        return


def save_results(repo_hash: str, results: Iterable[AnalysisResult]) -> None:
    """
    Salva análises em arquivo JSON local com escrita atômica.

    Materializa resultados em lista, serializa para JSON,
    e escreve para arquivo temporário antes de renomear
    (atomic write pattern).

    Args:
        repo_hash: Hash SHA-256 único do repositório.
        results: Iterável de AnalysisResult a persistir.
    """
    cache_dir = _get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_path = cache_dir / f"{repo_hash}.json"
    temp_path = cache_dir / f"{repo_hash}.tmp.json"

    # Materializa resultados em lista
    results_list = list(results)

    # Serializa para JSON
    serialized = [asdict(result) for result in results_list]

    # Escreve para arquivo temporário
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    # Rename atômico (substitui arquivo antigo se existe)
    os.replace(temp_path, cache_path)
