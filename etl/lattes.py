import os
import json
from db.client import db
from etl.common import (
    PROCESSED_DATA_DIR, LATTES_DIR,
    link_production_qualis
)

async def save_researcher_productions(tx, pesquisador_id: str, artigos: list, livros_capitulos: list):
    # Articles
    for artigo in artigos:
        titulo = artigo.get("titulo")
        if not titulo:
            continue
            
        ano_str = re_digits(artigo.get("ano"))
        ano_int = int(ano_str) if ano_str else None
        clean_doi = artigo.get("doi", "").strip() if artigo.get("doi") else None
        
        producao = None
        if clean_doi:
            producao = await tx.producao.find_unique(where={"doi": clean_doi})
            
        if not producao:
            producao = await tx.producao.find_first(
                where={
                    "titulo": {"equals": titulo.strip(), "mode": "insensitive"},
                    "ano": ano_int
                }
            )
            
        issn = artigo.get("issn") or artigo.get("ISSN") or None
        qualis = await link_production_qualis(issn) if issn else None
        
        if not producao:
            producao = await tx.producao.create(
                data={
                    "titulo": titulo.strip(),
                    "ano": ano_int,
                    "tipo": "ARTIGO",
                    "doi": clean_doi,
                    "url": artigo.get("url"),
                    "veiculo": artigo.get("veiculo") or artigo.get("nomePeriodico"),
                    "issn": issn,
                    "qualis": qualis,
                    "resumo": artigo.get("resumo")
                }
            )
        else:
            producao = await tx.producao.update(
                where={"id": producao.id},
                data={
                    "doi": clean_doi or producao.doi,
                    "veiculo": artigo.get("nomePeriodico") or artigo.get("veiculo") or producao.veiculo,
                    "resumo": artigo.get("resumo") or producao.resumo,
                    "issn": issn or producao.issn,
                    "qualis": qualis or (await link_production_qualis(producao.issn) if producao.issn else None)
                }
            )
            
        # Upsert relation
        rel = await tx.producaopesquisador.find_unique(
            where={
                "producaoId_pesquisadorId": {
                    "producaoId": producao.id,
                    "pesquisadorId": pesquisador_id
                }
            }
        )
        if not rel:
            await tx.producaopesquisador.create(
                data={
                    "producaoId": producao.id,
                    "pesquisadorId": pesquisador_id
                }
            )
            
    # Books / Chapters
    for livro in livros_capitulos:
        titulo = livro.get("titulo")
        if not titulo:
            continue
            
        ano_str = re_digits(livro.get("ano"))
        ano_int = int(ano_str) if ano_str else None
        clean_doi = livro.get("doi", "").strip() if livro.get("doi") else None
        
        producao = None
        if clean_doi:
            producao = await tx.producao.find_unique(where={"doi": clean_doi})
            
        if not producao:
            producao = await tx.producao.find_first(
                where={
                    "titulo": {"equals": titulo.strip(), "mode": "insensitive"},
                    "ano": ano_int
                }
            )
            
        if not producao:
            producao = await tx.producao.create(
                data={
                    "titulo": titulo.strip(),
                    "ano": ano_int,
                    "tipo": "LIVROCAPITULO",
                    "doi": clean_doi,
                    "url": livro.get("url"),
                    "veiculo": livro.get("editora") or livro.get("veiculo"),
                }
            )
        else:
            producao = await tx.producao.update(
                where={"id": producao.id},
                data={
                    "doi": clean_doi or producao.doi,
                    "veiculo": livro.get("editora") or livro.get("veiculo") or producao.veiculo
                }
            )
            
        rel = await tx.producaopesquisador.find_unique(
            where={
                "producaoId_pesquisadorId": {
                    "producaoId": producao.id,
                    "pesquisadorId": pesquisador_id
                }
            }
        )
        if not rel:
            await tx.producaopesquisador.create(
                data={
                    "producaoId": producao.id,
                    "pesquisadorId": pesquisador_id
                }
            )

def re_digits(val) -> str:
    if not val:
        return ""
    import re
    return "".join(re.findall(r"\d", str(val)))

async def save_lattes_to_db(data: dict):
    print(f"[ETL] 📡 Processando dados do pesquisador {data.get('nome')}...")
    
    orcid_id = data.get("orcidId")
    if orcid_id:
        orcid_id = orcid_id.split("/")[-1].strip()
        data["orcidId"] = orcid_id
        
    artigos = data.get("artigos", [])
    livros_capitulos = data.get("livrosCapitulos", [])
    
    try:
        async with db.transaction() as tx:
            lattes_id = data.get("lattes", "").strip()
            pesquisador = await tx.pesquisador.find_first(
                where={"lattesId": lattes_id}
            )
            
            if pesquisador:
                await tx.pesquisador.update(
                    where={"id": pesquisador.id},
                    data={
                        "orcidId": data.get("orcidId") or None,
                        "imageUrl": f"/static/{lattes_id}.webp"
                    }
                )
                
                await save_researcher_productions(tx, pesquisador.id, artigos, livros_capitulos)
                
                # Update queue status
                await tx.filaextracaopesquisador.upsert(
                    where={"lattesId": lattes_id},
                    data={
                        "update": {"status": "CONCLUIDO"},
                        "create": {
                            "lattesId": lattes_id,
                            "nome": data.get("nome"),
                            "status": "CONCLUIDO"
                        }
                    }
                )
                print(f"[ETL] ✅ Lattes e produções de {data.get('nome')} processados com sucesso.")
            else:
                print(f"[ETL] ⚠️ Pesquisador {data.get('nome')} não encontrado no banco de dados relacional.")
    except Exception as e:
        print(f"[ETL] ❌ Erro no Lattes de {data.get('nome')}: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_pesquisador_etl(json_path: str):
    print(f"[ETL] 🔍 Iniciando processamento do arquivo de pesquisador: {json_path}")
    resolved_path = os.path.abspath(json_path)
    if not os.path.exists(resolved_path):
        print(f"[ETL] ⚠️ Arquivo de origem não existe: {json_path}")
        return
        
    with open(resolved_path, "r", encoding="utf-8") as f:
        lattes_data = json.load(f)
        
    await save_lattes_to_db(lattes_data)
    
    # Move to processed data dir
    file_name = os.path.basename(resolved_path)
    processed_lattes_dir = os.path.join(PROCESSED_DATA_DIR, "lattes")
    os.makedirs(processed_lattes_dir, exist_ok=True)
    dest_path = os.path.join(processed_lattes_dir, file_name)
    
    if resolved_path != dest_path:
        try:
            if os.path.exists(resolved_path):
                os.rename(resolved_path, dest_path)
                print(f"[ETL] 📁 JSON Lattes {file_name} movido para {dest_path}")
        except Exception as e:
            print(f"[ETL] ⚠️ Não foi possível mover o arquivo Lattes {file_name}: {str(e)}")
