from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Assinatura, Fatura, StatusFatura
from app.schemas import FaturaOut

router = APIRouter(prefix="/assinaturas", tags=["assinaturas"])


@router.get("/{assinatura_id}/faturas", response_model=list[FaturaOut])
def listar_faturas(
    assinatura_id: int,
    status: StatusFatura | None = None,
    limite: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Lista as faturas de uma assinatura, da mais recente para a mais antiga.

    - status: filtra por status (opcional)
    - limite: máximo de faturas retornadas (padrão 12)
    """
    if db.get(Assinatura, assinatura_id) is None:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")

    consulta = select(Fatura).where(Fatura.assinatura_id == assinatura_id)
    if status is not None:
        consulta = consulta.where(Fatura.status == status)
    # O limite protege o agente: respostas enormes gastam tokens (dinheiro)
    # e atrapalham o modelo a achar a informação certa.
    consulta = consulta.order_by(Fatura.mes_referencia.desc()).limit(limite)

    return db.scalars(consulta).all()
