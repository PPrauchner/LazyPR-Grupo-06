"""
Testes unitários para o módulo de composição funcional.
Garante que pipe() e compose() executam as funções na ordem correta
e que gerem bem casos de limite.
"""
from core.pipeline.composer import compose, pipe, identity

def test_identity():
    """Garante que a função identidade retorna exatamente o valor de entrada."""
    assert identity(42) == 42
    assert identity("texto de teste") == "texto de teste"
    assert identity([1, 2, 3]) == [1, 2, 3]

def test_compose_order():
    """
    Garante que compose() executa as funções da DIREITA para a ESQUERDA.
    """
    soma_um = lambda x: x + 1
    duplica = lambda x: x * 2
    
    # Execução esperada: duplica(5) -> 10, soma_um(10) -> 11
    composed_fn = compose(soma_um, duplica)
    assert composed_fn(5) == 11

def test_pipe_order():
    """
    Garante que pipe() executa as funções da ESQUERDA para a DIREITA.
    """
    soma_um = lambda x: x + 1
    duplica = lambda x: x * 2
    
    # Execução esperada: soma_um(5) -> 6, duplica(6) -> 12
    piped_fn = pipe(soma_um, duplica)
    assert piped_fn(5) == 12

def test_compose_empty_args():
    """
    Garante que compose() sem argumentos atua de forma segura como
    uma função identidade.
    """
    empty_compose = compose()
    assert empty_compose("teste seguro") == "teste seguro"

def test_pipe_three_functions():
    """Garante o encadeamento correto com mais de duas funções no pipe."""
    adiciona_prefixo = lambda s: f"prefix_{s}"
    caixa_alta = lambda s: s.upper()
    adiciona_sufixo = lambda s: f"{s}_suffix"
    
    pipeline = pipe(adiciona_prefixo, caixa_alta, adiciona_sufixo)
    resultado = pipeline("teste")
    
    # prefix_teste -> PREFIX_TESTE -> PREFIX_TESTE_suffix
    assert resultado == "PREFIX_TESTE_suffix"