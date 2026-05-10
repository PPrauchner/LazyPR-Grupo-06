"""
core/aggregations/metrics.py
=============================
Fornece funções puras para o cálculo de métricas estatísticas sobre
grupos de `AnalysisResult`, como médias, medianas e distribuições
de tamanho de descrição.

Responsabilidades:
    - Calcular média, mediana, mínimo e máximo de `char_count` e `word_count`
      sobre qualquer coleção ou subgrupo de registros, via `reduce()`.
    - Calcular a distribuição de frequência dos níveis de clareza
      (insuficiente, básica, boa, excelente) por grupo, para alimentar
      os gráficos de correlação da Issue 07.
    - Implementar `correlation_summary(groups)` que, dado um dicionário
      de grupos (saída de grouping.py), computa métricas comparativas
      entre grupos para evidenciar padrões de contribuição.
    - Todas as funções devem ser puras e operar sobre estruturas imutáveis.

Não deve:
    - Realizar I/O, chamadas a LLMs ou lógica de plotagem.
    - Depender de bibliotecas estatísticas externas (numpy/pandas);
      usar apenas a stdlib e functools para manter a pureza funcional.
    - Depender de bibliotecas estatísticas externas (numpy/pandas).

Relacionado a:
    - Issue 06 (distribuição de tamanho de descrição)
    - Issue 07 (correlação entre clareza, tipo e linguagem)
    - HU 06 (distribuição de chars/palavras estratificada)
    - HU 07 (padrões de contribuição entre dimensões)
    - Regra Funcional 01 (reduce() para cálculos de agregação)
    - Conceito-Chave 03 (reduce para agregação)
"""
from functools import reduce
from typing import Iterable

from core.models.analysis_result import AnalysisResult


def description_stats(records: Iterable[AnalysisResult]) -> dict:
    """Calcula estatísticas descritivas de `char_count` e `word_count`.

    Itera os registros uma única vez com `reduce()`, acumulando os valores
    de caracteres e palavras em um único passo. As estatísticas são derivadas
    a partir das tuplas acumuladas.

    Args:
        records (Iterable[AnalysisResult]): Registros enriquecidos produzidos
            pelo pipeline.

    Returns:
        dict: Dicionário com a seguinte estrutura::

            {
                "char": {
                    "min": int, "max": int,
                    "mean": float, "median": float,
                    "values": tuple[int, ...]
                },
                "word": {
                    "min": int, "max": int,
                    "mean": float, "median": float,
                    "values": tuple[int, ...]
                },
                "total_records": int
            }

        Quando a entrada está vazia, todos os campos numéricos são 0 ou 0.0
        e "total_records" é 0.

    Exemplo:
        >>> stats = description_stats(results)
        >>> stats["char"]["mean"]
        312.4
        >>> stats["total_records"]
        150
    """

    def accumulator(acc: dict, record: AnalysisResult) -> dict:
        return {
            "char_values": acc["char_values"] + (record.char_count,),
            "word_values": acc["word_values"] + (record.word_count,),
            "count": acc["count"] + 1,
        }

    initial = {"char_values": (), "word_values": (), "count": 0}
    result = reduce(accumulator, records, initial)

    if result["count"] == 0:
        return {
            "char": {"min": 0, "max": 0, "mean": 0.0, "median": 0.0},
            "word": {"min": 0, "max": 0, "mean": 0.0, "median": 0.0},
            "total_records": 0,
        }

    def compute_stats(values: tuple) -> dict:
        sorted_vals = tuple(sorted(values))
        n = len(sorted_vals)
        median = (
            float(sorted_vals[n // 2])
            if n % 2 == 1
            else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        )
        mean = sum(sorted_vals) / n if n > 0 else 0.0
        return {
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": round(mean, 2),
            "median": median,
            "values": sorted_vals,
        }

    return {
        "char": compute_stats(result["char_values"]),
        "word": compute_stats(result["word_values"]),
        "total_records": result["count"],
    }


def _get_bin_label(value: int, limits: tuple[int, ...]) -> str:
    """Retorna o rótulo do intervalo (bin) ao qual um valor numérico pertence.

    O primeiro bin cobre [0, limits[0]], os bins intermediários cobrem
    (limits[i], limits[i+1]], e o último bin cobre (limits[-1], +inf).

    Args:
        value (int): Valor inteiro a classificar (ex: char_count).
        limits (tuple[int, ...]): Tupla ordenada com os limites superiores
            de cada bin. Ex: (100, 200, 500).

    Returns:
        str: Rótulo do bin, como "0-100", "100-200", "200-500" ou "500+".

    Exemplo:
        >>> _get_bin_label(150, (100, 200, 500))
        '100-200'
        >>> _get_bin_label(600, (100, 200, 500))
        '500+'
    """
    if value <= limits[0]:
        return f"0-{limits[0]}"

    pairs = zip(limits[:-1], limits[1:])
    matched = next(
        (f"{lower}-{upper}" for lower, upper in pairs if lower < value <= upper),
        None,
    )
    return matched if matched is not None else f"{limits[-1]}+"


def _build_distribution(
    records: Iterable[AnalysisResult], attr_name: str, bins: tuple[int, ...]
) -> dict[str, int]:
    """Constrói uma distribuição de frequências por bins para um atributo numérico.

    Usa `reduce()` e `getattr` para acumular contagens por bin sem mutar
    nenhuma estrutura intermediária. Cada passo retorna um novo dicionário.

    Args:
        records (Iterable[AnalysisResult]): Registros a agregar.
        attr_name (str): Nome do atributo inteiro a ler de cada registro
            (ex: "char_count" ou "word_count").
        bins (tuple[int, ...]): Tupla ordenada com os limites superiores
            dos bins, passada para `_get_bin_label`.

    Returns:
        dict[str, int]: Dicionário mapeando cada rótulo de bin à sua
        contagem de frequência. Todos os bins definidos por `bins` estão
        presentes, mesmo quando a contagem é zero.

    Exemplo:
        >>> _build_distribution(results, "char_count", (100, 200, 500))
        {"0-100": 5, "100-200": 23, "200-500": 41, "500+": 8}
    """

    def accumulator(acc: dict, record: AnalysisResult) -> dict:
        value = getattr(record, attr_name)
        label = _get_bin_label(value, bins)
        return {**acc, label: acc.get(label, 0) + 1}

    initial = {
        f"0-{bins[0]}": 0,
        **{f"{bins[i]}-{bins[i+1]}": 0 for i in range(len(bins) - 1)},
        f"{bins[-1]}+": 0,
    }

    return reduce(accumulator, records, initial)


def char_distribution(
    records: Iterable[AnalysisResult],
    bins: tuple[int, ...] = (100, 200, 500),
) -> dict[str, int]:
    """Agrupa registros por faixas de `char_count` e retorna a frequência por bin.

    Args:
        records (Iterable[AnalysisResult]): Registros a agregar.
        bins (tuple[int, ...]): Limites superiores dos bins.
            Padrão: (100, 200, 500).

    Returns:
        dict[str, int]: Frequência por faixa de caracteres.
            Exemplo: {"0-100": 10, "100-200": 34, "200-500": 55, "500+": 12}
    """
    return _build_distribution(records, "char_count", bins)


def word_distribution(
    records: Iterable[AnalysisResult],
    bins: tuple[int, ...] = (10, 50, 100),
) -> dict[str, int]:
    """Agrupa registros por faixas de `word_count` e retorna a frequência por bin.

    Args:
        records (Iterable[AnalysisResult]): Registros a agregar.
        bins (tuple[int, ...]): Limites superiores dos bins.
            Padrão: (10, 50, 100).

    Returns:
        dict[str, int]: Frequência por faixa de palavras.
            Exemplo: {"0-10": 8, "10-50": 61, "50-100": 30, "100+": 5}
    """
    return _build_distribution(records, "word_count", bins)


def clarity_distribution(records: Iterable[AnalysisResult]) -> dict[str, int]:
    """Calcula a frequência de cada nível de clareza sobre todos os registros.

    Usa `reduce()` para acumular contagens sem mutar o acumulador. Todos os
    quatro níveis do vocabulário controlado estão sempre presentes no resultado,
    mesmo quando a contagem é zero.

    Args:
        records (Iterable[AnalysisResult]): Registros a agregar.

    Returns:
        dict[str, int]: Dicionário com exatamente quatro chaves::

            {
                "insufficient": int,
                "basic": int,
                "good": int,
                "excellent": int
            }

    Exemplo:
        >>> clarity_distribution(results)
        {"insufficient": 12, "basic": 45, "good": 67, "excellent": 26}
    """

    def accumulator(acc: dict, record: AnalysisResult) -> dict:
        level = record.clarity_level
        return {**acc, level: acc.get(level, 0) + 1}

    initial = {"insufficient": 0, "basic": 0, "good": 0, "excellent": 0}
    return reduce(accumulator, records, initial)
