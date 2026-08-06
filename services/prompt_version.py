"""
services/prompt_version.py
===========================
Declara a versão vigente dos prompts enviados ao LLM, como dimensão própria
da chave de cache.

Responsabilidades:
    - Expor `PROMPT_VERSION`, que compõe o nome de arquivo dos dois espaços de
      nomes do cache (`analysis/` e `repo-classification/`), ao lado da versão
      de esquema de cada um.

Não deve:
    - Importar `services/llm_client.py`, nem qualquer coisa que dependa do
      Agno. O módulo é deliberadamente neutro: `services/storage.py` precisa
      desta constante, e o `llm_client` levanta `ImportError` na importação
      quando o Agno não está instalado — acoplar os dois faria todo teste de
      storage exigir a biblioteca de LLM.

Relacionado a:
    - Regra Geral 04 (persistência para evitar recomputação)
    - ADR-0002 (clareza avaliada sobre o Comentário de Revisão)
    - ADR-0003 (filtragem como recorte de visualização)
"""

# Versão da rubrica dos prompts. Bumpar este valor invalida sozinho todas as
# classificações já persistidas — nos DOIS espaços de nomes do cache — sem que
# ninguém precise apagar `.cache/` à mão: os resultados antigos passam a ser
# procurados sob outro nome de arquivo, dão miss e são reprocessados.
#
# Versão de esquema (formato de armazenamento) e versão de prompt (rubrica) são
# dimensões independentes: bumpar uma não mexe no que a outra invalida.
#
# "p1" é a rubrica introduzida pela issue #85: o prompt passou a descrever o
# dado real — um Comentário de Revisão julgado ao lado do seu `diff_hunk` — em
# vez de cobrar dele a rubrica de uma descrição de Pull Request. As
# classificações produzidas pela rubrica anterior não são comparáveis com as
# desta (ADR-0002), e por isso não podem sobreviver ao corte.
PROMPT_VERSION: str = "p1"
