import os
import sys
import asyncio
import time
from dotenv import load_dotenv
load_dotenv()

from db.client import db
from etl.common import DGP_DIR, LATTES_DIR, PROCESSED_DATA_DIR
from etl.dgp import run_group_etl
from etl.lattes import run_pesquisador_etl
from etl.fix_metadata import run_fix_metadata
from etl.run_all import run_all

# Helper search functions
def find_group_file(id_or_path: str) -> str:
    if os.path.isfile(id_or_path):
        return os.path.abspath(id_or_path)
    file_name = id_or_path if id_or_path.endswith('.json') else f"{id_or_path}.json"
    raw_path = os.path.join(DGP_DIR, file_name)
    if os.path.exists(raw_path):
        return raw_path
    processed_path = os.path.join(PROCESSED_DATA_DIR, 'dgp', file_name)
    if os.path.exists(processed_path):
        return processed_path
    raise FileNotFoundError(f"Arquivo de grupo não encontrado para o ID ou Caminho: '{id_or_path}'")

def find_lattes_file(id_or_path: str) -> str:
    if os.path.isfile(id_or_path):
        return os.path.abspath(id_or_path)
    file_name = id_or_path if id_or_path.endswith('.json') else f"{id_or_path}.json"
    raw_path = os.path.join(LATTES_DIR, file_name)
    if os.path.exists(raw_path):
        return raw_path
    processed_path = os.path.join(PROCESSED_DATA_DIR, 'lattes', file_name)
    if os.path.exists(processed_path):
        return processed_path
    raise FileNotFoundError(f"Arquivo de currículo Lattes não encontrado para o ID ou Caminho: '{id_or_path}'")

# Watchdog handler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EtlWatchdogHandler(FileSystemEventHandler):
    def __init__(self, loop):
        self.loop = loop

    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.json'):
            return
        
        path = event.src_path
        # Delay slightly to ensure file write finishes
        time.sleep(1)
        
        print(f"[Watcher] Novo arquivo detectado: {path}")
        if 'dgp' in path.lower() or 'espelhogrupo' in path.lower():
            asyncio.run_coroutine_threadsafe(run_group_etl(path), self.loop)
        elif 'lattes' in path.lower():
            asyncio.run_coroutine_threadsafe(run_pesquisador_etl(path), self.loop)

def start_watcher(loop):
    observer = Observer()
    handler = EtlWatchdogHandler(loop)
    
    # Watch DGP_DIR and LATTES_DIR
    for d in [DGP_DIR, LATTES_DIR]:
        if os.path.exists(d):
            observer.schedule(handler, d, recursive=False)
            print(f"[ETL] Monitorando diretório: {d}")
            
    observer.start()
    print('[ETL] Modo Watcher ativo. Aguardando arquivos...')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

async def main():
    args = sys.argv[1:]
    command = args[0] if args else None
    
    print('---------------------------------------------------------')
    print('🚀 Serviço de ETL Open DGP (Python)')
    print('---------------------------------------------------------')
    
    await db.connect()
    
    try:
        if not command:
            # Run watchdog in background/blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, start_watcher, loop)
            return

        if command in ['grupo', 'group']:
            if len(args) < 2:
                print("Erro: ID DGP ou Caminho do arquivo JSON do grupo não especificado.")
                print("Uso: python -m etl.main grupo <id_dgp_ou_caminho>")
                sys.exit(1)
            resolved = find_group_file(args[1])
            await run_group_etl(resolved)
            
        elif command in ['pesquisador', 'lattes']:
            if len(args) < 2:
                print("Erro: ID Lattes ou Caminho do arquivo JSON do pesquisador não especificado.")
                print("Uso: python -m etl.main pesquisador <id_lattes_ou_caminho>")
                sys.exit(1)
            resolved = find_lattes_file(args[1])
            await run_pesquisador_etl(resolved)
            
        elif command in ['fix', 'fix-metadata']:
            await run_fix_metadata(args[1:])
            
        elif command == 'run-all':
            await run_all()
            
        else:
            print(f"Erro: Comando desconhecido '{command}'")
            print("Comandos disponíveis: grupo, pesquisador, fix, run-all")
            sys.exit(1)
            
    except Exception as e:
        print("❌ Erro fatal durante a execução do ETL:", str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
