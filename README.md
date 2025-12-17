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

Todos os scripts (`main.py`, `reports.py`, `rank_issues.py`) usam um arquivo de configuração central.

1.  **Crie seu arquivo de configuração:**
    Faça uma cópia do `config.json.template` e renomeie para um nome de sua preferência (ex: `my-config.json`).
    ```bash
    cp config.json.template my-config.json
    ```

2.  **Preencha os campos do seu `my-config.json`:**
    Consulte o `config.json.template` para ver todos os campos disponíveis e suas descrições, incluindo `jira_server`, `jira_token`, `default_project`, `components_to_track`, e as configurações de `role.*`.

---
---

## 📊 Gerador de Relatórios (`reports.py`)

O script `reports.py` analisa o histórico de tarefas no Jira e gera relatórios sobre a produtividade da equipe. Para detalhes sobre seus argumentos e funcionalidades, consulte a documentação no topo do próprio arquivo.

---
---

## 🚦 Reordenador de Issues (`rank_issues.py`)

Este script permite reordenar programaticamente as issues filhas de uma issue pai (como um Épico, Story ou Tarefa) com base em múltiplos critérios.

### Funcionalidades do Reordenador

-   Reordena sub-tarefas de uma Tarefa/Story ou issues dentro de um Épico.
-   Suporta ordenação por múltiplos critérios em cascata (ex: por status, depois por prioridade).
-   Permite definir a direção (`asc` ou `desc`) para cada critério de ordenação.
-   Verifica se as issues já estão na ordem desejada para evitar operações desnecessárias.
-   Inclui um modo de simulação (`--dry-run`) para visualizar a nova ordem sem aplicar nenhuma mudança no Jira.
-   Oferece um modo de depuração (`--debug`) para analisar o processo de comparação passo a passo.

### Como Usar o `rank_issues.py`

**Exemplo 1: Ordenar por prioridade (mais alta primeiro)**
```bash
python rank_issues.py --config config.json --parent-key PROJ-123 --rank-by priority --order asc
```

**Exemplo 2: Ordenar por Status, depois por Chave (numérica)**
```bash
python rank_issues.py --config config.json --parent-key PROJ-123 --rank-by status,key --order asc,asc
```

**Exemplo 3: Simular uma ordenação por data de criação (mais recentes primeiro)**
```bash
python rank_issues.py --config config.json --parent-key PROJ-123 --rank-by created --order desc --dry-run
```

### Argumentos da Linha de Comando (`rank_issues.py`)

| Argumento | Obrigatório? | Descrição |
| :--- | :--- | :--- |
| `--config` / `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--parent-key` | Sim | A chave da issue pai (Épico, Tarefa, etc.). |
| `--rank-by` | Sim | Lista de critérios de ordenação, separados por vírgula. Opções: `created`, `updated`, `resolutiondate`, `priority`, `key`, `status`, `issuetype`. |
| `--order` | Não | Lista de direções (`asc` ou `desc`), separadas por vírgula. Se apenas uma for fornecida, será usada para todos os critérios. Padrão: `asc`. |
| `--dry-run` | Não | Exibe a nova ordem proposta sem aplicá-la no Jira. |
| `--debug` | Não | Ativa a saída de depuração detalhada para a lógica de ordenação. |