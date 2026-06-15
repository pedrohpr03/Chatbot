from flask import Flask, request, jsonify, render_template, session
import os
import uuid
import random
import logging

from src import spotify_client as spotify
from src import formatters as fmt
from src import intents
from src import llm_bot
from src import nltk_bot
from src import memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chatbotmusic-dev-secret")


@app.route('/')
def index():
    return render_template('index.html')


def _sessao_id() -> str:
    """Id da sessão do usuário (cookie assinado). Cria um se ainda não houver."""
    sid = session.get("sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid
    return sid


def _gerar_resposta(user_message: str, historico: list[dict]) -> str:
    """Decide a resposta: Spotify (base) → LLM com memória → NLTK."""
    # ── 1ª tentativa: Spotify ─────────────────────────────
    intent, payload = intents.detect(user_message)

    try:
        if intent == "track":
            tracks = spotify.search_track(payload)
            if tracks:
                return fmt.tracks(tracks, payload)

        elif intent == "artist_info":
            perfil  = spotify.search_artist(payload)
            na_base = perfil is not None and spotify.nome_corresponde(perfil["name"], payload)
            if na_base:
                completo = spotify.get_artist_profile(perfil["name"])
                if completo:
                    resumo = llm_bot.resumo_artista(completo["name"])
                    return fmt.artist(completo, resumo)

            resumo = llm_bot.resumo_artista(payload.title())
            if resumo:
                return fmt.artist_summary(payload.title(), resumo)

        elif intent == "artist":
            info = spotify.get_artist_profile(payload)
            if info:
                return fmt.artist(info)

        elif intent == "album":
            info = spotify.search_album(payload)
            if info:
                return fmt.album(info)

        elif intent == "discography":
            info = spotify.get_discography(payload)
            if info:
                return fmt.discography(info)

        elif intent == "playlist":
            playlists = spotify.search_playlists(payload)
            if playlists:
                return fmt.playlists(playlists, payload)

        elif intent == "recommendations":
            seed = payload or random.choice(spotify.SEED_ARTISTS)
            tracks = spotify.get_recommendations(seed)
            if tracks:
                return fmt.recommendations(tracks, seed)

    except Exception:
        logger.exception("Erro ao consultar o Spotify (intent=%s)", intent)

    resposta_llm = llm_bot.responder(user_message, historico)
    if resposta_llm:
        return resposta_llm

    return nltk_bot.responder(user_message)


@app.route('/chat', methods=['POST'])
def chat():
    data         = request.get_json()
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'response': 'Mensagem vazia!'})

    sid       = _sessao_id()
    historico = memory.get(sid)

    resposta = _gerar_resposta(user_message, historico)

    # Guarda o turno (usuário + bot) para dar contexto às próximas mensagens.
    memory.registrar(sid, user_message, resposta)
    return jsonify({'response': resposta})


@app.route('/reset', methods=['POST'])
def reset():
    sid = session.get("sid")
    if sid:
        memory.limpar(sid)
    return jsonify({'response': 'Conversa reiniciada!'})


if __name__ == '__main__':

    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug)
