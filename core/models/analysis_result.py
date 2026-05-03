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

from dataclasses import dataclass
from typing import Optional

from core.models.pr_record import PRRecord


@dataclass(frozen=True)
class AnalysisResult(PRRecord):
    """Resultado da análise de um PR após enriquecimento semântico."""

    project_type: Optional[str] = None
    pr_nature: Optional[str] = None
    clarity_level: Optional[str] = None
    char_count: int = 0
    word_count: int = 0
