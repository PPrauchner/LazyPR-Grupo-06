"""
services/llm_client.py
=======================
Isola todas as chamadas aos modelos de linguagem como efeito colateral
explícito, utilizando a biblioteca Agno com backends Groq ou OpenRouter.

Responsabilidades:
    - Implementar `classify_batch(prompts)` que envia um lote de prompts
      estruturados ao LLM e retorna as classificações em formato JSON
      parseado, sem expor detalhes do provider ao restante da aplicação.
    - Garantir que os dados enviados ao LLM já estejam pré-processados
      (limpos e normalizados) pelo pipeline funcional — este módulo não
      realiza nenhum pré-processamento.
    - Estruturar os prompts para retornar exclusivamente JSON válido com
      os campos esperados (project_type, pr_nature, clarity_level),
      facilitando o parsing funcional do resultado.
    - Implementar retry com backoff exponencial para falhas transitórias
      de rede, sem introduzir estado global.
    - Expor a chave de API via variável de ambiente, nunca hardcoded.

Não deve:
    - Processar, limpar ou agregar dados.
    - Persistir resultados (responsabilidade de storage.py).
    - Ser chamado diretamente pelo pipeline funcional — apenas por
      classifiers.py.

Relacionado a:
    - Issues 02, 03, 04 (chamadas LLM para cada tipo de classificação)
    - Regra Geral 03 (classificações realizadas por LLMs)
    - Regra Geral 06 (LLM como efeito colateral isolado)
    - Regra Funcional 02 (isolamento de efeitos colaterais)
    - Dica 05 (Agno + prompts retornando JSON)
    - Dica 07 (Groq/OpenRouter sem custo)
"""
