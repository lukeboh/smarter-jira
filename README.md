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
-   Oferece a opção de visualizar o relatório em contagem ou em percentuais no console.
-   **Exporta para Excel:** Ao usar a opção `--output`, gera um arquivo `.xlsx` com um relatório completo em 5 abas:
    1.  `Contagem por Responsável`: Números absolutos de tarefas por pessoa.
    2.  `Percentual por Responsável`: Distribuição percentual de tarefas por pessoa.
    3.  `Contagem por Perfil`: Números absolutos de tarefas, agrupados por perfil profissional.
    4.  `Percentual por Perfil`: Distribuição percentual de tarefas por perfil.
    5.  `Mapeamento Perfis`: Tabela de-para mostrando qual responsável pertence a qual perfil.

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
| `--percent` | Não | Altera a **visualização no console** para formato percentual. |
| `--output` | Não | Ativa a exportação para um arquivo Excel com o nome especificado. |
| `--show_roles` | Não | Altera a **visualização no console** para agrupar por perfil. |
| `--only-roles` | Não | Filtra os dados para incluir apenas responsáveis com perfil definido no config. |
| `--ignore-project-id` | Não | Executa a consulta em todos os projetos, ignorando o `project-id` do config. |

---
---

## 🚦 Reordenador de Issues (`rank_issues.py`)

Este script permite reordenar programaticamente as issues filhas de uma issue pai (como um Épico, Story ou Tarefa) ou de **todos os Épicos dentro de um projeto**, com base em múltiplos critérios.

A ferramenta oferece duas formas de operação:
1.  **Modo de Issue Pai (`--parent-key`):** Reordena as issues filhas de uma única issue pai.
2.  **Modo de Projeto (`--project-id`):** Encontra todos os Épicos em um projeto e reordena as issues filhas de cada um deles.

A ordem de prioridade para os parâmetros é:
1.  Argumentos passados diretamente na linha de comando.
2.  Valores definidos no arquivo de configuração JSON.

Isso significa que você pode definir um comportamento padrão no seu `config.json` e sobrescrevê-lo facilmente com um argumento na linha de comando quando necessário.

### Configurando no `config.json`

Você pode definir os parâmetros de ordenação diretamente no seu arquivo de configuração para evitar passá-los toda vez. Adicione as seguintes chaves ao seu `config.json`:

```json
{
  "//": "--- Configurações para o script rank_issues.py ---",
  "parent-key": "PROJ-123",
  "project-id": "PROJ",
  "rank-by": ["status", "issuetype"],
  "order": ["asc", "asc"],
  "status-order": ["In Progress", "To Do", "Backlog", "Done"],
  "issuetype-order": ["Story", "Task", "Bug"]
}
```

### Argumentos da Linha de Comando (`rank_issues.py`)

| Argumento | Obrigatório? | Descrição |
| :--- | :--- | :--- |
| `--config` / `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--parent-key` | Não* | Chave da issue pai. Se omitido, busca no config. |
| `--project-id` | Não* | ID do projeto para ordenar TODOS os épicos. |
| `--rank-by` | Sim** | Lista de critérios de ordenação, separados por vírgula. Opções: `created`, `updated`, `resolutiondate`, `priority`, `key`, `status`, `issuetype`. |
| `--order` | Não | Lista de direções (`asc` ou `desc`). Padrão: `asc`. |
| `--status-order` | Não | Ordem customizada para o status (separada por vírgulas). |
| `--issuetype-order`| Não | Ordem customizada para o tipo de issue (separada por vírgulas). |
| `--dry-run` | Não | Exibe a nova ordem proposta sem aplicá-la no Jira. |
| `--debug` | Não | Ativa a saída de depuração detalhada para a lógica de ordenação. |

*\* **Nota:** Você deve fornecer `--parent-key` **ou** `--project-id`, seja na linha de comando ou no arquivo de configuração.*
*\*\* **Nota:** O argumento `--rank-by` é obrigatório, seja via linha de comando ou no arquivo de configuração.*
