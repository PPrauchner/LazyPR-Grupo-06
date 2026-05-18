"""
core/transforms/normalizing.py
================================
Fornece funções puras de normalização que padronizam os valores dos campos
de um `PRRecord` para formatos canônicos utilizados nas análises.

Responsabilidades:
    - Normalizar strings de linguagem de programação para um conjunto
      controlado de valores (ex: "python", "Python 3" → "python").
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

import functools
from typing import Optional

from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult

# ---------------------------------------------------------------------------
# Vocabulário Controlado (Normalizações Obrigatórias)
# ---------------------------------------------------------------------------

_VALID_PROJECT_TYPES = frozenset(["library", "web_app", "framework", "cli", "other"])
_VALID_PR_NATURES = frozenset(
    ["bug_fix", "feature", "refactoring", "documentation", "other"]
)
_VALID_CLARITY_LEVELS = frozenset(["insufficient", "basic", "good", "excellent"])

# Mapeamento de variações de linguagem para forma canônica
# Estratégia: map() + filter() para cada variação encontrada
_LANGUAGE_VARIANTS = {
    "python": frozenset(["python", "python3", "python 3", "py", "py3"]),
    "javascript": frozenset(["javascript", "js", "ecmascript", "es6", "es2015"]),
    "typescript": frozenset(["typescript", "ts"]),
    "java": frozenset(["java", "jvm"]),
    "csharp": frozenset(["csharp", "c#", ".net"]),
    "go": frozenset(["go", "golang"]),
    "rust": frozenset(["rust", "rs"]),
    "cpp": frozenset(["c++", "cpp", "cxx"]),
    "c": frozenset(["c"]),
    "ruby": frozenset(["ruby", "rb"]),
    "php": frozenset(["php"]),
}


# ---------------------------------------------------------------------------
# Funções Puras de Normalização
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=256)
def normalize_language(text: str | None) -> str | None:
    """Normaliza string de linguagem para forma canônica.

    Mapeia variações ("Python 3", "py3") para forma canônica ("python").
    Se não encontrar variação conhecida, retorna None.

    Args:
        text: Texto bruto de linguagem (ex: "Python 3", "javascript").

    Returns:
        Forma canônica em minúsculas (ex: "python"), ou None se não
        reconhecida.

    Examples:
        >>> normalize_language("Python")
        'python'
        >>> normalize_language("JavaScript")
        'javascript'
        >>> normalize_language("UnknownLang")
        None
        >>> normalize_language(None)
        None
    """
    if text is None or not isinstance(text, str):
        return None

    normalized_input = text.strip().lower()

    # Procura a linguagem canônica que contém esta variação
    # Implementado com próximo() + filter() para pureza funcional
    matching_lang = next(
        (
            lang
            for lang, variants in _LANGUAGE_VARIANTS.items()
            if normalized_input in variants
        ),
        None,
    )

    return matching_lang


def calculate_char_count(body: str) -> int:
    """Calcula número de caracteres no corpo do PR.

    Args:
        body: Texto do corpo do PR.

    Returns:
        Número de caracteres em body.

    Examples:
        >>> calculate_char_count("hello")
        5
        >>> calculate_char_count("")
        0
    """
    return len(body) if body else 0


def calculate_word_count(body: str) -> int:
    """Calcula número de palavras no corpo do PR.

    Implementado via split() — palavras são tokens separados por whitespace.

    Args:
        body: Texto do corpo do PR.

    Returns:
        Número de palavras (tokens whitespace-separated).

    Examples:
        >>> calculate_word_count("hello world test")
        3
        >>> calculate_word_count("single")
        1
        >>> calculate_word_count("")
        0
    """
    if not body:
        return 0
    return len(body.split())


@functools.lru_cache(maxsize=256)
def normalize_label(label: str, field: str) -> str:
    """Normaliza label de classificação LLM para vocabulário controlado.

    Implementado com map() + filter() sobre vocabulário válido:
    se label exato está no conjunto válido, retorna; caso contrário,
    retorna "other" como sentinela.

    Args:
        label: Label bruto retornado pelo LLM.
        field: Campo sendo normalizado ("project_type", "pr_nature",
               "clarity_level") para seleção do vocabulário correto.

    Returns:
        Label normalizado do vocabulário controlado, ou "other" se inválido.

    Examples:
        >>> normalize_label("library", "project_type")
        'library'
        >>> normalize_label("biblioteca", "project_type")  # inválido
        'other'
        >>> normalize_label("bug_fix", "pr_nature")
        'bug_fix'
        >>> normalize_label("BugFix", "pr_nature")  # variação inválida
        'other'
    """
    normalized_label = label.strip().lower().replace("-", "_")

    # Seleciona vocabulário correto baseado no campo
    valid_vocab = {
        "project_type": _VALID_PROJECT_TYPES,
        "pr_nature": _VALID_PR_NATURES,
        "clarity_level": _VALID_CLARITY_LEVELS,
    }.get(
        field, _VALID_PROJECT_TYPES
    )  # padrão seguro

    # Retorna label se válido, senão "other"
    return normalized_label if normalized_label in valid_vocab else "other"


def normalize_pr_record(record: PRRecord) -> PRRecord:
    """Normaliza campos de um PRRecord para valores canônicos.

    Retorna novo PRRecord com language normalizada via normalize_language().
    Função pura — nunca modifica record original, apenas retorna cópia
    enriquecida.

    Args:
        record: PRRecord a normalizar.

    Returns:
        Novo PRRecord com language normalizada.

    Examples:
        >>> pr = PRRecord(id=1, ..., language="Python 3", ...)
        >>> normalized = normalize_pr_record(pr)
        >>> normalized.language
        'python'
        >>> pr.language  # original inalterado
        'Python 3'
    """
    normalized_language = normalize_language(record.language)
    return record._replace(language=normalized_language)


def normalize_analysis_result(result: AnalysisResult) -> AnalysisResult:
    """Normaliza campos de um AnalysisResult para vocabulário controlado.

    Retorna novo AnalysisResult com labels de classificação normalizados
    via normalize_label(). Função pura — nunca modifica result original.

    Args:
        result: AnalysisResult a normalizar.

    Returns:
        Novo AnalysisResult com labels normalizados.

    Examples:
        >>> ar = AnalysisResult(..., project_type="biblioteca", ...)
        >>> normalized = normalize_analysis_result(ar)
        >>> normalized.project_type
        'other'
        >>> ar.project_type  # original inalterado
        'biblioteca'
    """
    normalized_project_type = normalize_label(result.project_type, "project_type")
    normalized_pr_nature = normalize_label(result.pr_nature, "pr_nature")
    normalized_clarity_level = normalize_label(result.clarity_level, "clarity_level")

    return result._replace(
        project_type=normalized_project_type,
        pr_nature=normalized_pr_nature,
        clarity_level=normalized_clarity_level,
    )

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
