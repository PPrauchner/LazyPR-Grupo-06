"""
tests/test_llm_client.py
=========================
Testes da camada de chamadas ao LLM (services/llm_client.py) após a migração
para Agno.

Responsabilidades:
    - Verificar que as classificações são obtidas através de um agente Agno.
    - Provar que o throttle de 2,1 s e o backoff exponencial de até 6
      tentativas continuam ativos, usando um cliente dublado.
    - Cobrir os atalhos sem chamada ao LLM (body vazio, batch vazio).
"""

import json
import logging

import pytest

from services import llm_client

# ---------------------------------------------------------------------------
# Dublês
# ---------------------------------------------------------------------------


class FakeRunOutput:
    """Dublê do RunOutput do Agno: expõe apenas `content`."""

    def __init__(self, content: object) -> None:
        self.content = content


class FakeClassification:
    """Dublê de um schema Pydantic validado pelo Agno."""

    def __init__(self, **payload: str) -> None:
        self._payload = payload

    def model_dump_json(self) -> str:
        return json.dumps(self._payload)


class FakeAgent:
    """Dublê do Agent do Agno que devolve respostas roteirizadas.

    Attributes:
        scripted: Sequência de respostas; cada item é devolvido ou levantado.
        prompts: Prompts recebidos, na ordem das chamadas.
    """

    def __init__(self, *scripted: object) -> None:
        self.scripted = list(scripted)
        self.prompts: list[str] = []

    def run(self, prompt: str) -> FakeRunOutput:
        self.prompts.append(prompt)
        outcome = self.scripted.pop(0) if len(self.scripted) > 1 else self.scripted[0]
        if isinstance(outcome, Exception):
            raise outcome
        return FakeRunOutput(outcome)


@pytest.fixture
def recorded_sleeps(monkeypatch):
    """Substitui time.sleep por um registrador, sem esperar de verdade."""
    sleeps: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
    return sleeps


@pytest.fixture
def use_fake_agent(monkeypatch):
    """Injeta um FakeAgent no lugar do agente Agno real."""

    def _install(agent: FakeAgent) -> FakeAgent:
        monkeypatch.setattr(llm_client, "_build_agent", lambda *args, **kwargs: agent)
        return agent

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return _install


# ---------------------------------------------------------------------------
# Classificação via Agno
# ---------------------------------------------------------------------------


def test_classify_project_type_batch_returns_json_from_agno(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A resposta validada pelo Agno é serializada como JSON para o chamador."""
    agent = use_fake_agent(FakeAgent(FakeClassification(project_type="library")))

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "library"}
    assert len(agent.prompts) == 1


# ---------------------------------------------------------------------------
# Throttle e backoff — proteção contra o teto de 30 RPM do plano gratuito
# ---------------------------------------------------------------------------


def test_throttle_precedes_every_request(sample_pr, use_fake_agent, recorded_sleeps):
    """Cada requisição é precedida por uma pausa de 2,1 s.

    Falha se alguém remover ou encurtar o throttle: o 429 no meio de uma
    análise longa não aparece em teste, esta asserção aparece.
    """
    use_fake_agent(FakeAgent(FakeClassification(project_type="cli")))

    llm_client.classify_project_type_batch((sample_pr,))

    assert recorded_sleeps == [2.1]


def test_retries_six_times_with_exponential_backoff(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Falha persistente esgota 6 tentativas, recuando exponencialmente.

    Falha se o número de tentativas cair, se o backoff deixar de dobrar ou
    se o throttle deixar de ser aplicado antes de cada tentativa.
    """
    agent = use_fake_agent(FakeAgent(RuntimeError("connection reset")))

    with pytest.raises(ValueError, match="6 tentativas"):
        llm_client.classify_project_type_batch((sample_pr,))

    assert len(agent.prompts) == 6
    assert recorded_sleeps.count(2.1) == 6
    backoff_waits = [wait for wait in recorded_sleeps if wait != 2.1]
    assert backoff_waits == [2.0, 4.0, 8.0, 16.0, 32.0]


def test_rate_limit_error_honors_suggested_wait(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Em erro 429, aguarda o tempo sugerido pelo Groq mais 1 s de margem."""
    agent = use_fake_agent(
        FakeAgent(
            RuntimeError("Error 429 rate_limit_exceeded. Please try again in 7s."),
            FakeClassification(project_type="library"),
        )
    )

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "library"}
    assert len(agent.prompts) == 2
    assert recorded_sleeps == [2.1, 8.0, 2.1]


# ---------------------------------------------------------------------------
# Desvio de schema — orçamento de tentativas próprio, separado do de rede
# ---------------------------------------------------------------------------


def test_schema_deviation_spends_two_attempts_not_six(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Conteúdo fora do output_schema esgota 2 tentativas, não as 6 da rede.

    O Agno engole o ValidationError e devolve a string crua em `content`;
    a recusa é determinística, então repetir seis vezes só queima cota.
    """
    agent = use_fake_agent(FakeAgent('{"project_type": "monorepo"}'))

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "unknown"}
    assert len(agent.prompts) == 2


def test_schema_deviation_throttles_before_every_attempt(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """O throttle de 2,1 s continua precedendo cada tentativa do caminho de schema."""
    use_fake_agent(FakeAgent("desculpe, não posso classificar isso"))

    llm_client.classify_project_type_batch((sample_pr,))

    assert recorded_sleeps == [2.1, 2.1]


def test_schema_refusal_degrades_instead_of_raising(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Esgotado o orçamento de schema, a classificação vira o sentinela.

    Propagar abortaria a Análise inteira e descartaria tudo o que já foi pago
    em cota do Groq (ADR-0004).
    """
    use_fake_agent(FakeAgent('{"project_type": "monorepo"}'))

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "unknown"}


def test_schema_refusal_logs_the_repository_and_the_refused_content(
    sample_pr, use_fake_agent, recorded_sleeps, caplog
):
    """A recusa é atribuível no log: repositório e conteúdo recusado."""
    use_fake_agent(FakeAgent('{"project_type": "monorepo"}'))

    with caplog.at_level(logging.ERROR, logger=llm_client.__name__):
        llm_client.classify_project_type_batch((sample_pr,))

    assert sample_pr.repo in caplog.text
    assert "monorepo" in caplog.text


def test_nature_and_clarity_refusal_degrades_both_fields(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A chamada unificada degrada os dois campos de uma vez."""
    use_fake_agent(FakeAgent("não posso classificar isso"))

    raw = llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert json.loads(raw) == {"pr_nature": "unknown", "clarity_level": "unknown"}


# ---------------------------------------------------------------------------
# Desvio de schema que chega como exceção — HTTP 400 `json_validate_failed`
# ---------------------------------------------------------------------------


def test_json_validate_failed_uses_the_schema_budget_not_the_network_one(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """O 400 `json_validate_failed` do Groq é desvio de schema, não falha de rede.

    Sem essa classificação, a recusa determinística consumiria 6 tentativas
    com backoff exponencial (~62 s) antes de falhar.
    """
    agent = use_fake_agent(
        FakeAgent(
            RuntimeError(
                "Error code: 400 - {'error': {'code': 'json_validate_failed', "
                "'message': 'Failed to generate JSON.'}}"
            )
        )
    )

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "unknown"}
    assert len(agent.prompts) == 2
    # Só o throttle: nenhum backoff exponencial foi aplicado.
    assert recorded_sleeps == [2.1, 2.1]


def test_transient_json_validate_failed_recovers_on_the_retry(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A retentativa de schema também cobre o 400 transitório."""
    agent = use_fake_agent(
        FakeAgent(
            RuntimeError("Error code: 400 - json_validate_failed"),
            FakeClassification(project_type="library"),
        )
    )

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "library"}
    assert len(agent.prompts) == 2


def test_transient_schema_deviation_recovers_on_the_retry(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A tentativa extra cobre a flutuação genuína do JSON mode."""
    agent = use_fake_agent(
        FakeAgent(
            '{"project": "library"}',
            FakeClassification(project_type="library"),
        )
    )

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "library"}
    assert len(agent.prompts) == 2


def test_network_failures_do_not_consume_the_schema_budget(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Rede e schema têm orçamentos independentes: 5 falhas de rede não impedem
    que uma recusa de schema ainda tenha a sua retentativa."""
    agent = use_fake_agent(
        FakeAgent(
            RuntimeError("connection reset"),
            RuntimeError("connection reset"),
            '{"project_type": "monorepo"}',
            FakeClassification(project_type="cli"),
        )
    )

    raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": "cli"}
    assert len(agent.prompts) == 4


# ---------------------------------------------------------------------------
# Redução de volume de chamadas
# ---------------------------------------------------------------------------


def test_nature_and_clarity_share_a_single_call(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Natureza e clareza continuam vindo de uma única requisição."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    raw = llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert json.loads(raw) == {"pr_nature": "bug_fix", "clarity_level": "good"}
    assert len(agent.prompts) == 1


def test_project_type_batch_sends_one_prompt_for_the_whole_repository(
    sample_pr, sample_pr_same_repo, use_fake_agent, recorded_sleeps
):
    """O batching por repositório sobrevive: N registros, 1 chamada."""
    agent = use_fake_agent(FakeAgent(FakeClassification(project_type="library")))

    llm_client.classify_project_type_batch((sample_pr, sample_pr_same_repo))

    assert len(agent.prompts) == 1
    assert sample_pr.path in agent.prompts[0]
    assert sample_pr_same_repo.body[:50] in agent.prompts[0]


# ---------------------------------------------------------------------------
# O prompt descreve o dado real: um Comentário de Revisão (issue #85, ADR-0002)
# ---------------------------------------------------------------------------


def test_prompt_never_calls_the_content_a_pr_description(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """Nenhum prompt rotula o conteúdo enviado como descrição de PR."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert "pr description" not in agent.prompts[0].lower()


def test_prompt_labels_the_body_as_a_review_comment(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """O corpo enviado é apresentado ao modelo como comentário de revisão."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert "Review comment:" in agent.prompts[0]
    assert sample_pr.body in agent.prompts[0]


def test_clarity_rubric_does_not_punish_brevity(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A rubrica diz explicitamente que concisão não é defeito."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    prompt = agent.prompts[0].lower()
    assert "brevity is" in prompt and "not a defect" in prompt
    # As âncoras por nível substituem a rubrica de descrição de PR.
    assert all(
        level in prompt for level in ("insufficient", "basic", "good", "excellent")
    )


def test_diff_hunk_accompanies_the_body(sample_pr, use_fake_agent, recorded_sleeps):
    """O hunk comentado entra no prompt: sem ele o comentário é injulgável."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert "Diff hunk:" in agent.prompts[0]
    assert sample_pr.diff_hunk in agent.prompts[0]


def test_diff_hunk_is_truncated(sample_pr, use_fake_agent, recorded_sleeps):
    """O hunk é truncado para segurar o custo de token a 30 RPM."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )
    long_hunk = "@" * 5_000

    llm_client.classify_pr_nature_and_clarity_single(
        sample_pr._replace(diff_hunk=long_hunk)
    )

    assert long_hunk not in agent.prompts[0]
    assert "@" * llm_client._MAX_DIFF_HUNK_CHARS in agent.prompts[0]


def test_pr_nature_vocabulary_is_unchanged(sample_pr, use_fake_agent, recorded_sleeps):
    """A parte de natureza sobrevive com o vocabulário controlado intacto."""
    agent = use_fake_agent(
        FakeAgent(FakeClassification(pr_nature="bug_fix", clarity_level="good"))
    )

    llm_client.classify_pr_nature_and_clarity_single(sample_pr)

    assert all(
        value in agent.prompts[0]
        for value in ("bug_fix", "feature", "refactoring", "documentation", "other")
    )


def test_project_type_prompt_still_evaluates_the_repository(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """O prompt de Tipo de Projeto não muda de sujeito: avalia o repositório."""
    agent = use_fake_agent(FakeAgent(FakeClassification(project_type="library")))

    llm_client.classify_project_type_batch((sample_pr,))

    prompt = agent.prompts[0]
    assert f"Repository: {sample_pr.repo}" in prompt
    assert "project type of the repository" in prompt.lower()


# ---------------------------------------------------------------------------
# Atalhos sem chamada ao LLM
# ---------------------------------------------------------------------------


def test_empty_body_skips_the_llm(sample_pr, use_fake_agent, recorded_sleeps):
    """Body vazio devolve o sentinela sem gastar requisição."""
    agent = use_fake_agent(FakeAgent(RuntimeError("não deveria ser chamado")))

    raw = llm_client.classify_pr_nature_and_clarity_single(
        sample_pr._replace(body="   ")
    )

    assert json.loads(raw) == {
        "pr_nature": "other",
        "clarity_level": "insufficient",
    }
    assert agent.prompts == []
    assert recorded_sleeps == []


def test_missing_api_key_fails_before_any_request(sample_pr, monkeypatch):
    """Sem GROQ_API_KEY, a falha é imediata e explícita."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        llm_client.classify_project_type_batch((sample_pr,))


# ---------------------------------------------------------------------------
# Migração para Agno
# ---------------------------------------------------------------------------


def test_agent_is_an_agno_agent_with_groq_backend_and_output_schema():
    """As classificações passam por um Agent do Agno com schema validado."""
    from agno.agent import Agent
    from agno.models.groq import Groq as AgnoGroqModel

    agent = llm_client._build_agent(
        "test-key", "llama-3.1-8b-instant", llm_client.ProjectTypeOutput
    )

    assert isinstance(agent, Agent)
    assert isinstance(agent.model, AgnoGroqModel)
    assert agent.output_schema is llm_client.ProjectTypeOutput
    # O rate limit é responsabilidade de _invoke_with_retry, não do Agno.
    assert agent.retries == 0


def test_no_module_imports_the_groq_sdk_directly():
    """Nenhum módulo do projeto importa o SDK do Groq (só o Agno o faz)."""
    import pathlib
    import re as regex

    root = pathlib.Path(__file__).resolve().parent.parent
    packages = ("core", "services", "ui", "views", "utils", "tests")
    pattern = regex.compile(r"^\s*(from groq\b|import groq\b)", regex.MULTILINE)

    offenders = tuple(
        str(path.relative_to(root))
        for package in packages
        for path in (root / package).rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    ) + tuple(
        str(path.relative_to(root))
        for path in root.glob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    )

    assert offenders == ()
