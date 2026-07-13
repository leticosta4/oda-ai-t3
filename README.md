# Open DGP — Sistema de Busca Semântica para Grupos de Pesquisa do CNPq/DGP

Pipeline completo em Python para extração, estruturação, indexação vetorial e busca semântica (RAG) de grupos de pesquisa do **CNPq/DGP** e dados do **Currículo Lattes**, com foco em instituições baianas.

---

## Arquitetura e Técnicas

### Pipeline de Dados

```
Scraper (DGP + Lattes) → ETL (estruturação + enriquecimento) → LangChain API (indexação vetorial + RAG)
```

1. **Scraper** — Coleta dados públicos do DGP (grupos de pesquisa) e do Currículo Lattes via Playwright + BeautifulSoup, armazenando em fila de extração e JSONs brutos.
2. **ETL** — Processa os JSONs, povoa o banco relacional (Prisma ORM + PostgreSQL) e enriquece metadados por CrossRef, OpenAlex e Qualis CAPES.
3. **LangChain API** — Indexa os dados vetorialmente e expõe endpoints de perguntas semânticas (RAG) via FastAPI.

### Indexação Vetorial

- **Modelo de embedding**: `text-embedding-3-small` (OpenAI) — vetores de **1536 dimensões**
- **Chunking**: 1000 caracteres com 200 de overlap, quebra inteligente em newlines/espaços
- **Armazenamento**: extensão **pgvector** no PostgreSQL (coluna `vector(1536)`)
- **Indexação incremental**: apenas documentos novos ou atualizados são (re)vetorizados

### Abordagens de RAG Implementadas

| Versão | Técnica | Descrição |
|--------|---------|-----------|
| **A — RAG Simples** (`/question-simple`) | Busca vetorial + prompt direto | Top-5 chunks por distância L2 → contexto concatenado → GPT-4o-mini responde. Foco em alto recall. |
| **B — Self-RAG** (`/question-hybrid`, implementado mas não exposto) | Busca + auto-reflexão em JSON mode | Mesma busca, mas o LLM avalia relevância de cada chunk, gera rascunho, faz auto-crítica contra alucinações e só então responde. |
| **C — LLM Direto / NoRAG** (`/question-norag`) | Apenas LLM, sem contexto | Consulta o GPT-4o-mini sem nenhum contexto externo. **Baseline** para comparação. |

### Resultados Experimentais (LLM-as-a-Judge — 30 perguntas)

| Métrica | RAG Simples | LLM Direto |
|---|---|---|
| **Acurácia factual (F1)** | **99,3%** | 34,0% |
| **Taxa de alucinação** | **3,3%** | 90,0% |
| **Recall de recuperação** | **85,0%** | 0,0% |
| **Latência média** | 2,54s | 2,15s |

> Relatório completo em [`resultados_testes.md`](resultados_testes.md).

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
