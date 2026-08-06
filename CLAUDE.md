# CLAUDE.md — LazyPR (Grupo 06)

> Fonte de verdade para agentes trabalhando neste repositório.
> Modelo de domínio em [`CONTEXT.md`](./CONTEXT.md); decisões e porquês em
> [`docs/adr/`](./docs/adr/); convenções de código em
> [`.claude/rules/`](./.claude/rules/).

---

## 1. Identidade

**LazyPR** analisa pull requests do GitHub combinando **programação funcional
estrita** em Python com **classificação semântica via LLM**. Ingere datasets
volumosos de forma *lazy*, classifica cada PR e apresenta dashboards Streamlit.

- **Contexto:** projeto acadêmico — Residência em Programação III, Escola
  Politécnica de Pernambuco. O paradigma funcional é **requisito avaliado**, não
  preferência de estilo.
- **Repositório:** `PPrauchner/LazyPR-Grupo-06`
- **Dataset:** [GitHub Public Pull Request Comments (Kaggle)](https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments)

---

## 2. Stack e comandos

| Item | Valor |
|---|---|
| Linguagem | Python **3.12** |
| Gerenciador | **uv** (`uv.lock` — nunca usar pip/poetry) |
| Interface | Streamlit |
| Visualização | Plotly |
| LLM | Agno + backend Groq (`llama-3.1-8b-instant`) |
| Formatação | Black, `line-length = 88` |
| Testes | pytest + pytest-cov |

```bash
uv sync                                        # instalar dependências
streamlit run main.py                          # rodar o app (localhost:8501)
uv run pytest tests/                           # testes  ⚠️ ver §15
uv run pytest tests/ --cov=core --cov-report=term-missing
uv run black .                                 # formatar
```

Não há CI (`.github/workflows/` não existe) nem etapa de build — o app roda
direto do fonte.

### Branches

`dev` é a branch de integração e o **default do repositório**: todo PR tem `dev`
como base, e toda branch nova parte dela.

```bash
git checkout dev && git pull
git checkout -b <tipo>/<descricao-curta>
```

`main` guarda o histórico estável e só recebe merge a partir de `dev`. Não abrir
PR contra `main` nem partir branch dela.

---

## 3. Princípios de codificação (mandatórios)

### Paradigma funcional estrito

- **Proibido** `for`/`while` como mecanismo de transformação de dados.
- Use `map()`, `filter()`, `reduce()`, geradores e composição.
- Laços são tolerados **apenas** em I/O dentro de `services/`, com comentário
  justificando.

### Imutabilidade

- Modelos de domínio são `NamedTuple`.
- **Proibido** `.append()`, `.update()`, `.extend()` ou qualquer mutação in-place.
- Transformar = retornar nova instância (`record._replace(...)`, `data + (item,)`).
- Prefira `tuple` a `list` e `frozenset` a `set`.
- Agregações retornam `MappingProxyType` (dict imutável).

### Lazy evaluation

- Processamento de dataset via `yield` e expressões geradoras.
- `itertools` para encadear streams sem materializar.
- **Nunca** `list()` sobre o stream completo do dataset.

### Pureza

- Toda função em `core/` é pura: mesma entrada → mesma saída, sem I/O, sem
  estado global, sem efeito colateral.
- Impureza (I/O, rede, LLM, Streamlit) vive **exclusivamente** em `services/`,
  `ui/` e `views/`.

### ⚠️ Conflito com `karpathy-principles.md`

O `.claude/rules/karpathy-principles.md` manda "Simplicidade Primeiro". **Neste
projeto o paradigma funcional vence quando os dois conflitam** — ele é requisito
avaliado da disciplina. Um `for` mais legível **não** é substituto aceitável de
um `reduce()`. Nos demais eixos (mudanças cirúrgicas, nada especulativo,
execução orientada a metas) o Karpathy continua valendo integralmente.

---

## 4. Arquitetura — Functional Core / Imperative Shell

```
views/ + ui/          Streamlit — renderização e estado de sessão
      │ dados agregados
core/                 funções puras · imutabilidade · sem I/O
      │ PRRecord → AnalysisResult
services/ + utils/    I/O de arquivo · chamadas LLM · cache em disco
```

### Regras por camada

| Camada | ✅ Pode | ❌ Não pode |
|---|---|---|
| `core/` | `map`/`filter`/`reduce`, `functools`, `itertools`, `lru_cache`, `NamedTuple` | `import streamlit`, `open()`, `print()`, rede, estado global |
| `services/` | I/O de arquivo, HTTP, Groq, `try/except`, `os.getenv`, atomic writes | agregação, contagem, métricas, plotagem |
| `ui/` | componentes Streamlit, `st.session_state`, Plotly | transformar dados, chamar LLM, I/O direto |
| `views/` | orquestrar: ler sessão → filtrar → agregar → plotar | lógica de negócio própria |

Fluxo obrigatório de toda página em `views/`:
**ler `st.session_state` → aplicar filtros → chamar `aggregations/` → chamar
`ui/charts.py` → renderizar.** Nenhuma página acessa o dataset bruto.

---

## 5. Estrutura de pastas

```
core/                          # Functional Core — apenas funções puras
├── models/
│   ├── pr_record.py           # PRRecord (NamedTuple) — PR bruto
│   └── analysis_result.py     # AnalysisResult (NamedTuple) — PR enriquecido
├── pipeline/
│   ├── composer.py            # compose(), pipe(), identity()
│   ├── runner.py              # run_pipeline(steps, source) — única função centralizadora
│   └── stages.py              # catálogo de Etapas: clean_records(), normalize_records(), enrich_without_classification(), filter_results()
├── transforms/
│   ├── cleaning.py            # clean_pr_record(), clean_body(), truncate_text(), ...
│   ├── filtering.py           # by_language(), by_clarity_level(), compose_predicates(), apply_filters()
│   └── normalizing.py         # normalize_language(), normalize_label(), calculate_char_count()
├── aggregations/
│   ├── counters.py            # count_by() + count_by_language/project_type/pr_nature/clarity
│   ├── grouping.py            # group_by(), cross_count_language_clarity()
│   ├── metrics.py             # description_stats(), char_distribution(), correlation_summary()
│   └── correlations.py        # build_correlation_matrix(), clarity_by_language/project_type/pr_nature
└── validators/
    └── dataset_schema.py      # validate_dataset_columns()

services/                      # Imperative Shell
├── ingestion.py               # stream_csv(), stream_json(), ingest_dataset(), read_header_lazily()
├── llm_client.py              # classify_project_type_batch(), classify_pr_nature_and_clarity_single()
├── classifiers.py             # classify_project_type(), classify_pr_nature(), classify_clarity()
├── storage.py                 # has_cached_analysis(), load_results(), save_results()
└── exporters.py               # export_csv(), export_json(), to_download_bytes(), enrich_records()

ui/                            # Componentes reutilizáveis
├── components.py              # metric_card(), data_table(), status_banner(), download_buttons()
├── charts.py                  # bar_chart_by_category(), distribution_chart(), correlation_heatmap()
├── layout.py                  # render_section_title(), render_dataset_card()
├── sidebar_filters.py         # get_active_filters(), render_sidebar()
└── theme.py                   # initialize_theme(), apply_theme(), set_theme()

views/                         # Páginas (roteadas por main.py, sem prefixo numérico)
├── home.py · upload.py · overview.py · export.py
└── cleaning_dashboard.py · normalization_dashboard.py · correlations_dashboard.py

utils/
├── hashing.py                 # hash_content(), hash_file_stream(), hash_record()
└── memoization.py             # cached_classify(), clear_cache()

tests/                         # pytest — conftest.py com fixtures de PRRecord/AnalysisResult
main.py                        # entrypoint Streamlit — só configuração e roteamento
```

---

## 6. Modelos de domínio

```python
class PRRecord(NamedTuple):        # core/models/pr_record.py
    id: int
    html_url: str
    repo: str                      # derivado da html_url
    path: str
    body: str
    diff_hunk: str
    author: str                    # coluna "user" no dataset
    author_association: str
    commit_id: str
    line: int
    language: str | None           # derivado da extensão de `path`
    created_at: str | None
```

`AnalysisResult` (`core/models/analysis_result.py`) tem **todos** os campos de
`PRRecord` mais:

| Campo | Tipo | Origem |
|---|---|---|
| `project_type` | `ProjectType` | LLM, 1 chamada por repositório |
| `pr_nature` | `PRNature` | LLM |
| `clarity_level` | `ClarityLevel` | LLM |
| `char_count` | `int` | `len(body)` |
| `word_count` | `int` | `len(body.split())` |

---

## 7. Dataset — campos derivados

O dataset Kaggle traz **comentários de PR**, não PRs completos. Colunas
originais: `id`, `html_url`, `path`, `body`, `diff_hunk`, `user`,
`author_association`, `commit_id`, `line`, `created_at`.

Dois campos **não existem** no dataset e são derivados em
`services/ingestion.py`:

- **`repo`** — extraído da `html_url` (`owner/name`).
- **`language`** — inferida da **extensão do arquivo** em `path` via
  `_EXTENSION_TO_LANGUAGE`. **Não é inferida por LLM** (documentação antiga
  dizia isso; está errado).

---

## 8. Vocabulário controlado das classificações

Os prompts exigem JSON puro com **exatamente** um destes valores. Qualquer
outro é normalizado por `core/transforms/normalizing.py::normalize_label()`.

| Classificação | Valores válidos |
|---|---|
| `project_type` | `library` · `web_app` · `framework` · `cli` · `other` · `unknown` |
| `pr_nature` | `bug_fix` · `feature` · `refactoring` · `documentation` · `other` · `unknown` |
| `clarity_level` | `insufficient` · `basic` · `good` · `excellent` · `unknown` |

`unknown` é o sentinela para falha de LLM ou classificação ausente — declarado
como `UNKNOWN_PROJECT_TYPE`, `UNKNOWN_PR_NATURE`, `UNKNOWN_CLARITY_LEVEL`.

---

## 9. Pipeline

`run_pipeline(steps, source)` compõe de forma lazy as Etapas recebidas **por
argumento**, retornando um gerador. As Etapas vêm do catálogo em
`core/pipeline/stages.py` (mais `classify_project_type`, que é impura e mora em
`services/`); quem monta a tupla é o usuário, pelos checkboxes de
`views/upload.py`. Etapa desmarcada não entra na tupla — não há flag no runner:

```
stream_csv() → PRRecord
   ↓ clean_records                 body/diff truncados, HTML removido
   ↓ normalize_records             language canônica
   ↓ classify_project_type         → AnalysisResult   (ou, sem LLM,
     enrich_without_classification   → AnalysisResult com `unknown`)
   ↓ filter_results(predicates)    recorte opcional, só quando o chamador
                                   passa a Etapa (ADR-0003)
```

---

## 10. Cache e persistência

Dois níveis:

- **Sessão:** `@lru_cache` em funções puras determinísticas
  (`normalize_language`, `normalize_label`).
- **Disco:** classificações LLM em JSON no diretório `CACHE_DIR` (padrão
  `.cache`), indexadas por SHA-256 de `repo:ids_ordenados_do_batch`.

Regras invioláveis:

- Escrita **atômica** — gravar em `.tmp` e `os.replace()`.
- A chave de cache inclui os IDs do batch: datasets distintos que compartilham
  repositórios **não** colidem.
- Após cache hit, `language` e `created_at` são **sempre** sobrescritos com os
  valores do `PRRecord` atual — não podem congelar no cache.
- O disco tem **dois espaços de nomes** sob `CACHE_DIR`, em subdiretórios
  separados e com versão de esquema própria: `analysis/` (a Análise do dataset,
  `CACHE_SCHEMA_VERSION`) e `repo-classification/` (as classificações de LLM por
  repositório, `REPO_CLASSIFICATION_SCHEMA_VERSION`). Versionar um **não**
  invalida o outro — ver
  [ADR-0003](./docs/adr/0003-filtragem-como-recorte-de-visualizacao.md).

### Rate limit do Groq

Plano gratuito: **30 RPM**. `services/llm_client.py` aplica throttle de **2,1 s**
entre requisições (≤28 RPM), backoff exponencial com até 6 tentativas, e em erro
429 extrai da mensagem o tempo de espera sugerido. Batching por repositório
(`classify_project_type_batch`) e unificação de duas classificações numa chamada
(`classify_pr_nature_and_clarity_single`) reduzem o volume em ~43%.

---

## 11. Contrato entre `aggregations/` e `charts/`

`ui/charts.py` **nunca** recebe registros brutos — só estruturas já agregadas.

| Função em `charts.py` | Recebe de |
|---|---|
| `bar_chart_by_category()` | `counters.py` — `Mapping[str, int]` |
| `distribution_chart()` / `distribution_chart_from_bins()` | `metrics.py` |
| `correlation_heatmap()` | `correlations.build_correlation_matrix()` |

Biblioteca de plotagem: **Plotly**. Nunca `matplotlib` em página Streamlit.

---

## 12. Variáveis de ambiente

Apenas **três** são lidas pelo código:

| Variável | Padrão | Onde |
|---|---|---|
| `GROQ_API_KEY` | — (obrigatória) | `services/llm_client.py` |
| `LAZYPR_MAX_BODY_CHARS` | `1500` | `services/llm_client.py` |
| `CACHE_DIR` | `.cache` | `services/storage.py` |

O `.env.example` documenta outras cinco (`LAZYPR_MODEL`, `LAZYPR_CACHE_DIR`,
`LAZYPR_VERBOSE_LOGGING`, `STREAMLIT_MAX_RECORDS`, `STREAMLIT_THEME`) que o
código **nunca lê** — ver §15.

---

## 13. Testes

- Testar as funções puras de `core/` e `utils/` — sem mocks, elas não precisam.
- `services/` com fixtures e `unittest.mock.patch` para I/O e LLM.
- Não testar UI diretamente.
- Nomear `test_<função>_<cenário>`.
- Cobrir bordas: `body` vazio, `language=None`, label inválido vindo do LLM.
- Fixtures compartilhadas em `tests/conftest.py`.

---

## 14. Estilo e documentação

- **Type hints obrigatórios** em toda assinatura — sintaxe 3.10+ (`X | None`,
  `list[int]`). Evitar `Any`.
- **Docstrings Google** (Args/Returns/Raises) em módulo, classe e função pública.
- Código e identificadores em **inglês**; documentação em **português**.
- `try/except` só em `services/`, `ui/` e `views/`.
- Constantes `UPPER_SNAKE_CASE`, funções `snake_case`, classes `PascalCase`.

Detalhamento em [`.claude/rules/python-conventions.md`](./.claude/rules/python-conventions.md)
e [`.claude/rules/code-conventions.md`](./.claude/rules/code-conventions.md).

---

## 15. Estado de conformidade

Levantado em 27/07/2026. **O enunciado da disciplina é a fonte da verdade** — ver
"Regra zero" em [`.claude/rules/code-conventions.md`](./.claude/rules/code-conventions.md).
Os itens do primeiro grupo violam regra avaliada e **devem ser corrigidos**; não
são dívida a aceitar.

### Não-conformidades com o enunciado

1. ~~**Regra Geral 05 — pipeline sem funções de ordem superior**~~ — resolvida
   (issue #84): `run_pipeline(steps, source)` recebe as Etapas por argumento e
   as compõe, e `views/upload.py` oferece cada Etapa ao usuário como checkbox —
   a desmarcada não entra na tupla. `PipelineConfig`, `PipelineMetrics`,
   `build_pipeline` e `enable_aggregation` foram removidos.

### Defeitos

2. **A suíte de testes não coleta.** `uv run pytest tests/` falha com 4 erros:
   - `tests/test_classifiers.py` — `NameError: name 'patch' is not defined`
   - `tests/test_composer.py` × `tests/pipeline/test_composer.py` — basename
     duplicado sem `__init__.py` (idem `test_runner.py`)
   - `tests/transforms/test_filtering.py` — importa `has_project_type`, que não
     existe em `core/transforms/filtering.py`

3. **Prompts descrevem o dado errado.** `services/llm_client.py:367-369` e `:407`
   instruem o modelo a avaliar *"GitHub Pull Request descriptions"*, mas enviam
   `record.body` — o corpo de um Comentário de Revisão (ver
   [`CONTEXT.md`](./CONTEXT.md)). Comentários de revisão competentes são julgados
   como descrições de PR incompletas, o que enviesa `clarity_level` para baixo e
   contamina a correlação da HU 07.

4. **`main.py` com indentação inconsistente** (linhas 75-82): o bloco do `if` usa
   1 espaço, o do `else` usa 3, e há trailing whitespace — Regra Geral 09 (Clean
   Code). `uv run black .` resolve.

### Inconsistências (não violam regra)

5. **`.env.example` desatualizado** — documenta cinco variáveis que o código nunca
   lê (§12) e nomeia o cache de `LAZYPR_CACHE_DIR`, enquanto `services/storage.py`
   lê `CACHE_DIR`.

6. **Limite de truncamento com duas fontes** — `core/transforms/cleaning.py` fixa
   `MAX_BODY_LENGTH = 1_500` em código e `services/llm_client.py` lê
   `LAZYPR_MAX_BODY_CHARS`. Mudar a variável de ambiente não afeta a limpeza.

7. **`REQUIRED_COLUMNS` duplicado** em `core/transforms/cleaning.py` e
   `core/validators/dataset_schema.py`.

8. **Dois nomes para compor predicados** — `compose_predicates()` e
   `build_filter()` coexistem em `core/transforms/filtering.py`.

9. ~~**Dica 05 não atendida**~~ — resolvida: `services/llm_client.py` chama o LLM
   por um `Agent` do Agno com backend Groq e `output_schema` Pydantic
   ([ADR-0004](./docs/adr/0004-migracao-das-chamadas-de-llm-para-agno.md)). O
   throttle de 2,1 s e o backoff continuam em `_invoke_with_retry`, fora do Agno.
   `groq` permanece declarado porque o Agno depende dele internamente.

### Conforme

Regras Gerais 01-04 e 06-08; Regras Específicas 01-06. `core/` não tem nenhuma
mutação in-place e seus únicos `for` estão dentro de comprehensions. As
materializações de stream em `services/classifiers.py:179` e `views/upload.py:168`
são inerentes a agrupar por repositório (Dica 06) e a manter estado no Streamlit
— a primeira está justificada em comentário, como a Regra Específica 01 pede.

---

## 16. Onde procurar o quê

| Pergunta | Arquivo |
|---|---|
| O que este termo de domínio significa? | [`CONTEXT.md`](./CONTEXT.md) |
| Por que decidimos assim? | [`docs/adr/`](./docs/adr/) |
| Como escrever Python aqui? | [`.claude/rules/python-conventions.md`](./.claude/rules/python-conventions.md) |
| Como me comportar como agente? | [`.claude/rules/karpathy-principles.md`](./.claude/rules/karpathy-principles.md) — com a ressalva da §3 |
| Como instalar e usar? | [`README.md`](./README.md) |

---

## Agent skills

### Issue tracker

GitHub Issues de `PPrauchner/LazyPR-Grupo-06`, espelhadas no board GitHub Projects
nº 2 ("LazyPR"); movimento de coluna via `.claude/scripts/board-move.sh`. Exigido
pelo enunciado — não migrar. Ver [`docs/agents/issue-tracker.md`](./docs/agents/issue-tracker.md).

### Triage labels

Os cinco papéis canônicos em inglês — `needs-triage`, `needs-info`,
`ready-for-agent`, `ready-for-human`, `wontfix` — todos existentes no repo, usados
junto dos labels de área (`logic-core`, `frontend`, …). Ver
[`docs/agents/triage-labels.md`](./docs/agents/triage-labels.md).

### Domain docs

Single-context: um `CONTEXT.md` e um `docs/adr/` na raiz, sem `CONTEXT-MAP.md`.
Ver [`docs/agents/domain.md`](./docs/agents/domain.md).
