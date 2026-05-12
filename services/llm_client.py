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
import time
import itertools
from typing import Generator, Iterator

try:
    from groq import Groq
except ImportError as exc:
    raise ImportError("Groq não está instalado. Execute: uv add groq") from exc

from core.models.pr_record import PRRecord

# ---------------------------------------------------------------------------
# Constantes de configuração
# ---------------------------------------------------------------------------

_MAX_RETRIES: int = 3
_BACKOFF_FACTOR: float = 0.5  # segundos — base para backoff exponencial


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------


def _build_client(api_key: str | None) -> Groq:
    """
    Factory que constrói o cliente Groq.

    Args:
        api_key: Chave de autenticação lida do ambiente.

    Returns:
        Instância de Groq pronta para invocar o modelo.

    Raises:
        ValueError: Se a chave de API não estiver definida.
    """
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY não está definida. "
            "Adicione a variável ao arquivo .env antes de executar."
        )
    return Groq(api_key=api_key)


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
            "Infer the project type and return ONLY a JSON object with a single key.",
            "Valid values for 'project_type': 'library', 'web_app', 'framework', 'cli', 'other'.",
            "Return ONLY the JSON object. No explanations, no markdown, no extra text.",
            'Example: {"project_type": "library"}',
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
    client: Groq,
    model: str,
    prompt: str,
    max_retries: int = _MAX_RETRIES,
    backoff: float = _BACKOFF_FACTOR,
) -> str:
    """
    Invoca o cliente LLM com retry e backoff exponencial.

    Laço justificado: retry de I/O de rede é inerentemente imperativo
    e pertence exclusivamente à camada services/.

    Args:
        client: Instância do Groq já configurada.
        model: Identificador do modelo a ser utilizado.
        prompt: Prompt completo a ser enviado.
        max_retries: Número máximo de tentativas.
        backoff: Fator base para o backoff exponencial em segundos.

    Returns:
        Resposta bruta do LLM como string.

    Raises:
        ValueError: Se todas as tentativas falharem ou retornarem vazio.
    """
    last_exc: Exception = ValueError("Nenhuma tentativa foi realizada.")

    # Laço justificado: retry de I/O de rede (services/)
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.choices[0].message.content
            if not result:
                raise ValueError(
                    f"LLM retornou resposta vazia na tentativa {attempt + 1}."
                )
            return result
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(backoff * (2**attempt))  # backoff exponencial

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
    model = os.getenv("LAZYPR_MODEL", "llama3-8b-8192")
    max_chars = int(os.getenv("LAZYPR_MAX_BODY_CHARS", "1500"))

    client = _build_client(api_key)
    prompt = _build_prompt(records, max_chars)

    return _invoke_with_retry(client=client, model=model, prompt=prompt)
