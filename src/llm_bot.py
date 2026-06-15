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

_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct")

_SEM_RESPOSTA = "__SEM_RESPOSTA__"

_SYSTEM_PROMPT = (
    "Você é o ChatBotMusic, um assistente apaixonado por música. "
    "Converse em português do Brasil, de forma curta (no máximo 3 frases), "
    "calorosa e empolgada. Seu tema central é música: artistas, bandas, "
    "gêneros, álbuns, história e curiosidades musicais.\n"
    "REGRA DE OURO: nunca invente fatos. Se perguntarem sobre alguém que NÃO é "
    "músico (jogador, ator, cientista, político, influenciador) ou sobre outro "
    "assunto (carros, futebol, filmes, comida, etc.), dê UMA informação correta "
    "e breve sobre quem ou o que é e então puxe a conversa de volta para a "
    "música — ligando a uma banda, gênero, trilha sonora ou artista. "
    "NUNCA diga que um não-músico é cantor ou compositor; se não souber quem é "
    "a pessoa, admita com leveza e convide a falar de música.\n"
    "Ex.: 'quem é Vinícius Júnior?' → 'É um jogador de futebol brasileiro! "
    "Falando em craques, que tal conhecer o samba do Seu Jorge?'\n"
    "LETRAS: nunca reproduza, complete nem invente a LETRA de uma música "
    "(direitos autorais). Se pedirem uma letra, diga com leveza que não a "
    "encontrou e ofereça falar SOBRE a música — tema, significado, história.\n"
    "Responda APENAS com o texto exato "
    f"{_SEM_RESPOSTA} (sem mais nada) somente quando a pergunta for muito "
    "específica ou técnica sobre um tema fora de música, daquelas que exigem "
    "conhecimento aprofundado (ex.: 'como trocar o óleo do motor de um Civic "
    "2015', 'qual a fórmula da fotossíntese', 'resolva esta equação'). "
    "Nesses casos não invente nem chute: apenas devolva a sentinela."
)

# Regra: decide músico ou não Antes de responder,
# com exemplos nos dois sentidos. Sem isso, modelos menores inventam uma
# biografia musical para qualquer nome (ex.: tratam um jogador como cantor)
_RESUMO_SYS = (
    "Você avalia um nome e decide se é de um MÚSICO ou BANDA (cantor, rapper, "
    "DJ, compositor, instrumentista ou grupo musical).\n"
    "• Se NÃO for da música (atleta, ator, político, influenciador, personagem) "
    f"ou se você não reconhecer como músico, responda APENAS {_SEM_RESPOSTA}.\n"
    "• Se for músico/banda, escreva um resumo REAL de 2 a 4 frases, em português "
    "do Brasil, sobre a carreira musical, o estilo/gênero e a importância — texto "
    "corrido, sem listas e sem títulos. Não copie os exemplos abaixo.\n"
    f"Exemplos: Vinícius Júnior (jogador) → {_SEM_RESPOSTA}; Neymar (jogador) → "
    f"{_SEM_RESPOSTA}; Anitta (cantora) → escreva o resumo; Coldplay (banda) → "
    "escreva o resumo."
)

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


def _chat(system: str | None, user: str, temperature: float, max_tokens: int,
          history: list[dict] | None = None) -> str | None:
    """Faz uma chamada de chat ao modelo. Retorna o texto ou None em caso de erro.

    `history` (opcional) são os turnos anteriores da conversa, no formato
    {"role": "user"/"assistant", "content": ...}, inseridos entre o system e a
    mensagem atual para dar memória à conversa.
    """
    client = _get_client()
    if client is None:
        return None

    mensagens = []
    if system:
        mensagens.append({"role": "system", "content": system})
    if history:
        mensagens.extend(history)
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
    texto = _chat(_RESUMO_SYS, f"Nome a avaliar: '{nome}'", temperature=0.3, max_tokens=400)
    if not texto or _eh_sentinela(texto):
        return None
    return texto


def responder(message: str, history: list[dict] | None = None) -> str | None:
    """Resposta do LLM sobre música, com memória opcional da conversa.

    `history` são os turnos anteriores (lista de mensagens) e permite
    follow-ups com contexto. Devolve o texto da resposta, ou None quando o
    LLM não pode ajudar (sem token, erro de API, ou mensagem fora do tema
    musical) — nesses casos o app deve cair no chatbot de padrões (NLTK).
    """
    texto = _chat(_SYSTEM_PROMPT, message, temperature=0.7, max_tokens=500, history=history)
    if not texto or _eh_sentinela(texto):
        return None
    return texto
