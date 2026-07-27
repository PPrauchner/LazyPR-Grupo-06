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

Por ser Dica e não Regra, este ADR é reversível a custo baixo: se o Agno não
permitir o controle de rate limit necessário, voltar ao SDK direto **não** é
não-conformidade — mas exige superseder este ADR, e não apenas reverter o código.
