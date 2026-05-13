from collections import defaultdict

from app.services.coaching_utils import INSUFFICIENT_EVIDENCE, phase_label

AREA_KEYS = ["opening", "tactics", "strategy", "endgames", "time_management"]
PATTERN_AREA = {
    "desenvolvimento atrasado": "opening",
    "abertura mal compreendida": "opening",
    "excesso de lances de peão": "opening",
    "mover a mesma peça muitas vezes na abertura": "opening",
    "rei inseguro": "strategy",
    "perda de iniciativa": "strategy",
    "defesa passiva": "strategy",
    "cálculo tático insuficiente": "tactics",
    "peça pendurada": "tactics",
    "troca ruim": "strategy",
    "ignorar ameaças diretas": "tactics",
    "final mal convertido": "endgames",
    "gerenciamento ruim de tempo": "time_management",
}

AREA_LABELS = {
    "opening": "abertura",
    "tactics": "tática",
    "strategy": "estratégia",
    "endgames": "finais",
    "time_management": "gerenciamento de tempo",
}

THEME_TITLES = {
    "desenvolvimento atrasado": "Desenvolvimento e coordenação na abertura",
    "abertura mal compreendida": "Prioridades práticas da abertura",
    "excesso de lances de peão": "Segurança do rei antes de lances laterais",
    "mover a mesma peça muitas vezes na abertura": "Economia de tempos na abertura",
    "rei inseguro": "Segurança do rei",
    "perda de iniciativa": "Centro, atividade e iniciativa",
    "defesa passiva": "Defesa ativa",
    "cálculo tático insuficiente": "Cálculo de 2 a 3 lances",
    "peça pendurada": "Peças indefesas",
    "troca ruim": "Qualidade das trocas",
    "ignorar ameaças diretas": "Responder ameaças concretas",
    "final mal convertido": "Técnica de finais",
    "gerenciamento ruim de tempo": "Ritmo de decisão em momentos críticos",
}


def _training_for(pattern: str) -> list[str]:
    mapping = {
        "rei inseguro": [
            "Estudar posições onde o rei fica no centro contra vantagem de desenvolvimento.",
            "Antes de cada lance de abertura, perguntar: meu rei está seguro depois da resposta adversária?",
            "Revisar 10 partidas próprias marcando atrasos no roque ou na fuga do rei.",
        ],
        "desenvolvimento atrasado": [
            "Resolver posições de abertura escolhendo lances que desenvolvem peça com ganho de tempo.",
            "Comparar seus primeiros 10 lances com partidas modelo da mesma abertura.",
            "Treinar a pergunta: este lance melhora desenvolvimento, rei ou centro?",
        ],
        "excesso de lances de peão": [
            "Treinar cálculo antes de mover peões laterais na abertura.",
            "Separar lances de peão úteis de lances que apenas atacam uma peça que pode recuar.",
            "Revisar exemplos em que um lance lateral permitiu iniciativa no centro.",
        ],
        "cálculo tático insuficiente": [
            "Resolver exercícios com variantes forçadas de 2 a 3 lances.",
            "Antes de jogar, listar xeques, capturas e ameaças do adversário.",
            "Anotar o lance candidato e a resposta mais incômoda do adversário.",
        ],
        "peça pendurada": [
            "Fazer checklist de peças atacadas e peças sem defesa antes de cada lance.",
            "Resolver táticas focadas em peças indefesas e duplo ataque.",
            "Revisar os lances críticos perguntando qual peça ficou sobrecarregada.",
        ],
        "troca ruim": [
            "Antes de trocar, avaliar material, atividade das peças restantes e estrutura resultante.",
            "Estudar exemplos de trocas que entregam iniciativa ao adversário.",
            "Analisar finais simplificados perguntando quem fica com a peça ativa.",
        ],
    }
    return mapping.get(
        pattern,
        [
            f"Revisar os exemplos de {pattern} desta partida no tabuleiro.",
            "Transformar o erro recorrente em uma pergunta de checklist antes de jogar.",
            "Comparar o lance jogado com o melhor lance e escrever o que mudou na posição.",
        ],
    )


def _why_it_matters(pattern: dict) -> str:
    name = pattern.get("pattern")
    evidence = pattern.get("evidence") or []
    if name in {"rei inseguro", "desenvolvimento atrasado", "excesso de lances de peão"}:
        return "A partida mostrou que prioridades locais apareceram antes de desenvolvimento, coordenação ou segurança do rei."
    if name == "cálculo tático insuficiente":
        return "Os erros críticos indicam que respostas forçadas do adversário precisavam ser calculadas antes do lance escolhido."
    if name == "peça pendurada":
        return "Houve evidência de peças vulneráveis; isso transforma posições jogáveis em problemas táticos imediatos."
    if evidence:
        return f"A evidência principal foi: {evidence[0]}"
    return INSUFFICIENT_EVIDENCE


def _daily_exercise(pattern: str) -> str:
    if pattern in {"rei inseguro", "desenvolvimento atrasado", "excesso de lances de peão"}:
        return "Antes de cada lance na abertura, pergunte: este lance desenvolve peça, melhora o rei ou luta pelo centro?"
    if pattern == "cálculo tático insuficiente":
        return "Em 10 posições por dia, calcule a resposta mais forcing do adversário antes de olhar a solução."
    if pattern == "peça pendurada":
        return "Após cada lance candidato, aponte mentalmente todas as peças suas atacadas e indefesas."
    return "Escolha um momento crítico da partida e escreva em uma frase o que o melhor lance resolvia."


def _area_diagnosis(area: str, patterns: list[dict]) -> str:
    if not patterns:
        if area == "endgames":
            return "Poucos dados relevantes nesta partida."
        if area == "time_management":
            return (
                "Não há timestamps por lance suficientes para diagnosticar gerenciamento de tempo."
            )
        return (
            "Não há evidência suficiente nesta partida para apontar problema recorrente nesta área."
        )
    if area == "opening":
        return "Área prioritária: os erros indicam conflito entre lances locais e princípios de abertura."
    if area == "tactics":
        return "Erros táticos apareceram nos momentos críticos e precisam virar checklist antes do lance."
    if area == "strategy":
        return "A partida mostrou problemas de prioridade: segurança, coordenação e iniciativa pesaram mais que ameaças locais."
    if area == "endgames":
        return "Os finais tiveram impacto nos padrões críticos desta partida."
    return "Só é possível diagnosticar tempo quando o PGN contém timestamps úteis."


def generate_study_plan(
    patterns_by_color: dict[str, list[dict]], critical_moments: list[dict]
) -> dict:
    all_patterns = [pattern for patterns in patterns_by_color.values() for pattern in patterns]
    all_patterns.sort(key=lambda item: item.get("study_priority") or 99)
    if not all_patterns:
        summary = INSUFFICIENT_EVIDENCE
    else:
        top = all_patterns[0]
        summary = (
            "O principal problema foi "
            f"{top['pattern']} na {phase_label(top.get('affected_phase'))}, com evidência em: "
            f"{(top.get('evidence') or [INSUFFICIENT_EVIDENCE])[0]}"
        )

    priorities = []
    for index, pattern in enumerate(all_patterns[:5], start=1):
        examples = pattern.get("evidence") or [INSUFFICIENT_EVIDENCE]
        priorities.append(
            {
                "priority": index,
                "theme": THEME_TITLES.get(pattern["pattern"], pattern["pattern"]),
                "pattern": pattern["pattern"],
                "severity": pattern.get("severity"),
                "why_it_matters": _why_it_matters(pattern),
                "examples_from_game": examples,
                "how_to_train": _training_for(pattern["pattern"]),
                "daily_exercise": _daily_exercise(pattern["pattern"]),
                "recommended_time": "20 minutos por dia por 1 semana",
            }
        )

    area_patterns: dict[str, list[dict]] = defaultdict(list)
    for pattern in all_patterns:
        area_patterns[PATTERN_AREA.get(pattern["pattern"], "strategy")].append(pattern)

    areas = {}
    for area in AREA_KEYS:
        patterns = area_patterns.get(area, [])
        areas[area] = {
            "label": AREA_LABELS[area],
            "diagnosis": _area_diagnosis(area, patterns),
            "themes": [
                THEME_TITLES.get(pattern["pattern"], pattern["pattern"]) for pattern in patterns
            ],
            "evidence": [
                evidence for pattern in patterns for evidence in (pattern.get("evidence") or [])
            ][:3],
        }

    recommended_exercises = [
        exercise for priority in priorities for exercise in priority["how_to_train"][:1]
    ]
    if not recommended_exercises:
        recommended_exercises = [INSUFFICIENT_EVIDENCE]

    return {
        "summary": summary,
        "priorities": priorities,
        "areas": areas,
        "recommended_exercises": recommended_exercises,
        "critical_examples_count": len(critical_moments),
    }
