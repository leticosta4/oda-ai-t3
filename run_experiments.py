import asyncio
import sys
import os
import time
import json

# Set PYTHONPATH to the current root directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.client import db
from langchain_api.services import ask_question_simple, ask_question_norag

# 30 Test questions categorized
QUESTIONS = [
    # Fácil (1-7)
    {"q": "Quem é Larissa da Silva Santos?", "category": "Fácil", "type": "Fact"},
    {"q": "Existe algum grupo de pesquisa chamado CACES?", "category": "Fácil", "type": "Fact"},
    {"q": "Qual a produção sobre Bahia Robotics Team?", "category": "Fácil", "type": "Fact"},
    {"q": "Quem escreveu sobre Geometria fractal?", "category": "Fácil", "type": "Fact"},
    {"q": "Do que trata o estudo sobre Hericium erinaceus?", "category": "Fácil", "type": "Fact"},
    {"q": "Qual a instituição do grupo CACES?", "category": "Fácil", "type": "Fact"},
    {"q": "Quem publicou o artigo Scenario Evolution?", "category": "Fácil", "type": "Fact"},
    
    # Médio (8-17)
    {"q": "Quais pesquisadores trabalham com afasia?", "category": "Médio", "type": "Fact"},
    {"q": "Qual o tema de pesquisa de Larissa da Silva Santos?", "category": "Médio", "type": "Fact"},
    {"q": "Qual artigo trata sobre cercopithecus aethiops sabaeus?", "category": "Médio", "type": "Fact"},
    {"q": "Quais grupos estudam a conjuntura econômica e social?", "category": "Médio", "type": "Fact"},
    {"q": "Quais produções são relacionadas ao assentamento Eldorado?", "category": "Médio", "type": "Fact"},
    {"q": "Quais artigos abordam a educação bilíngue de Libras?", "category": "Médio", "type": "Fact"},
    {"q": "Quem pesquisou sobre lactobacillus murinus?", "category": "Médio", "type": "Fact"},
    {"q": "Qual a relação entre turismo de base comunitária e assentamento?", "category": "Médio", "type": "Fact"},
    {"q": "Quem fala sobre cacaicultura na Bahia?", "category": "Médio", "type": "Fact"},
    {"q": "Quais trabalhos discutem a perspective bakhtiniana?", "category": "Médio", "type": "Fact"},
    
    # Ambíguo (18-22)
    {"q": "O grupo CACES estuda economia solidária?", "category": "Ambíguo", "type": "Fact"},
    {"q": "Larissa da Silva Santos estuda Geometria Fractal?", "category": "Ambíguo", "type": "Fact"},
    {"q": "Qual a relação do Bahia Robotics Team com o Eldorado?", "category": "Ambíguo", "type": "Fact"},
    {"q": "O robô de combate cupim foi desenvolvido por Larissa da Silva Santos?", "category": "Ambíguo", "type": "Fact"},
    {"q": "Quem escreveu sobre mulleres e meios de comunicación?", "category": "Ambíguo", "type": "Fact"},
    
    # Recusa / Contexto Ausente (23-30)
    {"q": "Quem publicou sobre a crise do café na Bahia?", "category": "Recusa", "type": "Fact"},
    {"q": "Qual o objetivo do grupo de pesquisa de Astrofísica Avançada da UNEB?", "category": "Recusa", "type": "Refusal"},
    {"q": "Quantos artigos o pesquisador Albert Einstein publicou na UNEB?", "category": "Recusa", "type": "Refusal"},
    {"q": "Qual a produção científica do pesquisador de Mecânica Quântica?", "category": "Recusa", "type": "Fact"},
    {"q": "Qual o ano de formação do grupo de Química Quântica?", "category": "Recusa", "type": "Refusal"},
    {"q": "Quais pesquisadores publicaram sobre Redes Neurais Convolucionais de 2026?", "category": "Recusa", "type": "Refusal"},
    {"q": "Qual a repercussão do grupo de nanotecnologia molecular?", "category": "Recusa", "type": "Refusal"},
    {"q": "Quem escreveu sobre a colonização de Marte na UNEB?", "category": "Recusa", "type": "Refusal"},
]

async def run_tests():
    await db.connect()
    
    results = []
    
    print(f"Iniciando bateria de testes com {len(QUESTIONS)} questões...")
    
    for idx, item in enumerate(QUESTIONS):
        q = item["q"]
        cat = item["category"]
        q_type = item["type"]
        
        print(f"\n[{idx+1}/30] [{cat}] Executando: {q}")
        
        # Test Simple RAG (Versão A)
        start_a = time.time()
        res_a = await ask_question_simple(q)
        time_a = time.time() - start_a
        
        # Test LLM Sem RAG (Versão B)
        start_b = time.time()
        res_b = await ask_question_norag(q)
        time_b = time.time() - start_b
        
        # Log to console
        print(f"  Versão A (Simple RAG) ({time_a:.2f}s): {res_a['answer'][:100]}...")
        print(f"  Versão B (No RAG)     ({time_b:.2f}s): {res_b['answer'][:100]}...")
        
        results.append({
            "index": idx + 1,
            "question": q,
            "category": cat,
            "type": q_type,
            "version_a": {
                "answer": res_a["answer"],
                "sources_count": len(res_a["sources"]),
                "sources": res_a["sources"],
                "time": time_a
            },
            "version_b": {
                "answer": res_b["answer"],
                "sources_count": 0,
                "sources": [],
                "time": time_b
            }
        })
        
    await db.disconnect()
    
    # Save raw test results to current project directory
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("\nResultados salvos com sucesso em './test_results.json'!")

if __name__ == "__main__":
    asyncio.run(run_tests())
