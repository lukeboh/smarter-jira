# 🐍 Smarter Jira - Processador de Issues em Lote

Uma ferramenta de linha de comando (CLI) para criar, atualizar e reordenar issues no Jira em lote. Ideal para migrações, automações e gerenciamento de grandes volumes de tarefas.

---

## ✨ Funcionalidades

- **Criação em Lote:** Crie centenas de issues e sub-tarefas a partir de um único arquivo CSV.
- **Deleção em Lote:** Desfaça uma criação em lote usando os arquivos de log gerados.
- **Atualização em Lote:** Atualize campos de issues existentes.
- **Geração de Relatórios:** Crie relatórios de produtividade com base nas tarefas concluídas.
- **Reordenação de Issues:** Reordene programaticamente as issues filhas de um Épico ou Tarefa.
- **Configuração Flexível:** Adapte os scripts para diferentes instâncias e projetos do Jira através de um arquivo de configuração JSON.
- **Geração de Logs:** Cada operação gera logs; `rank_issues.py` também imprime um resumo e o tempo de execução.

---

## 🚀 Começando

Siga os passos abaixo para configurar e executar o projeto.

### Pré-requisitos

- Python 3.10+
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

### Execução via wrappers (sem ativar venv)

Os wrappers em `scripts/` criam o `.venv` automaticamente (se ausente), instalam as dependências e executam o script alvo com Python >=3.10. Não é necessário rodar `source .venv/bin/activate`.

1. **Torne os wrappers executáveis (uma vez):**
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Exemplos:**
   ```bash
   ./scripts/run_rank_issues.sh -c ./jira.tse.config.json --project-id TS1184S --dry-run --brief
   ./scripts/run_import.sh --action create -c ./jira.tse.config.json --csv ./issues.csv
   ./scripts/run_report.sh -c ./jira.tse.config.json --month 5 --year 2026 --output ./relatorio.xlsx
   ```

---

## ⚙️ Configuração

Todos os scripts (`import.py`, `report.py`, `rank_issues.py`) usam um arquivo de configuração central.

1.  **Crie seu arquivo de configuração:**
    ```bash
    cp config.json.template my-config.json
    ```

2.  **Preencha os campos do seu `my-config.json`:**
    Consulte o `config.json.template` para ver todos os campos disponíveis e suas descrições.

---

## 🚦 Reordenador de Issues (`rank_issues.py`)

O script reordena programaticamente as issues filhas de uma issue pai (Épico/Story/Tarefa) ou de todos os Épicos dentro de um projeto, com base em múltiplos critérios.

### Modos de operação

1.  **Modo de Issue Pai (`--parent-key`):** Reordena as issues filhas de uma única issue pai.
2.  **Modo de Projeto (`--project-id`):** Encontra todos os Épicos em um projeto e reordena as issues filhas de cada um deles.

### Prioridade de configurações

1.  Argumentos passados na linha de comando.
2.  Valores definidos no arquivo de configuração JSON.

### Exemplo de bloco `config.json`

```json
{
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
| `--rank-by` | Sim** | Lista de critérios de ordenação, separados por vírgula. Opções: `created`, `updated`, `resolutiondate`, `priority`, `key`, `status`, `issuetype`, `epic`, `summary`. |
| `--order` | Não | Lista de direções (`asc` ou `desc`). Padrão: `asc`. |
| `--status-order` | Não | Ordem customizada para o status (separada por vírgulas). |
| `--issuetype-order`| Não | Ordem customizada para o tipo de issue (separada por vírgulas). |
| `--dry-run` | Não | Exibe a nova ordem proposta sem aplicá-la no Jira. |
| `--sprint` | Não | Nome da sprint para ordenar todas as issues dessa sprint. Se omitido, pode ser lido do `sprint` no arquivo de config. |
| `--epic-order` | Não | Lista de chaves de épicos (separadas por vírgula) definindo ordem customizada por épicos. Ex: `ABC-1,ABC-2`. |
| `--brief` | Não | Saída sucinta: imprime uma linha por épico e o resumo final. |
| `--debug` | Não | Ativa a saída de depuração detalhada para a lógica de ordenação. |

\* **Nota:** Você deve fornecer `--parent-key` **ou** `--project-id`, seja na linha de comando ou no arquivo de configuração.
\*\* **Nota:** O argumento `--rank-by` é obrigatório, seja via linha de comando ou no arquivo de configuração.

### Exemplos de uso

- Teste (sem aplicar mudanças) para um épico específico com saída sucinta:

```bash
./scripts/run_rank_issues.sh --config ./jira.tse.config.json --parent-key TS1184S-26 --dry-run --brief
```

- Teste (sem aplicar mudanças) para uma sprint definida no config:

```bash
./scripts/run_rank_issues.sh --config ./jira.tse.config.json --dry-run --brief
```

- Rodar para todo o projeto com logs detalhados (útil para depuração):

```bash
./scripts/run_rank_issues.sh --config ./jira.tse.config.json --project-id TS1184S --debug
```

- Aplicar as alterações (remova `--dry-run`) — recomendação: gere um backup ou rode com `--dry-run` primeiro.

```bash
./scripts/run_rank_issues.sh --config ./jira.tse.config.json --project-id TS1184S
```

### Saída prevista

- Em modo normal: lista detalhada da ordem proposta por épico, e um resumo final com contagens.
- Em `--brief`: uma linha por épico (`<EPIC_KEY>: N filhas ordenadas.` ou `<EPIC_KEY>: nenhuma ordenação necessária.`), seguida do resumo do lote e do tempo total de execução.
 - Novo critério `epic`: use `--rank-by epic` para ordenar por épico (aceita `--epic-order` para prioridade customizada entre épicos).
 - Novo critério `summary`: use `--rank-by summary` para ordenar alfabeticamente pelo resumo.
- Em `--debug`: logs de comparação entre issues e respostas HTTP das chamadas de reordenação.

**Recomendação:** sempre execute com `--dry-run` e/ou `--brief` antes de aplicar em produção.
