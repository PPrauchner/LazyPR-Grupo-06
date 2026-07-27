Projetos de software hospedados no GitHub recebem contribuições externas e internas por meio de pull requests (PRs).

O histórico de PRs de um projeto contém informações valiosas sobre a dinâmica de contribuição, a qualidade das propostas de mudança e os padrões de revisão adotados pela comunidade.

No entanto, o histórico PRs é volumoso dependendo do escopo (datasets públicos como o GHTorrent e o GitHub Archive contêm milhões de registros) e heterogêneo (PRs variam de correções triviais a reestruturações complexas), o que dificulta a análise manual.

O objetivo deste projeto é desenvolver uma ferramenta que:
1. Ingira um dataset público de pull requests do GitHub.
2. Aplique, usando conceitos de programação funcional, pipelines de limpeza, filtragem e agregação.
3. Utilize Grandes Modelos de Linguagem (do inglês: Large Language Models — LLMs) para enriquecer os dados com classificações semânticas (tipo de projeto, natureza da contribuição, clareza da descrição).
4. Gere relatórios com os resultados da análise.

Histórias de Usuário
01. Como analista, quero fazer upload de datasets de pull requests para análise posterior.

02. Como analista, quero que a ferramenta categorize cada repositório por tipo de projeto (e.g., biblioteca, aplicação web, framework, etc.), para estratificar as análises por escopo.

03. Como analista, quero que a ferramenta categorize cada PR por natureza da contribuição (bug fix, feature, refatoração, documentação, etc.), para entender a distribuição de tipos de contribuição.

04. Como analista, quero que a ferramenta avalie a clareza da descrição de cada PR (e.g., insuficiente, básica, boa, excelente, etc.), para medir a qualidade das contribuições.

05. Como analista, quero visualizar o número de PRs estratificado por linguagem, tipo de projeto e natureza da contribuição.

06. Como analista, quero visualizar a distribuição de tamanho de descrição (caracteres, palavras) estratificada por linguagem, tipo de projeto e natureza.

07. Como analista, quero visualizar a relação entre clareza da descrição, tipo de projeto, natureza da contribuição e linguagem de origem, para entender padrões de contribuição.

08. Como analista, quero filtrar todas as visualizações pelos diferentes critérios analisados para focar em segmentos específicos do dataset.

09. Como analista, quero exportar os resultados da análise em formato CSV e JSON, para utilização em outras ferramentas.

Regras Gerais de Implementação
01. O projeto deve ser implementado em Python, utilizando conceitos do paradigma de programação funcional. Por padrão, deve-se utilizar o dataset disponível em: https://www.kaggle.com/datasets/pelmers/github-public-pull-request-comments?resource=download.

02. A ingestão do dataset deve utilizar geradores para processamento sob demanda (lazy evaluation), sem carregar o dataset inteiro em memória.

03. As classificações de tipo de projeto, natureza do PR e clareza da descrição devem ser realizadas por LLMs.

04. Todas análises de um determinado dataset devem ser persistidas de modo a evitar computações repetidas.

05. As etapas de análise devem ser implementadas como funções passadas como argumento para uma função que centralize um pipeline (usando a noção de funções de ordem superior), permitindo que o usuário ative ou desative etapas de forma configurável.

06. Chamadas aos LLMs devem ser isoladas como efeito colateral. LLMs devem receber dados já pré-processados pelo pipeline funcional e retornar classificações que serão pós-processadas pelo pipeline funcional. LLMs não devem substituir lógica de processamento que o estudante é responsável por implementar, como limpeza, normalização, cálculo de métricas, agrupamento e agregação. O único papel de LLMs será enriquecer os dados com classificações semânticas (e.g., definir qual é o tipo de projeto, a natureza da contribuição, a clareza da descrição, etc.) e não realizar tarefas de processamento de dados no lugar do código funcional que o estudante deve implementar.

07. Todo o processamento de dados deve utilizar funções puras, como map(), filter(), reduce(), funções lambda e estruturas imutáveis.

08. O sistema deve contar com uma interface gráfica.

09. O código deve seguir princípios de Clean Code: nomes descritivos, funções curtas, comentários significativos, etc.

Regras Específicas de Programação Funcional
01. Evite laços de repetição (for, while) como mecanismo principal de transformação de dados. Use alternativas funcionais: map(), filter(), reduce(), comprehensions e funções de alta ordem. Recursão também é incentivada. Laços só são permitidos excepcionalmente, mediante justificativa.

02. Implemente o núcleo de processamento como funções puras. Funções cuja saída é determinada exclusivamente pelas entradas e que não causam efeitos colaterais (modificação de variáveis externas, operações de I/O, modificação de estado global). Isole efeitos colaterais (leitura e escrita de arquivos, requisições HTTP, chamadas a LLMs, interação com interface gráfica) em uma camada separada.

03. Trate dados como imutáveis. Quando necessário transformar uma estrutura de dados, retorne uma nova instância em vez de modificar a original. Prefira tuplas, named tuples e frozensets a listas e dicionários quando a estrutura não precisar ser modificada. Evite métodos que alteram coleções in-place (e.g., append(), extend(), update()).

04. Utilize avaliação preguiçosa (lazy evaluation) via geradores (yield), expressões geradoras e itertools para processar o dataset sem carregar todos os registros em memória simultaneamente.

05. Utilize preferencialmente técnicas como memoização (functools.lru_cache ou implementação manual) para evitar recomputação de resultados em funções puras que são chamadas repetidamente com as mesmas entradas, especialmente para chamadas a LLMs e cálculos intermediários do pipeline de análise.

06. Estruture o código de modo que transformações complexas sejam construídas pela composição de funções menores. Funções devem poder ser combinadas via passagem como argumento, retorno de funções, ou encadeamento em pipelines de transformação.

 
Regras de Organização
Cada grupo deve criar um repositório privado no GitHub e adicionar os professores como colaboradores (usuários: paulosevero e sequincozes).
O desenvolvimento deve ser gerenciado usando a funcionalidade de Projetos do GitHub, com metodologia Kanban (ou similar), atendendo aos seguintes critérios:
Issues devem ser usadas como tarefas do projeto.
O quadro do projeto deve estar populado com todas as tarefas mapeadas para o desenvolvimento (até a entrega final), organizadas na coluna Backlog.
A cada semana, o grupo deve remanejar as tarefas conforme o andamento do desenvolvimento, seguindo o fluxo: Backlog → Sprint Backlog → Em Progresso → Feito, com responsáveis atribuídos a cada tarefa.
IMPORTANTE: A criação do repositório, compartilhamento com os professores e organização do projeto no GitHub devem ser realizados até dia 30/04/2026 às 23h59min. Negligência no atendimento deste critério resultará em conceito NOk para o grupo inteiro na verificação semanal.

 
Dicas de Implementação
01. Utilize os módulos csv ou json com geradores para leitura sob demanda do dataset. Exemplo: um gerador que lê o CSV linha a linha e produz tuplas ou named tuples para cada registro.

02. Utilize o módulo hashlib para gerar hashes do conteúdo enviado aos LLMs, e a função lru_cache (do módulo functools) para memoização das classificações.

03. Utilize a função reduce() para cálculos de agregação (somas, médias, contagens).

04. Utilize o Streamlit ou outra biblioteca de sua preferência para a interface gráfica, desde que seja possível visualizar os resultados da análise de forma interativa e desde que o "back-end" seja em Python (respeitando todas as outras definições deste enunciado).

05. Utilize Agno para chamadas a LLMs. Estruture os prompts para retornar classificações em formato JSON, facilitando o parsing funcional do resultado.

06. Considere agrupar PRs do mesmo repositório para enviar uma única chamada a LLMs para categorização do tipo de projeto (em vez de uma chamada por PR), reduzindo custo e tempo de processamento.

07. Utilize serviços como Groq e OpenRouter para acesso a LLMs sem custo.

Conceitos-Chave
01. Lazy evaluation via geradores para ingestão de datasets grandes.
02. Memoização para caching de chamadas à LLM e cálculos intermediários.
03. Funções de ordem superior para pipelines de pré-processamento e processamento de dados.
04. Separação entre lógica pura (pré-processamento, agregação, cruzamentos) e efeitos colaterais (LLM, I/O).
05. Funções puras para limpeza, normalização e cálculo de métricas.
06. Map, filter e reduce sobre streams de registros de PR.
07. Lambda para transformações e filtros inline.
08. Imutabilidade nas estruturas de dados intermediárias.
09. Composição de funções como mecanismo de construção de pipelines.
10. Clean Code: nomes descritivos, funções curtas, comentários significativos, etc.