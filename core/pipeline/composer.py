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
