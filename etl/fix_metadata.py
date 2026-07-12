import os
import json
from db.client import db
from etl.common import PROCESSED_DATA_DIR, link_production_qualis, strip_html
from etl.lattes import link_production_doi

async def fix_single_doi(prod_id: str, doi: str):
    print(f"[FIX] 🔍 Processando DOI: \"{doi}\"...")
    extra = await link_production_doi(doi)
    if extra:
        abstract = extra.get("abstract")
        clean_abstract = strip_html(abstract) if abstract else None
        await db.producao.update(
            where={"id": prod_id},
            data={
                "resumo": clean_abstract or None,
                "veiculo": extra.get("publisher") or None,
                "url": extra.get("licenseUrl") or None
            }
        )
        print(f"[FIX] ✅ Produção com DOI \"{doi}\" atualizada.")
    else:
        print(f"[FIX] ❌ Falha ao buscar dados para o DOI: \"{doi}\".")

async def run_fix_qualis():
    print('[QUALIS] 📡 Iniciando varredura nos JSONs do Lattes...')
    lattes_folder = os.path.join(PROCESSED_DATA_DIR, 'lattes')
    if not os.path.exists(lattes_folder):
        print(f"[QUALIS] ❌ Pasta não encontrada: {lattes_folder}")
        return
        
    files = [f for f in os.listdir(lattes_folder) if f.endswith('.json')]
    print(f"[QUALIS] Encontrados {len(files)} arquivos JSON.")
    
    count_updated = 0
    for file in files:
        try:
            file_path = os.path.join(lattes_folder, file)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            artigos = data.get("artigos", [])
            if not isinstance(artigos, list):
                continue
                
            for artigo in artigos:
                issn = artigo.get("issn") or artigo.get("ISSN")
                if not issn:
                    continue
                    
                producao = None
                doi = artigo.get("doi")
                if doi:
                    producao = await db.producao.find_unique(where={"doi": doi.strip()})
                    
                if not producao and artigo.get("titulo"):
                    producao = await db.producao.find_first(
                        where={"titulo": {"equals": artigo["titulo"].strip(), "mode": "insensitive"}}
                    )
                    
                if producao:
                    qualis = await link_production_qualis(issn)
                    await db.producao.update(
                        where={"id": producao.id},
                        data={
                            "issn": issn,
                            "qualis": qualis or None
                        }
                    )
                    count_updated += 1
        except Exception as e:
            print(f"[QUALIS] Erro ao processar arquivo {file}: {str(e)}")
            
    print(f"[QUALIS] ✅ Sincronização de Qualis concluída. {count_updated} artigos atualizados.")

async def run_fix_metadata(args: list):
    fix_all_doi = False
    specific_doi = None
    fix_qualis = False
    
    i = 0
    while i < len(args):
        flag = args[i]
        if flag == '-doi':
            fix_all_doi = True
        elif flag == '-DOI' and i + 1 < len(args):
            specific_doi = args[i + 1]
            i += 1
        elif flag == '-qualis':
            fix_qualis = True
        i += 1
        
    if not any([fix_all_doi, specific_doi, fix_qualis]):
        print('[FIX] Nenhuma flag informada.')
        print('Uso: python -m etl.main fix [-doi] [-DOI <id/doi>] [-qualis]')
        return
        
    if fix_all_doi:
        print('[FIX] Buscando todas as produções com DOI...')
        producoes = await db.producao.find_many(where={"doi": {"not": None}})
        print(f"[FIX] Encontradas {len(producoes)} produções para reprocessar.")
        for prod in producoes:
            if prod.doi:
                await fix_single_doi(prod.id, prod.doi)
    elif specific_doi:
        print(f"[FIX] Buscando produção para DOI/ID: \"{specific_doi}\"...")
        prod = await db.producao.find_first(
            where={
                "OR": [
                    {"id": specific_doi},
                    {"doi": specific_doi}
                ]
            }
        )
        if prod and prod.doi:
            await fix_single_doi(prod.id, prod.doi)
        else:
            print(f"[FIX] Produção não encontrada para: \"{specific_doi}\"")
            
    if fix_qualis:
        await run_fix_qualis()
        
    print('[FIX] Processamento concluído.')
