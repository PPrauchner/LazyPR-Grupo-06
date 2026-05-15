"""
services/exporters.py
======================
Implementa a exportação dos resultados enriquecidos para formatos
portáveis consumíveis por ferramentas externas de ciência de dados.

Responsabilidades:
    - Implementar `export_csv(results, filepath)` que serializa uma coleção
      de `AnalysisResult` em CSV, incluindo tanto os campos originais do
      dataset quanto as classificações semânticas geradas pelos LLMs.
    - Implementar `export_json(results, filepath)` com comportamento
      equivalente em formato JSON Lines, preservando o schema completo.
    - Implementar `to_download_bytes(results, fmt)` que retorna os dados
      serializados como `bytes` para uso direto com `st.download_button`
      do Streamlit, sem exigir escrita em disco intermediária.
    - Garantir que o schema exportado seja consistente e autodocumentado
      (cabeçalho CSV descritivo, campos JSON com nomes canônicos).

Não deve:
    - Realizar qualquer transformação ou filtragem dos dados.
    - Chamar LLMs ou acessar o pipeline funcional.

Relacionado a:
    - Issue 09 (exportação em CSV e JSON)
    - HU 09 (exportar resultados para uso em outras ferramentas)
"""
import csv
import io
import json
import os
from typing import Iterable, TextIO
from core.models.analysis_result import AnalysisResult


CSV_FIELDNAMES = [
    "id", "repo", "path", "author", "author_association", "body",
    "diff_hunk", "language", "char_count", "word_count", "project_type",
    "pr_nature", "clarity_level", "html_url", "commit_id", "line", "created_at"
]


def _analysis_result_to_dict(result: AnalysisResult) -> dict:
    """Converte AnalysisResult para dict alinhado com CSV_FIELDNAMES via Dictionary Comprehension (Clean Code)."""
    return {field: getattr(result, field) for field in CSV_FIELDNAMES}


def _write_csv_to_stream(stream: TextIO, results: Iterable[AnalysisResult]) -> None:
    """Helper para encapsular a escrita CSV e evitar repetição de código (DRY)."""
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for result in results:
        writer.writerow(_analysis_result_to_dict(result))


def _write_json_to_stream(stream: TextIO, results: Iterable[AnalysisResult]) -> None:
    """Helper para encapsular a escrita JSON Lines e evitar repetição de código (DRY)."""
    for result in results:
        row = _analysis_result_to_dict(result)
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_csv(results: Iterable[AnalysisResult], filepath: str) -> None:
    """Serializa coleção em arquivo CSV de forma segura (Atomic Write)."""
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            _write_csv_to_stream(f, results)
        os.replace(tmp_path, filepath)
    except IOError as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"Falha ao escrever CSV {filepath}: {e}") from e


def export_json(results: Iterable[AnalysisResult], filepath: str) -> None:
    """Serializa coleção em arquivo JSON Lines de forma segura (Atomic Write)."""
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            _write_json_to_stream(f, results)
        os.replace(tmp_path, filepath)
    except IOError as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"Falha ao escrever JSON {filepath}: {e}") from e


def to_download_bytes(results: Iterable[AnalysisResult], fmt: str = "csv") -> bytes:
    """Retorna dados serializados como bytes para st.download_button em memória."""
    if fmt not in ("csv", "json"):
        raise ValueError(f"Formato inválido: {fmt}. Deve ser 'csv' ou 'json'.")

    output = io.StringIO()
    
    if fmt == "csv":
        _write_csv_to_stream(output, results)
    else:
        _write_json_to_stream(output, results)
        
    return output.getvalue().encode("utf-8")
