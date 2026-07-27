# Domain docs

O LazyPR é **single-context**: um único `CONTEXT.md` e um único `docs/adr/`, ambos
na raiz. Não existe `CONTEXT-MAP.md` e não deve existir — o projeto não tem
subdomínios separados.

| Arquivo | O que é |
|---|---|
| [`CONTEXT.md`](../../CONTEXT.md) | glossário de domínio — só vocabulário, nada de implementação |
| [`docs/adr/`](../adr/) | decisões arquiteturais, numeradas sequencialmente |
| [`CLAUDE.md`](../../CLAUDE.md) | arquitetura, contratos entre camadas, estado de conformidade |
| [`.claude/rules/`](../../.claude/rules/) | convenções de código e restrições do projeto |

## Como consumir

**Antes de implementar**, leia o `CONTEXT.md` e use os termos de lá. Se precisar de
uma palavra que não está no glossário, esse é o sinal de que falta uma decisão —
pergunte em vez de inventar sinônimo.

**Antes de propor mudança de arquitetura**, leia os ADRs. Uma decisão registrada
não é revertida de passagem: se um ADR está errado, escreva o próximo que o
supersede, com o porquê.

**Ao escrever código**, respeite a ponte pt-BR ↔ inglês: identificadores em inglês,
documentação em português. O `CONTEXT.md` faz a tradução entre os dois.

## Como manter

Atualize o `CONTEXT.md` quando um termo for **resolvido**, não quando for
mencionado. Um glossário que acumula sinônimos deixa de ser glossário — cada
conceito tem um nome escolhido e os rejeitados vão em `_Avoid_`.

Escreva um ADR novo apenas quando os três critérios valerem juntos: difícil de
reverter, surpreendente sem contexto, e resultado de trade-off real. Decisão
óbvia não vira ADR.

## Particularidade deste projeto

O domínio tem uma imprecisão herdada do enunciado da disciplina: cada registro do
dataset é um **Comentário de Revisão**, mas o enunciado e a interface chamam de
**PR**. O `CONTEXT.md` registra os dois termos e a ponte entre eles. Ao escrever
código ou documentação, use a distinção — ela muda o que as métricas significam.
