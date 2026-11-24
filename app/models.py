"""Modelos do banco: cada classe é uma tabela.

Relações:
    Cliente 1 ── N Assinatura N ── 1 Plano
    Assinatura 1 ── N Fatura 1 ── N Pagamento   (uma fatura pode ter várias tentativas)
    Cliente 1 ── N Chamado
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# --- Valores permitidos nos campos de status -------------------------------
# Guardamos como texto no banco e usamos estes enums no código,
# para evitar erros de digitação como "aprovdo".

class StatusAssinatura(StrEnum):
    ATIVA = "ativa"
    SUSPENSA = "suspensa"      # suspensa por falta de pagamento
    CANCELADA = "cancelada"


class MetodoPagamento(StrEnum):
    CARTAO = "cartao"
    PIX = "pix"
    BOLETO = "boleto"


class StatusFatura(StrEnum):
    PENDENTE = "pendente"      # ainda não venceu
    PAGA = "paga"
    VENCIDA = "vencida"        # venceu e não foi paga
    CANCELADA = "cancelada"


class StatusPagamento(StrEnum):
    APROVADO = "aprovado"
    RECUSADO = "recusado"
    ESTORNADO = "estornado"    # devolvido ao cliente


class StatusChamado(StrEnum):
    ABERTO = "aberto"
    RESOLVIDO = "resolvido"


# --- Tabelas ---------------------------------------------------------------

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    cpf: Mapped[str] = mapped_column(String(14), unique=True)
    telefone: Mapped[str] = mapped_column(String(30))
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    assinaturas: Mapped[list["Assinatura"]] = relationship(back_populates="cliente")
    chamados: Mapped[list["Chamado"]] = relationship(back_populates="cliente")


class Plano(Base):
    __tablename__ = "planos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    descricao: Mapped[str] = mapped_column(String(255))
    # Numeric em vez de float: dinheiro nunca deve usar float (erros de arredondamento).
    preco_mensal: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    assinaturas: Mapped[list["Assinatura"]] = relationship(back_populates="plano")


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    plano_id: Mapped[int] = mapped_column(ForeignKey("planos.id"))
    status: Mapped[str] = mapped_column(String(20))
    metodo_pagamento: Mapped[str] = mapped_column(String(20))
    data_inicio: Mapped[date] = mapped_column(Date)
    data_cancelamento: Mapped[date | None] = mapped_column(Date, nullable=True)

    cliente: Mapped[Cliente] = relationship(back_populates="assinaturas")
    plano: Mapped[Plano] = relationship(back_populates="assinaturas")
    faturas: Mapped[list["Fatura"]] = relationship(back_populates="assinatura")


class Fatura(Base):
    __tablename__ = "faturas"

    id: Mapped[int] = mapped_column(primary_key=True)
    assinatura_id: Mapped[int] = mapped_column(ForeignKey("assinaturas.id"), index=True)
    mes_referencia: Mapped[date] = mapped_column(Date)   # sempre dia 1 do mês
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    vencimento: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))

    assinatura: Mapped[Assinatura] = relationship(back_populates="faturas")
    pagamentos: Mapped[list["Pagamento"]] = relationship(back_populates="fatura")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fatura_id: Mapped[int] = mapped_column(ForeignKey("faturas.id"), index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    metodo: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    motivo_recusa: Mapped[str | None] = mapped_column(String(120), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    fatura: Mapped[Fatura] = relationship(back_populates="pagamentos")


class Chamado(Base):
    """Chamado de suporte. O agente vai poder abrir chamados a partir do dia 2."""

    __tablename__ = "chamados"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    assunto: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    cliente: Mapped[Cliente] = relationship(back_populates="chamados")
