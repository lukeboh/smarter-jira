# 🐍 Smarter Jira - Processador de Issues em Lote

Uma ferramenta de linha de comando (CLI) para criar, atualizar e deletar issues no Jira em lote a partir de um arquivo CSV. Ideal para migrações, automações e gerenciamento de grandes volumes de tarefas.

---

## ✨ Funcionalidades

- **Criação em Lote:** Crie centenas de issues e sub-tarefas a partir de um único arquivo CSV.
- **Deleção em Lote:** Desfaça uma criação em lote usando os arquivos de log gerados.
- **Atualização em Lote:** Atualize campos de issues existentes (atualmente focado no `Assignee`).
- **Geração de Relatórios:** Crie relatórios de produtividade com base nas tarefas concluídas em um período.
- **Configuração Flexível:** Adapte os scripts para diferentes instâncias e projetos do Jira através de um arquivo de configuração JSON.
- **Geração de Logs:** Cada operação (`create`, `delete`, `update`) gera um arquivo de log detalhado, garantindo rastreabilidade e permitindo reverter ações.
- **Validações Inteligentes:** O script valida campos obrigatórios como o `Epic Link` para evitar a criação de issues incorretas.

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

## ⚙️ Configuração (`main.py`)

Para o script principal `main.py`, você precisa criar seu próprio arquivo de configuração.

1.  **Crie seu arquivo de configuração:**
    Faça uma cópia do `config.json.template` e renomeie para um nome de sua preferência (ex: `my-config.json`).
    ```bash
    cp config.json.template my-config.json
    ```

2.  **Preencha os campos do seu `my-config.json`:**

    | Chave | Descrição |
    | :--- | :--- |
    | `jira_server` | A URL base da sua instância do Jira (ex: `https://suaempresa.jira.com/`). |
    | `jira_token` | **(SECRETO)** Seu token de API pessoal do Jira. |
    | `epic_link_field_id` | **(CRÍTICO)** O ID do campo customizado para o "Epic Link". |
    | `default_project` | A chave do projeto padrão onde as issues serão criadas (ex: `PROJ`). |
    | `default_reporter` | O `username` do usuário que será o relator padrão. |
    | `default_assignee` | O `username` do usuário que será o responsável padrão. |
    | `default_component` | O nome de um componente padrão a ser associado às issues. |

---

## ▶️ Uso do `main.py`

**1. Criar Issues**
```bash
python main.py --config my-config.json --csv my-issues.csv
```

**2. Deletar Issues**
```bash
python main.py --config my-config.json --action delete --csv issues_log_xxxx.csv
```

---
---

## 📊 Gerador de Relatórios (`reports.py`)

O script `reports.py` analisa o histórico de tarefas no Jira e gera relatórios sobre a produtividade da equipe em um determinado período.

### Funcionalidades do Relatório

-   Gera uma tabela de tarefas concluídas, agrupadas por responsável ou, opcionalmente, por **Perfil Profissional**.
-   Ao agrupar por perfil, exibe a contagem de pessoas consolidadas em cada linha na coluna `Quant. Perfil Alocado`.
-   Permite a filtragem por um período específico (mês/ano ou datas de início/fim).
-   Permite a busca em **todos os projetos** do Jira, não apenas no projeto padrão.
-   Permite a seleção e ordenação de componentes de interesse através do arquivo de configuração.
-   Agrupa tarefas de componentes não especificados em uma categoria "Outros Componentes".
-   Garante que cada tarefa seja contada apenas uma vez, mesmo que tenha múltiplos componentes.
-   Oferece a opção de visualizar o relatório em contagem ou em percentuais.
-   Exporta o relatório para um arquivo Excel (`.xlsx`), que pode incluir:
    -   Aba `Contagem` com os números absolutos.
    -   Aba `Percentual` com os dados percentuais.
    -   Aba `Mapeamento Roles` com o de-para de Responsável -> Perfil, quando a opção de agrupar por perfil é usada.

### Configuração do `reports.py`

O `reports.py` utiliza o mesmo arquivo `config.json`. Para as funcionalidades de agrupamento por perfil, adicione chaves com o prefixo `role.`:

-   `components_to_track`: Uma string com nomes de componentes separados por vírgula (ex: `"Backend,Frontend,Infra"`). Define a prioridade e ordem das colunas.
-   `role.Nome do Responsável`: Mapeia um responsável para um perfil. Você pode ter quantas entradas `role.` precisar.

#### Exemplo de `config.json` para relatórios:
```json
{
  "jira_server": "https://seu-jira.com/",
  "jira_token": "SEU_TOKEN_AQUI",
  "default_project": "PROJETO",
  "components_to_track": "Backend,Frontend,Infra",
  "role.Fulano de Tal": "Engenharia de Software - Pleno",
  "role.Ciclana da Silva": "Engenharia de Software - Sênior"
}
```

### ▶️ Como Usar o `reports.py`

**Exemplo 1: Relatório padrão para o projeto default**
```bash
python reports.py --config config.json --month 11 --year 2025
```

**Exemplo 2: Relatório por perfil, para todos os projetos, exportado para Excel**
```bash
python reports.py --config config.json --year 2025 --show_roles --percent --ignore_default_project --output relatorio_geral.xlsx
```
*Este comando irá gerar um arquivo Excel com 3 abas, buscando dados de todos os projetos.*

### Argumentos da Linha de Comando (`reports.py`)

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
| `--ignore_default_project` | Não | Executa a consulta em todos os projetos, ignorando o `default_project` do config. |
