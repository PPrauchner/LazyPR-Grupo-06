"""
core/transforms/normalizing.py
================================
Fornece funções puras de normalização que padronizam os valores dos campos
de um `PRRecord` para formatos canônicos utilizados nas análises.

Responsabilidades:
    - Normalizar strings de linguagem de programação para um conjunto
      controlado de valores (ex: "python", "Python 3" → "Python").
    - Converter campos de data para objetos `datetime` ou timestamps Unix
      de forma consistente, independente do formato de origem do dataset.
    - Calcular e adicionar métricas derivadas de texto: `char_count` e
      `word_count` do corpo do PR, utilizadas nas visualizações da Issue 06.
    - Padronizar labels de classificação retornados pelo LLM para o
      vocabulário controlado esperado pelas agregações
      (ex: "bug-fix", "bugfix", "BugFix" → "bug_fix").
    - Todas as funções devem ser puras e retornar novas instâncias
      imutáveis, nunca modificando o registro de entrada.

Não deve:
    - Realizar chamadas a LLMs ou I/O.
    - Executar filtragem ou agregação.

Relacionado a:
    - Issue 06 (métricas de tamanho de descrição: chars e palavras)
    - Issue 04 (padronização dos labels de clareza retornados pelo LLM)
    - Regra Funcional 03 (imutabilidade — retornar nova instância)
    - Conceito-Chave 05 (funções puras para normalização)
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone
from core.transforms.cleaning import CleanPRRecord

_LANGUAGE_MAP: dict[str, str] = {
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "java": "Java",
    "kotlin": "Kotlin",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "c#": "C#",
    "csharp": "C#",
    "c++": "C++",
    "cpp": "C++",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "scala": "Scala",
    "shell": "Shell",
    "bash": "Shell",
    "unknown": "unknown",
}


_LABEL_MAP: dict[str, str] = {
    "bug_fix": "bug_fix",
    "bugfix": "bug_fix",
    "bug-fix": "bug_fix",
    "bug fix": "bug_fix",
    "fix": "bug_fix",
    "feature": "feature",
    "feat": "feature",
    "new feature": "feature",
    "refactoring": "refactoring",
    "refactor": "refactoring",
    "refact": "refactoring",
    "documentation": "documentation",
    "docs": "documentation",
    "doc": "documentation",
    # clareza
    "insuficiente": "insuficiente",
    "basica": "basica",
    "básica": "basica",
    "boa": "boa",
    "excelente": "excelente",
}


@dataclass(frozen=True)
class NormalizedPRRecord:
    """CleanPRRecord com campos normalizados e métricas derivadas."""

    title: str
    body: str
    author: str
    language: str
    project_type: str
    contribution_nature: str
    clarity_level: int
    created_at: date
    created_at_ts: int
    char_count: int
    word_count: int


# Funções puras de normalização
def normalize_language(value: str) -> str:
    """
    Converte variações de nome de linguagem para o valor canônico.

    Exemplos:
        "python 3" → "Python"
        "js"       → "JavaScript"
        "golang"   → "Go"

    Retorna o valor original capitalizado se não houver mapeamento.
    """
    return _LANGUAGE_MAP.get(value.strip().lower(), value.strip().capitalize())


def normalize_label(value: str) -> str:
    """
    Padroniza labels retornados pelo LLM para o vocabulário controlado.

    Exemplos:
        "BugFix"  → "bug_fix"
        "bug-fix" → "bug_fix"
        "docs"    → "documentation"
        "básica"  → "basica"

    Retorna o valor normalizado em snake_case se não houver mapeamento.
    """
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    return _LABEL_MAP.get(key, key)


def to_unix_timestamp(value: date) -> int:
    """
    Converte um objeto date para timestamp Unix (inteiro).

    Utiliza UTC para garantir consistência independente do ambiente.

    Exemplo:
        date(2024, 3, 15) → 1710460800
    """
    dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return int(dt.timestamp())


def compute_char_count(text: str) -> int:
    """Retorna o número de caracteres do texto."""
    return len(text)


def compute_word_count(text: str) -> int:
    """Retorna o número de palavras do texto (split por espaço/newline)."""
    return len(text.split()) if text else 0


# Ponto de entrada público
def normalize_pr_record(record: CleanPRRecord) -> NormalizedPRRecord:
    """
    Aplica todas as normalizações a um CleanPRRecord.

    Função pura: mesma entrada → sempre a mesma saída.
    Nenhum estado externo é lido ou modificado.
    """
    return NormalizedPRRecord(
        title=record.title,
        body=record.body,
        author=record.author,
        language=normalize_language(record.language),
        project_type=record.project_type,
        contribution_nature=normalize_label(record.contribution_nature),
        clarity_level=record.clarity_level,
        created_at=record.created_at,
        created_at_ts=to_unix_timestamp(record.created_at),
        char_count=compute_char_count(record.body),
        word_count=compute_word_count(record.body),
    )
