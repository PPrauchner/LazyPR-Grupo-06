"""
services/llm_client.py
=======================
Isola todas as chamadas aos modelos de linguagem como efeito colateral
explícito, utilizando a biblioteca Agno com backend Groq.

Responsabilidades:
    - Implementar `classify_project_type_batch()` que envia um lote de PRs
      do mesmo repositório ao LLM e retorna a classificação bruta como string.
    - Estruturar o prompt para que o modelo retorne estritamente uma das
      categorias válidas de projeto em formato JSON puro.
    - Implementar retry com backoff exponencial para falhas transitórias
      de rede, sem introduzir estado global.
    - Expor a chave de API via variável de ambiente, nunca hardcoded.

Não deve:
    - Processar, limpar, normalizar ou agregar dados.
    - Persistir resultados (responsabilidade de storage.py).
    - Ser chamado diretamente pelo pipeline funcional — apenas por classifiers.py.

Relacionado a:
    - Issues 02, 03, 04 (chamadas LLM para cada tipo de classificação)
    - Regra Geral 06 (LLM como efeito colateral isolado)
    - Regra Funcional 02 (isolamento de efeitos colaterais)
    - Dica 05 (Agno + prompts retornando JSON)
    - Dica 07 (Groq/OpenRouter sem custo)
"""

import os
import re
import time
import itertools
import logging
from typing import Generator, Iterator, Literal, Type
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from agno.agent import Agent
    from agno.models.groq import Groq as GroqModel
except ImportError as exc:
    raise ImportError("Agno não está instalado. Execute: uv add agno") from exc

from pydantic import BaseModel

from core.models.pr_record import PRRecord

# ---------------------------------------------------------------------------
# Constantes de configuração
# ---------------------------------------------------------------------------

_MAX_RETRIES: int = 6
_BACKOFF_FACTOR: float = 2.0

# Throttle: o plano gratuito do Groq limita 30 RPM → 1 requisição a cada 2 s
# mais margem de segurança (≤ 28 RPM).
_THROTTLE_SECONDS: float = 2.1

_DEFAULT_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Schemas de saída — vivem em services/ para que core/ não ganhe nenhum
# import novo (Regra Geral 06 / Regra Específica 02).
# ---------------------------------------------------------------------------

ProjectTypeValue = Literal["library", "web_app", "framework", "cli", "other"]
PRNatureValue = Literal[
    "bug_fix", "feature", "refactoring", "documentation", "other"
]
ClarityLevelValue = Literal["insufficient", "basic", "good", "excellent"]


class ProjectTypeOutput(BaseModel):
    """Saída estruturada da classificação de tipo de projeto."""

    project_type: ProjectTypeValue


class PRNatureOutput(BaseModel):
    """Saída estruturada da classificação de natureza da contribuição."""

    pr_nature: PRNatureValue


class ClarityOutput(BaseModel):
    """Saída estruturada da avaliação de clareza da descrição."""

    clarity_level: ClarityLevelValue


class PRNatureAndClarityOutput(BaseModel):
    """Saída estruturada da chamada unificada natureza + clareza."""

    pr_nature: PRNatureValue
    clarity_level: ClarityLevelValue

# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------


def _parse_retry_after(error_message: str, default: float = 5.0) -> float:
    """Extrai o tempo de espera sugerido pela API Groq em erros 429.

    O Groq inclui "Please try again in Xs" na mensagem de erro.
    Adiciona 1s de margem sobre o valor extraído.

    Args:
        error_message: Texto do erro retornado pela API.
        default: Tempo de espera padrão quando não encontrado na mensagem.

    Returns:
        Segundos a aguardar antes da próxima tentativa.
    """
    match = re.search(r"try again in (\d+(?:\.\d+)?)s", str(error_message))
    return float(match.group(1)) + 1.0 if match else default


def _build_agent(
    api_key: str | None,
    model: str,
    output_schema: Type[BaseModel],
) -> Agent:
    """
    Factory que constrói o agente Agno com backend Groq.

    O retry e o throttle **não** são delegados ao Agno (`retries=0`): o
    controle de rate limit pertence a `_invoke_with_retry`, porque um
    throttle quebrado não falha em teste — falha com 429 em produção.

    Args:
        api_key: Chave de autenticação lida do ambiente.
        model: Identificador do modelo Groq a ser utilizado.
        output_schema: Schema Pydantic que o Agno deve validar na resposta.

    Returns:
        Instância de Agent pronta para invocar o modelo.

    Raises:
        ValueError: Se a chave de API não estiver definida.
    """
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY não está definida. "
            "Adicione a variável ao arquivo .env antes de executar."
        )
    return Agent(
        model=GroqModel(id=model, api_key=api_key),
        output_schema=output_schema,
        retries=0,
        telemetry=False,
    )


def _format_record(
    record: PRRecord,
    max_path: int = 60,
    max_diff: int = 200,
    max_body: int = 200,
) -> str:
    """
    Formata um único PRRecord em uma string de contexto para o prompt.
    Função pura — não produz efeitos colaterais.

    Args:
        record: Registro de PR a ser formatado.
        max_path: Limite de caracteres para o campo path.
        max_diff: Limite de caracteres para o campo diff_hunk.
        max_body: Limite de caracteres para o campo body.

    Returns:
        String formatada representando o registro no contexto do prompt.
    """
    return (
        f"\n- Path: {record.path[:max_path]}"
        f"\n  Diff: {record.diff_hunk[:max_diff]}..."
        f"\n  Body: {record.body[:max_body]}..."
    )


def _take_within_limit(
    segments: Iterator[str],
    limit: int,
    initial_length: int,
) -> Generator[str, None, None]:
    """
    Consome segmentos de texto enquanto o comprimento acumulado não
    ultrapassar o limite definido. Implementado como gerador puro,
    sem mutação de variáveis externas.

    Args:
        segments: Iterador de strings a serem consumidas.
        limit: Limite máximo de caracteres acumulados.
        initial_length: Comprimento já ocupado pelas partes estáticas do prompt.

    Yields:
        Segmentos que cabem dentro do limite.
    """
    accumulated = initial_length
    for segment in segments:
        next_length = accumulated + len(segment)
        if next_length > limit:
            return
        accumulated = next_length
        yield segment


def _build_prompt(
    records: tuple[PRRecord, ...],
    max_chars: int,
) -> str:
    """
    Constrói o prompt completo a ser enviado ao LLM combinando as
    instruções estáticas com o contexto dinâmico dos PRs.

    Utiliza map() e itertools.chain para composição lazy dos segmentos,
    respeitando o limite de caracteres via _take_within_limit().

    Args:
        records: Tupla de PRRecords do mesmo repositório.
        max_chars: Limite máximo de caracteres do prompt completo.

    Returns:
        String do prompt pronta para envio ao LLM.
    """
    repo_name = records[0].repo

    system_instructions = "\n".join(
        [
            "You are an AI assistant classifying the type of a GitHub software project.",
            "You will receive metadata from Pull Request comments of the *same* repository.",
            "Infer the project type of the repository.",
            "Valid values for 'project_type': 'library', 'web_app', 'framework', 'cli', 'other'.",
        ]
    )

    repo_header = f"\nRepository: {repo_name}"
    prs_header = "\nPR context records:"

    static_part = f"{system_instructions}{repo_header}{prs_header}"
    initial_length = len(static_part)

    # Gerador lazy de segmentos formatados por PR
    formatted_segments: Iterator[str] = map(_format_record, records)

    # Consome apenas os segmentos que cabem dentro do limite
    limited_segments = _take_within_limit(
        segments=formatted_segments,
        limit=max_chars,
        initial_length=initial_length,
    )

    return "".join(itertools.chain([static_part], limited_segments))


def _invoke_with_retry(
    agent: Agent,
    prompt: str,
    max_retries: int = _MAX_RETRIES,
    backoff: float = _BACKOFF_FACTOR,
) -> BaseModel:
    """
    Invoca o agente Agno com throttle, retry e backoff exponencial.

    Esta função — e não o Agno — é a dona do controle de rate limit: aplica
    o throttle antes de cada requisição, respeita o tempo sugerido em erros
    429 e recua exponencialmente nas demais falhas.

    Laço justificado: retry de I/O de rede é inerentemente imperativo
    e pertence exclusivamente à camada services/.

    Args:
        agent: Instância de Agent do Agno já configurada com output_schema.
        prompt: Prompt completo a ser enviado.
        max_retries: Número máximo de tentativas.
        backoff: Fator base para o backoff exponencial em segundos.

    Returns:
        Instância do schema Pydantic validada pelo Agno.

    Raises:
        ValueError: Se todas as tentativas falharem ou retornarem vazio.
    """
    last_exc: Exception = ValueError("Nenhuma tentativa foi realizada.")

    # Laço justificado: retry de I/O de rede (services/)
    for attempt in range(max_retries):
        try:
            # Throttle obrigatório antes de cada requisição (30 RPM no plano free)
            time.sleep(_THROTTLE_SECONDS)
            result = agent.run(prompt).content
            if not hasattr(result, "model_dump_json"):
                raise ValueError(
                    f"LLM retornou resposta vazia ou não estruturada na "
                    f"tentativa {attempt + 1}."
                )
            return result
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                error_str = str(exc)
                # Erro 429: respeita o tempo sugerido pelo Groq ("try again in Xs")
                if "429" in error_str or "rate_limit_exceeded" in error_str:
                    wait = _parse_retry_after(error_str, default=backoff * (2 ** attempt))
                else:
                    wait = backoff * (2 ** attempt)
                logger.warning(f"Tentativa {attempt + 1} falhou. Aguardando {wait:.1f}s...")
                time.sleep(wait)

    raise ValueError(
        f"LLM falhou após {max_retries} tentativas. " f"Último erro: {last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# Interface pública
# ---------------------------------------------------------------------------


def classify_project_type_batch(records: tuple[PRRecord, ...]) -> str:
    """
    Envia um batch de PRs do mesmo repositório ao LLM e retorna
    a classificação bruta do tipo de projeto como string JSON.

    Todas as configurações são lidas do ambiente no momento da chamada,
    garantindo ausência de estado global. A resposta não é normalizada —
    essa responsabilidade é do chamador (services/classifiers.py).

    Args:
        records: Tupla de PRRecords pertencentes ao mesmo repositório.

    Returns:
        String bruta retornada pelo LLM, ex: '{"project_type": "library"}'.
        Não normalizada — normalização é responsabilidade do chamador.

    Raises:
        ValueError: Se a API key não estiver definida ou todas as
                    tentativas de invocação falharem.
        ImportError: Se a biblioteca Agno não estiver instalada.
    """
    if not records:
        return '{"project_type": "other"}'

    # Configurações lidas dentro do escopo da função — sem estado global
    api_key = os.getenv("GROQ_API_KEY")
    model = _DEFAULT_MODEL
    logger.debug(f"Usando modelo LLM: {model} para classify_project_type_batch")
    max_chars = int(os.getenv("LAZYPR_MAX_BODY_CHARS", "1500"))

    agent = _build_agent(api_key, model, ProjectTypeOutput)
    prompt = _build_prompt(records, max_chars)

    return _invoke_with_retry(agent=agent, prompt=prompt).model_dump_json()


def classify_pr_nature_single(record: PRRecord) -> str:
    """
    Classifica a natureza de um PR individual baseada no corpo da descrição.

    Envia um único PR ao LLM com prompt específico para inferir sua natureza:
    bug_fix, feature, refactoring, documentation ou other.

    Memoizado: mesma entrada (record) → mesma saída (cached).

    Args:
        record: PRRecord a classificar.

    Returns:
        String JSON bruta retornada pelo LLM,
        ex: '{"pr_nature": "feature"}'.

    Raises:
        ValueError: Se a API key não estiver definida ou LLM falhar.
    """
    if not record.body or not record.body.strip():
        return '{"pr_nature": "other"}'

    prompt = (
        "You are an AI assistant classifying the nature of a GitHub Pull Request.\n"
        "Analyze the PR description and determine its nature.\n"
        "Valid values for 'pr_nature': 'bug_fix', 'feature', 'refactoring', 'documentation', 'other'.\n"
        f"\nRepository: {record.repo}\n"
        f"Path: {record.path[:100]}\n"
        f"PR Description: {record.body[:1000]}\n"
    )

    api_key = os.getenv("GROQ_API_KEY")
    model = _DEFAULT_MODEL
    logger.debug(f"Usando modelo LLM: {model} para classify_pr_nature_single")

    agent = _build_agent(api_key, model, PRNatureOutput)
    return _invoke_with_retry(agent=agent, prompt=prompt).model_dump_json()


def classify_clarity_single(record: PRRecord) -> str:
    """
    Classifica o nível de clareza da descrição de um PR individual.

    Envia um único PR ao LLM com prompt específico para avaliar se a
    descrição é insufficient, basic, good ou excellent.

    Args:
        record: PRRecord a classificar.

    Returns:
        String JSON bruta retornada pelo LLM,
        ex: '{"clarity_level": "good"}'.

    Raises:
        ValueError: Se a API key não estiver definida ou LLM falhar.
    """
    if not record.body or not record.body.strip():
        return '{"clarity_level": "insufficient"}'

    prompt = (
        "You are an AI assistant evaluating the clarity of GitHub Pull Request descriptions.\n"
        "Assess the PR description and determine its clarity level.\n"
        "Valid values for 'clarity_level': 'insufficient', 'basic', 'good', 'excellent'.\n"
        "Consider: presence of context, problem statement, solution explanation, and examples.\n"
        f"\nRepository: {record.repo}\n"
        f"PR Description: {record.body[:1000]}\n"
    )

    api_key = os.getenv("GROQ_API_KEY")
    model = _DEFAULT_MODEL
    logger.debug(f"Usando modelo LLM: {model} para classify_clarity_single")

    agent = _build_agent(api_key, model, ClarityOutput)
    return _invoke_with_retry(agent=agent, prompt=prompt).model_dump_json()


def classify_pr_nature_and_clarity_single(record: PRRecord) -> str:
    """Classifica natureza e clareza de um PR em uma única chamada LLM.

    Substitui as duas chamadas separadas (classify_pr_nature_single +
    classify_clarity_single) por uma única requisição, reduzindo o consumo
    de RPM à metade para classificações por PR.

    Args:
        record: PRRecord a classificar.

    Returns:
        String JSON bruta com dois campos, ex:
        '{"pr_nature": "feature", "clarity_level": "good"}'.

    Raises:
        ValueError: Se a API key não estiver definida ou LLM falhar.
    """
    if not record.body or not record.body.strip():
        return '{"pr_nature": "other", "clarity_level": "insufficient"}'

    prompt = (
        "You are an AI assistant classifying a GitHub Pull Request.\n"
        "Analyze the PR description and classify both its nature and its clarity.\n"
        "Valid values for 'pr_nature': 'bug_fix', 'feature', 'refactoring', 'documentation', 'other'.\n"
        "Valid values for 'clarity_level': 'insufficient', 'basic', 'good', 'excellent'.\n"
        f"\nRepository: {record.repo}\n"
        f"Path: {record.path[:100]}\n"
        f"PR Description: {record.body[:1000]}\n"
    )

    api_key = os.getenv("GROQ_API_KEY")
    model = _DEFAULT_MODEL
    logger.debug(
        f"Usando modelo LLM: {model} para classify_pr_nature_and_clarity_single"
    )

    agent = _build_agent(api_key, model, PRNatureAndClarityOutput)
    return _invoke_with_retry(agent=agent, prompt=prompt).model_dump_json()
