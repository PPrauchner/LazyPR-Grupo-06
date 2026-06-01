"""
services/exporters.py
======================
Serializa os resultados enriquecidos em formatos portáveis consumíveis
por ferramentas externas de ciência de dados.

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
    "id",
    "repo",
    "path",
    "author",
    "author_association",
    "body",
    "diff_hunk",
    "language",
    "char_count",
    "word_count",
    "project_type",
    "pr_nature",
    "clarity_level",
    "html_url",
    "commit_id",
    "line",
    "created_at",
]


def enrich_records(
    records,
):
    return records


def _analysis_result_to_dict(result: AnalysisResult) -> dict:
    """Converte um `AnalysisResult` em dicionário alinhado com `CSV_FIELDNAMES`.

    Args:
        result (AnalysisResult): Registro enriquecido produzido pelo pipeline.

    Returns:
        dict: Dicionário com exatamente as chaves de `CSV_FIELDNAMES`, mapeando
        cada nome de campo ao valor correspondente no registro.
    """
    return {field: getattr(result, field) for field in CSV_FIELDNAMES}


def _write_csv_to_stream(stream: TextIO, results: Iterable[AnalysisResult]) -> None:
    """Escreve uma sequência de registros em um stream de texto aberto no formato CSV.

    Escreve uma linha de cabeçalho seguida de uma linha de dados por registro.
    A ordem dos campos segue `CSV_FIELDNAMES`.

    Args:
        stream (TextIO): Stream de texto aberto para escrita (ex: `open()` ou
            `io.StringIO()`).
        results (Iterable[AnalysisResult]): Registros a serializar.
    """
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    # Laço justificado: writer.writerow() é efeito colateral de I/O sem valor de retorno útil;
    # map() expressaria transformação, não escrita sequencial — for é semanticamente correto aqui.
    for result in results:
        writer.writerow(_analysis_result_to_dict(result))


def _write_json_to_stream(stream: TextIO, results: Iterable[AnalysisResult]) -> None:
    """Escreve uma sequência de registros em um stream de texto aberto no formato JSON Lines.

    Cada registro é serializado como um objeto JSON em sua própria linha
    (JSONL / newline-delimited JSON), tornando a saída compatível com
    pipelines externos de dados.

    Args:
        stream (TextIO): Stream de texto aberto para escrita (ex: `open()` ou
            `io.StringIO()`).
        results (Iterable[AnalysisResult]): Registros a serializar.
    """
    # Laço justificado: stream.write() é efeito colateral de I/O sem valor de retorno útil;
    # map() expressaria transformação, não escrita sequencial — for é semanticamente correto aqui.
    for result in results:
        row = _analysis_result_to_dict(result)
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_csv(results: Iterable[AnalysisResult], filepath: str) -> None:
    """Serializa uma coleção de registros em arquivo CSV.

    Usa escrita atômica: os dados são gravados em um arquivo temporário
    e então renomeados para o caminho final. Isso previne arquivos parciais
    ou corrompidos em caso de interrupção inesperada.

    Args:
        results (Iterable[AnalysisResult]): Registros a exportar.
        filepath (str): Caminho do arquivo de destino, ex: "output/results.csv".

    Raises:
        IOError: Se o arquivo não puder ser escrito ou renomeado.
    """
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            _write_csv_to_stream(f, results)
        os.replace(tmp_path, filepath)
    except IOError as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"Falha ao escrever CSV em {filepath}: {e}") from e


def export_json(results: Iterable[AnalysisResult], filepath: str) -> None:
    """Serializa uma coleção de registros em arquivo JSON Lines.

    Usa a mesma estratégia de escrita atômica de `export_csv`: grava em
    arquivo temporário e renomeia atomicamente para evitar corrupção.

    Args:
        results (Iterable[AnalysisResult]): Registros a exportar.
        filepath (str): Caminho do arquivo de destino, ex: "output/results.jsonl".

    Raises:
        IOError: Se o arquivo não puder ser escrito ou renomeado.
    """
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            _write_json_to_stream(f, results)
        os.replace(tmp_path, filepath)
    except IOError as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(f"Falha ao escrever JSON em {filepath}: {e}") from e


def to_download_bytes(results: Iterable[AnalysisResult], fmt: str = "csv") -> bytes:
    """Serializa os resultados como bytes para uso com o botão de download do Streamlit.

    Produz a mesma saída de `export_csv` ou `export_json`, mas inteiramente
    em memória, sem gravar nenhum arquivo temporário em disco. Adequado para
    passar diretamente a `st.download_button(data=...)`.

    Args:
        results (Iterable[AnalysisResult]): Registros a serializar.
        fmt (str): Formato de saída — "csv" ou "json". Padrão: "csv".

    Returns:
        bytes: Conteúdo serializado codificado em UTF-8.

    Raises:
        ValueError: Se `fmt` não for "csv" ou "json".

    Exemplo:
        >>> csv_bytes = to_download_bytes(results, fmt="csv")
        >>> st.download_button("Baixar CSV", data=csv_bytes, file_name="resultados.csv")
    """
    if fmt not in ("csv", "json"):
        raise ValueError(f"Formato inválido: '{fmt}'. Use 'csv' ou 'json'.")

    output = io.StringIO()

    if fmt == "csv":
        _write_csv_to_stream(output, results)
    else:
        _write_json_to_stream(output, results)

    return output.getvalue().encode("utf-8")
