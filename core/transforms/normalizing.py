"""
core/transforms/normalizing.py
================================
Fornece funções puras de normalização que padronizam os valores dos campos
de um `PRRecord` para formatos canônicos utilizados nas análises.

Responsabilidades:
    - Normalizar strings de linguagem de programação para um conjunto
      controlado de valores (ex: "python", "Python 3" → "Python").
    - Converter campos de data para objetos `datetime` ou timestamps Unix
      de forma consistente, independente do formato de origem do dataset.
    - Calcular e adicionar métricas derivadas de texto: `char_count` e
      `word_count` do corpo do PR, utilizadas nas visualizações da Issue 06.
    - Padronizar labels de classificação retornados pelo LLM para o
      vocabulário controlado esperado pelas agregações
      (ex: "bug-fix", "bugfix", "BugFix" → "bug_fix").
    - Todas as funções devem ser puras e retornar novas instâncias
      imutáveis, nunca modificando o registro de entrada.

Não deve:
    - Realizar chamadas a LLMs ou I/O.
    - Executar filtragem ou agregação.

Relacionado a:
    - Issue 06 (métricas de tamanho de descrição: chars e palavras)
    - Issue 04 (padronização dos labels de clareza retornados pelo LLM)
    - Regra Funcional 03 (imutabilidade — retornar nova instância)
    - Conceito-Chave 05 (funções puras para normalização)
"""
