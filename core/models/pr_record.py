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

from dataclasses import dataclass


@dataclass(frozen=True)
class PRRecord:
    """Registro imutável de um pull request bruto do dataset."""

    id: str
    repository: str
    title: str
    body: str
    author: str
    language: str | None = None
    created_at: str | None = None
