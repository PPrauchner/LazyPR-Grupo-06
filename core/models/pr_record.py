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
    """
    Registro bruto produzido pela etapa de ingestao.

    Atribuições:
        id: Identificador do comentario no dataset original.
        html_url: URL do comentario no GitHub.
        repo: Repositorio extraido da html_url, no formato "owner/name".
        path: Caminho do arquivo comentado no pull request.
        body: Texto bruto do comentario.
        diff_hunk: Trecho do diff associado ao comentario.
        author: Login do autor do comentario, vindo do campo user.
        author_association: Relacao do autor com o repositorio.
        commit_id: Hash do commit associado ao comentario.
        line: Linha do arquivo relacionada ao comentario.
        language: Linguagem inferida quando disponivel; caso contrario, None.
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
    language: str | None
    created_at: str | None
