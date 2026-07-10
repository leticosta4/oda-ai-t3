from db.client import db

def clean_str(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.split()).strip()

async def get_group_queue_discovery():
    return await db.filaextracaogrupo.find_many()

async def get_pesquisador_queue_discovery():
    return await db.filaextracaopesquisador.find_many()

async def normalize_queue_data():
    all_items = await db.filaextracaogrupo.find_many()
    updated_count = 0
    for item in all_items:
        clean_nome = clean_str(item.nome)
        clean_area = clean_str(item.area)
        clean_inst = clean_str(item.instituicao)
        
        if clean_nome != item.nome or clean_area != item.area or clean_inst != item.instituicao:
            await db.filaextracaogrupo.update(
                where={"dgpId": item.dgpId},
                data={
                    "nome": clean_nome,
                    "area": clean_area,
                    "instituicao": clean_inst
                }
            )
            item.nome = clean_nome
            item.area = clean_area
            item.instituicao = clean_inst
            updated_count += 1
            
    if updated_count > 0:
        print(f"[Database] Normalizadas strings de {updated_count} registros no banco.")
        
    items_after = await db.filaextracaogrupo.find_many()
    groups_map = {}
    for item in items_after:
        key = f"{item.nome}|{item.area}|{item.instituicao}"
        if key not in groups_map:
            groups_map[key] = []
        groups_map[key].append(item.dgpId)
        
    updated_similares = 0
    for key, dgp_ids in groups_map.items():
        count = len(dgp_ids)
        sample = next((i for i in items_after if i.dgpId == dgp_ids[0]), None)
        if sample and sample.similares != count:
            await db.filaextracaogrupo.update_many(
                where={"dgpId": {"in": dgp_ids}},
                data={"similares": count}
            )
            updated_similares += len(dgp_ids)
            
    if updated_similares > 0:
        print(f"[Database] Recalculado 'similares' para {updated_similares} registros no banco.")

async def group_queue_discovery(dgp_id: str, nome: str, area: str, instituicao: str):
    nome_limpo = clean_str(nome)
    area_limpa = clean_str(area)
    instituicao_limpa = clean_str(instituicao)
    
    return await db.filaextracaogrupo.upsert(
        where={"dgpId": dgp_id},
        data={
            "update": {
                "nome": nome_limpo,
                "area": area_limpa,
                "instituicao": instituicao_limpa
            },
            "create": {
                "dgpId": dgp_id,
                "nome": nome_limpo,
                "area": area_limpa,
                "instituicao": instituicao_limpa,
                "status": "PENDENTE",
                "similares": 1
            }
        }
    )

async def update_group_queue_status(dgp_id: str, status: str):
    return await db.filaextracaogrupo.update(
        where={"dgpId": dgp_id},
        data={"status": status}
    )

async def update_pesquisador_queue_status(lattes_id: str, status: str):
    return await db.filaextracaopesquisador.update(
        where={"lattesId": lattes_id},
        data={"status": status}
    )
