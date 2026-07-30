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

    with pytest.raises(llm_client.SchemaRefusalError):
        llm_client.classify_project_type_batch((sample_pr,))

    assert len(agent.prompts) == 2


def test_schema_deviation_throttles_before_every_attempt(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """O throttle de 2,1 s continua precedendo cada tentativa do caminho de schema."""
    use_fake_agent(FakeAgent("desculpe, não posso classificar isso"))

    with pytest.raises(llm_client.SchemaRefusalError):
        llm_client.classify_project_type_batch((sample_pr,))

    assert recorded_sleeps == [2.1, 2.1]


def test_schema_refusal_names_the_repository_and_the_refused_content(
    sample_pr, use_fake_agent, recorded_sleeps
):
    """A exceção é atribuível: identifica o repositório e o conteúdo recusado."""
    agent = use_fake_agent(FakeAgent('{"project_type": "monorepo"}'))

    with pytest.raises(llm_client.SchemaRefusalError) as excinfo:
        llm_client.classify_project_type_batch((sample_pr,))

    assert excinfo.value.repo == sample_pr.repo
    assert sample_pr.repo in str(excinfo.value)
    assert "monorepo" in str(excinfo.value)


def test_schema_refusal_is_a_value_error_subclass():
    """Subclasse de ValueError: chamadores antigos seguem capturando."""
    assert issubclass(llm_client.SchemaRefusalError, ValueError)


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
