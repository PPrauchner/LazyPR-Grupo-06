"""
services/ingestion.py
======================
Implementa a camada de ingestão do dataset como efeito colateral isolado,
expondo geradores que produzem registros sob demanda sem carregar o arquivo
inteiro em memória.

Responsabilidades:
    - Implementar `stream_csv(filepath)` como gerador que lê o dataset do
      Kaggle (github-public-pull-request-comments) linha a linha, produzindo
      um `PRRecord` por iteração via `yield`.
    - Implementar `stream_json(filepath)` com comportamento equivalente para
      datasets em formato JSON Lines.
    - Aceitar upload de arquivo via interface Streamlit e redirecionar o
      stream para os geradores, sem exigir que o arquivo seja salvo em disco
      integralmente antes do processamento.
    - Calcular o hash SHA-256 do arquivo durante a leitura (sem segunda
      passagem), expondo-o para que `storage.py` determine se o dataset
      já foi analisado anteriormente.
    - Isolar completamente o I/O de arquivo: nenhuma outra camada deve
      abrir arquivos diretamente.

Não deve:
    - Conter lógica de limpeza, normalização ou classificação.
    - Chamar LLMs.

Relacionado a:
    - Issue 01 (upload e ingestão de datasets)
    - HU 01 (fazer upload de datasets para análise)
    - Regra Geral 02 (geradores para lazy evaluation)
    - Regra Funcional 04 (yield, expressões geradoras, itertools)
    - Conceito-Chave 01 (lazy evaluation via geradores)
    - Dica 01 (módulos csv/json com geradores linha a linha)
"""
