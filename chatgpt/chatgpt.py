import openai
from autenticacao import Autenticacao_OpenAI

ChatKey = Autenticacao_OpenAI()


class chatgpt:

    def __init__(self) -> None:
        openai.api_key = ChatKey.key()

    def get_response(self, pergunta, texto):
        resposta = openai.Completion.create(
            engine="text-davinci-003",
            prompt=texto + "\nQ: " + pergunta + "\nA:",
            max_tokens=100,
            n=1,
            stop=None
        )
        return resposta['choices'][0]['text'] # type: ignore
