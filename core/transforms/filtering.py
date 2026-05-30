"""
core/transforms/filtering.py
=============================
Fornece predicados e funções de filtragem puras que selecionam subconjuntos
de registros a partir de critérios configuráveis pelo analista.

Responsabilidades:
    - Implementar predicados individuais e combináveis para cada critério
      de filtragem: linguagem de programação, tipo de projeto, natureza
      da contribuição, nível de clareza e intervalo de datas.
    - Expor `build_filter(*predicates)` que compõe múltiplos predicados
      em uma única função de filtro via conjunção lógica (AND), integrando-se
      ao sistema de filtros dinâmicos globais do dashboard.
    - Garantir que nenhum filtro mute o registro original; cada predicado
      apenas avalia e retorna True/False.
    - Suportar a combinação dinâmica de filtros selecionados pelo usuário
      na sidebar do Streamlit, sem recarregar o dataset base.

Não deve:
    - Modificar campos dos registros (responsabilidade de cleaning.py
      ou normalizing.py).
    - Conter lógica de agregação.

Relacionado a:
    - Issue 08 (motor de filtros dinâmicos globais)
    - HU 08 (filtrar todas as visualizações por critérios)
    - Regra Funcional 02 (funções puras)
    - Regra Funcional 07 (filter(), lambda)
    - Conceito-Chave 07 (lambda para filtros inline)
"""

from collections.abc import Callable, Iterable
from functools import reduce

from core.models.analysis_result import AnalysisResult

Predicate = Callable[[AnalysisResult], bool]


def by_language(languages: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por linguagem.

    A comparação é case-insensitive para evitar descartes causados por
    diferenças de capitalização, como "Python" e "python".

    Args:
        languages: Linguagens selecionadas pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando a linguagem
        do registro estiver entre as linguagens permitidas.
    """
    allowed = frozenset(map(str.lower, languages))
    return lambda record: record.language.lower() in allowed


def by_project_type(project_types: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por tipo de projeto.

    Os valores esperados devem seguir o vocabulário controlado do projeto,
    como "library", "web_app", "framework", "cli" e "other".

    Args:
        project_types: Tipos de projeto selecionados pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando o tipo de
        projeto do registro estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, project_types))
    return lambda record: record.project_type.lower() in allowed


def by_pr_nature(pr_natures: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por natureza da contribuição.

    Os valores devem corresponder ao campo pr_nature definido em AnalysisResult,
    como "bug_fix", "feature", "refactoring", "documentation" e "other".

    Args:
        pr_natures: Naturezas de contribuição selecionadas pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando a natureza
        da contribuição estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, pr_natures))
    return lambda record: record.pr_nature.lower() in allowed


def by_clarity_level(clarity_levels: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por nível de clareza.

    O projeto define clarity_level como categoria textual, não como número.
    Por isso, o filtro recebe um conjunto de labels válidas em vez de um
    intervalo numérico.

    Args:
        clarity_levels: Níveis de clareza selecionados pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando o nível de
        clareza estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, clarity_levels))
    return lambda record: record.clarity_level.lower() in allowed


def is_in_date_range(
    start_date: str,
    end_date: str,
) -> Predicate:
    """
    Cria predicado para filtrar registros
    dentro de um intervalo de datas.

    Args:
        start_date:
            Data inicial no formato YYYY-MM-DD.

        end_date:
            Data final no formato YYYY-MM-DD.

    Returns:
        Predicate que valida se o registro
        está dentro do intervalo informado.
    """

    return lambda record: start_date <= record.created_at <= end_date


def compose_predicates(predicates: Iterable[Predicate]) -> Predicate:
    """
    Constrói uma nova função pura combinando múltiplos predicados via conjunção lógica (AND).

    Utiliza `reduce()` para aplicar a composição funcional de forma imutável,
    agrupando os filtros passo a passo sem modificar ou mutar as funções originais.
    Se a lista de predicados estiver vazia, retorna uma função identidade que
    permite a passagem de todos os registros.

    Args:
        predicates: Iterável contendo as funções de filtragem (Predicate)
            que serão combinadas na validação.

    Returns:
        Uma única função do tipo Predicate que aceita um registro (AnalysisResult)
        e retorna True se, e somente se, todas as condições originais
        forem satisfeitas.
    """
    predicate_tuple: tuple[Predicate, ...] = tuple(predicates)

    if not predicate_tuple:
        return lambda _: True

    return reduce(
        lambda accumulated, current: (
            lambda record: accumulated(record) and current(record)
        ),
        predicate_tuple,
    )


def apply_filters(
    predicate,
    records,
):
    """Aplica um predicado composto aos registros.

    Utiliza lazy evaluation com filter() para evitar materialização de listas.
    Aceita um predicado único ou uma tuple de predicados que serão compostos.

    Args:
        predicate: Função (AnalysisResult → bool) OU tuple de funções
        records: Stream lazy de registros.

    Returns:
        Iterator de registros que satisfazem o predicado.
    """
    # Se predicate for uma tuple, compor os predicados
    if isinstance(predicate, tuple):
        final_predicate = compose_predicates(predicate)
    else:
        final_predicate = predicate

    return filter(
        final_predicate,
        records,
    )
