# 🐍 Smarter Jira - Processador de Issues em Lote

Uma ferramenta de linha de comando (CLI) para criar, atualizar e deletar issues no Jira em lote a partir de um arquivo CSV. Ideal para migrações, automações e gerenciamento de grandes volumes de tarefas.

---

## ✨ Funcionalidades

- **Criação em Lote:** Crie centenas de issues e sub-tarefas a partir de um único arquivo CSV.
- **Deleção em Lote:** Desfaça uma criação em lote usando os arquivos de log gerados.
- **Atualização em Lote:** Atualize campos de issues existentes (atualmente focado no `Assignee`).
- **Configuração Flexível:** Adapte o script para diferentes instâncias e projetos do Jira através de um arquivo de configuração JSON.
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

## ⚙️ Configuração

Antes de usar o script, você precisa criar seu próprio arquivo de configuração.

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
    | `jira_token` | **(SECRETO)** Seu token de API pessoal do Jira. Para gerar, vá em `Seu Perfil > Gerenciamento da Conta > Segurança > Criar e gerenciar tokens de API`. |
    | `epic_link_field_id` | **(CRÍTICO)** O ID do campo customizado para o "Epic Link". Varia entre instâncias do Jira. Veja a seção "Como Obter IDs de Campos" abaixo. |
    | `default_project` | A chave do projeto padrão onde as issues serão criadas (ex: `PROJ`). |
    | `default_reporter` | O `username` (não o email) do usuário que será o relator padrão. |
    | `default_assignee` | O `username` do usuário que será o responsável padrão. |
    | `default_component` | O nome de um componente padrão a ser associado às issues. |
    | `default_customfield_10247`| **(OPCIONAL)** O valor padrão para um campo customizado. O ID (`customfield_10247`) é apenas um exemplo. Se seu Jira não usa este campo, simplesmente remova esta linha do seu arquivo de configuração. |

### 🕵️ Como Obter IDs de Campos Customizados (`epic_link_field_id`, etc.)

A maneira mais fácil de descobrir o ID de um campo como "Epic Link" é exportando uma issue que já tenha este campo preenchido.

1.  No Jira, navegue até uma issue que tenha um Épico associado.
2.  Clique em **Exportar > XML**.
3.  Abra o arquivo XML e procure pelo nome do campo (ex: `Epic Link`). Você encontrará um bloco de código como este:

    ```xml
    <customfield id="customfield_10109" key="com.pyxis.greenhopper.jira:gh-epic-link">
        <customfieldname>Epic Link</customfieldname>
        <customfieldvalues>
            <customfieldvalue>PROJ-123</customfieldvalue>
        </customfieldvalues>
    </customfield>
    ```
4.  O valor que você precisa é o que está em `id`. Neste exemplo, seria `customfield_10109`.

---

## 📄 Formato do CSV

O script usa um arquivo CSV para definir as issues a serem criadas. Use o `issues.csv.template` como base. As colunas são autoexplicativas, mas atenção especial para:

- `Issue ID`: Um número único **dentro do CSV** para identificar cada linha.
- `Parent ID`: Para subtarefas, coloque aqui o `Issue ID` da tarefa pai.
- `Reporter`, `Assignee`: Se preenchidos, sobrescrevem os padrões do arquivo de configuração.
- `Epic Link`: Para tarefas principais, coloque a chave do Épico (ex: `PROJ-123`).

---

## ▶️ Exemplos de Uso

**1. Criar Issues**

Cria as issues definidas no arquivo `my-issues.csv`.
```bash
python main.py --config my-config.json --csv my-issues.csv
```

**2. Deletar Issues**

Lê um arquivo de log (`issues_log_xxxx.csv`) e deleta todas as issues listadas nele.
```bash
python main.py --config my-config.json --action delete --csv issues_log_xxxx.csv
```

**3. Atualizar Issues**

Lê um arquivo de log/CSV e atualiza o `Assignee` das issues listadas.
```bash
python main.py --config my-config.json --action update --csv corrected-issues.csv
```

---

## 命令行 Argumentos

| Argumento | Atalho | Obrigatório? | Descrição |
| :--- | :--- | :--- | :--- |
| `--action` | | Não | Ação a ser executada: `create` (padrão), `delete`, ou `update`. |
| `--config` | `-c` | Sim | Caminho para o seu arquivo de configuração JSON. |
| `--csv` | | Sim | Caminho para o arquivo CSV de entrada. |
| `--logfile` | | Não | Define um nome customizado para o arquivo de log de saída. |
| `--verbose` | `-v` | Não | Ativa o modo "verbose", que exibe o payload JSON enviado para a API. |
| `--ignore-epics`| `-i` | Não | Desabilita a verificação que torna o `Epic Link` obrigatório na criação. |

---

## 📝 Logs

O script gera um log detalhado para cada execução, nomeado com o prefixo do arquivo de entrada e um timestamp (ex: `my-issues_log_2025-10-10_183000.csv`).

Este log é seu "recibo" e "mecanismo de segurança". Ele contém a chave da issue, a ação realizada e todos os dados originais, e pode ser usado para alimentar as ações de `delete` ou `update`.
