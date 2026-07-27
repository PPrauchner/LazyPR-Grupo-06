# LazyPR

Ferramenta de análise do histórico de contribuições em projetos open source do
GitHub. Ingere um dataset público de pull requests, enriquece cada registro com
classificações semânticas produzidas por LLM e apresenta a distribuição dos
resultados ao analista.

## Language

### A unidade de análise

**Comentário de Revisão**:
Observação deixada por um revisor sobre uma linha específica de um arquivo. É a
unidade realmente ingerida — cada registro do dataset é um destes.
_Avoid_: registro, linha, entrada

**PR**:
Termo do enunciado para cada registro analisado. Na prática denota um Comentário
de Revisão: a imprecisão vem do enunciado, que exige o dataset
`github-public-pull-request-comments`. É a palavra usada em rótulos de interface,
relatórios e nas Histórias de Usuário.
_Avoid_: pull request por extenso, contribuição

> ⚠️ Consequência: `PRRecord` é nome herdado — a estrutura representa um
> Comentário de Revisão. As métricas que dizem "PRs" contam comentários, e vários
> comentários do mesmo pull request contam separadamente.

**Repositório**:
Projeto hospedado no GitHub, identificado por `owner/name`. É a unidade de
agrupamento para classificação de Tipo de Projeto — derivado da URL do
comentário, nunca informado diretamente pelo dataset.
_Avoid_: projeto, repo

**Analista**:
Papel de quem usa a ferramenta — sujeito de todas as Histórias de Usuário. Quer
entender padrões de contribuição de uma comunidade, não avaliar um PR específico.
_Avoid_: usuário, revisor

### As classificações semânticas

Enriquecimentos produzidos por LLM. São o único papel do LLM no sistema: ele
classifica, nunca processa dados.

**Tipo de Projeto**:
Categoria do Repositório quanto ao que ele entrega — biblioteca, aplicação web,
framework, CLI. Propriedade do repositório, não do comentário: todos os
comentários de um mesmo repositório compartilham o valor.
_Avoid_: categoria, escopo

**Natureza da Contribuição**:
Que tipo de mudança a contribuição representa — correção de defeito, nova
funcionalidade, refatoração, documentação.
_Avoid_: tipo de PR, categoria da mudança

**Clareza da Descrição**:
Quão bem escrito e compreensível é o texto analisado, numa escala ordinal de
insuficiente a excelente. É a métrica de qualidade da contribuição.
_Avoid_: qualidade, legibilidade, score

### O processamento

**Pipeline**:
Sequência configurável de etapas aplicada de forma preguiçosa sobre o stream de
registros. O analista ativa ou desativa etapas sem que o código mude.
_Avoid_: fluxo, processo, workflow

**Etapa**:
Uma transformação isolada dentro do Pipeline — limpeza, normalização, filtragem,
classificação. Cada etapa recebe e devolve um stream.
_Avoid_: fase, passo, step

**Análise**:
O conjunto de resultados enriquecidos produzido a partir de um dataset. É o que
se persiste para não recomputar: uma vez analisado, um dataset não volta ao LLM.
_Avoid_: resultado, processamento, execução
