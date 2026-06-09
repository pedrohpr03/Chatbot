"""ChatBotMusic — servidor Flask.

Orquestra as peças: detecta a intenção (intents), busca no Spotify
(spotify_client), formata a resposta (formatters) ou cai no chatbot
de padrões (nltk_bot).
"""
from flask import Flask, request, jsonify, render_template
import os
import random
import logging

from src import spotify_client as spotify
from src import formatters as fmt
from src import intents
from src import nltk_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data         = request.get_json()
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'response': 'Mensagem vazia!'})

    # ── 1ª tentativa: Spotify ─────────────────────────────
    intent, payload = intents.detect(user_message)

    try:
        if intent == "track":
            tracks = spotify.search_track(payload)
            if tracks:
                return jsonify({'response': fmt.tracks(tracks, payload)})

        elif intent == "artist":
            info = spotify.get_artist_profile(payload)
            if info:
                return jsonify({'response': fmt.artist(info)})

        elif intent == "album":
            info = spotify.search_album(payload)
            if info:
                return jsonify({'response': fmt.album(info)})

        elif intent == "discography":
            info = spotify.get_discography(payload)
            if info:
                return jsonify({'response': fmt.discography(info)})

        elif intent == "playlist":
            playlists = spotify.search_playlists(payload)
            if playlists:
                return jsonify({'response': fmt.playlists(playlists, payload)})

        elif intent == "recommendations":
            seed = payload or random.choice(spotify.SEED_ARTISTS)
            tracks = spotify.get_recommendations(seed)
            if tracks:
                return jsonify({'response': fmt.recommendations(tracks, seed)})

    except Exception:
        logger.exception("Erro ao consultar o Spotify (intent=%s)", intent)

    # ── 2ª tentativa: chatbot de padrões (NLTK) ───────────
    # Sem resultado (ou sem credenciais) → cai no chatbot normal
    return jsonify({'response': nltk_bot.responder(user_message)})


if __name__ == '__main__':
    # debug ligado só se FLASK_DEBUG estiver definido (ex.: FLASK_DEBUG=1)
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug)
