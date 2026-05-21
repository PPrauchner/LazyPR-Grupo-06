"""
tests/test_composer.py
=======================
Testes para core/pipeline/composer.py - composição funcional.

Cobertura:
    - pipe() e compose() com múltiplas funções
    - Ordem de aplicação (esquerda→direita vs direita→esquerda)
    - Função identidade
    - Casos extremos (vazio, uma função, múltiplas)
"""

import pytest
from core.pipeline.composer import pipe, compose, identity, _compose_pair


# ---------------------------------------------------------------------------
# Tests: pipe() - Esquerda para Direita
# ---------------------------------------------------------------------------


class TestPipe:
    """Testes para função pipe()."""

    def test_pipe_two_functions(self):
        """Testa pipe com duas funções."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        # pipe: double(x) depois add_one()
        piped = pipe(double, add_one)
        result = piped(5)

        # double(5) = 10, add_one(10) = 11
        assert result == 11

    def test_pipe_three_functions(self):
        """Testa pipe com três funções."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2
        square = lambda x: x ** 2

        # pipe: square(x) depois double() depois add_one()
        piped = pipe(square, double, add_one)
        result = piped(3)

        # square(3) = 9, double(9) = 18, add_one(18) = 19
        assert result == 19

    def test_pipe_with_strings(self):
        """Testa pipe com funções de string."""
        upper = lambda s: s.upper()
        add_exclamation = lambda s: s + "!"

        piped = pipe(upper, add_exclamation)
        result = piped("hello")

        # upper("hello") = "HELLO", add_exclamation("HELLO") = "HELLO!"
        assert result == "HELLO!"

    def test_pipe_empty(self):
        """Testa pipe vazio retorna identidade."""
        piped = pipe()
        result = piped(42)

        assert result == 42

    def test_pipe_single_function(self):
        """Testa pipe com uma única função."""
        add_one = lambda x: x + 1
        piped = pipe(add_one)

        assert piped(5) == 6

    def test_pipe_preserves_type(self):
        """Testa que pipe preserva tipos através da cadeia."""
        to_list = lambda x: [x]
        add_item = lambda lst: lst + [2]
        sort_list = lambda lst: sorted(lst)

        piped = pipe(to_list, add_item, sort_list)
        result = piped(1)

        assert result == [1, 2]
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests: compose() - Direita para Esquerda
# ---------------------------------------------------------------------------


class TestCompose:
    """Testes para função compose()."""

    def test_compose_two_functions(self):
        """Testa compose com duas funções (ordem matemática)."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        # compose: add_one(double(x)) — direita para esquerda
        composed = compose(add_one, double)
        result = composed(5)

        # double(5) = 10, add_one(10) = 11
        assert result == 11

    def test_compose_three_functions(self):
        """Testa compose com três funções."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2
        square = lambda x: x ** 2

        # compose: add_one(double(square(x)))
        composed = compose(add_one, double, square)
        result = composed(3)

        # square(3) = 9, double(9) = 18, add_one(18) = 19
        assert result == 19

    def test_compose_vs_pipe_same_result(self):
        """Testa que pipe e compose com ordem invertida produzem mesmo resultado."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        piped = pipe(double, add_one)
        composed = compose(add_one, double)

        assert piped(5) == composed(5)

    def test_compose_empty(self):
        """Testa compose vazio retorna identidade."""
        composed = compose()
        result = composed(42)

        assert result == 42

    def test_compose_single_function(self):
        """Testa compose com uma única função."""
        add_one = lambda x: x + 1
        composed = compose(add_one)

        assert composed(5) == 6

    def test_compose_with_strings(self):
        """Testa compose com funções de string."""
        upper = lambda s: s.upper()
        add_prefix = lambda s: "Hello, " + s

        composed = compose(add_prefix, upper)
        result = composed("world")

        # upper("world") = "WORLD", add_prefix("WORLD") = "Hello, WORLD"
        assert result == "Hello, WORLD"


# ---------------------------------------------------------------------------
# Tests: _compose_pair()
# ---------------------------------------------------------------------------


class TestComposePair:
    """Testes para função auxiliar _compose_pair()."""

    def test_compose_pair_basic(self):
        """Testa composição de exatamente duas funções."""
        f = lambda x: x + 1
        g = lambda x: x * 2

        composed = _compose_pair(f, g)
        result = composed(5)

        # g(5) = 10, f(10) = 11
        assert result == 11

    def test_compose_pair_order(self):
        """Testa que _compose_pair respeita ordem f ∘ g = f(g(x))."""
        double = lambda x: x * 2
        add_one = lambda x: x + 1

        # f=add_one, g=double → add_one(double(x))
        composed = _compose_pair(add_one, double)
        result = composed(5)

        # double(5) = 10, add_one(10) = 11
        assert result == 11

    def test_compose_pair_with_side_effects(self):
        """Testa composição de funções com múltiplas operações."""
        multiply_by_three = lambda x: x * 3
        subtract_five = lambda x: x - 5

        composed = _compose_pair(subtract_five, multiply_by_three)
        result = composed(4)

        # multiply_by_three(4) = 12, subtract_five(12) = 7
        assert result == 7


# ---------------------------------------------------------------------------
# Tests: identity()
# ---------------------------------------------------------------------------


class TestIdentity:
    """Testes para função identidade."""

    def test_identity_int(self):
        """Testa identidade com inteiro."""
        assert identity(42) == 42

    def test_identity_string(self):
        """Testa identidade com string."""
        assert identity("hello") == "hello"

    def test_identity_none(self):
        """Testa identidade com None."""
        assert identity(None) is None

    def test_identity_list(self):
        """Testa identidade com lista (retorna mesma instância)."""
        lst = [1, 2, 3]
        assert identity(lst) is lst

    def test_identity_dict(self):
        """Testa identidade com dicionário."""
        d = {"a": 1, "b": 2}
        assert identity(d) is d

    def test_identity_in_pipe(self):
        """Testa identidade como etapa no pipeline."""
        add_one = lambda x: x + 1

        piped = pipe(identity, add_one)
        result = piped(5)

        assert result == 6

    def test_identity_in_compose(self):
        """Testa identidade como etapa em composição."""
        add_one = lambda x: x + 1

        composed = compose(add_one, identity)
        result = composed(5)

        assert result == 6


# ---------------------------------------------------------------------------
# Complex Scenarios
# ---------------------------------------------------------------------------


class TestCompositionComplexScenarios:
    """Testes para cenários complexos de composição."""

    def test_data_transformation_pipeline(self):
        """Testa pipeline de transformação de dados complexo."""
        # Simula um pipeline de limpeza → normalização → enriquecimento
        remove_spaces = lambda s: s.replace(" ", "")
        to_uppercase = lambda s: s.upper()
        add_suffix = lambda s: s + "_PROCESSED"

        pipeline = pipe(remove_spaces, to_uppercase, add_suffix)
        result = pipeline("hello world")

        assert result == "HELLOWORLD_PROCESSED"

    def test_mathematical_expression_as_pipeline(self):
        """Testa composição matemática complexa."""
        # ((x + 1) * 2) - 5
        step1 = lambda x: x + 1  # +1
        step2 = lambda x: x * 2  # ×2
        step3 = lambda x: x - 5  # -5

        expression = pipe(step1, step2, step3)
        result = expression(3)

        # (3 + 1) * 2 - 5 = 4 * 2 - 5 = 8 - 5 = 3
        assert result == 3

    def test_filter_map_composition(self):
        """Testa composição com operações list-like."""
        numbers = [1, 2, 3, 4, 5]

        # Composição: multiplicar por 2, depois filtrar > 5
        double = lambda nums: [n * 2 for n in nums]
        filter_gt_5 = lambda nums: [n for n in nums if n > 5]

        pipeline = pipe(double, filter_gt_5)
        result = pipeline(numbers)

        # [2, 4, 6, 8, 10] → [6, 8, 10]
        assert result == [6, 8, 10]

    def test_reusable_pipeline_definition(self):
        """Testa que pipeline composto pode ser reutilizado."""
        # Define pipeline uma vez
        process = pipe(
            lambda x: x * 2,
            lambda x: x + 10,
            lambda x: x // 3,
        )

        # Aplica múltiplas vezes
        results = [process(x) for x in range(1, 5)]

        # (1*2+10)//3 = 4, (2*2+10)//3 = 4, (3*2+10)//3 = 5, (4*2+10)//3 = 6
        assert results == [4, 4, 5, 6]

    def test_identity_as_no_op_in_pipeline(self):
        """Testa que identity pode ser usada como no-op em pipeline."""
        add_one = lambda x: x + 1
        multiply_two = lambda x: x * 2

        # Com identity no meio (não faz diferença)
        pipeline_with_identity = pipe(add_one, identity, multiply_two)
        # Sem identity (mesmo resultado)
        pipeline_without = pipe(add_one, multiply_two)

        x = 5
        assert pipeline_with_identity(x) == pipeline_without(x)


# ---------------------------------------------------------------------------
# Type Preservation
# ---------------------------------------------------------------------------


class TestTypePreservation:
    """Testes para preservação de tipos através de pipelines."""

    def test_int_pipeline(self):
        """Testa que tipos int são preservados."""
        pipeline = pipe(lambda x: x + 1, lambda x: x * 2)
        result = pipeline(5)

        assert isinstance(result, int)
        assert result == 12

    def test_string_pipeline(self):
        """Testa que tipos string são preservados."""
        pipeline = pipe(
            lambda s: s.upper(),
            lambda s: s + "!",
        )
        result = pipeline("hello")

        assert isinstance(result, str)
        assert result == "HELLO!"

    def test_list_pipeline(self):
        """Testa que tipos list são preservados."""
        pipeline = pipe(
            lambda lst: lst + [4],
            lambda lst: sorted(lst),
        )
        result = pipeline([3, 1, 2])

        assert isinstance(result, list)
        assert result == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Determinism and Purity
# ---------------------------------------------------------------------------


class TestCompositionDeterminism:
    """Testes para garantir que composição é determinística e pura."""

    def test_repeated_execution_same_result(self):
        """Testa que mesma entrada sempre produz mesma saída."""
        pipeline = pipe(
            lambda x: x + 1,
            lambda x: x * 2,
            lambda x: x - 5,
        )

        x = 10
        result1 = pipeline(x)
        result2 = pipeline(x)
        result3 = pipeline(x)

        assert result1 == result2 == result3

    def test_no_side_effects(self):
        """Testa que pipelines não causam efeitos colaterais."""
        original_list = [1, 2, 3]
        original_copy = original_list.copy()

        # Pipeline que opera sobre lista
        pipeline = pipe(
            lambda lst: lst,  # Identity
            lambda lst: sorted(lst),
        )

        result = pipeline(original_list)

        # Original não deve ser modificada
        assert original_list == original_copy
        # Resultado deve ser sorted
        assert result == [1, 2, 3]
