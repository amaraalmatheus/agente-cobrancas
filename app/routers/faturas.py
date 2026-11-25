from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Fatura, Pagamento
from app.schemas import PagamentoOut

router = APIRouter(prefix="/faturas", tags=["faturas"])


# EXERCÍCIO: implemente este endpoint.
#
# GET /faturas/{fatura_id}/pagamentos
#   - Retorna todos os pagamentos (tentativas) de uma fatura, do mais antigo ao mais recente.
#   - Se a fatura não existir, retorna 404 com a mensagem "Fatura não encontrada".
#
# Dica: o listar_assinaturas, em routers/clientes.py, faz algo muito parecido.
# Para testar: a Ana deve ter uma fatura com 2 pagamentos "aprovado".

@router.get("/{fatura_id}/pagamentos", response_model=list[PagamentoOut])
def listar_pagamentos(fatura_id: int, db: Session = Depends(get_db)):
    """Lista as tentativas de pagamento de uma fatura."""

    if db.get(Fatura, fatura_id) is None:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")

    consulta = (
        select(Pagamento)
        .where(Pagamento.fatura_id == fatura_id)
        .order_by(Pagamento.criado_em)
    )
    
    return db.scalars(consulta).all()


