import pytest
from core.models.pr_record import PRRecord
from core.transforms.cleaning import (
    strip_whitespace,
    replace_null,
    remove_control_characters,
    remove_html_artifacts,
    remove_hidden_comments,
    normalize_line_ending,
    collapse_spaces,
    truncate_text,
    clean_text,
    clean_body,
    clean_diff_hunk,
    clean_optional_text,
    clean_pr_record,
    MAX_BODY_LENGTH,
    BODY_TRUNCATION_SUFFIX,
)

# --- Testes das Funções Menores (Unitárias) ---


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("  texto  ", "texto"),
        ("\n\ttexto\n", "texto"),
        ("texto", "texto"),
    ],
)
def test_strip_whitespace(entrada, esperado):
    assert strip_whitespace(entrada) == esperado


@pytest.mark.parametrize(
    "entrada, fallback, esperado",
    [
        (None, "", ""),
        ("   ", "vazio", "vazio"),
        (None, "desconhecido", "desconhecido"),
        ("  valido  ", "vazio", "valido"),
    ],
)
def test_replace_null(entrada, fallback, esperado):
    assert replace_null(entrada, fallback) == esperado


def test_remove_control_characters():
    # \x00 (Null), \x08 (Backspace) devem sumir. \n e \t devem ficar.
    entrada = "linha1\x00\nlinha2\t\x08"
    esperado = "linha1\nlinha2\t"
    assert remove_control_characters(entrada) == esperado


def test_remove_html_artifacts():
    entrada = "&lt;b&gt;negrito&lt;/b&gt; e <div>divisao</div>"
    # unescape transforma &lt;b&gt; em <b>, e re.sub remove as tags
    esperado = "negrito e divisao"
    assert remove_html_artifacts(entrada) == esperado


def test_remove_hidden_comments():
    entrada = "inicio<!-- comentario oculto\ncom multiplas linhas -->fim"
    esperado = "iniciofim"
    assert remove_hidden_comments(entrada) == esperado


def test_normalize_line_ending():
    entrada = "linha1\r\nlinha2\rlinha3"
    esperado = "linha1\nlinha2\nlinha3"
    assert normalize_line_ending(entrada) == esperado


def test_collapse_spaces():
    entrada = "palavra1    palavra2\t\tpalavra3"
    esperado = "palavra1 palavra2 palavra3"
    assert collapse_spaces(entrada) == esperado


# --- Testes de Truncamento ---


def test_truncate_text_dentro_do_limite():
    entrada = "texto curto"
    assert truncate_text(entrada, 50, "[truncado]") == "texto curto"


def test_truncate_text_acima_do_limite():

    entrada = "12345678901"
    esperado = "12345[...]"
    assert truncate_text(entrada, 10, "[...]") == esperado


# --- Testes dos Pipelines de Limpeza ---


def test_clean_text_pipeline_completo():

    entrada = " \r\n <!-- lixo --> <p>ola\x00</p>   mundo \t "
    esperado = "ola mundo"
    assert clean_text(entrada) == esperado


def test_clean_optional_text():
    assert clean_optional_text(None) is None
    assert clean_optional_text("   ") is None
    assert clean_optional_text(" texto valido ") == "texto valido"


def test_clean_body_truncation():
    # cria uma string que ultrapassa o limite
    entrada = "a" * (MAX_BODY_LENGTH + 100)
    resultado = clean_body(entrada)

    assert len(resultado) == MAX_BODY_LENGTH
    assert resultado.endswith(BODY_TRUNCATION_SUFFIX)


# --- Teste do PRRecord Completo ---


def test_clean_pr_record():
    # Cria um registro sujo fictício
    registro_sujo = PRRecord(
        id=1,
        html_url=" https://github.com/org/repo/pull/1 ",
        repo=" org/repo\n",
        path=" src/main.py ",
        body="<!-- template -->\nconteudo   com   espacos",
        diff_hunk=" + codigo\r\n- removido",
        author=" @joao\x00 ",
        author_association=" CONTRIBUTOR ",
        commit_id=" abcdef123456 ",
        line=42,  # Deve permanecer intacto (int)
        language="   ",  # Só espaços, deve virar None
        created_at=None,  # Deve permanecer None
    )

    registro_limpo = clean_pr_record(registro_sujo)

    # Asserts para verificar se os campos foram limpos corretamente
    assert registro_limpo.id == 1
    assert registro_limpo.html_url == "https://github.com/org/repo/pull/1"
    assert registro_limpo.repo == "org/repo"
    assert registro_limpo.path == "src/main.py"
    assert registro_limpo.body == "conteudo com espacos"
    assert registro_limpo.diff_hunk == "+ codigo\n- removido"
    assert registro_limpo.author == "@joao"
    assert registro_limpo.author_association == "CONTRIBUTOR"
    assert registro_limpo.commit_id == "abcdef123456"
    assert registro_limpo.line == 42

    assert registro_limpo.language is None
    assert registro_limpo.created_at is None
