# LazyPR

> Análise funcional e semântica de pull requests do GitHub com classificação via LLMs.

**LazyPR** é uma plataforma de análise de pull requests que combina programação funcional em Python com modelos de linguagem de grande porte (LLMs) para extrair padrões de contribuição em projetos de código aberto. O sistema ingere datasets volumosos de forma *lazy*, classifica semanticamente cada PR e gera dashboards interativos com os resultados enriquecidos.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Módulos e Responsabilidades](#módulos-e-responsabilidades)
- [Pipeline Funcional](#pipeline-funcional)
- [Dataset](#dataset)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Cache e Persistência](#cache-e-persistência)
- [Rate Limiting](#rate-limiting)
- [Stack Tecnológica](#stack-tecnológica)
- [Testes](#testes)
- [Equipe](#equipe)

---

## Visão Geral

Projetos hospedados no GitHub acumulam históricos extensos de pull requests contendo informações valiosas sobre qualidade de contribuição, padrões de revisão e dinâmica de comunidade. Analisar esse volume manualmente é inviável.

O LazyPR resolve esse problema com três pilares:

1. **Ingestão lazy** — datasets com milhões de registros são processados linha a linha via geradores Python, sem pressão sobre a memória RAM. A linguagem de programação de cada PR é inferida automaticamente a partir da extensão do arquivo comentado.

2. **Pipeline funcional** — todas as transformações, filtros e agregações são implementados como funções puras e compostas via funções de ordem superior (`map`, `filter`, `reduce`), garantindo previsibilidade e testabilidade.

3. **Enriquecimento semântico por LLM** — modelos de linguagem (Groq/llama) classificam o tipo de cada repositório, a natureza de cada PR e a qualidade da sua descrição. Classificações são armazenadas em cache persistente indexado por hash SHA-256 para evitar chamadas repetidas.

---

## Funcionalidades

| # | Funcionalidade | História de Usuário |
|---|---|---|
| 01 | Upload e ingestão lazy de datasets CSV/JSON de pull requests | HU 01 |
| 02 | Categorização de repositórios por tipo (biblioteca, framework, app web, CLI) | HU 02 |
| 03 | Classificação da natureza de cada PR (bug fix, feature, refatoração, documentação) | HU 03 |
| 04 | Avaliação da clareza da descrição (insuficiente → excelente) | HU 04 |
| 05 | Dashboard de volume de PRs estratificado por linguagem, tipo e natureza | HU 05 |
| 06 | Visualização da distribuição de tamanho de descrição (caracteres e palavras) | HU 06 |
| 07 | Gráfico de correlação entre clareza, tipo de projeto e linguagem | HU 07 |
| 08 | Sistema de filtros dinâmicos globais aplicados a todas as visualizações | HU 08 |
| 09 | Exportação dos resultados enriquecidos em CSV e JSON | HU 09 |

---

## Arquitetura

O projeto segue o padrão **Functional Core / Imperative Shell**:

```
┌─────────────────────────────────────────────────────┐
│                   Interface (Streamlit)              │
│              ui/ · views/ · sidebar_filters          │
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

- **Funções puras** em `core/` — mesma entrada sempre produz mesma saída, sem efeitos colaterais
- **Efeitos colaterais isolados** (I/O, LLM, rede) em `services/` e `utils/`
- **Imutabilidade** — `NamedTuple` em todo o domínio de dados (`PRRecord`, `AnalysisResult`)
- **Avaliação preguiçosa** via `yield` e `itertools` para suportar datasets volumosos sem carregar em memória
- **Memoização** de classificações LLM com chave SHA-256 do conteúdo, persistida em disco entre sessões
- **Composição** de funções via `pipe()` e `compose()` para construção declarativa de pipelines

---

## Estrutura do Projeto

```
LazyPR-Grupo-06/
│
├── core/                              # Functional Core — funções puras, sem I/O
│   ├── models/
│   │   ├── pr_record.py               # NamedTuple imutável do PR bruto (pré-enriquecimento)
│   │   └── analysis_result.py         # NamedTuple imutável do PR enriquecido (pós-LLM)
│   │
│   ├── pipeline/
│   │   ├── composer.py                # compose() e pipe() — composição de funções
│   │   └── runner.py                  # run_pipeline() — execução lazy configurável por etapa
│   │
│   ├── transforms/
│   │   ├── cleaning.py                # Limpeza de campos textuais (strip, nulos, truncate, HTML)
│   │   ├── filtering.py               # Predicados puros e build_filter() para filtros compostos
│   │   └── normalizing.py             # Padronização de valores + cálculo de char/word count
│   │
│   ├── aggregations/
│   │   ├── counters.py                # Contagens via reduce() por dimensão (retorna dict imutável)
│   │   ├── grouping.py                # group_by() — agrupamentos multidimensionais
│   │   └── metrics.py                 # Estatísticas descritivas e correlation_summary()
│   │
│   └── validators/
│       └── dataset_schema.py          # Validação de schema do CSV na ingestão
│
├── services/                          # Imperative Shell — efeitos colaterais isolados
│   ├── ingestion.py                   # stream_csv(), stream_json() — geradores lazy linha a linha
│   ├── llm_client.py                  # Chamadas Groq/llama com retry, throttle e backoff
│   ├── classifiers.py                 # Orquestra batching por repo, cache e chamadas ao LLM
│   ├── storage.py                     # Persistência de análises indexadas por hash SHA-256
│   └── exporters.py                   # Serialização CSV/JSON + bytes para download Streamlit
│
├── ui/                                # Componentes de interface reutilizáveis
│   ├── components.py                  # metric_card(), data_table(), status_banner(), download_buttons()
│   ├── charts.py                      # bar_chart_by_category(), distribution_chart_from_bins()
│   ├── layout.py                      # Helpers de layout e seções visuais
│   ├── sidebar_filters.py             # Filtros globais → get_active_filters() retorna Predicate
│   └── theme.py                       # Tema visual e inicialização de estilos
│
├── views/                             # Páginas do Streamlit (roteadas por main.py)
│   ├── home.py                        # Página inicial — KPIs, pipeline visual, acesso rápido
│   ├── upload.py                      # Upload e ingestão do dataset com validação de schema
│   ├── overview.py                    # Dashboard de volume e distribuições (HU 05, 06)
│   ├── cleaning_dashboard.py          # Visualização dos dados após etapa de limpeza
│   ├── normalization_dashboard.py     # Visualização dos dados após etapa de normalização
│   ├── correlations_dashboard.py      # Gráfico de correlação multidimensional (HU 07)
│   └── export.py                      # Exportação de resultados enriquecidos (HU 09)
│
├── tests/                             # Testes unitários focados nas funções puras
│   ├── conftest.py                    # Fixtures compartilhadas (PRRecord e AnalysisResult)
│   ├── transforms/
│   │   ├── test_cleaning.py
│   │   ├── test_filtering.py
│   │   └── test_global_filters.py
│   ├── aggregations/
│   │   └── test_grouping.py
│   ├── pipeline/
│   │   ├── test_composer.py
│   │   └── test_runner.py
│   ├── pages/
│   │   └── test_upload.py
│   ├── ui/
│   │   └── test_sidebar_filters.py
│   ├── test_classifiers.py
│   ├── test_hashing.py
│   ├── test_memoization.py
│   ├── test_normalizing.py
│   └── test_storage.py
│
├── utils/                             # Helpers genéricos
│   ├── hashing.py                     # hash_content(), hash_file_stream(), hash_record()
│   └── memoization.py                 # cached_classify() com lookup em disco via storage.py
│
├── main.py                            # Ponto de entrada — configuração e roteamento Streamlit
├── pyproject.toml                     # Dependências e metadados (gerenciado via uv)
├── .env.example                       # Template de variáveis de ambiente
└── README.md
```

---

## Módulos e Responsabilidades

### `core/models/`

| Módulo | Responsabilidade |
|---|---|
| `pr_record.py` | `NamedTuple` imutável representando um PR bruto: `id`, `html_url`, `repo`, `path`, `body`, `diff_hunk`, `author`, `author_association`, `commit_id`, `line`, `language`, `created_at` |
| `analysis_result.py` | `NamedTuple` imutável com todos os campos de `PRRecord` acrescidos das classificações LLM (`project_type`, `pr_nature`, `clarity_level`) e métricas calculadas (`char_count`, `word_count`) |

### `core/pipeline/`

| Módulo | Responsabilidade |
|---|---|
| `composer.py` | `compose(*fns)` e `pipe(*fns)` — combinam etapas de transformação em uma função única sem efeitos colaterais |
| `runner.py` | `run_pipeline(source, config)` — executa as etapas habilitadas (limpeza, normalização, filtragem, classificação) de forma lazy sobre o stream de `PRRecord`, retorna `Generator[AnalysisResult]` |

### `core/transforms/`

| Módulo | Responsabilidade |
|---|---|
| `cleaning.py` | Strip, substituição de nulos, remoção de caracteres de controle, decodificação de entidades HTML, remoção de comentários ocultos, normalização de quebras de linha, truncamento de body/diff para limites do LLM |
| `filtering.py` | Predicados puros por linguagem, tipo de projeto, natureza e clareza; `compose_predicates()` combina por conjunção (AND entre dimensões, OR dentro de cada uma) |
| `normalizing.py` | Padroniza strings de linguagem para forma canônica (`"Python 3"` → `"python"`), normaliza labels LLM para vocabulário controlado, calcula `char_count` e `word_count`; funções anotadas com `@lru_cache` |

### `core/aggregations/`

| Módulo | Responsabilidade |
|---|---|
| `counters.py` | `count_by(records, key_fn)` via `reduce()` — contagem genérica por qualquer dimensão; wrappers `count_by_language()`, `count_by_project_type()`, `count_by_pr_nature()`; retorna `MappingProxyType` imutável |
| `grouping.py` | `group_by(key_fn, records)` — agrupa por função chave via `reduce()`, retorna `dict[chave → tuple]` |
| `metrics.py` | `description_stats()` (min/max/média/mediana de chars e palavras via `reduce()`), `char_distribution()` e `word_distribution()` (frequência por faixas), `correlation_summary()` (proporções de clareza por grupo) |

### `services/`

| Módulo | Responsabilidade |
|---|---|
| `ingestion.py` | `stream_csv()` e `stream_json()` — geradores `yield from map(...)` linha a linha; inferência de linguagem pela extensão do arquivo (`_infer_language_from_path`); extração de `repo` da URL; cálculo de hash SHA-256 durante a leitura |
| `llm_client.py` | Chamadas à API Groq com throttle (2.1s entre requisições para respeitar 30 RPM do plano gratuito), retry com backoff exponencial, extração do tempo de espera de erros 429; `classify_pr_nature_and_clarity_single()` unifica duas classificações em uma chamada |
| `classifiers.py` | Agrupa PRs por repositório via `group_by()`; chave de cache composta por `repo:ids_ordenados`; `cached_classify()` verifica disco antes de chamar LLM; sempre sobrescreve `language` e `created_at` com os valores do `PRRecord` atual após cache hit |
| `storage.py` | `has_cached_analysis()`, `load_results()`, `save_results()` — persistência JSON atômica (escrita em `.tmp` + `os.replace`) indexada por hash SHA-256 |
| `exporters.py` | `export_csv()`, `export_json()` (escrita atômica em disco), `to_download_bytes()` para o botão de download do Streamlit |

### `ui/`

| Módulo | Responsabilidade |
|---|---|
| `components.py` | `metric_card()`, `data_table()`, `status_banner()`, `download_buttons()` — widgets reutilizáveis que recebem dados processados, sem lógica de negócio |
| `charts.py` | `bar_chart_by_category()`, `distribution_chart_from_bins()` — recebem saídas de `aggregations/`, retornam figuras Plotly |
| `sidebar_filters.py` | Renderiza controles de filtro na sidebar; `get_active_filters()` retorna `Predicate` composta pronta para `apply_filters()` |

### `utils/`

| Módulo | Responsabilidade |
|---|---|
| `hashing.py` | `hash_content(text)`, `hash_file_stream(stream)` — SHA-256 determinístico para chaves de cache |
| `memoization.py` | `cached_classify(fn, hash)` — verifica cache em disco via `storage.py` antes de executar a função; `clear_cache()` limpa caches LRU de normalização |

---

## Pipeline Funcional

O pipeline é configurável: cada etapa pode ser ativada ou desativada via `PipelineConfig` sem alterar o código das transformações.

```python
from services.ingestion import stream_csv
from core.pipeline.runner import run_pipeline, PipelineConfig

# Configuração declarativa das etapas
config = PipelineConfig(
    enable_cleaning=True,        # Limpeza de campos textuais
    enable_normalization=True,   # Padronização de linguagem e labels
    enable_filtering=True,       # Filtros globais da sidebar
    enable_classification=True,  # Classificações LLM (project_type, pr_nature, clarity_level)
)

# Ingestão lazy — nenhum registro é carregado em memória completamente
source = stream_csv("dataset.csv")

# Pipeline retorna Generator[AnalysisResult] — avaliação sob demanda
results = run_pipeline(source, config)

# Consumo downstream (lazy)
for result in results:
    print(result.language, result.project_type, result.pr_nature, result.clarity_level)
```

### Etapas do Pipeline

```
stream_csv() → PRRecord
       │
       ▼ [enable_cleaning]
clean_pr_record() → PRRecord (body/diff truncados, HTML removido)
       │
       ▼ [enable_normalization]
normalize_pr_record() → PRRecord (language em forma canônica)
       │
       ▼ [enable_filtering]
apply_filters([predicate]) → PRRecord (apenas os que passam)
       │
       ▼ [enable_classification]
classify_project_type() → AnalysisResult
  ├── 1 chamada LLM por repositório (batching)
  └── 1 chamada LLM por PR (pr_nature + clarity_level combinados)
       │
       ▼
AnalysisResult (completo, pronto para visualização e exportação)
```

---

## Dataset

O dataset padrão utilizado é o **GitHub Public Pull Request Comments**, disponível no Kaggle:

🔗 [kaggle.com/datasets/pelmers/github-public-pull-request-comments](https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments?resource=download)

### Schema do Dataset Kaggle

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `int` | Identificador único do comentário de PR |
| `html_url` | `str` | URL completa do comentário (usada para extrair `owner/repo`) |
| `path` | `str` | Caminho do arquivo comentado (ex: `src/main.go`) |
| `body` | `str` | Texto do comentário de revisão |
| `diff_hunk` | `str` | Trecho do diff associado ao comentário |
| `user` | `str` | Login do autor (mapeado internamente para `author`) |
| `author_association` | `str` | Relação do autor com o repo (`OWNER`, `MEMBER`, `CONTRIBUTOR`, `NONE`) |
| `commit_id` | `str` | Hash SHA do commit referenciado |
| `line` | `int` | Linha do arquivo comentada |
| `created_at` | `str` | Data/hora de criação em formato ISO 8601 |

> **Nota:** O dataset não possui colunas `language` ou `repo`. Ambas são derivadas automaticamente: `repo` é extraído da `html_url` (`owner/name`) e `language` é inferida da extensão do arquivo em `path` (`.py` → `python`, `.go` → `go`, `.ts` → `typescript`, etc.).

### Extensões de Arquivo Suportadas para Inferência de Linguagem

| Extensão | Linguagem | Extensão | Linguagem |
|---|---|---|---|
| `.py` | python | `.rb` | ruby |
| `.js`, `.jsx` | javascript | `.php` | php |
| `.ts`, `.tsx` | typescript | `.dart` | dart |
| `.java` | java | `.kt` | kotlin |
| `.go` | go | `.swift` | swift |
| `.rs` | rust | `.scala` | scala |
| `.c` | c | `.cs` | csharp |
| `.cpp`, `.cc`, `.cxx` | cpp | | |

---

## Instalação

### Pré-requisitos

- Python `>= 3.11`
- [`uv`](https://github.com/astral-sh/uv) para gerenciamento de dependências e ambientes virtuais

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/PPrauchner/LazyPR-Grupo-06.git
cd LazyPR-Grupo-06

# 2. Instale as dependências e crie o ambiente virtual
uv sync

# 3. Ative o ambiente virtual
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows (PowerShell)
```

---

## Configuração

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
# Chave de API do Groq (obrigatório)
# Obtenha gratuitamente em: https://console.groq.com/keys
GROQ_API_KEY=sua_chave_aqui

# Diretório de cache de análises persistidas (padrão: .cache)
CACHE_DIR=.cache

# Limite de caracteres do corpo do PR enviado ao LLM (padrão: 1500)
LAZYPR_MAX_BODY_CHARS=1500
```

### Variáveis de Ambiente

| Variável | Padrão | Obrigatório | Descrição |
|---|---|---|---|
| `GROQ_API_KEY` | — | ✅ | Chave de API do Groq para classificações LLM |
| `CACHE_DIR` | `.cache` | ❌ | Diretório onde análises persistidas são armazenadas |
| `LAZYPR_MAX_BODY_CHARS` | `1500` | ❌ | Limite de caracteres do `body` enviado ao LLM por PR |

> **Groq** oferece acesso gratuito a modelos como `llama-3.1-8b-instant` com limite de 30 requisições por minuto no plano gratuito. O LazyPR respeita esse limite automaticamente com throttle de 2.1s entre chamadas.

---

## Uso

### Iniciar o dashboard

```bash
streamlit run main.py
```

A aplicação abrirá automaticamente em `http://localhost:8501`.

### Fluxo de análise

```
1. Upload       → Carregue o arquivo CSV do dataset na página "Upload"
2. Validação    → O sistema valida o schema e calcula o hash do arquivo
3. Verificação  → Se o arquivo já foi analisado, os resultados são carregados do cache
4. Pipeline     → Limpeza → Normalização → Filtragem → Classificação LLM
5. Exploração   → Navegue por Overview, Limpeza, Normalização e Correlação
6. Filtragem    → Use a sidebar para filtrar por linguagem, tipo, natureza e clareza
7. Exportação   → Baixe os resultados enriquecidos em CSV ou JSON
```

### Páginas disponíveis

| Página | Descrição |
|---|---|
| 🏠 Home | KPIs gerais, visualização do pipeline e atalhos |
| 📂 Upload | Upload do dataset, validação de schema e execução do pipeline |
| 📊 Overview | Gráficos de volume por linguagem, tipo e natureza; distribuições de tamanho |
| 🔥 Correlação | Mapa de calor e padrões entre clareza, tipo de projeto e linguagem |
| 🧹 Limpeza | Visualização dos dados após etapa de limpeza textual |
| ⚙️ Normalização | Visualização dos dados após etapa de normalização de valores |
| 💾 Exportação | Download dos resultados enriquecidos em CSV e JSON |

---

## Cache e Persistência

O LazyPR evita reprocessamento via dois mecanismos de cache:

### Cache de sessão (LRU)

Funções puras com resultados determinísticos (`normalize_language`, `normalize_label`) usam `@functools.lru_cache` para evitar recomputação dentro da mesma sessão.

### Cache persistente em disco

Classificações LLM são armazenadas como arquivos JSON no diretório `CACHE_DIR`, indexados por uma chave SHA-256 composta por `repo:ids_ordenados_do_batch`. Isso garante que:

- Re-uploads do mesmo dataset são instantâneos
- Datasets distintos com repositórios em comum não compartilham cache indevidamente
- Os campos `language` e `created_at` são sempre atualizados com os dados do CSV atual (não ficam congelados no cache)

```
.cache/
├── a1b2c3d4...json    # Classificações do batch golang/go:1,11,21
├── e5f6a7b8...json    # Classificações do batch kubernetes/kubernetes:4,5,6
└── ...
```

---

## Rate Limiting

O plano gratuito do Groq permite **30 requisições por minuto (RPM)**. Para 50 PRs em 15 repositórios distintos, o LazyPR faz:

| Tipo de chamada | Quantidade | Estratégia |
|---|---|---|
| `classify_project_type_batch` | 1 por repositório | Batching: todos os PRs do repo em uma chamada |
| `classify_pr_nature_and_clarity_single` | 1 por PR | Unificado: natureza + clareza em um único JSON |
| **Total** | **~65 chamadas** | Redução de 43% vs. chamadas separadas |

O throttle de **2.1s entre requisições** garante ≤28 RPM, com análise de 50 PRs concluída em ~2 minutos. Em caso de erro 429, o sistema extrai o tempo de espera sugerido pelo Groq da mensagem de erro e aguarda exatamente esse intervalo antes de retentar (máximo de 6 tentativas com backoff exponencial).

---

## Stack Tecnológica

| Camada | Tecnologia | Versão |
|---|---|---|
| Linguagem | Python | ≥ 3.11 |
| Interface gráfica | Streamlit | ≥ 1.57 |
| Visualização | Plotly | ≥ 6.7 |
| Chamadas LLM | Groq SDK | ≥ 1.2 |
| Framework LLM | Agno | ≥ 2.6 |
| Variáveis de ambiente | python-dotenv | ≥ 1.2 |
| Gerenciamento de deps | uv | — |
| Testes | pytest + pytest-cov | ≥ 9.0 |
| Paradigma | Programação Funcional | funções puras · imutabilidade · lazy eval · composição |

---

## Testes

```bash
# Executar todos os testes
uv run pytest tests/

# Com relatório de cobertura
uv run pytest tests/ --cov=core --cov-report=term-missing

# Executar apenas os testes de transformações
uv run pytest tests/transforms/

# Executar um módulo específico
uv run pytest tests/test_normalizing.py -v
```

A suíte de testes cobre as funções puras do `core/` (cleaning, filtering, normalizing, aggregations, pipeline) e as integrações de services (storage, classifiers, hashing, memoization).

---

## Equipe

**Grupo 06 — Residência em Programação III — Escola Politécnica de Pernambuco**

| Membro | GitHub |
|---|---|
| Pietro Mendes Prauchner | [@PPrauchner](https://github.com/PPrauchner) |
| Inaurrara Flores Rozado | [@Inaurrara](https://github.com/Inaurrara) |
| Lorenzo Ficher | [@lorenzoficher](https://github.com/lorenzoficher) |
| Luiz Hermano | [@LuizHerm](https://github.com/LuizHerm) |
| Rafael Lopes | [@rjnlopes03](https://github.com/rjnlopes03) |

> Professores orientadores: [@paulosevero](https://github.com/paulosevero) · [@sequincozes](https://github.com/sequincozes)

---

<p align="center">
  Desenvolvido como projeto acadêmico · Grupo 06 · Escola Politécnica de Pernambuco
</p>
