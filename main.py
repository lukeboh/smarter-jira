
import requests
import json
import csv
import os
import argparse
from datetime import datetime

LOG_HEADERS = ['issue_key', 'action', 'Issue ID', 'Parent ID', 'Summary', 'Description', 'Issue Type', 'Reporter', 'Assignee', 'Epic Link']

# --- Funções Auxiliares ---

def load_config(config_path):
    """Carrega as configurações do arquivo JSON especificado."""
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo de configuração '{config_path}' não encontrado.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f)

# --- Funções da API do Jira ---

def create_jira_issue(config, token, issue_data, verbose=False, parent_key=None):
    """Cria uma issue no Jira."""
    api_url = f"{config['jira_server']}rest/api/2/issue"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    reporter_email = issue_data.get('Reporter') or config['default_reporter']
    assignee_email = issue_data.get('Assignee') or config.get('default_assignee')
    reporter_username = reporter_email.split('@')[0]

    payload = {
        "fields": {
            "project": {"key": config['default_project']},
            "summary": issue_data['Summary'],
            "description": issue_data['Description'],
            "issuetype": {"name": issue_data['Issue Type']},
            "reporter": {"name": reporter_username}
        }
    }

    if assignee_email:
        payload['fields']['assignee'] = {"name": assignee_email.split('@')[0]}
    if config.get('default_customfield_10247'):
        payload['fields']['customfield_10247'] = {"value": config['default_customfield_10247']}

    if not parent_key:
        payload['fields']['components'] = [{"name": config['default_component']}]
        epic_link_key = issue_data.get('Epic Link')
        epic_link_field_id = config.get('epic_link_field_id')
        if epic_link_key and epic_link_field_id:
            payload['fields'][epic_link_field_id] = epic_link_key
    else:
        payload['fields']['parent'] = {"key": parent_key}

    if verbose:
        print(f"--- PAYLOAD (CREATE) ---\n{json.dumps(payload, indent=4)}\n--------------------------")

    response = requests.post(api_url, headers=headers, data=json.dumps(payload))

    if response.status_code == 201:
        return response.json()
    else:
        print(f"Erro ao criar issue '{issue_data['Summary']}'. Status: {response.status_code}\nResposta: {response.text}")
        return None

def update_jira_issue(issue_key, config, token, issue_data, verbose=False):
    """Atualiza uma issue no Jira."""
    api_url = f"{config['jira_server']}rest/api/2/issue/{issue_key}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    fields_to_update = {}
    # Apenas o assignee pode ser atualizado por enquanto, conforme solicitado
    assignee_email = issue_data.get('Assignee') or config.get('default_assignee')
    if assignee_email:
        fields_to_update['assignee'] = {"name": assignee_email.split('@')[0]}

    if not fields_to_update:
        print(f"Aviso: Nenhum campo para atualizar para a issue {issue_key}")
        return True # Considera sucesso pois não há nada a fazer

    payload = {"fields": fields_to_update}

    if verbose:
        print(f"--- PAYLOAD (UPDATE) ---\n{json.dumps(payload, indent=4)}\n--------------------------")

    response = requests.put(api_url, headers=headers, data=json.dumps(payload))

    if response.status_code == 204:
        return True
    else:
        print(f"Erro ao atualizar issue {issue_key}. Status: {response.status_code}\nResposta: {response.text}")
        return False

def delete_jira_issue(issue_key, config, token):
    """Deleta uma issue no Jira."""
    api_url = f"{config['jira_server']}rest/api/2/issue/{issue_key}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(api_url, headers=headers)
    if response.status_code == 204:
        print(f"Sucesso ao deletar issue {issue_key}.")
        return True
    else:
        print(f"Erro ao deletar issue {issue_key}. Status: {response.status_code}\nResposta: {response.text}")
        return False

# --- Funções de Processamento ---

def get_row_data_for_log(row):
    return [row.get(h) for h in LOG_HEADERS[2:]]

def process_creation(config, token, csv_file, log_writer, verbose=False, ignore_epics=False):
    if not os.path.exists(csv_file):
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return
    parent_issue_map = {}
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        issues_to_process = list(reader)
    for row in issues_to_process:
        row = {k.strip(): v for k, v in row.items()}
        if not row.get('Parent ID'):
            if not ignore_epics and not row.get('Epic Link'):
                print(f"Erro: O Epic Link é obrigatório para a issue '{row['Summary']}'. Use --ignore-epics para desabilitar.")
                return
            print(f"Criando issue principal: '{row['Summary']}'")
            created_issue = create_jira_issue(config, token, row, verbose=verbose)
            if created_issue:
                key = created_issue['key']
                parent_issue_map[row['Issue ID']] = key
                log_writer.writerow([key, 'C'] + get_row_data_for_log(row))
                print(f"  -> Sucesso! Chave da Issue: {key}")
            else:
                print(f"  -> Falha ao criar a issue principal.")
    for row in issues_to_process:
        row = {k.strip(): v for k, v in row.items()}
        parent_id = row.get('Parent ID')
        if parent_id and parent_id in parent_issue_map:
            parent_key = parent_issue_map[parent_id]
            print(f"Criando sub-task '{row['Summary']}' para a issue pai {parent_key}")
            created_issue = create_jira_issue(config, token, row, verbose=verbose, parent_key=parent_key)
            if created_issue:
                key = created_issue['key']
                log_writer.writerow([key, 'C'] + get_row_data_for_log(row))
                print(f"  -> Sucesso! Chave da Sub-task: {key}")
            else:
                print(f"  -> Falha ao criar a sub-task.")

def process_deletion(config, token, csv_file, log_writer):
    if not os.path.exists(csv_file):
        print(f"Erro: Arquivo de log CSV '{csv_file}' não encontrado.")
        return
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows_to_delete = list(reader)
    rows_to_delete.reverse()
    for row in rows_to_delete:
        issue_key = row.get('issue_key')
        if issue_key:
            print(f"Deletando issue: {issue_key}")
            if delete_jira_issue(issue_key, config, token):
                log_data = [row.get(h) for h in LOG_HEADERS]
                log_data[1] = 'D'
                log_writer.writerow(log_data)
        else:
            print(f"Aviso: linha ignorada no arquivo de log por não conter 'issue_key': {row}")

def process_update(config, token, csv_file, log_writer, verbose=False):
    """Processa um arquivo de log para atualizar issues."""
    if not os.path.exists(csv_file):
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            issue_key = row.get('issue_key')
            if issue_key:
                print(f"Atualizando issue: {issue_key}")
                if update_jira_issue(issue_key, config, token, row, verbose=verbose):
                    log_data = [row.get(h) for h in LOG_HEADERS]
                    log_data[1] = 'U'
                    log_writer.writerow(log_data)
            else:
                print(f"Aviso: linha ignorada por não conter 'issue_key': {row}")

# --- Ponto de Entrada ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria, deleta ou atualiza issues no Jira a partir de um arquivo CSV.")
    parser.add_argument('--action', type=str, choices=['create', 'delete', 'update'], default='create', help='Ação a ser executada.')
    parser.add_argument('-c', '--config', type=str, required=True, help='Caminho para o arquivo de configuração JSON.')
    parser.add_argument('--csv', type=str, required=True, help='Caminho para o arquivo CSV de entrada.')
    parser.add_argument('--logfile', type=str, help='Nome do arquivo de log de saída. Padrão: NOME_DO_CSV_log_TIMESTAMP.csv')
    parser.add_argument('-v', '--verbose', action='store_true', help='Exibe o payload JSON enviado para a API do Jira.')
    parser.add_argument('-i', '--ignore-epics', action='store_true', help='Ignora a verificação de Epic Link obrigatório na criação.')
    args = parser.parse_args()

    config = load_config(args.config)
    if not config:
        exit(1)

    token = config.get("jira_token")
    if not token or "YOUR_JIRA_API_TOKEN" in token:
        print("Erro: Token do Jira não encontrado ou não configurado no arquivo de configuração JSON.")
        exit(1)

    log_filename = args.logfile or f"{os.path.splitext(os.path.basename(args.csv))[0]}_log_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    
    try:
        with open(log_filename, 'w', newline='', encoding='utf-8') as logfile:
            log_writer = csv.writer(logfile)
            log_writer.writerow(LOG_HEADERS)

            print(f"Iniciando ação: {args.action.upper()}")
            print(f"Usando arquivo de log: {log_filename}")

            if args.action == 'create':
                process_creation(config, token, args.csv, log_writer, verbose=args.verbose, ignore_epics=args.ignore_epics)
            elif args.action == 'delete':
                process_deletion(config, token, args.csv, log_writer)
            elif args.action == 'update':
                process_update(config, token, args.csv, log_writer, verbose=args.verbose)

            print("Processo finalizado.")

    except IOError as e:
        print(f"Erro ao escrever no arquivo de log '{log_filename}': {e}")
        exit(1)
