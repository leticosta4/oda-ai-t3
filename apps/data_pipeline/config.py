import logging
import sys

DATA_DIR = "./data"
ISSUES_LOG = f"{DATA_DIR}/issues.log"
APP_LOG = f"{DATA_DIR}/scraper.log"
DB_FILE = f"{DATA_DIR}/scraper_estado.db"
DISCOVERY_LOG = f"{DATA_DIR}/discovery.log"


# Configurações do ETL (Apache Hop)
# Se estiver rodando fora do Docker, use localhost:8080. 
# Se estiver dentro de outro container no mesmo network, use hop-web:8080.
HOP_SERVER_URL = "http://localhost:8080/hop" 
HOP_USER = "cluster"
HOP_PASS = "cluster"
HOP_WORKFLOW_PATH = "/files/apps/data_pipeline/hop/workflows/main_workflow.hwf"
ETL_BATCH_SIZE = 50 # Executar ETL a cada 50 grupos

dgp_logger = logging.getLogger("DgpScraper")
dgp_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
dgp_logger.addHandler(stdout_handler)

file_handler = logging.FileHandler(APP_LOG, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
dgp_logger.addHandler(file_handler)

issues_handler = logging.FileHandler(ISSUES_LOG, encoding="utf-8")
issues_handler.setLevel(logging.ERROR)
issues_handler.setFormatter(formatter)
dgp_logger.addHandler(issues_handler)




sonda_logger = logging.getLogger("DiscoverySonda")
sonda_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
sonda_logger.addHandler(stdout_handler)

file_handler = logging.FileHandler(DISCOVERY_LOG, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
sonda_logger.addHandler(file_handler)