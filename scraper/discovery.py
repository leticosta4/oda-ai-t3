import asyncio
import re
from playwright.async_api import async_playwright, Page, Locator
from scraper.database import group_queue_discovery, normalize_queue_data
from scraper.utils import random_sleep, clean_str

SEARCH_URL = "http://dgp.cnpq.br/dgp/faces/consulta/consulta_parametrizada.jsf"


async def handle_not_disabled(page: Page, btn: Locator):
    first_item = page.locator("li.ui-datalist-item").first
    first_item_before = (
        await first_item.text_content() if await first_item.count() > 0 else ""
    )
    await btn.click()

    async def check_changed():
        for _ in range(80):
            try:
                curr_item = page.locator("li.ui-datalist-item").first
                if await curr_item.count() > 0:
                    text = await curr_item.text_content()
                    if text != first_item_before:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    await check_changed()


async def prepare_search_page(page: Page, chave: str):
    print(f"🔄 Preparando página de busca para a chave: '{chave}'")
    await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
    await random_sleep(2000, 4000)

    await page.fill("input[id='idFormConsultaParametrizada:idTextoFiltro']", chave)
    await page.get_by_label("Não-atualizado").uncheck()
    await random_sleep(1000, 2000)
    # await page.click("button[id='idFormConsultaParametrizada:buscaRefinada']")
    # await page.wait_for_selector("label.ui-selectonemenu-label")

    # # Seleciona Região: Nordeste
    # await random_sleep(500, 1500)
    # await page.locator("div[id='idFormConsultaParametrizada:idRegiao']").click()
    # await (
    #     page.locator("ul.ui-selectonemenu-items li")
    #     .get_by_text("Nordeste", exact=True)
    #     .click()
    # )
    # await page.wait_for_load_state("networkidle")

    # # Seleciona UF: Bahia
    # # await page.locator("div[id='idFormConsultaParametrizada:idUF']").click()
    # # await (
    # #     page.locator("ul.ui-selectonemenu-items li")
    # #     .get_by_text("Bahia", exact=True)
    # #     .click()
    # # )
    # await page.wait_for_load_state("networkidle")

    await page.click("button[id='idFormConsultaParametrizada:idPesquisar']")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_selector(".itemConsulta", timeout=40000)


async def run_dgp_discovery(keys: list = ["a", "e", "i", "o", "u"]):
    print(f"🚀 Iniciando Discovery DGP para as chaves: {', '.join(keys)}")
    await normalize_queue_data()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Abort images/css for performance
        await page.route(
            "**/*",
            lambda route: (
                route.abort()
                if route.request.resource_type
                in ["image", "font", "stylesheet", "media"]
                else route.continue_()
            ),
        )

        for key in keys:
            try:
                await prepare_search_page(page, key)

                pagina_atual = 1
                while True:
                    print(f"📂 Bloco: {key.upper()} | Página: {pagina_atual}")
                    await asyncio.sleep(1.5)

                    botoes_espelho = await page.locator(
                        "a[id*='idBtnVisualizarEspelhoGrupo']"
                    ).all()
                    total_nesta_pagina = len(botoes_espelho)

                    for index, btn in enumerate(botoes_espelho, start=1):
                        aba = None
                        try:
                            # Obtém nome, área e instituição do grupo a partir do DOM da lista
                            # Para salvar no banco de dados
                            item_li = page.locator("li.ui-datalist-item").nth(index - 1)
                            nome_grupo = clean_str(await btn.text_content())

                            instituicao = ""
                            area = ""
                            labels = await item_li.locator("label").all()
                            for lbl in labels:
                                lbl_txt = await lbl.inner_text()
                                if "Instituição" in lbl_txt:
                                    val_el = item_li.locator(
                                        f"label:has-text('{lbl_txt}') + div"
                                    )
                                    if await val_el.count() > 0:
                                        instituicao = clean_str(
                                            await val_el.first.inner_text()
                                        )
                                elif "Área" in lbl_txt:
                                    val_el = item_li.locator(
                                        f"label:has-text('{lbl_txt}') + div"
                                    )
                                    if await val_el.count() > 0:
                                        area = clean_str(
                                            await val_el.first.inner_text()
                                        )

                            await asyncio.sleep(0.5)
                            async with context.expect_page(
                                timeout=15000
                            ) as nova_aba_info:
                                await btn.click(force=True)

                            aba = await nova_aba_info.value
                            await aba.wait_for_selector(
                                "#tituloImpressao", timeout=10000
                            )

                            conteudo_html = await aba.content()
                            match = re.search(r"espelhogrupo/(\d{16})", conteudo_html)
                            if match:
                                dgp_id = match.group(1)
                                await group_queue_discovery(
                                    dgp_id, nome_grupo, area, instituicao
                                )
                                print(
                                    f"   [+] Grupo cadastrado: {nome_grupo} ({dgp_id})"
                                )

                        except Exception as e:
                            print(
                                f"    [-] Erro ao processar item ({index}/{total_nesta_pagina}): {str(e)}"
                            )
                        finally:
                            if aba and not aba.is_closed():
                                await aba.close()

                    proximo_btn = page.locator(".ui-paginator-next")
                    if await proximo_btn.count() == 0:
                        break

                    is_disabled = "ui-state-disabled" in (
                        await proximo_btn.first.get_attribute("class") or ""
                    )
                    if is_disabled:
                        print(f"Fim de indexação para a macro-chave '{key.upper()}'.")
                        break
                    else:
                        await handle_not_disabled(page, proximo_btn.first)
                        pagina_atual += 1
                        await page.wait_for_selector(".itemConsulta", timeout=20000)
            except Exception as e:
                print(f"❌ Erro na busca com a chave '{key}': {str(e)}")

        await page.close()
        await context.close()
        await browser.close()

    await normalize_queue_data()
    print("🏁 Discovery DGP finalizado.")
