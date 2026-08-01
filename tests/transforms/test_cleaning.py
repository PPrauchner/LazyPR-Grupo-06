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
        ("", ""),
        ("   ", ""),
        ("\t\n\r", ""),
    ],
)
def test_strip_whitespace(entrada, esperado):
    """Testa remoção de espaçamento em branco (tabs, newlines, spaces)."""
    assert strip_whitespace(entrada) == esperado


@pytest.mark.parametrize(
    "entrada, fallback, esperado",
    [
        (None, "", ""),
        ("   ", "vazio", "vazio"),
        (None, "desconhecido", "desconhecido"),
        ("  valido  ", "vazio", "valido"),
        ("", "fallback", "fallback"),
        ("   \n\t  ", "default", "default"),
    ],
)
def test_replace_null(entrada, fallback, esperado):
    """Testa substituição de None ou espaço em branco por valor padrão."""
    assert replace_null(entrada, fallback) == esperado


def test_remove_control_characters():
    """Testa remoção de caracteres de controle (mantém \n e \t)."""
    # \x00 (Null), \x08 (Backspace) devem sumir. \n e \t devem ficar.
    entrada = "linha1\x00\nlinha2\t\x08"
    esperado = "linha1\nlinha2\t"
    assert remove_control_characters(entrada) == esperado


def test_remove_control_characters_edge_cases():
    """Testa casos extremos de caracteres de controle."""
    # Teste com vários controles
    entrada = "\x01\x02\x03teste\x1f\x7f"
    result = remove_control_characters(entrada)
    # Deve remover os caracteres de controle
    assert "teste" in result
    assert "\x01" not in result


def test_remove_html_artifacts():
    """Testa remoção de entidades HTML e tags."""
    entrada = "&lt;b&gt;negrito&lt;/b&gt; e <div>divisao</div>"
    # unescape transforma &lt;b&gt; em <b>, e re.sub remove as tags
    esperado = "negrito e divisao"
    assert remove_html_artifacts(entrada) == esperado


def test_remove_html_artifacts_multiple_entities():
    """Testa múltiplas entidades HTML."""
    entrada = "&amp; &quot; &apos; &lt; &gt;"
    result = remove_html_artifacts(entrada)
    # Deve conter os caracteres descodificados sem tags
    assert "&amp;" not in result
    assert "&" in result


def test_remove_html_artifacts_nested_tags():
    """Testa tags HTML aninhadas."""
    entrada = "<div><span>texto</span></div>"
    esperado = "texto"
    assert remove_html_artifacts(entrada) == esperado


def test_remove_hidden_comments():
    """Testa remoção de comentários HTML ocultos."""
    entrada = "inicio<!-- comentario oculto\ncom multiplas linhas -->fim"
    esperado = "iniciofim"
    assert remove_hidden_comments(entrada) == esperado


def test_remove_hidden_comments_multiple():
    """Testa múltiplos comentários ocultos."""
    entrada = "texto1<!-- primeiro -->texto2<!-- segundo -->texto3"
    esperado = "texto1texto2texto3"
    assert remove_hidden_comments(entrada) == esperado


def test_remove_hidden_comments_no_comments():
    """Testa quando não há comentários."""
    entrada = "texto sem comentarios"
    assert remove_hidden_comments(entrada) == entrada


def test_normalize_line_ending():
    """Testa normalização de quebras de linha para \n."""
    entrada = "linha1\r\nlinha2\rlinha3"
    esperado = "linha1\nlinha2\nlinha3"
    assert normalize_line_ending(entrada) == esperado


def test_normalize_line_ending_mixed():
    """Testa normalização com diferentes tipos de quebras."""
    entrada = "a\r\nb\rc\nd"
    result = normalize_line_ending(entrada)
    # Todas devem virar \n
    assert result.count("\n") == 3
    assert "\r" not in result


def test_collapse_spaces():
    """Testa colapso de espaços múltiplos em espaço único."""
    entrada = "palavra1    palavra2\t\tpalavra3"
    esperado = "palavra1 palavra2 palavra3"
    assert collapse_spaces(entrada) == esperado


def test_collapse_spaces_multiple_whitespace():
    """Testa colapso com vários tipos de espaçamento."""
    entrada = "a     b\t\tc  \n  d"
    result = collapse_spaces(entrada)
    # Tabs e múltiplos espaços devem virar um espaço
    assert "  " not in result  # Não deve ter dois espaços seguidos
    assert result.count(" ") >= 3  # Deve ter espaços


def test_truncate_text_dentro_do_limite():
    """Testa que texto dentro do limite não é truncado."""
    entrada = "texto curto"
    assert truncate_text(entrada, 50, "[truncado]") == "texto curto"


def test_truncate_text_exatamente_no_limite():
    """Testa texto exatamente no limite."""
    entrada = "12345"
    assert truncate_text(entrada, 5, "[...]") == "12345"


def test_truncate_text_acima_do_limite():
    """Testa truncamento de texto acima do limite."""
    entrada = "12345678901"
    esperado = "12345[...]"
    assert truncate_text(entrada, 10, "[...]") == esperado


def test_truncate_text_suffix_personalizado():
    """Testa truncamento com sufixo customizado."""
    entrada = "abcdefghij"
    esperado = "abcde[TRUNCATED]"
    assert truncate_text(entrada, 10, "[TRUNCATED]") == esperado


def test_truncate_text_muito_curto():
    """Testa comportamento quando limite é muito pequeno."""
    entrada = "abcde"
    # Limite de 3 com sufixo de 3 caracteres - o resultado será ajustado
    result = truncate_text(entrada, 3, "...")
    assert len(result) <= 3 + len("...")


# --- Testes dos Pipelines de Limpeza ---


def test_clean_text_pipeline_completo():
    """Testa pipeline completo de limpeza de texto."""
    entrada = " \r\n <!-- lixo --> <p>ola\x00</p>   mundo \t "
    esperado = "ola mundo"
    assert clean_text(entrada) == esperado


def test_clean_text_pipeline_vazio():
    """Testa pipeline com string vazia."""
    assert clean_text("") == ""


def test_clean_text_pipeline_apenas_whitespace():
    """Testa pipeline com apenas espaçamento."""
    assert clean_text("   \n\t\r  ") == ""


def test_clean_optional_text_none():
    """Testa clean_optional_text com None."""
    assert clean_optional_text(None) is None


def test_clean_optional_text_vazio():
    """Testa clean_optional_text com espaços em branco."""
    assert clean_optional_text("   ") is None


def test_clean_optional_text_valido():
    """Testa clean_optional_text com texto válido."""
    assert clean_optional_text(" texto valido ") == "texto valido"


def test_clean_optional_text_vazio_apos_limpeza():
    """Testa clean_optional_text quando texto fica vazio após limpeza."""
    assert clean_optional_text("   \n\t  ") is None


def test_clean_body_truncation():
    """Testa truncamento de body quando excede limite."""
    # cria uma string que ultrapassa o limite
    entrada = "a" * (MAX_BODY_LENGTH + 100)
    resultado = clean_body(entrada)

    assert len(resultado) == MAX_BODY_LENGTH
    assert resultado.endswith(BODY_TRUNCATION_SUFFIX)


def test_clean_body_dentro_limite():
    """Testa clean_body com texto dentro do limite."""
    entrada = "texto dentro do limite"
    resultado = clean_body(entrada)
    assert resultado == entrada
    assert not resultado.endswith(BODY_TRUNCATION_SUFFIX)


def test_clean_body_com_espacos_extras():
    """Testa clean_body com espaçamento extra."""
    entrada = "  texto   com    espacos  "
    resultado = clean_body(entrada)
    assert resultado == "texto com espacos"


def test_clean_diff_hunk_normalizacao():
    """Testa limpeza de diff_hunk."""
    entrada = " @@ -10,5 +10,8 @@ \n - linha removida\n + linha adicionada"
    resultado = clean_diff_hunk(entrada)
    # Deve conter as partes importantes
    assert "-10" in resultado or "10" in resultado
    assert "linha removida" in resultado or "removida" in resultado


# --- Teste do PRRecord Completo ---


def test_clean_pr_record():
    """Testa limpeza completa de um PRRecord."""
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


def test_clean_pr_record_todos_campos_validos():
    """Testa limpeza com todos campos já validados."""
    registro_limpo_entrada = PRRecord(
        id=123,
        html_url="https://github.com/user/repo/pull/456",
        repo="user/repo",
        path="src/utils.py",
        body="This is a clean body with proper formatting.",
        diff_hunk="@@ -1,10 +1,12 @@",
        author="username",
        author_association="MEMBER",
        commit_id="abc123def456",
        line=15,
        language="Python",
        created_at="2024-01-15",
    )

    resultado = clean_pr_record(registro_limpo_entrada)

    # Todos os campos devem permanecer iguais
    assert resultado == registro_limpo_entrada


def test_clean_pr_record_body_muito_longo():
    """Testa limpeza quando body ultrapassa limite."""
    body_longo = "texto " * 1000  # Cria um body muito longo
    registro = PRRecord(
        id=1,
        html_url="https://github.com/org/repo/pull/1",
        repo="org/repo",
        path="src/main.py",
        body=body_longo,
        diff_hunk="@@ -1,1 +1,1 @@",
        author="user",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=1,
        language="Python",
        created_at=None,
    )

    resultado = clean_pr_record(registro)

    # Body deve estar truncado
    assert len(resultado.body) <= MAX_BODY_LENGTH
    assert resultado.body.endswith(BODY_TRUNCATION_SUFFIX)
