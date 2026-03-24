import argparse
import json
import os
from functools import total_ordering, cmp_to_key
from jira import JIRA

def load_config(config_path):
    """Carrega as configurações do arquivo JSON especificado."""
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo de configuração '{config_path}' não encontrado.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f)

def get_rank_field_id(client):
    """Descobre dinamicamente o ID do campo 'Rank'."""
    try:
        all_fields = client.fields()
        for field in all_fields:
            if field['name'] == 'Rank':
                return field['id']
    except Exception as e:
        print(f"Aviso: Não foi possível descobrir o ID do campo 'Rank'. O rank não será exibido. Erro: {e}")
    return None

def rank_child_issues(client, parent_key, rank_by_list, order_list, dry_run=False, debug=False, status_order=None, issuetype_order=None):
    """Busca, ordena e, opcionalmente, reordena as issues filhas de uma issue pai."""
    try:
        print(f"Buscando a issue pai '{parent_key}' para determinar o tipo...")
        parent_issue = client.issue(parent_key, fields="issuetype")
        print(f"Issue pai encontrada. Tipo: {parent_issue.fields.issuetype.name}")
    except Exception as e:
        print(f"Erro: Não foi possível encontrar a issue pai '{parent_key}'.")
        print(e)
        return

    rank_field_id = get_rank_field_id(client)

    if parent_issue.fields.issuetype.name in ['Epic', 'Épico']:
        jql = f"'Epic Link' = '{parent_key}' ORDER BY Rank ASC"
    else:
        jql = f"parent = '{parent_key}' ORDER BY Rank ASC"
    
    print(f"Buscando issues filhas com JQL: {jql}")
    try:
        fields_to_fetch = set(rank_by_list)
        fields_to_fetch.update(['priority', 'status', 'issuetype'])
        if rank_field_id:
            fields_to_fetch.add(rank_field_id)
        
        child_issues = client.search_issues(jql, maxResults=False, fields=list(fields_to_fetch))
    except Exception as e:
        print("Erro ao executar a busca por issues filhas.")
        print(e)
        return

    if not child_issues:
        print("Nenhuma issue filha encontrada para reordenar.")
        return

    print(f"Encontradas {len(child_issues)} issues filhas.")

    current_order_keys = [issue.key for issue in child_issues]

    if len(order_list) == 1 and len(rank_by_list) > 1:
        order_list = order_list * len(rank_by_list)
    elif len(order_list) != len(rank_by_list):
        print(f"Erro: O número de critérios de ordenação ({len(rank_by_list)}) não corresponde ao número de direções ({len(order_list)}).")
        return

    status_order_lower = [s.lower() for s in status_order] if status_order else None
    issuetype_order_lower = [s.lower() for s in issuetype_order] if issuetype_order else None

    def get_value_for_criterion(issue, criterion):
        if criterion == 'key':
            try:
                prefix, number = issue.key.rsplit('-', 1)
                return (prefix, int(number))
            except (ValueError, TypeError):
                return (issue.key, 0)
        if criterion == 'priority':
            return int(issue.fields.priority.id)
        if criterion == 'status':
            if status_order_lower:
                status_name = issue.fields.status.name.lower()
                try:
                    return status_order_lower.index(status_name)
                except ValueError:
                    return len(status_order_lower)
            category_id_map = {2: 0, 4: 1, 3: 2}
            category_id = int(issue.fields.status.statusCategory.id)
            return category_id_map.get(category_id, 99)
        if criterion == 'issuetype':
            if issuetype_order_lower:
                issuetype_name = issue.fields.issuetype.name.lower()
                try:
                    return issuetype_order_lower.index(issuetype_name)
                except ValueError:
                    return len(issuetype_order_lower)
            return issue.fields.issuetype.name
        
        return getattr(issue.fields, criterion, None)

    def compare_issues(issue1, issue2):
        if debug: print(f"\n--- Comparando {issue1.key} e {issue2.key} ---")
        for i, criterion in enumerate(rank_by_list):
            val1 = get_value_for_criterion(issue1, criterion)
            val2 = get_value_for_criterion(issue2, criterion)
            order = order_list[i]
            
            if debug: print(f"  Critério '{criterion}' (ordem: {order}): val1={val1}, val2={val2}")

            if val1 is None and val2 is not None: return 1
            if val1 is not None and val2 is None: return -1
            if val1 is None and val2 is None:
                if debug: print("  > Ambos nulos. Empate.")
                continue

            if val1 < val2:
                result = -1 if order == 'asc' else 1
                if debug: print(f"  > {val1} < {val2}. Resultado: {result}")
                return result
            if val1 > val2:
                result = 1 if order == 'asc' else -1
                if debug: print(f"  > {val1} > {val2}. Resultado: {result}")
                return result
            if debug: print("  > Iguais. Empate, próximo critério.")
        if debug: print("--- Fim da Comparação: Iguais ---")
        return 0

    try:
        sorted_child_issues = sorted(child_issues, key=cmp_to_key(compare_issues))
        print(f"\nIssues ordenadas com sucesso por: {', '.join(rank_by_list)}.")
    except Exception as e:
        print(f"Erro inesperado ao ordenar as issues em memória: {e}")
        return

    proposed_order_keys = [issue.key for issue in sorted_child_issues]

    if current_order_keys == proposed_order_keys:
        print("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")
        return

    print("\n--- Ordem Proposta (Final) ---")
    for issue in sorted_child_issues:
        rank_value = getattr(issue.fields, rank_field_id, 'N/A') if rank_field_id else 'N/A'
        print(f"  - {issue.key} (Rank atual: {rank_value})")
    print("----------------------------")

    if dry_run:
        print("\nMODO DRY-RUN ATIVADO. Nenhuma alteração será aplicada no Jira.")
        return

    print("\nIniciando o processo de reordenação no Jira (isso pode levar um tempo)...")
    
    try:
        server_url = client._options['server'].rstrip('/')
        rank_url = f"{server_url}/rest/agile/1.0/issue/rank"
        
        previous_issue_key = sorted_child_issues[0].key
        for i in range(1, len(sorted_child_issues)):
            current_issue_key = sorted_child_issues[i].key
            print(f"  - Movendo '{current_issue_key}' para depois de '{previous_issue_key}'...")
            
            payload = {
                "issues": [current_issue_key],
                "rankAfterIssue": previous_issue_key
            }
            response = client._session.put(rank_url, json=payload)
            response.raise_for_status()
            
            previous_issue_key = current_issue_key

    except Exception as e:
        print("\nOcorreu um erro durante a reordenação via API do Jira.")
        print("É possível que a ordenação tenha sido parcialmente aplicada.")
        print(f"Erro: {e}")
        return

    print("\nReordenação concluída com sucesso!")


if __name__ == "__main__":


    def list_of_str(arg):


        # Retorna None se o argumento for None, senão divide a string


        if arg is None:


            return None


        return [s.strip() for s in arg.split(',')]





    # --- Análise de Argumentos ---





    # 1. Pré-análise para encontrar o caminho do arquivo de configuração


    # Isso nos permite carregar a configuração e usá-la para os padrões do analisador principal.


    pre_parser = argparse.ArgumentParser(add_help=False)


    pre_parser.add_argument('-c', '--config', type=str, help='Caminho para o arquivo de configuração JSON.')


    pre_args, _ = pre_parser.parse_known_args()





    # 2. Carregar configuração do arquivo, se existir


    config = {}


    if pre_args.config:


        loaded_config = load_config(pre_args.config)


        if loaded_config is None: # Erro se o arquivo for especificado mas não encontrado


            exit(1)


        config = loaded_config





    # 3. Analisador principal com padrões do arquivo de configuração


    # A ajuda é formatada para mostrar os padrões (que podem vir do config).


    parser = argparse.ArgumentParser(


        description="Reordena issues filhas de um Épico, Story ou Tarefa no Jira. "


                    "Argumentos passados na linha de comando sobrescrevem os valores do arquivo de configuração.",


        formatter_class=argparse.ArgumentDefaultsHelpFormatter


    )


    


    parser.add_argument(


        '-c', '--config', 


        type=str, 


        default=pre_args.config,


        help='Caminho para o arquivo de configuração JSON.'


    )


    parser.add_argument(


        '--parent-key',


        type=str,


        default=config.get('parent-key'),


        help='Chave da issue pai. Pode ser definida no arquivo de configuração.'


    )


    parser.add_argument(


        '--rank-by',


        type=list_of_str,


        default=config.get('rank-by'),


        help="Critérios de ordenação (separados por vírgula). Pode ser definido no arquivo de configuração."


    )


    parser.add_argument(


        '--order',


        type=list_of_str,


        default=config.get('order', ['asc']),


        help="Ordem para cada critério em --rank-by (asc/desc). Pode ser definido no arquivo de configuração."


    )


    parser.add_argument(


        '--status-order',


        type=list_of_str,


        default=config.get('status-order'),


        help="Ordem customizada para status. Pode ser definida no arquivo de configuração."


    )


    parser.add_argument(


        '--issuetype-order',


        type=list_of_str,


        default=config.get('issuetype-order'),


        help="Ordem customizada para tipo de issue. Pode ser definida no arquivo de configuração."


    )


    parser.add_argument(


        '--dry-run',


        action='store_true',


        help='Exibe a nova ordem sem aplicá-la no Jira.'


    )


    parser.add_argument(


        '--debug',


        action='store_true',


        help='Ativa a saída de depuração detalhada para a lógica de ordenação.'


    )





    args = parser.parse_args()





    # --- Validação Pós-Análise ---





    if not args.config:


        print("Erro: O arquivo de configuração ('-c' ou '--config') é obrigatório.")


        exit(1)


        


    if not args.parent_key:


        print("Erro: '--parent-key' é obrigatório (via linha de comando ou no config.json).")


        exit(1)





    if not args.rank_by:


        print("Erro: '--rank-by' é obrigatório (via linha de comando ou no config.json).")


        exit(1)


    


    valid_criteria = {'created', 'updated', 'resolutiondate', 'priority', 'key', 'status', 'issuetype'}


    for criterion in args.rank_by:


        if criterion not in valid_criteria:


            print(f"Erro: Critério de ordenação inválido '{criterion}'. Válidos são: {', '.join(sorted(list(valid_criteria)))}")


            exit(1)





    # --- Conexão e Execução ---


    


    token = config.get("jira_token")


    if not token or "YOUR_JIRA_API_TOKEN" in token:


        print("Erro: Token do Jira ('jira_token') não encontrado ou não configurado no arquivo de configuração.")


        exit(1)


        


    server = config.get("jira_server")


    if not server:


        print("Erro: URL do servidor Jira ('jira_server') não encontrada no arquivo de configuração.")


        exit(1)





    try:


        print("Conectando ao Jira...")


        jira_client = JIRA(


            server=server,


            options={'headers': {'Authorization': f'Bearer {token}'}}


        )


        print("Conectado com sucesso.")


        


        rank_child_issues(


            jira_client, 


            args.parent_key, 


            args.rank_by, 


            args.order, 


            args.dry_run, 


            args.debug, 


            status_order=args.status_order, 


            issuetype_order=args.issuetype_order


        )





    except Exception as e:


        print(f"Ocorreu um erro ao conectar ou executar a reordenação no Jira: {e}")


        exit(1)

