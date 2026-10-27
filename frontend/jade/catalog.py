"""Catálogo provisório: confirmar textos e urgências com a equipe da prancha."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    id: str
    label: str
    urgency: str
    color: str


MESSAGES = (
    Message("agua", "Quero água", "Baixa", "#007F9E"),
    Message("comida", "Estou com fome", "Baixa", "#3167AB"),
    Message("companhia", "Quero companhia", "Baixa", "#7C62A3"),
    Message("descansar", "Quero descansar", "Baixa", "#648345"),
    Message("banheiro", "Preciso ir ao banheiro", "Média", "#A56A16"),
    Message("posicao", "Quero mudar de posição", "Média", "#C16138"),
    Message("frio", "Estou com frio", "Média", "#3B7F79"),
    Message("calor", "Estou com calor", "Média", "#AA586D"),
    Message("dor", "Estou com dor", "Alta", "#C13F4C"),
    Message("ajuda", "Preciso de ajuda agora", "Alta", "#78503D"),
)
MESSAGE_BY_ID = {message.id: message for message in MESSAGES}
URGENCIES = ("Baixa", "Média", "Alta")
URGENCY_COLORS = {"Baixa": "#007F9E", "Média": "#A56A16", "Alta": "#C13F4C"}
TIMEZONE = "America/Sao_Paulo"
