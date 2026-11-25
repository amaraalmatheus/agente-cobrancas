from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Assinatura, Cliente
from app.schemas import AssinaturaOut, ClienteOut

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=ClienteOut)
def buscar_cliente_por_email(email: str, db: Session = Depends(get_db)):
    """Busca um cliente pelo e-mail. Normalmente é o primeiro passo do agente."""
    cliente = db.scalar(select(Cliente).where(Cliente.email == email.strip().lower()))
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


@router.get("/{cliente_id}/assinaturas", response_model=list[AssinaturaOut])
def listar_assinaturas(cliente_id: int, db: Session = Depends(get_db)):
    """Lista as assinaturas do cliente, já com os dados do plano."""
    if db.get(Cliente, cliente_id) is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    consulta = (
        select(Assinatura)
        .where(Assinatura.cliente_id == cliente_id)
        # selectinload busca os planos junto, numa consulta só,
        # em vez de uma consulta extra para cada assinatura (o "problema N+1").
        .options(selectinload(Assinatura.plano))
        .order_by(Assinatura.data_inicio)
    )
    return db.scalars(consulta).all()
