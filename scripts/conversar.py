"""Converse com o agente pelo terminal.

    python -m scripts.conversar

Digite "sair" para encerrar. Cada conversa usa várias requisições da sua cota diária.
"""

from app.agente.agente import Agente


def main() -> None:
    agente = Agente(mostrar_passos=True)
    print(f"Agente de cobranças ({agente.modelo}). Digite 'sair' para encerrar.\n")

    while True:
        mensagem = input("Você: ").strip()
        if mensagem.lower() in {"sair", "exit", "quit"}:
            break
        if not mensagem:
            continue

        resultado = agente.responder(mensagem)
        print(f"\nAgente: {resultado.resposta}")
        print(
            f"  [{resultado.chamadas_ao_modelo} chamadas ao modelo | "
            f"{resultado.tokens} tokens | {resultado.segundos}s]\n"
        )


if __name__ == "__main__":
    main()
