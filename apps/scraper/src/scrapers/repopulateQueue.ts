import * as fs from 'fs';
import * as path from 'path';
import { prisma } from '../common/database';
import { DGP_DATA_DIR } from '../common/config';
import { FilaExtracaoStatus } from '@oda/database';
import { log } from 'crawlee';

export async function repopulateQueue() {
    log.info(`[Queue] Lendo arquivos locais de grupos DGP em: ${DGP_DATA_DIR}`);

    if (!fs.existsSync(DGP_DATA_DIR)) {
        log.warning(`[Queue] Diretório DGP ${DGP_DATA_DIR} não existe.`);
        return;
    }

    const files = fs.readdirSync(DGP_DATA_DIR).filter(f => f.endsWith('.json'));
    log.info(`[Queue] Encontrados ${files.length} arquivos JSON.`);

    let addedCount = 0;
    let skippedCount = 0;

    for (const file of files) {
        const filePath = path.join(DGP_DATA_DIR, file);
        try {
            const content = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);

            if (!data.membros || !Array.isArray(data.membros)) {
                log.warning(`[Queue] Arquivo ${file} não contém a lista de membros.`);
                continue;
            }

            log.info(`[Queue] Processando membros do grupo: ${data.nome || file}`);

            for (const p of data.membros) {
                if (!p.lattes) {
                    log.warning(`[Queue] Membro ${p.nome} sem ID Lattes no arquivo ${file}. Pulando...`);
                    continue;
                }

                const row = await prisma.filaExtracaoPesquisador.findUnique({
                    where: { lattesId: p.lattes }
                });

                if (!row) {
                    await prisma.filaExtracaoPesquisador.create({
                        data: {
                            lattesId: p.lattes,
                            nome: p.nome,
                            status: FilaExtracaoStatus.PENDENTE
                        }
                    });
                    addedCount++;
                } else {
                    skippedCount++;
                }
            }
        } catch (e: any) {
            log.error(`[Queue] Erro ao processar arquivo ${file}: ${e.message}`);
        }
    }

    const statusCounts = await prisma.filaExtracaoPesquisador.groupBy({
        by: ['status'],
        _count: true
    });
    log.info(`[Queue] Status atual da fila de pesquisadores: ${JSON.stringify(statusCounts)}`);
    log.info(`[Queue] Repopulação concluída. Adicionados: ${addedCount}, Pulados (já existentes): ${skippedCount}`);
}
