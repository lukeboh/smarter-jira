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

def generate_report(issues, config, show_as_percent=False, output_file=None, show_roles=False):
    """Gera um relatório em formato de tabela a partir das issues."""
    
    components_str = config.get('components_to_track', '')
    tracked_components_ordered = [comp.strip() for comp in components_str.split(',') if comp.strip()]
    
    role_mappings = {}
    if show_roles:
        role_mappings = {k.replace('role.', '', 1): v for k, v in config.items() if k.startswith('role.')}

    unconfigured_users = set()
    data = []
    for issue in issues:
        assignee = "Não atribuído"
        if issue.fields.assignee:
            assignee = issue.fields.assignee.displayName

        report_identity = assignee
        if show_roles:
            role = role_mappings.get(assignee)
            if role:
                report_identity = role
            elif assignee != "Não atribuído":
                report_identity = f"*{assignee}"
                unconfigured_users.add(assignee)

        if not tracked_components_ordered:
            if not issue.fields.components:
                data.append({"original_assignee": assignee, "responsavel": report_identity, "componente": "Sem Componente"})
            else:
                for c in issue.fields.components:
                    data.append({"original_assignee": assignee, "responsavel": report_identity, "componente": c.name})
            continue

        assigned_category = "Outros Componentes"
        if issue.fields.components:
            issue_components_set = {c.name for c in issue.fields.components}
            for tracked_comp in tracked_components_ordered:
                if tracked_comp in issue_components_set:
                    assigned_category = tracked_comp
                    break
        
        data.append({"original_assignee": assignee, "responsavel": report_identity, "componente": assigned_category})

    if not data:
        print("Nenhuma issue concluída encontrada para o período especificado.")
        return

    df = pd.DataFrame(data)
    
    # --- Criação da Tabela de Contagem ---
    if show_roles:
        role_counts = df.groupby('responsavel')['original_assignee'].nunique()
        pivot_table = pd.crosstab(df['responsavel'], df['componente'])
        pivot_table.insert(0, 'Quant. Perfil Alocado', role_counts)
        pivot_table.index.name = 'Perfil profissional'
    else:
        pivot_table = pd.crosstab(df['responsavel'], df['componente'])

    if tracked_components_ordered:
        task_cols_ordered = [col for col in tracked_components_ordered if col in pivot_table.columns]
        if "Outros Componentes" in pivot_table.columns and "Outros Componentes" not in task_cols_ordered:
            task_cols_ordered.append("Outros Componentes")
        
        final_column_order = [col for col in pivot_table.columns if col not in task_cols_ordered] + task_cols_ordered
        pivot_table = pivot_table[final_column_order]

    task_cols = [col for col in pivot_table.columns if col != 'Quant. Perfil Alocado']
    pivot_table['Total'] = pivot_table[task_cols].sum(axis=1)
    total_row = pivot_table.sum()
    if 'Quant. Perfil Alocado' in total_row:
        total_row['Quant. Perfil Alocado'] = df['original_assignee'].nunique()
    pivot_table.loc['Total'] = total_row

    # --- Preparação das Tabelas para Exibição e Exportação ---
    
    # Tabela de Contagem está pronta em `pivot_table`
    
    # Tabela de Percentual (numérica)
    percent_df = None
    if pivot_table.loc['Total', 'Total'] > 0:
        percent_calc_df = pivot_table.drop(columns=['Quant. Perfil Alocado'], errors='ignore')
        percent_df = percent_calc_df.drop('Total').astype(float)
        row_totals = percent_df['Total']
        row_totals[row_totals == 0] = 1
        percent_df = percent_df.drop(columns='Total').div(row_totals, axis=0) * 100
        percent_df['Total'] = 100.0
        
        grand_total = percent_calc_df.loc['Total', 'Total']
        total_row_percent = (percent_calc_df.loc['Total'] / grand_total) * 100
        percent_df.loc['Total'] = total_row_percent

    # --- Exibição no Console ---
    if show_as_percent and percent_df is not None:
        # Formata a tabela de percentual para exibição, adicionando a contagem de perfis
        formatted_df = percent_df.map(lambda x: f"{x:.1f}%")
        if 'Quant. Perfil Alocado' in pivot_table.columns:
            formatted_df.insert(0, 'Quant. Perfil Alocado', pivot_table['Quant. Perfil Alocado'])
        
        print("--- Relatório de Tarefas Concluídas (Percentual) ---")
        print(formatted_df)
    else:
        print("--- Relatório de Tarefas Concluídas (Contagem) ---")
        print(pivot_table)
        
    print("-" * 70)

    if unconfigured_users:
        print("\nAviso: Foi solicitado a exibição de roles, mas os responsáveis marcados com (*) não possuem role configurada no arquivo config.")

    # --- Exportação para Excel ---
    if output_file:
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                pivot_table.to_excel(writer, sheet_name='Contagem')
                if percent_df is not None:
                    # Adiciona a coluna de contagem de volta para a exportação do Excel
                    excel_percent_df = percent_df.copy()
                    if 'Quant. Perfil Alocado' in pivot_table.columns:
                         excel_percent_df.insert(0, 'Quant. Perfil Alocado', pivot_table['Quant. Perfil Alocado'])
                    excel_percent_df.to_excel(writer, sheet_name='Percentual', float_format="%.1f")

                if show_roles and role_mappings:
                    mapping_df = pd.DataFrame(list(role_mappings.items()), columns=['Responsável', 'Perfil'])
                    mapping_df.to_excel(writer, sheet_name='Mapeamento Roles', index=False)
            print(f"\nRelatório salvo com sucesso em '{output_file}'")
        except Exception as e:
            print(f"\nErro ao salvar o arquivo Excel: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera um relatório de tarefas concluídas no Jira por responsável e componente."
    )
    # ... (argumentos permanecem os mesmos)
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
    parser.add_argument(
        '--output',
        type=str,
        help='Caminho do arquivo Excel para salvar o relatório (ex: relatorio.xlsx).'
    )
    parser.add_argument(
        '--show_roles',
        action='store_true',
        help='Agrupa o relatório por perfil (role) em vez de responsável individual.'
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
        
        generate_report(issues, config, args.percent, args.output, args.show_roles)

    except Exception as e:
        print(f"Ocorreu um erro ao conectar ao Jira ou buscar issues: {e}")
        exit(1)