# Sem estatística de etapa do Pipeline

O LazyPR não expõe ao Analista quantos registros cada Etapa do Pipeline processou.
A ideia foi implementada duas vezes de forma independente — `pipeline_stats` no
`st.session_state` (issue #103) e `PipelineMetrics` em `core/pipeline/runner.py`
(issue #105) — e nenhuma das duas chegou a renderizar um número na tela. Decidimos
remover as duas em vez de completar qualquer uma delas: nenhuma HU pede essa
informação, e o custo de sustentá-la é maior do que parece.

## Considered Options

- **Contagem por Etapa** (quantos entraram, quantos a limpeza tocou, quantos foram
  classificados) — a leitura mais natural do tipo que já existia. Mas exige observar
  a contagem **durante** o consumo do stream, sem materializá-lo, porque
  `run_pipeline` devolve um gerador preguiçoso e a §3 do `CLAUDE.md` proíbe `list()`
  sobre o stream completo. É instrumentação atravessando um caminho que hoje é puro
  e lazy até a fronteira, para alimentar um cartão que ninguém pediu.
- **Só o essencial** (total de registros e tempo de execução, na página de upload) —
  descarta os dois campos problemáticos e não depende da #84. Rejeitada por ser meia
  medida: o total de registros a página de upload já sabe, e tempo de execução
  isolado não responde a nenhuma pergunta do Analista.
- **Remover** (escolhida) — `PipelineMetrics` e o alias `default_pipeline` saem.

## Por que os dois tipos eram ficção

`PipelineMetrics` declarava quatro campos. Verificados contra o caminho real de
execução (`views/upload.py`), três não descreviam nada:

- `records_filtered` é **estruturalmente sempre 0**. O upload nunca passa
  `filter_predicates`, porque o recorte da sidebar é Filtro de Visualização e não
  Etapa (ADR-0003). A própria docstring do campo já admitia isso.
- `total_time_ms` nunca teve quem o medisse — nada em `run_pipeline` cronometra.
- `stages_applied` só poderia reportar uma constante: `views/upload.py` fixa
  `enable_normalization=True, enable_classification=True` em código, e o Analista
  não ativa nem desativa Etapa nenhuma hoje.

`pipeline_stats`, a primeira tentativa, era pior: gravava o **mesmo valor** — o
tamanho do resultado final — nos quatro campos, nos dois caminhos (análise nova e
cache hit). Mesmo renderizada, exibiria quatro cartões com o número idêntico.

Nenhum teste exercitava `PipelineMetrics`: a única menção no repositório era um
import não utilizado em `tests/test_runner.py`.

## A razão de domínio

Estatística de Etapa descreveria a **Análise**, que cobre sempre o dataset inteiro.
Os indicadores que a home exibe respondem ao **Filtro de Visualização**, que é um
recorte sobre a Análise já carregada. As duas grandezas na mesma tela são dois
universos com a mesma aparência, e nada no layout os distinguiria — o Analista leria
"1.200 registros classificados" ao lado de "340 PRs" sem saber por que diferem.

Foi exatamente esse conflito que as duas tentativas não resolveram, e é ele que
torna a página de upload o único lugar onde a informação caberia: lá a Análise
acabou de ser executada e não há recorte competindo por atenção.

## Consequences

`run_pipeline` fica sem nenhuma observabilidade. Um leitor futuro pode ler isso como
esquecimento — é o motivo deste ADR existir. Depurar uma execução longa continua
dependendo de log manual.

A decisão é barata de reverter e há uma condição que a torna mais barata ainda: se a
issue #84 (Regra Geral 05) passar as Etapas como argumento para `run_pipeline`,
`stages_applied` vira derivável de graça, sem instrumentação. Se estatística de Etapa
voltar à mesa, é depois da #84 e na página de upload — não na home, e não sobre a
interface de flags.

`build_pipeline`, `TransformStage` e `EnrichmentStage` **permanecem** em
`core/pipeline/runner.py` mesmo só tendo teste: a #84 vai promovê-los ao caminho de
produção. `enable_aggregation`, cujo corpo é um `pass`, também fica — a #84 reescreve
`PipelineConfig` inteiro, e removê-lo antes disso só cria conflito.

O `CONTEXT.md` não muda: nenhum termo entra ou sai de uso. **Etapa**, **Análise** e
**Filtro de Visualização** continuam como estão, e são justamente eles que sustentam
o raciocínio acima.
