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

### Memorização
- Use `functools.lru_cache` para funções puras chamadas repetidamente com mesmas entradas.
- Para classificações LLM, use `utils/memorization.py` com chave SHA-256 do conteúdo via `utils/hashing.py`.
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
│   ├── memorization.py        # memoize() + cached_classify()
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

## 9. Páginas do Streamlit — Responsabilidades e Fluxo de Dados

Cada página em `pages/` deve seguir o padrão: **ler do `st.session_state` → aplicar filtros → chamar aggregations → chamar charts → renderizar**. Nenhuma página deve acessar o dataset bruto diretamente.

### `pages/1_upload.py` — Upload e Ingestão (Issue 01)
- Renderiza `st.file_uploader` para CSV ou JSON
- Ao receber arquivo, chama `services/ingestion.py` para obter o hash e o stream de `PRRecord`
- Verifica via `services/storage.py` se análise já existe para aquele hash
- Se existir: carrega resultados do cache e salva em `st.session_state["results"]`
- Se não existir: executa `core/pipeline/runner.py` com todas as etapas habilitadas, exibe barra de progresso, persiste via `storage.py` e salva em `st.session_state["results"]`
- Ao final, redireciona o usuário para `2_overview.py`

### `pages/2_overview.py` — Dashboard de Volume e Distribuição (Issues 05 e 06)
- Lê `st.session_state["results"]` e `st.session_state["active_filter"]`
- Aplica o filtro composto retornado por `ui/sidebar_filters.get_active_filters()`
- Chama `core/aggregations/counters.count_by_language()`, `count_by_project_type()`, `count_by_pr_nature()` para alimentar os gráficos de barras
- Chama `core/aggregations/metrics.description_stats()` para alimentar os gráficos de distribuição de `char_count` e `word_count`
- Renderiza via `ui/charts.bar_chart_by_category()` e `ui/charts.distribution_chart()`
- Exibe `ui/components.metric_card()` com KPIs de alto nível (total de PRs, linguagens únicas, distribuição de clareza)

### `pages/3_correlation.py` — Correlação Multidimensional (Issue 07)
- Lê `st.session_state["results"]` com filtros aplicados
- Chama `core/aggregations/grouping.group_by()` com chave composta `(project_type, language)`
- Chama `core/aggregations/metrics.correlation_summary()` sobre os grupos
- Renderiza via `ui/charts.correlation_heatmap()` a relação entre clareza, tipo de projeto e linguagem
- Permite ao analista identificar padrões de contribuição entre dimensões

### `pages/4_export.py` — Exportação (Issue 09)
- Lê `st.session_state["results"]` com filtros aplicados
- Exibe prévia dos dados via `ui/components.data_table()`
- Chama `services/exporters.to_download_bytes(results, fmt="csv")` e `fmt="json"`
- Renderiza dois `st.download_button` — um para CSV e um para JSON
- O schema exportado deve incluir todos os campos de `AnalysisResult` com nomes canônicos

---

## 10. Visualizações — Contrato de Interface entre `aggregations/` e `charts/`

As funções de `ui/charts.py` nunca recebem registros brutos. Elas recebem **exclusivamente estruturas já agregadas** produzidas por `core/aggregations/`. O Copilot deve respeitar esse contrato ao gerar código de plotagem.

| Função em `charts.py` | Recebe (de `aggregations/`) | Renderiza |
|---|---|---|
| `bar_chart_by_category(counts, x, y, color)` | `dict[str, int]` de `counters.py` | Gráfico de barras agrupadas por dimensão |
| `distribution_chart(stats, dimension)` | `dict` com min/max/média/mediana de `metrics.py` | Histograma ou boxplot de `char_count`/`word_count` |
| `correlation_heatmap(matrix)` | `dict[tuple, float]` de `metrics.correlation_summary()` | Heatmap de correlação entre clareza e contexto |

**Biblioteca de plotagem:** Plotly Express (`plotly.express`). Altair é alternativa aceitável. Nunca usar `matplotlib` diretamente em páginas Streamlit.

---

## 11. Sistema de Filtros Dinâmicos (Issue 08)

O sistema de filtros deve funcionar sem reler o arquivo ou reexecutar as classificações LLM.

### Fluxo completo:
```
Usuário altera filtro na sidebar
        ↓
ui/sidebar_filters.get_active_filters()
        ↓ retorna função de filtro composta
core/transforms/filtering.build_filter(*predicates)
        ↓ aplica filter() sobre st.session_state["results"]
Dados filtrados passados para aggregations/ e depois para charts/
```

### Regras de implementação:
- Cada critério de filtro (linguagem, tipo, natureza, clareza) gera um predicado independente via `lambda`
- `build_filter(*predicates)` compõe todos os predicados ativos por conjunção (`all(p(r) for p in predicates)`)
- O filtro é aplicado sobre `st.session_state["results"]` a cada rerender — nunca salva subset filtrado no session_state
- Filtros devem ser sincronizados com `st.session_state` para persistir entre navegação de páginas
- Nenhum filtro modifica `st.session_state["results"]` — apenas produz uma view filtrada

---

## 12. Exportação — Schema e Formato (Issue 09)

### CSV
- Cabeçalho com nomes canônicos em `snake_case`
- Ordem das colunas: campos de identificação → campos textuais → métricas derivadas → classificações LLM

```
id, repo, path, author, author_association, body, diff_hunk, language,
char_count, word_count, project_type, pr_nature, clarity_level
```

### JSON
- Formato JSON Lines (um objeto por linha) para compatibilidade com pipelines externos
- Cada linha é um `AnalysisResult` serializado como objeto JSON plano (sem aninhamento)

### Implementação em `services/exporters.py`:
- `export_csv(results, filepath)` — escreve em disco
- `export_json(results, filepath)` — escreve em disco
- `to_download_bytes(results, fmt)` — retorna `bytes` para `st.download_button` sem escrita em disco
- Todas as funções devem aceitar um `Iterable[AnalysisResult]` — nunca assumir que é uma lista

---

## 13. Testes

### Estratégia geral
- Testar **apenas** funções do `core/` e `utils/` — são puras e não precisam de mocks
- Funções de `services/` devem ser testadas com fixtures e mocks de I/O/LLM
- Nunca testar lógica de UI diretamente

### Estrutura de `tests/`

```
tests/
├── test_cleaning.py        # Casos: strip, nulos, truncate, encoding inválido
├── test_filtering.py       # Casos: predicados individuais, build_filter composto
├── test_normalizing.py     # Casos: normalização de linguagem, char_count, word_count, labels LLM
├── test_counters.py        # Casos: contagem por dimensão, distribuição percentual
├── test_grouping.py        # Casos: group_by com chave simples e composta
├── test_metrics.py         # Casos: média, mediana, correlation_summary
├── test_composer.py        # Casos: compose(), pipe(), identidade, ordem de aplicação
└── test_hashing.py         # Casos: determinismo, colisões, hash de stream
```

### Padrões obrigatórios:
- Usar `pytest` com fixtures em `conftest.py` para `PRRecord` e `AnalysisResult` de exemplo
- Mockar chamadas LLM com `unittest.mock.patch` em testes de `classifiers.py`
- Nomear testes como `test_<função>_<cenário>` — ex: `test_build_filter_with_multiple_predicates`
- Cobrir casos de borda: body vazio, linguagem `None`, label LLM inválido retornado

### Exemplo de fixture:
```python
# tests/conftest.py
import pytest
from core.models.pr_record import PRRecord

@pytest.fixture
def sample_pr():
    return PRRecord(
        id=178204099,
        html_url="https://github.com/golang/go/pull/23805#discussion_r178204099",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="While `true` and `false` is not specified...",
        diff_hunk="@@ -210,6 +210,11 @@ again:",
        author="mewmew",
        author_association="CONTRIBUTOR",
        commit_id="f200cd75ab7c3fd16e046fa3cbc76565c4063cec",
        line=213,
        language=None,
        created_at=None,
    )
```

---

## 14. Configuração do Ambiente

### `.env` (nunca versionar — adicionar ao `.gitignore`)
```env
# Provider LLM — escolha um
GROQ_API_KEY=sua_chave_aqui
OPENROUTER_API_KEY=sua_chave_aqui

# Diretório de cache de análises persistidas
LAZYPR_CACHE_DIR=.cache/analyses

# Limite de caracteres do body enviado ao LLM (evita estouro de contexto)
LAZYPR_MAX_BODY_CHARS=1500

# Modelo a usar via Groq (padrão recomendado)
LAZYPR_MODEL=llama3-8b-8192
```

### `.gitignore` — entradas obrigatórias
```
.env
.cache/
.venv/
__pycache__/
*.pyc
*.tmp
```

### `pyproject.toml` — dependências essenciais
```toml
[project]
name = "lazypr"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "streamlit",
    "agno",
    "plotly",
    "python-dotenv",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "black",
    "ruff",
]
```

### Inicialização do projeto com `uv`
```bash
uv sync              # instala dependências
uv sync --extra dev  # instala dependências de desenvolvimento
streamlit run main.py
```

---

## 15. Estilo e Documentação

- **Type Hints** obrigatórios em todas as assinaturas de funções
- **Docstrings** no padrão Google (Args, Returns, Raises)
- **Tratamento de erros** com `try/except` apenas em `services/` e `ui/`
- **Formatação** com Black (configurado no `pyproject.toml`)
- Funções curtas — máximo recomendado de 20 linhas; se maior, extraia responsabilidades
- Nomes descritivos — sem abreviações, sem nomes genéricos como `data`, `result`, `temp`

---

## 16. Exemplos de Prompts para o Copilot

```
# Ingestão
"Crie um gerador em services/ingestion.py que leia o CSV linha a linha,
extraia o campo 'repo' da html_url com urllib.parse e retorne um PRRecord por iteração."

# Filtros
"Gere uma função pura em core/transforms/filtering.py para construir
um predicado composto via build_filter(*predicates) usando conjunção lógica com all()."

# Classificação
"Implemente classify_project_type() em services/classifiers.py que agrupe
PRs por repositório com group_by(), consulte o cache antes de chamar o LLM
e normalize a resposta via normalizing.py."

# Agregação
"Crie a função group_by(key_fn, records) em core/aggregations/grouping.py
como função de ordem superior pura, retornando um dict[str, tuple[AnalysisResult, ...]]."

# Cache
"Implemente atomic write em services/storage.py: escrever em arquivo .tmp
e usar os.replace() para renomear atomicamente, evitando corrupção."

# Visualização
"Gere bar_chart_by_category() em ui/charts.py que receba dict[str, int]
(saída de counters.py) e retorne uma figura plotly.express.bar sem acessar dados brutos."

# Filtros dinâmicos
"Implemente get_active_filters() em ui/sidebar_filters.py que leia os widgets
do st.sidebar e retorne uma função de filtro composta por build_filter()."

# Exportação
"Implemente to_download_bytes(results, fmt) em services/exporters.py que aceite
Iterable[AnalysisResult] e retorne bytes serializados em CSV ou JSON sem escrita em disco."

# Testes
"Crie test_build_filter_with_multiple_predicates em tests/test_filtering.py
usando a fixture sample_pr do conftest.py, sem nenhum mock."

# Correlação
"Implemente correlation_summary(groups) em core/aggregations/metrics.py que receba
dict[tuple, tuple[AnalysisResult, ...]] e retorne dict[tuple, float] com
a proporção de cada clarity_level por grupo, usando reduce()."
```