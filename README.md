# LazyPR

> Análise funcional e semântica de pull requests do GitHub com classificação via LLMs.

**LazyPR** é uma ferramenta de análise de pull requests que combina programação funcional em Python com modelos de linguagem para extrair padrões de contribuição em projetos de código aberto. O sistema ingere datasets volumosos de forma *lazy*, classifica semanticamente cada PR e gera dashboards interativos com os resultados.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Módulos e Responsabilidades](#módulos-e-responsabilidades)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Pipeline Funcional](#pipeline-funcional)
- [Dataset](#dataset)
- [Stack Tecnológica](#stack-tecnológica)
- [Equipe](#equipe)

---

## Visão Geral

Projetos hospedados no GitHub acumulam históricos extensos de pull requests que contêm informações valiosas sobre qualidade de contribuição, padrões de revisão e dinâmica de comunidade. Analisar esse volume manualmente é inviável.

O LazyPR resolve esse problema com três pilares:

1. **Ingestão lazy** — datasets com milhões de registros são processados linha a linha via geradores Python, sem pressão sobre a memória RAM.
2. **Pipeline funcional** — todas as transformações, filtros e agregações são implementados como funções puras e compostas via funções de ordem superior, garantindo previsibilidade e testabilidade.
3. **Enriquecimento semântico por LLM** — modelos de linguagem classificam o tipo de cada repositório, a natureza de cada PR e a qualidade da sua descrição, com cache persistente para evitar chamadas repetidas.

---

## Funcionalidades

| # | Funcionalidade | Issue |
|---|---|---|
| 01 | Upload e ingestão lazy de datasets CSV/JSON | `#01` |
| 02 | Categorização de repositórios por tipo (biblioteca, framework, app web…) | `#02` |
| 03 | Classificação da natureza de cada PR (bug fix, feature, refatoração, docs) | `#03` |
| 04 | Avaliação da clareza da descrição (insuficiente → excelente) | `#04` |
| 05 | Dashboard de volume de PRs estratificado por linguagem, tipo e natureza | `#05` |
| 06 | Visualização da distribuição de tamanho de descrição (chars e palavras) | `#06` |
| 07 | Gráfico de correlação entre clareza, tipo de projeto e linguagem | `#07` |
| 08 | Sistema de filtros dinâmicos globais aplicados a todas as visualizações | `#08` |
| 09 | Exportação dos resultados enriquecidos em CSV e JSON | `#09` |

---

## Arquitetura

O projeto segue o padrão **Functional Core / Imperative Shell**:

```
┌─────────────────────────────────────────────────────┐
│                   Interface (Streamlit)              │
│              ui/ · pages/ · sidebar_filters          │
└───────────────────────┬─────────────────────────────┘
                        │ dados agregados
┌───────────────────────▼─────────────────────────────┐
│              Functional Core  (core/)                │
│   models · pipeline · transforms · aggregations     │
│         funções puras · imutabilidade · sem I/O     │
└──────────┬──────────────────────────────┬───────────┘
           │ PRRecord                     │ AnalysisResult
┌──────────▼──────────┐      ┌────────────▼────────────┐
│  Imperative Shell   │      │   Imperative Shell      │
│  services/ingestion │      │ services/classifiers    │
│  services/storage   │      │ services/llm_client     │
│  services/exporters │      │ utils/memoization       │
└─────────────────────┘      └─────────────────────────┘
         I/O de arquivo              Chamadas LLM
```

**Princípios que guiam a implementação:**

- Funções puras em `core/` — mesma entrada sempre produz mesma saída, sem efeitos colaterais
- Efeitos colaterais (I/O, LLM, rede) isolados em `services/` e `utils/`
- Dados tratados como imutáveis — `NamedTuple` e `dataclass(frozen=True)` em todo o domínio
- Avaliação preguiçosa via `yield` e `itertools` para suportar datasets com milhões de registros
- Memoização automática de classificações LLM com chave SHA-256 do conteúdo

---

## Estrutura do Projeto

```
LAZYPR-GRUPO-06/
│
├── core/                          # Functional Core — funções puras, sem I/O
│   ├── models/
│   │   ├── pr_record.py           # NamedTuple do PR bruto (pré-enriquecimento)
│   │   └── analysis_result.py     # NamedTuple do PR enriquecido (pós-LLM)
│   │
│   ├── pipeline/
│   │   ├── composer.py            # compose() e pipe() — composição de funções
│   │   └── runner.py              # run_pipeline() — execução lazy configurável
│   │
│   ├── transforms/
│   │   ├── cleaning.py            # Limpeza de campos textuais (strip, nulos, truncate)
│   │   ├── filtering.py           # Predicados e build_filter() para filtros compostos
│   │   └── normalizing.py         # Padronização de valores + cálculo de char/word count
│   │
│   └── aggregations/
│       ├── counters.py            # Contagens via reduce() por dimensão
│       ├── grouping.py            # group_by() — agrupamentos multidimensionais
│       └── metrics.py             # Médias, distribuições e correlation_summary()
│
├── services/                      # Imperative Shell — efeitos colaterais isolados
│   ├── ingestion.py               # Geradores lazy para CSV/JSON (stream_csv, stream_json)
│   ├── llm_client.py              # Chamadas Agno/Groq — classify_batch()
│   ├── classifiers.py             # Orquestra batching, cache e chamadas ao LLM
│   ├── storage.py                 # Persistência de análises indexadas por hash
│   └── exporters.py               # Serialização CSV/JSON + bytes para download
│
├── ui/                            # Interface gráfica — componentes Streamlit
│   ├── components.py              # Widgets reutilizáveis (cards, tabelas, banners)
│   ├── charts.py                  # Funções de plotagem (bar, distribution, heatmap)
│   └── sidebar_filters.py         # Controles de filtro → predicados funcionais
│
├── pages/                         # Páginas do Streamlit (roteamento automático)
│   ├── 1_upload.py                # Tela de upload e ingestão do dataset
│   ├── 2_overview.py              # Dashboard de volume e distribuição (Issues 05, 06)
│   ├── 3_correlation.py           # Gráfico de correlação multidimensional (Issue 07)
│   └── 4_export.py                # Exportação de resultados (Issue 09)
│
├── tests/                         # Testes unitários focados nas funções puras
│   ├── test_cleaning.py
│   ├── test_filtering.py
│   ├── test_normalizing.py
│   ├── test_counters.py
│   ├── test_grouping.py
│   ├── test_metrics.py
│   ├── test_composer.py
│   └── test_hashing.py
│
├── utils/                         # Helpers genéricos
│   ├── memoization.py             # Decorador memoize() + cached_classify()
│   └── hashing.py                 # hash_content(), hash_file_stream(), hash_record()
│
├── main.py                        # Ponto de entrada — configuração e init do Streamlit
├── pyproject.toml                 # Dependências e metadados (gerenciado via uv)
└── README.md
```

---

## Módulos e Responsabilidades

### `core/models/`

| Módulo | Responsabilidade |
|---|---|
| `pr_record.py` | `NamedTuple` imutável representando um PR bruto: id, repositório, título, corpo, autor, linguagem, data |
| `analysis_result.py` | `NamedTuple` imutável com os campos de `PRRecord` + classificações LLM: `project_type`, `pr_nature`, `clarity_level`, `char_count`, `word_count` |

### `core/pipeline/`

| Módulo | Responsabilidade |
|---|---|
| `composer.py` | `compose(*fns)` e `pipe(*fns)` — combinam etapas de transformação em uma função única sem efeitos colaterais |
| `runner.py` | `run_pipeline(steps, source)` — executa etapas habilitadas de forma lazy sobre o stream de `PRRecord`, retorna gerador de `AnalysisResult` |

### `core/transforms/`

| Módulo | Responsabilidade |
|---|---|
| `cleaning.py` | Strip, remoção de nulos, truncamento para limite do LLM, remoção de artefatos de encoding — tudo via `map()` e funções puras |
| `filtering.py` | Predicados por linguagem, tipo, natureza e clareza; `build_filter(*predicates)` compõe critérios por conjunção lógica |
| `normalizing.py` | Padroniza strings de linguagem, converte datas, calcula `char_count` e `word_count`, normaliza labels retornados pelo LLM |

### `core/aggregations/`

| Módulo | Responsabilidade |
|---|---|
| `counters.py` | Contagens e distribuições percentuais por dimensão via `reduce()`, produz estruturas imutáveis para os gráficos |
| `grouping.py` | `group_by(key_fn, records)` — agrupa por qualquer combinação de dimensões, retorna mapa imutável de chave → tupla |
| `metrics.py` | Média, mediana, min/max de `char_count`/`word_count`; `correlation_summary()` para a visualização de padrões da Issue 07 |

### `services/`

| Módulo | Responsabilidade |
|---|---|
| `ingestion.py` | `stream_csv()` e `stream_json()` — geradores `yield` linha a linha; calcula hash SHA-256 do arquivo durante a leitura |
| `llm_client.py` | `classify_batch(prompts)` via Agno/Groq; prompts retornam JSON; retry com backoff; chave de API por variável de ambiente |
| `classifiers.py` | Orquestra batching por repositório (Dica 06), consulta cache antes de chamar o LLM, pós-processa JSON via `normalizing.py` |
| `storage.py` | Persiste e carrega análises por hash do dataset; `has_cached_analysis()`, `load_results()`, `save_results()` |
| `exporters.py` | `export_csv()`, `export_json()`, `to_download_bytes()` para o botão de download do Streamlit |

### `ui/`

| Módulo | Responsabilidade |
|---|---|
| `components.py` | `metric_card()`, `data_table()`, `status_banner()`, `download_buttons()` — recebem dados processados, sem lógica de negócio |
| `charts.py` | `bar_chart_by_category()`, `distribution_chart()`, `correlation_heatmap()` — recebem saídas de `aggregations/`, retornam figuras |
| `sidebar_filters.py` | Renderiza controles de filtro; `get_active_filters()` retorna função de filtro composta pronta para o pipeline |

### `utils/`

| Módulo | Responsabilidade |
|---|---|
| `memoization.py` | `memoize(fn)` como decorador; `cached_classify()` com lookup por hash; integra com `storage.py` para persistência cross-sessão |
| `hashing.py` | `hash_content(text)`, `hash_file_stream(stream)`, `hash_record(pr_record)` — SHA-256 determinístico para cache |

---

## Instalação

### Pré-requisitos

- Python `>= 3.11`
- [`uv`](https://github.com/astral-sh/uv) para gerenciamento de dependências

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/SEU-ORG/LAZYPR-GRUPO-06.git
cd LAZYPR-GRUPO-06

# 2. Instale as dependências com uv
uv sync

# 3. Ative o ambiente virtual
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto com as variáveis necessárias:

```env
# Provedor LLM (escolha um)
GROQ_API_KEY=sua_chave_aqui
OPENROUTER_API_KEY=sua_chave_aqui

# Diretório de cache de análises persistidas
LAZYPR_CACHE_DIR=.cache/analyses

# Limite de tokens enviados ao LLM por PR (default: 512)
LAZYPR_MAX_TOKENS=512
```

> As chaves de API para **Groq** e **OpenRouter** podem ser obtidas gratuitamente em seus respectivos portais.

---

## Uso

### Iniciar o dashboard

```bash
streamlit run main.py
```

### Fluxo básico

1. **Upload** — acesse a página *Upload* e carregue o arquivo CSV/JSON do dataset
2. **Processamento** — o pipeline executa as etapas de limpeza, normalização e classificação LLM automaticamente; análises são persistidas em cache para execuções futuras
3. **Exploração** — navegue pelas páginas *Overview* e *Correlação* para visualizar os resultados
4. **Filtragem** — use os controles da sidebar para filtrar por linguagem, tipo de projeto, natureza e clareza
5. **Exportação** — na página *Export*, baixe os resultados enriquecidos em CSV ou JSON

### Executar os testes

```bash
# Todos os testes
uv run pytest tests/

# Com cobertura
uv run pytest tests/ --cov=core --cov-report=term-missing
```

---

## Pipeline Funcional

O pipeline é declarativo: cada etapa é uma função pura passada como argumento para `run_pipeline()`. Etapas podem ser ativadas ou desativadas sem alterar o código das transformações.

```python
from core.pipeline.composer import pipe
from core.pipeline.runner import run_pipeline
from core.transforms.cleaning import clean_record
from core.transforms.normalizing import normalize_record
from core.transforms.filtering import build_filter, is_language
from services.ingestion import stream_csv
from services.classifiers import classify_project_type, classify_pr_nature, classify_clarity

# Predicado de filtro composto
only_python = build_filter(is_language("Python"))

# Composição declarativa das etapas
steps = [
    clean_record,
    normalize_record,
    only_python,           # etapa opcional — remova para processar todas as linguagens
    classify_project_type,
    classify_pr_nature,
    classify_clarity,
]

# Execução lazy sobre o stream — nenhum registro é carregado em memória integralmente
results = run_pipeline(steps, source=stream_csv("dataset.csv"))

# Consumo downstream (gerador — avaliação sob demanda)
for result in results:
    print(result.project_type, result.pr_nature, result.clarity_level)
```

---

## Dataset

O dataset padrão utilizado é o **GitHub Public Pull Request Comments**, disponível no Kaggle:

🔗 [kaggle.com/datasets/pelmers/github-public-pull-request-comments](https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments?resource=download)

O sistema também aceita qualquer arquivo CSV ou JSON Lines com os campos mínimos:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `str` | Identificador único do PR |
| `repo` | `str` | Nome do repositório (`owner/name`) |
| `title` | `str` | Título do pull request |
| `body` | `str` | Descrição do pull request |
| `language` | `str` | Linguagem principal do repositório |
| `created_at` | `str` | Data de criação (ISO 8601) |

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Interface gráfica | Streamlit |
| Chamadas LLM | Agno |
| Providers LLM | Groq · OpenRouter |
| Visualização | Plotly · Altair |
| Gerenciamento de deps | uv |
| Testes | pytest · pytest-cov |
| Paradigma | Programação Funcional (funções puras, imutabilidade, lazy eval) |

---

## Equipe

**Grupo 06 — Disciplina de Programação Funcional**

| Membro | GitHub |
|---|---|
| Pietro Mendes Prauchner | [@PPrauchner](https://github.com/PPrauchner) |
| Inaurrara Flores Rozado | [@Inaurrara](https://github.com/Inaurrara) |
| Lorenzo Ficher | [@lorenzoficher](https://github.com/lorenzoficher) |
| Luiz Hermano | [@LuizHerm](https://github.com/LuizHerm) |
| Rafael Lopes | [@rjnlopes03](https://github.com/rjnlopes03) |

> Professores colaboradores: [@paulosevero](https://github.com/paulosevero) · [@sequincozes](https://github.com/sequincozes)

---

<p align="center">
  Desenvolvido como projeto acadêmico · Grupo 06
</p>