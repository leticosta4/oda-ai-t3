import json
import uuid
from db.client import db
from langchain_api.config import embeddings, model, ANSWER_PROMPT, SUMMARIZE_PROMPT
from langchain_core.output_parsers import StringOutputParser
from langchain_core.runnables import RunnablePassthrough

async def ask_question(question: str, chat_history: str = ""):
    query_vector = await embeddings.aembed_query(question)
    vector_str = f"[{','.join(map(str, query_vector))}]"
    
    # Query nearest chunks
    matched_chunks = await db.query_raw(
        'SELECT conteudo FROM rag_chunk ORDER BY embedding <-> $1::vector ASC LIMIT 5',
        vector_str
    )
    
    context = "\n\n".join(c["conteudo"] for c in matched_chunks if "conteudo" in c)
    
    chain = (
        {
            "context": lambda x: context,
            "question": RunnablePassthrough(),
        }
        | ANSWER_PROMPT
        | model
        | StringOutputParser()
    )
    
    return await chain.ainvoke(question)

async def ingest_document(content: str, metadata: dict = {}):
    doc_id = str(uuid.uuid4())
    doc = await db.ragdocument.create(
        data={
            "sourceType": "PRODUCAO",
            "sourceId": doc_id,
            "titulo": metadata.get("titulo") or "Documento Ingerido",
            "conteudo": content,
            "metadata": json.dumps(metadata)
        }
    )
    
    vector = await embeddings.aembed_query(content)
    vector_str = f"[{','.join(map(str, vector))}]"
    chunk_id = str(uuid.uuid4())
    
    await db.execute_raw(
        'INSERT INTO "rag_chunk" ("id", "document_id", "conteudo", "embedding", "ordem", "metadata", "atualizado_em") VALUES ($1, $2, $3, $4::vector, $5, $6, NOW())',
        chunk_id, doc.id, content, vector_str, 0, json.dumps(metadata)
    )
    return {"success": True}

async def ingest_research_group(data: dict):
    nome = data.get("nome") or "Desconhecido"
    dgp_id = data.get("id_dgp") or ""
    
    content = f"Grupo de Pesquisa: {nome}\n"
    content += f"DGP ID: {dgp_id}\n"
    content += f"Instituição: {data.get('instituicao') or ''}\n"
    content += f"Área: {data.get('area') or ''}\n"
    content += f"Ano de Formação: {data.get('ano_formacao') or ''}\n"
    content += f"Repercussão: {data.get('repercussao') or ''}\n"
    
    # Check if doc exists to replicate upsert
    existing = await db.ragdocument.find_unique(
        where={
            "sourceType_sourceId": {
                "sourceType": "GRUPO_PESQUISA",
                "sourceId": dgp_id
            }
        }
    )
    
    if existing:
        doc = await db.ragdocument.update(
            where={"id": existing.id},
            data={
                "titulo": nome,
                "conteudo": content,
                "metadata": json.dumps(data)
            }
        )
    else:
        doc = await db.ragdocument.create(
            data={
                "sourceType": "GRUPO_PESQUISA",
                "sourceId": dgp_id,
                "titulo": nome,
                "conteudo": content,
                "metadata": json.dumps(data)
            }
        )
        
    await db.ragchunk.delete_many(where={"documentId": doc.id})
    
    vector = await embeddings.aembed_query(content)
    vector_str = f"[{','.join(map(str, vector))}]"
    chunk_id = str(uuid.uuid4())
    
    await db.execute_raw(
        'INSERT INTO "rag_chunk" ("id", "document_id", "conteudo", "embedding", "ordem", "metadata", "atualizado_em") VALUES ($1, $2, $3, $4::vector, $5, $6, NOW())',
        chunk_id, doc.id, content, vector_str, 0, json.dumps(data)
    )
    return {"success": True}

async def summarize_text(text: str, instructions: str = None):
    chain = SUMMARIZE_PROMPT | model | StringOutputParser()
    return await chain.ainvoke({
        "text": text,
        "instructions": instructions or "Faça um resumo conciso destacando as principais contribuições."
    })

async def perform_semantic_search(query: str, type_filter: str = None, limit: int = 10, offset: int = 0):
    query_vector = await embeddings.aembed_query(query)
    vector_str = f"[{','.join(map(str, query_vector))}]"
    
    enum_mapping = {
        'GRUPO_PESQUISA': 'grupo_pesquisa',
        'LINHA_PESQUISA': 'linha_pesquisa',
        'PESQUISADOR': 'pesquisador',
        'PRODUCAO': 'producao',
        'AREA_CONHECIMENTO': 'area_conhecimento'
    }
    
    db_type = enum_mapping.get(type_filter, type_filter.lower()) if type_filter else None
    
    sql = """
        SELECT rd.source_id as "sourceId", MIN(rc.embedding <-> $1::vector) as score
        FROM rag_chunk rc
        JOIN rag_document rd ON rc.document_id = rd.id
    """
    params = [vector_str]
    
    if db_type:
        sql += " WHERE rd.source_type = $2::rag_source_type"
        params.append(db_type)
        
    sql += f"""
        GROUP BY rd.source_id
        ORDER BY score ASC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """
    params.append(limit)
    params.append(offset)
    
    count_sql = 'SELECT COUNT(DISTINCT source_id)::int as count FROM rag_document'
    count_params = []
    if db_type:
        count_sql += " WHERE source_type = $1::rag_source_type"
        count_params.append(db_type)
        
    results = await db.query_raw(sql, *params)
    count_res = await db.query_raw(count_sql, *count_params)
    
    total_items = count_res[0]["count"] if count_res else 0
    return {"results": results, "totalItems": total_items}
