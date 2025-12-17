
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

def get_issues(client, start_date, end_date, project_key, ignore_project=False):
    """Busca issues concluídas no Jira dentro de um período."""
    
    jql_parts = []
    if not ignore_project and project_key:
        jql_parts.append(f"project = '{project_key}'")
    elif not ignore_project and not project_key:
        print("Aviso: 'default_project' não definido no config. Buscando em todos os projetos.")

    jql_parts.append("status IN (FECHADO, RESOLVIDO)")
    jql_parts.append(f"resolved >= '{start_date}'")
    jql_parts.append(f"resolved <= '{end_date}'")
    
    jql_query = " AND ".join(jql_parts)
    
    print(f"Executando JQL:\n{jql_query}\n")
    
    issues = client.search_issues(jql_query, maxResults=False, fields="assignee,components,summary")
    return issues

def _create_pivot_table(df, index_col, components_ordered):
    """Função auxiliar para criar e ordenar uma tabela pivô."""
    pivot = pd.crosstab(df[index_col], df['componente'])
    
    if components_ordered:
        final_order = [col for col in components_ordered if col in pivot.columns]
        if "Outros Componentes" in pivot.columns and "Outros Componentes" not in final_order:
            final_order.append("Outros Componentes")
        for col in pivot.columns:
            if col not in final_order:
                final_order.append(col)
        pivot = pivot[final_order]
        
    return pivot

def _calculate_percent_df(pivot_table):
    """Função auxiliar para calcular o dataframe de percentuais."""
    if pivot_table.empty or 'Total' not in pivot_table.columns or pivot_table.loc['Total', 'Total'] == 0:
        return None
        
    percent_df = pivot_table.drop('Total').astype(float)
    row_totals = percent_df['Total']
    row_totals[row_totals == 0] = 1
    
    percent_df = percent_df.drop(columns='Total').div(row_totals, axis=0) * 100
    percent_df['Total'] = 100.0
    
    grand_total = pivot_table.loc['Total', 'Total']
    total_row_percent = (pivot_table.loc['Total'] / grand_total) * 100
    percent_df.loc['Total'] = total_row_percent
    
    return percent_df

def generate_report(issues, config, show_as_percent=False, output_file=None, show_roles=False, only_roles=False):
    """Gera um relatório em formato de tabela a partir das issues."""
    
    components_str = config.get('components_to_track', '')
    tracked_components_ordered = [comp.strip() for comp in components_str.split(',') if comp.strip()]
    
    role_mappings = {k.replace('role.', '', 1): v for k, v in config.items() if k.startswith('role.')}
    
    data = []
    if only_roles:
        people_with_roles = set(role_mappings.keys())

    for issue in issues:
        assignee = "Não atribuído"
        if issue.fields.assignee:
            assignee = issue.fields.assignee.displayName

        if only_roles and assignee not in people_with_roles:
            continue

        role = role_mappings.get(assignee)
        if not role and assignee != "Não atribuído":
            role = f"*{assignee}"

        if not tracked_components_ordered:
            if not issue.fields.components:
                data.append({"assignee": assignee, "role": role or assignee, "componente": "Sem Componente"})
            else:
                for c in issue.fields.components:
                    data.append({"assignee": assignee, "role": role or assignee, "componente": c.name})
            continue

        assigned_category = "Outros Componentes"
        if issue.fields.components:
            issue_components_set = {c.name for c in issue.fields.components}
            for tracked_comp in tracked_components_ordered:
                if tracked_comp in issue_components_set:
                    assigned_category = tracked_comp
                    break
        
        data.append({"assignee": assignee, "role": role or assignee, "componente": assigned_category})

    if not data:
        print("Nenhuma issue encontrada para os critérios especificados.")
        return

    df = pd.DataFrame(data)

    # --- Geração de todas as 4 tabelas ---

    # 1. Contagem por Responsável
    assignee_pivot = _create_pivot_table(df, 'assignee', tracked_components_ordered)
    assignee_pivot['Total'] = assignee_pivot.sum(axis=1)
    assignee_pivot.loc['Total'] = assignee_pivot.sum()

    # 2. Percentual por Responsável
    assignee_percent_df = _calculate_percent_df(assignee_pivot)

    # 3. Contagem por Perfil (Role)
    role_pivot = _create_pivot_table(df, 'role', tracked_components_ordered)
    role_counts = df.groupby('role')['assignee'].nunique()
    role_pivot.insert(0, 'Quant. Perfil Alocado', role_counts)
    role_pivot.index.name = 'Perfil profissional'
    task_cols = [col for col in role_pivot.columns if col != 'Quant. Perfil Alocado']
    role_pivot['Total'] = role_pivot[task_cols].sum(axis=1)
    total_row = role_pivot.sum()
    total_row['Quant. Perfil Alocado'] = df['assignee'].nunique()
    role_pivot.loc['Total'] = total_row
    
    # 4. Percentual por Perfil (Role)
    role_percent_df = _calculate_percent_df(role_pivot.drop(columns=['Quant. Perfil Alocado']))

    # --- Exibição no Console (condicional) ---
    if show_roles:
        display_table = role_pivot
        percent_table_to_format = role_percent_df
        if show_as_percent and percent_table_to_format is not None:
            formatted_df = percent_table_to_format.map(lambda x: f"{x:.1f}%")
            formatted_df.insert(0, 'Quant. Perfil Alocado', role_pivot['Quant. Perfil Alocado'])
            display_table = formatted_df
        print("--- Relatório de Tarefas Concluídas por Perfil ---")
    else:
        display_table = assignee_pivot
        if show_as_percent and assignee_percent_df is not None:
            display_table = assignee_percent_df.map(lambda x: f"{x:.1f}%")
        print("--- Relatório de Tarefas Concluídas por Responsável ---")
    
    print(display_table)
    print("-" * 70)

    # --- Exportação para Excel (sempre gera as 5 abas se --output for usado) ---
    if output_file:
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Aba 1
                assignee_pivot.to_excel(writer, sheet_name='Contagem por Responsável')
                # Aba 2
                if assignee_percent_df is not None:
                    assignee_percent_df.to_excel(writer, sheet_name='Percentual por Responsável', float_format="%.1f")
                # Aba 3
                role_pivot.to_excel(writer, sheet_name='Contagem por Perfil')
                # Aba 4
                if role_percent_df is not None:
                    excel_role_percent_df = role_percent_df.copy()
                    excel_role_percent_df.insert(0, 'Quant. Perfil Alocado', role_pivot['Quant. Perfil Alocado'])
                    excel_role_percent_df.to_excel(writer, sheet_name='Percentual por Perfil', float_format="%.1f")
                # Aba 5
                if role_mappings:
                    mapping_df = pd.DataFrame(list(role_mappings.items()), columns=['Responsável', 'Perfil'])
                    mapping_df.to_excel(writer, sheet_name='Mapeamento Perfis', index=False)

            print(f"\nRelatório salvo com sucesso em '{output_file}'")
        except Exception as e:
            print(f"\nErro ao salvar o arquivo Excel: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera um relatório de tarefas concluídas no Jira por responsável e componente."
    )
    # Argumentos...
    parser.add_argument('-c', '--config', type=str, required=True, help='Caminho para o arquivo de configuração JSON.')
    parser.add_argument('--start-date', type=str, help='Data de início do período (YYYY-MM-DD).')
    parser.add_argument('--end-date', type=str, help='Data de fim do período (YYYY-MM-DD).')
    parser.add_argument('--month', type=int, help='Mês numérico (1-12) para o relatório.')
    parser.add_argument('--year', type=int, help='Ano para o relatório.')
    parser.add_argument('--percent', action='store_true', help='Exibe os resultados em formato percentual.')
    parser.add_argument('--output', type=str, help='Caminho do arquivo Excel para salvar o relatório.')
    parser.add_argument('--show_roles', action='store_true', help='Agrupa o relatório por perfil (role).')
    parser.add_argument('--ignore_default_project', action='store_true', help='Executa a consulta em todos os projetos.')
    parser.add_argument('--only-roles', action='store_true', help='Considera apenas responsáveis com perfil definido.')

    args = parser.parse_args()
    config = load_config(args.config)
    if not config: exit(1)
    token = config.get("jira_token")
    if not token or "YOUR_JIRA_API_TOKEN" in token:
        print("Erro: Token do Jira não encontrado ou não configurado no arquivo de configuração JSON.")
        exit(1)

    # Lógica de data...
    start_date_str, end_date_str = "", ""
    if args.start_date and args.end_date:
        start_date_str, end_date_str = args.start_date, args.end_date
    elif args.month and args.year:
        start_date = datetime(args.year, args.month, 1)
        end_date = datetime(args.year, args.month, monthrange(args.year, args.month)[1])
        start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    elif args.year:
        start_date, end_date = datetime(args.year, 1, 1), datetime(args.year, 12, 31)
        start_date_str, end_date_str = start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    else:
        print("Erro: Você deve especificar um período.")
        exit(1)

    print(f"Gerando relatório para o período de {start_date_str} a {end_date_str}...")

    try:
        jira_client = JIRA(server=config['jira_server'], options={'headers': {'Authorization': f'Bearer {token}'}})
        project_key = config.get('default_project')
        issues = get_issues(jira_client, start_date_str, end_date_str, project_key, args.ignore_default_project)
        generate_report(issues, config, args.percent, args.output, args.show_roles, args.only_roles)
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
        exit(1)
