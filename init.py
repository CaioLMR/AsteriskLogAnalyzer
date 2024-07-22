import paramiko #comunicação com servidores remotos (ssh)
import pandas as pd #Analise de dados (excel)
import re #Expressoes regulares
from google.oauth2.service_account import Credentials #Autorizar a aplicação para acessar api do google
import gspread #interação com google sheets
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
import os #interagir com o sistema operacional subjacente
import io #trabalhar com entrada e saida de dados
import getpass #Mascarar Caracteres - senha

# Solicita autenticação para conexão SSH
hostname = input("Digite o hostname ou endereço IP do servidor SSH: ")
username = input("Digite Usuario do Servidor SSH: ")
password = getpass.getpass("Digite a Senha do Servidor SSH: ")
passwordbd = getpass.getpass("Digite a Senha do Banco de Dados: ")

# Comandos a serem executados no servidor remoto
comando_hostname = 'hostname'
comando_ramais = 'less -F /var/log/asterisk/full | grep "Registered SIP \'" | grep -E "\\b([1-9][0-9]{2}|[1-9][0-9]{3})\\b" | awk \'{print $9, $11}\' | awk \'{sub(/:.*/, "", $2); print}\' | sort | uniq -c'
comando_lagged = 'less -F /var/log/asterisk/messages | grep "Lagged" | grep -E "\\b([1-9][0-9]{2}|[1-9][0-9]{3})\\b" | awk \'{print $8}\' | sort | uniq -c'
comando_unreachable = 'less -F /var/log/asterisk/messages | grep "UNREACHABLE" | grep -E "\\b([1-9][0-9]{2}|[1-9][0-9]{3})\\b" | awk \'{print $8}\' | sort | uniq -c'
comando_dnd = 'grep "Playing \'do-not-disturb.slin\'" /var/log/asterisk/full | awk \'{print $1, $2, $3, $4, $7, $9}\''
comando_exten = 'grep "DidMap not" /var/log/asterisk/full | egrep -o \'(Exten [[:digit:]]*)\' | sort -n | uniq'
comando_mysql = 'mysql -u root -p{passwordbd} -e "use ironvox; SELECT * FROM IronvoxConf"'

# Expressão regular para encontrar ramais com 4 dígitos XXXX ou 3 digitos [2-9]XX
ramal_regex = r"('\d{4}'|'[2-9]\d{2}')"

# Função para verificar ramais repetidos
def verificar_ramais_repetidos(output):
    ramais_encontrados = re.findall(ramal_regex, output)
    ramais_repetidos = {ramal: ramais_encontrados.count(ramal) for ramal in set(ramais_encontrados) if ramais_encontrados.count(ramal) > 1}
    
    resultados = []
    if ramais_repetidos:
        for ramal, count in ramais_repetidos.items():
            linhas = [linha for linha in output.splitlines() if ramal in linha]
            resultados.append({
                'Peer': ramal,
                'Contagem': count,
                'Linhas': '\n'.join(linhas)
            })
    
    return resultados

# Executa o comando pwd para pegar diretorio onde esta o script
current_directory = os.popen('pwd').read().strip()

# Define a variável service_account_file com o caminho do json para autenticação
service_account_file = f'{current_directory}/auth.json'
print(service_account_file)

# Autenticação e conexão com Google Drive e Google Sheets
scope = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(service_account_file, scopes=scope)
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

def delete_existing_file(drive_service, folder_id, file_name):
    query = f"'{folder_id}' in parents and name='{file_name}' and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        for item in items:
            drive_service.files().delete(fileId=item['id']).execute()
            print(f"Arquivo existente '{file_name}' excluído do Google Drive.")
            print()  # Linha em branco

# Conectar via SSH e processar
try:
    # Cria uma sessão SSH
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Conectando ao servidor via SSH...")
    
    # Conecta ao servidor
    ssh_client.connect(hostname, username=username, password=password)
    print("Conectado ao servidor.")

    # Executa o comando `hostname` no servidor remoto
    stdin_hostname, stdout_hostname, stderr_hostname = ssh_client.exec_command(comando_hostname)
    hostname_result = stdout_hostname.read().decode('utf-8').strip()
    print(f"Hostname do servidor: {hostname_result}")

    # Executa os comandos no servidor remoto e coleta as saídas
    def execute_command(command, desc):
        print(f"Executando comando '{desc}'...")
        stdin, stdout, stderr = ssh_client.exec_command(command)
        return stdout.read().decode('utf-8').strip()

    output_ramais = execute_command(comando_ramais, "Ramais")
    output_lagged = execute_command(comando_lagged, "Lagged")
    output_unreachable = execute_command(comando_unreachable, "UNREACHABLE")
    output_dnd = execute_command(comando_dnd, "DND")
    output_exten = execute_command(comando_exten, "Exten")
    output_mysql = execute_command(comando_mysql, "Modulos")

    # Chama a função para verificar ramais repetidos com a saída processada
    print("Processando resultados de ramais repetidos...")
    resultados_ramais = verificar_ramais_repetidos(output_ramais)

    # Criar DataFrames com os resultados dos comandos
    print("Criando DataFrames...")
    df_mysql = pd.read_csv(io.StringIO(output_mysql), sep='\t')
    df_resultados = pd.DataFrame(resultados_ramais)
    df_lagged = pd.DataFrame([x.split(maxsplit=1) for x in output_lagged.splitlines()], columns=['Contagem', 'Peer'])
    df_unreachable = pd.DataFrame([x.split(maxsplit=1) for x in output_unreachable.splitlines()], columns=['Contagem', 'Peer'])
    df_dnd = pd.DataFrame([x.split() for x in output_dnd.splitlines()], columns=['Data', 'Hora', 'Timezone', 'Ano', 'Peer', 'Arquivo'])
    df_exten = pd.DataFrame([x.split()[1] for x in output_exten.splitlines()], columns=['Exten'])

    # Define nome do arquivo excel pelo host do server remoto
    nome_arquivo_excel = f'{hostname_result}.xlsx'
    print(f"Nome do arquivo Excel: {nome_arquivo_excel}")

    # ID da pasta no Google Drive
    folder_id = '1qGue58Yau9ZUmkJQdWcBYIXuQtpiWOg1'

    # Verificar e deletar arquivo existente
    print("Verificando e excluindo arquivo existente se necessário...")
    delete_existing_file(drive_service, folder_id, nome_arquivo_excel)

    # Criar uma nova planilha no Google Drive
    print("Criando nova planilha no Google Drive...")
    spreadsheet = client.create(nome_arquivo_excel)
    spreadsheet.share('script-suporte@inspired-vault-429812-q5.iam.gserviceaccount.com', perm_type='user', role='writer')
    print(f"Planilha '{nome_arquivo_excel}' criada e compartilhada.")

    # Selecionar a planilha criada
    sheet = client.open(nome_arquivo_excel)

    # Adicionar dados às abas correspondentes
    def add_worksheet_with_data(sheet, title, dataframe):
        print(f"Adicionando aba '{title}' com dados...")
        worksheet = sheet.add_worksheet(title=title, rows="100", cols="20")
        set_with_dataframe(worksheet, dataframe)

    add_worksheet_with_data(sheet, "IronvoxConf", df_mysql)
    add_worksheet_with_data(sheet, "Ramais_Repetidos", df_resultados)
    add_worksheet_with_data(sheet, "Lagged", df_lagged)
    add_worksheet_with_data(sheet, "UNREACHABLE", df_unreachable)
    add_worksheet_with_data(sheet, "DND", df_dnd)
    add_worksheet_with_data(sheet, "Exten", df_exten)

    # Remover a planilha caso ja exista outra com mesmo nome
    print("Removendo a aba padrão da planilha...")
    sheet.del_worksheet(sheet.sheet1)

    # Mover a planilha para a pasta desejada
    print("Movendo a planilha para a pasta desejada...")
    file_id = spreadsheet.id
    drive_service.files().update(fileId=file_id, addParents=folder_id, removeParents='root').execute()

    print(f"Arquivo Excel '{nome_arquivo_excel}' salvo com sucesso no Google Drive na pasta especificada.")

except paramiko.AuthenticationException:
    print("Erro de autenticação. Verifique suas credenciais.")
except paramiko.SSHException as e:
    print(f"Erro SSH: {e}")
except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    # Fechar a conexão SSH
    if 'ssh_client' in locals():
        print("Fechando a conexão SSH...")
        ssh_client.close()
