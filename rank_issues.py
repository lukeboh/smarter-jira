import argparse
import json
import os
import traceback
import time
from functools import cmp_to_key
from jira import JIRA, JIRAError


def check_and_handle_401(e):
    """Verifica se a exceção é um erro 401 (Não Autorizado) do Jira e encerra com mensagem amigável."""
    is_401 = False
    if isinstance(e, JIRAError) and e.status_code == 401:
        is_401 = True
    elif "401" in str(e):
        is_401 = True

    if is_401:
        print("\nErro: O token do Jira fornecido não é mais válido (Erro HTTP 401 - Não Autorizado).")
        print("Por favor, verifique se o 'jira_token' no seu arquivo de configuração está correto e ativo.")
        exit(1)



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
            if field.get('name') == 'Rank':
                return field.get('id')
    except Exception as e:
        check_and_handle_401(e)
        print(f"Aviso: Não foi possível descobrir o ID do campo 'Rank'. Erro: {e}")
    return None


def rank_child_issues(client, parent_key, rank_by_list, order_list, dry_run=False, debug=False, status_order=None, issuetype_order=None, brief=False):
    """Busca, ordena e, opcionalmente, reordena as issues filhas de uma issue pai."""
    if not rank_by_list:
        print(f"Erro: parâmetro 'rank_by_list' vazio para {parent_key}. Pulando.")
        return 0, 0
    if isinstance(rank_by_list, str):
        rank_by_list = [s.strip() for s in rank_by_list.split(',')]
    if not order_list:
        order_list = ['asc']

    try:
        verbose = not brief
        if verbose:
            print(f"\n--- Processando issue pai: {parent_key} ---")
        parent_issue = client.issue(parent_key, fields="issuetype")
        if verbose:
            print(f"Buscando a issue pai '{parent_key}' para determinar o tipo...")
            print(f"Issue pai encontrada. Tipo: {parent_issue.fields.issuetype.name}")
    except Exception as e:
        check_and_handle_401(e)
        print(f"Erro: Não foi possível encontrar a issue pai '{parent_key}'. Pulando.")
        if debug:
            print(traceback.format_exc())
        return 0, 0

    rank_field_id = get_rank_field_id(client)

    # tentar descobrir o campo 'Epic Link' para suportar ordenação por épico
    epic_field_id = None
    try:
        all_fields = client.fields()
        for field in all_fields:
            if field.get('name') == 'Epic Link':
                epic_field_id = field.get('id')
                break
    except Exception as e:
        check_and_handle_401(e)
        epic_field_id = None

    if parent_issue.fields.issuetype.name in ['Epic', 'Épico']:
        jql = f"'Epic Link' = '{parent_key}' ORDER BY Rank ASC"
    else:
        jql = f"parent = '{parent_key}' ORDER BY Rank ASC"

    if verbose:
        print(f"Buscando issues filhas com JQL: {jql}")

    try:
        fields_to_fetch = set(rank_by_list)
        fields_to_fetch.update(['priority', 'status', 'issuetype'])
        if rank_field_id:
            fields_to_fetch.add(rank_field_id)
        # Se 'epic' for critério, troque pelo ID real do campo (quando disponível)
        if 'epic' in fields_to_fetch and epic_field_id:
            fields_to_fetch.discard('epic')
            fields_to_fetch.add(epic_field_id)

        child_issues = client.search_issues(jql, maxResults=False, fields=list(fields_to_fetch))
    except Exception as e:
        check_and_handle_401(e)
        print(f"Erro ao executar a busca por issues filhas para '{parent_key}': {e}")
        if debug:
            print(traceback.format_exc())
        return 0, 0

    if not child_issues:
        if brief:
            print(f"{parent_key}: nenhuma ordenação necessária.")
        else:
            print("Nenhuma issue filha encontrada para reordenar.")
        return 0, 0

    if verbose:
        print(f"Encontradas {len(child_issues)} issues filhas.")

    current_order_keys = [issue.key for issue in child_issues]

    if len(order_list) == 1 and len(rank_by_list) > 1:
        order_list = order_list * len(rank_by_list)
    elif len(order_list) != len(rank_by_list):
        print(f"Erro: O número de critérios de ordenação ({len(rank_by_list)}) não corresponde ao número de direções ({len(order_list)}).")
        return len(child_issues), 0

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
            try:
                return int(issue.fields.priority.id)
            except Exception:
                return None
        if criterion == 'status':
            try:
                if status_order_lower:
                    status_name = issue.fields.status.name.lower()
                    try:
                        return status_order_lower.index(status_name)
                    except ValueError:
                        return len(status_order_lower)
                category_id_map = {2: 0, 4: 1, 3: 2}
                category_id = int(issue.fields.status.statusCategory.id)
                return category_id_map.get(category_id, 99)
            except Exception:
                return None
        if criterion == 'issuetype':
            try:
                if issuetype_order_lower:
                    issuetype_name = issue.fields.issuetype.name.lower()
                    try:
                        return issuetype_order_lower.index(issuetype_name)
                    except ValueError:
                        return len(issuetype_order_lower)
                return issue.fields.issuetype.name
            except Exception:
                return None
        if criterion == 'summary':
            try:
                return (issue.fields.summary or '').strip().lower()
            except Exception:
                return None

        if criterion == 'epic':
            try:
                # Tenta vários acessos para obter a chave do épico
                if epic_field_id:
                    # campo customizado retorna a chave do épico em muitas instâncias
                    val = issue.raw.get('fields', {}).get(epic_field_id)
                    if val:
                        return val
                # fallback para 'epic' ou 'Epic Link' direto nos fields
                if hasattr(issue.fields, 'epic'):
                    return getattr(issue.fields, 'epic')
                if hasattr(issue.fields, 'Epic'):
                    return getattr(issue.fields, 'Epic')
                # última tentativa: procurar por qualquer campo que contenha 'epic' no nome
                for k, v in (issue.raw.get('fields') or {}).items():
                    if k and 'epic' in k.lower():
                        return v
            except Exception:
                return None

        return getattr(issue.fields, criterion, None)

    def compare_issues(issue1, issue2):
        if debug:
            print(f"\n--- Comparando {issue1.key} e {issue2.key} ---")
        for i, criterion in enumerate(rank_by_list):
            val1 = get_value_for_criterion(issue1, criterion)
            val2 = get_value_for_criterion(issue2, criterion)
            order = order_list[i]

            if debug:
                print(f"  Critério '{criterion}' (ordem: {order}): val1={val1}, val2={val2}")

            if val1 is None and val2 is not None:
                return 1
            if val1 is not None and val2 is None:
                return -1
            if val1 is None and val2 is None:
                if debug:
                    print("  > Ambos nulos. Empate.")
                continue

            try:
                if val1 < val2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        print(f"  > {val1} < {val2}. Resultado: {result}")
                    return result
                if val1 > val2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        print(f"  > {val1} > {val2}. Resultado: {result}")
                    return result
            except TypeError:
                s1 = str(val1)
                s2 = str(val2)
                if s1 < s2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        print(f"  > {s1} < {s2}. Resultado: {result}")
                    return result
                if s1 > s2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        print(f"  > {s1} > {s2}. Resultado: {result}")
                    return result

            if debug:
                print("  > Iguais. Empate, próximo critério.")
        if debug:
            print("--- Fim da Comparação: Iguais ---")
        return 0

    try:
        sorted_child_issues = sorted(child_issues, key=cmp_to_key(compare_issues))
        if verbose:
            print(f"\nIssues ordenadas com sucesso por: {', '.join(rank_by_list)}.")
    except Exception as e:
        print(f"Erro inesperado ao ordenar as issues em memória: {e}")
        if debug:
            print(traceback.format_exc())
        return len(child_issues), 0

    proposed_order_keys = [issue.key for issue in sorted_child_issues]

    if current_order_keys == proposed_order_keys:
        if brief:
            print(f"{parent_key}: nenhuma ordenação necessária.")
        else:
            print("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")
        return len(child_issues), 0

    if brief and dry_run:
        # Modo sucinto em dry-run: contar e retornar sem aplicar mudanças
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        print(f"{parent_key}: {len(sorted_child_issues)} filhas ordenadas.")
        return len(sorted_child_issues), moved

    # Impressão detalhada (não-brief)
    if not brief:
        print("\n--- Ordem Proposta (Final) ---")
        for issue in sorted_child_issues:
            rank_value = getattr(issue.fields, rank_field_id, 'N/A') if rank_field_id else 'N/A'
            print(f"  - {issue.key} (Rank atual: {rank_value})")
        print("----------------------------")

    if dry_run:
        if verbose:
            print("\nMODO DRY-RUN ATIVADO. Nenhuma alteração será aplicada no Jira.")
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        return len(sorted_child_issues), moved

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
            if debug or verbose:
                print(f"    -> API response: {response.status_code} {response.reason}")

            previous_issue_key = current_issue_key

    except Exception as e:
        check_and_handle_401(e)
        print("\nOcorreu um erro durante a reordenação via API do Jira.")
        print("É possível que a ordenação tenha sido parcialmente aplicada.")
        print(f"Erro: {e}")
        if debug:
            print(traceback.format_exc())
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        return len(sorted_child_issues), moved

    print("\nReordenação concluída com sucesso!")
    moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
    if brief:
        # Em modo breve, apenas uma linha resumo por épico
        print(f"{parent_key}: {len(sorted_child_issues)} filhas ordenadas.")
    return len(sorted_child_issues), moved


def rank_issues_collection(client, label, issues, rank_by_list, order_list, dry_run=False, debug=False, status_order=None, issuetype_order=None, epic_order=None, brief=False):
    """Ordena e opcionalmente aplica ordenação para uma coleção arbitrária de issues."""
    if not rank_by_list:
        print(f"Erro: parâmetro 'rank_by_list' vazio para {label}. Pulando.")
        return 0, 0
    if isinstance(rank_by_list, str):
        rank_by_list = [s.strip() for s in rank_by_list.split(',')]
    if not order_list:
        order_list = ['asc']

    verbose = not brief
    if verbose:
        print(f"\n--- Processando coleção: {label} (issues: {len(issues)}) ---")

    rank_field_id = get_rank_field_id(client)

    # descobrir epic field id se necessário
    epic_field_id = None
    try:
        all_fields = client.fields()
        for field in all_fields:
            if field.get('name') == 'Epic Link':
                epic_field_id = field.get('id')
                break
    except Exception as e:
        check_and_handle_401(e)
        epic_field_id = None

    current_order_keys = [issue.key for issue in issues]

    if len(order_list) == 1 and len(rank_by_list) > 1:
        order_list = order_list * len(rank_by_list)
    elif len(order_list) != len(rank_by_list):
        print(f"Erro: O número de critérios de ordenação ({len(rank_by_list)}) não corresponde ao número de direções ({len(order_list)}).")
        return len(issues), 0

    status_order_lower = [s.lower() for s in status_order] if status_order else None
    issuetype_order_lower = [s.lower() for s in issuetype_order] if issuetype_order else None
    epic_order_list = epic_order or []

    def get_value_for_criterion(issue, criterion):
        if criterion == 'key':
            try:
                prefix, number = issue.key.rsplit('-', 1)
                return (prefix, int(number))
            except (ValueError, TypeError):
                return (issue.key, 0)
        if criterion == 'priority':
            try:
                return int(issue.fields.priority.id)
            except Exception:
                return None
        if criterion == 'status':
            try:
                if status_order_lower:
                    status_name = issue.fields.status.name.lower()
                    try:
                        return status_order_lower.index(status_name)
                    except ValueError:
                        return len(status_order_lower)
                category_id_map = {2: 0, 4: 1, 3: 2}
                category_id = int(issue.fields.status.statusCategory.id)
                return category_id_map.get(category_id, 99)
            except Exception:
                return None
        if criterion == 'issuetype':
            try:
                if issuetype_order_lower:
                    issuetype_name = issue.fields.issuetype.name.lower()
                    try:
                        return issuetype_order_lower.index(issuetype_name)
                    except ValueError:
                        return len(issuetype_order_lower)
                return issue.fields.issuetype.name
            except Exception:
                return None
        if criterion == 'summary':
            try:
                return (issue.fields.summary or '').strip().lower()
            except Exception:
                return None

        if criterion == 'epic':
            try:
                epic_val = None
                if epic_field_id:
                    epic_val = issue.raw.get('fields', {}).get(epic_field_id)
                if not epic_val:
                    # tentar atributos padrões
                    if hasattr(issue.fields, 'epic'):
                        epic_val = getattr(issue.fields, 'epic')
                if epic_val:
                    ev = str(epic_val)
                    if epic_order_list:
                        try:
                            return epic_order_list.index(ev)
                        except ValueError:
                            return len(epic_order_list)
                    return ev
                return None
            except Exception:
                return None

        return getattr(issue.fields, criterion, None)

    def compare_issues(issue1, issue2):
        if debug:
            print(f"\n--- Comparando {issue1.key} e {issue2.key} ---")
        for i, criterion in enumerate(rank_by_list):
            val1 = get_value_for_criterion(issue1, criterion)
            val2 = get_value_for_criterion(issue2, criterion)
            order = order_list[i]

            if debug:
                print(f"  Critério '{criterion}' (ordem: {order}): val1={val1}, val2={val2}")

            if val1 is None and val2 is not None:
                return 1
            if val1 is not None and val2 is None:
                return -1
            if val1 is None and val2 is None:
                if debug:
                    print("  > Ambos nulos. Empate.")
                continue

            try:
                if val1 < val2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        print(f"  > {val1} < {val2}. Resultado: {result}")
                    return result
                if val1 > val2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        print(f"  > {val1} > {val2}. Resultado: {result}")
                    return result
            except TypeError:
                s1 = str(val1)
                s2 = str(val2)
                if s1 < s2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        print(f"  > {s1} < {s2}. Resultado: {result}")
                    return result
                if s1 > s2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        print(f"  > {s1} > {s2}. Resultado: {result}")
                    return result

            if debug:
                print("  > Iguais. Empate, próximo critério.")
        if debug:
            print("--- Fim da Comparação: Iguais ---")
        return 0

    try:
        sorted_issues = sorted(issues, key=cmp_to_key(compare_issues))
        if verbose:
            print(f"\nIssues ordenadas com sucesso por: {', '.join(rank_by_list)}.")
    except Exception as e:
        print(f"Erro inesperado ao ordenar as issues em memória: {e}")
        if debug:
            print(traceback.format_exc())
        return len(issues), 0

    proposed_order_keys = [issue.key for issue in sorted_issues]

    if current_order_keys == proposed_order_keys:
        if brief:
            print(f"{label}: nenhuma ordenação necessária.")
        else:
            print("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")
        return len(issues), 0

    if brief and dry_run:
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        print(f"{label}: {len(sorted_issues)} issues ordenadas.")
        return len(sorted_issues), moved

    if not brief:
        print("\n--- Ordem Proposta (Final) ---")
        # Exibir para cada issue: chave, epic link e destino da movimentação proposta
        for idx, issue in enumerate(sorted_issues):
            # rank atual
            rank_value = getattr(issue.fields, rank_field_id, 'N/A') if rank_field_id else 'N/A'
            # tentar obter epic link bruto para exibição
            epic_display = None
            try:
                if epic_field_id:
                    epic_display = issue.raw.get('fields', {}).get(epic_field_id)
                if not epic_display and hasattr(issue.fields, 'epic'):
                    epic_display = getattr(issue.fields, 'epic')
                if not epic_display and hasattr(issue.fields, 'Epic'):
                    epic_display = getattr(issue.fields, 'Epic')
                if not epic_display:
                    for k, v in (issue.raw.get('fields') or {}).items():
                        if k and 'epic' in k.lower():
                            epic_display = v
                            break
                if epic_display is None:
                    epic_display = 'N/A'
            except Exception:
                epic_display = 'N/A'

            # destino proposto: depois do anterior na lista ordenada
            if idx == 0:
                dest = 'TOP'
            else:
                dest = sorted_issues[idx - 1].key

            # posição atual (se conhecida)
            try:
                current_pos = current_order_keys.index(issue.key) + 1
            except ValueError:
                current_pos = 'N/A'

            print(f"  - {issue.key} (Epic: {epic_display}) -> after: {dest} (current pos: {current_pos}, Rank atual: {rank_value})")
        print("----------------------------")

    if dry_run:
        if verbose:
            print("\nMODO DRY-RUN ATIVADO. Nenhuma alteração será aplicada no Jira.")
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        return len(sorted_issues), moved

    print("\nIniciando o processo de reordenação no Jira (isso pode levar um tempo)...")

    try:
        server_url = client._options['server'].rstrip('/')
        rank_url = f"{server_url}/rest/agile/1.0/issue/rank"

        previous_issue_key = sorted_issues[0].key
        for i in range(1, len(sorted_issues)):
            current_issue_key = sorted_issues[i].key
            print(f"  - Movendo '{current_issue_key}' para depois de '{previous_issue_key}'...")

            payload = {
                "issues": [current_issue_key],
                "rankAfterIssue": previous_issue_key
            }
            response = client._session.put(rank_url, json=payload)
            response.raise_for_status()
            if debug or verbose:
                print(f"    -> API response: {response.status_code} {response.reason}")

            previous_issue_key = current_issue_key

    except Exception as e:
        check_and_handle_401(e)
        print("\nOcorreu um erro durante a reordenação via API do Jira.")
        print("É possível que a ordenação tenha sido parcialmente aplicada.")
        print(f"Erro: {e}")
        if debug:
            print(traceback.format_exc())
        moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
        return len(sorted_issues), moved

    print("\nReordenação concluída com sucesso!")
    moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
    if brief:
        print(f"{label}: {len(sorted_issues)} issues ordenadas.")
    return len(sorted_issues), moved


if __name__ == "__main__":

    def list_of_str(arg):
        if arg is None:
            return None
        return [s.strip() for s in arg.split(',')]

    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('-c', '--config', type=str, help='Caminho para o arquivo de configuração JSON.')
    pre_args, _ = pre_parser.parse_known_args()

    config = {}
    if pre_args.config:
        loaded_config = load_config(pre_args.config)
        if loaded_config is None:
            exit(1)
        config = loaded_config

    parser = argparse.ArgumentParser(
        description=(
            "Reordena issues filhas de um Épico/Story/Tarefa ou de todos os Épicos de um projeto no Jira. "
            "Argumentos passados na linha de comando sobrescrevem os valores do arquivo de configuração.\n"
            "Use `--dry-run` para testar, `--brief` para saída sucinta e `--debug` para logs detalhados."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('-c', '--config', type=str, default=pre_args.config, help='Caminho para o arquivo de configuração JSON.')

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--parent-key', type=str, default=None, help='Chave da issue pai (Épico, Story, etc.) para ordenar suas filhas. Tem prioridade sobre project-id no config.')
    group.add_argument('--project-id', type=str, default=None, help='ID do Projeto para ordenar as issues de TODOS os seus Épicos. Usado somente se --parent-key não for fornecido na linha de comando.')
    group.add_argument('--sprint', type=list_of_str, default=None, help='Nome(s) da(s) Sprint(s) para ordenar todas as issues. Aceita múltiplos valores separados por vírgula.')

    parser.add_argument('--rank-by', type=list_of_str, default=config.get('rank-by'), help="Critérios de ordenação (separados por vírgula). Ex: --rank-by status,issuetype,resolutiondate")
    parser.add_argument('--order', type=list_of_str, default=config.get('order', ['asc']), help="Ordem para cada critério em --rank-by (asc/desc).")
    parser.add_argument('--status-order', type=list_of_str, default=config.get('status-order'), help="Ordem customizada para status.")
    parser.add_argument('--issuetype-order', type=list_of_str, default=config.get('issuetype-order'), help="Ordem customizada para tipo de issue.")
    parser.add_argument('--dry-run', action='store_true', help='Exibe a nova ordem sem aplicá-la no Jira.')
    parser.add_argument('--debug', action='store_true', help='Ativa a saída de depuração detalhada para a lógica de ordenação.')
    parser.add_argument('--brief', action='store_true', help='Saída sucinta: para cada épico imprime apenas uma linha resumo sobre a ordenação (útil para logs).')
    parser.add_argument('--epic-order', type=list_of_str, default=config.get('epic-order'), help='Lista de chaves de épicos definindo ordem customizada por épicos. Ex: --epic-order ABC-1,ABC-2')

    args = parser.parse_args()

    start_time = time.time()

    parent_key = args.parent_key if args.parent_key is not None else config.get('parent-key')
    project_id = args.project_id if args.project_id is not None else config.get('project-id')
    sprint = args.sprint if args.sprint is not None else config.get('sprint')
    if args.parent_key is not None:
        project_id = None
    if args.sprint is not None:
        # CLI sprint explicit -> override parent/project
        parent_key = None
        project_id = None

    # Normaliza sprint para uma lista de strings
    sprint_list = []
    if sprint:
        if isinstance(sprint, list):
            sprint_list = [str(s).strip() for s in sprint if str(s).strip()]
        elif isinstance(sprint, str):
            sprint_list = [s.strip() for s in sprint.split(',') if s.strip()]
        else:
            sprint_list = [str(sprint).strip()]

    if not args.config:
        print("Erro: O arquivo de configuração ('-c' ou '--config') é obrigatório.")
        exit(1)

    if not parent_key and not project_id and not sprint_list:
        print("Erro: Especifique '--parent-key' para ordenar um item, '--project-id' para ordenar todos os épicos de um projeto, ou '--sprint' para ordenar uma sprint.")
        exit(1)

    if not args.rank_by:
        print("Erro: '--rank-by' é obrigatório (via linha de comando ou no config.json).")
        exit(1)

    valid_criteria = {'created', 'updated', 'resolutiondate', 'priority', 'key', 'status', 'issuetype'}
    # adicionar novos critérios
    valid_criteria.add('epic')
    valid_criteria.add('summary')
    for criterion in args.rank_by:
        if criterion not in valid_criteria:
            print(f"Erro: Critério de ordenação inválido '{criterion}'. Válidos são: {', '.join(sorted(list(valid_criteria)))}")
            exit(1)

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
            options={'headers': {'Authorization': f'Bearer {token}'}},
        )
        try:
            jira_client._session.headers.update({'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
        except Exception:
            pass
        print("Conectado com sucesso.")

        if project_id:
            print(f"Modo de Projeto ativado para '{project_id}'. Buscando todos os épicos...")
            jql_epics = f'project = "{project_id}" AND issuetype = Epic ORDER BY key ASC'

            # Tentar primeiro sem 'fields' — em algumas versões do client passar 'fields'
            # pode causar erros internos ('NoneType' is not iterable').
            epics = None
            try:
                epics = jira_client.search_issues(jql_epics, maxResults=False)
            except Exception:
                try:
                    epics = jira_client.search_issues(jql_epics, maxResults=False, fields=['key'])
                except Exception:
                    try:
                        epics = jira_client.search_issues(jql_epics, maxResults=False, fields="key")
                    except Exception as e:
                        print(f"Erro ao buscar épicos (todos os fallbacks falharam): {e}")
                        epics = None

            if epics:
                epics = [e for e in epics if getattr(e, 'raw', None) is not None]
            if not epics:
                print(f"Nenhum épico encontrado no projeto '{project_id}'.")
            else:
                print(f"Encontrados {len(epics)} épicos. Processando cada um...")
                epics_processed = 0
                total_children_analyzed = 0
                total_children_reordered = 0
                for epic in epics:
                    epics_processed += 1
                    children, moved = rank_child_issues(
                        jira_client,
                        epic.key,
                        args.rank_by,
                        args.order,
                        args.dry_run,
                        args.debug,
                        args.status_order,
                        args.issuetype_order,
                        brief=args.brief,
                    )
                    total_children_analyzed += children
                    total_children_reordered += moved
                print(f"\nResumo: Épicos processados: {epics_processed}; Filhos analisados: {total_children_analyzed}; Filhos reordenados (ou que mudariam): {total_children_reordered}")
        elif sprint_list:
            sprint_name = ", ".join(sprint_list)
            print(f"Modo de Sprint ativado para '{sprint_name}'. Buscando issues na(s) sprint(s)...")
            
            # Constrói a cláusula JQL escapando aspas duplas dos nomes de sprints
            escaped_sprints = [s.replace('"', '\\"') for s in sprint_list]
            if len(escaped_sprints) == 1:
                sprint_clause = f'sprint = "{escaped_sprints[0]}"'
            else:
                sprint_clause = 'sprint IN (' + ', '.join([f'"{s}"' for s in escaped_sprints]) + ')'

            # tipos de issue relevantes por padrão: Story, Bug, Task
            # Acrescentar variações conhecidas ('Bug Setot') e 'Melhoria' conforme instância local.
            # Observação: instâncias Jira podem ter nomes diferentes; há fallback para filtrar tipos inválidos.
            issuetypes = ['Story', 'Bug', 'Task', 'Bug Setot', 'Melhoria']
            jql_types = ','.join([f'"{t}"' for t in issuetypes])
            jql_sprint = f'{sprint_clause} AND issuetype IN ({jql_types}) ORDER BY Rank ASC'
            try:
                # detectar epic field id para incluir nos fields quando necessário
                epic_field_id = None
                try:
                    all_fields = jira_client.fields()
                    for field in all_fields:
                        if field.get('name') == 'Epic Link':
                            epic_field_id = field.get('id')
                            break
                except Exception:
                    epic_field_id = None

                fields_to_fetch = set(args.rank_by)
                fields_to_fetch.update(['priority', 'status', 'issuetype'])
                rank_field_id = get_rank_field_id(jira_client)
                if rank_field_id:
                    fields_to_fetch.add(rank_field_id)
                if 'epic' in fields_to_fetch and epic_field_id:
                    fields_to_fetch.discard('epic')
                    fields_to_fetch.add(epic_field_id)

                try:
                    issues = jira_client.search_issues(jql_sprint, maxResults=False, fields=list(fields_to_fetch))
                except Exception as e:
                    # Se o erro for devido a issuetype inválido, tentar filtrar pelos tipos existentes
                    msg = str(e)
                    if 'issuetype' in msg.lower() or 'não existe' in msg.lower() or 'does not exist' in msg.lower():
                        try:
                            available_types = [it.name for it in jira_client.issue_types()]
                        except Exception:
                            available_types = []
                        valid_issuetypes = [t for t in issuetypes if t in available_types]
                        if valid_issuetypes:
                            jql_types = ','.join([f'"{t}"' for t in valid_issuetypes])
                            jql_sprint = f'{sprint_clause} AND issuetype IN ({jql_types}) ORDER BY Rank ASC'
                        else:
                            jql_sprint = f'{sprint_clause} ORDER BY Rank ASC'
                        try:
                            issues = jira_client.search_issues(jql_sprint, maxResults=False, fields=list(fields_to_fetch))
                        except Exception as e2:
                            print(f"Erro ao buscar issues da(s) sprint(s) '{sprint_name}' após ajuste dos tipos: {e2}")
                            issues = None
                    else:
                        print(f"Erro ao buscar issues da(s) sprint(s) '{sprint_name}': {e}")
                        issues = None
            except Exception as e:
                print(f"Erro ao preparar busca de issues da(s) sprint(s) '{sprint_name}': {e}")
                issues = None

            if not issues:
                print(f"Nenhuma issue encontrada na sprint '{sprint_name}'.")
            else:
                print(f"Encontradas {len(issues)} issues na sprint. Processando ordenação...")
                children, moved = rank_issues_collection(
                    jira_client,
                    f"Sprint: {sprint_name}",
                    issues,
                    args.rank_by,
                    args.order,
                    args.dry_run,
                    args.debug,
                    args.status_order,
                    args.issuetype_order,
                    epic_order=args.epic_order,
                    brief=args.brief,
                )
                print(f"\nResumo: Sprint processada: 1; Issues analisadas: {children}; Issues reordenadas (ou que mudariam): {moved}")
        else:
            children, moved = rank_child_issues(
                jira_client,
                parent_key,
                args.rank_by,
                args.order,
                args.dry_run,
                args.debug,
                status_order=args.status_order,
                issuetype_order=args.issuetype_order,
                brief=args.brief,
            )
            print(f"\nResumo: Épicos processados: 1; Filhos analisados: {children}; Filhos reordenados (ou que mudariam): {moved}")

    except Exception as e:
        check_and_handle_401(e)
        print(f"Ocorreu um erro ao conectar ou executar a reordenação no Jira: {e}")
        print(traceback.format_exc())
        exit(1)
    finally:
        elapsed = time.time() - start_time
        print(f"\nTempo total de execução: {elapsed:.2f} segundos")
