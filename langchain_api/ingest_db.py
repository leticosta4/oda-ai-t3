import asyncio
import json
import sys
import uuid
from dotenv import load_dotenv
load_dotenv()

from db.client import db
from langchain_api.config import embeddings

def split_text(text: str, chunk_size=1000, chunk_overlap=200) -> list:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start_index = 0
    while start_index < len(text):
        end_index = start_index + chunk_size
        if end_index >= len(text):
            chunks.append(text[start_index:])
            break
            
        split_index = end_index
        overlap_zone = text[end_index - chunk_overlap:end_index]
        last_newline = overlap_zone.rfind('\n')
        if last_newline != -1:
            split_index = end_index - chunk_overlap + last_newline + 1
        else:
            last_space = overlap_zone.rfind(' ')
            if last_space != -1:
                split_index = end_index - chunk_overlap + last_space + 1
                
        chunks.append(text[start_index:split_index])
        next_start_index = split_index - chunk_overlap
        if next_start_index <= start_index:
            start_index = end_index - chunk_overlap
        else:
            start_index = next_start_index
    return chunks

async def need_vectorization(source_type: str, source_id: str, db_updated_at) -> bool:
    existing = await db.ragdocument.find_unique(
        where={
            "sourceType_sourceId": {
                "sourceType": source_type,
                "sourceId": source_id
            }
        }
    )
    if not existing:
        return True
    return db_updated_at.timestamp() > existing.atualizadoEm.timestamp()

async def save_rag_document(source_type: str, source_id: str, titulo: str, content: str, metadata: dict):
    try:
        doc = await db.ragdocument.find_unique(
            where={
                "sourceType_sourceId": {
                    "sourceType": source_type,
                    "sourceId": source_id
                }
            }
        )
        if doc:
            doc = await db.ragdocument.update(
                where={"id": doc.id},
                data={
                    "titulo": titulo,
                    "conteudo": content,
                    "metadata": json.dumps(metadata)
                }
            )
        else:
            doc = await db.ragdocument.create(
                data={
                    "sourceType": source_type,
                    "sourceId": source_id,
                    "titulo": titulo,
                    "conteudo": content,
                    "metadata": json.dumps(metadata)
                }
            )
            
        await db.ragchunk.delete_many(where={"documentId": doc.id})
        
        chunks = split_text(content)
        vectors = await embeddings.aembed_documents(chunks)
        
        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            vector_str = f"[{','.join(map(str, vector))}]"
            chunk_id = str(uuid.uuid4())
            await db.execute_raw(
                'INSERT INTO "rag_chunk" ("id", "document_id", "conteudo", "embedding", "ordem", "metadata", "atualizado_em") VALUES ($1, $2, $3, $4::vector, $5, $6, NOW())',
                chunk_id, doc.id, chunk_text, vector_str, i, json.dumps(metadata)
            )
        print(f"[VETORIZAÇÃO] ✅ {source_type} \"{titulo}\" vetorizado com {len(chunks)} chunks.")
    except Exception as e:
        print(f"❌ Erro ao vetorizar {source_type} \"{titulo}\": {str(e)}")

async def sync_db():
    print('🔄 Iniciando sincronização incremental de embeddings (apenas novos e atualizados)...')
    
    # 1. Sync Groups
    print('📦 Analisando Grupos de Pesquisa...')
    grupos = await db.grupopesquisa.find_many(
        include={
            "instituicao": {"include": {"estado": True}},
            "linhasPesquisa": True,
            "membros": {"include": {"pesquisador": True}},
            "areasConhecimento": {"include": {"area": True}}
        }
    )
    
    grupos_sincronizados = 0
    for g in grupos:
        sync = await need_vectorization('GRUPO_PESQUISA', g.id, g.atualizadoEm)
        if not sync:
            continue
            
        content = f"Grupo de Pesquisa: {g.nome}\n"
        content += f"DGP ID: {g.dgpId or 'N/A'}\n"
        if g.instituicao:
            sig = g.instituicao.sigla or ''
            est = g.instituicao.estado.nome if g.instituicao.estado else 'N/A'
            content += f"Instituição: {g.instituicao.nome} ({sig}) - Estado: {est}\n"
        content += f"Área Predominante: {g.areaPredominante or 'N/A'}\n"
        content += f"Ano de Formação: {g.anoFormacao or 'N/A'}\n"
        content += f"Repercussão: {g.repercussao or 'N/A'}\n"
        
        areas = [ac.area.nome for ac in g.areasConhecimento if ac.area]
        if areas:
            content += f"Áreas de Conhecimento: {', '.join(areas)}\n"
            
        if g.linhasPesquisa:
            content += "Linhas de Pesquisa:\n"
            for lp in g.linhasPesquisa:
                content += f"- {lp.titulo}: {lp.objetivo or 'Sem objetivo cadastrado'}\n"
                
        if g.membros:
            content += "Membros do Grupo:\n"
            for m in g.membros:
                if m.pesquisador:
                    content += f"- {m.pesquisador.nome} ({m.pesquisador.tipo or 'N/A'}, {m.pesquisador.formacaoAcademica or 'N/A'})\n"
                    
        await save_rag_document('GRUPO_PESQUISA', g.id, g.nome, content, {"dgpId": g.dgpId or ''})
        grupos_sincronizados += 1
        
    print(f"[ETL-IA] Grupos de Pesquisa processados: {grupos_sincronizados} sincronizados.")
    
    # 2. Sync Researchers
    print('👥 Analisando Pesquisadores...')
    pesquisadores = await db.pesquisador.find_many(
        include={
            "membrosGrupo": {"include": {"grupoPesquisa": {"include": {"instituicao": True}}}},
            "producoes": {"include": {"producao": True}},
            "areasConhecimento": {"include": {"area": True}}
        }
    )
    
    pesquisadores_sincronizados = 0
    for p in pesquisadores:
        sync = await need_vectorization('PESQUISADOR', p.id, p.atualizadoEm)
        if not sync:
            continue
            
        content = f"Pesquisador: {p.nome}\n"
        content += f"Lattes ID: {p.lattesId or 'N/A'}\n"
        content += f"Tipo: {p.tipo or 'N/A'}\n"
        content += f"Formação Acadêmica: {p.formacaoAcademica or 'N/A'}\n"
        content += f"Indicadores OpenAlex: H-Index = {p.indexH if p.indexH is not None else 'N/A'}, i10-Index = {p.indexI10 if p.indexI10 is not None else 'N/A'}\n"
        content += f"OpenAlex ID: {p.openAlexId or 'N/A'} | ORCID ID: {p.orcidId or 'N/A'}\n"
        
        areas = [ac.area.nome for ac in p.areasConhecimento if ac.area]
        if areas:
            content += f"Áreas de Conhecimento: {', '.join(areas)}\n"
            
        grupos_assoc = [f"{mg.grupoPesquisa.nome} ({mg.grupoPesquisa.instituicao.sigla if mg.grupoPesquisa.instituicao else ''})" for mg in p.membrosGrupo]
        if grupos_assoc:
            content += f"Grupos de Pesquisa Associados: {', '.join(grupos_assoc)}\n"
            
        artigos = [f'"{pr.producao.titulo}" ({pr.producao.ano or ""})' for pr in p.producoes if pr.producao.tipo == 'ARTIGO']
        if artigos:
            content += "Artigos Publicados:\n" + "\n".join(f"- {a}" for a in artigos) + "\n"
            
        await save_rag_document('PESQUISADOR', p.id, p.nome, content, {"lattesId": p.lattesId or ''})
        pesquisadores_sincronizados += 1
        
    print(f"[ETL-IA] Pesquisadores processados: {pesquisadores_sincronizados} sincronizados.")
    
    # 3. Sync Productions
    print('📚 Analisando Produções...')
    producoes = await db.producao.find_many(
        include={"autores": {"include": {"pesquisador": True}}}
    )
    
    producoes_sincronizadas = 0
    for pr in producoes:
        sync = await need_vectorization('PRODUCAO', pr.id, pr.atualizadoEm)
        if not sync:
            continue
            
        content = f"Produção Acadêmica: {pr.titulo}\n"
        content += f"Tipo: {pr.tipo}\n"
        content += f"Ano: {pr.ano or 'N/A'} | Veículo: {pr.veiculo or 'N/A'}\n"
        content += f"DOI: {pr.doi or 'N/A'} | URL: {pr.url or 'N/A'}\n"
        
        autores = [a.pesquisador.nome for a in pr.autores if a.pesquisador]
        if autores:
            content += f"Autores/Pesquisadores: {', '.join(autores)}\n"
            
        if pr.resumo:
            content += f"Resumo:\n{pr.resumo}\n"
            
        await save_rag_document('PRODUCAO', pr.id, pr.titulo, content, {"doi": pr.doi or ''})
        producoes_sincronizadas += 1
        
    print(f"[ETL-IA] Produções processadas: {producoes_sincronizadas} sincronizadas.")
    
    # 4. Sync Lines
    print('🔬 Analisando Linhas de Pesquisa...')
    linhas = await db.linhapesquisa.find_many(
        include={
            "grupo": {"include": {"instituicao": True}},
            "palavrasChave": {"include": {"palavraChave": True}},
            "setoresAplicacao": {"include": {"setorAplicacao": True}}
        }
    )
    
    linhas_sincronizadas = 0
    for lp in linhas:
        sync = await need_vectorization('LINHA_PESQUISA', lp.id, lp.atualizadoEm)
        if not sync:
            continue
            
        content = f"Linha de Pesquisa: {lp.titulo}\n"
        content += f"Objetivo: {lp.objetivo or 'Sem objetivo cadastrado'}\n"
        
        kws = [pc.palavraChave.termo for pc in lp.palavrasChave if pc.palavraChave]
        if kws:
            content += f"Palavras-chave: {', '.join(kws)}\n"
            
        sectors = [sa.setorAplicacao.nome for sa in lp.setoresAplicacao if sa.setorAplicacao]
        if sectors:
            content += f"Setores de Atividade/Aplicação: {', '.join(sectors)}\n"
            
        if lp.grupo:
            sig = lp.grupo.instituicao.sigla if lp.grupo.instituicao else ''
            content += f"Grupo de Pesquisa Associado: {lp.grupo.nome} ({sig})\n"
            
        await save_rag_document('LINHA_PESQUISA', lp.id, lp.titulo, content, {"grupoId": lp.grupoId})
        linhas_sincronizadas += 1
        
    print(f"[ETL-IA] Linhas de Pesquisa processadas: {linhas_sincronizadas} sincronizadas.")
    print('🎉 Sincronização incremental concluída com sucesso!')

async def main():
    await db.connect()
    try:
        await sync_db()
    except Exception as e:
        print("❌ Erro fatal no script de sincronização:", e)
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
