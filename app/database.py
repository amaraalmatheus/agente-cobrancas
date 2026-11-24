"""Conexão com o banco de dados.

Começamos com SQLite (um arquivo local, sem instalar nada).
Para trocar por PostgreSQL depois, basta definir a variável de ambiente
DATABASE_URL, por exemplo:
    postgresql+psycopg://usuario:senha@localhost:5432/cobrancas
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cobrancas.db")

# O SQLite precisa desse parâmetro para funcionar com o FastAPI,
# que pode atender requisições em threads diferentes.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Classe base de todos os modelos (tabelas)."""


def get_db():
    """Abre uma sessão por requisição e garante que ela seja fechada.

    Usado pelo FastAPI com Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
