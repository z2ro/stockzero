import os

import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
API_URL = st.sidebar.text_input("API URL", DEFAULT_API_URL)
st.title("Chess Game Analyzer")
st.caption("Cole um PGN ou importe partidas públicas do Chess.com.")

mode = st.radio("Modo", ["PGN", "Chess.com"])
max_moves = st.number_input("Máximo de lances analisados (útil para testes rápidos)", 1, 300, 20)


def show_response(response: requests.Response) -> None:
    if response.ok:
        data = response.json()
        st.success(f"Análise criada: game_id={data.get('game_id') or 'vários'}")
        st.json(data)
    else:
        st.error(response.text)


if mode == "PGN":
    pgn = st.text_area("PGN", height=280)
    if st.button("Analisar PGN") and pgn.strip():
        show_response(
            requests.post(
                f"{API_URL}/analyze/pgn",
                json={"pgn": pgn, "max_moves": max_moves},
                timeout=300,
            )
        )
else:
    username = st.text_input("Username Chess.com")
    col1, col2 = st.columns(2)
    year = col1.number_input("Ano", 2007, 2100, 2026)
    month = col2.number_input("Mês", 1, 12, 1)
    color = st.selectbox("Cor", [None, "white", "black"])
    if st.button("Importar e analisar") and username:
        payload = {
            "username": username,
            "year": year,
            "month": month,
            "color": color,
            "limit": 1,
            "max_moves": max_moves,
        }
        show_response(
            requests.post(f"{API_URL}/analyze/chesscom", json=payload, timeout=600)
        )
