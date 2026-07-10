import re
import requests
import os
import logging
from bs4 import BeautifulSoup
from scraper.config import IMAGE_DIR

def get_campo_adjacente(soup, padrao):
    lbl = soup.find('label', string=re.compile(padrao))
    if lbl:
        ctrl = lbl.find_next_sibling('div', class_='controls')
        if ctrl:
            return ctrl.get_text(strip=True)
    return ""

def limpar_texto(t):
    if not t: return ""
    return " ".join(t.split()).strip()

class DGPextractor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("DgpScraper")
        
    def extrair_detalhes_rh(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        detalhes = {"lattes": "", "areas": [], "grupos": [], "linhas": []}

        match = re.search(r'espelhorh/(\d{16})', html_content)
        if match: detalhes["lattes"] = match.group(1)

        areas_label = soup.find('label', string=re.compile(r'Áreas de atuação:'))
        if areas_label:
            div_control = areas_label.find_next_sibling('div', class_='controls')
            if div_control:
                for li in div_control.find_all('li'): detalhes["areas"].append(limpar_texto(li.get_text(strip=True)))

        tb_grupos = soup.find('tbody', id=re.compile(r'.*tblEspelhoRHGPAtuacao_data'))
        if tb_grupos:
            for tr in tb_grupos.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 2 and tds[0].get('colspan') is None: detalhes["grupos"].append(limpar_texto(tds[0].get_text(strip=True)))

        tb_linhas = soup.find('tbody', id=re.compile(r'.*tblEspelhoRHLPAtuacao_data'))
        if tb_linhas:
            for tr in tb_linhas.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 2 and tds[0].get('colspan') is None: detalhes["linhas"].append(limpar_texto(tds[0].get_text(strip=True)))

        return detalhes

    def extrair_detalhes_da_linha(self, html_linha, nome_linha_esperado):
        soup = BeautifulSoup(html_linha, 'html.parser')
        linha = {
            "nome": nome_linha_esperado, 
            "objetivo": "Não Identificado", 
            "areas_conhecimento": [], 
            "palavras_chave": [], 
            "setores_aplicacao": []
        }
        
        container_info = soup.find(id='linhaPesquisa')
        if container_info:
            obj_label = container_info.find(string=re.compile(r'Objetivo', re.IGNORECASE))
            if obj_label:
                target = obj_label.find_parent().find_next_sibling('div', class_='controls')
                if target:
                    linha['objetivo'] = limpar_texto(target.get_text(strip=True))

        secoes = {
            'palavraChave': 'palavras_chave',
            'areaConhecimento': 'areas_conhecimento',
            'setorAplicacao': 'setores_aplicacao'
        }

        for html_id, campo_destino in secoes.items():
            container = soup.find(id=html_id)
            if container:
                lis = container.find_all('li')
                if lis:
                    itens = [limpar_texto(li.get_text(strip=True)) for li in lis if limpar_texto(li.get_text(strip=True))]
                    linha[html_id if html_id != 'palavraChave' else 'palavras_chave'] = itens
                    linha[campo_destino] = itens

        return linha

    def extrair_html_espelho(self, html_content, html_array_linhas_popups, membro_detalhes_map):
        soup = BeautifulSoup(html_content, 'html.parser')
        dados = {
            "id_dgp": "000000", "nome": "N/A", "repercussao": "", "area": "N/A", 
            "instituicao": "N/A", "ano_formacao": "N/A", "endereco": {}, "membros": [], "linhas": []
        }

        id_text = soup.find(string=re.compile(r'espelhogrupo/\d{16}'))
        if id_text:
            match = re.search(r'\d{16}', id_text)
            if match: dados["id_dgp"] = match.group(0)

        titulo_box = soup.find(id='tituloImpressao')
        if titulo_box and titulo_box.find('h1'):
            h1 = titulo_box.find('h1')
            for child in h1.find_all(['div', 'img']): child.decompose()
            dados["nome"] = limpar_texto(h1.get_text(strip=True))

        dados["ano_formacao"] = limpar_texto(get_campo_adjacente(soup, r'Ano de formação'))
        dados["area"] = limpar_texto(get_campo_adjacente(soup, r'Área predominante'))
        dados["instituicao"] = limpar_texto(get_campo_adjacente(soup, r'Instituição do grupo'))

        div_endereco = soup.find(id='endereco')
        if div_endereco:
            dados["endereco"] = {
                "cep": get_campo_adjacente(div_endereco, 'CEP'),
                "localidade": get_campo_adjacente(div_endereco, 'Localidade'),
                "uf": get_campo_adjacente(div_endereco, 'UF'),
                "bairro": get_campo_adjacente(div_endereco, 'Bairro'),
                "complemento": get_campo_adjacente(div_endereco, 'Complemento'),
                "numero": get_campo_adjacente(div_endereco, 'Número'),
                "logradouro": get_campo_adjacente(div_endereco, 'Logradouro')
            }

        div_rep = soup.find(id='repercussao')
        if div_rep:
            textos = [limpar_texto(p.get_text(" ", strip=True)) for p in div_rep.find_all('p', align=False)]
            dados["repercussao"] = "\n".join(textos)

        try:
            lideres_div = soup.find('label', string=re.compile(r'Líder\(es\) do grupo:')).find_next_sibling('div', class_='controls')
            lista_lideres_str = [texto.strip() for texto in lideres_div.stripped_strings if texto.strip()]
        except Exception:
            lista_lideres_str = []

        div_rh = soup.find(id='recursosHumanos')
        if div_rh:
            for tb in div_rh.find_all('table', role='grid'):
                header_anterior = tb.find_previous_sibling('h4')
                if header_anterior and 'egressos' in header_anterior.get_text(strip=True).lower(): continue
                headers = [th.get_text(strip=True).lower() for th in tb.find_all('th')]
                if not headers: continue
                if any("período" in h for h in headers) or any("periodo" in h for h in headers): continue
                    
                nome_coluna_alvo = headers[0]
                tb_body = tb.find('tbody')
                if tb_body:
                    for tr in tb_body.find_all('tr'):
                        colunas = tr.find_all('td')
                        if len(colunas) >= 2 and colunas[0].get('colspan') is None:
                            nome_membro = limpar_texto(colunas[0].get_text(strip=True))
                            formacao_tabela = limpar_texto(colunas[1].get_text(strip=True)) if len(colunas) > 1 else ""

                            categoria = "PESQUISADOR"
                            if "pesquisador" in nome_coluna_alvo: categoria = "LIDER" if nome_membro in lista_lideres_str else "PESQUISADOR"
                            elif "estudante" in nome_coluna_alvo: categoria = "ESTUDANTE"
                            elif "técnico" in nome_coluna_alvo or "tecnico" in nome_coluna_alvo: categoria = "TECNICO"
                            elif "estrangeiro" in nome_coluna_alvo: categoria = "ESTRANGEIRO"
                                
                            dict_adicional_rh = membro_detalhes_map.get(nome_membro, {})
                            formacao_final = formacao_tabela if formacao_tabela else dict_adicional_rh.get("titulacao", "")

                            dados["membros"].append({
                                "nome": nome_membro, 
                                "lattes": dict_adicional_rh.get("lattes", ""),
                                "formacao_academica": formacao_final,
                                "categoria_lattes": categoria,
                                "areas": dict_adicional_rh.get("areas", []),
                                "grupos_associados": dict_adicional_rh.get("grupos", []),
                                "linhas_associadas": dict_adicional_rh.get("linhas", [])
                            })

        idx_linha = 0
        div_linhas = soup.find(id='linhaPesquisa')
        if div_linhas and div_linhas.find('tbody'):
            for tr in div_linhas.find('tbody').find_all('tr'):
                colunas = tr.find_all('td')
                if len(colunas) > 0 and colunas[0].get('colspan') is None:
                    titulo_linha = limpar_texto(colunas[0].get_text(strip=True))
                    html_da_vez = html_array_linhas_popups[idx_linha] if idx_linha < len(html_array_linhas_popups) else ""
                    dados["linhas"].append(self.extrair_detalhes_da_linha(html_da_vez, titulo_linha))
                    idx_linha += 1
        return dados

class LattesExtractor:
    def extrair_imagem(self, html, nome_pesquisador):
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img", class_="foto")
        if not img: return ""
        imagem_url = str(img.get("src"))
        if not imagem_url: return ""
        try:
            img_resposta = requests.get(imagem_url)
            nome_arquivo = f"{nome_pesquisador}.webp"
            caminho_completo = os.path.join(IMAGE_DIR, nome_arquivo)
            with open(caminho_completo, "wb") as arquivo:
                arquivo.write(img_resposta.content)
        except Exception as e:
            print(f'Não consegui baixar {imagem_url}. Erro: {e}')

    def extrair_informacoes_basicas(self, html):
        soup = BeautifulSoup(html, "html.parser")
        basico = {"resumo": "", "orcid_id": "", "nomes_citacoes": [], "nacionalidade": "", "ultima_att_lattes": ""}
        
        informacoes_autor = soup.find("ul", class_="informacoes-autor")
        if informacoes_autor:
            basico["ultima_att_lattes"] = informacoes_autor.find_all("li")[-1].text.strip()
        
        resumo = soup.find("p", class_="resumo")
        if resumo:
            basico["resumo"] = resumo.text.strip()
            
        a = soup.find("a", {'name': 'Identificacao'})
        if not a:
            return basico
        div = a.find_next("div")
        if not div:
            return basico
        
        divs = div.find_all("div", class_="text-align-right")
        chaves = {}
        for div_titulo in divs:
            b_tag = div_titulo.find("b")
            if b_tag:
                chave = b_tag.get_text(strip=True)
                div_valor = div_titulo.find_next_sibling("div", class_="layout-cell-9")
                if div_valor:
                    valor = div_valor.get_text(strip=True)
                    if "Orcid iD" in chave and valor.startswith("?"):
                        valor = valor.lstrip("?").strip()
                    chaves[chave] = valor

        for chave, valor in chaves.items():
            if chave == "País de Nacionalidade":
                basico["nacionalidade"] = valor
            if chave == "Orcid iD":
                basico["orcid_id"] = valor
            if chave == "Nome em citações bibliográficas":
                basico["nomes_citacoes"] = [c.strip() for c in valor.split(";") if c.strip()]
                
        return basico
    
    def extrair_detalhes_projetos(self, html):
        soup = BeautifulSoup(html, "html.parser")
        projeto_default = {"nome": "","descrição": "", "integrantes": "", "ano_inicio": "", "ano_fim": ""}
        projeto = {"projeto_pesquisa":[], "projeto_extensao":[], "projeto_desenvolvimento": [], "outros_projetos": []}
        chaves = {"ProjetosPesquisa":"projeto_pesquisa","ProjetosExtensao":"projeto_extensao" , "ProjetosDesenvolvimento":"projeto_desenvolvimento", "OutrosProjetos": "outros_projetos"}
        
        for chave, chave_projeto in chaves.items():
            a_tag = soup.find("a", {'name': chave})
            if not a_tag: continue
            div_tag = a_tag.find_next("div", class_="layout-cell layout-cell-12 data-cell")
            if not div_tag: continue
            
            for div in div_tag.find_all("div", class_="layout-cell layout-cell-3 text-align-right"):
                b_tag = div.find("b")
                if not b_tag:
                    continue

                texto = b_tag.get_text(strip=True)
                if not texto or "-" not in texto:
                    continue

                anos = texto.split("-")
                if len(anos) != 2:
                    continue

                novo_projeto = projeto_default.copy()
                novo_projeto["ano_inicio"] = anos[0].strip()
                novo_projeto["ano_fim"] = anos[1].strip()

                nome_div = div.find_next_sibling("div")
                if nome_div:
                    nome = nome_div.get_text(strip=True)
                    novo_projeto["nome"] = nome

                vazio_div = nome_div.find_next_sibling("div") if nome_div else None
                descricao_div = vazio_div.find_next_sibling("div") if vazio_div else None
                
                while descricao_div:
                    texto = descricao_div.get_text(strip=True)
                    if "Projeto certificado" in texto or not texto:
                        descricao_div = descricao_div.find_next_sibling("div")
                        continue
                    if "Descrição:" in texto or "Integrantes:" in texto:
                        break
                    descricao_div = descricao_div.find_next_sibling("div")
              
                if descricao_div:
                    texto_desc = descricao_div.get_text("\n")
                    if "Descrição:" not in texto_desc and "Integrantes:" not in texto_desc:
                        continue
                    for linha in texto_desc.split("\n"):
                        if "Descrição:" in linha:
                            novo_projeto["descrição"] = linha.replace("Descrição:", "").strip()
                        if "Integrantes:" in linha:
                            novo_projeto["integrantes"] = linha.replace("Integrantes:", "").strip()

                projeto[chave_projeto].append(novo_projeto)
                
        return projeto
    
    def extrair_detalhes_eventos(self, html):
        soup = BeautifulSoup(html, "html.parser")
        evento_default = {"nome": "", "tipo": "", "ano": ""}
        eventos = {"evento_participacao":[], "evento_organizacao": []}
        chaves = {"ParticipacaoEventos":"evento_participacao","OrganizacaoEventos":"evento_organizacao"}

        for chave, chave_evento in chaves.items():
            seen = set()
            a_tag = soup.find("a", {'name': chave})
            if not a_tag: continue
            div_tag = a_tag.find_next("div", class_="inst_back")
            if not div_tag: continue
            for div in div_tag.find_next_siblings("div", class_="layout-cell layout-cell-11"):
                novo_evento = evento_default.copy()
                span_tag = div.find("span")      
                if not span_tag:
                    continue
                texto = span_tag.get_text(strip=True)
                sep = re.split(r"(.+?)\s*(\b\d{4}\b)\.\s*\((.+?)\)", texto)
                if len(sep) > 0 and sep[0] == "": sep.pop(0)
                if len(sep) > 0 and sep[-1] == ".": sep.pop(-1)
                if len(sep) >= 3:
                    novo_evento["nome"] = sep[0].strip()
                    novo_evento["ano"] = sep[1].strip()
                    novo_evento["tipo"] = sep[2].strip()

                if novo_evento["nome"] and novo_evento["nome"] not in seen:
                    eventos[chave_evento].append(novo_evento)
                    seen.add(novo_evento["nome"])

        return eventos
