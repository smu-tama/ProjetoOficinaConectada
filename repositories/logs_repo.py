import pandas as pd
from database.connection import agora_str, get_connection


def registrar_log(
    acao: str,
    detalhes: str,
    usuario: str | None = None,
    perfil: str | None = None,
) -> None:
    """Insere um evento de auditoria na tabela logs."""
    usuario_final = usuario.strip() if usuario and usuario.strip() else "Visitante / Não autenticado"
    perfil_final = perfil.strip() if perfil and perfil.strip() else "Sem perfil"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO logs (Data_Hora, Usuario, Perfil, Acao, Detalhes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agora_str(), usuario_final, perfil_final, acao, detalhes),
        )
        conn.commit()
    finally:
        conn.close()


def listar_logs(acao: str | None = None, busca: str | None = None) -> pd.DataFrame:
    """Retorna os logs ordenados do mais recente para o mais antigo, com filtros opcionais."""
    conn = get_connection()
    try:
        df = pd.read_sql(
            """
            SELECT ID_Log, Data_Hora, Usuario, Perfil, Acao, Detalhes
            FROM logs
            ORDER BY ID_Log DESC
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return df

    if acao and acao != "Todas":
        df = df[df["Acao"] == acao]

    if busca and busca.strip():
        termo = busca.strip().lower()
        df = df[
            df["Usuario"].astype(str).str.lower().str.contains(termo, na=False)
            | df["Detalhes"].astype(str).str.lower().str.contains(termo, na=False)
            | df["Acao"].astype(str).str.lower().str.contains(termo, na=False)
        ]

    return df.reset_index(drop=True)


def listar_acoes_logs() -> list[str]:
    """Retorna os tipos distintos de ações registradas nos logs."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Acao FROM logs ORDER BY Acao ASC")
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [row["Acao"] for row in rows if row["Acao"]]