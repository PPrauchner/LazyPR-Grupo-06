# Triage labels

Os cinco papéis canônicos da skill `triage` e as strings correspondentes neste
repositório. Todos existem no GitHub — aplicar com `gh issue edit`.

| Papel | Label | Significa |
|---|---|---|
| Precisa de avaliação | `needs-triage` | um mantenedor ainda não decidiu o que fazer com a issue |
| Aguardando quem reportou | `needs-info` | falta informação para prosseguir |
| Pronta para agente | `ready-for-agent` | especificada o bastante para um agente implementar sem contexto humano |
| Pronta para humano | `ready-for-human` | exige julgamento, acesso ou decisão que um agente não deve tomar |
| Não será feita | `wontfix` | descartada — label padrão do GitHub, preexistente |

## Regra da fila AFK

`/afk-queue` consome exclusivamente issues com `ready-for-agent`. Uma issue só
recebe esse label quando um humano puder respondê-la afirmativamente:

> Um agente que abra esta issue sem nenhum outro contexto consegue implementá-la
> e verificar que funcionou?

Se depende de uma decisão de produto, de credencial que só existe na máquina de
alguém, ou de uma conversa que aconteceu fora do repo, use `ready-for-human`.

## Neste projeto

O enunciado da disciplina é a fonte da verdade (ver `.claude/rules/code-conventions.md`).
Uma issue que peça algo em conflito com uma Regra Geral ou Regra Específica de
Programação Funcional não é `ready-for-agent` — é `needs-triage`, porque a
divergência precisa ser resolvida por uma pessoa antes de virar código.

Os labels de área (`logic-core`, `frontend`, `data-ingestion`, …) são
independentes destes e devem ser aplicados em conjunto. Ver `issue-tracker.md`.
