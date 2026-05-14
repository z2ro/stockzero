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


def inject_review_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #0f172a;
            --bg-soft: #111827;
            --panel: rgba(30, 41, 59, 0.88);
            --panel-strong: rgba(15, 23, 42, 0.96);
            --border: rgba(148, 163, 184, 0.18);
            --text: #e5e7eb;
            --muted: #94a3b8;
            --green: #22c55e;
            --yellow: #f59e0b;
            --red: #ef4444;
            --blue: #38bdf8;
            --radius: 22px;
        }
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
              radial-gradient(circle at top left, rgba(34,197,94,.10), transparent 32rem),
              radial-gradient(circle at top right, rgba(56,189,248,.12), transparent 34rem),
              linear-gradient(135deg, #0f172a 0%, #111827 48%, #18181b 100%);
            color: var(--text);
        }
        div[data-testid="stHeader"], header[data-testid="stHeader"] {
            height: 0 !important;
            min-height: 0 !important;
            background: transparent !important;
            visibility: hidden;
        }
        div[data-testid="stToolbar"], div[data-testid="stDecoration"], #MainMenu, footer {
            display: none !important;
        }
        section[data-testid="stSidebar"] {
            background: rgba(2, 6, 23, .82);
            border-right: 1px solid var(--border);
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 4rem;
            max-width: 1440px;
        }
        .main .block-container { padding-left: 2rem; padding-right: 2rem; }
        h1, h2, h3 { letter-spacing: -0.03em; }
        p, li, div { line-height: 1.58; }
        div.stButton > button {
            border: 1px solid rgba(148,163,184,.18);
            border-radius: 14px;
            min-height: 44px;
            width: 100%;
            color: #e5e7eb;
            background: linear-gradient(180deg, rgba(51,65,85,.95), rgba(30,41,59,.95));
            box-shadow: 0 12px 28px rgba(2,6,23,.18);
            font-weight: 800;
            transition: all .18s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(56,189,248,.45);
            box-shadow: 0 18px 36px rgba(2,6,23,.28);
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #16a34a, #22c55e);
            color: #052e16;
            border: 0;
        }
        .app-shell { padding-top: 1.15rem; }
        .hero {
            border: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(15,23,42,.92), rgba(30,41,59,.74));
            border-radius: 30px;
            padding: 30px 34px;
            margin: 0 0 26px;
            box-shadow: 0 28px 80px rgba(2,6,23,.34);
        }
        .eyebrow {
            color: #86efac;
            text-transform: uppercase;
            letter-spacing: .14em;
            font-size: .78rem;
            font-weight: 900;
            margin-bottom: 8px;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2.25rem, 5vw, 4.2rem);
            line-height: .96;
        }
        .hero p {
            max-width: 820px;
            color: #cbd5e1;
            font-size: 1.08rem;
            margin: 18px 0 0;
        }
        .top-nav {
            display:flex; gap:10px; align-items:center; justify-content:space-between;
            margin: 12px 0 22px;
        }
        .pill {
            display:inline-flex; align-items:center; gap:8px; padding:8px 12px;
            border-radius:999px; background:rgba(15,23,42,.74);
            border:1px solid var(--border); color:#cbd5e1; font-size:.88rem; font-weight:800;
        }
        .section-title {
            display:flex; align-items:flex-end; justify-content:space-between; gap:1rem;
            margin: 26px 0 16px;
        }
        .section-title h2 { margin:0; font-size:1.75rem; }
        .section-title p { margin:0; color:var(--muted); }
        .glass-card, .game-card, .analysis-card, .study-card {
            border: 1px solid var(--border);
            background: linear-gradient(180deg, rgba(30,41,59,.86), rgba(15,23,42,.82));
            border-radius: var(--radius);
            box-shadow: 0 18px 45px rgba(2,6,23,.25);
        }
        .game-card {
            padding: 18px 20px;
            margin: 10px 0 14px;
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
        }
        .game-card:hover {
            transform: translateY(-2px);
            border-color: rgba(34,197,94,.44);
            box-shadow: 0 24px 56px rgba(2,6,23,.38);
        }
        .players { font-weight:900; font-size:1.06rem; }
        .player-line { display:flex; justify-content:space-between; gap:12px; margin:4px 0; }
        .rating, .muted { color: var(--muted); font-weight: 600; }
        .meta-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:10px; margin-top:14px; }
        .meta-item {
            border:1px solid rgba(148,163,184,.12); border-radius:14px;
            padding:9px 10px; background:rgba(15,23,42,.56);
        }
        .meta-label { color:var(--muted); font-size:.75rem; text-transform:uppercase; font-weight:900; letter-spacing:.08em; }
        .meta-value { color:#f8fafc; font-weight:900; font-size:.96rem; }
        .analysis-header {
            border:1px solid var(--border); border-radius:28px;
            background:linear-gradient(135deg, rgba(15,23,42,.94), rgba(30,41,59,.78));
            padding:22px 24px; margin: 6px 0 24px;
            box-shadow:0 22px 70px rgba(2,6,23,.3);
        }
        .match-title { font-size: clamp(1.6rem, 3vw, 2.6rem); font-weight:950; margin:0; }
        .stat-row { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; margin-top:18px; }
        .stat-card {
            padding:13px 14px; border-radius:18px; background:rgba(15,23,42,.62);
            border:1px solid rgba(148,163,184,.12);
        }
        .stat-card small { color:var(--muted); text-transform:uppercase; letter-spacing:.08em; font-weight:900; }
        .stat-card strong { display:block; font-size:1.16rem; margin-top:4px; }
        .board-shell {
            border:1px solid var(--border); border-radius:28px; padding:18px;
            background:linear-gradient(180deg, rgba(30,41,59,.88), rgba(15,23,42,.92));
            box-shadow: 0 28px 70px rgba(2,6,23,.36);
        }
        .board-caption { color:#cbd5e1; margin: 6px 0 12px; font-weight:700; }
        .review-player {
            background: rgba(15,23,42,.72); border: 1px solid rgba(148,163,184,.14);
            border-radius: 16px; padding: 10px 14px;
            display: flex; align-items: center; justify-content: space-between;
            margin: 8px 0; color: #f8fafc; font-weight: 850;
        }
        .review-player .rating { color: #94a3b8; font-weight: 650; }
        .review-clock {
            background: rgba(248,250,252,.92); color: #0f172a; border-radius: 12px;
            padding: 6px 14px; font-size: 1.05rem; font-weight: 950;
        }
        .review-panel {
            background: linear-gradient(180deg, rgba(30,41,59,.92), rgba(15,23,42,.96));
            border-radius: 28px; border: 1px solid var(--border);
            padding: 18px; box-shadow: 0 24px 64px rgba(2,6,23,.33);
        }
        .review-header {
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid rgba(148,163,184,.16);
            padding-bottom: 12px; margin-bottom: 14px;
            font-size: 1.18rem; font-weight: 950;
        }
        .coach-row { display: flex; gap: 14px; align-items: flex-start; margin: 16px 0; }
        .coach-avatar { font-size: 2.5rem; line-height: 1; }
        .coach-bubble {
            background: rgba(15,23,42,.74); color: #e2e8f0; border:1px solid rgba(148,163,184,.14);
            border-radius: 20px; padding: 16px 18px; font-weight: 750; flex: 1; min-height: 70px;
        }
        .analysis-card { padding: 16px; margin: 12px 0; }
        .detail-grid { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:12px; margin:12px 0; }
        .detail-card {
            border:1px solid rgba(148,163,184,.12); border-radius:18px; padding:14px;
            background:rgba(15,23,42,.58);
        }
        .detail-card h4 { margin:0 0 6px; font-size:.92rem; color:#bfdbfe; }
        .detail-card p { margin:0; color:#e5e7eb; }
        .move-num { color: #94a3b8; text-align: right; padding-right: 6px; font-weight: 800; }
        .critical-inline {
            background: rgba(245,158,11,.10); border-left: 3px solid #f59e0b; border-radius: 12px;
            padding: 8px 10px; margin: 6px 0 8px 44px; font-size: .88rem; color:#fde68a;
        }
        .eval-wrap { background: rgba(15,23,42,.66); border-radius: 16px; padding: 8px; margin-top: 16px; border:1px solid rgba(148,163,184,.10); }
        .study-card { padding: 22px; margin: 16px 0; }
        .study-card h3 { margin-top:0; }
        .pattern-badge {
            display:inline-flex; align-items:center; gap:8px; border-radius:999px;
            padding:7px 11px; margin:4px 6px 4px 0;
            border:1px solid rgba(148,163,184,.16); background:rgba(15,23,42,.64);
            color:#cbd5e1; font-weight:800; font-size:.86rem;
        }
        .skeleton {
            height: 124px; border-radius: 22px; margin: 12px 0;
            background: linear-gradient(90deg, rgba(30,41,59,.7), rgba(51,65,85,.9), rgba(30,41,59,.7));
            background-size: 240% 100%; animation: shimmer 1.4s infinite;
            border:1px solid rgba(148,163,184,.12);
        }
        @keyframes shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
        @media (max-width: 900px) {
            .main .block-container { padding-left: 1rem; padding-right: 1rem; }
            .hero { padding: 22px; border-radius: 24px; }
            .meta-grid, .stat-row, .detail-grid { grid-template-columns: 1fr; }
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


def set_app_page(page: str, game_id: int | None = None) -> None:
    st.session_state["app_page"] = page
    if game_id is not None:
        st.session_state["game_id"] = int(game_id)
    params = {"page": page}
    if game_id is not None:
        params["game_id"] = str(game_id)
    st.query_params.clear()
    st.query_params.update(params)


def current_page() -> str:
    query_page = st.query_params.get("page")
    if query_page in {"games", "analysis"}:
        st.session_state["app_page"] = query_page
    if st.query_params.get("game_id"):
        try:
            st.session_state["game_id"] = int(st.query_params["game_id"])
            st.session_state["app_page"] = "analysis"
        except ValueError:
            pass
    return st.session_state.get("app_page", "games")


def render_hero(title: str, subtitle: str, eyebrow: str = "Chess Game Analyzer") -> None:
    st.markdown(
        f"""
        <div class="app-shell">
          <div class="hero">
            <div class="eyebrow">{escape(eyebrow)}</div>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-title">
          <div>
            <h2>{escape(title)}</h2>
            <p>{escape(subtitle)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_skeleton_cards(count: int = 3) -> None:
    for _ in range(count):
        st.markdown('<div class="skeleton"></div>', unsafe_allow_html=True)


def game_card_html(game: dict, username: str) -> str:
    white = game.get("white", {})
    black = game.get("black", {})
    marker_white = "•" if game.get("user_color") == "white" else ""
    marker_black = "•" if game.get("user_color") == "black" else ""
    plies = count_pgn_plies(game.get("pgn"))
    return f"""
    <div class="game-card">
      <div class="players">
        <div class="player-line"><span>♙ {escape(marker_white)} {escape(player_text(white))}</span><span class="muted">Brancas</span></div>
        <div class="player-line"><span>♟ {escape(marker_black)} {escape(player_text(black))}</span><span class="muted">Pretas</span></div>
      </div>
      <div class="meta-grid">
        <div class="meta-item"><div class="meta-label">Resultado</div><div class="meta-value">{escape(str(game.get("result") or "?"))}</div></div>
        <div class="meta-item"><div class="meta-label">Ritmo</div><div class="meta-value">{escape(str(game.get("time_class") or game.get("time_control") or "—"))}</div></div>
        <div class="meta-item"><div class="meta-label">Lances</div><div class="meta-value">{plies}</div></div>
        <div class="meta-item"><div class="meta-label">Data</div><div class="meta-value">{escape(str(game.get("played_at") or "—"))}</div></div>
      </div>
    </div>
    """


def show_chesscom_games_panel(username: str, games: list[dict], max_moves: int) -> None:
    section_title(
        "Histórico de partidas",
        "Escolha uma partida para abrir uma análise dedicada, sem empurrar o relatório para baixo da lista.",
    )
    if not games:
        st.markdown(
            """
            <div class="study-card">
              <h3>Nenhuma partida encontrada</h3>
              <p class="muted">Não encontramos partidas públicas com PGN para esse usuário. Tente outro username ou cole um PGN manualmente.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for index, game in enumerate(games):
        cols = st.columns([0.78, 0.22], gap="medium")
        with cols[0]:
            st.markdown(game_card_html(game, username), unsafe_allow_html=True)
        with cols[1]:
            st.write("")
            st.write("")
            if st.button("Analisar", key=f"analyze_chesscom_{index}", type="primary"):
                payload = {
                    "username": username,
                    "pgn": game["pgn"],
                    "url": game.get("url"),
                    "max_moves": max_moves,
                }
                placeholder = st.empty()
                with placeholder.container():
                    render_skeleton_cards(1)
                    st.caption("Stockfish está analisando a partida selecionada…")
                data = api_post("/analyze/chesscom/game", payload, timeout=900)
                set_app_page("analysis", data["game_id"])
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


def _show_player_coaching(title: str, summary: dict) -> None:
    st.markdown(f"### {title}")
    st.markdown(f"**Jogador:** {summary.get('player') or '—'}")
    st.markdown(f"**Principal problema:** {summary.get('main_weakness') or '—'}")
    st.markdown(f"**Sugestão prática:** {summary.get('practical_suggestion') or '—'}")
    st.markdown(f"**Fase mais crítica:** {summary.get('worst_phase_label') or '—'}")
    if summary.get("strengths"):
        st.markdown("**O que jogou bem**")
        for strength in summary["strengths"]:
            st.markdown(f"- {strength}")
    if summary.get("weaknesses"):
        st.markdown("**O que poderia melhorar**")
        for weakness in summary["weaknesses"]:
            st.markdown(f"- {weakness}")


def show_study_plan(report: dict) -> None:
    plan = report.get("study_plan") or {}
    coaching = report.get("coaching_summary") or {}
    summaries = report.get("player_summaries") or {}
    critical = report.get("critical_moments") or []

    st.markdown("### Resumo da partida")
    st.write(coaching.get("game_summary") or plan.get("summary") or "—")
    if coaching.get("headline"):
        st.info(coaching["headline"])
    if coaching.get("main_lesson"):
        st.markdown(f"**Principal lição da partida:** {coaching['main_lesson']}")

    cols = st.columns(2)
    with cols[0]:
        _show_player_coaching(
            "O que as brancas poderiam ter jogado melhor", summaries.get("white") or {}
        )
    with cols[1]:
        _show_player_coaching(
            "O que as pretas poderiam ter jogado melhor", summaries.get("black") or {}
        )

    st.markdown("### Momentos críticos")
    if critical:
        for moment in critical[:5]:
            with st.expander(f"{moment.get('move_ref')} — melhor: {moment.get('best_move')}"):
                st.markdown(f"**O que tentou:** {moment.get('what_player_tried')}")
                st.markdown(f"**Problema:** {moment.get('problem')}")
                st.markdown(
                    f"**Por que o melhor lance era melhor:** {moment.get('why_best_was_better')}"
                )
                st.markdown(
                    f"**Prioridade da posição:** {', '.join(moment.get('position_priority') or [])}"
                )
                st.markdown(f"**Consequência prática:** {moment.get('practical_consequence')}")
                st.markdown(f"**Tema de estudo:** {moment.get('study_theme')}")
    else:
        st.caption("Nenhum momento crítico suficiente para diagnóstico.")

    st.markdown("### Plano de estudo personalizado")
    for priority in plan.get("priorities") or []:
        st.markdown(f"#### {priority.get('priority')}. {priority.get('theme')}")
        st.write(priority.get("why_it_matters"))
        if priority.get("examples_from_game"):
            st.markdown("**Exemplos da partida**")
            for example in priority["examples_from_game"]:
                st.markdown(f"- {example}")
        if priority.get("how_to_train"):
            st.markdown("**Como treinar**")
            for exercise in priority["how_to_train"]:
                st.markdown(f"- {exercise}")
        st.caption(
            f"Exercício diário: {priority.get('daily_exercise')} · {priority.get('recommended_time')}"
        )

    st.markdown("### Plano por área")
    for area, data in (plan.get("areas") or {}).items():
        with st.expander(data.get("label") or area):
            st.write(data.get("diagnosis"))
            themes = data.get("themes") or []
            if themes:
                st.markdown("**Temas:** " + ", ".join(themes))
            else:
                st.caption("Sem temas recorrentes nesta área.")

    st.markdown("### Exercícios recomendados")
    for exercise in plan.get("recommended_exercises") or []:
        st.markdown(f"- {exercise}")


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


def render_analysis_header(game: dict, report: dict) -> None:
    accuracy = report.get("accuracy", {})
    white = f"{game.get('white') or 'Brancas'}" + (
        f" ({game.get('white_rating')})" if game.get("white_rating") else ""
    )
    black = f"{game.get('black') or 'Pretas'}" + (
        f" ({game.get('black_rating')})" if game.get("black_rating") else ""
    )
    st.markdown(
        f"""
        <div class="analysis-header">
          <div class="eyebrow">Análise dedicada · game_id {game.get("id")}</div>
          <h1 class="match-title">{escape(white)} vs {escape(black)}</h1>
          <p class="muted">{escape(str(game.get("opening") or "Abertura desconhecida"))} · {escape(str(game.get("result") or "Resultado não informado"))}</p>
          <div class="stat-row">
            <div class="stat-card"><small>Precisão brancas</small><strong>{accuracy.get("white", 0)}%</strong></div>
            <div class="stat-card"><small>Precisão pretas</small><strong>{accuracy.get("black", 0)}%</strong></div>
            <div class="stat-card"><small>Data</small><strong>{escape(str(game.get("played_at") or "—"))}</strong></div>
            <div class="stat-card"><small>Tempo</small><strong>{escape(str(game.get("time_control") or "—"))}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_explanation_cards(item: dict | None) -> None:
    if not item or not item.get("explanation"):
        return
    exp = item["explanation"]
    cards = [
        ("Problema do lance", exp.get("why_it_worsens")),
        ("Prioridade da posição", ", ".join(exp.get("position_priorities") or [])),
        ("Consequência prática", "; ".join(exp.get("concrete_consequences") or [])),
        ("Plano correto", exp.get("missed_idea")),
    ]
    html = '<div class="detail-grid">'
    for title, text in cards:
        if text:
            html += (
                f'<div class="detail-card"><h4>{escape(title)}</h4><p>{escape(str(text))}</p></div>'
            )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def show_game(game_id: int) -> None:
    game = api_get(f"/games/{game_id}")
    report = game.get("report") or {}
    pgn = game.get("pgn") or ""

    if st.button("← Voltar para partidas", key=f"back_to_games_{game_id}"):
        set_app_page("games")
        st.rerun()

    render_analysis_header(game, report)

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

    analysis_tab, coaching_tab, data_tab = st.tabs(["♟️ Análise", "🎯 Coaching report", "📄 Dados"])

    with analysis_tab:
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

        board_col, panel_col = st.columns([1.35, 0.9], gap="large")
        with board_col:
            st.markdown('<div class="board-shell">', unsafe_allow_html=True)
            render_player_bar(game.get("black"), game.get("black_rating"), "--:--")
            st.markdown(
                f'<div class="board-caption">{escape(labels[selected])} · vermelho = lance jogado · verde = melhor opção Stockfish</div>',
                unsafe_allow_html=True,
            )
            board_wrap = st.columns([0.045, 0.955], gap="small")
            with board_wrap[0]:
                current_eval = selected_item.get("eval_after_cp") if selected_item else None
                eval_text = eval_badge(selected_item) or "0.0"
                fill_pct = 50 if current_eval is None else max(5, min(95, 50 + current_eval / 20))
                st.markdown(
                    f"""
                    <div style="height:min(72vh,720px);background:#020617;border-radius:14px;position:relative;border:1px solid rgba(148,163,184,.14);overflow:hidden;">
                      <div style="position:absolute;bottom:0;width:100%;height:{fill_pct}%;background:#f8fafc;"></div>
                      <div style="position:absolute;top:8px;left:3px;font-size:.72rem;color:#94a3b8;font-weight:900;">
                        {eval_text}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with board_wrap[1]:
                render_board(board_position, chess.WHITE, best_move_arrows(selected_item), size=720)
            render_player_bar(game.get("white"), game.get("white_rating"), "--:--", bottom=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with panel_col:
            render_review_panel(
                report, analysis_by_ply, selected_item, selected, slider_key, max_ply
            )
            render_explanation_cards(selected_item)

    with coaching_tab:
        show_study_plan(report)

    with data_tab:
        st.download_button("Baixar PGN", pgn, file_name=f"game_{game_id}.pgn")
        st.text_area("PGN", pgn, height=260)
        st.json(game)


with st.sidebar:
    st.markdown("### ♟️ Chess Game Analyzer")
    page_choice = st.radio(
        "Navegação",
        ["games", "analysis"],
        format_func=lambda value: "Histórico / Importar" if value == "games" else "Análise atual",
        index=0 if current_page() == "games" else 1,
    )
    if page_choice != current_page():
        set_app_page(page_choice)
        st.rerun()
    max_moves = DEFAULT_MAX_MOVES
    st.caption(f"Stockfish analisará até {max_moves} meios-lances por partida.")


def show_games_page(max_moves: int) -> None:
    render_hero(
        "Análise de xadrez com coaching pós-partida",
        "Importe PGNs ou partidas públicas do Chess.com e abra cada análise em uma página dedicada, com tabuleiro grande, explicações humanas e plano de estudo premium.",
    )

    source_tab, chesscom_tab, open_tab = st.tabs(
        ["📋 Colar PGN", "🌐 Chess.com", "#️⃣ Abrir game_id"]
    )

    with source_tab:
        section_title("Analisar PGN", "Cole uma partida e abra a análise em uma página própria.")
        pgn = st.text_area("PGN", height=260, placeholder='[Event "Casual"]\n\n1. e4 e5 2. Nf3 *')
        if st.button("Analisar PGN", type="primary") and pgn.strip():
            placeholder = st.empty()
            with placeholder.container():
                render_skeleton_cards(2)
                st.caption("Criando análise dedicada…")
            data = api_post("/analyze/pgn", {"pgn": pgn, "max_moves": max_moves})
            set_app_page("analysis", data["game_id"])
            st.rerun()

    with chesscom_tab:
        section_title(
            "Buscar partidas Chess.com",
            "A lista fica limpa; ao analisar, você navega para a página da partida.",
        )
        username = st.text_input(
            "Username Chess.com", value=st.session_state.get("chesscom_username", "")
        )
        if st.button("Buscar partidas", type="primary") and username:
            placeholder = st.empty()
            with placeholder.container():
                render_skeleton_cards(3)
            data = api_get(f"/players/{username}/chesscom-public-games?limit=20")
            st.session_state["chesscom_username"] = username
            st.session_state["chesscom_games"] = data.get("games") or []
            placeholder.empty()

        stored_games = st.session_state.get("chesscom_games") or []
        stored_username = st.session_state.get("chesscom_username") or username
        if stored_games:
            show_chesscom_games_panel(stored_username, stored_games, max_moves)
        elif username:
            st.markdown(
                """
                <div class="study-card">
                  <h3>Pronto para buscar</h3>
                  <p class="muted">Clique em buscar para carregar cards modernos com partidas públicas.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with open_tab:
        section_title(
            "Abrir análise existente",
            "Use um game_id salvo para ir diretamente à página de análise.",
        )
        game_id_input = st.number_input("game_id", 1, step=1)
        if st.button("Abrir análise", type="primary"):
            set_app_page("analysis", int(game_id_input))
            st.rerun()


try:
    page = current_page()
    if page == "analysis" and st.session_state.get("game_id"):
        show_game(int(st.session_state["game_id"]))
    else:
        show_games_page(max_moves)
except requests.HTTPError as exc:
    st.error(f"Erro da API: {exc.response.text}")
except requests.RequestException as exc:
    st.error(f"Não foi possível conectar à API em {API_URL}: {exc}")
