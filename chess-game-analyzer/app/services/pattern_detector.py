from collections import Counter, defaultdict

from app.services.coaching_utils import (
    INSUFFICIENT_EVIDENCE,
    best_ref,
    critical_moves,
    move_ref,
    phase_label,
)

THEME_TO_PATTERN = {
    "desenvolvimento atrasado": "desenvolvimento atrasado",
    "erro de abertura": "abertura mal compreendida",
    "perda de tempo": "excesso de lances de peão",
    "rei exposto": "rei inseguro",
    "peça pendurada": "peça pendurada",
    "troca ruim": "troca ruim",
    "cálculo insuficiente": "cálculo tático insuficiente",
    "ataque duplo": "cálculo tático insuficiente",
    "ataque ao rei": "ignorar ameaças diretas",
    "controle central": "perda de iniciativa",
    "final de peões": "final mal convertido",
    "defesa passiva": "defesa passiva",
}

PATTERN_THEME = {
    "desenvolvimento atrasado": "Desenvolvimento e coordenação na abertura",
    "rei inseguro": "Segurança do rei",
    "cálculo tático insuficiente": "Cálculo de ameaças forçadas",
    "peça pendurada": "Peças indefesas",
    "troca ruim": "Avaliação de trocas",
    "final mal convertido": "Técnica de finais",
    "abertura mal compreendida": "Prioridades de abertura",
    "excesso de lances de peão": "Prioridade antes de lances laterais",
    "mover a mesma peça muitas vezes na abertura": "Tempos de desenvolvimento",
    "ignorar ameaças diretas": "Profilaxia e ameaças do adversário",
    "perda de iniciativa": "Centro, atividade e iniciativa",
    "defesa passiva": "Defesa ativa",
    "gerenciamento ruim de tempo": "Gerenciamento de tempo",
}

PATTERN_WEAKNESS = {
    "desenvolvimento atrasado": "Atrasou o desenvolvimento e a coordenação das peças.",
    "rei inseguro": "Deixou o rei vulnerável quando havia pressão adversária.",
    "cálculo tático insuficiente": "Não calculou completamente ameaças forçadas de 2 a 3 lances.",
    "peça pendurada": "Permitiu peças vulneráveis ou sem defesa suficiente.",
    "troca ruim": "Escolheu trocas que pioraram material ou atividade.",
    "final mal convertido": "Teve dificuldade em decisões de final.",
    "abertura mal compreendida": "Não respeitou as prioridades práticas da abertura.",
    "excesso de lances de peão": "Jogou lances de peão antes de resolver rei, centro ou desenvolvimento.",
    "mover a mesma peça muitas vezes na abertura": "Gastou tempos repetindo peça na abertura.",
    "ignorar ameaças diretas": "Deixou de responder a ameaças concretas do adversário.",
    "perda de iniciativa": "Cedeu atividade e controle central ao adversário.",
    "defesa passiva": "Defendeu de forma passiva em vez de buscar recursos ativos.",
    "gerenciamento ruim de tempo": "Usou mal o tempo disponível em momentos críticos.",
}


def _severity(count: int, total_cp: int) -> str:
    if count >= 3 or total_cp >= 700:
        return "high"
    if count >= 2 or total_cp >= 300:
        return "medium"
    return "low"


def _evidence_for_move(move: dict, pattern: str) -> str:
    explanation = move.get("explanation") or {}
    priorities = explanation.get("position_priorities") or []
    consequences = explanation.get("concrete_consequences") or []
    base = f"{move_ref(move)} em vez de {best_ref(move)}"
    if (
        pattern in {"rei inseguro", "desenvolvimento atrasado", "excesso de lances de peão"}
        and priorities
    ):
        return f"{base}: prioridade real era {', '.join(priorities[:2])}"
    if consequences:
        return f"{base}: {consequences[0]}"
    if explanation.get("why_it_worsens"):
        return f"{base}: {explanation['why_it_worsens']}"
    return base


def detect_patterns(moves: list[dict], color: str | None = None) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    phase_counter: dict[str, Counter[str]] = defaultdict(Counter)
    cp_counter: Counter[str] = Counter()

    for move in critical_moves(moves, color):
        themes = move.get("themes") or []
        for theme in themes:
            pattern = THEME_TO_PATTERN.get(theme)
            if not pattern:
                continue
            buckets[pattern].append(move)
            phase_counter[pattern][move.get("phase") or "unknown"] += 1
            cp_counter[pattern] += move.get("cp_loss") or 0

    patterns = []
    for pattern, pattern_moves in buckets.items():
        affected_phase = phase_counter[pattern].most_common(1)[0][0]
        evidence = []
        seen = set()
        for move in pattern_moves:
            text = _evidence_for_move(move, pattern)
            if text not in seen:
                seen.add(text)
                evidence.append(text)
            if len(evidence) >= 3:
                break
        patterns.append(
            {
                "pattern": pattern,
                "severity": _severity(len(pattern_moves), cp_counter[pattern]),
                "evidence": evidence or [INSUFFICIENT_EVIDENCE],
                "affected_phase": affected_phase,
                "affected_phase_label": phase_label(affected_phase),
                "study_priority": 0,
                "count": len(pattern_moves),
                "total_cp_loss": cp_counter[pattern],
                "theme": PATTERN_THEME.get(pattern, pattern),
                "weakness_text": PATTERN_WEAKNESS.get(pattern, pattern),
                "source_themes": sorted(
                    {
                        theme
                        for move in pattern_moves
                        for theme in (move.get("themes") or [])
                        if THEME_TO_PATTERN.get(theme) == pattern
                    }
                ),
            }
        )

    patterns.sort(
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(item["severity"], 0),
            item["count"],
            item["total_cp_loss"],
        ),
        reverse=True,
    )
    for index, pattern in enumerate(patterns, start=1):
        pattern["study_priority"] = index
    return patterns


def detect_patterns_by_color(moves: list[dict]) -> dict[str, list[dict]]:
    return {"white": detect_patterns(moves, "white"), "black": detect_patterns(moves, "black")}
