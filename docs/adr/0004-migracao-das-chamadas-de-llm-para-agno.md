# Migração das chamadas de LLM para Agno

A Dica 05 do enunciado recomenda Agno para as chamadas a LLMs; o código usa o SDK
do Groq direto, e `agno>=2.6.5` está declarado no `pyproject.toml` sem ser
importado por módulo nenhum — uma dependência fantasma. Como
`.claude/rules/code-conventions.md` exige ADR para mudança de stack, decidimos
**migrar para Agno, e migrar cedo** — antes da correção dos prompts
([ADR-0002](./0002-clareza-avaliada-sobre-o-comentario-de-revisao.md)) — para que
os prompts sejam reescritos uma única vez, já sobre a biblioteca definitiva.

## Considered Options

- **Não migrar, e remover `agno` do `pyproject.toml`** — a Dica 05 é *Dica*, não
  Regra: usar o SDK direto não é não-conformidade. Zero risco, e o SDK direto dá
  controle fino sobre o rate limit. Descartada porque o grupo prefere atender à
  Dica, que a banca pode valorizar.
- **Migrar depois das correções de prompt** — mais seguro por ordem, mas obrigaria
  a reescrever os prompts duas vezes.
- **Migrar cedo** (escolhida) — os prompts nascem sobre o Agno.

## Consequences

O throttle de 2,1 s entre requisições e o backoff exponencial de até 6 tentativas
são o que segura o teto de **30 RPM** do plano gratuito do Groq. A migração precisa
preservá-los ou reimplementá-los sobre o Agno. Essa é a parte perigosa: um throttle
quebrado não falha em teste — falha com erro 429 no meio de uma análise longa, em
produção.

Por isso a migração é sequenciada **depois** do conserto da suíte de testes, que
hoje não coleta. Migrar sem suíte que rode significa trocar a camada inteira de LLM
sem nenhuma forma de verificar que a proteção sobreviveu.

## Caminho de erro: recusa de schema falha alto

A migração criou um caminho de falha que não existia antes. Com o SDK direto, uma
resposta fora do vocabulário controlado (`"monorepo"`, chave errada, texto solto)
chegava como string a `services/classifiers.py` e degradava para o sentinela
`unknown` via `normalize_label()`. Com o Agno, a validação contra o `Literal` do
`output_schema` acontece antes: o `parse_response_model_str` engole o
`ValidationError`, registra um *warning* e devolve **a string crua** em `content`
— `normalize_label()` nunca é alcançada.

Duas decisões seguem daí.

**Orçamentos de tentativa separados.** Antes, o desvio de schema era tratado como
falha de rede: 6 tentativas com backoff exponencial, ~12 s de espera, para o
modelo repetir uma recusa largamente determinística. Agora
`_invoke_with_retry` conta rede e schema em separado — rede mantém as 6
tentativas e o backoff (inclusive o tempo sugerido no 429), schema tem **2
tentativas**. A tentativa extra existe porque o JSON mode é probabilístico e
flutua de verdade; a partir daí só se queima cota. O throttle de 2,1 s continua
precedendo **toda** requisição, nos dois caminhos — é ele que segura os 30 RPM.

**Falhar alto, não degradar para sentinela.** Esgotado o orçamento de schema,
`SchemaRefusalError` (subclasse de `ValueError`, para não quebrar quem já captura
`ValueError`) propaga carregando o repositório de origem e o conteúdo recusado
truncado. `views/upload.py` a converte em mensagem de erro legível.

A alternativa considerada era converter a recusa em `UNKNOWN_PROJECT_TYPE` /
`UNKNOWN_PR_NATURE` / `UNKNOWN_CLARITY_LEVEL` e seguir. Foi recusada: `unknown`
gravado no resultado é indistinguível de classificação legítima e contaminaria a
correlação da HU 07 sem deixar rastro. Os sentinelas continuam servindo apenas ao
que já serviam — campo ausente do JSON e label fora do vocabulário que
`normalize_label()` alcança.

Consequência conhecida e aceita: como `save_results()` só é chamado depois de
materializar o gerador, falhar alto descarta a classificação já paga naquela
execução. Persistência incremental mudaria o contrato da Regra Geral 04 e fica
para issue própria.

Por ser Dica e não Regra, este ADR é reversível a custo baixo: se o Agno não
permitir o controle de rate limit necessário, voltar ao SDK direto **não** é
não-conformidade — mas exige superseder este ADR, e não apenas reverter o código.
