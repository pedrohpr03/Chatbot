"""Memória de conversa, por sessão.

Guarda as últimas interações de cada sessão para dar contexto à LLM, permitindo
responder perguntas como "e o álbum dele?" na conversa. Zera quando o
servidor reinicia."""
import re
import html
from collections import deque, defaultdict

MAX_TURNOS         = 8     # pares (usuário + bot) mantidos por sessão
MAX_CHARS_RESPOSTA = 500   

_historicos: dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_TURNOS * 2))


def get(sid: str) -> list[dict]:
    return list(_historicos[sid])


def registrar(sid: str, mensagem_usuario: str, resposta_bot: str) -> None:
    historico = _historicos[sid]
    historico.append({"role": "user", "content": mensagem_usuario})
    historico.append({"role": "assistant", "content": _texto_limpo(resposta_bot)})


def limpar(sid: str) -> None:
    _historicos.pop(sid, None)


def _texto_limpo(resposta: str) -> str:

    sem_tags = re.sub(r"<[^>]+>", " ", resposta)
    texto    = html.unescape(sem_tags)
    texto    = re.sub(r"\s+", " ", texto).strip()
    return texto[:MAX_CHARS_RESPOSTA]
