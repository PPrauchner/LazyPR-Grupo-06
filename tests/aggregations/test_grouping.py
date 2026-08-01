from typing import NamedTuple
from core.aggregations.grouping import group_by, cross_count_language_clarity


# Mock imutável simulando um registro normalizado do pipeline
class MockRecord(NamedTuple):
    language: str
    clarity_level: str


def test_group_by_pure_function():
    records = (
        MockRecord("Python", "boa"),
        MockRecord("Python", "excelente"),
        MockRecord("Go", "boa"),
    )

    # Usando uma chave simples
    grouped = group_by(lambda r: r.language, records)

    assert isinstance(grouped["Python"], tuple)  # Verifica imutabilidade da coleção
    assert len(grouped["Python"]) == 2
    assert len(grouped["Go"]) == 1


def test_cross_count_language_clarity():
    records = (
        MockRecord("Python", "boa"),
        MockRecord("Python", "boa"),
        MockRecord("Python", "insuficiente"),
        MockRecord("Java", "boa"),
    )

    # Executa a contagem cruzada multidimensional
    cross_counts = cross_count_language_clarity(records)

    # Verifica as totalizações mapeadas pelas chaves compostas
    assert cross_counts[("Python", "boa")] == 2
    assert cross_counts[("Python", "insuficiente")] == 1
    assert cross_counts[("Java", "boa")] == 1

    # Garante que chaves inexistentes não estão no dicionário
    assert ("Java", "insuficiente") not in cross_counts
