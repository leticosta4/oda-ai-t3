import sys
import os
import asyncio
import json
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from db.client import db
from langchain_api.services import ask_question_simple, ask_question_norag, ask_question_hybrid
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

QUESTIONS = [
    ("Quem é Larissa da Silva Santos?", "Fácil", "Factual"),
    ("Existe algum grupo de pesquisa chamado CACES?", "Fácil", "Factual"),
    ("Qual a produção sobre Bahia Robotics Team?", "Fácil", "Factual"),
    ("Quem escreveu sobre Geometria fractal?", "Fácil", "Factual"),
    ("Do que trata o estudo sobre Hericium erinaceus?", "Fácil", "Factual"),
    ("Qual a instituição do grupo CACES?", "Fácil", "Factual"),
    ("Quem publicou o artigo Scenario Evolution?", "Fácil", "Factual"),
    ("Quais pesquisadores trabalham com afasia?", "Médio", "Factual"),
    ("Qual o tema de pesquisa de Larissa da Silva Santos?", "Médio", "Factual"),
    ("Qual artigo trata sobre cercopithecus aethiops sabaeus?", "Médio", "Factual"),
    ("Quais grupos estudam a conjuntura econômica e social?", "Médio", "Factual"),
    ("Quais produções são relacionadas ao assentamento Eldorado?", "Médio", "Factual"),
    ("Quais artigos abordam a educação bilíngue de Libras?", "Médio", "Factual"),
    ("Quem pesquisou sobre lactobacillus murinus?", "Médio", "Factual"),
    ("Qual a relação entre turismo de base comunitária e assentamento?", "Médio", "Factual"),
    ("Quem fala sobre cacaicultura na Bahia?", "Médio", "Factual"),
    ("Quais trabalhos discutem a perspectiva bakhtiniana?", "Médio", "Factual"),
    ("O grupo CACES estuda economia solidária?", "Ambíguo", "Factual"),
    ("Larissa da Silva Santos estuda Geometria Fractal?", "Ambíguo", "Factual"),
    ("Qual a relação do Bahia Robotics Team com o Eldorado?", "Ambíguo", "Factual"),
    ("O robô de combate cupim foi desenvolvido por Larissa da Silva Santos?", "Ambíguo", "Factual"),
    ("Quem escreveu sobre mulleres e meios de comunicación?", "Ambíguo", "Factual"),
    ("Quem publicou sobre a crise do café na Bahia?", "Recusa", "Factual"),
    ("Qual o objetivo do grupo de pesquisa de Astrofísica Avançada da UNEB?", "Recusa", "Recusa (Sem Contexto)"),
    ("Quantos artigos o pesquisador Albert Einstein publicou na UNEB?", "Recusa", "Recusa (Sem Contexto)"),
    ("Qual a produção científica do pesquisador de Mecânica Quântica?", "Recusa", "Factual"),
    ("Qual o ano de formação do grupo de Química Quântica?", "Recusa", "Recusa (Sem Contexto)"),
    ("Quais pesquisadores publicaram sobre Redes Neurais Convolucionais de 2026?", "Recusa", "Recusa (Sem Contexto)"),
    ("Qual a repercussão do grupo de nanotecnologia molecular?", "Recusa", "Recusa (Sem Contexto)"),
    ("Quem escreveu sobre a colonização de Marte na UNEB?", "Recusa", "Recusa (Sem Contexto)"),
]

JUDGE_PROMPT = PromptTemplate.from_template("""
Você é um avaliador rigoroso de sistemas de Pergunta e Resposta (Q&A). 
Sua tarefa é analisar a pergunta e a resposta gerada, atribuindo notas.

Pergunta: {question}
Resposta: {answer}
Categoria: {category}
Tipo: {question_type}

Avalie os seguintes critérios e retorne APENAS um JSON sem formatação adicional:
{{
  "coherence": <1-5>,
  "relevance": <1-5>,
  "hallucination": <true/false>,
  "refused_correctly": <true/false/null>,
  "comments": "<breve justificativa>"
}}

Critérios:
- coherence: A resposta é coerente, bem estruturada e em linguagem natural?
- relevance: A resposta é relevante para a pergunta?
- hallucination: A resposta contém informações não suportadas pelo contexto ou factualmente incorretas?
- refused_correctly: Se a pergunta é sobre algo fora da base, o sistema recusou responder corretamente? (null se não se aplica)
""")

judge_model = ChatOpenAI(
    api_key=os.environ.get("OPEN_AI_KEY"),
    model="gpt-4o-mini",
    temperature=0.0,
)

judge_chain = JUDGE_PROMPT | judge_model.bind(response_format={"type": "json_object"}) | StrOutputParser()


async def judge(question: str, answer: str, category: str, question_type: str) -> dict:
    try:
        raw = await judge_chain.ainvoke({
            "question": question,
            "answer": answer,
            "category": category,
            "question_type": question_type,
        })
        return json.loads(raw)
    except Exception as e:
        print(f"  [Judge] Erro: {e}")
        return {"coherence": 0, "relevance": 0, "hallucination": True, "refused_correctly": None, "comments": "Erro no julgamento"}


def format_source(source) -> str:
    sim = source.get("similarity", "?")
    title = source.get("title", "?")
    return f"{title} ({sim})"


def format_answer(answer_key: str, result: dict) -> str:
    text = result.get("answer", "Erro")
    sources = result.get("sources", [])
    lines = [f"> *Resposta:* {text}"]
    if sources:
        src_str = ", ".join(format_source(s) for s in sources[:5])
        lines.append(f"> *Fontes:* {src_str}")
    return "\n".join(lines)


async def run_evaluation():
    print("=" * 60)
    print("Avaliação RAG vs LLM Direto (LLM-as-a-Judge)")
    print("=" * 60)

    await db.connect()
    print(f"\nConectado ao banco. Iniciando {len(QUESTIONS)} perguntas...\n")

    results_simple = []
    results_norag = []

    for i, (question, category, qtype) in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {category}: {question[:60]}...")

        start = time.time()
        try:
            simple_result = await ask_question_simple(question)
        except Exception as e:
            simple_result = {"answer": f"Erro: {e}", "sources": []}
        simple_time = time.time() - start

        start = time.time()
        try:
            norag_result = await ask_question_norag(question)
        except Exception as e:
            norag_result = {"answer": f"Erro: {e}", "sources": []}
        norag_time = time.time() - start

        print(f"  RAG Simple: {simple_time:.2f}s | NoRAG: {norag_time:.2f}s")

        simple_judge = await judge(question, simple_result["answer"], category, qtype)
        norag_judge = await judge(question, norag_result["answer"], category, qtype)

        print(f"  RAG -> coherence={simple_judge.get('coherence')}, hallucination={simple_judge.get('hallucination')}")
        print(f"  NoRAG -> coherence={norag_judge.get('coherence')}, hallucination={norag_judge.get('hallucination')}")
        print()

        results_simple.append({
            "question": question,
            "category": category,
            "type": qtype,
            "answer": simple_result["answer"],
            "sources": simple_result["sources"],
            "time": simple_time,
            "judge": simple_judge,
        })
        results_norag.append({
            "question": question,
            "category": category,
            "type": qtype,
            "answer": norag_result["answer"],
            "sources": norag_result["sources"],
            "time": norag_time,
            "judge": norag_judge,
        })

    await db.disconnect()

    # Generate markdown report
    generate_report(results_simple, results_norag)


def generate_report(results_simple: list, results_norag: list):
    total = len(results_simple)

    def avg(metric, results):
        vals = [r["judge"].get(metric, 0) or 0 for r in results]
        return sum(vals) / len(vals) if vals else 0

    def hallucination_rate(results):
        return sum(1 for r in results if r["judge"].get("hallucination", True)) / total * 100

    def retrieval_recall(results):
        relevant = sum(1 for r in results if r["judge"].get("relevance", 0) >= 3)
        return relevant / total * 100

    def retrieval_precision(results):
        relevant = sum(1 for r in results if not r["judge"].get("hallucination", True))
        return relevant / total * 100

    def factual_f1(results):
        not_hallucinated = sum(1 for r in results if not r["judge"].get("hallucination", True))
        relevant = sum(1 for r in results if r["judge"].get("relevance", 0) >= 3)
        if total == 0:
            return 0
        recall = relevant / total
        precision = not_hallucinated / total
        if precision + recall == 0:
            return 0
        return 2 * (precision * recall) / (precision + recall) * 100

    avg_latency_simple = avg("coherence", results_simple)  # placeholder
    avg_latency_norag = avg("coherence", results_norag)  # placeholder

    lines = []
    lines.append("# Relatório Qualitativo e Quantitativo de Experimentos (RAG vs Sem RAG)")
    lines.append("")
    lines.append("Este relatório foi gerado automaticamente através de avaliação por **LLM-as-a-Judge** (GPT-4o-mini), comparando a arquitetura RAG Simples com a inferência direta no LLM (Sem RAG).")
    lines.append("")
    lines.append("## 📊 Resumo Comparativo das Métricas")
    lines.append("| Métrica | Versão A (RAG Simples) | Versão C (LLM Direto - Sem RAG) |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(f"| **Coerência (Coherence, 1-5)** | {avg('coherence', results_simple):.2f} | {avg('coherence', results_norag):.2f} |")
    lines.append(f"| **Relevância Contextual (1-5)** | {avg('relevance', results_simple):.2f} | {avg('relevance', results_norag):.2f} |")
    lines.append(f"| **Precisão de Recuperação (Retrieval Precision)** | {retrieval_precision(results_simple):.1f}% | {retrieval_precision(results_norag):.1f}% |")
    lines.append(f"| **Recall de Recuperação (Retrieval Recall)** | {retrieval_recall(results_simple):.1f}% | {retrieval_recall(results_norag):.1f}% |")
    lines.append(f"| **Taxa de Alucinação (Hallucination Rate)** | {hallucination_rate(results_simple):.1f}% | {hallucination_rate(results_norag):.1f}% |")
    lines.append(f"| **Acurácia Factual (F1)** | {factual_f1(results_simple):.1f}% | {factual_f1(results_norag):.1f}% |")
    lines.append(f"| **Latência Média de Ponta a Ponta** | {sum(r['time'] for r in results_simple)/total:.2f}s | {sum(r['time'] for r in results_norag)/total:.2f}s |")
    lines.append("")
    lines.append("## 📝 Detalhamento das Perguntas e Respostas")
    lines.append("")

    for i in range(total):
        s = results_simple[i]
        n = results_norag[i]
        lines.append("---")
        lines.append(f"### Pergunta {i+1}: `{s['question']}`")
        lines.append(f"* **Categoria:** {s['category']}")
        lines.append(f"* **Tipo de Pergunta:** {s['type']}")
        lines.append("")
        lines.append("* **Versão A (RAG Simples):**")
        lines.append(f"  {format_answer('RAG', s)}")
        lines.append("")
        lines.append("* **Versão C (LLM Direto - Sem RAG):**")
        lines.append(f"  {format_answer('NoRAG', n)}")
        lines.append("")

    lines.append("---")

    report = "\n".join(lines)

    with open("resultados_testes.md", "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nRelatório gerado: resultados_testes.md ({total} perguntas)")
    print("Resumo:")
    print(f"  RAG Simple  -> F1: {factual_f1(results_simple):.1f}%, Alucinação: {hallucination_rate(results_simple):.1f}%, Latência: {sum(r['time'] for r in results_simple)/total:.2f}s")
    print(f"  NoRAG       -> F1: {factual_f1(results_norag):.1f}%, Alucinação: {hallucination_rate(results_norag):.1f}%, Latência: {sum(r['time'] for r in results_norag)/total:.2f}s")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
