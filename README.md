# Script de Automação SSH, Google Sheets e Análise de Dados

Este script foi desenvolvido para realizar uma série de tarefas automatizadas em servidores remotos via SSH, processar dados relacionados aos servidores e armazenar esses dados em uma planilha no Google Sheets. Ele interage com o Google Drive para gerenciar arquivos e utiliza expressões regulares para identificar informações específicas nos logs dos servidores.

## Funcionalidades

- **Conexão SSH**: Conecta-se a um servidor remoto via SSH e executa comandos no terminal.
- **Análise de Dados**: Analisa logs do servidor e extrai informações sobre ramais, lagged, status de conexões, entre outros.
- **Google Sheets**: Cria planilhas no Google Sheets e armazena os resultados extraídos dos logs em abas organizadas.
- **Autenticação**: Utiliza credenciais de serviço do Google para se autenticar e interagir com as APIs do Google.

## Pré-requisitos

Antes de executar o script, você precisa garantir que as seguintes dependências estão instaladas em seu ambiente:

1. **Bibliotecas Python**:
   - `paramiko`: Para comunicação com o servidor via SSH.
   - `pandas`: Para análise e manipulação de dados, especialmente ao criar planilhas Excel e Google Sheets.
   - `re`: Para utilizar expressões regulares no processamento dos dados.
   - `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`: Para autenticação na API do Google.
   - `gspread`: Para interação com planilhas do Google Sheets.
   - `gspread-dataframe`: Para manipulação de DataFrames com `gspread`.
   - `google-api-python-client`: Para interação com a API do Google Drive.

Você pode instalar as dependências com o seguinte comando:

```bash
pip install paramiko pandas gspread google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client gspread-dataframe

## Como Usar

### Passo 1: Prepare o arquivo de credenciais do Google

O script requer um arquivo `auth.json` para autenticar a aplicação. Certifique-se de ter o arquivo de credenciais do Google e coloque-o no mesmo diretório do script.

### Passo 2: Execute o Script

O script solicita as seguintes informações para a execução:

- **Endereço IP do servidor SSH**
- **Usuário do servidor SSH**
- **Senha do servidor SSH**
- **Senha do banco de dados**

Após isso, o script se conecta ao servidor SSH, executa comandos para obter informações e armazena os resultados em planilhas do Google Sheets.

Para rodar o script, basta executá-lo com o Python:

```bash
python nome_do_script.py

