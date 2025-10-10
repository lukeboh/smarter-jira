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

def create_jira_issue(config, token, issue_data, verbose=False, parent_key=None):
    """Cria uma issue no Jira."""
    api_url = f"{config['jira_server']}rest/api/2/issue"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Lógica de fallback para reporter e assignee
    reporter_email = issue_data.get('Reporter') or config['default_reporter']
    assignee_email = issue_data.get('Assignee') or config.get('default_assignee')

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
                "name": reporter_email
            },
            "customfield_10247": { "value": config['default_customfield_10247'] }
        }
    }

    if assignee_email:
        payload['fields']['assignee'] = {"name": assignee_email}

    # Adiciona campos que só se aplicam a issues pais (não sub-tasks)
    if not parent_key:
        payload['fields']['components'] = [
            {
                "name": config['default_component']
            }
        ]
        # Adiciona o Epic Link se ele existir no CSV
        epic_link = issue_data.get('Epic Link')
        if epic_link:
            # O nome do campo para a API do Jira é geralmente 'Epic Link'
            payload['fields']['Epic Link'] = epic_link

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

def process_csv(config_file, csv_file, verbose=False, ignore_epics=False):
    """Processa o arquivo CSV e cria as issues."""
    config = load_config(config_file)
    if not config:
        print("Processo interrompido devido a erro de configuração.")
        return

    token = config.get("jira_token")
    if not token or "YOUR_JIRA_API_TOKEN" in token:
        print("Erro: Token do Jira não encontrado ou não configurado no arquivo de configuração JSON.")
        return

    if not os.path.exists(csv_file):
        print(f"Erro: Arquivo CSV '{csv_file}' não encontrado.")
        return

    parent_issue_map = {} # Mapeia o ID do CSV para a chave da issue criada no Jira

    with open(csv_file, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        issues_to_process = list(reader)
        
        for row in issues_to_process:
            # Normaliza os nomes das colunas (remove espaços em branco)
            row = {k.strip(): v for k, v in row.items()}

            if not row.get('Parent ID'):
                # Validação do Epic Link para issues principais
                if not ignore_epics and not row.get('Epic Link'):
                    print(f"Erro: O Epic Link é obrigatório para a issue '{row['Summary']}'. Use --ignore-epics para desabilitar esta verificação.")
                    return # Interrompe o processo

                print(f"Criando issue principal: '{row['Summary']}'")
                created_issue = create_jira_issue(config, token, row, verbose=verbose)
                if created_issue:
                    parent_issue_map[row['Issue ID']] = created_issue['key']
                    print(f"  -> Sucesso! Chave da Issue: {created_issue['key']}")
                else:
                    print(f"  -> Falha ao criar a issue principal.")

        for row in issues_to_process:
            # Normaliza os nomes das colunas (remove espaços em branco)
            row = {k.strip(): v for k, v in row.items()}
            
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
    parser.add_argument('--csv', type=str, required=True, help='Caminho para o arquivo CSV com as issues.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Exibe o payload JSON enviado para a API do Jira.')
    parser.add_argument('-i', '--ignore-epics', action='store_true', help='Ignora a verificação de Epic Link obrigatório.')
    args = parser.parse_args()

    print("Iniciando processo de criação de issues no Jira...")
    process_csv(config_file=args.config, csv_file=args.csv, verbose=args.verbose, ignore_epics=args.ignore_epics)
    print("Processo finalizado.")