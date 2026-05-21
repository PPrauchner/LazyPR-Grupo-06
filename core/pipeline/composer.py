"""
core/pipeline/composer.py
==========================
Fornece a função de composição funcional que combina etapas de transformação
em um pipeline configurável, respeitando o paradigma de funções de ordem superior.

Responsabilidades:
    - Implementar `compose(*fns)` que retorna uma função resultante do
      encadeamento sequencial de `fns`, onde a saída de cada função é
      a entrada da próxima — equivalente a f₃(f₂(f₁(x))).
    - Implementar `pipe(*fns)` como variante de `compose` com ordem natural
      de leitura (da esquerda para a direita), facilitando a declaração
      legível das etapas do pipeline.
    - Garantir que as funções compostas sejam tratadas como valores de
      primeira classe, podendo ser passadas, retornadas e armazenadas.
    - Todas as funções deste módulo devem ser puras: nenhum efeito colateral,
      nenhum estado global.

Não deve:
    - Executar o pipeline sobre dados reais (responsabilidade de runner.py).
    - Importar módulos de I/O, LLM ou interface gráfica.

Relacionado a:
    - Issue 08 (filtros dinâmicos compostos por predicados)
    - Regra Geral 05 (pipeline com funções de ordem superior)
    - Regra Funcional 06 (composição de funções menores)
    - Conceito-Chave 09 (composição como mecanismo de pipeline)
"""

from __future__ import annotations

from typing import Callable, TypeVar

# Tipos genéricos para composição
A = TypeVar("A")  # Tipo de entrada
B = TypeVar("B")  # Tipo intermediário
C = TypeVar("C")  # Tipo de saída


# ---------------------------------------------------------------------------
# Composição Funcional
# ---------------------------------------------------------------------------


def compose(
    *functions: Callable,
) -> Callable:
    """Compõe múltiplas funções em uma única função.

    Ordem: direita para esquerda (tradicional em programação funcional).
    Equivalente matemático: (f ∘ g)(x) = f(g(x))

    Para multiple functions: compose(f, g, h)(x) = f(g(h(x)))

    Args:
        *functions: Funções a compor em ordem (da última aplicada para primeira).

    Returns:
        Função composta que aceita um argumento e aplica todas as funções
        em sequência (direita para esquerda).

    Examples:
        >>> add_one = lambda x: x + 1
        >>> double = lambda x: x * 2
        >>> composed = compose(add_one, double)
        >>> composed(5)  # add_one(double(5)) = add_one(10) = 11
        11

        >>> from core.transforms.cleaning import clean_text
        >>> from core.transforms.normalizing import normalize_language
        >>> pipeline = compose(normalize_language, clean_text)
        >>> result = pipeline("PYTHON 3")
        'python'
    """
    if not functions:
        # Função identidade: retorna entrada inalterada
        return lambda x: x

    if len(functions) == 1:
        # Uma função: retorna ela mesma
        return functions[0]

    # Múltiplas funções: reduz da direita para esquerda
    return _compose_pair(functions[0], compose(*functions[1:]))


def _compose_pair(f: Callable[[B], C], g: Callable[[A], B]) -> Callable[[A], C]:
    """Compõe exatamente duas funções: f ∘ g = f(g(x))."""
    return lambda x: f(g(x))


def pipe(
    *functions: Callable,
) -> Callable:
    """Compõe múltiplas funções em ordem natural (esquerda para direita).

    Ordem: esquerda para direita (mais intuitiva para leitura).
    Equivalente a: pipeline(x) = fn4(fn3(fn2(fn1(x))))

    Args:
        *functions: Funções a compor em ordem (da primeira aplicada para última).

    Returns:
        Função composta que aceita um argumento e aplica todas as funções
        em sequência (esquerda para direita).

    Examples:
        >>> add_one = lambda x: x + 1
        >>> double = lambda x: x * 2
        >>> piped = pipe(double, add_one)
        >>> piped(5)  # add_one(double(5)) = add_one(10) = 11
        11

        >>> from services.ingestion import ingest_csv
        >>> from core.transforms.normalizing import normalize_pr_record
        >>> from services.classifiers import classify_project_type
        >>> pipeline = pipe(
        ...     ingest_csv,
        ...     lambda records: (normalize_pr_record(r) for r in records),
        ...     classify_project_type,
        ... )
        >>> results = pipeline("data.csv")
    """
    # pipe é compose com ordem invertida
    return compose(*reversed(functions))


# ---------------------------------------------------------------------------
# Identidade e Constantes
# ---------------------------------------------------------------------------


def identity(x: A) -> A:
    """Função identidade: retorna a entrada inalterada.

    Útil como placeholder ou para composições triviais.

    Args:
        x: Qualquer valor.

    Returns:
        O mesmo valor x.

    Examples:
        >>> identity(42)
        42
        >>> identity("hello")
        'hello'
    """
    return x
