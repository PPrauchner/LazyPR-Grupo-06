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

import json
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

from core.models.analysis_result import (
    UNKNOWN_CLARITY_LEVEL,
    UNKNOWN_PR_NATURE,
    UNKNOWN_PROJECT_TYPE,
)
from core.models.pr_record import PRRecord

# ---------------------------------------------------------------------------
# Constantes de configuração
# ---------------------------------------------------------------------------

_MAX_RETRIES: int = 6
_BACKOFF_FACTOR: float = 2.0

# Orçamento próprio para desvio de schema: uma retentativa cobre a flutuação
# genuína do JSON mode, que é probabilístico. Além disso a recusa é
# determinística — insistir só gasta cota e throttle (ver ADR-0004).
_SCHEMA_MAX_ATTEMPTS: int = 2

# Trecho do conteúdo recusado incluído no log, para atribuição.
_REFUSED_CONTENT_PREVIEW: int = 200

# Marcadores do erro que o Groq devolve quando o JSON mode não consegue
# produzir resposta válida: HTTP 400 com `code: json_validate_failed`. Esse
# desvio de schema sobe como exceção de `agent.run()`, não como conteúdo cru.
# A detecção é por texto, e não por `isinstance`: capturar a exceção pelo tipo
# exigiria importar o SDK do Groq (proibido neste projeto) ou uma exceção
# interna do Agno. É frágil de propósito — o custo de errar é apenas gastar o
# orçamento de rede, o comportamento anterior.
_SCHEMA_REFUSAL_MARKERS: tuple[str, ...] = (
    "json_validate_failed",
    "failed to generate json",
)

# Throttle: o plano gratuito do Groq limita 30 RPM → 1 requisição a cada 2 s
# mais margem de segurança (≤ 28 RPM).
_THROTTLE_SECONDS: float = 2.1

_DEFAULT_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Schemas de saída — vivem em services/ para que core/ não ganhe nenhum
# import novo (Regra Geral 06 / Regra Específica 02).
# ---------------------------------------------------------------------------

ProjectTypeValue = Literal["library", "web_app", "framework", "cli", "other"]
PRNatureValue = Literal["bug_fix", "feature", "refactoring", "documentation", "other"]
ClarityLevelValue = Literal["insufficient", "basic", "good", "excellent"]


class ProjectTypeOutput(BaseModel):
    """Saída estruturada da classificação de tipo de projeto."""

    project_type: ProjectTypeValue


class PRNatureAndClarityOutput(BaseModel):
    """Saída estruturada da chamada unificada natureza + clareza."""

    pr_nature: PRNatureValue
    clarity_level: ClarityLevelValue


# ---------------------------------------------------------------------------
# Respostas degradadas — usadas quando o orçamento de schema se esgota
# ---------------------------------------------------------------------------

# Esgotado o orçamento de schema, a classificação degrada para o sentinela em
# vez de propagar: abortar a Análise inteira por causa de um registro descarta
# tudo o que já foi pago em cota do Groq (ADR-0004). A recusa fica registrada
# em log, com repositório e conteúdo.
_DEGRADED_PROJECT_TYPE_JSON: str = json.dumps({"project_type": UNKNOWN_PROJECT_TYPE})
_DEGRADED_NATURE_AND_CLARITY_JSON: str = json.dumps(
    {"pr_nature": UNKNOWN_PR_NATURE, "clarity_level": UNKNOWN_CLARITY_LEVEL}
)


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


def _is_schema_refusal_exception(exc: BaseException) -> bool:
    """Informa se a exceção de `agent.run()` é, na verdade, desvio de schema.

    O Groq rejeita a própria geração quando o JSON mode não converge e devolve
    HTTP 400 `json_validate_failed`; isso sobe como exceção, não como conteúdo
    cru. Sem essa classificação, uma recusa determinística consumiria as 6
    tentativas de rede com backoff exponencial.

    A inspeção é textual porque o tipo da exceção não está disponível: importar
    `groq.BadRequestError` violaria a regra de não importar o SDK do Groq, e a
    exceção do Agno é interna. Falso negativo apenas devolve o caminho ao
    orçamento de rede — o comportamento anterior.

    Args:
        exc: Exceção levantada pela invocação do agente.

    Returns:
        True se a mensagem carregar um marcador de recusa de schema.
    """
    text = " ".join(
        str(part)
        for part in (exc, getattr(exc, "body", ""), getattr(exc, "message", ""))
    ).lower()
    return any(marker in text for marker in _SCHEMA_REFUSAL_MARKERS)


def _schema_budget_exhausted(
    repo: str,
    content: object,
    attempts: int,
    max_attempts: int,
) -> bool:
    """Registra um desvio de schema e informa se o orçamento acabou.

    Args:
        repo: Repositório cujo lote provocou a recusa.
        content: Conteúdo (ou exceção) recusado, para atribuição no log.
        attempts: Tentativas de schema já consumidas.
        max_attempts: Orçamento total de tentativas de schema.

    Returns:
        True quando o orçamento se esgotou e o chamador deve degradar para o
        sentinela `unknown`; False quando ainda há retentativa disponível.
    """
    preview = str(content)[:_REFUSED_CONTENT_PREVIEW]
    if attempts >= max_attempts:
        logger.error(
            f"O LLM devolveu conteúdo fora do schema para o repositório "
            f"'{repo}' em {attempts} tentativa(s). A classificação degradou "
            f"para o sentinela 'unknown'. Conteúdo recusado: {preview!r}"
        )
        return True
    logger.warning(
        f"Resposta fora do output_schema para '{repo}' na tentativa "
        f"{attempts}. Repetindo uma vez. Conteúdo recusado: {preview!r}"
    )
    return False


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
    repo: str = "desconhecido",
    max_retries: int = _MAX_RETRIES,
    backoff: float = _BACKOFF_FACTOR,
    schema_max_attempts: int = _SCHEMA_MAX_ATTEMPTS,
) -> BaseModel | None:
    """
    Invoca o agente Agno com throttle e dois orçamentos de tentativa distintos.

    Esta função — e não o Agno — é a dona do controle de rate limit: aplica
    o throttle antes de cada requisição, respeita o tempo sugerido em erros
    429 e recua exponencialmente nas falhas de rede.

    Falha de rede e desvio de schema não compartilham política. A rede é
    transitória e merece backoff longo; a recusa de schema é largamente
    determinística e insistir nela só queima cota. Por isso cada uma tem o seu
    orçamento, contado em separado. O desvio de schema chega por dois caminhos
    — conteúdo cru devolvido pelo Agno, ou HTTP 400 `json_validate_failed`
    levantado pelo Groq — e ambos usam o orçamento de schema.

    Laço justificado: retry de I/O de rede é inerentemente imperativo
    e pertence exclusivamente à camada services/.

    Args:
        agent: Instância de Agent do Agno já configurada com output_schema.
        prompt: Prompt completo a ser enviado.
        repo: Repositório de origem, usado para tornar a falha atribuível.
        max_retries: Número máximo de tentativas para falhas de rede.
        backoff: Fator base para o backoff exponencial em segundos.
        schema_max_attempts: Número máximo de tentativas para desvio de schema.

    Returns:
        Instância do schema Pydantic validada pelo Agno, ou None quando o
        orçamento de schema se esgotou — sinal para o chamador degradar para o
        sentinela `unknown` em vez de abortar a Análise inteira (ADR-0004).

    Raises:
        ValueError: Se as tentativas de rede se esgotarem.
    """
    network_attempts = 0
    schema_attempts = 0

    # Laço justificado: retry de I/O de rede (services/)
    while True:
        # Throttle obrigatório antes de cada requisição (30 RPM no plano free)
        time.sleep(_THROTTLE_SECONDS)
        try:
            response = agent.run(prompt)
        except Exception as exc:
            if _is_schema_refusal_exception(exc):
                schema_attempts += 1
                if _schema_budget_exhausted(
                    repo, exc, schema_attempts, schema_max_attempts
                ):
                    return None
                continue
            network_attempts += 1
            if network_attempts >= max_retries:
                raise ValueError(
                    f"LLM falhou após {max_retries} tentativas. " f"Último erro: {exc}"
                ) from exc
            error_str = str(exc)
            # Erro 429: respeita o tempo sugerido pelo Groq ("try again in Xs")
            exponential = backoff * (2 ** (network_attempts - 1))
            if "429" in error_str or "rate_limit_exceeded" in error_str:
                wait = _parse_retry_after(error_str, default=exponential)
            else:
                wait = exponential
            logger.warning(
                f"Tentativa de rede {network_attempts} falhou. "
                f"Aguardando {wait:.1f}s..."
            )
            time.sleep(wait)
            continue

        content = getattr(response, "content", None)
        if hasattr(content, "model_dump_json"):
            return content

        # Desvio de schema (ou resposta vazia): o Agno engole o ValidationError
        # e devolve o conteúdo cru, então o guarda é a ausência do serializador.
        schema_attempts += 1
        if _schema_budget_exhausted(
            repo, content, schema_attempts, schema_max_attempts
        ):
            return None


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
        Esgotado o orçamento de schema, devolve o sentinela
        '{"project_type": "unknown"}' em vez de propagar a recusa.

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

    response = _invoke_with_retry(agent=agent, prompt=prompt, repo=records[0].repo)
    return (
        response.model_dump_json()
        if response is not None
        else _DEGRADED_PROJECT_TYPE_JSON
    )


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
    response = _invoke_with_retry(agent=agent, prompt=prompt, repo=record.repo)
    return (
        response.model_dump_json()
        if response is not None
        else _DEGRADED_NATURE_AND_CLARITY_JSON
    )
