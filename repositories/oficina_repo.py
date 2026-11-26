import pandas as pd
from database.connection import agora_str, get_connection


TABELAS_PERMITIDAS = {"usuarios", "clientes", "estoque", "maquinas", "passagens_oficina"}


def carregar_tabela(tabela: str) -> pd.DataFrame:
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError(f"Tabela não permitida: {tabela}")
    conn = get_connection()
    try:
        return pd.read_sql(f"SELECT * FROM {tabela}", conn)
    finally:
        conn.close()


def salvar_tabela_df(df: pd.DataFrame, tabela: str) -> None:
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError(f"Tabela não permitida: {tabela}")
    conn = get_connection()
    try:
        df.to_sql(tabela, conn, if_exists="replace", index=False)
    finally:
        conn.close()


def inserir_passagem(
    id_maquina: str,
    data_entrada: str | None = None,
    status: str = "Aguardando Avaliação Técnica",
) -> int:
    entrada = data_entrada or agora_str()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO passagens_oficina (
                ID_Maquina, Data_Hora_Entrada, Data_Hora_Laudo, Data_Hora_Envio_Orcamento,
                Data_Hora_Resposta_Cliente, Data_Hora_Inicio_Servico,
                Data_Hora_Conclusao_Servico, Data_Hora_Notificacao_Conclusao,
                Data_Hora_Saida, Status, Descricao_Laudo, Anomalias,
                Pecas_Solicitadas, Valor_Orcamento, Mecanico_Laudo, Mecanico_Execucao, Fotos_Laudo
            ) VALUES (?, ?, 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', ?, 'Pendente', 'Nenhuma', '[]', 0.0, 'Pendente', 'Pendente', '[]')
            """,
            (str(id_maquina), entrada, status),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def atualizar_passagem_campos(id_passagem: int, campos: dict) -> None:
    if not campos:
        return
    set_clause = ", ".join(f"{col} = ?" for col in campos.keys())
    valores = list(campos.values()) + [int(id_passagem)]
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE passagens_oficina SET {set_clause} WHERE ID_Passagem = ?",
            valores,
        )
        conn.commit()
    finally:
        conn.close()


def obter_passagens_por_maquina(id_maquina: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM passagens_oficina WHERE ID_Maquina = ? ORDER BY ID_Passagem DESC",
            conn,
            params=(str(id_maquina),),
        )
    finally:
        conn.close()


def excluir_maquina_e_historico(id_maquina: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM passagens_oficina WHERE ID_Maquina = ?",
            (str(id_maquina),),
        )
        cursor.execute("DELETE FROM maquinas WHERE ID = ?", (str(id_maquina),))
        conn.commit()
    finally:
        conn.close()


def obter_visao_consolidada() -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(
            """
            SELECT
                m.ID,
                m.QR_Code,
                m.ID_Cliente,
                m.Cliente_Nome,
                m.Telefone,
                m.Modelo,
                m.Obs_Cadastro,
                m.Data_Hora_Cadastro,
                COALESCE(m.Fotos_Cadastro, '[]') AS Fotos_Cadastro,
                p.ID_Passagem,
                COALESCE(p.Status, 'Sem Passagem Aberta') AS Status,
                COALESCE(p.Valor_Orcamento, 0.0) AS Valor_Orcamento,
                COALESCE(p.Data_Hora_Entrada, 'N/A') AS Data_Hora_Entrada,
                COALESCE(p.Data_Hora_Laudo, 'Pendente') AS Data_Hora_Laudo,
                COALESCE(p.Data_Hora_Envio_Orcamento, 'Pendente') AS Data_Hora_Envio_Orcamento,
                COALESCE(p.Data_Hora_Resposta_Cliente, 'Pendente') AS Data_Hora_Resposta_Cliente,
                COALESCE(p.Data_Hora_Inicio_Servico, 'Pendente') AS Data_Hora_Inicio_Servico,
                COALESCE(p.Data_Hora_Conclusao_Servico, 'Pendente') AS Data_Hora_Conclusao_Servico,
                COALESCE(p.Data_Hora_Notificacao_Conclusao, 'Pendente') AS Data_Hora_Notificacao_Conclusao,
                COALESCE(p.Data_Hora_Saida, 'Pendente') AS Data_Hora_Saida,
                COALESCE(p.Descricao_Laudo, 'Pendente') AS Descricao_Laudo,
                COALESCE(p.Anomalias, 'Nenhuma') AS Anomalias,
                COALESCE(p.Pecas_Solicitadas, '[]') AS Pecas_Solicitadas,
                COALESCE(p.Mecanico_Laudo, 'Pendente') AS Mecanico_Laudo,
                COALESCE(p.Mecanico_Execucao, 'Pendente') AS Mecanico_Execucao,
                COALESCE(p.Fotos_Laudo, '[]') AS Fotos_Laudo
            FROM maquinas m
            LEFT JOIN passagens_oficina p
                ON p.ID_Passagem = (
                    SELECT p2.ID_Passagem
                    FROM passagens_oficina p2
                    WHERE p2.ID_Maquina = m.ID
                    ORDER BY p2.ID_Passagem DESC
                    LIMIT 1
                )
            """,
            conn,
        )
    finally:
        conn.close()


def obter_historico_por_cliente(id_cliente: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = get_connection()
    try:
        maquinas_df = pd.read_sql(
            """
            SELECT
                m.ID,
                m.QR_Code,
                m.Modelo,
                m.Data_Hora_Cadastro,
                m.Obs_Cadastro,
                COALESCE(m.Fotos_Cadastro, '[]') AS Fotos_Cadastro,
                COUNT(p.ID_Passagem) AS Total_Passagens,
                COALESCE((
                    SELECT p_ult.Status
                    FROM passagens_oficina p_ult
                    WHERE p_ult.ID_Maquina = m.ID
                    ORDER BY p_ult.ID_Passagem DESC
                    LIMIT 1
                ), 'Sem Passagem Aberta') AS Ultimo_Status
            FROM maquinas m
            LEFT JOIN passagens_oficina p ON p.ID_Maquina = m.ID
            WHERE m.ID_Cliente = ?
            GROUP BY m.ID, m.QR_Code, m.Modelo, m.Data_Hora_Cadastro, m.Obs_Cadastro, m.Fotos_Cadastro
            ORDER BY m.ID ASC
            """,
            conn,
            params=(str(id_cliente),),
        )
        passagens_df = pd.read_sql(
            """
            SELECT
                p.*,
                m.Modelo,
                m.QR_Code
            FROM passagens_oficina p
            INNER JOIN maquinas m ON m.ID = p.ID_Maquina
            WHERE m.ID_Cliente = ?
            ORDER BY p.ID_Passagem DESC
            """,
            conn,
            params=(str(id_cliente),),
        )
        return maquinas_df, passagens_df
    finally:
        conn.close()