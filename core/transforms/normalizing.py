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

from __future__ import annotations

import functools
from typing import Optional

from core.models.analysis_result import AnalysisResult
from core.models.pr_record import PRRecord

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
    """
    if text is None or not isinstance(text, str):
        return None

    normalized_input = text.strip().lower()

    # Procura a linguagem canônica que contém esta variação
    # Implementado com next() + iterador para pureza funcional
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
    """Calcula número de caracteres no corpo do PR."""
    return len(body) if body else 0


def calculate_word_count(body: str) -> int:
    """Calcula número de palavras no corpo do PR."""
    if not body:
        return 0
    return len(body.split())


@functools.lru_cache(maxsize=256)
def normalize_label(label: str, field: str) -> str:
    """Normaliza label de classificação LLM para vocabulário controlado.

    Implementado com map() + filter() sobre vocabulário válido:
    se label exato está no conjunto válido, retorna; caso contrário,
    retorna "other" como sentinela.
    """
    if not label:
        return "other"

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
    Função pura — nunca modifica record original, apenas retorna cópia enriquecida.
    """
    normalized_language = normalize_language(record.language)
    return record._replace(language=normalized_language)


def normalize_analysis_result(
    result: AnalysisResult,
) -> AnalysisResult:

    return result._replace(
        project_type=normalize_label(
            result.project_type,
            "project_type",
        ),
        pr_nature=normalize_label(
            result.pr_nature,
            "pr_nature",
        ),
        clarity_level=normalize_label(
            result.clarity_level,
            "clarity_level",
        ),
    )
