"""
services/classifiers.py
========================
Orquestra as classificações semânticas realizadas pelos LLMs, gerenciando
estratégias de batching, cache e integração com o pipeline funcional.

Responsabilidades:
    - Implementar `classify_project_type(records)` que agrupa PRs do mesmo
      repositório em um único lote antes de chamar `llm_client.py`,
      evitando uma chamada por PR e reduzindo custo conforme a Dica 06.
    - Implementar `classify_pr_nature(record)` que envia título e corpo
      limpo de um PR ao LLM para determinar sua natureza
      (bug_fix, feature, refactoring, documentation).
    - Implementar `classify_clarity(record)` que instrui o LLM a avaliar
      a clareza da descrição, retornando um dos níveis do vocabulário
      controlado (insuficiente, básica, boa, excelente).
    - Verificar o cache (via utils/memoization.py) antes de qualquer
      chamada ao LLM, delegando a chamada real apenas em caso de cache miss.
    - Pós-processar a resposta JSON do LLM via funções puras de
      normalizing.py antes de construir o `AnalysisResult`.

Não deve:
    - Conter lógica de plotagem, agregação ou I/O de arquivo.
    - Substituir processamento funcional que deve ser feito no core/.

Relacionado a:
    - Issue 02 (categorização de repositórios)
    - Issue 03 (classificação da natureza do PR)
    - Issue 04 (avaliação de clareza das descrições)
    - HU 02, 03, 04 (enriquecimento semântico)
    - Regra Geral 04 (persistência para evitar recomputação)
    - Regra Geral 06 (LLM recebe dados pré-processados)
    - Dica 06 (agrupamento de PRs por repositório)
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from core.transforms.cleaning import CleanPRRecord

# Interfaces (substituir pelas implementações reais quando fizer llm_client)


def call_llm(prompt: str) -> str:
    raise NotImplementedError("Implemente em services/llm_client.py")


def get_cache(key: str) -> str | None:
    raise NotImplementedError("Implemente em utils/memoization.py")


def set_cache(key: str, value: str) -> None:
    raise NotImplementedError("Implemente em utils/memoization.py")


# Vocabulários controlados


class ProjectType(str, Enum):
    LIBRARY = "library"
    CLI = "cli"
    API = "api"
    WEB_APP = "web_app"
    DATA_PIPELINE = "data_pipeline"
    UNKNOWN = "unknown"


class PRNature(str, Enum):
    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class ClarityLevel(str, Enum):
    INSUFICIENTE = "insuficiente"
    BASICA = "basica"
    BOA = "boa"
    EXCELENTE = "excelente"

    @property
    def score(self) -> int:
        return {"insuficiente": 1, "basica": 2, "boa": 3, "excelente": 4}[self.value]


# Resultados
@dataclass(frozen=True)
class ProjectTypeResult:
    repository: str
    project_type: ProjectType
    raw_response: str


@dataclass(frozen=True)
class PRNatureResult:
    nature: PRNature
    raw_response: str


@dataclass(frozen=True)
class ClarityResult:
    level: ClarityLevel
    score: int
    raw_response: str


def _cached_call(key: str, prompt: str) -> str:
    """Retorna do cache ou chama o LLM e armazena o resultado."""
    cached = get_cache(key)
    if cached is not None:
        return cached
    response = call_llm(prompt)
    set_cache(key, response)
    return response


def _parse(raw: str, field: str) -> str:
    """Extrai um campo do JSON retornado pelo LLM e normaliza o valor."""
    try:
        data = json.loads(
            raw.strip().removeprefix("```json").removesuffix("```").strip()
        )
        return data.get(field, "").strip().lower().replace(" ", "_")
    except json.JSONDecodeError:
        return ""


_PROMPTS = {
    "project_type": (
        'Classifique o tipo do projeto. Responda APENAS com JSON: {"project_type": "<valor>"}\n'
        "Valores: library, cli, api, web_app, data_pipeline, unknown"
    ),
    "nature": (
        'Classifique a natureza do PR. Responda APENAS com JSON: {"nature": "<valor>"}\n'
        "Valores: bug_fix, feature, refactoring, documentation, unknown"
    ),
    "clarity": (
        'Avalie a clareza da descrição. Responda APENAS com JSON: {"clarity": "<valor>"}\n'
        "Valores: insuficiente, basica, boa, excelente\n"
        "insuficiente=ausente/genérica | basica=sem contexto | boa=explica o porquê | excelente=completa com impacto"
    ),
}


def classify_project_type(records: Iterable[CleanPRRecord]) -> list[ProjectTypeResult]:
    """Agrupa PRs por repositório e faz uma única chamada ao LLM por grupo."""
    groups: dict[str, list[CleanPRRecord]] = defaultdict(list)
    for r in records:
        groups[r.repository].append(r)

    results = []
    for repo, prs in groups.items():
        sample = "\n".join(f"- {pr.title}" for pr in prs[:10])
        prompt = f"{_PROMPTS['project_type']}\n\nRepositório: {repo}\nPRs:\n{sample}"
        raw = _cached_call(f"project_type:{repo}", prompt)
        value = _parse(raw, "project_type")
        project_type = (
            ProjectType(value)
            if value in ProjectType._value2member_map_
            else ProjectType.UNKNOWN
        )
        results.append(ProjectTypeResult(repo, project_type, raw))
    return results


def classify_pr_nature(record: CleanPRRecord) -> PRNatureResult:
    """Classifica a natureza do PR
    Sendo eles: bug_fix, feature, refactoring e documentation."""

    prompt = f"{_PROMPTS['nature']}\n\nTítulo: {record.title}\nDescrição:\n{record.body or '[sem descrição]'}"
    raw = _cached_call(f"nature:{record.title}:{record.body[:200]}", prompt)
    value = _parse(raw, "nature")
    nature = (
        PRNature(value) if value in PRNature._value2member_map_ else PRNature.UNKNOWN
    )
    return PRNatureResult(nature, raw)


def classify_clarity(record: CleanPRRecord) -> ClarityResult:
    """Avalia a clareza da descrição em quatro níveis."""
    prompt = f"{_PROMPTS['clarity']}\n\nTítulo: {record.title}\nDescrição:\n{record.body or '[sem descrição]'}"
    raw = _cached_call(f"clarity:{record.title}:{record.body[:200]}", prompt)
    value = _parse(raw, "clarity")
    level = (
        ClarityLevel(value)
        if value in ClarityLevel._value2member_map_
        else ClarityLevel.INSUFICIENTE
    )
    return ClarityResult(level, level.score, raw)
