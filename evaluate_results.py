import json
import re
import os
import sys
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Append the actual project workspace to sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

from db.client import db
from generate_chart import generate_comparative_chart

# Load environment variables from relative path
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

# Instantiate the LLM Judge
judge_model = ChatOpenAI(
    api_key=os.environ.get("OPEN_AI_KEY"), model="gpt-4o-mini", temperature=0.0
).bind(response_format={"type": "json_object"})

JUDGE_PROMPT = PromptTemplate.from_template("""
Você é um avaliador acadêmico especialista em RAG (Retrieval-Augmented Generation) extremamente rigoroso, cricri e intolerante a qualquer extrapolação.
Sua tarefa é avaliar a qualidade da resposta gerada por um sistema de RAG para uma determinada pergunta, comparando-a com o Contexto de Referência fornecido (que é a verdade absoluta dos fatos).

Contexto de Referência:
{context}

Pergunta: {question}
Resposta Gerada: {answer}

Você deve responder estritamente com um objeto JSON contendo a avaliação sob as seguintes chaves e regras:
- "factual_correctness": nota de 1 a 5. Avalia se a Resposta Gerada está factualmente correta e de acordo com o Contexto de Referência (1 = totalmente incorreta/invenção, 5 = totalmente correta de acordo com as fontes).
- "coherence": nota de 1 a 5. Coerência lógica, fluidez e clareza da Resposta Gerada.
- "contextual_relevance": nota de 1 a 5. Relevância da Resposta Gerada em relação ao Contexto de Referência (se respondeu à pergunta com base no contexto ou se desviou).
- "multi_hop_score": nota de 1 a 5. Se a resposta exige conexões entre múltiplos fatos no contexto, avalie o quão bem realizou esse raciocínio complexo.
- "retrieval_precision": float de 0 a 100. Proporção das informações na resposta que são justificadas pelo contexto fornecido.
- "retrieval_recall": float de 0 a 100. Proporção das informações relevantes presentes no contexto que foram capturadas e incluídas na resposta.
- "is_hallucination": boolean. Defina como true se a resposta inventou, extrapolou, especulou ou adicionou qualquer detalhe mínimo (incluindo conectivos, suposições tangenciais ou extrapolações semânticas que parecem lógicas mas não estão escritas palavra por palavra no Contexto de Referência). Se houver qualquer informação na Resposta Gerada que não esteja presente no Contexto de Referência, você DEVE marcar como true. Se o modelo se recusou corretamente a responder alegando falta de contexto, defina como false.

JSON:""")


async def get_document_contents(sources):
    """Retrieves original full textual contents for verification from PostgreSQL using Metadados."""
    if not sources:
        return ""

    contents = []
    for s in sources:
        src_id = s.get("sourceId")
        if not src_id:
            continue
        try:
            doc = await db.ragdocument.find_first(where={"sourceId": src_id})
            if doc:
                contents.append(f"--- Fonte: {doc.titulo} ---\n{doc.conteudo}")
        except Exception as e:
            print(f"Erro ao buscar documento {src_id}: {e}")

    return "\n\n".join(contents)


async def evaluate_async():
    json_path = os.path.join(ROOT_DIR, "test_results.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            results = json.load(f)
    except FileNotFoundError:
        print(
            f"Arquivo de resultados '{json_path}' não encontrado. Por favor, execute o script 'run_experiments.py' primeiro."
        )
        return

    await db.connect()

    judge_chain = JUDGE_PROMPT | judge_model | StrOutputParser()

    total = len(results)
    print(
        f"Iniciando avaliação qualitativa de {total} questões usando LLM-as-a-Judge..."
    )

    # Aggregated metrics accumulator
    metrics_a = {
        "factual_correctness": 0.0,
        "coherence": 0.0,
        "contextual_relevance": 0.0,
        "multi_hop_score": 0.0,
        "retrieval_precision": 0.0,
        "retrieval_recall": 0.0,
        "hallucinations": 0,
        "latency": 0.0,
    }
    metrics_b = {
        "factual_correctness": 0.0,
        "coherence": 0.0,
        "contextual_relevance": 0.0,
        "multi_hop_score": 0.0,
        "retrieval_precision": 0.0,
        "retrieval_recall": 0.0,
        "hallucinations": 0,
        "latency": 0.0,
    }

    for idx, r in enumerate(results):
        question = r["question"]
        print(f"[{idx + 1}/{total}] Julgando: '{question}'...")

        # Load actual contexts from database (we use A's sources as reference for B)
        context_a = await get_document_contents(r["version_a"]["sources"])

        combined_context = (
            context_a if context_a else "Nenhum contexto recuperado das fontes."
        )

        # Add latency
        metrics_a["latency"] += r["version_a"]["time"]
        # Note: version_b contains the Sem RAG / No RAG baseline
        metrics_b["latency"] += r["version_b"]["time"]

        # Judge Version A (RAG Simples)
        ans_a = r["version_a"]["answer"]
        eval_raw_a = await judge_chain.ainvoke(
            {"context": combined_context, "question": question, "answer": ans_a}
        )
        try:
            eval_a = json.loads(eval_raw_a)
            metrics_a["factual_correctness"] += eval_a.get("factual_correctness", 1)
            metrics_a["coherence"] += eval_a.get("coherence", 1)
            metrics_a["contextual_relevance"] += eval_a.get("contextual_relevance", 1)
            metrics_a["multi_hop_score"] += eval_a.get("multi_hop_score", 1)
            metrics_a["retrieval_precision"] += eval_a.get("retrieval_precision", 0)
            metrics_a["retrieval_recall"] += eval_a.get("retrieval_recall", 0)
            if eval_a.get("is_hallucination", False):
                metrics_a["hallucinations"] += 1
        except Exception as e:
            print(f"Erro ao parsear avaliação A: {e}")

        # Judge Version B (LLM Sem RAG)
        ans_b = r["version_b"]["answer"]
        eval_raw_b = await judge_chain.ainvoke(
            {"context": combined_context, "question": question, "answer": ans_b}
        )
        try:
            eval_b = json.loads(eval_raw_b)
            metrics_b["factual_correctness"] += eval_b.get("factual_correctness", 1)
            metrics_b["coherence"] += eval_b.get("coherence", 1)
            metrics_b["contextual_relevance"] += eval_b.get("contextual_relevance", 1)
            metrics_b["multi_hop_score"] += eval_b.get("multi_hop_score", 1)
            metrics_b["retrieval_precision"] += 0.0
            metrics_b["retrieval_recall"] += 0.0
            if eval_b.get("is_hallucination", False):
                metrics_b["hallucinations"] += 1
        except Exception as e:
            print(f"Erro ao parsear avaliação B: {e}")

    await db.disconnect()

    # Calculate Averages
    avg_metrics_a = {
        k: v / total for k, v in metrics_a.items() if k not in ["hallucinations"]
    }
    avg_metrics_b = {
        k: v / total for k, v in metrics_b.items() if k not in ["hallucinations"]
    }

    hallucination_rate_a = (metrics_a["hallucinations"] / total) * 100.0
    hallucination_rate_b = (metrics_b["hallucinations"] / total) * 100.0

    # F1 Score calculations
    fact_pct_a = (avg_metrics_a["factual_correctness"] / 5.0) * 100.0
    rel_pct_a = (avg_metrics_a["contextual_relevance"] / 5.0) * 100.0
    f1_a = (
        (2 * fact_pct_a * rel_pct_a) / (fact_pct_a + rel_pct_a)
        if (fact_pct_a + rel_pct_a) > 0
        else 0
    )

    fact_pct_b = (avg_metrics_b["factual_correctness"] / 5.0) * 100.0
    rel_pct_b = (avg_metrics_b["contextual_relevance"] / 5.0) * 100.0
    f1_b = (
        (2 * fact_pct_b * rel_pct_b) / (fact_pct_b + rel_pct_b)
        if (fact_pct_b + rel_pct_b) > 0
        else 0
    )

    print("\n=== EXPERIMENTAL METRICS EVALUATED ===")
    print("Métrica | Versão A | Versão B")
    print(
        f"Coherence (1-5): {avg_metrics_a['coherence']:.2f} | {avg_metrics_b['coherence']:.2f}"
    )
    print(
        f"Contextual Relevance (1-5): {avg_metrics_a['contextual_relevance']:.2f} | {avg_metrics_b['contextual_relevance']:.2f}"
    )
    print(f"Retrieval Precision: {avg_metrics_a['retrieval_precision']:.1f}% | 0.0%")
    print(f"Retrieval Recall: {avg_metrics_a['retrieval_recall']:.1f}% | 0.0%")
    print(
        f"Hallucination Rate: {hallucination_rate_a:.1f}% | {hallucination_rate_b:.1f}%"
    )
    print(f"Factual Accuracy (F1): {f1_a:.1f}% | {f1_b:.1f}%")
    print(
        f"Tempo Médio de Resposta: {avg_metrics_a['latency']:.2f}s | {avg_metrics_b['latency']:.2f}s"
    )

    # Update main.tex content with advanced evaluated results
    latex_path = os.path.join(ROOT_DIR, "main.tex")
    with open(latex_path, "r", encoding="utf-8") as f:
        latex_content = f.read()

    table_pattern = r"(\\begin\{tabular\}\{lcc\}.*?\\end\{tabular\})"

    new_table = f"""\\begin{{tabular}}{{lcc}}
\\toprule
\\textbf{{Métrica}} & \\textbf{{Versão A (RAG Simples)}} & \\textbf{{Versão B (LLM Direto - Sem RAG)}} \\\\
\\midrule
Coerência (Coherence, 1-5) & {avg_metrics_a["coherence"]:.2f} & {avg_metrics_b["coherence"]:.2f} \\\\
Relevância Contextual (Contextual Relevance, 1-5) & {avg_metrics_a["contextual_relevance"]:.2f} & {avg_metrics_b["contextual_relevance"]:.2f} \\\\
Precisão de Recuperação (Retrieval Precision) & {avg_metrics_a["retrieval_precision"]:.1f}\\% & 0.0\\% \\\\
Recall de Recuperação (Retrieval Recall) & {avg_metrics_a["retrieval_recall"]:.1f}\\% & 0.0\\% \\\\
Taxa de Alucinação (Hallucination Rate) & {hallucination_rate_a:.1f}\\% & {hallucination_rate_b:.1f}\\% \\\\
Acurácia Factual (F1) & {f1_a:.1f}\\% & {f1_b:.1f}\\% \\\\
Latência Média de Ponta a Ponta & {avg_metrics_a["latency"]:.2f} s & {avg_metrics_b["latency"]:.2f} s \\\\
\\bottomrule
\\end{{tabular}}"""

    modified_latex = re.sub(
        table_pattern, lambda m: new_table, latex_content, flags=re.DOTALL
    )

    with open(latex_path, "w", encoding="utf-8") as f:
        f.write(modified_latex)

    print(f"\nTabela LaTeX atualizada com sucesso em '{latex_path}'!")

    # Update resultados_testes.md with the exact same evaluated metrics
    md_path = os.path.join(ROOT_DIR, "resultados_testes.md")

    md = []
    md.append("# Relatório Qualitativo e Quantitativo de Experimentos (RAG vs Sem RAG)")
    md.append(
        "\nEste relatório foi gerado automaticamente através de avaliação por **LLM-as-a-Judge** (GPT-4o-mini), comparando a arquitetura RAG Simples com a inferência direta no LLM (Sem RAG)."
    )

    md.append("\n## 📊 Resumo Comparativo das Métricas")
    md.append("| Métrica | Versão A (RAG Simples) | Versão B (LLM Direto - Sem RAG) |")
    md.append("| :--- | :---: | :---: |")
    md.append(
        f"| **Coerência (Coherence, 1-5)** | {avg_metrics_a['coherence']:.2f} | {avg_metrics_b['coherence']:.2f} |"
    )
    md.append(
        f"| **Relevância Contextual (1-5)** | {avg_metrics_a['contextual_relevance']:.2f} | {avg_metrics_b['contextual_relevance']:.2f} |"
    )
    md.append(
        f"| **Precisão de Recuperação (Retrieval Precision)** | {avg_metrics_a['retrieval_precision']:.1f}% | 0.0% |"
    )
    md.append(
        f"| **Recall de Recuperação (Retrieval Recall)** | {avg_metrics_a['retrieval_recall']:.1f}% | 0.0% |"
    )
    md.append(
        f"| **Taxa de Alucinação (Hallucination Rate)** | {hallucination_rate_a:.1f}% | {hallucination_rate_b:.1f}% |"
    )
    md.append(f"| **Acurácia Factual (F1)** | {f1_a:.1f}% | {f1_b:.1f}% |")
    md.append(
        f"| **Latência Média de Ponta a Ponta** | {avg_metrics_a['latency']:.2f}s | {avg_metrics_b['latency']:.2f}s |"
    )

    md.append("\n## 📝 Detalhamento das Perguntas e Respostas")

    for r in results:
        idx = r["index"]
        q = r["question"]
        cat = r["category"]
        q_type = r["type"]

        md.append("\n---")
        md.append(f"### Pergunta {idx}: `{q}`")
        md.append(f"* **Categoria:** {cat}")
        md.append(
            f"* **Tipo de Pergunta:** {'Factual' if q_type == 'Fact' else 'Recusa (Sem Contexto)'}"
        )

        ans_a = r["version_a"]["answer"].replace("\n", " ")
        md.append("\n* **Versão A (RAG Simples):**")
        md.append(f"  > *Resposta:* {ans_a}")
        if r["version_a"]["sources"]:
            md.append(
                "  > *Fontes:* "
                + ", ".join(
                    f"{s['title']} ({s['similarity']})"
                    for s in r["version_a"]["sources"]
                )
            )

        ans_b = r["version_b"]["answer"].replace("\n", " ")
        md.append("\n* **Versão B (LLM Direto - Sem RAG):**")
        md.append(f"  > *Resposta:* {ans_b}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"Relatório '{md_path}' atualizado com sucesso!")

    # Dynamically generate and update the comparison chart
    generate_comparative_chart(
        avg_metrics_a,
        avg_metrics_b,
        hallucination_rate_a,
        hallucination_rate_b,
        f1_a,
        f1_b,
    )


if __name__ == "__main__":
    asyncio.run(evaluate_async())
