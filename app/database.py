"""Conexão com o banco de dados.

O endereço do banco vem da variável DATABASE_URL, definida no arquivo .env
(copie o .env.example). Exemplo para PostgreSQL:
    postgresql+psycopg://cobrancas:cobrancas@localhost:5432/cobrancas

Sem .env, usa um arquivo SQLite local (útil para testes rápidos).
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()  # lê o arquivo .env, se existir

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
