"""
core/models/analysis_result.py
===============================
Define a estrutura de dados imutável que representa um pull request após
o enriquecimento semântico realizado pelas classificações dos LLMs.

Responsabilidades:
    - Declarar o tipo `AnalysisResult` como NamedTuple (ou dataclass frozen=True),
      estendendo os campos de `PRRecord` com os atributos classificados:
        · project_type   — tipo do repositório (biblioteca, framework, app web, etc.)
        · pr_nature      — natureza da contribuição (bug fix, feature, refatoração, docs)
        · clarity_level  — clareza da descrição (insuficiente, básica, boa, excelente)
        · char_count     — contagem de caracteres do corpo do PR
        · word_count     — contagem de palavras do corpo do PR
    - Ser a estrutura-alvo produzida pelo pipeline após a etapa de classificação,
      consumida pelas camadas de agregação e visualização.
    - Garantir que classificações ausentes (falha de LLM, cache miss) sejam
      representadas de forma explícita (ex: valor sentinela ou Optional).

Não deve:
    - Chamar LLMs nem realizar I/O.
    - Conter lógica de agregação ou plotagem.

Relacionado a:
    - Issues 02, 03, 04 (classificações semânticas)
    - HU 02, 03, 04 (categorização de repositório, natureza e clareza)
    - Regra Geral 07 (estruturas imutáveis)
    - Regra Funcional 03 (imutabilidade de dados)
"""

from typing import NamedTuple


class AnalysisResult(NamedTuple):
    """Resultado da análise semântica de um PR.

    Estende PRRecord com classificações obrigatórias do LLM,
    representando um PR após enriquecimento com tipos de projeto,
    natureza da contribuição e clareza da descrição.

    Attributes:
        id: Identificador único do comentário.
        html_url: URL completa do comentário no GitHub.
        repo: Repositório no formato "owner/repo".
        path: Arquivo comentado.
        body: Texto completo do comentário.
        diff_hunk: Trecho do diff associado.
        author: Login do autor.
        author_association: Relação com repositório.
        commit_id: ID do commit.
        line: Número da linha.
        language: Linguagem do arquivo.
        created_at: Data de criação.
        project_type: Tipo de projeto ("library"|"web_app"|"framework"|"cli"|"other").
        pr_nature: Natureza da contribuição ("bug_fix"|"feature"|"refactoring"|"documentation"|"other").
        clarity_level: Clareza da descrição ("insufficient"|"basic"|"good"|"excellent").
        char_count: Contagem de caracteres do body.
        word_count: Contagem de palavras do body.
    """

    id: int
    html_url: str
    repo: str
    path: str
    body: str
    diff_hunk: str
    author: str
    author_association: str
    commit_id: str
    line: int
    language: str | None
    created_at: str | None
    project_type: str
    pr_nature: str
    clarity_level: str
    char_count: int
    word_count: int
