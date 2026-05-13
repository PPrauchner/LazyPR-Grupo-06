"""
core/transforms/cleaning.py
============================
Fornece funções puras de limpeza dos campos brutos de um `PRRecord`,
preparando os dados para normalização e envio ao pipeline de classificação.

Responsabilidades:
    - Remover espaços em branco desnecessários (strip) de campos textuais
      como título e corpo do PR.
    - Substituir valores nulos ou ausentes por representações canônicas
      (string vazia, valor sentinela) sem lançar exceções silenciosas.
    - Truncar corpos de PR excessivamente longos para o limite máximo
      aceitável pelo contexto dos LLMs, preservando a estrutura semântica.
    - Remover caracteres de controle, encoding inválido e artefatos de
      formatação (ex: markdown bruto, tags HTML escapadas).
    - Todas as funções devem ser puras: dado o mesmo `PRRecord` de entrada,
      a saída deve ser sempre idêntica e nenhum estado externo é modificado.

Não deve:
    - Normalizar valores (responsabilidade de normalizing.py).
    - Filtrar registros (responsabilidade de filtering.py).
    - Realizar I/O de qualquer natureza.

Relacionado a:
    - Issue 03 (limpeza do texto antes do envio ao LLM)
    - Regra Geral 06 (dados pré-processados antes da camada LLM)
    - Regra Funcional 02 (funções puras, sem efeitos colaterais)
    - Regra Funcional 07 (map(), filter(), funções lambda)
    - Conceito-Chave 05 (funções puras para limpeza)
"""

import re
import unicodedata
from html import unescape

from core.models.pr_record import PRRecord
from typing import Iterable as _Iterable

MAX_BODY_LENGTH = 1_500
MAX_DIFF_HUNK_LENGTH = 2_000

BODY_TRUNCATION_SUFFIX = "\n\n[body truncated]"
DIFF_TRUNCATION_SUFFIX = "\n\n[diff truncated]"

EMPTY_STRING = ""


def strip_whitespace(text: str) -> str:
    """
    Remove espaços em branco das extremidades de um texto.

    Args:
        text: Texto de entrada já convertido para string válida.

    Returns:
        O mesmo texto sem espaços, quebras de linha ou tabulações nas
        extremidades.
    """
    return text.strip()


def replace_null(value: str | None, fallback: str = EMPTY_STRING) -> str:
    """
    Substitui valores ausentes ou vazios por um fallback canônico.

    Args:
        value: Valor textual original, podendo ser None.
        fallback: Valor usado quando value for None ou string vazia.

    Returns:
        O texto original sem espaços nas extremidades, ou fallback quando
        não houver conteúdo textual útil.
    """
    stripped = value.strip() if value is not None else EMPTY_STRING
    return stripped if stripped else fallback


def remove_control_characters(text: str) -> str:
    """
    Remove caracteres de controle Unicode de um texto.

    Quebras de linha e tabulações são preservadas porque podem carregar
    significado em comentários, trechos de código e diff_hunks.

    Args:
        text: Texto de entrada.

    Returns:
        Texto sem caracteres de controle indesejados.
    """
    return "".join(
        filter(
            lambda char: char in ("\n", "\t") or unicodedata.category(char) != "Cc",
            text,
        )
    )


def remove_html_artifacts(text: str) -> str:
    """
    Decodifica entidades HTML e remove tags HTML simples.

    Esta função trata artefatos comuns vindos de comentários exportados,
    como &amp;, &lt;, &gt; e tags HTML embutidas.

    Args:
        text: Texto possivelmente contendo entidades ou tags HTML.

    Returns:
        Texto com entidades HTML decodificadas e tags removidas.
    """
    return re.sub(r"<[^>]+>", EMPTY_STRING, unescape(text))


def truncate_text(text: str, max_length: int, suffix: str) -> str:
    """
    Trunca um texto quando ele ultrapassa o tamanho máximo permitido.

    O sufixo de truncamento é incluído dentro do limite final para deixar
    explícito que o conteúdo foi reduzido antes de seguir no pipeline.

    Args:
        text: Texto que pode ser truncado.
        max_length: Quantidade máxima de caracteres permitida.
        suffix: Marcador textual adicionado ao final do texto truncado.

    Returns:
        Texto original quando estiver dentro do limite, ou texto truncado
        com o marcador de truncamento.
    """
    if len(text) <= max_length:
        return text

    cutoff = max(max_length - len(suffix), 0)
    return text[:cutoff] + suffix[: max_length - cutoff]


def clean_text(value: str | None, fallback: str = EMPTY_STRING) -> str:
    """
    Aplica a sequência padrão de limpeza textual.

    A função centraliza o tratamento comum usado por campos como html_url,
    repo, path, author e commit_id. Ela é pura e determinística.

    Args:
        value: Texto original, podendo ser None.
        fallback: Valor usado quando o texto original estiver ausente.

    Returns:
        Texto limpo, sem nulos, caracteres de controle, artefatos HTML e
        espaços desnecessários nas extremidades.
    """
    return strip_whitespace(
        remove_html_artifacts(
            remove_control_characters(
                replace_null(value, fallback),
            )
        )
    )


def clean_body(body: str | None) -> str:
    """
    Limpa e trunca o corpo do comentário do pull request.

    O campo body é usado nas etapas de classificação e cálculo de métricas,
    então precisa chegar ao restante do pipeline em formato textual seguro.

    Args:
        body: Corpo bruto do comentário, podendo ser None.

    Returns:
        Corpo limpo e limitado por MAX_BODY_LENGTH.
    """
    return truncate_text(
        clean_text(body),
        MAX_BODY_LENGTH,
        BODY_TRUNCATION_SUFFIX,
    )


def clean_diff_hunk(diff_hunk: str | None) -> str:
    """
    Limpa e trunca o trecho de diff associado ao comentário.

    O diff_hunk pode ser usado como contexto adicional para inferência de
    linguagem e natureza da contribuição, mas deve ser limitado para evitar
    excesso de contexto nas etapas posteriores.

    Args:
        diff_hunk: Trecho bruto do diff, podendo ser None.

    Returns:
        Diff limpo e limitado por MAX_DIFF_HUNK_LENGTH.
    """
    return truncate_text(
        clean_text(diff_hunk),
        MAX_DIFF_HUNK_LENGTH,
        DIFF_TRUNCATION_SUFFIX,
    )


def clean_optional_text(value: str | None) -> str | None:
    """
    Limpa um campo textual opcional preservando ausência como None.

    Essa função é útil para campos que podem realmente não existir no dataset,
    como language e created_at, evitando transformar ausência semântica em
    string vazia.

    Args:
        value: Texto opcional de entrada.

    Returns:
        Texto limpo quando houver conteúdo, ou None quando o campo estiver
        ausente ou vazio.
    """
    cleaned = clean_text(value)
    return cleaned if cleaned else None


def clean_pr_record(record: PRRecord) -> PRRecord:
    """
    Aplica a limpeza completa a um PRRecord bruto.

    A função não altera o registro original. Em vez disso, cria uma nova
    instância de PRRecord com os campos textuais limpos, respeitando a
    imutabilidade exigida pela arquitetura funcional do projeto.

    Args:
        record: Registro bruto produzido pela etapa de ingestão.

    Returns:
        Nova instância de PRRecord contendo os campos textuais limpos e os
        campos não textuais preservados.
    """
    return PRRecord(
        id=record.id,
        html_url=clean_text(record.html_url),
        repo=clean_text(record.repo),
        path=clean_text(record.path),
        body=clean_body(record.body),
        diff_hunk=clean_diff_hunk(record.diff_hunk),
        author=clean_text(record.author),
        author_association=clean_text(record.author_association),
        commit_id=clean_text(record.commit_id),
        line=record.line,
        language=clean_optional_text(record.language),
        created_at=clean_optional_text(record.created_at),
    )

REQUIRED_COLUMNS: frozenset[str] = frozenset({
    "id", "html_url", "path", "body", "diff_hunk", "user", 
    "author_association", "commit_id", "line",
})

def get_missing_columns(header: _Iterable[str]) -> tuple[str, ...]:
    """
    Verifica quais colunas obrigatórias estão ausentes no cabeçalho.

    A função utiliza teoria de conjuntos para comparar as colunas fornecidas
    com o conjunto restrito de colunas exigidas (`REQUIRED_COLUMNS`). É uma
    função pura que higieniza os espaços em branco do cabeçalho de entrada 
    sem causar mutação nos dados originais.

    Args:
        header: Iterável contendo os nomes das colunas lidos do arquivo.

    Returns:
        Tupla ordenada alfabeticamente contendo os nomes das colunas 
        obrigatórias que não foram encontradas. Retorna uma tupla vazia 
        se o schema estiver perfeitamente válido.
    """
    header_set = frozenset(col.strip() for col in header)
    missing = REQUIRED_COLUMNS.difference(header_set)
    return tuple(sorted(missing))