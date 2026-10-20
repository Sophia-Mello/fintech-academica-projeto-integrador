"""Acesso ao SQLite fornecido e persistência de lançamentos da aplicação.

O arquivo fintech_integrada.db é a base recebida e não é alterado por este módulo.
O Streamlit grava em uma cópia criada na primeira execução.
"""
from __future__ import annotations
import hashlib
import os
from datetime import date, datetime
from pathlib import Path
import sqlite3
import pandas as pd
from .validacao import CATEGORIAS, validar_despesa

DIRETORIO = Path(__file__).resolve().parents[1]
BASE_ORIGINAL = DIRETORIO / 'fintech_integrada.db'
BANCO_OPERACIONAL = Path(os.environ.get('FINTECH_DB_PATH', str(DIRETORIO / 'fintech_operacional.db')))


def hash_original() -> str:
    return hashlib.sha256(BASE_ORIGINAL.read_bytes()).hexdigest()


def preparar_operacional(destino: Path | None = None) -> Path:
    """Cria cópia de trabalho com auditoria adicional, sem editar o banco recebido."""
    destino = Path(destino or BANCO_OPERACIONAL).resolve()
    if destino == BASE_ORIGINAL.resolve():
        raise ValueError('O banco original não pode ser usado para gravações do app.')
    if destino.exists():
        return destino
    if not BASE_ORIGINAL.is_file():
        raise FileNotFoundError(f'Banco de origem não encontrado: {BASE_ORIGINAL}')
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + '.tmp')
    if tmp.exists():
        raise FileExistsError(f'Cópia temporária já existe: {tmp}')
    try:
        with sqlite3.connect(f'file:{BASE_ORIGINAL}?mode=ro', uri=True) as origem:
            if origem.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Banco recebido inválido.')
            with sqlite3.connect(tmp) as copia:
                origem.backup(copia)
                copia.executescript('''
                    CREATE TABLE IF NOT EXISTS despesas_staging (
                        linha_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_despesa INTEGER NOT NULL UNIQUE,
                        valor REAL NOT NULL, data TEXT NOT NULL,
                        estudante_id INTEGER NOT NULL, municipio_id INTEGER NOT NULL,
                        categoria TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS despesas_app_metadata (
                        id_despesa INTEGER PRIMARY KEY, origem_registro TEXT NOT NULL);
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_despesas_clean_id ON despesas_clean(id);
                    CREATE INDEX IF NOT EXISTS idx_despesas_clean_data ON despesas_clean(data,estudante_id);
                ''')
                copia.commit()
        os.replace(tmp, destino)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return destino


def conectar(destino: Path | None = None) -> sqlite3.Connection:
    db = preparar_operacional(destino)
    c = sqlite3.connect(db, timeout=20)
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=20000')
    return c


def despesas_completas(banco: Path | None = None) -> pd.DataFrame:
    """Lê tabelas originais ou operacionais, distinguindo a proveniência."""
    db = Path(banco) if banco is not None else preparar_operacional()
    with sqlite3.connect(db) as c:
        possui_metadata = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='despesas_app_metadata'").fetchone()[0] > 0
        join_meta = 'LEFT JOIN despesas_app_metadata o ON o.id_despesa=d.id' if possui_metadata else ''
        origem = "COALESCE(o.origem_registro,'original_semana_06')" if possui_metadata else "'original_semana_06'"
        df = pd.read_sql_query(f'''
            SELECT d.id,d.valor,d.data,d.estudante_id,d.municipio_id,d.categoria,d.is_outlier,
                   e.nome AS estudante,e.matricula,m.nome AS municipio,m.uf_sigla AS uf,
                   {origem} AS origem_registro
            FROM despesas_clean d
            INNER JOIN estudantes e ON e.id=d.estudante_id
            INNER JOIN municipios m ON m.id=d.municipio_id
            {join_meta}
            ORDER BY d.data,d.id
        ''', c)
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['is_outlier'] = df['is_outlier'].fillna(0).astype(bool)
    return df


def cadastro(nome: str, banco: Path | None = None) -> pd.DataFrame:
    if nome not in {'estudantes','municipios'}:
        raise ValueError('Tabela inválida.')
    db = Path(banco) if banco is not None else preparar_operacional()
    with sqlite3.connect(db) as c:
        return pd.read_sql_query(f'SELECT * FROM {nome} ORDER BY nome',c)


def staging(banco: Path | None = None) -> pd.DataFrame:
    db = Path(banco) if banco is not None else preparar_operacional()
    with sqlite3.connect(db) as c:
        return pd.read_sql_query('SELECT * FROM despesas_staging ORDER BY linha_id',c)


def atualizar_iqr(conn: sqlite3.Connection) -> None:
    linhas = conn.execute('SELECT id,valor FROM despesas_clean ORDER BY id').fetchall()
    if not linhas:
        return
    valores = pd.Series([v for _,v in linhas], dtype=float)
    q1, q3 = valores.quantile([0.25,0.75])
    minimo, maximo = q1 - 1.5*(q3-q1), q3 + 1.5*(q3-q1)
    conn.executemany('UPDATE despesas_clean SET is_outlier=? WHERE id=?', [
        (int(v < minimo or v > maximo),int(i)) for i,v in linhas
    ])


def registrar_despesa(estudante_id: int, municipio_id: int, valor: float,
                     data: date | datetime, categoria: str, banco: Path | None = None) -> int:
    validar_despesa(valor,data,categoria)
    data_sql = data.strftime('%Y-%m-%d')
    with conectar(banco) as c:
        try:
            c.execute('BEGIN IMMEDIATE')
            n = c.execute('''
                SELECT MAX(ultimo)+1 FROM (
                    SELECT COALESCE(MAX(id),0) AS ultimo FROM despesas
                    UNION ALL
                    SELECT COALESCE(MAX(id),0) AS ultimo FROM despesas_clean)
            ''').fetchone()[0]
            c.execute('INSERT INTO despesas(id,valor,data,estudante_id,municipio_id) VALUES(?,?,?,?,?)',
                      (n,float(valor),data_sql,int(estudante_id),int(municipio_id)))
            c.execute('''INSERT INTO despesas_clean
                       (id,valor,data,estudante_id,municipio_id,categoria,is_outlier)
                       VALUES(?,?,?,?,?,?,0)''',
                      (n,float(valor),data_sql,int(estudante_id),int(municipio_id),CATEGORIAS[categoria]))
            c.execute("INSERT INTO despesas_app_metadata VALUES(?,'aplicativo')", (n,))
            c.execute('INSERT INTO despesas_staging(id_despesa,valor,data,estudante_id,municipio_id,categoria) VALUES (?,?,?,?,?,?)',
                      (n,float(valor),data_sql,int(estudante_id),int(municipio_id),CATEGORIAS[categoria]))
            atualizar_iqr(c)
            c.commit()
            return n
        except Exception:
            c.rollback()
            raise
