import * as fs from 'fs';
import * as path from 'path';
import { prismaConfig, PrismaClient, Prisma } from '@oda/database';
import { OPEN_ALEX_URL, DOI_URL, PROCESSED_DATA_DIR } from './commom/config';
import { TipoProducao } from '@oda/database';
import { stripHtml } from './commom/normalize';
import { DefaultArgs } from '../../../shared/database/generated/prisma/runtime/client';

const prisma = new PrismaClient(prismaConfig);

/**
 * Lógica de persistência para Currículos Lattes
 */

async function getOpenAlexData(nome: string, orcid?:string) {
    try{
        const params = orcid ? `filter=orcid:${orcid}` : `search.exact=${nome}` 
        const url = `${OPEN_ALEX_URL}?api_key=${process.env.OPEN_ALEX_KEY}&${params}`
        const res = await fetch(url)
        if (!res.ok || res.status == 404){ throw new Error(`Pesquisador(a) ${nome} não encontrado no openAlex`)}
        const data = await res.json()
        if(data.meta.count == 0) return null
        const { id } = data.results[0]
        const {h_index, i10_index} = data.results[0].summary_stats
        return { h_index, i10_index, openAlexId: id}
    }catch(e: unknown){
        if(e instanceof Error){
            console.log(`Ocorrou um erro ao procurar dados openAlex para ${nome} - ${e.message}`)
        }
    }
}

async function linkProductionDoi(doi: string) {
    try{
        const url = `${DOI_URL}${doi}`
        const res = await fetch(url)
        if (!res.ok || res.status == 404) throw new Error(`Artigo não encontrado na api do DOI`)
        
        const data = await res.json() 
        const abstract: string = data?.abstract ? stripHtml(data.abstract) : ""
        const publisher: string = data?.publisher || ""
        const licenseUrl: string = data?.license?.[0]?.URL || ""
    console.log(data?.license?.[0]?.URL)
        return {abstract, publisher, licenseUrl} 
    }catch(e: unknown){
         if(e instanceof Error){
            console.log(`Ocorrou um erro ao informações para o doi: ${doi} - ${e.message}`)
        }
    }
}

async function linkProductionQualis(issn: string) {}


async function saveResearcherProductions(tx: Omit<PrismaClient<Prisma.PrismaClientOptions, Prisma.LogLevel, DefaultArgs>, "$connect" | "$disconnect" | "$on" | "$use" | "$extends">, pesquisadorId: string, artigos: any[], livrosCapitulos: any[]) {
    for (const artigo of artigos) {
        if (!artigo.titulo) continue;

        const anoInt = artigo.ano ? parseInt(artigo.ano.replace(/\D/g, ''), 10) : null;
        const cleanDoi = artigo.doi ? artigo.doi.trim() : null;

        let producao = null;
        
        if (cleanDoi) {
            producao = await tx.producao.findUnique({
                where: { doi: cleanDoi }
            });
        }

        if (!producao) {
            producao = await tx.producao.findFirst({
                where: {
                    titulo: { equals: artigo.titulo.trim(), mode: 'insensitive' },
                    ano: anoInt
                }
            });
        }
        console.log("Artigo enriquecido", artigo)
        if (!producao) {
            producao = await tx.producao.create({
                data: {
                    titulo: artigo.titulo.trim(),
                    ano: anoInt,
                    tipo: TipoProducao.ARTIGO,
                    doi: cleanDoi || null,
                    url: artigo.url || null,
                    veiculo: artigo?.veiculo || null,
                    resumo: artigo?.resumo || null
                }
            });
        } else {
            producao = await tx.producao.update({
                where: { id: producao.id },
                data: {
                    doi: cleanDoi || producao.doi,
                    veiculo: artigo.nomePeriodico || artigo.veiculo || producao.veiculo,
                    resumo: artigo.resumo || producao.resumo
                }
            });
        }

        // Associa o autor na tabela pivot
        await tx.producaoPesquisador.upsert({
            where: {
                producaoId_pesquisadorId: {
                    producaoId: producao.id,
                    pesquisadorId
                }
            },
            update: {},
            create: {
                producaoId: producao.id,
                pesquisadorId
            }
        });
    }

    // 2. Processa Livros e Capítulos
    for (const livro of livrosCapitulos) {
        if (!livro.titulo) continue;

        const anoInt = livro.ano ? parseInt(livro.ano.replace(/\D/g, ''), 10) : null;
        const cleanDoi = livro.doi ? livro.doi.trim() : null;

        let producao = null;

        if (cleanDoi) {
            producao = await tx.producao.findUnique({
                where: { doi: cleanDoi }
            });
        }

        if (!producao) {
            producao = await tx.producao.findFirst({
                where: {
                    titulo: { equals: livro.titulo.trim(), mode: 'insensitive' },
                    ano: anoInt
                }
            });
        }

        if (!producao) {
            producao = await tx.producao.create({
                data: {
                    titulo: livro.titulo.trim(),
                    ano: anoInt,
                    tipo: TipoProducao.LIVROCAPITULO,
                    doi: cleanDoi || null,
                    url: livro.url || null,
                    veiculo: livro.editora || livro.veiculo || null,
                }
            });
        } else {
            producao = await tx.producao.update({
                where: { id: producao.id },
                data: {
                    doi: cleanDoi || producao.doi,
                    veiculo: livro.editora || livro.veiculo || producao.veiculo
                }
            });
        }

        // Associa o autor na tabela pivot
        await tx.producaoPesquisador.upsert({
            where: {
                producaoId_pesquisadorId: {
                    producaoId: producao.id,
                    pesquisadorId
                }
            },
            update: {},
            create: {
                producaoId: producao.id,
                pesquisadorId
            }
        });
    }
}

/**
 * Lógica de persistência para Currículos Lattes
 */
export async function saveLattesToDb(data: any) {
    console.log(`[ETL] 📡 Buscando dados acadêmicos externos para ${data.nome}...`);

    const openAlexData = await getOpenAlexData(data.nome, data.orcid || data.orcidId);

    const artigosEnriquecidos = [] as any;
    if (data.artigos && Array.isArray(data.artigos)) {
        for (const artigo of data.artigos) {
            let resumo = null, veiculo = null, url = null;
            if (artigo.doi) {
                const artigosExtra = await linkProductionDoi(artigo.doi);
                
                if (artigosExtra) {
                    resumo = artigosExtra.abstract ? stripHtml(artigosExtra.abstract) : null;
                    veiculo = artigosExtra.publisher
                    url = artigosExtra.licenseUrl
                }
            }
            artigosEnriquecidos.push({
                ...artigo,
                resumo,
                veiculo,
                url
            });
        }
    }
    console.log(artigosEnriquecidos)
    const livrosCapitulos = data.livrosCapitulos || [];

    try {
        await prisma.$transaction(async (tx) => {
            const pesquisador = await tx.pesquisador.findFirst({
                where: { lattesId: data.lattes}
            });

            if (pesquisador) {
                await tx.pesquisador.update({
                    where: { id: pesquisador.id },
                    data: {
                        indexH: openAlexData?.h_index || null,
                        indexI10: openAlexData?.i10_index || null,
                        openAlexId: openAlexData?.openAlexId || null,
                        imageUrl: `/static/${data.lattes}.webp`
                    }
                });

                await saveResearcherProductions(tx, pesquisador.id, artigosEnriquecidos, livrosCapitulos);

                await tx.filaExtracaoPesquisador.upsert({
                    where: { lattesId: data.lattes },
                    update: { status: 'CONCLUIDO' },
                    create: {
                        lattesId: data.lattes,
                        nome: data.nome,
                        status: 'CONCLUIDO'
                    }
                });

                console.log(`[ETL] ✅ Lattes e produções de ${data.nome} processados com sucesso.`);
            } else {
                console.log(`[ETL] ⚠️ Pesquisador ${data.nome} não encontrado no banco de dados relacional.`);
            }
        }, { timeout: 30000 });
    } catch (error) {
        console.error(`[ETL] ❌ Erro no Lattes de ${data.nome}:`, error);
    }
}

/**
 * Executa o ETL de um pesquisador específico a partir do caminho do seu arquivo JSON.
 * (Preparado para alterações na função interna de salvamento saveLattesToDb)
 */
export async function runPesquisadorEtl(jsonPath: string) {
    console.log(`[ETL] 🔍 Iniciando processamento do arquivo de pesquisador: ${jsonPath}`);
    if (!fs.existsSync(jsonPath)) {
        console.log(`[ETL] ⚠️ Arquivo de origem não existe (pode ter sido processado concorrentemente): ${jsonPath}`);
        return;
    }

    const content = fs.readFileSync(jsonPath, 'utf-8');
    const lattesData = JSON.parse(content);

    await saveLattesToDb(lattesData);

    const lattesFileName = path.basename(jsonPath);
    const processedLattesDir = path.join(PROCESSED_DATA_DIR, 'lattes');
    if (!fs.existsSync(processedLattesDir)) fs.mkdirSync(processedLattesDir, { recursive: true });
    const destPath = path.join(processedLattesDir, lattesFileName);
    if (jsonPath !== destPath) {
        try {
            if (fs.existsSync(jsonPath)) {
                fs.renameSync(jsonPath, destPath);
                console.log(`[ETL] 📁 JSON Lattes ${lattesFileName} movido para ${destPath}`);
            } else {
                console.log(`[ETL] 📁 JSON Lattes ${lattesFileName} já foi movido por outro processo.`);
            }
        } catch (renameError: any) {
            console.warn(`[ETL] ⚠️ Não foi possível mover o arquivo Lattes ${lattesFileName}: ${renameError.message}`);
        }
    } else {
        console.log(`[ETL] 📁 JSON Lattes ${lattesFileName} já está na pasta processed-data.`);
    }
}
