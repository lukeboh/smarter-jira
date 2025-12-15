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

---

## ⚙️ Configuração (`main.py`)

Para o script principal `main.py`, você precisa criar seu próprio arquivo de configuração.

1.  **Crie seu arquivo de configuração:**
    Faça uma cópia do `config.json.template` e renomeie para um nome de sua preferência (ex: `my-config.json`).
    ```bash
    cp config.json.template my-config.json
    ```
    Como arquivos `*.json` estão no `.gitignore`, seu arquivo de configuração não será enviado para o repositório.

2.  **Preencha os campos do seu `my-config.json`:**

    | Chave | Descrição |
    | :--- | :--- |
    | `jira_server` | A URL base da sua instância do Jira (ex: `https://suaempresa.jira.com/`). |
    | `jira_token` | **(SECRETO)** Seu token de API pessoal do Jira. |
    | `epic_link_field_id` | **(CRÍTICO)** O ID do campo customizado para o "Epic Link". Veja a seção "Como Obter IDs de Campos" abaixo. |
    | `default_project` | A chave do projeto padrão onde as issues serão criadas (ex: `PROJ`). |
    | `default_reporter` | O `username` (não o email) do usuário que será o relator padrão. |
    | `default_assignee` | O `username` do usuário que será o responsável padrão. |
    | `default_component` | O nome de um componente padrão a ser associado às issues. |

### 🕵️ Como Obter IDs de Campos Customizados (`epic_link_field_id`, etc.)

A maneira mais fácil de descobrir o ID de um campo como "Epic Link" é exportando uma issue que já tenha este campo preenchido. No Jira, navegue até uma issue, clique em **Exportar > XML** e procure pelo nome do campo no arquivo XML. O `id` do campo estará visível (ex: `customfield_10109`).

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

**3. Atualizar Issues**
```bash
python main.py --config my-config.json --action update --csv corrected-issues.csv
```

---
---

## 📊 Gerador de Relatórios (`reports.py`)

O script `reports.py` analisa o histórico de tarefas no Jira e gera relatórios sobre a produtividade da equipe em um determinado período.

### Funcionalidades do Relatório

-   Gera uma tabela de tarefas concluídas, agrupadas por responsável e por componente.
-   Permite a filtragem por um período específico (mês/ano ou datas de início/fim).
-   Permite a seleção e ordenação de componentes de interesse através do arquivo de configuração.
-   Agrupa tarefas de componentes não especificados em uma categoria "Outros Componentes".
-   Garante que cada tarefa seja contada apenas uma vez, mesmo que tenha múltiplos componentes, respeitando a ordem de prioridade definida.
-   Oferece a opção de visualizar o relatório em valores absolutos (contagem) ou em percentuais.

### Configuração do `reports.py`

O `reports.py` utiliza o mesmo arquivo `config.json`. Para as novas funcionalidades, você pode adicionar a seguinte chave opcional:

-   `components_to_track`: Uma string com nomes de componentes separados por vírgula (ex: `"Backend,Frontend,Infra"`).
    -   A ordem dos componentes nesta lista define a **prioridade na contagem** e a **ordem das colunas** no relatório.
    -   Tarefas com múltiplos componentes serão contadas apenas uma vez, no primeiro componente correspondente que aparecer na sua lista.
    -   Se uma tarefa não possuir nenhum dos componentes listados, será agrupada em "Outros Componentes".

#### Exemplo de `config.json` para relatórios:
```json
{
  "jira_server": "https://seu-jira.com/",
  "jira_token": "SEU_TOKEN_AQUI",
  "default_project": "PROJETO",
  "components_to_track": "Backend,Frontend,Infra"
}
```

### ▶️ Como Usar o `reports.py`

**Exemplo 1: Gerar relatório de contagem para um mês específico**
```bash
python reports.py --config config.json --month 11 --year 2025
```

**Exemplo 2: Gerar relatório com datas específicas**
```bash
python reports.py --config config.json --start-date 2025-11-01 --end-date 2025-11-30
```

**Exemplo 3: Gerar relatório em formato percentual**
```bash
python reports.py --config config.json --month 11 --year 2025 --percent
```

### Argumentos da Linha de Comando (`reports.py`)

| Argumento | Obrigatório? | Descrição |
| :--- | :--- | :--- |
| `--config` / `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--start-date` | Não | Data de início do período (YYYY-MM-DD). Usar com `--end-date`. |
| `--end-date` | Não | Data de fim do período (YYYY-MM-DD). Usar com `--start-date`. |
| `--month` | Não | Mês numérico (1-12) para o relatório. Requer `--year`. |
| `--year` | Não | Ano para o relatório. Pode ser usado com `--month` ou sozinho. |
| `--percent` | Não | Exibe os resultados em formato percentual em vez de contagem. |