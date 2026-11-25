"""Ferramentas que o agente pode usar.

Cada função aqui vira uma "ferramenta" para o Gemini. O SDK lê:
  - o NOME da função       -> nome da ferramenta
  - os TIPOS dos parâmetros -> o que o modelo precisa enviar
  - a DOCSTRING            -> quando e para que usar a ferramenta
Por isso as docstrings são escritas para o MODELO ler. Elas fazem parte do prompt.

As ferramentas reaproveitam as funções dos routers (dia 2), então a regra
de negócio fica num lugar só: a API e o agente se comportam igual.
"""

from fastapi import HTTPException
from pydantic import ValidationError

from app.database import SessionLocal
from app.routers import assinaturas, chamados, clientes, faturas
from app.schemas import (
    AssinaturaOut,
    ChamadoCreate,
    ChamadoOut,
    ClienteOut,
    FaturaOut,
    PagamentoOut,
)


def _para_json(itens, schema) -> list[dict]:
    """Converte objetos do banco em dicionários simples (datas e valores viram texto)."""
    return [schema.model_validate(item).model_dump(mode="json") for item in itens]


def buscar_cliente(email: str) -> dict:
    """Busca um cliente pelo e-mail. Use SEMPRE como primeiro passo, para obter o cliente_id.

    Args:
        email: e-mail do cliente, exatamente como ele informou.
    """
    with SessionLocal() as db:
        try:
            cliente = clientes.buscar_cliente_por_email(email=email, db=db)
        except HTTPException as erro:
            return {"erro": erro.detail}
        return ClienteOut.model_validate(cliente).model_dump(mode="json")


def listar_assinaturas(cliente_id: int) -> dict:
    """Lista as assinaturas de um cliente, com plano, preço, status e forma de pagamento.

    Args:
        cliente_id: id retornado por buscar_cliente.
    """
    with SessionLocal() as db:
        try:
            itens = clientes.listar_assinaturas(cliente_id=cliente_id, db=db)
        except HTTPException as erro:
            return {"erro": erro.detail}
        return {"assinaturas": _para_json(itens, AssinaturaOut)}


def listar_faturas(assinatura_id: int) -> dict:
    """Lista as 12 faturas mais recentes de uma assinatura, da mais nova para a mais antiga.

    Status possíveis: paga, vencida (venceu sem pagamento), pendente (ainda não venceu).

    Args:
        assinatura_id: id retornado por listar_assinaturas.
    """
    with SessionLocal() as db:
        try:
            # Chamando a função direto (fora do FastAPI), precisamos passar
            # todos os parâmetros que no endpoint tinham valor padrão via Query().
            itens = assinaturas.listar_faturas(
                assinatura_id=assinatura_id, status=None, limite=12, db=db
            )
        except HTTPException as erro:
            return {"erro": erro.detail}
        return {"faturas": _para_json(itens, FaturaOut)}


def listar_pagamentos(fatura_id: int) -> dict:
    """Lista todas as tentativas de pagamento de uma fatura (aprovadas, recusadas ou estornadas).

    Use para investigar cobranças em duplicidade ou pagamentos recusados.
    Mais de um pagamento "aprovado" na mesma fatura indica cobrança em duplicidade.

    Args:
        fatura_id: id retornado por listar_faturas.
    """
    with SessionLocal() as db:
        try:
            itens = faturas.listar_pagamentos(fatura_id=fatura_id, db=db)
        except HTTPException as erro:
            return {"erro": erro.detail}
        return {"pagamentos": _para_json(itens, PagamentoOut)}


def abrir_chamado(cliente_id: int, assunto: str, descricao: str) -> dict:
    """Abre um chamado para a equipe humana resolver. Retorna o número do chamado (id).

    Use quando o problema exige ação humana, como estorno de cobrança em duplicidade
    ou cobrança feita depois do cancelamento. Na descrição, inclua os ids das faturas
    e pagamentos envolvidos e os valores.

    Args:
        cliente_id: id do cliente.
        assunto: resumo curto do problema (3 a 120 caracteres).
        descricao: descrição detalhada, com ids e valores (mínimo de 10 caracteres).
    """
    with SessionLocal() as db:
        try:
            dados = ChamadoCreate(cliente_id=cliente_id, assunto=assunto, descricao=descricao)
            chamado = chamados.abrir_chamado(dados=dados, db=db)
        except HTTPException as erro:
            return {"erro": erro.detail}
        except ValidationError as erro:
            return {"erro": f"Dados inválidos: {erro.errors()[0]['msg']}"}
        return ChamadoOut.model_validate(chamado).model_dump(mode="json")


# Lista usada pelo agente. Para dar uma ferramenta nova ao agente, basta incluí-la aqui.
FERRAMENTAS = [buscar_cliente, listar_assinaturas, listar_faturas, listar_pagamentos, abrir_chamado]
FERRAMENTAS_POR_NOME = {f.__name__: f for f in FERRAMENTAS}
