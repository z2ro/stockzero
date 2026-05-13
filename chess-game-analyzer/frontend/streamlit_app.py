from html import escape
from io import StringIO
import os

import chess
import chess.pgn
import chess.svg
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Chess Game Analyzer", page_icon="♟️", layout="wide")

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_MAX_MOVES = int(os.getenv("DEFAULT_ANALYSIS_MAX_MOVES", "80"))
API_URL = st.sidebar.text_input("API URL", DEFAULT_API_URL).rstrip("/")
st.title("♟️ Chess Game Analyzer")
st.caption(
    "Analise PGNs ou partidas públicas do Chess.com com um tabuleiro navegável "
    "e explicações mais claras."
)


def inject_review_css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #302e2c; color: #ddd; }
        div[data-testid="stHeader"] { background: rgba(48, 46, 44, 0.96); }
        .block-container { padding-top: 1rem; max-width: 1400px; }
        .review-player {
            background: #252421; border-radius: 6px; padding: 8px 12px;
            display: flex; align-items: center; justify-content: space-between;
            margin: 6px 0; color: #f1f1f1; font-weight: 700;
        }
        .review-player .rating { color: #b8b8b8; font-weight: 500; }
        .review-clock {
            background: #f1f1f1; color: #222; border-radius: 4px;
            padding: 5px 14px; font-size: 1.35rem; font-weight: 800;
        }
        .review-panel {
            background: #242321; border-radius: 8px; border: 1px solid #191817;
            padding: 0 14px 14px 14px; box-shadow: 0 8px 24px rgba(0,0,0,.25);
        }
        .review-header {
            height: 46px; display: flex; align-items: center; justify-content: center;
            border-bottom: 1px solid #383633; font-size: 1.05rem; font-weight: 800;
        }
        .coach-row { display: flex; gap: 12px; align-items: center; margin: 18px 0; }
        .coach-avatar { font-size: 4.2rem; line-height: 1; }
        .coach-bubble {
            background: #f6f6f6; color: #111; border-radius: 10px;
            padding: 16px 18px; font-weight: 700; flex: 1; min-height: 62px;
        }
        .review-actions { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin: 10px 0; }
        .review-action {
            background: linear-gradient(#4a4946, #333230); border-radius: 5px;
            text-align: center; padding: 12px 6px; font-weight: 800; color: #e9e9e9;
        }
        .review-action.next { background: linear-gradient(#8cc45a, #5a9c3d); color: white; }
        .move-list { max-height: 330px; overflow-y: auto; margin-top: 6px; }
        .move-table { width: 100%; border-collapse: collapse; font-size: .94rem; }
        .move-table td { padding: 6px 8px; border: 0; }
        .move-table tr:nth-child(odd) { background: #2b2a27; }
        .move-table .num { color: #aaa; width: 38px; text-align: right; }
        .move-table .selected { background: rgba(125, 176, 80, .28); color: #b8f27b; font-weight: 800; border-radius: 4px; }
        .move-row { display: grid; grid-template-columns: 38px 1fr 1fr; gap: 6px; align-items: center; margin: 2px 0; }
        .move-num { color: #aaa; text-align: right; padding-right: 6px; font-weight: 700; }
        .critical-inline {
            background: #332f2a; border-left: 3px solid #f0b84a; border-radius: 4px;
            padding: 7px 9px; margin: 6px 0 8px 44px; font-size: .86rem;
        }
        .critical-card {
            border: 1px solid #403f3b; border-radius: 6px; padding: 10px 12px;
            margin: 8px 0; background: #1f1e1c;
        }
        .critical-card strong { color: #fff; }
        .eval-wrap { background: #3a3936; border-radius: 2px; padding: 5px; margin-top: 14px; }
        .bottom-controls { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 12px; }
        .bottom-controls div {
            background: linear-gradient(#4a4946, #302f2d); border-radius: 7px;
            text-align: center; padding: 14px 0; font-weight: 900; font-size: 1.35rem;
        }
        div.stButton > button {
            background: linear-gradient(#4a4946, #333230); color: #eee; border: 0;
            border-radius: 6px; font-weight: 800; min-height: 42px; width: 100%;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(#8cc45a, #5a9c3d); color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_review_css()


CLASS_EMOJI = {
    "Best": "✅",
    "Excellent": "🌟",
    "Good": "👍",
    "Inaccuracy": "⚠️",
    "Mistake": "❌",
    "Blunder": "🚨",
    "Missed Win": "💎",
    "Forced": "🔒",
    "Book move": "📖",
}


def api_get(path: str) -> dict:
    response = requests.get(f"{API_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict, timeout: int = 600) -> dict:
    response = requests.post(f"{API_URL}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def positions_from_pgn(pgn: str) -> list[dict]:
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        return []

    board = game.board()
    positions = [
        {
            "label": "Início",
            "board": board.copy(stack=False),
            "lastmove": None,
            "ply": 0,
            "san": "",
        }
    ]
    for ply, move in enumerate(game.mainline_moves(), start=1):
        san = board.san(move)
        board.push(move)
        move_number = (ply + 1) // 2
        color = "Brancas" if ply % 2 else "Pretas"
        positions.append(
            {
                "label": f"{move_number}. {san}" if ply % 2 else f"{move_number}... {san}",
                "board": board.copy(stack=False),
                "lastmove": move,
                "ply": ply,
                "san": san,
                "color": color,
            }
        )
    return positions


def render_board(
    position: dict,
    orientation: chess.Color = chess.WHITE,
    arrows: list[chess.svg.Arrow] | None = None,
    size: int = 720,
) -> None:
    svg = chess.svg.board(
        board=position["board"],
        lastmove=position.get("lastmove"),
        arrows=arrows or [],
        orientation=orientation,
        size=size,
        colors={"square light": "#eeeed2", "square dark": "#769656"},
    )
    components.html(svg, height=size + 18)


def arrow_from_uci(uci: str | None, color: str) -> chess.svg.Arrow | None:
    if not uci or len(uci) < 4:
        return None
    try:
        return chess.svg.Arrow(
            chess.parse_square(uci[:2]),
            chess.parse_square(uci[2:4]),
            color=color,
        )
    except ValueError:
        return None


def best_move_arrows(item: dict | None) -> list[chess.svg.Arrow]:
    if not item:
        return []

    arrows: list[chess.svg.Arrow] = []
    played_arrow = arrow_from_uci(item.get("played_uci"), "#e74c3c")
    if played_arrow:
        arrows.append(played_arrow)

    best_uci = item.get("best_move_uci")
    if not best_uci and item.get("best_lines"):
        best_uci = item["best_lines"][0].get("move_uci")
    if best_uci != item.get("played_uci"):
        best_arrow = arrow_from_uci(best_uci, "#7ac943")
        if best_arrow:
            arrows.append(best_arrow)
    return arrows


def board_position_for_selection(
    positions: list[dict],
    item: dict | None,
    selected: int,
) -> dict:
    if item and item.get("fen_before"):
        return {
            "label": f"Antes de {item.get('move_number')}. {item.get('played_san')}",
            "board": chess.Board(item["fen_before"]),
            "lastmove": None,
            "ply": item.get("ply"),
        }
    return positions[selected]


def move_analysis_by_ply(game: dict) -> dict[int, dict]:
    return {item["ply"]: item for item in (game.get("analysis") or {}).get("moves", [])}


def count_pgn_plies(pgn: str | None) -> int:
    if not pgn:
        return 0
    return max(0, len(positions_from_pgn(pgn)) - 1)


def player_text(player: dict) -> str:
    username = player.get("username") or "?"
    rating = player.get("rating")
    rating_text = f" ({rating})" if rating else ""
    return f"{username}{rating_text}"


def show_chesscom_games_panel(username: str, games: list[dict], max_moves: int) -> None:
    st.subheader("Histórico de Partidas")
    if not games:
        st.info("Nenhuma partida pública com PGN foi encontrada para esse usuário.")
        return

    header = st.columns([3, 1, 1, 1, 1, 1])
    header[0].markdown("**Jogadores**")
    header[1].markdown("**Resultado**")
    header[2].markdown("**Tempo**")
    header[3].markdown("**Lances**")
    header[4].markdown("**Data**")
    header[5].markdown("**Ação**")

    for index, game in enumerate(games):
        row = st.container(border=True)
        with row:
            cols = st.columns([3, 1, 1, 1, 1, 1])
            white = player_text(game.get("white", {}))
            black = player_text(game.get("black", {}))
            user_color = game.get("user_color")
            marker_white = "👉 " if user_color == "white" else ""
            marker_black = "👉 " if user_color == "black" else ""
            cols[0].markdown(f"♙ {marker_white}{white}  \n♟ {marker_black}{black}")
            cols[1].markdown(f"**{game.get('result') or '?'}**")
            cols[2].write(game.get("time_class") or game.get("time_control") or "—")
            cols[3].write(count_pgn_plies(game.get("pgn")))
            cols[4].write(game.get("played_at") or "—")
            if cols[5].button("Analizar", key=f"analyze_chesscom_{index}"):
                payload = {
                    "username": username,
                    "pgn": game["pgn"],
                    "url": game.get("url"),
                    "max_moves": max_moves,
                }
                with st.spinner("Analisando apenas esta partida com Stockfish..."):
                    data = api_post("/analyze/chesscom/game", payload, timeout=900)
                st.session_state["game_id"] = data["game_id"]
                st.success(f"Partida analisada: game_id={data['game_id']}")
                st.rerun()


def show_metrics(report: dict) -> None:
    accuracy = report.get("accuracy", {})
    counts = report.get("counts", {})
    cols = st.columns(4)
    cols[0].metric("Precisão brancas", f"{accuracy.get('white', 0)}%")
    cols[1].metric("Precisão pretas", f"{accuracy.get('black', 0)}%")
    blunders = counts.get("white", {}).get("Blunder", 0) + counts.get("black", {}).get("Blunder", 0)
    cols[2].metric("Erros graves", blunders)
    cols[3].metric("Fase mais crítica", report.get("worst_phase_label") or "—")


def show_move_details(item: dict | None) -> None:
    if not item:
        st.info("Selecione um lance analisado para ver avaliação, melhor lance e explicação.")
        return

    classification = item.get("classification")
    emoji = CLASS_EMOJI.get(classification, "•")
    st.subheader(f"{emoji} {item.get('move_number')}. {item.get('played_san')} — {classification}")
    detail_cols = st.columns(3)
    loss = f"{item.get('cp_loss', 0)} cp" if item.get("cp_loss") is not None else "mate"
    detail_cols[0].metric("Perda", loss)
    detail_cols[1].metric("Melhor lance", item.get("best_move_san") or "—")
    detail_cols[2].metric("Fase", item.get("phase") or "—")

    if item.get("explanation"):
        exp = item["explanation"]
        if exp.get("human_evaluation"):
            st.info(f"Avaliação humana: {exp['human_evaluation']}")
        st.markdown("**Situação antes do lance**")
        st.write(exp.get("situation_before") or "Sem diagnóstico posicional disponível.")
        st.markdown("**Problema do lance jogado**")
        st.write(exp.get("why_it_worsens"))
        st.markdown("**O que o melhor lance resolvia**")
        st.write(exp.get("missed_idea"))

        comparison = exp.get("direct_comparison") or []
        if comparison:
            st.markdown("**Comparação direta**")
            st.table(
                [
                    {
                        "Lance jogado": row.get("played"),
                        "Melhor lance": row.get("best"),
                    }
                    for row in comparison
                ]
            )

        if exp.get("opponent_plan"):
            st.markdown("**Plano do adversário depois do erro**")
            st.write(exp["opponent_plan"])
        if exp.get("position_priorities"):
            st.markdown("**Prioridade da posição**")
            for index, priority in enumerate(exp["position_priorities"], start=1):
                st.markdown(f"{index}. {priority}")
        if exp.get("concrete_consequences"):
            st.markdown("**Consequência prática**")
            for consequence in exp["concrete_consequences"]:
                st.markdown(f"- {consequence}")
        if exp.get("priority_explanation"):
            st.caption(exp["priority_explanation"])

        if exp.get("fen_after_played") or exp.get("fen_after_best"):
            st.markdown("**Comparação visual**")
            visual_cols = st.columns(2)
            if exp.get("fen_after_played"):
                with visual_cols[0]:
                    st.caption("Após o lance jogado")
                    render_board(
                        {"board": chess.Board(exp["fen_after_played"]), "lastmove": None},
                        chess.WHITE,
                        size=260,
                    )
            if exp.get("fen_after_best"):
                with visual_cols[1]:
                    st.caption("Após o melhor lance")
                    render_board(
                        {"board": chess.Board(exp["fen_after_best"]), "lastmove": None},
                        chess.WHITE,
                        size=260,
                    )
    else:
        st.caption("Lance sem explicação crítica; use a avaliação e a PV como referência.")

    if item.get("themes"):
        st.markdown("**Temas:** " + ", ".join(f"`{theme}`" for theme in item["themes"]))
    if item.get("pv"):
        st.markdown("**Linha sugerida:** " + " ".join(item["pv"][:8]))


def show_critical_cards(report: dict, slider_key: str | None = None) -> None:
    cards = report.get("critical_cards") or []
    if not cards:
        st.success("Nenhum lance crítico encontrado no trecho analisado.")
        return
    for card in cards:
        emoji = CLASS_EMOJI.get(card.get("classification"), "•")
        label = f"{emoji} {card['title']} — {card['loss']}"
        with st.expander(label):
            st.markdown(f"**Melhor lance:** `{card.get('best_move')}`")
            st.markdown(f"**Fase:** {card.get('phase_label')}")
            if card.get("human_evaluation"):
                st.info(f"Avaliação humana: {card.get('human_evaluation')}")
            if card.get("situation_before"):
                st.markdown(f"**Situação antes:** {card.get('situation_before')}")
            st.markdown(f"**Problema:** {card.get('short_reason')}")
            st.markdown(f"**O que o melhor lance resolvia:** {card.get('coach_tip')}")
            if card.get("direct_comparison"):
                st.markdown("**Comparação direta**")
                st.table(
                    [
                        {
                            "Lance jogado": row.get("played"),
                            "Melhor lance": row.get("best"),
                        }
                        for row in card.get("direct_comparison")
                    ]
                )
            if card.get("opponent_plan"):
                st.markdown(f"**Plano do adversário:** {card.get('opponent_plan')}")
            if card.get("position_priorities"):
                st.markdown(
                    "**Prioridade da posição:** " + " → ".join(card.get("position_priorities"))
                )
            if card.get("concrete_consequences"):
                st.markdown("**Consequência prática:**")
                for consequence in card.get("concrete_consequences"):
                    st.markdown(f"- {consequence}")
            if card.get("themes"):
                st.markdown("**Temas:** " + ", ".join(card["themes"]))
            if slider_key and card.get("ply") is not None:
                jump_key = f"jump_critical_{slider_key}_{card['ply']}"
                if st.button("Ver no tabuleiro", key=jump_key):
                    st.session_state[slider_key] = int(card["ply"])
                    st.rerun()


def show_study_plan(report: dict) -> None:
    plan = report.get("study_plan") or {}
    priorities = plan.get("priorities") or []
    if priorities:
        st.markdown("### Prioridades")
        st.write(" → ".join(priorities))
    for category, suggestions in (plan.get("categories") or {}).items():
        if not suggestions:
            continue
        st.markdown(f"#### {category}")
        for suggestion in suggestions:
            st.markdown(f"- **{suggestion['theme']}**: {suggestion['short_plan']}")
            st.caption(suggestion["recommended_exercise"])


def format_player(name: str | None, rating: int | None) -> str:
    rating_text = f" <span class='rating'>({rating})</span>" if rating else ""
    return f"{escape(name or '?')}{rating_text}"


def render_player_bar(
    name: str | None,
    rating: int | None,
    clock: str,
    bottom: bool = False,
) -> None:
    avatar = "🖼️" if bottom else "♟️"
    st.markdown(
        f"""
        <div class="review-player">
          <div>{avatar} {format_player(name, rating)}</div>
          <div class="review-clock">{escape(clock)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def coach_message(item: dict | None) -> str:
    if not item:
        return "Navegue pelos lances para revisar a posição com o treinador."
    best = item.get("best_move_san") or "a melhor linha"
    label = item.get("classification") or "Lance"
    exp = item.get("explanation") or {}
    priorities = exp.get("position_priorities") or []
    if item.get("cp_loss") is not None and item["cp_loss"] > 0:
        if priorities:
            return f"{item.get('played_san')} é {label.lower()}; prioridade: {priorities[0]}. Melhor era {best}."
        return f"{item.get('played_san')} é {label.lower()}; Stockfish preferia {best}."
    return f"{item.get('played_san')} está ok. Melhor referência: {best}."


def eval_badge(item: dict | None) -> str:
    if not item or item.get("eval_after_cp") is None:
        return ""
    value = item["eval_after_cp"] / 100
    return f"{value:+.2f}"


def move_cell(item: dict | None, selected_ply: int) -> str:
    if not item:
        return ""
    emoji = CLASS_EMOJI.get(item.get("classification"), "")
    text = f"{emoji} {escape(item.get('played_san') or '')}".strip()
    css = " class='selected'" if item.get("ply") == selected_ply else ""
    return f"<td{css}>{text}</td>"


def move_table_html(analysis_by_ply: dict[int, dict], selected_ply: int) -> str:
    max_ply = max(analysis_by_ply.keys(), default=0)
    rows = []
    for move_number in range(1, (max_ply + 1) // 2 + 1):
        white_item = analysis_by_ply.get(move_number * 2 - 1)
        black_item = analysis_by_ply.get(move_number * 2)
        rows.append(
            "<tr>"
            f"<td class='num'>{move_number}.</td>"
            f"{move_cell(white_item, selected_ply)}"
            f"{move_cell(black_item, selected_ply)}"
            "</tr>"
        )
    return "<div class='move-list'><table class='move-table'>" + "".join(rows) + "</table></div>"


def eval_graph_svg(curve: list[dict], selected_ply: int) -> str:
    width, height = 420, 78
    if not curve:
        return f"<svg width='100%' viewBox='0 0 {width} {height}'></svg>"
    points = []
    for index, item in enumerate(curve):
        cp = max(-800, min(800, item.get("white_cp") or 0))
        x = 0 if len(curve) == 1 else index * (width / (len(curve) - 1))
        y = height / 2 - (cp / 800) * (height / 2 - 8)
        points.append((x, y))
    polygon = (
        f"0,{height} " + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + f" {width},{height}"
    )
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    selected_x = 0
    if curve:
        selected_index = max(0, min(selected_ply - 1, len(curve) - 1))
        selected_x = points[selected_index][0]
    dots = "".join(
        f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3' fill='#ff6f61'/>"
        for x, y in points[:: max(1, len(points) // 8)]
    )
    return f"""
    <svg width="100%" viewBox="0 0 {width} {height}" role="img">
      <rect width="{width}" height="{height}" fill="#3a3936"/>
      <line x1="0" y1="{height / 2}" x2="{width}" y2="{height / 2}" stroke="#ddd" stroke-width="1" opacity=".7"/>
      <polygon points="{polygon}" fill="#f4f4f4" opacity=".95"/>
      <polyline points="{polyline}" fill="none" stroke="#f4f4f4" stroke-width="2"/>
      {dots}
      <line x1="{selected_x:.1f}" y1="0" x2="{selected_x:.1f}" y2="{height}" stroke="#ff6f61" stroke-width="3"/>
    </svg>
    """


def clamp_ply(ply: int, max_ply: int) -> int:
    return max(0, min(max_ply, ply))


def set_target_ply(slider_key: str, ply: int, max_ply: int) -> None:
    st.session_state[slider_key] = clamp_ply(ply, max_ply)


def query_param_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def apply_keyboard_query(slider_key: str, max_ply: int) -> None:
    nav_seq = query_param_value("nav")
    ply_value = query_param_value("ply")
    if not nav_seq or nav_seq == st.session_state.get(f"{slider_key}_nav_seq"):
        return
    try:
        set_target_ply(slider_key, int(ply_value or 0), max_ply)
        st.session_state[f"{slider_key}_nav_seq"] = nav_seq
    except ValueError:
        return


def install_keyboard_navigation(selected_ply: int, max_ply: int) -> None:
    components.html(
        f"""
        <script>
        const reviewState = {{ selected: {selected_ply}, max: {max_ply} }};
        window.parent.__cgaReviewState = reviewState;
        if (!window.parent.__cgaKeyboardBound) {{
          window.parent.__cgaKeyboardBound = true;
          window.parent.document.addEventListener('keydown', (event) => {{
            const tag = (event.target && event.target.tagName || '').toLowerCase();
            if (['input', 'textarea', 'select'].includes(tag)) return;
            const state = window.parent.__cgaReviewState;
            if (!state) return;
            let next = null;
            if (event.key === 'ArrowRight' || event.key === 'l' || event.key === ' ') {{
              next = state.selected + 1;
            }} else if (event.key === 'ArrowLeft' || event.key === 'h') {{
              next = state.selected - 1;
            }} else if (event.key === 'Home') {{
              next = 0;
            }} else if (event.key === 'End') {{
              next = state.max;
            }}
            if (next === null) return;
            event.preventDefault();
            next = Math.max(0, Math.min(state.max, next));
            const url = new URL(window.parent.location.href);
            url.searchParams.set('ply', String(next));
            url.searchParams.set('nav', String(Date.now()));
            window.parent.location.href = url.toString();
          }});
        }}
        </script>
        """,
        height=0,
        width=0,
    )


def critical_note(item: dict | None) -> str | None:
    critical_classes = {"Inaccuracy", "Mistake", "Blunder", "Missed Win"}
    if not item or item.get("classification") not in critical_classes:
        return None
    best = item.get("best_move_san") or "—"
    loss = item.get("cp_loss")
    loss_text = f"{loss} cp" if loss is not None else "mate"
    return f"{CLASS_EMOJI.get(item.get('classification'), '⚠️')} Melhor: {best} · perda {loss_text}"


def move_button_label(item: dict | None) -> str:
    if not item:
        return ""
    emoji = CLASS_EMOJI.get(item.get("classification"), "")
    return f"{emoji} {item.get('played_san') or ''}".strip()


def render_move_button(
    item: dict | None,
    selected_ply: int,
    slider_key: str,
    max_ply: int,
    key_prefix: str,
) -> None:
    if not item:
        st.write("")
        return
    is_selected = item.get("ply") == selected_ply
    button_type = "primary" if is_selected else "secondary"
    if st.button(move_button_label(item), key=f"{key_prefix}_{item['ply']}", type=button_type):
        set_target_ply(slider_key, int(item["ply"]), max_ply)
        st.rerun()


def render_move_list(
    analysis_by_ply: dict[int, dict],
    selected_ply: int,
    slider_key: str,
    max_ply: int,
) -> None:
    max_analyzed_ply = max(analysis_by_ply.keys(), default=0)
    with st.container(height=330):
        for move_number in range(1, (max_analyzed_ply + 1) // 2 + 1):
            white_item = analysis_by_ply.get(move_number * 2 - 1)
            black_item = analysis_by_ply.get(move_number * 2)
            cols = st.columns([0.16, 0.42, 0.42])
            cols[0].markdown(f"<div class='move-num'>{move_number}.</div>", unsafe_allow_html=True)
            with cols[1]:
                render_move_button(white_item, selected_ply, slider_key, max_ply, "white_move")
            with cols[2]:
                render_move_button(black_item, selected_ply, slider_key, max_ply, "black_move")
            for item in (white_item, black_item):
                note = critical_note(item)
                if note:
                    st.markdown(
                        f"<div class='critical-inline'>{escape(note)}</div>",
                        unsafe_allow_html=True,
                    )


def render_review_panel(
    report: dict,
    analysis_by_ply: dict[int, dict],
    selected_item: dict | None,
    selected_ply: int,
    slider_key: str,
    max_ply: int,
) -> None:
    st.markdown("<div class='review-panel'>", unsafe_allow_html=True)
    st.markdown("<div class='review-header'>⭐ Revisão da Partida 🔍</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="coach-row">
          <div class="coach-avatar">👨‍🏫</div>
          <div class="coach-bubble">
            {CLASS_EMOJI.get(selected_item.get("classification") if selected_item else "", "💡")}
            {escape(coach_message(selected_item))}
            <span style="float:right;background:#eee;padding:2px 8px;border-radius:3px;">
              {eval_badge(selected_item)}
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_cols = st.columns(3)
    best_clicked = action_cols[0].button("⭐ Melhor", key=f"best_{slider_key}")
    explain_clicked = action_cols[1].button("💡 Explicar", key=f"explain_{slider_key}")
    if action_cols[2].button("➜ Próximo", key=f"next_action_{slider_key}", type="primary"):
        set_target_ply(slider_key, selected_ply + 1, max_ply)
        st.rerun()

    if best_clicked and selected_item:
        best = selected_item.get("best_move_san") or "—"
        best_line = " ".join(selected_item.get("pv") or []) or "Linha não disponível."
        st.success(f"Melhor lance: {best}. Linha: {best_line}")
    selected_note = critical_note(selected_item)
    if selected_note:
        st.warning(selected_note)
    if explain_clicked:
        show_move_details(selected_item)

    st.markdown("#### Lances e críticos")
    render_move_list(analysis_by_ply, selected_ply, slider_key, max_ply)
    graph = eval_graph_svg(report.get("evaluation_curve") or [], selected_ply)
    st.markdown(f"<div class='eval-wrap'>{graph}</div>", unsafe_allow_html=True)

    control_cols = st.columns(5)
    controls = [
        ("⏮", 0),
        ("‹", selected_ply - 1),
        ("▶", selected_ply + 1),
        ("›", selected_ply + 1),
        ("⏭", max_ply),
    ]
    for index, (label, target) in enumerate(controls):
        if control_cols[index].button(label, key=f"nav_{index}_{slider_key}"):
            set_target_ply(slider_key, target, max_ply)
            st.rerun()
    st.caption("Atalhos: ←/→ para voltar/avançar, Home/End para início/fim.")
    st.markdown("</div>", unsafe_allow_html=True)


def show_game(game_id: int) -> None:
    game = api_get(f"/games/{game_id}")
    report = game.get("report") or {}
    pgn = game.get("pgn") or ""

    positions = positions_from_pgn(pgn)
    analysis_by_ply = move_analysis_by_ply(game)
    if not positions:
        st.warning("Não foi possível recriar o tabuleiro porque o PGN não está disponível.")
        return

    slider_key = f"target_ply_{game_id}"
    max_ply = len(positions) - 1
    labels = [position["label"] for position in positions]
    if slider_key not in st.session_state:
        st.session_state[slider_key] = max_ply
    apply_keyboard_query(slider_key, max_ply)
    selected = st.slider(
        "Navegue lance a lance",
        0,
        max_ply,
        value=st.session_state[slider_key],
        format="%d",
        label_visibility="collapsed",
    )
    st.session_state[slider_key] = selected
    install_keyboard_navigation(selected, max_ply)
    selected_item = analysis_by_ply.get(positions[selected]["ply"])
    board_position = board_position_for_selection(positions, selected_item, selected)

    board_col, panel_col = st.columns([1.55, 1], gap="large")
    with board_col:
        render_player_bar(game.get("black"), game.get("black_rating"), "9:35")
        st.caption(f"{labels[selected]} · vermelho = lance jogado · verde = melhor opção Stockfish")
        board_wrap = st.columns([0.04, 0.96], gap="small")
        with board_wrap[0]:
            current_eval = selected_item.get("eval_after_cp") if selected_item else None
            eval_text = eval_badge(selected_item) or "0.0"
            fill_pct = 50 if current_eval is None else max(5, min(95, 50 + current_eval / 20))
            st.markdown(
                f"""
                <div style="height:720px;background:#111;border-radius:3px;position:relative;">
                  <div style="position:absolute;bottom:0;width:100%;height:{fill_pct}%;background:#f5f5f5;"></div>
                  <div style="position:absolute;top:6px;left:2px;font-size:.75rem;color:#ddd;">
                    {eval_text}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with board_wrap[1]:
            render_board(board_position, chess.WHITE, best_move_arrows(selected_item), size=720)
        render_player_bar(game.get("white"), game.get("white_rating"), "9:15", bottom=True)

    with panel_col:
        render_review_panel(report, analysis_by_ply, selected_item, selected, slider_key, max_ply)
        with st.expander("🎯 Plano de estudo"):
            show_study_plan(report)
        with st.expander("📄 PGN / JSON"):
            st.download_button("Baixar PGN", pgn, file_name=f"game_{game_id}.pgn")
            st.text_area("PGN", pgn, height=180)
            st.json(game)


with st.sidebar:
    st.header("Analisar")
    mode = st.radio("Origem", ["PGN", "Chess.com", "Abrir game_id"])
    max_moves = DEFAULT_MAX_MOVES
    st.caption(f"Stockfish analisará até {max_moves} meios-lances por partida.")

try:
    if mode == "PGN":
        pgn = st.text_area("Cole o PGN", height=260)
        if st.button("Analisar PGN", type="primary") and pgn.strip():
            with st.spinner("Analisando com Stockfish..."):
                data = api_post("/analyze/pgn", {"pgn": pgn, "max_moves": max_moves})
            st.session_state["game_id"] = data["game_id"]
            st.success(f"Análise criada: game_id={data['game_id']}")

    elif mode == "Chess.com":
        username = st.text_input("Username Chess.com")
        if st.button("Buscar partidas", type="primary") and username:
            with st.spinner("Buscando partidas públicas no Chess.com..."):
                data = api_get(f"/players/{username}/chesscom-public-games?limit=20")
            st.session_state["chesscom_username"] = username
            st.session_state["chesscom_games"] = data.get("games") or []

        stored_games = st.session_state.get("chesscom_games") or []
        stored_username = st.session_state.get("chesscom_username") or username
        if stored_games:
            show_chesscom_games_panel(stored_username, stored_games, max_moves)
        elif username:
            st.info(
                "Clique em **Buscar partidas** para listar partidas públicas antes de analisar."
            )

    else:
        game_id_input = st.number_input("game_id", 1, step=1)
        if st.button("Abrir partida"):
            st.session_state["game_id"] = int(game_id_input)

    if st.session_state.get("game_id"):
        show_game(int(st.session_state["game_id"]))
    else:
        st.info("Comece colando um PGN, importando do Chess.com ou abrindo um game_id já salvo.")
except requests.HTTPError as exc:
    st.error(f"Erro da API: {exc.response.text}")
except requests.RequestException as exc:
    st.error(f"Não foi possível conectar à API em {API_URL}: {exc}")
