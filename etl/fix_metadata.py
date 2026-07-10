import os
import json
from db.client import db
from etl.common import PROCESSED_DATA_DIR, link_production_qualis

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
    fix_qualis = False
    
    for flag in args:
        if flag == '-qualis':
            fix_qualis = True
        
    if not fix_qualis:
        print('[FIX] Nenhuma flag informada.')
        print('Uso: python -m etl.main fix -qualis')
        return
        
    if fix_qualis:
        await run_fix_qualis()
        
    print('[FIX] Processamento concluído.')
