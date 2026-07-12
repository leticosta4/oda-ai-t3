import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from db.client import db
from scraper.database import update_group_queue_status
from scraper.config import DGP_DATA_DIR, save_json
from scraper.parsers import DGPextractor
from scraper.lattes import run_lattes_scraper

extractor = DGPextractor()


async def block_aggressively(route):
    if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
        await route.abort()
    else:
        await route.continue_()


async def scrape_group_page(context: BrowserContext, page: Page, dgp_id: str):
    print(f"[Scraper] Estabelecendo conexão para extração do espelho {dgp_id}...")
    await page.route("**/*", block_aggressively)

    url_alvo = f"https://dgp.cnpq.br/dgp/espelhogrupo/{dgp_id}"
    response = None
    for attempt in range(3):
        try:
            response = await page.goto(
                url_alvo, timeout=60000, wait_until="domcontentloaded"
            )
            break
        except Exception as e:
            if attempt == 2:
                raise e
            print(
                f"[Scraper] Tentativa {attempt + 1} falhou para {dgp_id}: {str(e)}. Retentando em 5 segundos..."
            )
            await asyncio.sleep(5)

    if response and response.status == 429:
        raise Exception("HTTP_429_RATE_LIMIT")
    elif response and response.status >= 500:
        raise Exception(f"HTTP_ERROR_{response.status}")

    await page.wait_for_selector("#recursosHumanos", timeout=30000)

    membro_detalhes_map = {}
    linhas_tr = await page.locator("#recursosHumanos tbody tr").all()
    total_membros = len(linhas_tr)

    print(f"[Scraper] Verificando {total_membros} pesquisadores...")
    for index, tr in enumerate(linhas_tr, start=1):
        aba_rh = None
        try:
            tds = await tr.locator("td").all()
            if len(tds) >= 2:
                nome = (await tds[0].inner_text()).strip()
                btn_rh = tr.locator("a[id*='idBtnVisualizarEspelho']").first

                if await btn_rh.count() > 0:
                    print(f"[{index}/{total_membros}] Sonda secundária -> {nome}")
                    async with context.expect_page(timeout=15000) as aba_rh_info:
                        await btn_rh.click()

                    aba_rh = await aba_rh_info.value
                    await aba_rh.route("**/*", block_aggressively)
                    await aba_rh.wait_for_load_state("domcontentloaded")

                    html_rh = await aba_rh.content()
                    detalhes = extractor.extrair_detalhes_rh(html_rh)
                    membro_detalhes_map[nome] = detalhes
        except Exception as e:
            print(f"[Scraper] Erro ao obter detalhes do RH {index}: {str(e)}")
        finally:
            if aba_rh and not aba_rh.is_closed():
                await aba_rh.close()

    html_popups = []
    botoes_linha = await page.locator(
        "a[id*='idBtnVisualizarEspelhoLinhaPesquisa']"
    ).all()
    total_linhas = len(botoes_linha)

    for idx, botao in enumerate(botoes_linha, start=1):
        aba_linha = None
        try:
            print(f"[{idx}/{total_linhas}] Varredura em Linha de Pesquisa...")
            async with context.expect_page(timeout=15000) as aba_linha_info:
                await botao.click()

            aba_linha = await aba_linha_info.value
            await aba_linha.route("**/*", block_aggressively)
            await aba_linha.wait_for_load_state("domcontentloaded")

            html_lin = await aba_linha.content()
            html_popups.append(html_lin)
        except Exception as e:
            print(f"[Scraper] Erro ao obter detalhes da linha {idx}: {str(e)}")
        finally:
            if aba_linha and not aba_linha.is_closed():
                await aba_linha.close()

    html_espelho = await page.content()
    data = extractor.extrair_html_espelho(
        html_espelho, html_popups, membro_detalhes_map
    )
    data["id_dgp"] = dgp_id

    save_json(data, DGP_DATA_DIR, dgp_id)
    print(f"✅ Grupo {dgp_id} extraído e salvo com sucesso.")

    # Filter and queue researchers
    for p in data.get("membros", []):
        lattes_id = p.get("lattes")
        if not lattes_id:
            continue

        row = await db.filaextracaopesquisador.find_unique(
            where={"lattesId": lattes_id}
        )
        if not row:
            await db.filaextracaopesquisador.create(
                data={
                    "lattesId": lattes_id,
                    "nome": p.get("nome"),
                    "status": "PENDENTE",
                }
            )
            print(f"[Queue] Adicionado à fila: {p.get('nome')} ({lattes_id})")


async def run_dgp_scraper(dgp_ids: list = []):
    print("[Scraper] Iniciando Extração DGP a partir da fila (FilaExtracao)")

    pending_groups = []
    if dgp_ids:
        for gid in dgp_ids:
            row = await db.filaextracaogrupo.upsert(
                where={"dgpId": gid},
                data={
                    "update": {},
                    "create": {
                        "dgpId": gid,
                        "nome": f"Grupo_{gid}",
                        "area": "N/A",
                        "instituicao": "N/A",
                        "status": "PENDENTE",
                    },
                },
            )
            pending_groups.append({"dgpId": row.dgpId, "nome": row.nome})
    else:
        pending = await db.filaextracaogrupo.find_many(
            where={"status": "PENDENTE"}, take=10
        )
        pending_groups = [{"dgpId": p.dgpId, "nome": p.nome} for p in pending]

    if not pending_groups:
        print("[Scraper] Nenhum grupo pendente na fila.")
        return

    print(
        f"[Scraper] Encontrados {len(pending_groups)} grupos pendentes. Iniciando extração..."
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for group in pending_groups:
            dgp_id = group["dgpId"]
            print(f"\n🔍 Processando Grupo: {dgp_id}")

            try:
                await update_group_queue_status(dgp_id, "PROCESSANDO")
                await scrape_group_page(context, page, dgp_id)
                await update_group_queue_status(dgp_id, "CONCLUIDO")
            except Exception as e:
                print(
                    f"[Scraper] Erro crítico no handler para o grupo '{dgp_id}': {str(e)}"
                )
                await update_group_queue_status(dgp_id, "CONCLUIDO")
                if "HTTP_429_RATE_LIMIT" in str(e):
                    print("[Scraper] Rate Limit atingido. Aguardando 30 segundos...")
                    await asyncio.sleep(30)

        await page.close()
        await context.close()
        await browser.close()

    print("[Scraper] Extração DGP finalizada.")

    # Process pending researchers automatically
    pending_researchers = await db.filaextracaopesquisador.find_many(
        where={"status": "PENDENTE"}
    )
    if pending_researchers:
        print(
            f"[Scraper] Iniciando extração Lattes sequencial para {len(pending_researchers)} pesquisadores pendentes..."
        )
        names = [p.nome for p in pending_researchers]
        await run_lattes_scraper(names)
