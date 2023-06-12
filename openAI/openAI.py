import openai

from autenticacao import Autenticacao_OpenAI as autenticacao

Autenticacao = autenticacao()


class ChatGPT:

    def __init__(self):
        self._openai_key = Autenticacao.key()

    def conexao(self):
        openai.api_key = self._openai_key
        return openai

    def get_response(self, pergunta, texto):
        resposta_chat = self.conexao.Completion.create(
            engine="text-davinci-003",
            prompt=texto + "\nQ: " + pergunta + "\nA:",
            max_tokens=100,
            n=1,
            stop=None
        )
        return resposta_chat
