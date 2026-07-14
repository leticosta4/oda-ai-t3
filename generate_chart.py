import os
import matplotlib.pyplot as plt
import numpy as np

def generate_comparative_chart(avg_metrics_a, avg_metrics_b, hallucination_rate_a, hallucination_rate_b, f1_a, f1_b):
    """
    Generates a comparative bar chart dynamically based on evaluated metrics.
    """
    # Set style for a clean look
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Data for Plot 1 (Scores 1-5)
    labels_scores = ['Coerência', 'Relevância\nContextual']
    rag_scores = [avg_metrics_a.get('coherence', 1.0), avg_metrics_a.get('contextual_relevance', 1.0)]
    norage_scores = [avg_metrics_b.get('coherence', 1.0), avg_metrics_b.get('contextual_relevance', 1.0)]

    # Data for Plot 2 (Percentages)
    labels_pct = ['Acurácia Factual (F1)', 'Taxa de Alucinação']
    rag_pct = [f1_a, hallucination_rate_a]
    norage_pct = [f1_b, hallucination_rate_b]

    x = np.arange(len(labels_scores))
    width = 0.35

    # Color Palette
    color_rag = '#1f77b4'  # Deep blue
    color_norage = '#d62728'  # Muted red

    # Plot 1: Scores 1-5
    rects1_a = ax1.bar(x - width/2, rag_scores, width, label='Versão A (RAG Simples)', color=color_rag)
    rects1_b = ax1.bar(x + width/2, norage_scores, width, label='Versão B (LLM Sem RAG)', color=color_norage)
    ax1.set_ylabel('Pontuação (1 - 5)', fontsize=11, fontweight='bold')
    ax1.set_title('Métricas de Qualidade de Resposta', fontsize=12, fontweight='bold', pad=15)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels_scores, fontsize=10)
    ax1.set_ylim(0, 5.5)
    ax1.legend(loc='lower left')

    # Plot 2: Percentages
    x2 = np.arange(len(labels_pct))
    rects2_a = ax2.bar(x2 - width/2, rag_pct, width, label='Versão A (RAG Simples)', color=color_rag)
    rects2_b = ax2.bar(x2 + width/2, norage_pct, width, label='Versão B (LLM Sem RAG)', color=color_norage)
    ax2.set_ylabel('Percentual (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Métricas Factual e Alucinação', fontsize=12, fontweight='bold', pad=15)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(labels_pct, fontsize=10)
    ax2.set_ylim(0, 110)
    ax2.legend(loc='upper right')

    # Value labels helper
    def autolabel(rects, ax, is_pct=False):
        for rect in rects:
            height = rect.get_height()
            suffix = '%' if is_pct else ''
            ax.annotate(f'{height:.1f}{suffix}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, fontweight='bold')

    autolabel(rects1_a, ax1)
    autolabel(rects1_b, ax1)
    autolabel(rects2_a, ax2, is_pct=True)
    autolabel(rects2_b, ax2, is_pct=True)

    plt.tight_layout()

    # Save image
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(ROOT_DIR, "static", "resultado_comparativo.png")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Gráfico comparativo atualizado dinamicamente em '{output_path}'")

if __name__ == "__main__":
    # Fallback to default metrics if run directly
    print("Executando com métricas padrão do último experimento...")
    default_metrics_a = {'coherence': 4.93, 'contextual_relevance': 4.97}
    default_metrics_b = {'coherence': 3.77, 'contextual_relevance': 1.67}
    generate_comparative_chart(default_metrics_a, default_metrics_b, 3.3, 90.0, 99.3, 34.0)
