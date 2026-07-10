import os
import json
import re
from db.client import db

ROOT_DIR = os.getcwd()
DATA_DIR = os.path.abspath(os.path.join(ROOT_DIR, "data"))
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw-data")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed-data")
DGP_DIR = os.path.join(RAW_DATA_DIR, "dgp")
LATTES_DIR = os.path.join(RAW_DATA_DIR, "lattes")
DOI_URL = "https://citation.doi.org/metadata?doi="

for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, DGP_DIR, LATTES_DIR]:
    os.makedirs(d, exist_ok=True)

def normalize_string(s: str) -> str:
    if not s:
        return ""
        
    stopwords = {
        # Português
        'de', 'do', 'da', 'dos', 'das', 'em', 'um', 'uma', 'uns', 'umas', 
        'para', 'com', 'por', 'sem', 'sob', 'sobre', 'a', 'o', 'as', 'os', 'e',
        # Inglês
        'of', 'the', 'in', 'on', 'at', 'for', 'with', 'by', 'a', 'an', 'and', 'to', 'from', 'about'
    }

    import unicodedata
    s_clean = s.strip().lower()
    s_clean = unicodedata.normalize('NFD', s_clean)
    s_clean = "".join(c for c in s_clean if unicodedata.category(c) != 'Mn')
    s_clean = re.sub(r'[^a-z0-9\s]', ' ', s_clean)
    s_clean = re.sub(r'\s+', ' ', s_clean)
    words = s_clean.split()
    
    filtered_words = [w for w in words if w and w not in stopwords]
    return "-".join(filtered_words)

def strip_html(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'<[^>]*>', '', s).strip()

# Qualis database cache
_qualis_map = None

def load_qualis_map():
    global _qualis_map
    if _qualis_map is not None:
        return _qualis_map
        
    _qualis_map = {}
    qualis_paths = [
        os.path.join(ROOT_DIR, "qualis-capes-2017-2020.json"),
        os.path.join(ROOT_DIR, "etl", "qualis-capes-2017-2020.json")
    ]
    for path in qualis_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    issn = item.get("issn")
                    qualis = item.get("qualis")
                    if issn and qualis:
                        clean_issn = issn.replace("-", "").strip().upper()
                        _qualis_map[clean_issn] = qualis
                print(f"[Qualis] Carregado qualis map com {len(_qualis_map)} ISSNs.")
                break
            except Exception as e:
                print(f"[Qualis] Erro ao carregar {path}: {str(e)}")
    return _qualis_map

async def link_production_qualis(issn: str) -> str:
    if not issn:
        return None
    q_map = load_qualis_map()
    clean_issn = issn.replace("-", "").strip().upper()
    return q_map.get(clean_issn)

# Database Transaction Helpers
async def get_or_create_area_conhecimento_hierarchy(tx, area_str: str):
    if not area_str:
        return None
    parts = [p.strip() for p in re.split(r'[>;]', area_str) if p.strip()]
    current_parent_id = None
    leaf_area = None

    for part in parts:
        nome_normalizado = normalize_string(part)
        # We simulate upsert using try-except or find/create
        area = await tx.areaconhecimento.find_unique(where={"nomeNormalizado": nome_normalizado})
        if area:
            area = await tx.areaconhecimento.update(
                where={"nomeNormalizado": nome_normalizado},
                data={"areaPaiId": current_parent_id}
            )
        else:
            area = await tx.areaconhecimento.create(
                data={
                    "nome": part,
                    "nomeNormalizado": nome_normalizado,
                    "areaPaiId": current_parent_id
                }
            )
        current_parent_id = area.id
        leaf_area = area
    return leaf_area

async def upsert_palavra_chave(tx, termo: str):
    termo_normalizado = normalize_string(termo)
    pc = await tx.palavrachave.find_unique(where={"termoNormalizado": termo_normalizado})
    if not pc:
        pc = await tx.palavrachave.create(
            data={
                "termo": termo.strip(),
                "termoNormalizado": termo_normalizado
            }
        )
    return pc

async def upsert_setor_aplicacao(tx, nome: str):
    nome_normalizado = normalize_string(nome)
    sa = await tx.setoraplicacao.find_unique(where={"nomeNormalizado": nome_normalizado})
    if not sa:
        sa = await tx.setoraplicacao.create(
            data={
                "nome": nome.strip(),
                "nomeNormalizado": nome_normalizado
            }
        )
    return sa

async def create_linha_pesquisa(tx, grupo_id: str, titulo: str, dgp_id: str, objetivo: str, palavras: list, setores: list):
    linha = None
    if dgp_id:
        linha = await tx.linhapesquisa.find_unique(where={"dgpId": dgp_id})
        if linha:
            linha = await tx.linhapesquisa.update(
                where={"dgpId": dgp_id},
                data={
                    "titulo": titulo.strip(),
                    "objetivo": objetivo.strip() if objetivo else None,
                    "grupoId": grupo_id
                }
            )
        else:
            linha = await tx.linhapesquisa.create(
                data={
                    "dgpId": dgp_id,
                    "titulo": titulo.strip(),
                    "objetivo": objetivo.strip() if objetivo else None,
                    "grupoId": grupo_id
                }
            )
    else:
        linha = await tx.linhapesquisa.create(
            data={
                "titulo": titulo.strip(),
                "objetivo": objetivo.strip() if objetivo else None,
                "grupoId": grupo_id
            }
        )
        
    unique_pc_ids = set()
    for termo in palavras:
        if not termo.strip():
            continue
        pc = await upsert_palavra_chave(tx, termo)
        unique_pc_ids.add(pc.id)
        
    for pc_id in unique_pc_ids:
        # Upsert relation
        rel = await tx.linhapesquisapalavrachave.find_unique(
            where={
                "linhaPesquisaId_palavraChaveId": {
                    "linhaPesquisaId": linha.id,
                    "palavraChaveId": pc_id
                }
            }
        )
        if not rel:
            await tx.linhapesquisapalavrachave.create(
                data={
                    "linhaPesquisaId": linha.id,
                    "palavraChaveId": pc_id
                }
            )
            
    unique_sa_ids = set()
    for nome in setores:
        if not nome.strip():
            continue
        sa = await upsert_setor_aplicacao(tx, nome)
        unique_sa_ids.add(sa.id)
        
    for sa_id in unique_sa_ids:
        rel = await tx.linhapesquisasetoraplicacao.find_unique(
            where={
                "linhaPesquisaId_setorAplicacaoId": {
                    "linhaPesquisaId": linha.id,
                    "setorAplicacaoId": sa_id
                }
            }
        )
        if not rel:
            await tx.linhapesquisasetoraplicacao.create(
                data={
                    "linhaPesquisaId": linha.id,
                    "setorAplicacaoId": sa_id
                }
            )
            
    return linha
