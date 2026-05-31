"""
core/models/pr_record.py
========================
Define a estrutura de dados imutável que representa um pull request bruto,
tal como lido pelo módulo de ingestão antes de qualquer enriquecimento.

Responsabilidades:
    - Declarar o tipo `PRRecord` como NamedTuple (ou dataclass frozen=True),
      contendo todos os campos presentes no dataset do Kaggle:
      id, repositório, título, corpo, autor, linguagem, data de criação, etc.
    - Garantir imutabilidade em tempo de execução, impedindo modificações
      acidentais durante as etapas do pipeline.
    - Servir como contrato de interface entre o módulo de ingestão
      (services/ingestion.py) e as etapas de transformação (core/transforms/).

Não deve:
    - Conter lógica de negócio, validação ou I/O.
    - Depender de nenhum outro módulo do projeto.

Relacionado a:
    - Issue 01 (ingestão de datasets)
    - HU 01 (upload de datasets para análise)
    - Regra Geral 07 (estruturas imutáveis)
    - Regra Funcional 03 (imutabilidade de dados)
"""

from typing import NamedTuple


class PRRecord(NamedTuple):
    """Registro imutável de um PR bruto do dataset Kaggle.

    Representa um comentário de pull request com todos os campos
    originais do dataset antes de enriquecimento semântico.

    Attributes:
        id: Identificador único do comentário.
        html_url: URL completa do comentário no GitHub.
        repo: Repositório no formato "owner/repo".
        path: Arquivo comentado (ex: "src/main.py").
        body: Texto completo do comentário.
        diff_hunk: Trecho do diff associado.
        author: Login do autor do comentário.
        author_association: Relação com repo ("OWNER", "MEMBER", "CONTRIBUTOR", etc).
        commit_id: ID do commit referenciado.
        line: Número da linha comentada.
        language: Linguagem principal do arquivo (None se indeterminada).
        created_at: Data de criação no ISO format (None se ausente).
    """

    from typing import NamedTuple

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
    language: str | None = None
    created_at: str | None = None
