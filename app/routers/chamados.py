from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chamado, Cliente, StatusChamado
from app.schemas import ChamadoCreate, ChamadoOut

router = APIRouter(prefix="/chamados", tags=["chamados"])


@router.post("", response_model=ChamadoOut, status_code=201)
def abrir_chamado(dados: ChamadoCreate, db: Session = Depends(get_db)):
    """Abre um chamado para a equipe humana (ex.: pedido de estorno)."""
    if db.get(Cliente, dados.cliente_id) is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    chamado = Chamado(
        **dados.model_dump(),
        status=StatusChamado.ABERTO,
        criado_em=datetime.now(),
    )
    db.add(chamado)
    db.commit()
    db.refresh(chamado)  # recarrega do banco para pegar o id gerado
    return chamado
