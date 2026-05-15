"""
Página responsável pelo upload e ingestão de datasets CSV/JSON.

Esta interface permite que o usuário carregue arquivos contendo
pull requests públicos do GitHub. Após o upload, o pipeline
funcional inicia o processamento lazy dos registros utilizando
geradores Python, evitando carregamento completo em memória.

Responsabilidades:
- Upload de arquivos CSV/JSON
- Validação inicial do dataset
- Inicialização do pipeline funcional
- Disparo do processo de classificação e enriquecimento
- Persistência do hash da análise para cache posterior
"""
