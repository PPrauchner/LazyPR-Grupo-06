# Auditoria do repositório — 27/07/2026

> Relatório de handoff. Insumo para uma sessão de `grill-with-docs` seguida de
> `to-issues`. **Não é um plano aprovado** — os achados estão verificados, mas o
> recorte em issues e as decisões de produto ficam para a grelha.
>
> Fonte da verdade: [`docs/enunciado.md`](./enunciado.md). Domínio:
> [`CONTEXT.md`](../CONTEXT.md). Estado prévio: §15 do [`CLAUDE.md`](../CLAUDE.md).

---

## 0. Leia primeiro: o working tree está sujo

Existe uma **implementação completa e não commitada do seletor de idioma pt/en**
no working tree. Ela foi escrita nesta sessão por engano — o pedido era gerar
issues, não implementar. Nada foi commitado.

```
?? locales/pt.json  locales/en.json     131 chaves, paridade garantida por teste
?? utils/i18n.py                        resolvedor sem Streamlit
?? ui/i18n.py                           t(), tv(), seletor, tradução de agregações
?? tests/test_i18n.py                   29 testes, todos passando
 M main.py ui/{charts,components,layout,sidebar_filters}.py
 M views/{home,overview,upload,export,correlations,cleaning,normalization}_*.py
 M tests/ui/test_sidebar_filters.py
```

**Decida antes de começar:** descartar (`git checkout -- . && rm -rf locales
utils/i18n.py ui/i18n.py tests/test_i18n.py`) e tratar o idioma como issue nova,
ou aproveitar como base de um PR. O §7 deste relatório descreve o desenho, que
vale independentemente do código sobreviver ou não.

Um detalhe importa para o recorte: **a troca de idioma obriga a desacoplar o
roteamento**. Hoje `PAGES` guarda rótulos visíveis (`"📂 Upload"`) que `main.py`
compara por igualdade — traduzir o rótulo quebra a navegação. Qualquer issue de
i18n carrega essa refatoração junto, ou depende de uma issue que a faça antes.

---

## 1. Como este relatório foi produzido

Leitura integral de `ui/`, `views/`, `main.py`, `core/pipeline/runner.py`,
`core/transforms/filtering.py`, `services/storage.py` e dos prompts de
`services/llm_client.py`; execução da suíte de testes; conferência cruzada com
`docs/enunciado.md`.

Todo achado abaixo foi **verificado no código**, com arquivo e linha. Onde o
`CLAUDE.md` §15 já registrava o item, está dito se a auditoria **confirma**,
**refina** ou **corrige** o registro. Onde há dúvida de produto, ela está
isolada no §6 em vez de embutida no achado.

Números de linha referem-se ao `HEAD` (`7468bfe`), não ao working tree sujo.

---

## 2. Achados novos — não estão no §15

### 2.1 🔴 Crítico — o pipeline lê `st.session_state` dentro de `core/` e contamina o cache

**Onde:** `core/pipeline/runner.py:149-158`

```python
if config.enable_filtering:
    from ui.sidebar_filters import get_active_filters   # core/ importando ui/
    predicate = get_active_filters()                    # lê st.session_state
    stream = apply_filters([predicate], stream)
```

Dois problemas encadeados:

**(a) Violação de camada.** `core/` importa `ui/` e lê estado global de sessão.
Regra Específica 02 exige núcleo puro com efeitos isolados; a tabela de camadas
do `CLAUDE.md` §4 proíbe `import streamlit` em `core/`. A proibição é burlada
por indireção — o import é de `ui.sidebar_filters`, que importa Streamlit.

**(b) Consequência de dados, mais grave que a violação.** `enable_filtering`
tem default `True` (`runner.py:75`) e `views/upload.py:158-161` instancia
`PipelineConfig(enable_normalization=True, enable_classification=True)` — sem
desligar filtragem. Logo, **no caminho real de execução**, os filtros marcados
na sidebar no momento do upload recortam o stream *antes* de
`save_results()` (`views/upload.py:170`).

A chave do cache é apenas o hash do arquivo (`hash_file_stream`,
`views/upload.py:124`). Não entra filtro nenhum. Resultado: subir um dataset com
"Python" marcado na sidebar persiste **só os registros Python** sob o hash do
dataset **inteiro**. Limpar os filtros depois não recupera nada — `has_cached_analysis`
acerta, `load_results` devolve o recorte, e a análise fica permanentemente
truncada. Ninguém percebe, porque não há aviso.

Isso também fere a Regra Geral 04, que exige persistir *a análise do dataset* —
não a de um subconjunto acidental.

> **Para a grelha:** filtragem é etapa de pipeline (pré-classificação, economiza
> LLM) ou é filtro de visualização (pós-análise, sobre o cache)? Hoje o código
> faz as duas coisas com o mesmo mecanismo, e é daí que vem o bug. `CONTEXT.md`
> define Etapa como parte do Pipeline, e a HU 08 fala em "filtrar todas as
> visualizações" — o que sugere visualização, não ingestão.

### 2.2 🟠 Alto — o filtro de Tipo de Projeto "Web App" nunca casa

**Onde:** `ui/sidebar_filters.py:44-50` × `core/transforms/filtering.py:43-45`

A sidebar oferece rótulos em *title case*:

```python
PROJECT_TYPES = ("Framework", "Library", "CLI", "Web App", "Other")
```

O predicado compara em minúsculas contra o valor canônico do registro:

```python
allowed = frozenset(map(str.lower, project_types))
return lambda record: (record.project_type or "").lower() in allowed
```

Quatro dos cinco sobrevivem por coincidência (`"Framework"` → `framework` ✓).
**Só `"Web App"` quebra:** vira `"web app"`, e o vocabulário canônico
(`CLAUDE.md` §8) é `web_app`. Filtrar por Web App devolve **zero registros**,
silenciosamente. Fere a HU 08.

Note que `tests/ui/test_sidebar_filters.py:151-173` testa esse filtro com
`("Library",)` — um dos que funcionam por acidente — então o teste passa e o bug
sobrevive.

> **Para a grelha:** a correção óbvia é `PROJECT_TYPES` guardar os valores
> canônicos e a tela exibir rótulo via `format_func`. Isso é exatamente o que a
> issue de i18n precisa (§7). Vale unir as duas ou manter separadas?

### 2.3 🟡 Médio — `render_correlation_dashboard` é definido duas vezes

**Onde:** `views/correlations_dashboard.py:41` e `:48`

A segunda definição sobrescreve a primeira. A primeira é a única que trata
`records` vazio (`st.warning("Nenhum resultado disponível.")`) — e é código
morto. A página em uso não tem guarda: com dataset vazio ela chama
`clarity_by_language({})` e renderiza heatmaps vazios sem explicar por quê.

---

## 3. Confirmações e refinamentos do §15

| §15 | Situação | Evidência |
|---|---|---|
| 1 — Regra Geral 05 não cumprida | **Confirmado** | `runner.py:85` recebe `config`, não etapas; encadeia por `if` (`:138`, `:143`, `:149`, `:161`). `build_pipeline` (`:207`) existe e cumpre a regra, mas não é chamado em produção — só em testes. |
| 2 — suíte não coleta | **Confirmado**, 4 erros | ver §4 |
| 3 — prompts descrevem o dado errado | **Confirmado** | `llm_client.py:367-368`, `:407`, `:329` dizem *"PR description"*; enviam `record.body`, que é Comentário de Revisão |
| 4 — indentação de `main.py` | **Confirmado** | `main.py:75-82`: bloco do `if` com 1 espaço, do `else` com 3, mais trailing whitespace |
| 5 — `.env.example` desatualizado | **Corrigido** | ver abaixo |
| 6 — truncamento com duas fontes | **Refinado: são três** | ver abaixo |
| 7 — `REQUIRED_COLUMNS` duplicado | **Confirmado** | `core/transforms/cleaning.py:301` (frozenset) × `core/validators/dataset_schema.py:5` (tupla) |
| 8 — dois nomes para compor predicados | **Confirmado** | `filtering.py:98` `compose_predicates` e `:116` `build_filter`, que só delega |
| 9 — Agno não usado | **Confirmado** | `agno>=2.6.5` no `pyproject.toml`, zero imports em `.py` |

### §15.5 corrigido — a contagem está errada

O §15 diz "cinco variáveis que o código nunca lê". Medido:

- **`.env.example` declara 6:** `GROQ_API_KEY`, `LAZYPR_MODEL`,
  `LAZYPR_MAX_BODY_CHARS`, `LAZYPR_CACHE_DIR`, `LAZYPR_VERBOSE_LOGGING`,
  `STREAMLIT_MAX_RECORDS`.
- **O código lê 3:** `GROQ_API_KEY`, `LAZYPR_MAX_BODY_CHARS`, `CACHE_DIR`.
- **Nunca lidas: 4** — `LAZYPR_MODEL`, `LAZYPR_CACHE_DIR`,
  `LAZYPR_VERBOSE_LOGGING`, `STREAMLIT_MAX_RECORDS`.
- **Lida mas não documentada: 1** — `CACHE_DIR` (`services/storage.py:49`). O
  `.env.example` promete `LAZYPR_CACHE_DIR`, que ninguém lê: **quem seguir o
  `.env.example` para mudar o diretório de cache não muda nada.**

`STREAMLIT_THEME`, citada no §15 e no §12, **não existe** no `.env.example`.

### §15.6 refinado — o truncamento tem três fontes, não duas

| Fonte | Valor | Onde |
|---|---|---|
| Constante de limpeza | `1_500` fixo | `core/transforms/cleaning.py:39` |
| Variável de ambiente | `LAZYPR_MAX_BODY_CHARS`, default `1500` | `services/llm_client.py:297` — só o prompt **em lote** |
| Literal no prompt | `1000` fixo | `llm_client.py:335`, `:374`, `:414` — os três prompts **por PR** |

Ou seja: a variável de ambiente controla um dos quatro prompts. Nos outros três
o corte é `[:1000]`, hardcoded. Como a limpeza já cortou em 1500, o corte
efetivo por PR é 1000 e `LAZYPR_MAX_BODY_CHARS` é ilusório para eles.

---

## 4. Estado da suíte de testes

`uv run pytest tests/` **aborta na coleta** — nenhum teste roda.

```
ERROR tests/test_classifiers.py          NameError: name 'patch' is not defined
ERROR tests/test_composer.py             basename duplicado com tests/pipeline/test_composer.py
ERROR tests/test_runner.py               basename duplicado com tests/pipeline/test_runner.py
ERROR tests/transforms/test_filtering.py ImportError: has_project_type não existe
                                         em core/transforms/filtering.py
4 errors in 1.85s
```

Os dois basenames duplicados são o mesmo defeito: sem `__init__.py` em
`tests/pipeline/`, o pytest não distingue os módulos.

**Achado adicional:** contornando a coleta e rodando o arquivo isolado,
`tests/ui/test_sidebar_filters.py` tem **8 falhas** que ninguém nunca viu:

- 7× `AttributeError: 'dict' object attribute 'get' is read-only` — os testes
  fazem `mock_st.session_state.get = mock_st.session_state.__getitem__` sobre um
  `dict` puro, o que é impossível em Python. Linhas 110, 138, 164, 190, 215, 246, 289.
- 1× `test_pages_vocabulary_not_empty` — asserta `"Upload" in PAGES`, mas
  `PAGES` guarda `"📂 Upload"`, e `in` sobre tupla é igualdade exata.

Essa última é sintoma do acoplamento do §0: o teste documenta a intenção
("existe uma página de Upload") e o código a quebrou ao embutir o emoji no
identificador.

> **Consequência para o recorte:** enquanto a coleta falha, **nenhuma issue tem
> critério de aceite verificável**. Isso empurra o conserto da suíte para o topo
> da fila, antes de qualquer refatoração.

---

## 5. Clean Code (Regra Geral 09)

- `main.py:75-82` — indentação de 1 e 3 espaços, trailing whitespace.
- `views/home.py:110` — typo em texto de tela: *"utiizando"*.
- `views/export.py:27` — `render_export_page(records=None)` ignora o parâmetro e
  lê `st.session_state["analysis_results"]` direto (`:45`), enquanto todas as
  outras páginas recebem `records` de `main.py`. Contrato inconsistente.
- `core/pipeline/runner.py` — `PipelineMetrics` (`:45`) é declarado e a docstring
  do módulo promete "registrar métricas de execução" (`:16`), mas nada instancia
  a estrutura. `enable_aggregation` (`:77`) só leva a um `pass` (`:194-196`).
  Contratos declarados e inertes.
- `runner.py:38` e `:151` — `apply_filters` importado duas vezes, módulo e função.
- `uv run black .` resolve a indentação; o resto é manual.

> ⚠️ `black` não está instalado no `.venv` (`uv run black` falha com
> *program not found*). Use `uv run --with black black <caminhos>` e **limite os
> caminhos aos arquivos tocados** — rodar na raiz reformata 16 arquivos e afoga o
> diff da issue.

---

## 6. Perguntas para a grelha

Estas não são achados: são bifurcações que uma pessoa precisa resolver antes de
virarem issue.

1. **A unidade de análise mina a HU 04?** `CONTEXT.md` já registra que o dataset
   traz Comentários de Revisão, não descrições de PR — e que a imprecisão vem do
   enunciado. Mas a HU 04 pede avaliar "a clareza da descrição de cada PR", e
   **descrição de PR não existe no dataset**. Corrigir os prompts (§3, item 3)
   para dizer "comentário de revisão" alinha o código ao dado real, mas afasta o
   texto da HU. Manter como está enviesa `clarity_level` para baixo e contamina a
   correlação da HU 07. É a decisão de domínio mais cara do projeto e nenhuma ADR
   a registra.
2. **Filtragem é etapa de pipeline ou de visualização?** (ver 2.1)
3. **Corrigir os prompts invalida o cache.** As classificações persistidas foram
   produzidas pelo prompt errado. Reprocessar custa tempo de LLM a 30 RPM.
   Invalidar tudo, versionar a chave de cache por versão de prompt, ou conviver?
4. **Agno (Dica 05) vale o risco?** É Dica, não Regra — descumprir não é
   não-conformidade. Trocar o SDK mexe no throttle de 2,1 s e no backoff que
   hoje seguram os 30 RPM do plano free. `code-conventions.md` diz que a stack
   não muda sem ADR. Candidata natural a `ready-for-human`.
5. **`build_pipeline` já cumpre a Regra Geral 05 — por que não é usado?** A
   correção pode ser bem menor do que parece: passar as etapas por
   `views/upload.py` em vez de reescrever `run_pipeline`. Vale confirmar se há
   motivo histórico antes de recortar a issue.

---

## 7. O seletor de idioma — desenho de referência

O pedido original era "opção de troca de língua tal qual o Oráculo do Marco I,
inglês e português". O Oráculo (`3° Semestre/RP III/Marco I/grupo-03`) tem uma
implementação madura e documentada em ADR — vale copiar o desenho, não inventar.

**Padrão do Oráculo** (`utils/i18n.py`, `utils/sidebar.py`, ADR-0009):

- `locales/pt.json` + `locales/en.json`, chaves planas (`"nav.home"`), **sem
  biblioteca de i18n** — a ADR-0009 argumenta que Babel/gettext é peso
  desproporcional para ~60 rótulos sem pluralização.
- Idioma no **query param `?lang=`**, nunca em `st.session_state`: sobrevive ao
  refresh e torna o link compartilhável já traduzido.
- Nenhum rótulo traduzido é guardado em estado — `t()` resolve na hora de
  renderizar, senão a tela fica meio traduzida ao trocar de idioma.
- Chave ausente **cai para o idioma padrão**; ausente nos dois, volta crua.
- **Teste de paridade** exige conjuntos de chaves idênticos entre os locales —
  é o que transforma "esqueci de traduzir" em falha de teste.
- Seletor com `on_change` que escreve o param *antes* do rerun (o Oráculo
  registra em comentário que fazer isso no corpo quebrava o `file_uploader`).

**O que muda no LazyPR:**

- **Padrão pt**, não en. O Oráculo escolheu inglês porque já tinha sido avaliado
  e virou portfólio; o Marco II ainda vai à banca.
- **Desacoplar o roteamento é pré-requisito** (§0). `PAGES` precisa guardar chave
  estável (`"upload"`), `main.py` rotear por ela, e o rótulo sair de
  `nav.<chave>`. `page_override` em `views/home.py` e `views/upload.py` também
  guarda rótulo hoje.
- **O vocabulário controlado precisa de rótulo de tela.** `bug_fix`, `web_app`,
  `excellent` aparecem crus nos filtros e nos eixos dos gráficos. Traduzir o
  *rótulo* mantendo o *valor* canônico nos predicados, no cache e no CSV
  exportado — o Oráculo fixa esse limite em ADR-0008 ("a língua não alcança o
  CSV"). Isso encosta direto no achado 2.2.
- Superfície medida: **131 chaves** cobrem `ui/` e `views/` inteiros, incluindo
  títulos de gráfico, hovertemplates do Plotly e mensagens de status.

Ponto de atenção: `ui/charts.py` guarda títulos em dicionários de módulo
(`DISTRIBUTION_CONFIG`, `BIN_CONFIG`, `charts.py:34-63`). Como são avaliados no
import, precisam virar chaves resolvidas em tempo de render — senão congelam no
idioma vigente quando o módulo carregou.

---

## 8. Fatos do repositório

- **Board vazio.** As 75 issues estão fechadas (`gh issue list --state all`).
  Nenhuma aberta. O enunciado (Regras de Organização) exige o quadro populado com
  todas as tarefas mapeadas até a entrega — hoje ele está zerado.
- **Sem CI.** `.github/workflows/` não existe; nada valida conformidade
  automaticamente. Toda verificação é humana ou por agente.
- **Branch de integração:** `dev`, default do repositório. Toda branch parte dela.
- **Labels disponíveis:** área (`data-ingestion`, `logic-core`,
  `ai-classification`, `ai-metrics`, `data-science`, `frontend`, `data-output`) +
  triagem (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
  `wontfix`). A convenção pede **um de cada** por issue
  (`docs/agents/issue-tracker.md`).
- **Regra da fila AFK:** `ready-for-agent` só quando um agente sem contexto
  consegue implementar *e verificar*. Enquanto a suíte não coletar (§4), poucas
  issues satisfazem a segunda metade.
