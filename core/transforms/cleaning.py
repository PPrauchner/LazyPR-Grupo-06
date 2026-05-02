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
from dataclasses import dataclass

# Constantes

MAX_BODY_LENGTH = 6_000  # limite seguro para contexto de LLM
BODY_TRUNCATION_SUFFIX = "\n\n[corpo truncado]"

EMPTY_STRING = ""
UNKNOWN_TITLE = "[sem título]"


@dataclass(frozen=True)
class PRRecord:
    """Representação imutável de um Pull Request bruto."""

    title: str | None
    body: str | None
    author: str | None


@dataclass(frozen=True)
class CleanPRRecord:
    """PRRecord após limpeza — todos os campos são strings válidas."""

    title: str
    body: str
    author: str


def strip_whitespace(text: str) -> str:
    """Remove espaços em branco nas extremidades do texto."""
    return text.strip()


def replace_null(value: str | None, fallback: str) -> str:
    """Retorna o valor original ou o fallback se for None/vazio."""
    if value is None:
        return fallback
    stripped = value.strip()
    return stripped if stripped else fallback


def remove_control_characters(text: str) -> str:
    """
    Remove caracteres de controle Unicode (categoria 'C'), exceto
    quebras de linha (\n) e tabulações (\t), que têm valor semântico.
    """

    def is_allowed(char: str) -> bool:
        if char in ("\n", "\t"):
            return True
        return unicodedata.category(char) != "Cc"

    return "".join(filter(is_allowed, text))


def remove_html_artifacts(text: str) -> str:
    """
    Remove tags HTML e decodifica entidades HTML escapadas comuns
    que aparecem como artefatos em corpos de PR.

    Exemplos:
        "&lt;b&gt;texto&lt;/b&gt;" → "texto"
        "&amp;"                   → "&"
    """

    html_entities = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)

    text = re.sub(r"<[^>]+>", EMPTY_STRING, text)

    return text


def truncate_body(text: str, max_length: int = MAX_BODY_LENGTH) -> str:
    """
    Trunca o corpo do PR se ultrapassar max_length caracteres.
    Adiciona um sufixo para indicar que o conteúdo foi cortado,
    preservando integridade semântica até o ponto de corte.
    """
    if len(text) <= max_length:
        return text

    cutoff = max_length - len(BODY_TRUNCATION_SUFFIX)
    return text[:cutoff] + BODY_TRUNCATION_SUFFIX


def clean_title(raw: str | None) -> str:
    """
    Limpa o título do PR:
         Substitui None/vazio por valor sentinela.
         Remove caracteres de controle.
         Remove artefatos HTML.
         Faz strip de espaços em branco.
    """
    title = replace_null(raw, UNKNOWN_TITLE)

    if title == UNKNOWN_TITLE:
        return title

    title = remove_control_characters(title)
    title = remove_html_artifacts(title)
    title = strip_whitespace(title)

    return title if title else UNKNOWN_TITLE


def clean_body(raw: str | None) -> str:
    """
    Limpa o corpo do PR:
        1. Substitui None por string vazia.
        2. Remove caracteres de controle.
        3. Remove artefatos HTML.
        4. Faz strip de espaços em branco.
        5. Trunca se exceder MAX_BODY_LENGTH.
    """
    body = replace_null(raw, EMPTY_STRING)

    if not body:
        return EMPTY_STRING

    body = remove_control_characters(body)
    body = remove_html_artifacts(body)
    body = strip_whitespace(body)
    body = truncate_body(body)

    return body


def clean_author(raw: str | None) -> str:
    """
    Limpa o autor do PR:
        1. Substitui None/vazio por string vazia.
        2. Remove caracteres de controle.
        3. Faz strip de espaços em branco.
    """
    author = replace_null(raw, EMPTY_STRING)

    if not author:
        return EMPTY_STRING

    author = remove_control_characters(author)
    author = strip_whitespace(author)

    return author


def clean_pr_record(record: PRRecord) -> CleanPRRecord:
    """
    Aplica o pipeline completo de limpeza a um PRRecord bruto.

    Função pura: mesma entrada → sempre a mesma saída.
    Nenhum estado externo é lido ou modificado.
    """
    return CleanPRRecord(
        title=clean_title(record.title),
        body=clean_body(record.body),
        author=clean_author(record.author),
    )
