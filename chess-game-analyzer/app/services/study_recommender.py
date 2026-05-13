from collections import Counter, defaultdict

CATEGORY_BY_THEME = {
    "segurança do rei": "strategy",
    "desenvolvimento": "opening",
    "controle central": "opening",
    "proteger peças vulneráveis": "tactics",
    "melhorar atividade e coordenação das peças": "strategy",
    "erro de abertura": "opening",
    "desenvolvimento atrasado": "opening",
    "peça pendurada": "tactics",
    "tática de garfo": "tactics",
    "cravada": "tactics",
    "descoberta": "tactics",
    "ataque duplo": "tactics",
    "cálculo insuficiente": "tactics",
    "rei exposto": "strategy",
    "troca ruim": "strategy",
    "casa fraca": "strategy",
    "conversão de vantagem": "strategy",
    "defesa passiva": "strategy",
    "final de peões": "endgames",
}


def _exercise_for(theme: str) -> str:
    mapping = {
        "peça pendurada": "Resolva 15 posições procurando peças sem defesa antes de calcular capturas.",
        "cálculo insuficiente": "Treine variações forçadas de 2 a 3 lances antes de qualquer captura ou xeque.",
        "erro de abertura": "Revise os planos típicos da abertura jogada e compare seus 10 primeiros lances.",
        "desenvolvimento atrasado": "Pratique partidas rápidas buscando desenvolver peças menores antes de ataques laterais.",
        "final de peões": "Revise oposição, quadrado do peão e peões passados por 20 minutos.",
        "rei exposto": "Estude padrões de segurança do rei e punições contra roque enfraquecido.",
        "troca ruim": "Analise trocas perguntando quem melhora a peça restante e o final resultante.",
        "segurança do rei": "Revise partidas modelo em que o rei no centro é punido por abertura de linhas.",
        "desenvolvimento": "Treine escolher lances que desenvolvem peças antes de movimentos laterais de peão.",
        "controle central": "Resolva posições perguntando quais lances contestam d4/e4/d5/e5 imediatamente.",
        "proteger peças vulneráveis": "Antes de mover, liste peças atacadas, defensores e capturas candidatas do adversário.",
    }
    return mapping.get(theme, f"Resolva exercícios focados em {theme} por 20 minutos.")


def recommend_study(report: dict) -> dict:
    theme_counter: Counter[str] = Counter()
    examples = defaultdict(list)
    for item in [report.get("biggest_error"), report.get("critical_moment")]:
        if not item:
            continue
        explanation = item.get("explanation") or {}
        semantic = item.get("semantic_context") or {}
        teachable_points = list(item.get("themes") or [])
        teachable_points.extend(explanation.get("position_priorities") or [])
        teachable_points.extend(semantic.get("position_priorities") or [])
        for theme in teachable_points:
            theme_counter[theme] += 1
            examples[theme].append(
                {
                    "move_number": item.get("move_number"),
                    "move": item.get("played_san"),
                    "classification": item.get("classification"),
                    "cp_loss": item.get("cp_loss"),
                    "why": explanation.get("opponent_plan") or semantic.get("opponent_plan"),
                }
            )

    for color_counts in report.get("counts", {}).values():
        if color_counts.get("Blunder", 0) or color_counts.get("Mistake", 0):
            theme_counter["cálculo insuficiente"] += color_counts.get("Blunder", 0) + color_counts.get("Mistake", 0)

    priorities = [theme for theme, _ in theme_counter.most_common(5)] or ["cálculo insuficiente"]
    grouped = {"opening": [], "tactics": [], "strategy": [], "endgames": [], "time_management": []}
    for theme in priorities:
        category = CATEGORY_BY_THEME.get(theme, "strategy")
        grouped[category].append(
            {
                "theme": theme,
                "examples": examples.get(theme, []),
                "recommended_exercise": _exercise_for(theme),
                "short_plan": (
                    f"Estude {theme} por 20 minutos por dia; depois volte ao lance crítico e "
                    "explique qual prioridade da posição o melhor lance resolvia."
                ),
            }
        )

    grouped["time_management"].append(
        {
            "theme": "gerenciamento de tempo",
            "examples": [],
            "recommended_exercise": "Ative relógio em análises futuras; sem timestamps por lance o sistema não conclui causas de tempo.",
            "short_plan": "Após cada partida, marque lances críticos e compare com o tempo gasto, quando disponível.",
        }
    )
    return {"priorities": priorities[:5], "categories": grouped}
