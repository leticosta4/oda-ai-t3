import os
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from db.client import db
from scraper.database import update_pesquisador_queue_status
from scraper.config import LATTES_DATA_DIR, save_json
from scraper.parsers import LattesExtractor

lattes_url = "https://buscatextual.cnpq.br/buscatextual/busca.do"
lattes_extractor = LattesExtractor()

async def block_aggressively(route):
    if route.request.resource_type in ["image", "stylesheet", "font", "media"]:
        await route.abort()
    else:
        await route.continue_()

async def buscar_e_extrair_lattes(context: BrowserContext, page: Page, nome_pesquisador: str, target_lattes_id: str = "") -> bool:
    try:
        print(f"🔍 [Lattes] Buscando: {nome_pesquisador} (ID Esperado: {target_lattes_id or 'Qualquer um'})")
        await page.goto(lattes_url, timeout=60000)
        
        await page.fill("input[id='textoBusca']", nome_pesquisador)
        await page.click("input[id='buscarDemais']")
        await page.click("a[id='botaoBuscaFiltros']")
        await page.wait_for_selector(".resultado", timeout=40000)
        
        results = page.locator(".resultado b a")
        count = await results.count()
        if count == 0:
            print(f"⚠️ [Lattes] Nenhum resultado encontrado para {nome_pesquisador}")
            return False
            
        success = False
        for i in range(count):
            result_link = results.nth(i)
            link_text = (await result_link.text_content() or "").strip()
            
            print(f"[Lattes] Abrindo resultado {i + 1} de {count}: {link_text}...")
            await result_link.click()
            
            await page.wait_for_selector(".moldal-interna", state="visible", timeout=15000)
            frame = page.frame_locator("iframe.iframe-modal")
            
            try:
                async with context.expect_page(timeout=30000) as new_page_info:
                    await frame.locator("a:has-text('Currículo Lattes')").evaluate("el => el.click()")
            
                curriculo_page = await new_page_info.value
                await curriculo_page.wait_for_load_state("domcontentloaded")
                
                html_content = await curriculo_page.content()
                basico = lattes_extractor.extrair_informacoes_basicas(html_content)
                
                parsed_lattes_id = basico.get("lattes", "").replace("http://lattes.cnpq.br/", "").replace("https://lattes.cnpq.br/", "").strip()
                if not parsed_lattes_id:
                    # Tentar encontrar via regex no html se a extração padrão falhar
                    import re
                    match = re.search(r"lattes\.cnpq\.br/(\d+)", html_content)
                    if match:
                        parsed_lattes_id = match.group(1)
                        basico["lattes"] = parsed_lattes_id
                
                print(f"[Lattes] ID do Lattes analisado: {parsed_lattes_id} (Esperado: {target_lattes_id or 'Qualquer'})")
                
                if target_lattes_id and parsed_lattes_id != target_lattes_id:
                    print("[Lattes] ID do Lattes diferente do esperado. Tentando próximo resultado...")
                    await curriculo_page.close()
                    # Fechar modal
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(0.5)
                    continue
                    
                projetos = lattes_extractor.extrair_detalhes_projetos(html_content)
                eventos = lattes_extractor.extrair_detalhes_eventos(html_content)
                lattes_extractor.extrair_imagem(html_content, parsed_lattes_id or nome_pesquisador)
                
                dados = {
                    "nome": nome_pesquisador,
                    "lattes": parsed_lattes_id,
                    **basico,
                    **projetos,
                    **eventos
                }
                
                save_json(dados, LATTES_DATA_DIR, parsed_lattes_id or nome_pesquisador)
                print(f"✅ [Lattes] Sucesso: {nome_pesquisador} (ID: {parsed_lattes_id})")
                await curriculo_page.close()
                
                # Fechar modal
                await page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
                success = True
                break
            except Exception as e:
                print(f"❌ [Lattes] Erro ao extrair dados no popup/modal: {str(e)}")
                try:
                    await page.keyboard.press('Escape')
                except Exception:
                    pass
                await asyncio.sleep(0.5)
                
        return success
    except Exception as e:
        print(f"❌ [Lattes] Erro ao processar pesquisador {nome_pesquisador}: {str(e)}")
        return False

async def run_lattes_scraper(names: list = []):
    targets = []
    
    if not names:
        pending = await db.filaextracaopesquisador.find_many(
            where={"status": "PENDENTE"},
            take=50
        )
        if not pending:
            print("[Lattes] Nenhum pesquisador pendente na fila.")
            return
        targets = [{"nome": p.nome, "lattesId": p.lattesId} for p in pending]
    else:
        for name in names:
            row = await db.filaextracaopesquisador.find_first(
                where={"nome": name}
            )
            targets.append({"nome": name, "lattesId": row.lattesId if row else ""})
            
    for t in targets:
        if t["lattesId"]:
            await update_pesquisador_queue_status(t["lattesId"], "PROCESSANDO")
            
    print(f"🚀 Iniciando Scraper Lattes para {len(targets)} pesquisadores (Instância Única)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.route("**/*", block_aggressively)
        
        for t in targets:
            try:
                success = await buscar_e_extrair_lattes(context, page, t["nome"], t["lattesId"])
                if t["lattesId"]:
                    await update_pesquisador_queue_status(t["lattesId"], "CONCLUIDO")
            except Exception as e:
                print(f"Erro ao extrair {t['nome']}: {str(e)}")
                if t["lattesId"]:
                    await update_pesquisador_queue_status(t["lattesId"], "CONCLUIDO")
                    
        await page.close()
        await context.close()
        await browser.close()
        
    print("🏁 Scraper Lattes finalizado.")
