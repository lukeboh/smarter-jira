import argparse
import json
import os
import sys
import traceback
import time
from functools import cmp_to_key
from jira import JIRA, JIRAError

# Reconfigura o encoding da saída padrão no Windows para evitar quebras por caracteres especiais
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


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
    with open(config_path, 'r', encoding='utf-8') as f:
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


def parse_sprint_info(item):
    start_date = None
    sprint_id = -1
    if isinstance(item, dict):
        start_date = item.get('startDate')
        sprint_id_val = item.get('id')
        if sprint_id_val is not None:
            try:
                sprint_id = int(sprint_id_val)
            except (ValueError, TypeError):
                pass
    elif isinstance(item, str):
        import re
        match_id = re.search(r'\bid=(\d+)\b', item)
        if match_id:
            sprint_id = int(match_id.group(1))
        else:
            match_num = re.search(r'\d+', item)
            if match_num:
                sprint_id = int(match_num.group())
        match_start = re.search(r'\bstartDate=([^,\]]+)', item)
        if match_start:
            sd = match_start.group(1).strip()
            if sd and sd.lower() != '<null>':
                start_date = sd
    else:
        try:
            start_date = getattr(item, 'startDate', None)
        except Exception:
            pass
        try:
            sprint_id_val = getattr(item, 'id', None)
            if sprint_id_val is not None:
                sprint_id = int(sprint_id_val)
        except Exception:
            pass

    if start_date is None or not isinstance(start_date, str):
        start_date = "9999-12-31"

    return (start_date, sprint_id)


def make_logger(log_buffer=None):
    """Retorna uma função de log que acumula mensagens se log_buffer for fornecido, ou imprime no console."""
    def log(*args, **kwargs):
        msg = " ".join(str(arg) for arg in args)
        if log_buffer is not None:
            log_buffer.append(msg)
        else:
            print(*args, **kwargs)
    return log


def get_issuetype_emoji(name):
    if not name:
        return "❓"
    name_lower = name.lower().strip()
    if "bug" in name_lower:
        return "🐛"
    if "melhoria" in name_lower or "improvement" in name_lower:
        return "⚡"
    if "story" in name_lower or "história" in name_lower or "historia" in name_lower:
        return "📖"
    if "task" in name_lower or "tarefa" in name_lower:
        return "📋"
    if "epic" in name_lower or "épico" in name_lower or "epico" in name_lower:
        return "👑"
    return "❓"


def get_priority_emoji(priority):
    if not priority:
        return "⚪"
    name = priority.name.lower() if hasattr(priority, 'name') else str(priority).lower()
    pid = str(priority.id) if hasattr(priority, 'id') else str(priority)
    if pid == '1' or 'highest' in name or 'crítico' in name or 'critico' in name or 'urgente' in name:
        return "🔴"
    if pid == '2' or 'high' in name or 'alta' in name:
        return "🟠"
    if pid == '3' or 'medium' in name or 'média' in name or 'media' in name:
        return "🟡"
    if pid == '4' or 'low' in name or 'baixa' in name:
        return "🟢"
    if pid == '5' or 'lowest' in name or 'muito baixa' in name:
        return "🔵"
    return "⚪"


def get_severity_emoji(severity_val):
    if not severity_val:
        return "⚪"
    val_str = severity_val.value if hasattr(severity_val, 'value') else str(severity_val)
    name = val_str.lower().strip()
    if "bloqueante" in name or "blocker" in name:
        return "🛑"
    if "crítico" in name or "critico" in name or "critical" in name:
        return "🚨"
    if "normal" in name:
        return "🟢"
    return "⚪"


def get_status_emoji(status):
    if not status:
        return "⚪"
    name = status.name.lower() if hasattr(status, 'name') else str(status).lower()
    name = name.strip()
    if "pendência" in name or "pendencia" in name or "pending" in name:
        return "⚠️"
    if "em teste" in name or "testing" in name:
        return "🧪"
    if "pronto para teste" in name or "ready for test" in name:
        return "📥"
    if "em andamento" in name or "in progress" in name:
        return "🏃"
    if "novo" in name or "new" in name:
        return "🆕"
    if "a fazer" in name or "to do" in name:
        return "📋"
    if "backlog" in name:
        return "📥"
    if "resolvido" in name or "resolved" in name:
        return "✅"
    if "homologação" in name or "homologacao" in name:
        return "🔄"
    if "fechado" in name or "closed" in name or "done" in name or "pronto" in name:
        return "🔒"
    if "cancelado" in name or "cancelled" in name or "canceled" in name:
        return "❌"
    return "ℹ️"


def format_issue_info(issue, rank_by_list, epic_field_id, severity_field_id):
    target_fields = ['issuetype', 'priority', 'severity', 'status', 'summary']
    sorting_fields = [f for f in rank_by_list if f in target_fields]
    non_sorting_fields = [f for f in target_fields if f not in sorting_fields]
    fields_order = sorting_fields + non_sorting_fields

    parts = []
    for f in fields_order:
        if f == 'issuetype':
            val = getattr(issue.fields, 'issuetype', None)
            name = val.name if val else None
            parts.append(get_issuetype_emoji(name))
        elif f == 'priority':
            val = getattr(issue.fields, 'priority', None)
            parts.append(get_priority_emoji(val))
        elif f == 'severity':
            severity_val = None
            if severity_field_id:
                severity_val = issue.raw.get('fields', {}).get(severity_field_id)
            if not severity_val:
                if hasattr(issue.fields, 'severity'):
                    severity_val = getattr(issue.fields, 'severity')
                else:
                    for k, v in (issue.raw.get('fields') or {}).items():
                        if k and 'severity' in k.lower():
                            severity_val = v
                            break
            parts.append(get_severity_emoji(severity_val))
        elif f == 'status':
            val = getattr(issue.fields, 'status', None)
            parts.append(get_status_emoji(val))
        elif f == 'summary':
            val = getattr(issue.fields, 'summary', '')
            parts.append(val if val else '')

    return " ".join(parts)


def rank_child_issues(client, parent_key, rank_by_list, order_list, dry_run=False, debug=False, status_order=None, issuetype_order=None, brief=False, epic_field_id=None, sprint_field_id=None, severity_field_id=None, severity_order=None, batch_size=50, log_buffer=None, rank_subtasks=False):
    """Busca, ordena e, opcionalmente, reordena as issues filhas de uma issue pai."""
    logger = make_logger(log_buffer)
    if not rank_by_list:
        logger(f"Erro: parâmetro 'rank_by_list' vazio para {parent_key}. Pulando.")
        return 0, 0
    if isinstance(rank_by_list, str):
        rank_by_list = [s.strip() for s in rank_by_list.split(',')]
    if not order_list:
        order_list = ['asc']

    try:
        verbose = not brief
        if verbose:
            logger(f"\n--- Processando issue pai: {parent_key} ---")
        parent_issue = client.issue(parent_key, fields="issuetype")
        if verbose:
            logger(f"Buscando a issue pai '{parent_key}' para determinar o tipo...")
            logger(f"Issue pai encontrada. Tipo: {parent_issue.fields.issuetype.name}")
    except Exception as e:
        check_and_handle_401(e)
        logger(f"Erro: Não foi possível encontrar a issue pai '{parent_key}'. Pulando.")
        if debug:
            logger(traceback.format_exc())
        return 0, 0

    rank_field_id = get_rank_field_id(client)

    # se não fornecido, tentar descobrir os campos
    if not epic_field_id or not sprint_field_id or not severity_field_id:
        try:
            all_fields = client.fields()
            if not epic_field_id:
                for field in all_fields:
                    if field.get('name') == 'Epic Link':
                        epic_field_id = field.get('id')
                        break
            if not sprint_field_id:
                for field in all_fields:
                    schema = field.get('schema', {})
                    if (field.get('name') == 'Sprint' or 
                        ('custom' in schema and 'sprint' in schema.get('custom', '').lower())):
                        sprint_field_id = field.get('id')
                        break
            if not severity_field_id:
                for field in all_fields:
                    if (field.get('name') == 'Gravidade' or 
                        field.get('name') == 'Severity'):
                        severity_field_id = field.get('id')
                        break
        except Exception as e:
            check_and_handle_401(e)

    if parent_issue.fields.issuetype.name in ['Epic', 'Épico']:
        jql = f"'Epic Link' = '{parent_key}' ORDER BY Rank ASC"
    else:
        jql = f"parent = '{parent_key}' ORDER BY Rank ASC"

    if verbose:
        print(f"Buscando issues filhas com JQL: {jql}")

    try:
        fields_to_fetch = set(rank_by_list)
        fields_to_fetch.update(['priority', 'status', 'issuetype', 'summary'])
        if rank_field_id:
            fields_to_fetch.add(rank_field_id)
        if severity_field_id:
            fields_to_fetch.add(severity_field_id)
        if rank_subtasks:
            fields_to_fetch.add('subtasks')
        # Se 'epic' for critério, troque pelo ID real do campo (quando disponível)
        if 'epic' in fields_to_fetch and epic_field_id:
            fields_to_fetch.discard('epic')
            fields_to_fetch.add(epic_field_id)
        # Se 'sprint' for critério, troque pelo ID real do campo (quando disponível)
        if 'sprint' in fields_to_fetch and sprint_field_id:
            fields_to_fetch.discard('sprint')
            fields_to_fetch.add(sprint_field_id)
        # Se 'severity' for critério, troque pelo ID real do campo (quando disponível)
        if 'severity' in fields_to_fetch:
            fields_to_fetch.discard('severity')
            if severity_field_id:
                fields_to_fetch.add(severity_field_id)

        child_issues = client.search_issues(jql, maxResults=False, fields=list(fields_to_fetch))
    except Exception as e:
        check_and_handle_401(e)
        logger(f"Erro ao executar a busca por issues filhas para '{parent_key}': {e}")
        if debug:
            logger(traceback.format_exc())
        return 0, 0

    if not child_issues:
        if brief:
            logger(f"{parent_key}: nenhuma ordenação necessária.")
        else:
            logger("Nenhuma issue filha encontrada para reordenar.")
        return 0, 0

    if verbose:
        logger(f"Encontradas {len(child_issues)} issues filhas.")

    current_order_keys = [issue.key for issue in child_issues]

    if len(order_list) == 1 and len(rank_by_list) > 1:
        order_list = order_list * len(rank_by_list)
    elif len(order_list) != len(rank_by_list):
        print(f"Erro: O número de critérios de ordenação ({len(rank_by_list)}) não corresponde ao número de direções ({len(order_list)}).")
        return len(child_issues), 0

    status_order_lower = [s.lower() for s in status_order] if status_order else None
    issuetype_order_lower = [s.lower() for s in issuetype_order] if issuetype_order else None
    severity_order_lower = [s.lower() for s in severity_order] if severity_order else None

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

        if criterion == 'sprint':
            try:
                sprint_val = None
                if sprint_field_id:
                    sprint_val = issue.raw.get('fields', {}).get(sprint_field_id)
                if not sprint_val:
                    if hasattr(issue.fields, 'sprint'):
                        sprint_val = getattr(issue.fields, 'sprint')
                    else:
                        for k, v in (issue.raw.get('fields') or {}).items():
                            if k and 'sprint' in k.lower():
                                sprint_val = v
                                break
                if sprint_val:
                    if not isinstance(sprint_val, list):
                        sprint_val = [sprint_val]
                    sprint_tuples = []
                    for item in sprint_val:
                        sprint_tuples.append(parse_sprint_info(item))
                    if sprint_tuples:
                        return max(sprint_tuples)
                return None
            except Exception:
                return None

        if criterion == 'severity':
            try:
                severity_val = None
                if severity_field_id:
                    severity_val = issue.raw.get('fields', {}).get(severity_field_id)
                if not severity_val:
                    if hasattr(issue.fields, 'severity'):
                        severity_val = getattr(issue.fields, 'severity')
                    else:
                        for k, v in (issue.raw.get('fields') or {}).items():
                            if k and 'severity' in k.lower():
                                severity_val = v
                                break
                if severity_val:
                    val_str = severity_val.value if hasattr(severity_val, 'value') else str(severity_val)
                    val_str_lower = val_str.lower().strip()
                    if severity_order_lower:
                        try:
                            return severity_order_lower.index(val_str_lower)
                        except ValueError:
                            return len(severity_order_lower)
                    default_order = ['bloqueante', 'crítico', 'critico', 'normal']
                    try:
                        return default_order.index(val_str_lower)
                    except ValueError:
                        return len(default_order)
                return None
            except Exception:
                return None

        return getattr(issue.fields, criterion, None)

    def compare_issues(issue1, issue2):
        if debug:
            logger(f"\n--- Comparando {issue1.key} e {issue2.key} ---")
        for i, criterion in enumerate(rank_by_list):
            val1 = get_value_for_criterion(issue1, criterion)
            val2 = get_value_for_criterion(issue2, criterion)
            order = order_list[i]

            if debug:
                logger(f"  Critério '{criterion}' (ordem: {order}): val1={val1}, val2={val2}")

            if val1 is None and val2 is not None:
                return 1
            if val1 is not None and val2 is None:
                return -1
            if val1 is None and val2 is None:
                if debug:
                    logger("  > Ambos nulos. Empate.")
                continue

            try:
                if val1 < val2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        logger(f"  > {val1} < {val2}. Resultado: {result}")
                    return result
                if val1 > val2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        logger(f"  > {val1} > {val2}. Resultado: {result}")
                    return result
            except TypeError:
                s1 = str(val1)
                s2 = str(val2)
                if s1 < s2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        logger(f"  > {s1} < {s2}. Resultado: {result}")
                    return result
                if s1 > s2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        logger(f"  > {s1} > {s2}. Resultado: {result}")
                    return result

            if debug:
                logger("  > Iguais. Empate, próximo critério.")
        if debug:
            logger("--- Fim da Comparação: Iguais ---")
        return 0

    try:
        sorted_child_issues = sorted(child_issues, key=cmp_to_key(compare_issues))
        if verbose:
            logger(f"\nIssues ordenadas com sucesso por: {', '.join(rank_by_list)}.")
    except Exception as e:
        logger(f"Erro inesperado ao ordenar as issues em memória: {e}")
        if debug:
            logger(traceback.format_exc())
        return len(child_issues), 0

    proposed_order_keys = [issue.key for issue in sorted_child_issues]

    if current_order_keys == proposed_order_keys:
        if not rank_subtasks:
            if brief:
                logger(f"{parent_key}: nenhuma ordenação necessária.")
            else:
                logger("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")
            return len(child_issues), 0

    moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
    needs_reordering = (moved > 0)

    if needs_reordering:
        if brief and dry_run:
            if not rank_subtasks:
                logger(f"{parent_key}: {len(sorted_child_issues)} filhas ordenadas.")
                return len(sorted_child_issues), moved

        # Impressão detalhada (não-brief)
        if not brief:
            logger("\n--- Ordem Proposta (Final) ---")
            for issue in sorted_child_issues:
                rank_value = getattr(issue.fields, rank_field_id, 'N/A') if rank_field_id else 'N/A'
                issue_info = format_issue_info(issue, rank_by_list, epic_field_id, severity_field_id)
                logger(f"  - {issue.key} | {issue_info} (Rank atual: {rank_value})")
            logger("----------------------------")

        if dry_run:
            if verbose and not brief:
                logger("\nMODO DRY-RUN ATIVADO. Nenhuma alteração será aplicada no Jira.")
        else:
            logger("\nIniciando o processo de reordenação no Jira (isso pode levar um tempo)...")
            try:
                server_url = client._options['server'].rstrip('/')
                rank_url = f"{server_url}/rest/agile/1.0/issue/rank"
                batch_size = max(1, batch_size)
                total_issues = len(sorted_child_issues)
                i = 1
                ref_issue_key = sorted_child_issues[0].key
                while i < total_issues:
                    batch_issues = sorted_child_issues[i:i + batch_size]
                    batch_keys = [issue.key for issue in batch_issues]
                    if len(batch_keys) == 1:
                        logger(f"  - Movendo '{batch_keys[0]}' para depois de '{ref_issue_key}'...")
                    else:
                        logger(f"  - Movendo lote de {len(batch_keys)} issues ({', '.join(batch_keys)}) para depois de '{ref_issue_key}'...")
                    payload = {
                        "issues": batch_keys,
                        "rankAfterIssue": ref_issue_key
                    }
                    response = client._session.put(rank_url, json=payload)
                    response.raise_for_status()
                    if debug or verbose:
                        logger(f"    -> API response: {response.status_code} {response.reason}")
                    ref_issue_key = batch_keys[-1]
                    i += batch_size
                logger("\nReordenação concluída com sucesso!")
            except Exception as e:
                check_and_handle_401(e)
                logger("\nOcorreu um erro durante a reordenação via API do Jira.")
                logger("É possível que a ordenação tenha sido parcialmente aplicada.")
                logger(f"Erro: {e}")
                if debug:
                    logger(traceback.format_exc())
    else:
        if not brief:
            logger("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")

    total_analyzed = len(sorted_child_issues)
    total_moved = moved

    if parent_issue.fields.issuetype.name in ['Epic', 'Épico'] and rank_subtasks:
        for child in sorted_child_issues:
            if hasattr(child.fields, 'subtasks') and child.fields.subtasks:
                if verbose:
                    logger(f"\n[Subtarefas] Ordenando subtarefas de {child.key}...")
                sub_analyzed, sub_moved = rank_child_issues(
                    client, child.key, rank_by_list, order_list,
                    dry_run=dry_run, debug=debug, status_order=status_order,
                    issuetype_order=issuetype_order, brief=brief,
                    epic_field_id=epic_field_id, sprint_field_id=sprint_field_id,
                    severity_field_id=severity_field_id, severity_order=severity_order,
                    batch_size=batch_size, log_buffer=log_buffer, rank_subtasks=False
                )
                total_analyzed += sub_analyzed
                total_moved += sub_moved

    if brief and (needs_reordering or rank_subtasks):
        logger(f"{parent_key}: {total_analyzed} filhas ordenadas.")
    return total_analyzed, total_moved


def rank_issues_collection(client, label, issues, rank_by_list, order_list, dry_run=False, debug=False, status_order=None, issuetype_order=None, epic_order=None, brief=False, epic_field_id=None, sprint_field_id=None, severity_field_id=None, severity_order=None, batch_size=50, log_buffer=None, rank_subtasks=False):
    """Ordena e opcionalmente aplica ordenação para uma coleção arbitrária de issues."""
    logger = make_logger(log_buffer)
    if not rank_by_list:
        logger(f"Erro: parâmetro 'rank_by_list' vazio para {label}. Pulando.")
        return 0, 0
    if isinstance(rank_by_list, str):
        rank_by_list = [s.strip() for s in rank_by_list.split(',')]
    if not order_list:
        order_list = ['asc']

    verbose = not brief
    if verbose:
        logger(f"\n--- Processando coleção: {label} (issues: {len(issues)}) ---")

    rank_field_id = get_rank_field_id(client)

    # se não fornecido, tentar descobrir os campos
    if not epic_field_id or not sprint_field_id or not severity_field_id:
        try:
            all_fields = client.fields()
            if not epic_field_id:
                for field in all_fields:
                    if field.get('name') == 'Epic Link':
                        epic_field_id = field.get('id')
                        break
            if not sprint_field_id:
                for field in all_fields:
                    schema = field.get('schema', {})
                    if (field.get('name') == 'Sprint' or 
                        ('custom' in schema and 'sprint' in schema.get('custom', '').lower())):
                        sprint_field_id = field.get('id')
                        break
            if not severity_field_id:
                for field in all_fields:
                    if (field.get('name') == 'Gravidade' or 
                        field.get('name') == 'Severity'):
                        severity_field_id = field.get('id')
                        break
        except Exception as e:
            check_and_handle_401(e)

    current_order_keys = [issue.key for issue in issues]

    if len(order_list) == 1 and len(rank_by_list) > 1:
        order_list = order_list * len(rank_by_list)
    elif len(order_list) != len(rank_by_list):
        print(f"Erro: O número de critérios de ordenação ({len(rank_by_list)}) não corresponde ao número de direções ({len(order_list)}).")
        return len(issues), 0

    status_order_lower = [s.lower() for s in status_order] if status_order else None
    issuetype_order_lower = [s.lower() for s in issuetype_order] if issuetype_order else None
    severity_order_lower = [s.lower() for s in severity_order] if severity_order else None
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

        if criterion == 'sprint':
            try:
                sprint_val = None
                if sprint_field_id:
                    sprint_val = issue.raw.get('fields', {}).get(sprint_field_id)
                if not sprint_val:
                    if hasattr(issue.fields, 'sprint'):
                        sprint_val = getattr(issue.fields, 'sprint')
                    else:
                        for k, v in (issue.raw.get('fields') or {}).items():
                            if k and 'sprint' in k.lower():
                                sprint_val = v
                                break
                if sprint_val:
                    if not isinstance(sprint_val, list):
                        sprint_val = [sprint_val]
                    sprint_tuples = []
                    for item in sprint_val:
                        sprint_tuples.append(parse_sprint_info(item))
                    if sprint_tuples:
                        return max(sprint_tuples)
                return None
            except Exception:
                return None

        if criterion == 'severity':
            try:
                severity_val = None
                if severity_field_id:
                    severity_val = issue.raw.get('fields', {}).get(severity_field_id)
                if not severity_val:
                    if hasattr(issue.fields, 'severity'):
                        severity_val = getattr(issue.fields, 'severity')
                    else:
                        for k, v in (issue.raw.get('fields') or {}).items():
                            if k and 'severity' in k.lower():
                                severity_val = v
                                break
                if severity_val:
                    val_str = severity_val.value if hasattr(severity_val, 'value') else str(severity_val)
                    val_str_lower = val_str.lower().strip()
                    if severity_order_lower:
                        try:
                            return severity_order_lower.index(val_str_lower)
                        except ValueError:
                            return len(severity_order_lower)
                    default_order = ['bloqueante', 'crítico', 'critico', 'normal']
                    try:
                        return default_order.index(val_str_lower)
                    except ValueError:
                        return len(default_order)
                return None
            except Exception:
                return None

        return getattr(issue.fields, criterion, None)

    def compare_issues(issue1, issue2):
        if debug:
            logger(f"\n--- Comparando {issue1.key} e {issue2.key} ---")
        for i, criterion in enumerate(rank_by_list):
            val1 = get_value_for_criterion(issue1, criterion)
            val2 = get_value_for_criterion(issue2, criterion)
            order = order_list[i]

            if debug:
                logger(f"  Critério '{criterion}' (ordem: {order}): val1={val1}, val2={val2}")

            if val1 is None and val2 is not None:
                return 1
            if val1 is not None and val2 is None:
                return -1
            if val1 is None and val2 is None:
                if debug:
                    logger("  > Ambos nulos. Empate.")
                continue

            try:
                if val1 < val2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        logger(f"  > {val1} < {val2}. Resultado: {result}")
                    return result
                if val1 > val2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        logger(f"  > {val1} > {val2}. Resultado: {result}")
                    return result
            except TypeError:
                s1 = str(val1)
                s2 = str(val2)
                if s1 < s2:
                    result = -1 if order == 'asc' else 1
                    if debug:
                        logger(f"  > {s1} < {s2}. Resultado: {result}")
                    return result
                if s1 > s2:
                    result = 1 if order == 'asc' else -1
                    if debug:
                        logger(f"  > {s1} > {s2}. Resultado: {result}")
                    return result

            if debug:
                logger("  > Iguais. Empate, próximo critério.")
        if debug:
            logger("--- Fim da Comparação: Iguais ---")
        return 0

    try:
        sorted_issues = sorted(issues, key=cmp_to_key(compare_issues))
        if verbose:
            logger(f"\nIssues ordenadas com sucesso por: {', '.join(rank_by_list)}.")
    except Exception as e:
        logger(f"Erro inesperado ao ordenar as issues em memória: {e}")
        if debug:
            logger(traceback.format_exc())
        return len(issues), 0

    proposed_order_keys = [issue.key for issue in sorted_issues]

    if current_order_keys == proposed_order_keys:
        if not rank_subtasks:
            if brief:
                logger(f"{label}: nenhuma ordenação necessária.")
            else:
                logger("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")
            return len(issues), 0

    moved = sum(1 for i, k in enumerate(proposed_order_keys) if current_order_keys[i] != k)
    needs_reordering = (moved > 0)

    if needs_reordering:
        if brief and dry_run:
            if not rank_subtasks:
                logger(f"{label}: {len(sorted_issues)} issues ordenadas.")
                return len(sorted_issues), moved

        if not brief:
            logger("\n--- Ordem Proposta (Final) ---")
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

                issue_info = format_issue_info(issue, rank_by_list, epic_field_id, severity_field_id)
                logger(f"  - {issue.key} | {issue_info} (Epic: {epic_display}) -> after: {dest} (current pos: {current_pos}, Rank atual: {rank_value})")
            print("----------------------------")

        if dry_run:
            if verbose and not brief:
                logger("\nMODO DRY-RUN ATIVADO. Nenhuma alteração será aplicada no Jira.")
        else:
            logger("\nIniciando o processo de reordenação no Jira (isso pode levar um tempo)...")
            try:
                server_url = client._options['server'].rstrip('/')
                rank_url = f"{server_url}/rest/agile/1.0/issue/rank"
                batch_size = max(1, batch_size)
                total_issues = len(sorted_issues)
                i = 1
                ref_issue_key = sorted_issues[0].key
                while i < total_issues:
                    batch_issues = sorted_issues[i:i + batch_size]
                    batch_keys = [issue.key for issue in batch_issues]
                    if len(batch_keys) == 1:
                        logger(f"  - Movendo '{batch_keys[0]}' para depois de '{ref_issue_key}'...")
                    else:
                        logger(f"  - Movendo lote de {len(batch_keys)} issues ({', '.join(batch_keys)}) para depois de '{ref_issue_key}'...")
                    payload = {
                        "issues": batch_keys,
                        "rankAfterIssue": ref_issue_key
                    }
                    response = client._session.put(rank_url, json=payload)
                    response.raise_for_status()
                    if debug or verbose:
                        logger(f"    -> API response: {response.status_code} {response.reason}")
                    ref_issue_key = batch_keys[-1]
                    i += batch_size
                logger("\nReordenação concluída com sucesso!")
            except Exception as e:
                check_and_handle_401(e)
                logger("\nOcorreu um erro durante a reordenação via API do Jira.")
                logger("É possível que a ordenação tenha sido parcialmente aplicada.")
                logger(f"Erro: {e}")
                if debug:
                    logger(traceback.format_exc())
    else:
        if not brief:
            logger("\nAs issues já estão na ordem desejada. Nenhuma alteração é necessária.")

    total_analyzed = len(sorted_issues)
    total_moved = moved

    if rank_subtasks:
        for issue in sorted_issues:
            if hasattr(issue.fields, 'subtasks') and issue.fields.subtasks:
                if verbose:
                    logger(f"\n[Subtarefas] Ordenando subtarefas de {issue.key}...")
                sub_analyzed, sub_moved = rank_child_issues(
                    client, issue.key, rank_by_list, order_list,
                    dry_run=dry_run, debug=debug, status_order=status_order,
                    issuetype_order=issuetype_order, brief=brief,
                    epic_field_id=epic_field_id, sprint_field_id=sprint_field_id,
                    severity_field_id=severity_field_id, severity_order=severity_order,
                    batch_size=batch_size, log_buffer=log_buffer, rank_subtasks=False
                )
                total_analyzed += sub_analyzed
                total_moved += sub_moved

    if brief and (needs_reordering or rank_subtasks):
        logger(f"{label}: {total_analyzed} issues ordenadas.")
    return total_analyzed, total_moved


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

    parser.add_argument('--rank-by', type=list_of_str, default=config.get('rank-by'), help="Critérios de ordenação (separados por vírgula). Opções: created, updated, resolutiondate, priority, key, status, issuetype, epic, summary, sprint, severity. Ex: --rank-by sprint,status")
    parser.add_argument('--order', type=list_of_str, default=config.get('order', ['asc']), help="Ordem para cada critério em --rank-by (asc/desc).")
    parser.add_argument('--status-order', type=list_of_str, default=config.get('status-order'), help="Ordem customizada para status.")
    parser.add_argument('--issuetype-order', type=list_of_str, default=config.get('issuetype-order'), help="Ordem customizada para tipo de issue.")
    parser.add_argument('--severity-order', type=list_of_str, default=config.get('severity-order'), help="Ordem customizada para severidade (severity).")
    parser.add_argument('--dry-run', action='store_true', help='Exibe a nova ordem sem aplicá-la no Jira.')
    parser.add_argument('--debug', action='store_true', help='Ativa a saída de depuração detalhada para a lógica de ordenação.')
    parser.add_argument('--brief', action='store_true', help='Saída sucinta: para cada épico imprime apenas uma linha resumo sobre a ordenação (útil para logs).')
    parser.add_argument('--epic-order', type=list_of_str, default=config.get('epic-order'), help='Lista de chaves de épicos definindo ordem customizada por épicos. Ex: --epic-order ABC-1,ABC-2')
    parser.add_argument('--batch-size', type=int, default=config.get('batch-size', 50), help="Tamanho do lote de issues para envio à API do Jira. Use 1 para desativar o loteamento.")
    parser.add_argument('--max-workers', type=int, default=config.get('max-workers', 4), help="Número máximo de threads paralelas para processamento de múltiplos épicos.")
    parser.add_argument('--rank-subtasks', action='store_true', default=config.get('rank-subtasks', False), help="Ordena também as subtarefas de cada issue encontrada.")

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
    valid_criteria.add('sprint')
    valid_criteria.add('severity')
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

        # carregar/descobrir IDs dos campos
        epic_field_id = config.get('epic_link_field_id')
        sprint_field_id = config.get('sprint_field_id')
        severity_field_id = config.get('severity_field_id')
        if not epic_field_id or not sprint_field_id or not severity_field_id:
            try:
                all_fields = jira_client.fields()
                if not epic_field_id:
                    for field in all_fields:
                        if field.get('name') == 'Epic Link':
                            epic_field_id = field.get('id')
                            break
                if not sprint_field_id:
                    for field in all_fields:
                        schema = field.get('schema', {})
                        if (field.get('name') == 'Sprint' or 
                            ('custom' in schema and 'sprint' in schema.get('custom', '').lower())):
                            sprint_field_id = field.get('id')
                            break
                if not severity_field_id:
                    for field in all_fields:
                        if (field.get('name') == 'Gravidade' or 
                            field.get('name') == 'Severity'):
                            severity_field_id = field.get('id')
                            break
            except Exception as e:
                check_and_handle_401(e)
                print(f"Aviso: Não foi possível obter informações dos campos do Jira: {e}")

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
                import concurrent.futures

                max_workers = args.max_workers
                total_children_analyzed = 0
                total_children_reordered = 0

                if max_workers is None or max_workers <= 1:
                    epics_processed = 0
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
                            epic_field_id=epic_field_id,
                            sprint_field_id=sprint_field_id,
                            severity_field_id=severity_field_id,
                            severity_order=args.severity_order,
                            batch_size=args.batch_size,
                            rank_subtasks=args.rank_subtasks,
                        )
                        total_children_analyzed += children
                        total_children_reordered += moved
                else:
                    epics_processed = len(epics)

                    def process_epic(epic):
                        log_buf = []
                        try:
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
                                epic_field_id=epic_field_id,
                                sprint_field_id=sprint_field_id,
                                severity_field_id=severity_field_id,
                                severity_order=args.severity_order,
                                batch_size=args.batch_size,
                                log_buffer=log_buf,
                                rank_subtasks=args.rank_subtasks,
                            )
                            return children, moved, log_buf, None
                        except Exception as thread_e:
                            return 0, 0, log_buf, thread_e

                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = [executor.submit(process_epic, epic) for epic in epics]
                        for future in futures:
                            children, moved, log_buf, err = future.result()
                            if log_buf:
                                print("\n".join(log_buf))
                            if err:
                                print(f"Erro ao processar épico: {err}")
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

            jql_sprint = f'{sprint_clause} AND type IN standardIssueTypes() ORDER BY Rank ASC'
            try:
                fields_to_fetch = set(args.rank_by)
                fields_to_fetch.update(['priority', 'status', 'issuetype', 'summary'])
                rank_field_id = get_rank_field_id(jira_client)
                if rank_field_id:
                    fields_to_fetch.add(rank_field_id)
                if severity_field_id:
                    fields_to_fetch.add(severity_field_id)
                if args.rank_subtasks:
                    fields_to_fetch.add('subtasks')
                if 'epic' in fields_to_fetch and epic_field_id:
                    fields_to_fetch.discard('epic')
                    fields_to_fetch.add(epic_field_id)
                if 'sprint' in fields_to_fetch and sprint_field_id:
                    fields_to_fetch.discard('sprint')
                    fields_to_fetch.add(sprint_field_id)
                if 'severity' in fields_to_fetch:
                    fields_to_fetch.discard('severity')
                    if severity_field_id:
                        fields_to_fetch.add(severity_field_id)

                try:
                    issues = jira_client.search_issues(jql_sprint, maxResults=False, fields=list(fields_to_fetch))
                except Exception as e:
                    # Se houver erro (por ex: standardIssueTypes() não suportado), fallback para buscar sem filtro
                    try:
                        jql_sprint_fallback = f'{sprint_clause} ORDER BY Rank ASC'
                        issues = jira_client.search_issues(jql_sprint_fallback, maxResults=False, fields=list(fields_to_fetch))
                        if issues:
                            # Filtrar manualmente sub-tarefas
                            issues = [issue for issue in issues if getattr(issue.fields.issuetype, 'subtask', False) is False]
                    except Exception as e2:
                        print(f"Erro ao buscar issues da(s) sprint(s) '{sprint_name}' no fallback: {e2}")
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
                    epic_field_id=epic_field_id,
                    sprint_field_id=sprint_field_id,
                    severity_field_id=severity_field_id,
                    severity_order=args.severity_order,
                    batch_size=args.batch_size,
                    rank_subtasks=args.rank_subtasks,
                )
                sprints_count = len(sprint_list)
                if sprints_count == 1:
                    print(f"\nResumo: Sprint processada: 1; Issues analisadas: {children}; Issues reordenadas (ou que mudariam): {moved}")
                else:
                    print(f"\nResumo: Sprints processadas: {sprints_count}; Issues analisadas: {children}; Issues reordenadas (ou que mudariam): {moved}")
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
                epic_field_id=epic_field_id,
                sprint_field_id=sprint_field_id,
                severity_field_id=severity_field_id,
                severity_order=args.severity_order,
                batch_size=args.batch_size,
                rank_subtasks=args.rank_subtasks,
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
