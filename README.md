# Open DGP - Monólito (Python)

Sistema completo e unificado em Python para extração, processamento, estruturação, busca semântica (RAG) e análise de grupos de pesquisa do CNPq/DGP.

---

## Tecnologias Principais
* **Python 3.12**
* **FastAPI** (Serviço de RAG & busca semântica com LangChain)
* **Playwright & BeautifulSoup4** (Web Scraping dos dados públicos de forma simplificada e sequencial)
* **Prisma ORM (Python Client) & PostgreSQL** (Persistência relacional e vetorial pgvector)

---

## 🚀 Como Inicializar o Projeto

### 1. Instalação das Dependências
Instale todas as dependências necessárias utilizando o `pip`:
```bash
pip install -r requirements.txt
```

### 2. Variáveis de Ambiente
Crie ou configure o arquivo `.env` na raiz do projeto (use o `.env.example` como base). Garanta que as seguintes variáveis estejam configuradas:
- `DATABASE_URL` (URL de conexão PostgreSQL)
- `OPEN_AI_KEY` (Chave de API OpenAI para embeddings e RAG)

### 3. Geração do Cliente Prisma
Gere o cliente do banco de dados para Python executando:
```bash
prisma generate
```

### 4. Subir a Infraestrutura (Docker)
Para subir o banco de dados PostgreSQL com pgvector:
```bash
docker compose up -d postgres
```

### 5. Restaurar Banco a partir do Backup (Alternativa ao Scraper)
Se você não quiser executar o scraper (que pode levar horas), utilize o dump fornecido em `backup.sql` para popular o banco com dados já coletados:

```bash
./restore-db.sh
```

O script verifica automaticamente se o container `postgres` está rodando e se o banco já contém dados — se estiver vazio, executa o `pg_restore`; caso contrário, ignora para evitar conflitos.

---

## Executando os Serviços e Scripts

### A. Scraper (Coleta de Dados)
O scraper coleta dados públicos do DGP e do Currículo Lattes sequencialmente, sem cacheamento local e com uma única instância ativa de Playwright:
* **Descoberta de Grupos (Parametrizada):**
  ```bash
  python -m scraper.main discovery
  ```
* **Extração de Dados dos Grupos na Fila:**
  ```bash
  python -m scraper.main dgp
  ```
* **Extração de Currículos Lattes na Fila:**
  ```bash
  python -m scraper.main lattes
  ```
* **Repopular Fila de Pesquisadores a partir dos JSONs Locais:**
  ```bash
  python -m scraper.main repopulate
  ```
* **Resetar Status da Fila (de PROCESSANDO para PENDENTE):**
  ```bash
  python -m scraper.main reset-queue
  ```

### B. ETL (Importação e Processamento de Dados)
Processa os JSONs brutos da pasta `data/raw-data` e popula a estrutura relacional do banco:
* **Watcher Automatizado (Processa novos arquivos em tempo real):**
  ```bash
  python -m etl.main
  ```
* **Processar Grupo Específico:**
  ```bash
  python -m etl.main grupo <id_dgp_ou_caminho_json>
  ```
* **Processar Pesquisador Específico:**
  ```bash
  python -m etl.main pesquisador <id_lattes_ou_caminho_json>
  ```
* **Processar Todos os Grupos e Pesquisadores Salvos:**
  ```bash
  python -m etl.main run-all
  ```
* **Reprocessar/Corrigir Metadados (CrossRef/OpenAlex/Qualis):**
  ```bash
  python -m etl.main fix [-doi] [-DOI <doi>] [-lattes] [-LATTES <lattes_id>] [-qualis]
  ```

### C. LangChain API (Busca Semântica & RAG com FastAPI)
Serviço REST em FastAPI para perguntas semânticas, resumos e indexação vetorial:
* **Vetorizar e Sincronizar o Banco (Indexação Incremental):**
  ```bash
  python -m langchain_api.ingest_db
  ```
* **Iniciar o Servidor de Desenvolvimento:**
  ```bash
  python -m langchain_api.main
  ```
  O serviço FastAPI estará rodando na porta `8002`.

---

## 🐳 Executando com Docker Compose (Modo Produção)
Se desejar rodar o banco de dados e o serviço FastAPI do LangChain unificados:
```bash
docker compose up --build -d
```

Após subir, certifique-se de restaurar o banco (se estiver vazio):
```bash
./restore-db.sh
```
