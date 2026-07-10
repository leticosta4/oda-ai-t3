import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

from db.client import db
from scraper.discovery import run_dgp_discovery
from scraper.dgp import run_dgp_scraper
from scraper.lattes import run_lattes_scraper
from scraper.repopulate import repopulate_queue

async def main():
    args = sys.argv[1:]
    command = args[0] if args else "dgp-extract"
    
    print(f"[Pipeline] Iniciando Data Pipeline Python com comando: {command}")
    
    # Connect Prisma client
    await db.connect()
    
    try:
        if command in ["discovery", "dgp-discovery"]:
            keys = args[1:] if len(args) > 1 else ["a", "e", "i", "o", "u"]
            await run_dgp_discovery(keys)
        elif command in ["dgp", "dgp-extract"]:
            dgp_ids = args[1:]
            await run_dgp_scraper(dgp_ids)
        elif command in ["lattes", "lattes-scraper"]:
            names = args[1:]
            await run_lattes_scraper(names)
        elif command in ["repopulate", "repopulate-researchers"]:
            await repopulate_queue()
        elif command == "reset-queue":
            updated_count = await db.filaextracaopesquisador.update_many(
                where={"status": "PROCESSANDO"},
                data={"status": "PENDENTE"}
            )
            print(f"[Queue] Redefinidos {updated_count} pesquisadores de PROCESSANDO para PENDENTE.")
        else:
            print(f"[Pipeline] Erro: Comando desconhecido '{command}'")
            print("Comandos disponíveis: dgp-discovery, dgp-extract, lattes, repopulate, reset-queue")
            sys.exit(1)
    except Exception as e:
        print("[Pipeline] Erro fatal na execução:", e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
