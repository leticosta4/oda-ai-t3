import os
import json
from db.client import db
from scraper.config import DGP_DATA_DIR


async def repopulate_queue():
    print(f"[Queue] Lendo arquivos locais de grupos DGP em: {DGP_DATA_DIR}")

    if not os.path.exists(DGP_DATA_DIR):
        print(f"[Queue] Diretório DGP {DGP_DATA_DIR} não existe.")
        return

    files = [f for f in os.listdir(DGP_DATA_DIR) if f.endswith(".json")]
    print(f"[Queue] Encontrados {len(files)} arquivos JSON.")

    added_count = 0
    skipped_count = 0

    for file in files:
        file_path = os.path.join(DGP_DATA_DIR, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "membros" not in data or not isinstance(data["membros"], list):
                print(f"[Queue] Arquivo {file} não contém a lista de membros.")
                continue

            print(f"[Queue] Processando membros do grupo: {data.get('nome') or file}")

            for p in data["membros"]:
                lattes = p.get("lattes")
                if not lattes:
                    print(
                        f"[Queue] Membro {p.get('nome')} sem ID Lattes no arquivo {file}. Pulando..."
                    )
                    continue

                row = await db.filaextracaopesquisador.find_unique(
                    where={"lattesId": lattes}
                )

                if not row:
                    await db.filaextracaopesquisador.create(
                        data={
                            "lattesId": lattes,
                            "nome": p.get("nome"),
                            "status": "PENDENTE",
                        }
                    )
                    added_count += 1
                else:
                    skipped_count += 1
        except Exception as e:
            print(f"[Queue] Erro ao processar arquivo {file}: {str(e)}")

    total_pending = await db.filaextracaopesquisador.count(where={"status": "PENDENTE"})
    total_concluido = await db.filaextracaopesquisador.count(
        where={"status": "CONCLUIDO"}
    )
    total_proc = await db.filaextracaopesquisador.count(where={"status": "PROCESSANDO"})
    print(
        f"[Queue] Status da fila: PENDENTE={total_pending}, CONCLUIDO={total_concluido}, PROCESSANDO={total_proc}"
    )
    print(
        f"[Queue] Repopulação concluída. Adicionados: {added_count}, Pulados: {skipped_count}"
    )
