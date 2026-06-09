"""Chatbot conversacional via LLM (HuggingFace Inference API).

Usado quando a mensagem não é um comando do Spotify. Conversa sobre música
em português usando um modelo hospedado no HuggingFace. Se não conseguir
ajudar — mensagem fora do tema, erro/cota da API ou sem token —, devolve None,
e o app cai no chatbot de padrões (NLTK), que é a última opção.
"""
import os
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Modelo hospedado no HuggingFace (ungated, multilíngue). Troque via HF_MODEL.
_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# Sentinela: o modelo devolve exatamente isto quando a mensagem não é sobre
# música. Assim detectamos "não achei nada relacionado" e caímos no NLTK.
_SEM_RESPOSTA = "__SEM_RESPOSTA__"

_SYSTEM_PROMPT = (
    "Você é o ChatBotMusic, um assistente apaixonado por música. "
    "Converse em português do Brasil, de forma curta (no máximo 3 frases), "
    "calorosa e empolgada. Seu tema central é música: artistas, bandas, "
    "gêneros, álbuns, história e curiosidades musicais.\n"
    "Você PODE comentar de forma leve e superficial sobre qualquer outro "
    "assunto (carros, futebol, filmes, comida, etc.), sem se aprofundar, e "
    "deve SEMPRE tentar puxar a conversa de volta para música — por exemplo, "
    "ligando o tema a uma banda, música, trilha sonora ou gênero. "
    "Ex.: se perguntarem sobre carros, fale uma frase geral e emende com "
    "músicas ou artistas que falam de carros/estrada.\n"
    "Responda APENAS com o texto exato "
    f"{_SEM_RESPOSTA} (sem mais nada) somente quando a pergunta for muito "
    "específica ou técnica sobre um tema fora de música, daquelas que exigem "
    "conhecimento aprofundado (ex.: 'como trocar o óleo do motor de um Civic "
    "2015', 'qual a fórmula da fotossíntese', 'resolva esta equação'). "
    "Nesses casos não invente nem chute: apenas devolva a sentinela."
)

# Inicialização preguiçosa: o cliente só é criado se houver token de API.
_client = None
_init_tentada = False


def _get_client():
    """Cria (uma única vez) o cliente da Inference API. None se não der."""
    global _client, _init_tentada
    if _init_tentada:
        return _client
    _init_tentada = True

    token = os.getenv("HF_TOKEN")
    if not token:
        logger.info("HF_TOKEN não configurado — LLM desativado, usando só NLTK.")
        return None

    try:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(provider="auto", api_key=token)
    except Exception:
        logger.exception("Falha ao inicializar o cliente HuggingFace.")
        _client = None

    return _client


def _chat(system: str | None, user: str, temperature: float, max_tokens: int) -> str | None:
    """Faz uma chamada de chat ao modelo. Retorna o texto ou None em caso de erro."""
    client = _get_client()
    if client is None:
        return None

    mensagens = []
    if system:
        mensagens.append({"role": "system", "content": system})
    mensagens.append({"role": "user", "content": user})

    try:
        resp = client.chat_completion(
            mensagens,
            model=_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        # Cobre cota esgotada (429), modelo indisponível, rede, etc.
        logger.exception("Erro ao consultar o modelo no HuggingFace.")
        return None


def _eh_sentinela(texto: str) -> bool:
    """Detecta a sentinela mesmo se o modelo mudar underscores/markdown/caixa.

    Modelos menores às vezes devolvem 'SEM_RESPOSTA' ou '**SEM RESPOSTA**' em
    vez do '__SEM_RESPOSTA__' exato. Normalizamos (sem underscores/espaços) e,
    para evitar falso positivo em resposta longa de verdade, só consideramos
    sentinela quando a mensagem é curta.
    """
    normal = texto.upper().replace("_", "").replace(" ", "")
    return len(texto) < 80 and "SEMRESPOSTA" in normal


def resumo_artista(nome: str) -> str | None:
    """Resumo curto, em texto, sobre um artista/banda musical.

    Devolve um texto de 2 a 4 frases, ou None se o LLM não estiver disponível
    ou não conhecer o artista — nesses casos o app tenta outra alternativa.
    """
    prompt = (
        f"Escreva um resumo curto (2 a 4 frases), em português do Brasil, sobre o "
        f"artista ou banda musical '{nome}'. Foque na carreira musical, no estilo ou "
        f"gênero e na importância dele. Use texto corrido, sem listas e sem títulos. "
        f"Se você não conhecer esse artista musical, responda APENAS com {_SEM_RESPOSTA}."
    )
    texto = _chat(None, prompt, temperature=0.6, max_tokens=400)
    if not texto or _eh_sentinela(texto):
        return None
    return texto


def responder(message: str) -> str | None:
    """Resposta do LLM sobre música.

    Devolve o texto da resposta, ou None quando o LLM não pode ajudar
    (sem token, erro de API, ou mensagem fora do tema musical) — nesses
    casos o app deve cair no chatbot de padrões (NLTK).
    """
    texto = _chat(_SYSTEM_PROMPT, message, temperature=0.7, max_tokens=500)
    if not texto or _eh_sentinela(texto):
        return None
    return texto
