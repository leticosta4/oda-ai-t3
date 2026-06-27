import * as chokidar from 'chokidar';
import * as fs from 'fs';
import * as dotenv from 'dotenv';
import path from 'path';
dotenv.config({
  path: path.resolve(__dirname, "../../../.env"),
});
import { DGP_DIR, LATTES_DIR, PROCESSED_DATA_DIR } from './commom/config';
import { runGroupEtl, saveGroupToDb } from './dgpEtl';
import { runPesquisadorEtl, saveLattesToDb } from './lattesEtl';


console.log('---------------------------------------------------------');
console.log('🚀 Serviço de ETL Open DGP (TypeScript)');
console.log('---------------------------------------------------------');

function startWatcher() {
    const watcher = chokidar.watch([DGP_DIR, LATTES_DIR], {
        ignored: /(^|[\/\\])\../,
        persistent: true,
        awaitWriteFinish: true
    });

    watcher.on('add', (filePath) => {
        if (!filePath.endsWith('.json')) return;
        
        try {
            if (filePath.includes('dgp')) {
                runGroupEtl(filePath);
            } else if (filePath.includes('lattes')) {
                runPesquisadorEtl(filePath);
            }
        } catch (e: any) {
            console.error(`[ETL] Erro ao processar arquivo no watcher ${filePath}: ${e.message}`);
        }
    });

    console.log('[ETL] Modo Watcher ativo. Aguardando arquivos...');
}

function findGroupFile(idOrPath: string): string {
    if (fs.existsSync(idOrPath) && fs.statSync(idOrPath).isFile()) {
        return path.resolve(idOrPath);
    }
    const fileName = idOrPath.endsWith('.json') ? idOrPath : `${idOrPath}.json`;
    const rawPath = path.join(DGP_DIR, fileName);
    if (fs.existsSync(rawPath)) return rawPath;
    const processedPath = path.join(PROCESSED_DATA_DIR, 'dgp', fileName);
    if (fs.existsSync(processedPath)) return processedPath;
    throw new Error(`Arquivo de grupo não encontrado para o ID ou Caminho: "${idOrPath}"`);
}

function findLattesFile(idOrPath: string): string {
    if (fs.existsSync(idOrPath) && fs.statSync(idOrPath).isFile()) {
        return path.resolve(idOrPath);
    }
    const fileName = idOrPath.endsWith('.json') ? idOrPath : `${idOrPath}.json`;
    const rawPath = path.join(LATTES_DIR, fileName);
    if (fs.existsSync(rawPath)) return rawPath;
    const processedPath = path.join(PROCESSED_DATA_DIR, 'lattes', fileName);
    if (fs.existsSync(processedPath)) return processedPath;
    throw new Error(`Arquivo de currículo Lattes não encontrado para o ID ou Caminho: "${idOrPath}"`);
}

async function main() {
    const args = process.argv.slice(2);
    const command = args[0];

    if (!command) {
        startWatcher();
        return;
    }

    try {
        switch (command) {
            case 'grupo':
            case 'group': {
                const idOrPath = args[1];
                if (!idOrPath) {
                    console.error("Erro: ID DGP ou Caminho do arquivo JSON do grupo não especificado.");
                    console.log("Uso: pnpm start grupo <id_dgp_ou_caminho>");
                    process.exit(1);
                }
                const resolvedPath = findGroupFile(idOrPath);
                await runGroupEtl(resolvedPath);
                break;
            }
            case 'pesquisador':
            case 'lattes': {
                const idOrPath = args[1];
                if (!idOrPath) {
                    console.error("Erro: ID Lattes ou Caminho do arquivo JSON do pesquisador não especificado.");
                    console.log("Uso: pnpm start pesquisador <id_lattes_ou_caminho>");
                    process.exit(1);
                }
                const resolvedPath = findLattesFile(idOrPath);
                await runPesquisadorEtl(resolvedPath);
                break;
            }
            default:
                console.error(`Erro: Comando desconhecido '${command}'`);
                console.log("Comandos disponíveis: grupo, pesquisador");
                process.exit(1);
        }
    } catch (error: any) {
        console.error("❌ Erro fatal durante a execução do ETL:", error.message);
        process.exit(1);
    }
}

main();
