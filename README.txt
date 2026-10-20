IMPORTADOR DE EXTRATO OFX - FLASK + POSTGRESQL (NEON)

O QUE O SISTEMA FAZ
1. Permite selecionar um arquivo OFX.
2. Lê e apresenta as movimentações e o resumo de entradas, saídas e saldo calculado.
3. Permite escolher manualmente uma classificação para cada movimentação:
   - Folha de pagamento
   - Aluguel
   - Recebimento de cliente
   - Energia elétrica
   - Material
   - Outros
4. Só grava as movimentações no PostgreSQL depois que o usuário clicar em "Salvar classificações no banco".
5. Evita duplicatas pela combinação de data_movimentacao, valor e descricao. Se o registro já existir, atualiza a classificação escolhida.

REQUISITOS
- Python 3.10 ou superior
- Banco PostgreSQL no Neon

CONFIGURAÇÃO DO BANCO
A tabela precisa ter as colunas data_movimentacao, valor, descricao e classificacao, além de uma restrição única para data_movimentacao + valor + descricao.

Se ainda não adicionou a coluna classificacao, execute no DBeaver:
ALTER TABLE movimentacoes ADD COLUMN IF NOT EXISTS classificacao VARCHAR(100);

Se ainda não criou a restrição única, execute:
ALTER TABLE movimentacoes ADD CONSTRAINT movimentacao_unica UNIQUE (data_movimentacao, valor, descricao);

Se a restrição já existir, não execute o segundo comando novamente.

COMO EXECUTAR NO WINDOWS (POWERSHELL)
1. Extraia o ZIP.
2. Abra o terminal dentro da pasta importador_extrato.
3. Instale as dependências:
   pip install -r requirements.txt
4. Configure a URL de conexão do Neon no terminal, substituindo pelo valor atual da sua conexão:
   $env:DATABASE_URL="SUA_URL_DE_CONEXAO_DO_NEON"
5. Inicie a aplicação:
   python app.py
6. Abra no navegador:
   http://127.0.0.1:5000
7. Escolha o OFX, clique em "Analisar extrato", selecione uma classificação para cada movimentação e clique em "Salvar classificações no banco".

IMPORTANTE
O resumo mostra a soma das movimentações do arquivo importado; ele não substitui necessariamente o saldo oficial do banco. Esta versão é destinada a testes locais e atividade acadêmica. Antes de publicar, configure segurança e ambiente de produção.
