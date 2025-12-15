import argparse
import json
import os
from datetime import datetime, timedelta
from calendar import monthrange

import pandas as pd
from jira import JIRA

def load_config(config_path):
    """Carrega as configurações do arquivo JSON especificado."""
    if not os.path.exists(config_path):
        print(f"Erro: Arquivo de configuração '{config_path}' não encontrado.")
        return None
    with open(config_path, 'r') as f:
        return json.load(f)

def get_issues(client, start_date, end_date, project_key):
    """Busca issues concluídas no Jira dentro de um período para um projeto."""
    
    jql_query = (
        f"project = '{project_key}' AND "
        f"status IN (FECHADO, RESOLVIDO) AND "
        f"resolved >= '{start_date}' AND resolved <= '{end_date}'"
    )
    
    print(f"Executando JQL:\n{jql_query}\n")
    
    issues = client.search_issues(jql_query, maxResults=False, fields="assignee,components,summary")
    return issues

def generate_report(issues, config, show_as_percent=False):
    """Gera um relatório em formato de tabela a partir das issues."""
    
    components_str = config.get('components_to_track', '')
    tracked_components_ordered = [comp.strip() for comp in components_str.split(',') if comp.strip()]
    
    data = []
    for issue in issues:
        assignee = "Não atribuído"
        if issue.fields.assignee:
            assignee = issue.fields.assignee.displayName

        if not tracked_components_ordered:
            if not issue.fields.components:
                data.append({"responsavel": assignee, "componente": "Sem Componente"})
            else:
                for c in issue.fields.components:
                    data.append({"responsavel": assignee, "componente": c.name})
            continue

        assigned_category = "Outros Componentes"
        if issue.fields.components:
            issue_components_set = {c.name for c in issue.fields.components}
            for tracked_comp in tracked_components_ordered:
                if tracked_comp in issue_components_set:
                    assigned_category = tracked_comp
                    break
        
        data.append({"responsavel": assignee, "componente": assigned_category})

    if not data:
        print("Nenhuma issue concluída encontrada para o período especificado.")
        return

    df = pd.DataFrame(data)
    pivot_table = pd.crosstab(df['responsavel'], df['componente'])

    if tracked_components_ordered:
        final_column_order = [col for col in tracked_components_ordered if col in pivot_table.columns]
        if "Outros Componentes" in pivot_table.columns:
            final_column_order.append("Outros Componentes")
        for col in pivot_table.columns:
            if col not in final_column_order:
                final_column_order.append(col)
        pivot_table = pivot_table[final_column_order]

    pivot_table['Total'] = pivot_table.sum(axis=1)
    pivot_table.loc['Total'] = pivot_table.sum()

    if not show_as_percent:
        print("--- Relatório de Tarefas Concluídas por Responsável e Componente (Contagem) ---")
        print(pivot_table)
    else:
        # Calcula percentuais
        percent_df = pivot_table.drop('Total').astype(float) # Dropa a linha Total para não dividir por zero
        row_totals = percent_df['Total']
        
        # Evita divisão por zero se uma linha inteira for 0
        row_totals[row_totals == 0] = 1 

        percent_df = percent_df.drop(columns='Total').div(row_totals, axis=0) * 100
        percent_df['Total'] = 100.0

        # Calcula a linha de total percentual
        grand_total = pivot_table.loc['Total', 'Total']
        if grand_total > 0:
            total_row_percent = (pivot_table.loc['Total'] / grand_total) * 100
        else:
            total_row_percent = pivot_table.loc['Total'] * 0

        percent_df.loc['Total'] = total_row_percent
        
        # Formata todo o dataframe
        formatted_df = percent_df.applymap(lambda x: f"{x:.1f}%")
        
        print("--- Relatório de Tarefas Concluídas por Responsável e Componente (Percentual) ---")
        print(formatted_df)
        
    print("-" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera um relatório de tarefas concluídas no Jira por responsável e componente."
    )
    parser.add_argument(
        '-c', '--config', 
        type=str, 
        required=True, 
        help='Caminho para o arquivo de configuração JSON (ex: config.json).'
    )
    parser.add_argument(
        '--start-date', 
        type=str, 
        help='Data de início do período (formato: YYYY-MM-DD).'
    )
    parser.add_argument(
        '--end-date', 
        type=str, 
        help='Data de fim do período (formato: YYYY-MM-DD).'
    )
    parser.add_argument(
        '--month',
        type=int,
        help='Mês numérico (1-12) para gerar o relatório. Requer --year.'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Ano para gerar o relatório. Usado com --month ou para o ano inteiro.'
    )
    parser.add_argument(
        '--percent',
        action='store_true',
        help='Exibe os resultados em formato percentual em vez de contagem.'
    )

    args = parser.parse_args()

    config = load_config(args.config)
    if not config:
        exit(1)

    token = config.get("jira_token")
    if not token or "YOUR_JIRA_API_TOKEN" in token:
        print("Erro: Token do Jira não encontrado ou não configurado no arquivo de configuração JSON.")
        exit(1)

    start_date_str = ""
    end_date_str = ""

    if args.start_date and args.end_date:
        start_date_str = args.start_date
        end_date_str = args.end_date
    elif args.month and args.year:
        year = args.year
        month = args.month
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, monthrange(year, month)[1])
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
    elif args.year:
        start_date = datetime(args.year, 1, 1)
        end_date = datetime(args.year, 12, 31)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
    else:
        print("Erro: Você deve especificar um período. Use '--start-date' e '--end-date', ou '--month' e '--year'.")
        exit(1)

    print(f"Gerando relatório para o período de {start_date_str} a {end_date_str}...")

    try:
        jira_client = JIRA(
            server=config['jira_server'],
            options={
                'headers': {
                    'Authorization': f'Bearer {token}'
                }
            }
        )
        
        project_key = config.get('default_project')
        if not project_key:
            print("Erro: 'default_project' não definido no arquivo de configuração.")
            exit(1)

        issues = get_issues(jira_client, start_date_str, end_date_str, project_key)
        
        generate_report(issues, config, args.percent)

    except Exception as e:
        print(f"Ocorreu um erro ao conectar ao Jira ou buscar issues: {e}")
        exit(1)