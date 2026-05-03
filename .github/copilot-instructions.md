# Copilot Instructions — Projeto LazyPR (Grupo-06)

---

## 1. Contexto e Identidade

**Objetivo:** Ferramenta de análise semântica de Pull Requests do GitHub utilizando Programação Funcional e LLMs para classificar tipo de projeto, natureza da contribuição e clareza da descrição.

**Tecnologias:** Python 3.12+, Streamlit (UI), Agno + Groq/OpenRouter (LLM), `uv` (gerenciamento de dependências), Black (formatação).

**Público:** Professores da disciplina de Programação Funcional.

**Dataset:** [GitHub Public Pull Request Comments — Kaggle](https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments)

---

## 2. Princípios de Codificação (Mandatórios)

### Paradigma Funcional Estrito
- **Proibido** o uso de `for` ou `while` como mecanismo principal de transformação de dados.
- Use exclusivamente `map()`, `filter()`, `reduce()`, compreensões de lista/geradores e recursão.
- Laços são permitidos **somente** em código de I/O na camada `services/`, mediante justificativa em comentário.

### Imutabilidade
- Modelos de domínio devem ser `NamedTuple` ou `dataclass(frozen=True)`.
- **Proibido** o uso de `.append()`, `.update()`, `.extend()` ou qualquer método que altere estruturas in-place.
- Ao transformar dados, sempre retorne uma nova instância — nunca modifique a original.
- Prefira `tuple` a `list` e `frozenset` a `set` quando a coleção não precisar ser modificada.

### Lazy Evaluation
- Todo processamento de dataset deve usar geradores (`yield`) e expressões geradoras.
- Use `itertools` para encadeamento e combinação de streams sem materialização.
- Nenhuma função deve chamar `list()` sobre o stream completo do dataset.

### Pureza de Funções
- Toda função dentro de `core/` deve ser pura: mesma entrada → mesma saída, sem I/O, sem estado global, sem efeitos colaterais.
- Funções impuras (I/O, rede, LLM, Streamlit) vivem **exclusivamente** em `services/` e `ui/`.

### Memoização
- Use `functools.lru_cache` para funções puras chamadas repetidamente com mesmas entradas.
- Para classificações LLM, use `utils/memoization.py` com chave SHA-256 do conteúdo via `utils/hashing.py`.
- O cache deve ser persistido em disco via `services/storage.py` para sobreviver entre sessões.

---

## 3. Schema de Dados Real (Dataset do Kaggle)

O dataset contém comentários de PRs, **não** os PRs completos. O schema real de cada registro é:

```python
# Campos presentes no dataset
{
    "id":                 int,    # identificador do comentário
    "html_url":           str,    # ex: "https://github.com/golang/go/pull/23805#..."
    "path":               str,    # arquivo comentado, ex: "src/math/rand/rand.go"
    "body":               str,    # texto do comentário
    "diff_hunk":          str,    # trecho do diff associado ao comentário
    "user":               str,    # login do autor
    "author_association": str,    # "CONTRIBUTOR", "MEMBER", "OWNER", etc.
    "commit_id":          str,
    "line":               int,
}
```

**Campos ausentes no dataset** que devem ser derivados:
- `repo` — extraído da `html_url` (ex: `"golang/go"`)
- `language` — inferido pelo LLM a partir de `path` e `diff_hunk`
- `title` e `created_at` — ausentes; tratar como `None` ou omitir do modelo

---

## 4. Modelos de Domínio

### `core/models/pr_record.py` — registro bruto
```python
class PRRecord(NamedTuple):
    id:                 int
    html_url:           str
    repo:               str        # extraído da html_url em services/ingestion.py
    path:               str
    body:               str
    diff_hunk:          str
    author:             str        # campo "user" no dataset
    author_association: str
    commit_id:          str
    line:               int
    language:           str | None # inferido via LLM ou None
    created_at:         str | None # ausente no dataset
```

### `core/models/analysis_result.py` — registro enriquecido
```python
class AnalysisResult(NamedTuple):
    # Todos os campos de PRRecord, mais:
    project_type:  str        # "library" | "web_app" | "framework" | "cli" | "other"
    pr_nature:     str        # "bug_fix" | "feature" | "refactoring" | "documentation" | "other"
    clarity_level: str        # "insufficient" | "basic" | "good" | "excellent"
    char_count:    int        # len(body)
    word_count:    int        # len(body.split())
```

---

## 5. Arquitetura de Pastas e Responsabilidades

```
LAZYPR-GRUPO-06/
├── core/                     # Functional Core — APENAS funções puras
│   ├── models/
│   │   ├── pr_record.py      # NamedTuple do PR bruto
│   │   └── analysis_result.py# NamedTuple do PR enriquecido
│   ├── pipeline/
│   │   ├── composer.py       # compose() e pipe() — composição de funções
│   │   └── runner.py         # run_pipeline(steps, source) — execução lazy
│   ├── transforms/
│   │   ├── cleaning.py       # Limpeza de campos textuais (strip, nulos, truncate)
│   │   ├── filtering.py      # Predicados e build_filter() para filtros compostos
│   │   └── normalizing.py    # Padronização de valores + char_count + word_count
│   └── aggregations/
│       ├── counters.py       # Contagens via reduce() por dimensão
│       ├── grouping.py       # group_by() — agrupamentos multidimensionais
│       └── metrics.py        # Médias, distribuições, correlation_summary()
│
├── services/                 # Imperative Shell — efeitos colaterais isolados
│   ├── ingestion.py          # Geradores lazy CSV/JSON + extração de repo da URL
│   ├── llm_client.py         # Chamadas Agno/Groq — classify_batch()
│   ├── classifiers.py        # Batching por repo + orquestração de cache + LLM
│   ├── storage.py            # Persistência JSON em .cache/ via atomic writes
│   └── exporters.py          # Serialização CSV/JSON + bytes para st.download_button
│
├── ui/
│   ├── components.py         # Widgets reutilizáveis do Streamlit
│   ├── charts.py             # Funções de plotagem (recebem dados agregados)
│   └── sidebar_filters.py    # Controles → get_active_filters() → predicado composto
│
├── pages/
│   ├── 1_upload.py
│   ├── 2_overview.py
│   ├── 3_correlation.py
│   └── 4_export.py
│
├── tests/                    # Testes unitários — foco nas funções puras de core/
├── utils/
│   ├── memoization.py        # memoize() + cached_classify()
│   └── hashing.py            # hash_content(), hash_file_stream(), hash_record()
│
├── main.py
├── pyproject.toml
└── README.md
```

---

## 6. Regras por Camada

### `core/` — Functional Core
- ✅ `map()`, `filter()`, `reduce()`, `functools`, `itertools`
- ✅ Funções que recebem e retornam `NamedTuple`
- ✅ `lru_cache` em funções puras chamadas repetidamente
- ❌ `import requests`, `import streamlit`, `open()`, `print()`
- ❌ Qualquer acesso a variável global ou estado externo

### `services/` — Imperative Shell
- ✅ I/O de arquivo, requisições HTTP, chamadas ao Agno/Groq
- ✅ `try/except` para tratamento de falhas de rede e parsing
- ✅ Atomic writes para persistência de cache (escrever em `.tmp`, renomear)
- ✅ Leitura de variáveis de ambiente (`os.getenv`)
- ❌ Lógica de agregação, contagem ou cálculo de métricas
- ❌ Lógica de plotagem ou componentes Streamlit

### `ui/` — Interface
- ✅ Componentes Streamlit, `st.session_state`
- ✅ Chamar funções de `core/aggregations/` para obter dados agregados
- ✅ Chamar funções de `ui/charts.py` passando dados prontos
- ❌ Transformações de dados, chamadas LLM ou I/O de arquivo direto

---

## 7. Convenções de Cache e Persistência

- **Diretório:** configurável via `LAZYPR_CACHE_DIR` no `.env` (padrão: `.cache/analyses/`)
- **Formato:** JSON — um arquivo por repositório, nomeado pelo hash SHA-256 de `repo + description`
- **Escrita:** sempre atomic — escrever em arquivo `.tmp` e renomear atomicamente
- **Chave de hash para classificação LLM:** SHA-256 de `repo + body_truncated` (para `pr_nature` e `clarity`) ou `repo + description` (para `project_type`)
- **Batching:** PRs do mesmo repositório devem ser agrupados em uma única chamada LLM para `project_type`

---

## 8. Vocabulário Controlado das Classificações LLM

Os prompts devem instruir o modelo a retornar **estritamente** um dos valores abaixo. Qualquer outro valor deve ser normalizado por `core/transforms/normalizing.py`.

| Classificação | Valores válidos |
|---|---|
| `project_type` | `"library"`, `"web_app"`, `"framework"`, `"cli"`, `"other"` |
| `pr_nature` | `"bug_fix"`, `"feature"`, `"refactoring"`, `"documentation"`, `"other"` |
| `clarity_level` | `"insufficient"`, `"basic"`, `"good"`, `"excellent"` |

O prompt deve sempre incluir a lista de valores válidos e exigir resposta em JSON puro, sem texto livre:
```json
{"project_type": "library"}
```

---

## 9. Estilo e Documentação

- **Type Hints** obrigatórios em todas as assinaturas de funções
- **Docstrings** no padrão Google (Args, Returns, Raises)
- **Tratamento de erros** com `try/except` apenas em `services/` e `ui/`
- **Formatação** com Black (configurado no `pyproject.toml`)
- Funções curtas — máximo recomendado de 20 linhas; se maior, extraia responsabilidades
- Nomes descritivos — sem abreviações, sem nomes genéricos como `data`, `result`, `temp`

---

## 10. Exemplos de Prompts para o Copilot

```
"Crie um gerador em services/ingestion.py que leia o CSV linha a linha,
extraia o campo 'repo' da html_url e retorne um PRRecord por iteração."

"Gere uma função pura em core/transforms/filtering.py para construir
um predicado composto via build_filter(*predicates) usando conjunção lógica."

"Implemente classify_project_type() em services/classifiers.py que agrupe
PRs por repositório, consulte o cache antes de chamar o LLM e normalize
a resposta via normalizing.py."

"Crie a função group_by(key_fn, records) em core/aggregations/grouping.py
como função de ordem superior pura, retornando um dict imutável."

"Implemente atomic write em services/storage.py: escrever em arquivo .tmp
e renomear para evitar corrupção em caso de interrupção."

"Gere um heatmap de correlação em ui/charts.py que receba um dict de grupos
(saída de grouping.py) e retorne uma figura Plotly sem acessar dados brutos."
```