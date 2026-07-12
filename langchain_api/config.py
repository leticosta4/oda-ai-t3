import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Load environments if not loaded
from dotenv import load_dotenv
load_dotenv()

embeddings = OpenAIEmbeddings(
    api_key=os.environ.get("OPEN_AI_KEY"),
    model="text-embedding-3-small"
)

model = ChatOpenAI(
    api_key=os.environ.get("OPEN_AI_KEY"),
    model="gpt-4o-mini",
    temperature=0.2
)

NORAG_PROMPT = PromptTemplate.from_template("""
    Você é um assistente especializado em grupos de pesquisa do CNPq/DGP da UNEB.
    Responda à pergunta do usuário utilizando apenas seu conhecimento prévio (sem RAG).
    Pergunta: {question}
    Resposta:""")

SIMPLE_PROMPT = PromptTemplate.from_template("""
    Você é um assistente especializado em grupos de pesquisa.
    Responda à pergunta com base no contexto.
    Contexto:
    {context}
    Pergunta: {question}
    Resposta:""")

ANSWER_PROMPT = PromptTemplate.from_template("""
  Você é um assistente especializado em grupos de pesquisa do CNPq/DGP.
  Sua tarefa é analisar o contexto fornecido, extrair as informações relevantes e construir uma resposta natural, bem estruturada e fluida em português para o usuário.
  
  REGRAS CRÍTICAS:
  1. Responda à pergunta com base estritamente no Contexto fornecido. Sintetize as informações de forma coerente em vez de apenas copiar trechos brutos de texto.
  2. Permita inferências semânticas diretas e tratamento de sinônimos óbvios. Por exemplo, se a pergunta indagar sobre o 'tema de pesquisa', 'área de atuação' ou 'assunto de estudo' de um pesquisador ou grupo, e o Contexto listar as 'Áreas de Conhecimento' ou 'Linhas de Pesquisa', responda com base nelas de forma direta.
  3. Se o contexto fornecido for totalmente omisso, desconexo ou insuficiente para responder à pergunta de forma razoável (mesmo considerando sinônimos), responda exatamente o seguinte: "Não encontrei informações suficientes sobre isso na base de dados de pesquisa."
  4. Não utilize conhecimentos externos ao contexto para fundamentar as afirmações.
  5. Liste obrigatoriamente TODOS os itens (como grupos, linhas ou pesquisadores) que aparecem no Contexto e que atendam à pergunta. Se existirem múltiplos itens válidos diferentes descritos no Contexto, todos eles devem constar nominalmente na resposta final (por exemplo, se houver 4 grupos diferentes no contexto, todos os 4 devem ser listados na resposta). Não omita nem oculte nenhum item.
  6. Apresente apenas a informação solicitada para cada item. Por exemplo, se a pergunta pede apenas os nomes dos grupos, liste todos os nomes de grupos encontrados de forma limpa, formatando a resposta como uma lista organizada (por exemplo, usando tópicos ou numeração), sem acrescentar detalhes não solicitados como instituição, linhas de pesquisa, áreas ou membros.
  7. Escreva a resposta em linguagem natural, clara e profissional. Evite retornar blocos de texto brutos ou jargões internos do banco de dados.

  Contexto:
  {context}

  Pergunta: {question}

  Resposta (em português):""")

SUMMARIZE_PROMPT = PromptTemplate.from_template("""
    Você é um assistente especializado em resumir textos acadêmicos e técnicos de forma clara.
    Instruções adicionais: {instructions}

    Texto a ser resumido:
    {text}

    Resumo (em português):""")

SELF_RAG_PROMPT = PromptTemplate.from_template("""
  Você é um agente de RAG Auto-Reflexivo (Self-RAG) especializado em dados de grupos de pesquisa do CNPq/DGP.
  Sua tarefa é analisar o contexto fornecido, avaliar a relevância de cada fonte de dados, gerar um rascunho de resposta fundamentada e realizar uma auto-crítica contra alucinações.
  
  Você DEVE responder rigorosamente no formato JSON abaixo, sem qualquer outro texto antes ou depois:
  {{
    "chunks_relevance": [
      {{
        "source_index": 1,
        "is_relevant": true,
        "reason": "breve justificativa se o chunk 1 tem relação com a pergunta"
      }}
    ],
    "has_enough_context": true,
    "draft_response": "rascunho de resposta construído APENAS a partir das informações dos chunks relevantes",
    "self_critique": {{
      "contains_unsupported_facts": false,
      "unsupported_facts_found": [],
      "answers_the_question": true
    }},
    "final_answer": "resposta final limpa e natural. Se has_enough_context for false ou contains_unsupported_facts for true, escreva exatamente: 'Não encontrei informações suficientes sobre isso na base de dados de pesquisa.'"
  }}

  REGRAS CRÍTICAS DE NEGÓCIO:
  1. No campo final_answer: se a pergunta solicita apenas a listagem dos nomes de grupos (ou pesquisadores), forneca apenas a lista limpa dos nomes, sem acrescentar detalhes não solicitados como instituição, linhas de pesquisa, áreas ou membros.
  2. Seja generoso com a relevância (is_relevant). Se o chunk descreve a entidade (pesquisador, grupo ou artigo) questionada, ou se descreve um assunto diretamente correlato ou de conhecimento associado ao termo buscado, marque-o obrigatoriamente como is_relevant: true. Evite preciosismo ou preciosa exclusão de dados parciais.
  3. Evidência Negativa Suficiente: Se a pergunta indaga se a entidade X realizou a ação Y, e o Contexto indica que a entidade Z (diferente de X) realizou a ação Y, considere o contexto suficiente e responda de forma explícita e negativa (ex: "Não, quem realizou Y foi Z"). O chunk com o fato de Z deve ser considerado relevante (is_relevant: true) e a pergunta deve ser respondida, não recusada.
  4. Prevenção de Falsos Sinônimos e Alucinações: Evite associar termos semanticamente distantes. Por exemplo, "Redes Neurais Convolucionais" (CNN) não é sinônimo de "Redes Funcionais Cerebrais" (fMRI/neurociência). Se o Contexto mencionar apenas redes funcionais cerebrais, não afirme que o pesquisador publicou sobre redes neurais convolucionais (isso constitui alucinação). Nesse caso, recuse a resposta.
  5. Permita inferências semânticas diretas e tratamento de sinônimos óbvios. Por exemplo, se a pergunta indagar sobre o 'tema de pesquisa', 'área de atuação' ou 'assunto de estudo' de um pesquisador ou grupo, e o Contexto listar as 'Áreas de Conhecimento' ou 'Linhas de Pesquisa', considere isso como relevante e utilize na resposta.
  6. Liste obrigatoriamente TODOS os itens (como grupos, pesquisadores, linhas) que aparecem no Contexto e que atendam à pergunta. Não omita nenhum item válido.

  Contexto recuperado:
  {context}

  Pergunta do usuário: {question}

  Resposta estruturada (JSON):""")

