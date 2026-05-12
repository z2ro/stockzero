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


def render_board(position: dict, orientation: chess.Color = chess.WHITE) -> None:
    svg = chess.svg.board(
        board=position["board"],
        lastmove=position.get("lastmove"),
        orientation=orientation,
        size=430,
    )
    components.html(svg, height=450)


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
    st.subheader(
        f"{emoji} {item.get('move_number')}. {item.get('played_san')} — {classification}"
    )
    detail_cols = st.columns(3)
    loss = f"{item.get('cp_loss', 0)} cp" if item.get("cp_loss") is not None else "mate"
    detail_cols[0].metric("Perda", loss)
    detail_cols[1].metric("Melhor lance", item.get("best_move_san") or "—")
    detail_cols[2].metric("Fase", item.get("phase") or "—")

    if item.get("explanation"):
        exp = item["explanation"]
        st.markdown(f"**Por que piorou:** {exp.get('why_it_worsens')}")
        st.markdown(f"**Ideia perdida:** {exp.get('missed_idea')}")
    else:
        st.caption("Lance sem explicação crítica; use a avaliação e a PV como referência.")

    if item.get("themes"):
        st.markdown("**Temas:** " + ", ".join(f"`{theme}`" for theme in item["themes"]))
    if item.get("pv"):
        st.markdown("**Linha sugerida:** " + " ".join(item["pv"][:8]))


def show_critical_cards(report: dict) -> None:
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
            st.markdown(f"**Resumo:** {card.get('short_reason')}")
            st.markdown(f"**Dica de estudo:** {card.get('coach_tip')}")
            if card.get("themes"):
                st.markdown("**Temas:** " + ", ".join(card["themes"]))


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


def show_game(game_id: int) -> None:
    game = api_get(f"/games/{game_id}")
    report = game.get("report") or {}
    pgn = game.get("pgn") or ""

    st.divider()
    white = game.get("white") or "Brancas"
    black = game.get("black") or "Pretas"
    st.header(f"Partida #{game_id}: {white} vs {black}")
    opening = game.get("opening") or "desconhecida"
    result = game.get("result") or "—"
    st.caption(f"Abertura: {opening} · Resultado: {result}")
    show_metrics(report)
    st.info(report.get("natural_summary") or "Relatório gerado.")

    positions = positions_from_pgn(pgn)
    analysis_by_ply = move_analysis_by_ply(game)
    tab_board, tab_critical, tab_study, tab_raw = st.tabs(
        ["🧩 Tabuleiro", "🚨 Lances críticos", "🎯 Plano de estudo", "📄 PGN/JSON"]
    )

    with tab_board:
        if not positions:
            st.warning("Não foi possível recriar o tabuleiro porque o PGN não está disponível.")
        else:
            left, right = st.columns([1, 1])
            with left:
                labels = [position["label"] for position in positions]
                selected = st.slider(
                    "Navegue lance a lance",
                    0,
                    len(positions) - 1,
                    len(positions) - 1,
                    format="%d",
                )
                st.caption(labels[selected])
                orientation_name = st.radio("Orientação", ["Brancas", "Pretas"], horizontal=True)
                orientation = chess.WHITE if orientation_name == "Brancas" else chess.BLACK
                render_board(positions[selected], orientation)
            with right:
                show_move_details(analysis_by_ply.get(positions[selected]["ply"]))

    with tab_critical:
        show_critical_cards(report)

    with tab_study:
        show_study_plan(report)

    with tab_raw:
        st.download_button("Baixar PGN", pgn, file_name=f"game_{game_id}.pgn")
        st.text_area("PGN", pgn, height=240)
        with st.expander("JSON completo"):
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
        st.info(
            "Comece colando um PGN, importando do Chess.com ou abrindo um game_id já salvo."
        )
except requests.HTTPError as exc:
    st.error(f"Erro da API: {exc.response.text}")
except requests.RequestException as exc:
    st.error(f"Não foi possível conectar à API em {API_URL}: {exc}")
