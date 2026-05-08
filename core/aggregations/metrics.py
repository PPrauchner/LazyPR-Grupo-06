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
    """Calcula estatísticas (min, max, mean, median) de char_count e word_count."""

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


def _get_bin_label(value: int, limits: tuple) -> str:
    """Função pura auxiliar para calcular a qual bin um valor pertence."""
    if value <= limits[0]:
        return f"0-{limits[0]}"
        
    pairs = zip(limits[:-1], limits[1:])
    matched = next(
        (f"{lower}-{upper}" for lower, upper in pairs if lower < value <= upper), 
        None
    )
    return matched if matched is not None else f"{limits[-1]}+"


def _build_distribution(records: Iterable[AnalysisResult], attr_name: str, bins: tuple) -> dict[str, int]:
    """
    Função genérica para criar distribuições, eliminando repetição de código (DRY).
    Avalia a propriedade passada em 'attr_name' via metaprogramação funcional.
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


def char_distribution(records: Iterable[AnalysisResult], bins: tuple = (100, 200, 500)) -> dict[str, int]:
    """Agrupa char_count em bins e retorna frequência por bin."""
    return _build_distribution(records, "char_count", bins)


def word_distribution(records: Iterable[AnalysisResult], bins: tuple = (10, 50, 100)) -> dict[str, int]:
    """Agrupa word_count em bins e retorna frequência por bin."""
    return _build_distribution(records, "word_count", bins)


def clarity_distribution(records: Iterable[AnalysisResult]) -> dict[str, int]:
    """Calcula frequência de cada clarity_level."""
    def accumulator(acc: dict, record: AnalysisResult) -> dict:
        level = record.clarity_level
        return {**acc, level: acc.get(level, 0) + 1}

    initial = {"insufficient": 0, "basic": 0, "good": 0, "excellent": 0}
    return reduce(accumulator, records, initial)
