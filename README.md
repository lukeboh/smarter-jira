# 🐍 Smarter Jira - Processador de Issues em Lote

Uma ferramenta de linha de comando (CLI) para criar, atualizar e deletar issues no Jira em lote a partir de um arquivo CSV. Ideal para migrações, automações e gerenciamento de grandes volumes de tarefas.

---

## ✨ Funcionalidades

- **Criação em Lote:** Crie centenas de issues e sub-tarefas a partir de um único arquivo CSV.
- **Deleção em Lote:** Desfaça uma criação em lote usando os arquivos de log gerados.
- **Atualização em Lote:** Atualize campos de issues existentes.
- **Geração de Relatórios:** Crie relatórios de produtividade com base nas tarefas concluídas.
- **Reordenação de Issues:** Reordene programaticamente as issues filhas de um Épico ou Tarefa.
- **Configuração Flexível:** Adapte os scripts para diferentes instâncias e projetos do Jira através de um arquivo de configuração JSON.
- **Geração de Logs:** Cada operação (`create`, `delete`, `update`) gera um arquivo de log detalhado.

---

## 🚀 Começando

Siga os passos abaixo para configurar e executar o projeto.

### Pré-requisitos

- Python 3.x
- `pip` para gerenciamento de pacotes

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/lukeboh/smarter-jira.git
    cd smarter-jira
    ```

2.  **Crie e ative um ambiente virtual:** (Recomendado)
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: Para usar a funcionalidade de exportar relatórios para Excel, o `requirements.txt` inclui a biblioteca `openpyxl`.*

---

## ⚙️ Configuração

Todos os scripts (`import.py`, `report.py`, `rank_issues.py`) usam um arquivo de configuração central.

1.  **Crie seu arquivo de configuração:**
    Faça uma cópia do `config.json.template` e renomeie para um nome de sua preferência (ex: `my-config.json`).
    ```bash
    cp config.json.template my-config.json
    ```

2.  **Preencha os campos do seu `my-config.json`:**
    Consulte o `config.json.template` para ver todos os campos disponíveis e suas descrições.

---
---

## 📊 Gerador de Relatórios (`report.py`)

O script `report.py` analisa o histórico de tarefas no Jira e gera relatórios sobre a produtividade da equipe.

### Funcionalidades do Relatório

-   Gera uma tabela de tarefas concluídas, agrupadas por responsável ou por **Perfil Profissional**.
-   Ao agrupar por perfil, exibe a contagem de pessoas consolidadas em cada linha (`Quant. Perfil Alocado`).
-   Permite filtrar o relatório para incluir **apenas** responsáveis com perfis definidos no config.
-   Permite a busca em **todos os projetos** do Jira, não apenas no projeto padrão.
-   Permite a seleção e ordenação de componentes de interesse.
-   Garante que cada tarefa seja contada apenas uma vez, mesmo que tenha múltiplos componentes.
-   Oferece a opção de visualizar o relatório em contagem ou em percentuais.
-   Exporta o relatório para um arquivo Excel (`.xlsx`), com abas separadas para Contagem, Percentual e Mapeamento de Perfis.

### Configuração do `report.py`

Adicione as seguintes chaves opcionais ao seu `config.json` para usar os recursos avançados:
-   `components_to_track`: String com nomes de componentes separados por vírgula (ex: `"Backend,Frontend"`).
-   `role.Nome do Responsável`: Mapeia um responsável para um perfil (ex: `"role.Fulano de Tal": "Engenharia de Software"`).

### Argumentos da Linha de Comando (`report.py`)

| Argumento | Obrigatório? | Descrição |
| :--- | :--- | :--- |
| `--config` / `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--start-date` | Não | Data de início do período (YYYY-MM-DD). |
| `--end-date` | Não | Data de fim do período (YYYY-MM-DD). |
| `--month` | Não | Mês numérico (1-12) para o relatório. |
| `--year` | Não | Ano para o relatório. |
| `--percent` | Não | Exibe os resultados em formato percentual. |
| `--output` | Não | Caminho do arquivo Excel para salvar o relatório. |
| `--show_roles` | Não | Agrupa o relatório por perfil, exibindo a contagem de pessoas por perfil. |
| `--only-roles` | Não | Considera no relatório apenas responsáveis que possuem um perfil definido no config. |
| `--ignore_default_project` | Não | Executa a consulta em todos os projetos, ignorando o `default_project` do config. |

---
---

## 🚦 Reordenador de Issues (`rank_issues.py`)

Este script permite reordenar programaticamente as issues filhas de uma issue pai (como um Épico, Story ou Tarefa) com base em múltiplos critérios.

### Argumentos da Linha de Comando (`rank_issues.py`)

| Argumento | Obrigatório? | Descrição |
| :--- | :--- | :--- |
| `--config` / `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--parent-key` | Sim | A chave da issue pai (Épico, Tarefa, etc.). |
| `--rank-by` | Sim | Lista de critérios de ordenação, separados por vírgula. Opções: `created`, `updated`, `resolutiondate`, `priority`, `key`, `status`, `issuetype`. |
| `--order` | Não | Lista de direções (`asc` ou `desc`), separadas por vírgula. Padrão: `asc`. |
| `--dry-run` | Não | Exibe a nova ordem proposta sem aplicá-la no Jira. |
| `--debug` | Não | Ativa a saída de depuração detalhada para a lógica de ordenação. |