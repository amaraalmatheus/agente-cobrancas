"""O loop do agente.

Como funciona, a cada mensagem do cliente:
  1. Enviamos ao Gemini: instruções + histórico da conversa + lista de ferramentas.
  2. O Gemini responde de um de dois jeitos:
       a) com TEXTO          -> é a resposta final, acabou.
       b) com CHAMADAS de ferramentas -> nós executamos as funções (o modelo
          não executa nada, só pede) e devolvemos os resultados. Volta ao passo 1.
  3. Para não entrar em loop infinito (e gastar a cota), há um limite de passos.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.agente.ferramentas import FERRAMENTAS, FERRAMENTAS_POR_NOME

load_dotenv()

MAX_PASSOS = 8

INSTRUCOES = """Você é o assistente de suporte de cobranças de um serviço de streaming por assinatura.
Data de hoje: {hoje}.

Regras:
- Para consultar qualquer dado, você precisa do e-mail do cliente. Se ele não informou, peça.
- Use as ferramentas para obter os dados. NUNCA invente faturas, valores, datas ou status.
- Se as ferramentas não trouxerem a informação, diga que não encontrou. Não suponha.
- Investigue antes de concluir: para dúvidas sobre cobrança, consulte faturas E pagamentos.
- Cobrança em duplicidade ou cobrança após o cancelamento: abra um chamado e informe o
  número do chamado ao cliente. Você não pode fazer estornos; quem faz é a equipe humana.
- Pagamento recusado: explique o motivo da recusa e oriente o cliente a atualizar a forma de pagamento.
- Responda em português, de forma curta, educada e objetiva. Valores no formato R$ 39,90.
- Não mostre ids internos ao cliente, exceto o número do chamado.
"""


@dataclass
class Resultado:
    """O que o agente devolve: a resposta e as métricas da execução (úteis para a avaliação)."""

    resposta: str
    ferramentas_usadas: list[dict] = field(default_factory=list)
    chamadas_ao_modelo: int = 0
    tokens: int = 0
    segundos: float = 0.0


class Agente:
    def __init__(self, modelo: str | None = None, mostrar_passos: bool = False):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.modelo = modelo or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.mostrar_passos = mostrar_passos
        self.historico: list[types.Content] = []  # memória da conversa
        self.config = types.GenerateContentConfig(
            system_instruction=INSTRUCOES.format(hoje=date.today().strftime("%d/%m/%Y")),
            tools=FERRAMENTAS,
            # Desligamos a execução automática do SDK para controlar o loop nós mesmos:
            # assim podemos registrar cada passo, limitar os passos e tratar erros.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0.2,  # mais baixa = respostas mais consistentes
        )

    def responder(self, mensagem: str) -> Resultado:
        inicio = time.perf_counter()
        resultado = Resultado(resposta="")
        self.historico.append(types.Content(role="user", parts=[types.Part(text=mensagem)]))

        for _ in range(MAX_PASSOS):
            resposta = self.client.models.generate_content(
                model=self.modelo, contents=self.historico, config=self.config
            )
            resultado.chamadas_ao_modelo += 1
            if resposta.usage_metadata and resposta.usage_metadata.total_token_count:
                resultado.tokens += resposta.usage_metadata.total_token_count

            # Guardamos a resposta do modelo inteira no histórico (inclusive as chamadas
            # de ferramenta), senão na próxima rodada ele "esquece" o que pediu.
            self.historico.append(resposta.candidates[0].content)

            if not resposta.function_calls:
                resultado.resposta = resposta.text or ""
                break

            partes_com_resultados = []
            for chamada in resposta.function_calls:
                argumentos = dict(chamada.args or {})
                saida = self._executar(chamada.name, argumentos)
                resultado.ferramentas_usadas.append({"nome": chamada.name, "argumentos": argumentos})
                if self.mostrar_passos:
                    print(f"  🔧 {chamada.name}({argumentos})")
                    print(f"     → {json.dumps(saida, ensure_ascii=False)[:200]}")
                partes_com_resultados.append(
                    types.Part.from_function_response(name=chamada.name, response=saida)
                )
            self.historico.append(types.Content(role="user", parts=partes_com_resultados))
        else:
            resultado.resposta = (
                "Desculpe, não consegui concluir o atendimento. Vou encaminhar para um atendente."
            )

        resultado.segundos = round(time.perf_counter() - inicio, 2)
        return resultado

    def _executar(self, nome: str, argumentos: dict) -> dict:
        """Executa a ferramenta pedida pelo modelo, sem deixar um erro derrubar o agente."""
        funcao = FERRAMENTAS_POR_NOME.get(nome)
        if funcao is None:
            return {"erro": f"Ferramenta '{nome}' não existe."}
        try:
            return funcao(**argumentos)
        except Exception as erro:  # o modelo pode mandar argumentos errados
            return {"erro": f"Falha ao executar {nome}: {erro}"}
