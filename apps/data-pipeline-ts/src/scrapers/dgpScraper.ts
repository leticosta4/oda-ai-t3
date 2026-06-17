import { PlaywrightCrawler, log } from 'crawlee';
import { BrowserContext, Page } from 'playwright';
import { DGPExtractor } from '../parsers/dgpParser';
import { db } from '../common/database';
import { saveJson, DGP_DATA_DIR } from '../common/config';

const extractor = new DGPExtractor();
const SEARCH_URL = 'http://dgp.cnpq.br/dgp/faces/consulta/consulta_parametrizada.jsf';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const randomSleep = (min: number, max: number) => sleep(Math.floor(Math.random() * (max - min + 1) + min));

async function scrapeGroupPage(context: BrowserContext, groupPage: Page) {
    const url = groupPage.url();
    const match = url.match(/espelhogrupo\/(\d{16})/);
    const dgpId = match ? match[1] : null;

    if (!dgpId) {
        log.warning(`[Scraper] Não foi possível encontrar ID na URL: ${url}`);
        return;
    }

    log.info(`📄 Extraindo dados do Grupo ID: ${dgpId}`);

    try {
        await groupPage.waitForSelector('#recursosHumanos', { timeout: 30000 });
        await randomSleep(1000, 2000);

        const rhDetailsMap = new Map<string, any>();
        const rhButtons = await groupPage.$$("a[id*='idBtnVisualizarEspelho']");
        
        for (const btn of rhButtons) {
            const nome = await btn.evaluate(el => {
                const row = el.closest('tr');
                return row ? (row.querySelector('td')?.textContent || '').trim() : '';
            });

            await randomSleep(500, 1500);
            const [popup] = await Promise.all([
                context.waitForEvent('page', { timeout: 20000 }),
                btn.click(),
            ]);
            await popup.waitForLoadState('domcontentloaded');
            const html = await popup.content();
            rhDetailsMap.set(nome || 'Desconhecido', extractor.extractRHDetails(html));
            await popup.close();
        }

        const linesPopups: string[] = [];
        const linesButtons = await groupPage.$$("a[id*='idBtnVisualizarEspelhoLinhaPesquisa']");
        
        for (const btn of linesButtons) {
            await randomSleep(500, 1500);
            const [popup] = await Promise.all([
                context.waitForEvent('page', { timeout: 20000 }),
                btn.click(),
            ]);
            await popup.waitForLoadState('domcontentloaded');
            linesPopups.push(await popup.content());
            await popup.close();
        }

        const mainHtml = await groupPage.content();
        const data = extractor.extractGroupMirror(mainHtml, linesPopups, rhDetailsMap);
        
        data.id_dgp = dgpId;
        saveJson(data, DGP_DATA_DIR, dgpId);
        log.info(`✅ Grupo ${dgpId} salvo com sucesso.`);
        
        await db.queueDiscovery(dgpId);
        await db.updateQueueStatus(dgpId, 'CONCLUIDO');

    } catch (err) {
        log.error(`❌ Erro ao extrair grupo ${dgpId}: ${err.message}`);
        await db.queueDiscovery(dgpId);
        await db.updateQueueStatus(dgpId, 'ERRO');
    }
}

export async function runDgpScraper() {
    log.info('🚀 Iniciando Scraper Unificado DGP com Crawlee (Clique Direto -> Extração)');

    const chavesVarredura = ["a", "e", "i", "o", "u"];

    const crawler = new PlaywrightCrawler({
        headless: true,
        maxConcurrency: 1, // Mantido 1 pois navega pelas páginas de busca
        requestHandlerTimeoutSecs: 1800, // Timeout alto para páginas com muitos grupos

        preNavigationHooks: [
            async ({ page }) => {
                await page.route('**/*', (route) => {
                    if (['image', 'font', 'stylesheet', 'media'].includes(route.request().resourceType())) {
                        return route.abort();
                    }
                    return route.continue();
                });
            }
        ],

        async requestHandler({ page, request }) {
            const context = page.context();
            const chave = request.userData.chave;
            
            log.info(`\n🔍 Buscando chave: '${chave.toUpperCase()}'`);
            
            try {
                await page.goto(SEARCH_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
                await randomSleep(2000, 3000);

                await page.fill("input[id='idFormConsultaParametrizada:idTextoFiltro']", chave);
                await page.click("button[id='idFormConsultaParametrizada:idPesquisar']");
                
                let hasNextPage = true;
                let pageNum = 1;

                while (hasNextPage) {
                    log.info(`📍 Processando página ${pageNum} da chave '${chave}'`);
                    await page.waitForSelector(".itemConsulta", { timeout: 30000 });

                    const links = page.locator("a[id*='idBtnVisualizarEspelhoGrupo']");
                    const count = await links.count();
                    log.info(`Encontrados ${count} grupos na página.`);

                    for (let i = 0; i < count; i++) {
                        const btn = links.nth(i);
                        try {
                            log.info(`[${i+1}/${count}] Abrindo espelho do grupo...`);
                            await randomSleep(2000, 4000); 

                            const [groupPage] = await Promise.all([
                                context.waitForEvent('page', { timeout: 30000 }),
                                btn.click(),
                            ]);

                            await groupPage.waitForLoadState('domcontentloaded');
                            await scrapeGroupPage(context, groupPage);
                            await groupPage.close();
                        } catch (err) {
                            log.error(`Falha ao abrir grupo: ${err.message}`);
                        }
                    }

                    const proximoBtn = page.locator(".ui-paginator-next");
                    if (await proximoBtn.count() > 0) {
                        const isDisabled = await proximoBtn.evaluate((el) => el.classList.contains('ui-state-disabled'));
                        if (!isDisabled) {
                            log.info('Avançando para a próxima página de resultados...');
                            await randomSleep(3000, 5000);
                            await proximoBtn.click();
                            await page.waitForResponse(res => res.url().includes('consulta_parametrizada.jsf'));
                            pageNum++;
                        } else {
                            hasNextPage = false;
                        }
                    } else {
                        hasNextPage = false;
                    }
                }
            } catch (error) {
                log.error(`Erro na busca da chave '${chave}': ${error.message}`);
            }
        },
    });

    await crawler.addRequests(chavesVarredura.map(chave => ({
        url: SEARCH_URL,
        userData: { chave },
        uniqueKey: `DGP-SEARCH-${chave}`
    })));

    await crawler.run();
    log.info('🏁 Scraper DGP finalizado via Crawlee.');
}
