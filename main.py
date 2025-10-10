
import requests
import json
import csv
import os
import argparse

# --- Funções ---

def load_config(config_path):
    """Carrega as configurações do arquivo JSON especificado."""
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo de configuração '{config_path}' não encontrado.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f)

def load_token():
    """Carrega o token de autenticação."""
    token_file = 'token.txt'
    if not os.path.exists(token_file):
        print(f"Erro: Arquivo de token '{token_file}' não encontrado.")
        return None
    with open(token_file, 'r') as f:
        token = f.read().strip()
        if "COLOQUE_SEU_TOKEN" in token:
            print(f"AVISO: Por favor, substitua o conteúdo de '{token_file}' pelo seu token de API do Jira.")
            return None
        return token

def create_jira_issue(config, token, issue_data, verbose=False, parent_key=None):
    """Cria uma issue no Jira."""
    api_url = f"{config['jira_server']}rest/api/2/issue"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "fields": {
            "project": {
                "key": config['default_project']
            },
            "summary": issue_data['Summary'],
            "description": issue_data['Description'],
            "issuetype": {
                "name": issue_data['Issue Type']
            },
            "reporter": {
                "name": config['default_reporter']
            },
            "customfield_10247": { "value": config['default_customfield_10247'] }
        }
    }

    # Adiciona o campo 'components' apenas para issues pais (não sub-tasks)
    if not parent_key:
        payload['fields']['components'] = [
            {
                "name": config['default_component']
            }
        ]

    # Adiciona o link de parent para sub-tasks
    if parent_key and issue_data['Issue Type'].lower() in ['sub-task', 'subtarefa']:
        payload['fields']['parent'] = {
            "key": parent_key
        }

    if verbose:
        print("--- PAYLOAD ENVIADO PARA O JIRA ---")
        print(json.dumps(payload, indent=4))
        print("----------------------------------")

    response = requests.post(api_url, headers=headers, data=json.dumps(payload))

    if response.status_code == 201:
        return response.json()
    else:
        print(f"Erro ao criar issue '{issue_data['Summary']}'. Status: {response.status_code}")
        print(f"Resposta: {response.text}")
        return None

def process_csv(config_file, csv_file, verbose=False):
    """Processa o arquivo CSV e cria as issues."""
    config = load_config(config_file)
    token = load_token()

    if not config or not token:
        print("Processo interrompido devido a erro de configuração ou token.")
        return

    if not os.path.exists(csv_file):
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return

    parent_issue_map = {} # Mapeia o ID do CSV para a chave da issue criada no Jira

    with open(csv_file, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        issues_to_process = list(reader)
        
        for row in issues_to_process:
            if not row.get('Parent ID'):
                print(f"Criando issue principal: '{row['Summary']}'")
                created_issue = create_jira_issue(config, token, row, verbose=verbose)
                if created_issue:
                    parent_issue_map[row['Issue ID']] = created_issue['key']
                    print(f"  -> Sucesso! Chave da Issue: {created_issue['key']}")
                else:
                    print(f"  -> Falha ao criar a issue principal.")

        for row in issues_to_process:
            parent_id = row.get('Parent ID')
            if parent_id and parent_id in parent_issue_map:
                parent_key = parent_issue_map[parent_id]
                print(f"Criando sub-task '{row['Summary']}' para a issue pai {parent_key}")
                created_issue = create_jira_issue(config, token, row, verbose=verbose, parent_key=parent_key)
                if created_issue:
                    print(f"  -> Sucesso! Chave da Sub-task: {created_issue['key']}")
                else:
                    print(f"  -> Falha ao criar a sub-task.")


# --- Ponto de Entrada ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria issues no Jira a partir de um arquivo CSV.")
    parser.add_argument('-c', '--config', type=str, required=True, help='Caminho para o arquivo de configuração JSON.')
    parser.add_argument('-csv', type=str, required=True, help='Caminho para o arquivo CSV com as issues.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Exibe o payload JSON enviado para a API do Jira.')
    args = parser.parse_args()

    print("Iniciando processo de criação de issues no Jira...")
    process_csv(config_file=args.config, csv_file=args.csv, verbose=args.verbose)
    print("Processo finalizado.")
