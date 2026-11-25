"""Schemas: definem o formato dos dados que ENTRAM e SAEM da API.

Os models (models.py) representam as tabelas do banco.
Os schemas representam o que o cliente da API (e o agente) vê.
Separar os dois permite esconder campos sensíveis, como o CPF.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SchemaDoBanco(BaseModel):
    """Base para schemas de saída: permite criar o schema direto de um objeto do SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)


# --- Saída (respostas da API) -----------------------------------------------

class ClienteOut(SchemaDoBanco):
    id: int
    nome: str
    email: str
    telefone: str
    criado_em: datetime
    # O CPF fica de fora de propósito: o agente não precisa dele,
    # e quanto menos dado pessoal for enviado ao modelo de IA, melhor.


class PlanoOut(SchemaDoBanco):
    id: int
    nome: str
    descricao: str
    preco_mensal: Decimal


class AssinaturaOut(SchemaDoBanco):
    id: int
    status: str
    metodo_pagamento: str
    data_inicio: date
    data_cancelamento: date | None
    plano: PlanoOut


class FaturaOut(SchemaDoBanco):
    id: int
    assinatura_id: int
    mes_referencia: date
    valor: Decimal
    vencimento: date
    status: str


class PagamentoOut(SchemaDoBanco):
    id: int
    fatura_id: int
    valor: Decimal
    metodo: str
    status: str
    motivo_recusa: str | None
    criado_em: datetime


class ChamadoOut(SchemaDoBanco):
    id: int
    cliente_id: int
    assunto: str
    descricao: str
    status: str
    criado_em: datetime


# --- Entrada (corpo das requisições) ----------------------------------------

class ChamadoCreate(BaseModel):
    cliente_id: int
    assunto: str = Field(min_length=3, max_length=120)
    descricao: str = Field(min_length=10)
