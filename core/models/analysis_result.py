"""
Define a estrutura de dados imutável que representa um pull request após
o enriquecimento semântico realizado pelas classificações dos LLMs.

Responsabilidades:
    - Declarar o tipo AnalysisResult como NamedTuple (ou dataclass frozen=True),
      estendendo os campos de PRRecord com os atributos classificados:
        - project_type: tipo do repositório (biblioteca, framework, app web, etc.)
        - pr_nature: natureza da contribuição (bug fix, feature, refatoração, docs)
        - clarity_level: clareza da descrição (insuficiente, básica, boa, excelente)
        - char_count: contagem de caracteres do corpo do PR
        - word_count: contagem de palavras do corpo do PR
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

from typing import Literal
from typing import NamedTuple

UNKNOWN_PROJECT_TYPE = "unknown"
UNKNOWN_PR_NATURE = "unknown"
UNKNOWN_CLARITY_LEVEL = "unknown"

ProjectType = Literal[
    "library",
    "web_app",
    "framework",
    "cli",
    "other",
    "unknown",
]

PRNature = Literal[
    "bug_fix",
    "feature",
    "refactoring",
    "documentation",
    "other",
    "unknown",
]

ClarityLevel = Literal[
    "insufficient",
    "basic",
    "good",
    "excellent",
    "unknown",
]


class AnalysisResult(NamedTuple):
    """Registro enriquecido produzido ao final do pipeline de análise.

    Este tipo estende o PRRecord bruto de forma estrutural: mantém todos os
    campos do registro original e acrescenta os atributos produzidos pelas
    etapas de classificação e normalização.

    As classificações usam vocabulário controlado. Quando uma classificação não
    estiver disponível por falha de LLM, cache miss ou resposta inválida, o
    pipeline deve preencher o campo correspondente com "unknown".
        A
    Campos herdados do PRRecord:
    id: Identificador do comentario no dataset original.
    html_url: URL do comentario no GitHub.
    repo: Repositorio extraido da html_url, no formato "owner/name".
    path: Caminho do arquivo comentado no pull request.
    body: Texto limpo do comentario.
    diff_hunk: Trecho do diff associado ao comentario.
    author: Login do autor do comentario.
    author_association: Relacao do autor com o repositorio.
    commit_id: Hash do commit associado ao comentario.
    line: Linha do arquivo relacionada ao comentario.
    language: Linguagem inferida ou normalizada para o registro.
    created_at: Data de criacao quando disponivel; caso contrario, None.
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
    language: str
    created_at: str | None
    project_type: ProjectType
    pr_nature: PRNature
    clarity_level: ClarityLevel
    char_count: int
    word_count: int