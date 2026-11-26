import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "oficina.db"


def agora_str() -> str:
    """Retorna data e hora atuais formatadas para os registros da oficina."""
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


def get_connection() -> sqlite3.Connection:
    """Abre e retorna uma conexão com o banco SQLite."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def garantir_colunas_passagens(cursor: sqlite3.Cursor) -> None:
    """Garante que todas as colunas esperadas existam na tabela passagens_oficina."""
    colunas_esperadas = {
        "Data_Hora_Entrada": "TEXT",
        "Data_Hora_Laudo": "TEXT",
        "Data_Hora_Envio_Orcamento": "TEXT",
        "Data_Hora_Resposta_Cliente": "TEXT",
        "Data_Hora_Inicio_Servico": "TEXT",
        "Data_Hora_Conclusao_Servico": "TEXT",
        "Data_Hora_Notificacao_Conclusao": "TEXT",
        "Data_Hora_Saida": "TEXT",
        "Fotos_Laudo": "TEXT",
    }
    cursor.execute("PRAGMA table_info(passagens_oficina)")
    existentes = {row["name"] for row in cursor.fetchall()}
    for coluna, tipo in colunas_esperadas.items():
        if coluna not in existentes:
            cursor.execute(f"ALTER TABLE passagens_oficina ADD COLUMN {coluna} {tipo}")


def migrar_maquinas_legado(cursor: sqlite3.Cursor) -> None:
    """Migra schema antigo de maquinas para passagens_oficina sem perda de dados."""
    cursor.execute("PRAGMA table_info(maquinas)")
    cols_maq = {row["name"] for row in cursor.fetchall()}

    if "Status" in cols_maq:
        cursor.execute("SELECT COUNT(*) AS total FROM passagens_oficina")
        qtd_passagens = cursor.fetchone()["total"]
        if qtd_passagens == 0:
            cursor.execute("""
                SELECT ID, Data_Hora_Entrada, Data_Hora_Laudo, Data_Hora_Envio_Orcamento,
                       Data_Hora_Resposta_Cliente, Data_Hora_Inicio_Servico,
                       Data_Hora_Conclusao_Servico, Data_Hora_Notificacao_Conclusao,
                       Data_Hora_Saida, Status, Descricao_Laudo, Anomalias,
                       Pecas_Solicitadas, Valor_Orcamento, Mecanico_Laudo, Mecanico_Execucao
                FROM maquinas
            """)
            legados = cursor.fetchall()
            for row in legados:
                cursor.execute("""
                    INSERT INTO passagens_oficina (
                        ID_Maquina, Data_Hora_Entrada, Data_Hora_Laudo, Data_Hora_Envio_Orcamento,
                        Data_Hora_Resposta_Cliente, Data_Hora_Inicio_Servico,
                        Data_Hora_Conclusao_Servico, Data_Hora_Notificacao_Conclusao,
                        Data_Hora_Saida, Status, Descricao_Laudo, Anomalias,
                        Pecas_Solicitadas, Valor_Orcamento, Mecanico_Laudo, Mecanico_Execucao, Fotos_Laudo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]')
                """, (
                    row["ID"],
                    row["Data_Hora_Entrada"],
                    row["Data_Hora_Laudo"],
                    row["Data_Hora_Envio_Orcamento"],
                    row["Data_Hora_Resposta_Cliente"],
                    row["Data_Hora_Inicio_Servico"],
                    row["Data_Hora_Conclusao_Servico"],
                    row["Data_Hora_Notificacao_Conclusao"],
                    row["Data_Hora_Saida"],
                    row["Status"],
                    row["Descricao_Laudo"],
                    row["Anomalias"],
                    row["Pecas_Solicitadas"],
                    row["Valor_Orcamento"],
                    row["Mecanico_Laudo"],
                    row["Mecanico_Execucao"],
                ))

        cursor.execute("ALTER TABLE maquinas RENAME TO maquinas_legado")
        cursor.execute("""
            CREATE TABLE maquinas (
                ID TEXT PRIMARY KEY,
                QR_Code TEXT,
                ID_Cliente TEXT,
                Cliente_Nome TEXT,
                Telefone TEXT,
                Modelo TEXT,
                Data_Hora_Cadastro TEXT,
                Obs_Cadastro TEXT,
                Fotos_Cadastro TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO maquinas (
                ID, QR_Code, ID_Cliente, Cliente_Nome, Telefone,
                Modelo, Data_Hora_Cadastro, Obs_Cadastro, Fotos_Cadastro
            )
            SELECT ID, QR_Code, ID_Cliente, Cliente_Nome, Telefone, Modelo,
                   COALESCE(Data_Hora_Entrada, ''), COALESCE(Obs_Cadastro, ''), '[]'
            FROM maquinas_legado
        """)
        cursor.execute("DROP TABLE maquinas_legado")

    cursor.execute("PRAGMA table_info(maquinas)")
    cols_maq_atual = {row["name"] for row in cursor.fetchall()}
    if "Data_Hora_Cadastro" not in cols_maq_atual:
        cursor.execute("ALTER TABLE maquinas ADD COLUMN Data_Hora_Cadastro TEXT")
    if "Fotos_Cadastro" not in cols_maq_atual:
        cursor.execute("ALTER TABLE maquinas ADD COLUMN Fotos_Cadastro TEXT DEFAULT '[]'")


def inicializar_banco() -> None:
    """Cria tabelas necessárias e insere registros iniciais se o banco estiver vazio."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            Usuario TEXT PRIMARY KEY,
            Senha TEXT,
            Perfil TEXT,
            Nome TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            ID_Cliente TEXT PRIMARY KEY,
            Nome TEXT,
            Telefone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            ID_Peca TEXT PRIMARY KEY,
            Nome TEXT,
            Quantidade INTEGER,
            Minimo INTEGER,
            Preco_Unitario REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maquinas (
            ID TEXT PRIMARY KEY,
            QR_Code TEXT,
            ID_Cliente TEXT,
            Cliente_Nome TEXT,
            Telefone TEXT,
            Modelo TEXT,
            Data_Hora_Cadastro TEXT,
            Obs_Cadastro TEXT,
            Fotos_Cadastro TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passagens_oficina (
            ID_Passagem INTEGER PRIMARY KEY AUTOINCREMENT,
            ID_Maquina TEXT NOT NULL,
            Data_Hora_Entrada TEXT,
            Data_Hora_Laudo TEXT,
            Data_Hora_Envio_Orcamento TEXT,
            Data_Hora_Resposta_Cliente TEXT,
            Data_Hora_Inicio_Servico TEXT,
            Data_Hora_Conclusao_Servico TEXT,
            Data_Hora_Notificacao_Conclusao TEXT,
            Data_Hora_Saida TEXT,
            Status TEXT,
            Descricao_Laudo TEXT,
            Anomalias TEXT,
            Pecas_Solicitadas TEXT,
            Valor_Orcamento REAL,
            Mecanico_Laudo TEXT,
            Mecanico_Execucao TEXT,
            Fotos_Laudo TEXT,
            FOREIGN KEY (ID_Maquina) REFERENCES maquinas(ID)
        )
    """)

    garantir_colunas_passagens(cursor)
    migrar_maquinas_legado(cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            ID_Log INTEGER PRIMARY KEY AUTOINCREMENT,
            Data_Hora TEXT NOT NULL,
            Usuario TEXT NOT NULL,
            Perfil TEXT NOT NULL,
            Acao TEXT NOT NULL,
            Detalhes TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany("INSERT INTO usuarios VALUES (?, ?, ?, ?)", [
            ("admin", "123", "Secretaria (Administração)", "Administração Central"),
            ("mecanico1", "123", "Mecânico (Oficina)", "Carlos Mecânico"),
        ])

    cursor.execute("SELECT COUNT(*) AS total FROM clientes")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany("INSERT INTO clientes VALUES (?, ?, ?)", [
            ("CLI-001", "João Silva", "21999998888"),
            ("CLI-002", "Maria Oliveira", "21988887777"),
        ])

    cursor.execute("SELECT COUNT(*) AS total FROM estoque")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany("INSERT INTO estoque VALUES (?, ?, ?, ?, ?)", [
            ("PEC-001", "Correia Dentada", 10, 3, 150.00),
            ("PEC-002", "Filtro de Óleo", 15, 5, 45.00),
            ("PEC-003", "Vela de Ignição", 1, 4, 30.00),
            ("PEC-004", "Pastilha de Freio", 8, 2, 120.00),
        ])

    conn.commit()
    conn.close()