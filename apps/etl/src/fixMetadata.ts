import { prismaConfig, PrismaClient } from '@oda/database';
import { getOpenAlexData, linkProductionDoi } from './lattesEtl';
import { stripHtml } from './commom/normalize';
const prisma = new PrismaClient(prismaConfig);

export async function runFixMetadata(args: string[]) {
    let fixAllDoi = false;
    let specificDoi: string | null = null;
    let fixAllLattes = false;
    let specificLattes: string | null = null;

    for (let i = 0; i < args.length; i++) {
        const flag = args[i];
        if (flag === '-doi') {
            fixAllDoi = true;
        } else if (flag === '-DOI') {
            specificDoi = args[i + 1];
            i++; 
        } else if (flag === '-lattes') {
            fixAllLattes = true;
        } else if (flag === '-LATTES') {
            specificLattes = args[i + 1];
            i++; 
        }
    }

    if (!fixAllDoi && !specificDoi && !fixAllLattes && !specificLattes) {
        console.log('[FIX] Nenhuma flag informada.');
        console.log('Uso: pnpm etl fix [-doi] [-DOI <id/doi>] [-lattes] [-LATTES <lattesId/id>]');
        return;
    }

    if (fixAllDoi) {
        console.log('[FIX] Buscando todas as produções com DOI...');
        const producoes = await prisma.producao.findMany({
            where: { doi: { not: null } }
        });
        console.log(`[FIX] Encontradas ${producoes.length} produções para reprocessar.`);
        for (const prod of producoes) {
            if (prod.doi) {
                await fixSingleDoi(prod.id, prod.doi);
            }
        }
    } else if (specificDoi) {
        console.log(`[FIX] Buscando produção para DOI/ID: "${specificDoi}"...`);
        const prod = await prisma.producao.findFirst({
            where: {
                OR: [
                    { id: specificDoi },
                    { doi: specificDoi }
                ]
            }
        });
        if (prod && prod.doi) {
            await fixSingleDoi(prod.id, prod.doi);
        } else {
            console.error(`[FIX] Produção não encontrada para: "${specificDoi}"`);
        }
    }

    if (fixAllLattes) {
        console.log('[FIX] Buscando pesquisadores sem ID do OpenAlex...');
        const pesquisadores = await prisma.pesquisador.findMany({
            where: {
                NOT: {
                    orcidId:{
                        equals: null
                    }
                }
            }
        });
        console.log(`[FIX] Encontrados ${pesquisadores.length} pesquisadores para atualizar.`);
        for (const pesq of pesquisadores) {
            await fixSingleLattes(pesq.id, pesq.nome, pesq.orcidId || undefined);
        }
    } else if (specificLattes) {
        console.log(`[FIX] Buscando pesquisador para Lattes ID/UUID: "${specificLattes}"...`);
        const pesq = await prisma.pesquisador.findFirst({
            where: {
                OR: [
                    { id: specificLattes },
                    { lattesId: specificLattes }
                ]
            }
        });
        if (pesq) {
            await fixSingleLattes(pesq.id, pesq.nome, pesq.orcidId || undefined);
        } else {
            console.error(`[FIX] Pesquisador não encontrado para: "${specificLattes}"`);
        }
    }

    console.log('[FIX] Todos os reprocessamentos concluídos.');
}

async function fixSingleDoi(id: string, doi: string) {
    console.log(`[FIX] 🔍 Processando DOI: "${doi}"...`);
    const extra = await linkProductionDoi(doi);
    if (extra) {
        const { abstract, publisher, licenseUrl } = extra;
        const cleanAbstract = abstract ? stripHtml(abstract) : null;
        await prisma.producao.update({
            where: { id },
            data: {
                resumo: cleanAbstract || undefined,
                veiculo: publisher || undefined,
                url: licenseUrl || undefined
            }
        });
        console.log(`[FIX] ✅ Produção com DOI "${doi}" atualizada.`);
    } else {
        console.log(`[FIX] ❌ Falha ao buscar dados para o DOI: "${doi}".`);
    }
}

async function fixSingleLattes(id: string, nome: string, orcid: string) {
    console.log(`[FIX] 🔍 Buscando OpenAlex para: "${nome}" (ORCID: ${orcid || 'N/A'})...`);
    const data = await getOpenAlexData(orcid);
    
    if (data) {
        console.log(data)
        await prisma.pesquisador.update({
            where: { id },
            data: {
                openAlexId: data.openAlexId || null,
                indexH: data.h_index || null,
                indexI10: data.i10_index || null
            }
        });
        console.log(`[FIX] ✅ Pesquisador "${nome}" atualizado.`);
    } else {
        console.log(`[FIX] ❌ Dados do OpenAlex não encontrados para: "${nome}".`);
    }
}
