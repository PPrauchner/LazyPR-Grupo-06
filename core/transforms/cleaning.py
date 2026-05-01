"""
core/transforms/cleaning.py
============================
Fornece funções puras de limpeza dos campos brutos de um `PRRecord`,
preparando os dados para normalização e envio ao pipeline de classificação.

Responsabilidades:
    - Remover espaços em branco desnecessários (strip) de campos textuais
      como título e corpo do PR.
    - Substituir valores nulos ou ausentes por representações canônicas
      (string vazia, valor sentinela) sem lançar exceções silenciosas.
    - Truncar corpos de PR excessivamente longos para o limite máximo
      aceitável pelo contexto dos LLMs, preservando a estrutura semântica.
    - Remover caracteres de controle, encoding inválido e artefatos de
      formatação (ex: markdown bruto, tags HTML escapadas).
    - Todas as funções devem ser puras: dado o mesmo `PRRecord` de entrada,
      a saída deve ser sempre idêntica e nenhum estado externo é modificado.

Não deve:
    - Normalizar valores (responsabilidade de normalizing.py).
    - Filtrar registros (responsabilidade de filtering.py).
    - Realizar I/O de qualquer natureza.

Relacionado a:
    - Issue 03 (limpeza do texto antes do envio ao LLM)
    - Regra Geral 06 (dados pré-processados antes da camada LLM)
    - Regra Funcional 02 (funções puras, sem efeitos colaterais)
    - Regra Funcional 07 (map(), filter(), funções lambda)
    - Conceito-Chave 05 (funções puras para limpeza)
"""
