import os
import json
import re
from db.client import db
from etl.common import (
    PROCESSED_DATA_DIR, DGP_DIR, LATTES_DIR,
    get_or_create_area_conhecimento_hierarchy, create_linha_pesquisa
)
from etl.lattes import run_pesquisador_etl

async def save_group_to_db(data: dict):
    dgp_id = data.get("idDgp")
    if not dgp_id:
        return
        
    grupo_id = ""
    try:
        # Find institution
        async with db.transaction() as tx:
            inst_sigla_row = await tx.filaextracaogrupo.find_first(where={"dgpId": dgp_id})
            inst_sigla = inst_sigla_row.instituicao if inst_sigla_row else ""
            
            inst_raw = data.get("instituicao", "")
            inst_clean = inst_raw.replace(inst_sigla, "").replace("-", "").strip()
            inst_name = inst_clean or "Instituição Desconhecida"
            
            instituicao = await tx.instituicao.find_first(
                where={"nome": {"contains": inst_name, "mode": "insensitive"}}
            )
            
            if not instituicao:
                sigla = inst_sigla.strip() if inst_sigla else "INST"
                estado = await tx.estado.find_unique(where={"sigla": "BA"})
                instituicao = await tx.instituicao.create(
                    data={
                        "nome": inst_name,
                        "sigla": sigla,
                        "estadoId": estado.id if estado else None
                    }
                )
                
            ano_str = "".join(re.findall(r"\d", str(data.get("anoFormacao", ""))))
            ano = int(ano_str) if ano_str else None
            
            # Upsert GroupPesquisa
            grupo = await tx.grupopesquisa.find_unique(where={"dgpId": dgp_id})
            if grupo:
                grupo = await tx.grupopesquisa.update(
                    where={"dgpId": dgp_id},
                    data={
                        "nome": data.get("nome", "").strip(),
                        "anoFormacao": ano,
                        "areaPredominante": data.get("areaPredominante", "").strip() or "N/A",
                        "repercussao": data.get("repercussao", "").strip() or None,
                        "instituicaoId": instituicao.id
                    }
                )
            else:
                grupo = await tx.grupopesquisa.create(
                    data={
                        "dgpId": dgp_id,
                        "nome": data.get("nome", "").strip(),
                        "anoFormacao": ano,
                        "areaPredominante": data.get("areaPredominante", "").strip() or "N/A",
                        "repercussao": data.get("repercussao", "").strip() or None,
                        "instituicaoId": instituicao.id
                    }
                )
                
            leaf_area = await get_or_create_area_conhecimento_hierarchy(tx, data.get("area") or data.get("areaPredominante"))
            if leaf_area:
                rel = await tx.grupopesquisaareaconhecimento.find_unique(
                    where={
                        "grupoId_areaId": {
                            "grupoId": grupo.id,
                            "areaId": leaf_area.id
                        }
                    }
                )
                if not rel:
                    await tx.grupopesquisaareaconhecimento.create(
                        data={
                            "grupoId": grupo.id,
                            "areaId": leaf_area.id
                        }
                    )
            grupo_id = grupo.id
            
        print(f"[ETL] 🏢 Grupo \"{data.get('nome')}\" (ID: {grupo_id}) inserido e confirmado.")
        
        # Process lines of research
        linhas = data.get("linhas", [])
        if isinstance(linhas, list):
            async with db.transaction() as tx:
                # Delete relations
                # Find lines associated with this group
                gp_lines = await tx.linhapesquisa.find_many(where={"grupoId": grupo_id})
                gp_line_ids = [l.id for l in gp_lines]
                
                if gp_line_ids:
                    await tx.membrolinhapesquisa.delete_many(where={"linhaPesquisaId": {"in": gp_line_ids}})
                    await tx.linhapesquisapalavrachave.delete_many(where={"linhaPesquisaId": {"in": gp_line_ids}})
                    await tx.linhapesquisasetoraplicacao.delete_many(where={"linhaPesquisaId": {"in": gp_line_ids}})
                    await tx.linhapesquisa.delete_many(where={"grupoId": grupo_id})
                    
                for linha in linhas:
                    title = linha.get("nome")
                    if not title:
                        continue
                    palavras = linha.get("palavrasChave", [])
                    setores = linha.get("setoresAplicacao", [])
                    
                    nova_linha = await create_linha_pesquisa(
                        tx,
                        grupo_id,
                        title.strip(),
                        linha.get("dgpId"),
                        linha.get("objetivo"),
                        palavras,
                        setores
                    )
                    print(f"[ETL] 🔬 Linha de Pesquisa criada -> ID: {nova_linha.id} | Nome: \"{nova_linha.titulo}\"")
            print("[ETL] ✅ Linhas de pesquisa inseridas e confirmadas.")
            
        # Process members
        membros = data.get("membros", [])
        if isinstance(membros, list):
            async with db.transaction() as tx:
                for membro in membros:
                    nome = membro.get("nome")
                    if not nome:
                        continue
                    clean_lattes = membro.get("lattes", "").strip() if membro.get("lattes") else None
                    if not clean_lattes:
                        continue
                        
                    raw_tipo = membro.get("categoriaLattes", "").strip().upper()
                    tipo_map = {
                        'PESQUISADOR': 'PESQUISADOR',
                        'LIDER': 'PESQUISADOR',
                        'ESTUDANTE': 'ESTUDANTE',
                        'TECNICO': 'TECNICO',
                        'ESTRANGERO': 'COLABORADOR_ESTRANGEIRO',
                        'ESTRANGEIRO': 'COLABORADOR_ESTRANGEIRO',
                        'COLABORADOR_ESTRANGEIRO': 'COLABORADOR_ESTRANGEIRO'
                    }
                    tipo = tipo_map.get(raw_tipo)
                    
                    raw_form = membro.get("formacaoAcademica", "").strip().upper()
                    # Strip accents
                    import unicodedata
                    raw_form = unicodedata.normalize('NFD', raw_form)
                    raw_form = "".join(c for c in raw_form if unicodedata.category(c) != 'Mn')
                    
                    form_map = {
                        'GRADUACAO': 'GRADUACAO',
                        'ESPECIALIZACAO': 'ESPECIALIZACAO',
                        'MESTRADO': 'MESTRADO',
                        'DOUTORADO': 'DOUTORADO'
                    }
                    formacao = form_map.get(raw_form, 'OUTRO') if raw_form else None
                    
                    pesquisador = await tx.pesquisador.find_unique(where={"lattesId": clean_lattes})
                    if pesquisador:
                        pesquisador = await tx.pesquisador.update(
                            where={"id": pesquisador.id},
                            data={
                                "formacaoAcademica": formacao,
                                "tipo": tipo
                            }
                        )
                    else:
                        pesquisador = await tx.pesquisador.create(
                            data={
                                "nome": nome.strip(),
                                "lattesId": clean_lattes,
                                "tipo": tipo,
                                "formacaoAcademica": formacao
                            }
                        )
                        
                    areas = membro.get("areas", [])
                    if isinstance(areas, list):
                        for area_str in areas:
                            if not area_str.strip():
                                continue
                            leaf_area = await get_or_create_area_conhecimento_hierarchy(tx, area_str)
                            if leaf_area:
                                rel = await tx.pesquisadoresareaconhecimento.find_unique(
                                    where={
                                        "pesquisadorId_areaId": {
                                            "pesquisadorId": pesquisador.id,
                                            "areaId": leaf_area.id
                                        }
                                    }
                                )
                                if not rel:
                                    await tx.pesquisadoresareaconhecimento.create(
                                        data={
                                            "pesquisadorId": pesquisador.id,
                                            "areaId": leaf_area.id
                                        }
                                    )
                                    
                    linhas_assoc = membro.get("linhasAssociadas", [])
                    if isinstance(linhas_assoc, list):
                        for linha_titulo in linhas_assoc:
                            if not linha_titulo.strip():
                                continue
                            # Find associated line
                            linha_obj = await tx.linhapesquisa.find_first(
                                where={
                                    "grupoId": grupo_id,
                                    "titulo": {"equals": linha_titulo.strip(), "mode": "insensitive"}
                                }
                            )
                            if linha_obj:
                                rel = await tx.membrolinhapesquisa.find_unique(
                                    where={
                                        "linhaPesquisaId_pesquisadorId": {
                                            "linhaPesquisaId": linha_obj.id,
                                            "pesquisadorId": pesquisador.id
                                        }
                                    }
                                )
                                if not rel:
                                    await tx.membrolinhapesquisa.create(
                                        data={
                                            "linhaPesquisaId": linha_obj.id,
                                            "pesquisadorId": pesquisador.id
                                        }
                                    )
                                    
                    # Join group relation
                    rel = await tx.membrogrupo.find_unique(
                        where={
                            "pesquisadorId_grupoId": {
                                "pesquisadorId": pesquisador.id,
                                "grupoId": grupo_id
                            }
                        }
                    )
                    if not rel:
                        await tx.membrogrupo.create(
                            data={
                                "pesquisadorId": pesquisador.id,
                                "grupoId": grupo_id
                            }
                        )
            print("[ETL] 👥 Pesquisadores vinculados ao grupo.")
            
        print(f"[ETL] ✅ Processamento do Grupo {dgp_id} concluído.")
        await db.filaextracaogrupo.update(
            where={"dgpId": dgp_id},
            data={"status": "CONCLUIDO"}
        )
    except Exception as e:
        print(f"[ETL] ❌ Erro ao processar grupo {dgp_id}: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_group_etl(json_path: str):
    print(f"[ETL] 🔍 Iniciando processamento do arquivo de grupo: {json_path}")
    resolved_path = os.path.abspath(json_path)
    if not os.path.exists(resolved_path):
        print(f"[ETL] ⚠️ Arquivo de grupo não encontrado: {json_path}")
        return
        
    with open(resolved_path, "r", encoding="utf-8") as f:
        group_data = json.load(f)
        
    await save_group_to_db(group_data)
    
    # Chain ETL for group members
    membros = group_data.get("membros", [])
    if isinstance(membros, list):
        print(f"[ETL] Encontrados {len(membros)} membros elegíveis no grupo.")
        for membro in membros:
            lattes_id = membro.get("lattes")
            if not lattes_id:
                continue
            lattes_file_path = os.path.join(LATTES_DIR, f"{lattes_id.strip()}.json")
            if os.path.exists(lattes_file_path):
                print(f"[ETL] 👤 Iniciando ETL encadeado do pesquisador: {membro.get('nome')}")
                await run_pesquisador_etl(lattes_file_path)
                
    # Move to processed data dir
    file_name = os.path.basename(resolved_path)
    processed_dgp_dir = os.path.join(PROCESSED_DATA_DIR, "dgp")
    os.makedirs(processed_dgp_dir, exist_ok=True)
    dest_path = os.path.join(processed_dgp_dir, file_name)
    
    if resolved_path != dest_path:
        try:
            if os.path.exists(resolved_path):
                os.rename(resolved_path, dest_path)
                print(f"[ETL] 📁 JSON Grupo {file_name} movido para {dest_path}")
        except Exception as e:
            print(f"[ETL] ⚠️ Não foi possível mover o arquivo Grupo {file_name}: {str(e)}")
