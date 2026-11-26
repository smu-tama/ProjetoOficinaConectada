import datetime
import random
import re
import io
import json
import sqlite3
import qrcode
import cv2
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_back_camera_input import back_camera_input

st.set_page_config(
    page_title="Oficina Conectada - Sistema de Gestão",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------
# IDENTIDADE VISUAL (BRANCO, AZUL E AMARELO) & COCKPIT COMPACTO
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --azul-escuro: #0F3D75;
            --azul-principal: #1D5FA7;
            --azul-claro-bg: #EEF4FB;
            --amarelo-destaque: #F5B700;
            --amarelo-suave: #FFF8DB;
            --branco: #FFFFFF;
            --borda-azul: #C8D9EE;
            --texto-escuro: #162436;
        }

        .stApp {
            background-color: #F4F8FC;
            color: var(--texto-escuro);
        }

        /* Reduz padding superior/inferior para caber tudo acima da dobra */
        .block-container {
            padding-top: 1.1rem !important;
            padding-bottom: 1rem !important;
            max-width: 98% !important;
        }

        [data-testid="stSidebar"] {
            background-color: var(--branco);
            border-right: 2px solid var(--borda-azul);
        }

        /* Cabeçalho de marca Branco, Azul e Amarelo */
        .oficina-header {
            background: linear-gradient(90deg, #0F3D75 0%, #1D5FA7 84%, #F5B700 100%);
            color: #FFFFFF;
            padding: 12px 20px;
            border-radius: 10px;
            border-bottom: 3px solid #F5B700;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(15, 61, 117, 0.12);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .oficina-header h1 {
            margin: 0;
            font-size: 1.35rem;
            color: #FFFFFF;
        }
        .oficina-header span {
            font-size: 0.85rem;
            color: #FFF8DB;
            font-weight: 500;
        }

        /* Botões padrão em Azul com detalhe Amarelo */
        .stButton > button,
        .stFormSubmitButton > button,
        .stDownloadButton > button {
            background-color: #1D5FA7;
            color: #FFFFFF;
            border: 1.5px solid #0F3D75;
            border-radius: 7px;
            font-weight: 600;
            padding: 0.35rem 0.75rem;
            transition: all 0.16s ease;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stDownloadButton > button:hover {
            background-color: #0F3D75;
            color: #FFD166;
            border-color: #F5B700;
        }

        /* Painel superior de navegação (Mecânico no PC) */
        .painel-nav-desktop-label {
            font-size: 0.82rem;
            font-weight: 700;
            color: #0F3D75;
            border-left: 4px solid #F5B700;
            padding-left: 8px;
            margin-bottom: 6px;
        }

        /* Abas com destaque Azul e Amarelo */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            border-bottom: 2px solid #C8D9EE;
            margin-bottom: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #FFFFFF;
            color: #0F3D75;
            border: 1px solid #C8D9EE;
            border-bottom: none;
            border-radius: 7px 7px 0 0;
            font-weight: 600;
            font-size: 0.84rem;
            padding: 6px 11px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0F3D75 !important;
            color: #FFD166 !important;
            border-bottom: 3px solid #F5B700 !important;
        }

        /* Cards de métricas compactos */
        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #C8D9EE;
            border-top: 3px solid #F5B700;
            border-radius: 8px;
            padding: 8px 12px;
            box-shadow: 0 1px 4px rgba(15, 61, 117, 0.06);
        }
        [data-testid="stMetricLabel"] {
            color: #0F3D75 !important;
            font-weight: 700;
            font-size: 0.78rem !important;
        }
        [data-testid="stMetricValue"] {
            color: #162436 !important;
            font-size: 1.35rem !important;
        }

        /* Painéis internos do Cockpit */
        .cockpit-box-title {
            background-color: #FFFFFF;
            border: 1px solid #C8D9EE;
            border-left: 5px solid #F5B700;
            color: #0F3D75;
            padding: 7px 12px;
            border-radius: 7px;
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 8px;
        }

        .nav-mobile-only {
            display: none;
        }

        @media (max-width: 768px) {
            .nav-desktop-only {
                display: none !important;
            }
            .nav-mobile-only {
                display: block !important;
                background-color: #FFF8DB;
                border: 1.5px solid #F5B700;
                color: #0F3D75;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 0.85rem;
                font-weight: 600;
                margin-bottom: 10px;
            }
            .oficina-header h1 {
                font-size: 1.15rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="oficina-header">
        <h1>🔧 Oficina Conectada: Gestão Integrada (SQL)</h1>
        <span>Branco • Azul • Amarelo | Operação Ágil</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def agora_str():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------
# CONFIGURAÇÃO E INICIALIZAÇÃO DO BANCO DE DADOS SQLITE
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect("oficina.db", check_same_thread=False)
    return conn


def garantir_colunas_passagens(cursor):
    colunas_esperadas = {
        "Data_Hora_Entrada": "TEXT",
        "Data_Hora_Laudo": "TEXT",
        "Data_Hora_Envio_Orcamento": "TEXT",
        "Data_Hora_Resposta_Cliente": "TEXT",
        "Data_Hora_Inicio_Servico": "TEXT",
        "Data_Hora_Conclusao_Servico": "TEXT",
        "Data_Hora_Notificacao_Conclusao": "TEXT",
        "Data_Hora_Saida": "TEXT",
    }
    cursor.execute("PRAGMA table_info(passagens_oficina)")
    existentes = {row[1] for row in cursor.fetchall()}
    for col, tipo in colunas_esperadas.items():
        if col not in existentes:
            cursor.execute(f"ALTER TABLE passagens_oficina ADD COLUMN {col} {tipo}")


def inicializar_banco():
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
            Obs_Cadastro TEXT
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
            FOREIGN KEY (ID_Maquina) REFERENCES maquinas(ID)
        )
    """)

    garantir_colunas_passagens(cursor)

    cursor.execute("PRAGMA table_info(maquinas)")
    cols_maq = {row[1] for row in cursor.fetchall()}
    if "Status" in cols_maq:
        cursor.execute("SELECT COUNT(*) FROM passagens_oficina")
        qtd_passagens = cursor.fetchone()[0]
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
                        Pecas_Solicitadas, Valor_Orcamento, Mecanico_Laudo, Mecanico_Execucao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)

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
                Obs_Cadastro TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO maquinas (ID, QR_Code, ID_Cliente, Cliente_Nome, Telefone, Modelo, Data_Hora_Cadastro, Obs_Cadastro)
            SELECT ID, QR_Code, ID_Cliente, Cliente_Nome, Telefone, Modelo,
                   COALESCE(Data_Hora_Entrada, ''), COALESCE(Obs_Cadastro, '')
            FROM maquinas_legado
        """)
        cursor.execute("DROP TABLE maquinas_legado")

    cursor.execute("PRAGMA table_info(maquinas)")
    cols_maq_atual = {row[1] for row in cursor.fetchall()}
    if "Data_Hora_Cadastro" not in cols_maq_atual:
        cursor.execute("ALTER TABLE maquinas ADD COLUMN Data_Hora_Cadastro TEXT")

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

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO usuarios VALUES (?, ?, ?, ?)", [
            ("admin", "123", "Secretaria (Administração)", "Administração Central"),
            ("mecanico1", "123", "Mecânico (Oficina)", "Carlos Mecânico"),
        ])

    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO clientes VALUES (?, ?, ?)", [
            ("CLI-001", "João Silva", "21999998888"),
            ("CLI-002", "Maria Oliveira", "21988887777"),
        ])

    cursor.execute("SELECT COUNT(*) FROM estoque")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO estoque VALUES (?, ?, ?, ?, ?)", [
            ("PEC-001", "Correia Dentada", 10, 3, 150.00),
            ("PEC-002", "Filtro de Óleo", 15, 5, 45.00),
            ("PEC-003", "Vela de Ignição", 1, 4, 30.00),
            ("PEC-004", "Pastilha de Freio", 8, 2, 120.00),
        ])

    conn.commit()
    conn.close()


inicializar_banco()


def registrar_log(acao, detalhes):
    usuario = st.session_state.get("usuario_logado") or "Visitante / Não autenticado"
    perfil = st.session_state.get("perfil_logado") or "Sem perfil"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (Data_Hora, Usuario, Perfil, Acao, Detalhes) VALUES (?, ?, ?, ?, ?)",
        (agora_str(), usuario, perfil, acao, detalhes),
    )
    conn.commit()
    conn.close()


if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None
if "flash_sucesso" not in st.session_state:
    st.session_state.flash_sucesso = None
if "tela_mecanico" not in st.session_state:
    st.session_state.tela_mecanico = "Entrada / Passagens"

if st.session_state.flash_sucesso:
    st.success(st.session_state.flash_sucesso)
    st.session_state.flash_sucesso = None


# ---------------------------------------------------------
# FUNÇÕES DE CONSULTA E PERSISTÊNCIA SQL
# ---------------------------------------------------------
def carregar_dados(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df


def salvar_dataframe(df, tabela):
    if tabela == "logs":
        raise PermissionError("A tabela de logs é imutável e não pode ser substituída.")
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists="replace", index=False)
    conn.close()


def criar_passagem(id_maquina, data_entrada=None, status="Aguardando Avaliação Técnica"):
    entrada = data_entrada or agora_str()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO passagens_oficina (
            ID_Maquina, Data_Hora_Entrada, Data_Hora_Laudo, Data_Hora_Envio_Orcamento,
            Data_Hora_Resposta_Cliente, Data_Hora_Inicio_Servico,
            Data_Hora_Conclusao_Servico, Data_Hora_Notificacao_Conclusao,
            Data_Hora_Saida, Status, Descricao_Laudo, Anomalias,
            Pecas_Solicitadas, Valor_Orcamento, Mecanico_Laudo, Mecanico_Execucao
        ) VALUES (?, ?, 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', 'Pendente', ?, 'Pendente', 'Nenhuma', '[]', 0.0, 'Pendente', 'Pendente')
    """, (id_maquina, entrada, status))
    nova_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return nova_id


def atualizar_passagem(id_passagem, campos_dict):
    if not campos_dict:
        return
    set_clause = ", ".join(f"{col} = ?" for col in campos_dict.keys())
    valores = list(campos_dict.values()) + [id_passagem]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE passagens_oficina SET {set_clause} WHERE ID_Passagem = ?", valores)
    conn.commit()
    conn.close()


def obter_passagens_maquina(id_maquina):
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM passagens_oficina WHERE ID_Maquina = ? ORDER BY ID_Passagem DESC",
        conn,
        params=(str(id_maquina),),
    )
    conn.close()
    return df


def obter_ultima_passagem(id_maquina):
    df_p = obter_passagens_maquina(id_maquina)
    if df_p.empty:
        return None
    return df_p.iloc[0]


# ---------------------------------------------------------
# FUNÇÃO AUXILIAR: GERAR QR CODE REAL EM BYTES
# ---------------------------------------------------------
def gerar_imagem_qrcode(texto_dado):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(texto_dado)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def validar_telefone(tel_str):
    apenas_numeros = re.sub(r"\D", "", tel_str)
    if len(apenas_numeros) >= 10 and len(apenas_numeros) <= 11:
        return apenas_numeros
    return None


def fmt_data(val, fallback="Pendente"):
    if val is None or (isinstance(val, float) and np.isnan(val)) or str(val).strip() in ("", "None", "nan"):
        return fallback
    return str(val)


def fmt_valor(val):
    try:
        return f"R$ {float(val):.2f}"
    except Exception:
        return "R$ 0.00"


def renderizar_cronologia_html(passagem):
    return f"""
        <hr style="border-color: #C8D9EE; margin: 8px 0;">
        <p style="margin: 3px 0;"><b>📅 Chegada:</b> {fmt_data(passagem.get('Data_Hora_Entrada'))} | <b>📋 Laudo:</b> {fmt_data(passagem.get('Data_Hora_Laudo'))}</p>
        <p style="margin: 3px 0;"><b>📤 Enviado Cliente:</b> {fmt_data(passagem.get('Data_Hora_Envio_Orcamento'))} | <b>✍️ Resposta:</b> {fmt_data(passagem.get('Data_Hora_Resposta_Cliente'))}</p>
        <p style="margin: 3px 0;"><b>▶️ Início Serviço:</b> {fmt_data(passagem.get('Data_Hora_Inicio_Servico'))} | <b>🏁 Conclusão:</b> {fmt_data(passagem.get('Data_Hora_Conclusao_Servico'))}</p>
        <p style="margin: 3px 0;"><b>📲 Notificado:</b> {fmt_data(passagem.get('Data_Hora_Notificacao_Conclusao'))} | <b>🚚 Saída:</b> {fmt_data(passagem.get('Data_Hora_Saida'))}</p>
    """


def renderizar_cronologia_texto(passagem):
    return (
        f"📅 **Chegada:** {fmt_data(passagem.get('Data_Hora_Entrada'))} • "
        f"📋 **Laudo:** {fmt_data(passagem.get('Data_Hora_Laudo'))}\n\n"
        f"📤 **Orçamento ao cliente:** {fmt_data(passagem.get('Data_Hora_Envio_Orcamento'))} • "
        f"✍️ **Resposta cliente:** {fmt_data(passagem.get('Data_Hora_Resposta_Cliente'))}\n\n"
        f"▶️ **Início serviço:** {fmt_data(passagem.get('Data_Hora_Inicio_Servico'))} • "
        f"🏁 **Conclusão:** {fmt_data(passagem.get('Data_Hora_Conclusao_Servico'))}\n\n"
        f"📲 **Notificado:** {fmt_data(passagem.get('Data_Hora_Notificacao_Conclusao'))} • "
        f"🚚 **Saída:** {fmt_data(passagem.get('Data_Hora_Saida'))}"
    )


def exibir_banco_passagens_maquina(id_maquina, titulo_secao="🗂️ Histórico de Passagens da Máquina"):
    df_p = obter_passagens_maquina(id_maquina)
    st.markdown(f"**{titulo_secao} ({len(df_p)} registrada(s))**")
    if df_p.empty:
        st.info("Esta máquina possui 0 passagens/orçamentos registrados.")
        return

    df_resumo = df_p[[
        "ID_Passagem",
        "Status",
        "Valor_Orcamento",
        "Data_Hora_Entrada",
        "Data_Hora_Conclusao_Servico",
        "Data_Hora_Saida",
    ]].copy()
    st.dataframe(df_resumo, use_container_width=True, hide_index=True, height=180)

    pass_ids = list(df_p["ID_Passagem"])
    sel_p = st.selectbox(
        "Inspecionar detalhes da passagem:",
        pass_ids,
        format_func=lambda pid: f"Passagem #{pid} — {df_p[df_p['ID_Passagem'] == pid].iloc[0]['Status']}",
        key=f"insp_pass_{id_maquina}",
    )
    p = df_p[df_p["ID_Passagem"] == sel_p].iloc[0]
    st.caption(
        f"Laudo: {fmt_data(p.get('Descricao_Laudo'))} | Anomalias: {fmt_data(p.get('Anomalias'), 'Nenhuma')} | "
        f"Mec. Laudo: {fmt_data(p.get('Mecanico_Laudo'), 'Pendente')} | Mec. Exec.: {fmt_data(p.get('Mecanico_Execucao'), 'Pendente')}"
    )
    st.markdown(renderizar_cronologia_texto(p))
    if p.get("Pecas_Solicitadas"):
        try:
            p_list = json.loads(p["Pecas_Solicitadas"])
            if p_list:
                st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True, height=130)
        except Exception:
            pass


def carregar_visao_consolidada_passagens():
    conn = get_connection()
    df = pd.read_sql("""
        SELECT
            m.ID,
            m.QR_Code,
            m.ID_Cliente,
            m.Cliente_Nome,
            m.Telefone,
            m.Modelo,
            m.Obs_Cadastro,
            m.Data_Hora_Cadastro,
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
            COALESCE(p.Mecanico_Execucao, 'Pendente') AS Mecanico_Execucao
        FROM maquinas m
        LEFT JOIN passagens_oficina p
            ON p.ID_Passagem = (
                SELECT p2.ID_Passagem
                FROM passagens_oficina p2
                WHERE p2.ID_Maquina = m.ID
                ORDER BY p2.ID_Passagem DESC
                LIMIT 1
            )
    """, conn)
    conn.close()
    return df


def carregar_historico_cliente(id_cliente):
    conn = get_connection()
    maquinas_df = pd.read_sql("""
        SELECT
            m.ID,
            m.QR_Code,
            m.Modelo,
            m.Data_Hora_Cadastro,
            m.Obs_Cadastro,
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
        GROUP BY m.ID, m.QR_Code, m.Modelo, m.Data_Hora_Cadastro, m.Obs_Cadastro
        ORDER BY m.ID ASC
    """, conn, params=(str(id_cliente),))

    passagens_df = pd.read_sql("""
        SELECT
            p.*,
            m.Modelo,
            m.QR_Code
        FROM passagens_oficina p
        INNER JOIN maquinas m ON m.ID = p.ID_Maquina
        WHERE m.ID_Cliente = ?
        ORDER BY p.ID_Passagem DESC
    """, conn, params=(str(id_cliente),))
    conn.close()
    return maquinas_df, passagens_df


def renderizar_visao_historica_cliente(contexto_key="default", compacto=False):
    df_cli = carregar_dados("clientes")
    if df_cli.empty:
        st.info("Nenhum cliente cadastrado no sistema.")
        return

    c_busca, c_sel = st.columns([1, 1.4])
    filtro_cli = c_busca.text_input(
        "Buscar cliente (nome/ID/tel):",
        key=f"filtro_cli_{contexto_key}",
    )

    df_cli_view = df_cli.copy()
    if filtro_cli.strip():
        termo = filtro_cli.strip().lower()
        df_cli_view = df_cli_view[
            df_cli_view["Nome"].str.lower().str.contains(termo, na=False)
            | df_cli_view["ID_Cliente"].str.lower().str.contains(termo, na=False)
            | df_cli_view["Telefone"].astype(str).str.lower().str.contains(termo, na=False)
        ]

    if df_cli_view.empty:
        st.warning("Nenhum cliente corresponde ao filtro informado.")
        return

    opcoes_cli = [
        f"{r['ID_Cliente']} — {r['Nome']} ({r['Telefone']})"
        for _, r in df_cli_view.iterrows()
    ]
    sel_cli = c_sel.selectbox("Cliente:", opcoes_cli, key=f"sel_cli_{contexto_key}")
    cli_row = df_cli_view.iloc[opcoes_cli.index(sel_cli)]
    id_cli = str(cli_row["ID_Cliente"])

    maquinas_cli, passagens_cli = carregar_historico_cliente(id_cli)

    status_encerrados = {"Entregue / Retirado", "Orçamento Recusado"}
    em_andamento_qtd = int((~passagens_cli["Status"].isin(status_encerrados)).sum()) if not passagens_cli.empty else 0

    total_orcado = 0.0
    if not passagens_cli.empty:
        validos = passagens_cli[passagens_cli["Status"] != "Orçamento Recusado"]
        total_orcado = float(pd.to_numeric(validos["Valor_Orcamento"], errors="coerce").fillna(0.0).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Máquinas", len(maquinas_cli))
    m2.metric("Passagens", len(passagens_cli))
    m3.metric("Em Andamento", em_andamento_qtd)
    m4.metric("Total Orçado", fmt_valor(total_orcado))

    altura_tab = 160 if compacto else 220
    st.markdown("**🚜 Máquinas do Cliente**")
    if maquinas_cli.empty:
        st.info("Este cliente ainda não possui máquinas cadastradas.")
    else:
        st.dataframe(
            maquinas_cli[["ID", "Modelo", "Total_Passagens", "Ultimo_Status", "Data_Hora_Cadastro"]],
            use_container_width=True,
            hide_index=True,
            height=altura_tab,
        )

    st.markdown("**🗂️ Histórico de Passagens**")
    if passagens_cli.empty:
        st.info("Nenhuma passagem registrada para as máquinas deste cliente.")
        return

    col_f1, col_f2 = st.columns(2)
    ids_maq_cli = ["Todas"] + sorted(maquinas_cli["ID"].astype(str).unique().tolist())
    status_cli = ["Todos"] + sorted(passagens_cli["Status"].dropna().astype(str).unique().tolist())

    filtro_maq = col_f1.selectbox("Máquina:", ids_maq_cli, key=f"f_maq_{contexto_key}")
    filtro_st = col_f2.selectbox("Status:", status_cli, key=f"f_st_{contexto_key}")

    passagens_filtradas = passagens_cli.copy()
    if filtro_maq != "Todas":
        passagens_filtradas = passagens_filtradas[passagens_filtradas["ID_Maquina"].astype(str) == filtro_maq]
    if filtro_st != "Todos":
        passagens_filtradas = passagens_filtradas[passagens_filtradas["Status"] == filtro_st]

    if passagens_filtradas.empty:
        st.info("Nenhuma passagem encontrada com os filtros selecionados.")
        return

    st.dataframe(
        passagens_filtradas[[
            "ID_Passagem",
            "ID_Maquina",
            "Modelo",
            "Status",
            "Valor_Orcamento",
            "Data_Hora_Entrada",
            "Data_Hora_Saida",
        ]],
        use_container_width=True,
        hide_index=True,
        height=altura_tab,
    )

    sel_pass_cli = st.selectbox(
        "Ver cronologia/laudo da passagem:",
        list(passagens_filtradas["ID_Passagem"]),
        format_func=lambda pid: f"Passagem #{pid} — Máq. {passagens_filtradas[passagens_filtradas['ID_Passagem'] == pid].iloc[0]['ID_Maquina']} ({passagens_filtradas[passagens_filtradas['ID_Passagem'] == pid].iloc[0]['Status']})",
        key=f"det_p_cli_{contexto_key}",
    )
    p = passagens_filtradas[passagens_filtradas["ID_Passagem"] == sel_pass_cli].iloc[0]
    st.caption(
        f"**Laudo:** {fmt_data(p.get('Descricao_Laudo'))} | **Anomalias:** {fmt_data(p.get('Anomalias'), 'Nenhuma')} | "
        f"**Mecânicos:** {fmt_data(p.get('Mecanico_Laudo'), 'Pendente')} / {fmt_data(p.get('Mecanico_Execucao'), 'Pendente')}"
    )
    st.markdown(renderizar_cronologia_texto(p))


# ---------------------------------------------------------
# SISTEMA DE LOGIN
# ---------------------------------------------------------
st.sidebar.markdown("### 🔐 Autenticação de Usuário")

if st.session_state.usuario_logado is None:
    st.sidebar.subheader("Fazer Login no Sistema")

    with st.sidebar.form("form_login"):
        user_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        btn_login = st.form_submit_button("Entrar")

        if btn_login:
            df_usuarios = carregar_dados("usuarios")
            match = df_usuarios[
                (df_usuarios["Usuario"] == user_input.strip())
                & (df_usuarios["Senha"] == senha_input.strip())
            ]
            if not match.empty:
                st.session_state.usuario_logado = match.iloc[0]["Nome"]
                st.session_state.perfil_logado = match.iloc[0]["Perfil"]
                st.session_state.flash_sucesso = "Login efetuado com sucesso!"
                registrar_log("LOGIN", f"Usuário '{user_input.strip()}' ({match.iloc[0]['Nome']}) entrou no sistema.")
                st.rerun()
            else:
                registrar_log("LOGIN_FALHA", f"Tentativa de login inválida com usuário '{user_input.strip()}'.")
                st.error("Usuário ou senha incorretos.")

    st.info("👈 Digite suas credenciais para acessar o sistema.")
    st.stop()
else:
    st.sidebar.success(
        f"Conectado: **{st.session_state.usuario_logado}**\n\nPerfil: *{st.session_state.perfil_logado}*"
    )

    if st.sidebar.button("Sair (Logout)"):
        nome_saindo = st.session_state.usuario_logado
        st.session_state.usuario_logado = None
        st.session_state.perfil_logado = None
        registrar_log("LOGOUT", f"Usuário '{nome_saindo}' encerrou a sessão.")
        st.rerun()

st.sidebar.markdown("---")


# ---------------------------------------------------------
# NAVEGAÇÃO ADAPTATIVA (MECÂNICO: SUPERIOR NO PC / LATERAL NO MOBILE)
# ---------------------------------------------------------
def navegar_telas(opcoes_telas, chave_estado):
    tela_atual = st.session_state.get(chave_estado, opcoes_telas[0])
    if tela_atual not in opcoes_telas:
        tela_atual = opcoes_telas[0]
        st.session_state[chave_estado] = tela_atual

    st.markdown('<div class="nav-desktop-only">', unsafe_allow_html=True)
    st.markdown('<div class="painel-nav-desktop-label">🧭 Painel Superior de Navegação</div>', unsafe_allow_html=True)
    cols = st.columns(len(opcoes_telas))
    for idx, nome_tela in enumerate(opcoes_telas):
        ativa = nome_tela == tela_atual
        rotulo = f"🟡 {nome_tela}" if ativa else nome_tela
        if cols[idx].button(rotulo, key=f"top_nav_{chave_estado}_{idx}", use_container_width=True):
            st.session_state[chave_estado] = nome_tela
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="nav-mobile-only">📱 Tela atual: <b>{tela_atual}</b> — Abra o menu lateral (<b>☰</b> ou <b>&gt;</b>) para navegar entre as telas.</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("### 🧭 Navegação entre Telas")
    for idx, nome_tela in enumerate(opcoes_telas):
        ativa = nome_tela == tela_atual
        rotulo_side = f"🟡 {nome_tela}" if ativa else nome_tela
        if st.sidebar.button(rotulo_side, key=f"side_nav_{chave_estado}_{idx}", use_container_width=True):
            st.session_state[chave_estado] = nome_tela
            st.rerun()

    st.sidebar.markdown("---")
    return st.session_state[chave_estado]


# ---------------------------------------------------------
# CENTRAL DE NOTIFICAÇÕES (Lidas do SQL)
# ---------------------------------------------------------
df_passagens_notif = carregar_dados("passagens_oficina")

notif_pendentes_sec = len(
    df_passagens_notif[
        df_passagens_notif["Status"].isin([
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)",
        ])
    ]
) if not df_passagens_notif.empty else 0

notif_envio_cliente_sec = len(
    df_passagens_notif[
        df_passagens_notif["Status"] == "Aguardando Envio ao Cliente"
    ]
) if not df_passagens_notif.empty else 0

notif_falta_pecas_sec = len(
    df_passagens_notif[
        df_passagens_notif["Status"] == "Aguardando Precificação (Falta Peças no Estoque)"
    ]
) if not df_passagens_notif.empty else 0

notif_notificar_conclusao_sec = len(
    df_passagens_notif[
        df_passagens_notif["Status"] == "Serviço Concluído (Aguardando Notificação ao Cliente)"
    ]
) if not df_passagens_notif.empty else 0

notif_concluidas_sec = len(
    df_passagens_notif[
        df_passagens_notif["Status"] == "Serviço Concluído (Aguardando Retirada)"
    ]
) if not df_passagens_notif.empty else 0

notif_aprovados_oficina = len(
    df_passagens_notif[
        df_passagens_notif["Status"].isin(["Cliente Aprovou (Pronto para Iniciar)", "Aguardando Peças"])
    ]
) if not df_passagens_notif.empty else 0

st.sidebar.subheader("🔔 Notificações do Sistema")
if st.session_state.perfil_logado == "Secretaria (Administração)":
    if notif_pendentes_sec > 0:
        st.sidebar.warning(f"📥 **{notif_pendentes_sec}** orçamento(s) para precificação.")
    if notif_envio_cliente_sec > 0:
        st.sidebar.info(f"📤 **{notif_envio_cliente_sec}** orçamento(s) para enviar ao cliente.")
    if notif_falta_pecas_sec > 0:
        st.sidebar.error(f"🚨 **{notif_falta_pecas_sec}** com falta de peças.")
    if notif_notificar_conclusao_sec > 0:
        st.sidebar.warning(f"📲 **{notif_notificar_conclusao_sec}** concluído(s) para notificar.")
    if notif_concluidas_sec > 0:
        st.sidebar.success(f"🎉 **{notif_concluidas_sec}** aguardando retirada.")
    if (
        notif_pendentes_sec == 0
        and notif_envio_cliente_sec == 0
        and notif_falta_pecas_sec == 0
        and notif_notificar_conclusao_sec == 0
        and notif_concluidas_sec == 0
    ):
        st.sidebar.info("Nenhuma pendência no momento.")

elif st.session_state.perfil_logado == "Mecânico (Oficina)":
    if notif_aprovados_oficina > 0:
        st.sidebar.success(f"✅ **{notif_aprovados_oficina}** serviço(s) aprovado(s)/aguardando peças!")
    else:
        st.sidebar.info("Nenhuma nova notificação.")

st.sidebar.markdown("---")


def exibir_notificacoes_mecanico_fixas():
    if st.session_state.perfil_logado != "Mecânico (Oficina)":
        return

    df_p = carregar_dados("passagens_oficina")
    if df_p.empty:
        return

    aprovadas = df_p[df_p["Status"] == "Cliente Aprovou (Pronto para Iniciar)"]
    aguard_pecas = df_p[df_p["Status"] == "Aguardando Peças"]
    em_bancada = df_p[df_p["Status"] == "Em Manutenção (Na Bancada)"]

    if len(aprovadas) > 0 or len(aguard_pecas) > 0 or len(em_bancada) > 0:
        partes = []
        if len(aprovadas) > 0:
            ids_ap = ", ".join(aprovadas["ID_Maquina"].astype(str).tolist())
            partes.append(f"**{len(aprovadas)}** aprovado(s) para iniciar (Máq: {ids_ap})")
        if len(aguard_pecas) > 0:
            ids_pc = ", ".join(aguard_pecas["ID_Maquina"].astype(str).tolist())
            partes.append(f"**{len(aguard_pecas)}** aguardando peças (Máq: {ids_pc})")
        if len(em_bancada) > 0:
            ids_bc = ", ".join(em_bancada["ID_Maquina"].astype(str).tolist())
            partes.append(f"**{len(em_bancada)}** na bancada (Máq: {ids_bc})")

        st.info("🔔 **Notificações da Oficina:** " + " • ".join(partes))


def renderizar_ficha_completa_maquina(maq_info):
    id_maq = str(maq_info["ID"])
    df_p = obter_passagens_maquina(id_maq)
    ultima = df_p.iloc[0] if not df_p.empty else None

    status_atual = ultima["Status"] if ultima is not None else "Sem Passagem Aberta"
    laudo_atual = ultima["Descricao_Laudo"] if ultima is not None else "N/A"
    anomalias_atual = ultima["Anomalias"] if ultima is not None else "Nenhuma"
    valor_atual = float(ultima["Valor_Orcamento"]) if ultima is not None else 0.0
    mec_laudo = fmt_data(ultima.get("Mecanico_Laudo") if ultima is not None else None, "N/A")
    mec_exec = fmt_data(ultima.get("Mecanico_Execucao") if ultima is not None else None, "N/A")
    cronologia_html = renderizar_cronologia_html(ultima) if ultima is not None else "<hr><p><i>Nenhuma passagem registrada para esta máquina ainda.</i></p>"

    st.markdown(
        f"""
        <div style="border: 2px solid #1D5FA7; border-left: 6px solid #F5B700; padding: 14px; border-radius: 10px; background-color: #FFFFFF; color: #162436; font-size: 0.9rem;">
            <h4 style="margin-top: 0; margin-bottom: 6px; color: #0F3D75;">📄 Ficha Técnica (ID: {maq_info['ID']}) — {maq_info['Modelo']}</h4>
            <p style="margin: 3px 0;"><b>👤 Cliente:</b> {maq_info['Cliente_Nome']} ({maq_info.get('ID_Cliente', 'N/A')} | Tel: {maq_info['Telefone']}) • <b>Passagens:</b> {len(df_p)}</p>
            <p style="margin: 3px 0;"><b>📌 Status Atual:</b> <span style="color: #0F3D75; background-color: #FFF8DB; padding: 1px 7px; border-radius: 5px; border: 1px solid #F5B700; font-weight: bold;">{status_atual}</span> • <b>Orçamento:</b> {fmt_valor(valor_atual)}</p>
            <p style="margin: 3px 0;"><b>🛠️ Laudo:</b> {laudo_atual} | <b>⚠️ Anomalias:</b> {anomalias_atual}</p>
            <p style="margin: 3px 0;"><b>✍️ Mec. Laudo:</b> {mec_laudo} | <b>⚙️ Mec. Execução:</b> {mec_exec}</p>
            {cronologia_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    exibir_banco_passagens_maquina(id_maq)


# ---------------------------------------------------------
# FUNÇÃO AUXILIAR DE BUSCA, CONSULTA E LEITOR DE QR CODE TRASEIRO
# ---------------------------------------------------------
def renderizar_tabela_com_busca(titulo="📊 Visão Geral das Máquinas e Passagens", compacto=False):
    if not compacto:
        st.subheader(titulo)
    df_maq_base = carregar_dados("maquinas")
    if df_maq_base.empty:
        st.info("Nenhuma máquina cadastrada no sistema.")
        return

    df_maq = carregar_visao_consolidada_passagens()
    altura_tabela = 210 if compacto else 320

    tab_busca_txt, tab_ficha_id, tab_scan_qr = st.tabs([
        "🔍 Lista & Filtro",
        "📋 Ficha & Passagens",
        "📷 Leitor QR",
    ])

    with tab_busca_txt:
        termo_busca = st.text_input(
            "Filtrar por Cliente, ID da Máquina, Modelo ou Status:",
            key=f"busca_{titulo}_{compacto}",
        )

        df_exibicao = df_maq.copy()
        if termo_busca:
            termo = termo_busca.lower()
            df_exibicao = df_exibicao[
                df_exibicao["Cliente_Nome"].str.lower().str.contains(termo, na=False)
                | df_exibicao["ID"].str.lower().str.contains(termo, na=False)
                | df_exibicao["Modelo"].str.lower().str.contains(termo, na=False)
                | df_exibicao["Status"].str.lower().str.contains(termo, na=False)
            ]

        st.dataframe(
            df_exibicao[[
                "ID",
                "Cliente_Nome",
                "Modelo",
                "ID_Passagem",
                "Status",
                "Valor_Orcamento",
                "Data_Hora_Entrada",
            ]],
            use_container_width=True,
            hide_index=True,
            height=altura_tabela,
        )

    with tab_ficha_id:
        opcoes_det = ["-- Selecionar Máquina --"] + [
            f"{r['ID']} — {r['Modelo']} ({r['Cliente_Nome']})"
            for _, r in df_maq_base.iterrows()
        ]
        sel_det = st.selectbox(
            "Selecione a máquina:",
            opcoes_det,
            key=f"detalhe_{titulo}_{compacto}",
        )
        if sel_det != "-- Selecionar Máquina --":
            id_detalhe = sel_det.split(" — ")[0]
            row_maq = df_maq_base[df_maq_base["ID"] == id_detalhe].iloc[0]
            renderizar_ficha_completa_maquina(row_maq)

            if st.session_state.perfil_logado == "Secretaria (Administração)":
                if st.button("🗑️ Excluir Máquina e Histórico", key=f"btn_exc_{id_detalhe}_{compacto}"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM passagens_oficina WHERE ID_Maquina = ?", (str(id_detalhe),))
                    cursor.execute("DELETE FROM maquinas WHERE ID = ?", (str(id_detalhe),))
                    conn.commit()
                    conn.close()
                    registrar_log("EXCLUIR_MAQUINA", f"Máquina ID {id_detalhe} e suas passagens removidas do cadastro.")
                    st.session_state.flash_sucesso = f"Máquina {id_detalhe} removida com sucesso!"
                    st.rerun()

    with tab_scan_qr:
        foto_capturada = back_camera_input(key=f"back_cam_{titulo}_{compacto}")
        if foto_capturada is not None:
            bytes_img = foto_capturada.getvalue()
            np_arr = np.frombuffer(bytes_img, np.uint8)
            img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            detector = cv2.QRCodeDetector()
            codigo_lido, _, _ = detector.detectAndDecode(img_cv)

            if codigo_lido:
                st.success(f"🎯 QR Code Lido: **{codigo_lido}**")
                maq_encontrada = df_maq_base[
                    df_maq_base["QR_Code"].str.contains(codigo_lido, case=False, na=False)
                    | df_maq_base["ID"].str.contains(codigo_lido, case=False, na=False)
                ]
                if not maq_encontrada.empty:
                    renderizar_ficha_completa_maquina(maq_encontrada.iloc[0])
                else:
                    st.warning(f"⚠️ Código '{codigo_lido}' não encontrado.")
            else:
                st.error("❌ Nenhum QR Code nítido detectado.")


# ---------------------------------------------------------
# VISÃO 1: MECÂNICO (Dispositivo Móvel / Oficina)
# ---------------------------------------------------------
if st.session_state.perfil_logado == "Mecânico (Oficina)":
    st.subheader(f"📱 Módulo da Oficina — Mecânico: {st.session_state.usuario_logado}")

    exibir_notificacoes_mecanico_fixas()

    telas_mecanico = [
        "Entrada / Passagens",
        "Etiqueta QR Code",
        "Laudo Técnico",
        "Execução",
        "Máquinas e Passagens",
        "Histórico por Cliente",
    ]
    tela_ativa = navegar_telas(telas_mecanico, "tela_mecanico")

    if tela_ativa == "Entrada / Passagens":
        st.subheader("📝 Registrar Máquina e Passagens na Oficina")

        df_cli = carregar_dados("clientes")
        opcoes_clientes = (
            ["-- Selecionar Cliente Existente --"]
            + list(df_cli["Nome"] + " (" + df_cli["Telefone"] + ")")
            + ["+ Cadastrar Novo Cliente"]
        )

        cliente_sel = st.selectbox("Proprietário da Máquina:", opcoes_clientes)

        id_cli_final = None
        nome_cli_final = ""
        tel_cli_final = ""

        if cliente_sel == "+ Cadastrar Novo Cliente":
            with st.form("form_novo_cliente", clear_on_submit=True):
                novo_nome = st.text_input("Nome Completo do Cliente")
                novo_tel = st.text_input("Telefone (Apenas Números com DDD, ex: 21999998888)")
                btn_cli = st.form_submit_button("Salvar Cliente")

                if btn_cli:
                    tel_valido = validar_telefone(novo_tel)
                    if not novo_nome.strip():
                        st.error("O nome do cliente é obrigatório.")
                    elif not tel_valido:
                        st.error("Telefone inválido! Digite apenas números contendo o DDD (10 ou 11 dígitos).")
                    else:
                        novo_id_cli = f"CLI-{len(df_cli) + 1:03d}"
                        novo_c = pd.DataFrame([
                            {
                                "ID_Cliente": novo_id_cli,
                                "Nome": novo_nome.strip(),
                                "Telefone": tel_valido,
                            }
                        ])
                        df_cli = pd.concat([df_cli, novo_c], ignore_index=True)
                        salvar_dataframe(df_cli, "clientes")
                        registrar_log("CADASTRO_CLIENTE", f"Cliente '{novo_nome.strip()}' ({novo_id_cli}, tel {tel_valido}) cadastrado.")
                        st.session_state.flash_sucesso = f"Cliente {novo_nome} cadastrado com sucesso!"
                        st.rerun()

        elif cliente_sel != "-- Selecionar Cliente Existente --":
            nome_cli_final = cliente_sel.split(" (")[0]
            cli_row = df_cli[df_cli["Nome"] == nome_cli_final].iloc[0]
            id_cli_final = cli_row["ID_Cliente"]
            tel_cli_final = cli_row["Telefone"]

        st.markdown("---")
        modo_entrada = st.selectbox(
            "Modo de Registro:",
            [
                "Cadastrar Nova Máquina (com ou sem abertura imediata de passagem)",
                "Abrir Nova Passagem para Máquina Já Cadastrada",
            ],
        )

        if modo_entrada == "Cadastrar Nova Máquina (com ou sem abertura imediata de passagem)":
            with st.form("form_mec_cadastro", clear_on_submit=True):
                modelo = st.text_input("Modelo / Descrição do Equipamento")
                codigo_manual = st.text_input(
                    "Código da Máquina (Opcional: Deixe em branco para gerar automático)"
                )
                obs_cadastro = st.text_area("Observações de Cadastro / Recepção")
                abrir_passagem_agora = st.checkbox(
                    "Abrir 1ª passagem na oficina imediatamente (se desmarcado, a máquina fica com 0 passagens)",
                    value=True,
                )

                submitted = st.form_submit_button("Registrar Máquina")

                if submitted:
                    if not id_cli_final:
                        st.error("Por favor, selecione um cliente proprietário válido antes de salvar.")
                    elif not modelo.strip():
                        st.error("Preencha o modelo da máquina.")
                    else:
                        codigo_num = codigo_manual.strip() if codigo_manual.strip() != "" else f"{random.randint(1000, 9999)}"
                        qr_gerado = f"QR-EQP-{codigo_num}"
                        data_hora_atual = agora_str()

                        df_maq = carregar_dados("maquinas")
                        if not df_maq.empty and codigo_num in df_maq["ID"].astype(str).values:
                            st.error(f"Já existe uma máquina cadastrada com o código {codigo_num}!")
                        else:
                            nova_maq = {
                                "ID": str(codigo_num),
                                "QR_Code": qr_gerado,
                                "ID_Cliente": id_cli_final,
                                "Cliente_Nome": nome_cli_final,
                                "Telefone": tel_cli_final,
                                "Modelo": modelo.strip(),
                                "Data_Hora_Cadastro": data_hora_atual,
                                "Obs_Cadastro": obs_cadastro,
                            }
                            df_maq = pd.concat([df_maq, pd.DataFrame([nova_maq])], ignore_index=True)
                            salvar_dataframe(df_maq, "maquinas")

                            if abrir_passagem_agora:
                                id_pass = criar_passagem(str(codigo_num), data_entrada=data_hora_atual)
                                registrar_log(
                                    "ENTRADA_MAQUINA_PASSAGEM",
                                    f"Máquina ID {codigo_num} ({modelo.strip()}) cadastrada para '{nome_cli_final}' com passagem #{id_pass} em {data_hora_atual}.",
                                )
                                st.session_state.flash_sucesso = (
                                    f"Máquina ID {codigo_num} cadastrada e passagem #{id_pass} aberta em {data_hora_atual}!"
                                )
                            else:
                                registrar_log(
                                    "CADASTRO_MAQUINA_SEM_PASSAGEM",
                                    f"Máquina ID {codigo_num} ({modelo.strip()}) cadastrada para '{nome_cli_final}' sem passagem aberta (0 passagens).",
                                )
                                st.session_state.flash_sucesso = (
                                    f"Máquina ID {codigo_num} cadastrada com 0 passagens abertas!"
                                )
                            st.rerun()

        else:
            df_maq_exist = carregar_dados("maquinas")
            if df_maq_exist.empty:
                st.info("Nenhuma máquina cadastrada ainda.")
            else:
                if id_cli_final:
                    df_filtrada = df_maq_exist[df_maq_exist["ID_Cliente"] == id_cli_final]
                    if df_filtrada.empty:
                        st.warning("Este cliente não possui máquinas cadastradas. Exibindo todas as máquinas:")
                        df_filtrada = df_maq_exist
                else:
                    df_filtrada = df_maq_exist

                opcoes_maq = [
                    f"{r['ID']} — {r['Modelo']} (Cliente: {r['Cliente_Nome']})"
                    for _, r in df_filtrada.iterrows()
                ]
                maq_sel = st.selectbox("Selecione a Máquina:", opcoes_maq)
                id_maq_sel = maq_sel.split(" — ")[0]

                exibir_banco_passagens_maquina(id_maq_sel, "Passagens Anteriores desta Máquina")

                if st.button("➕ Abrir Nova Passagem na Oficina para esta Máquina"):
                    hora_ent = agora_str()
                    id_pass = criar_passagem(id_maq_sel, data_entrada=hora_ent)
                    registrar_log(
                        "NOVA_PASSAGEM",
                        f"Nova passagem #{id_pass} aberta para máquina ID {id_maq_sel} em {hora_ent}.",
                    )
                    st.session_state.flash_sucesso = (
                        f"Nova passagem #{id_pass} aberta para a máquina ID {id_maq_sel} em {hora_ent}!"
                    )
                    st.rerun()

    elif tela_ativa == "Etiqueta QR Code":
        st.subheader("🖨️ Geração de QR Code Real & Impressão Direta")
        df_maq = carregar_dados("maquinas")
        if df_maq.empty:
            st.info("Nenhuma máquina cadastrada para gerar etiquetas.")
        else:
            maq_etiqueta_id = st.selectbox("Selecione a máquina para gerar a etiqueta:", df_maq["ID"])
            maq_info = df_maq[df_maq["ID"] == maq_etiqueta_id].iloc[0]

            conteudo_qrcode = f"{maq_info['ID']}"
            bytes_qrcode = gerar_imagem_qrcode(conteudo_qrcode)

            st.markdown("---")
            st.markdown(
                f"""
                <style>
                    @media print {{
                        body * {{
                            visibility: hidden;
                        }}
                        #etiqueta-print, #etiqueta-print * {{
                            visibility: visible;
                        }}
                        #etiqueta-print {{
                            position: absolute;
                            left: 0;
                            top: 0;
                            width: 100%;
                        }}
                    }}
                </style>

                <div id="etiqueta-print" style="border: 2px dashed #1D5FA7; padding: 20px; border-radius: 10px; width: 320px; background-color: #FFFFFF; color: #0F3D75; text-align: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; font-size: 18px; color: #0F3D75;">🔧 OFICINA CONECTADA</h3>
                    <hr style="border: 1px solid #F5B700; margin: 10px 0;">
                    <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Cliente:</b> {maq_info['Cliente_Nome']}</p>
                    <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Modelo:</b> {maq_info['Modelo']}</p>
                    <p style="font-size: 12px; margin: 4px 0; text-align: left;"><b>Cadastro:</b> {fmt_data(maq_info.get('Data_Hora_Cadastro'))}</p>
                    <div style="margin: 10px 0;">
                        <img src="data:image/png;base64,{__import__('base64').b64encode(bytes_qrcode).decode()}" width="160px" />
                    </div>
                    <h2 style="margin: 0; color: #0F3D75; background-color: #FFF8DB; border: 1px solid #F5B700; border-radius: 6px; padding: 4px; font-size: 22px;">ID: {maq_info['ID']}</h2>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <button onclick="window.print();" style="background-color: #0F3D75; color: #FFD166; padding: 10px 20px; border: 2px solid #F5B700; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px;">
                    🖨️ Imprimir Etiqueta Diretamente
                </button>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("---")

    elif tela_ativa == "Laudo Técnico":
        st.subheader("🛠️ Diagnóstico, Exclusão/Alteração e Envio de Laudo")

        df_consolidado = carregar_visao_consolidada_passagens()
        editaveis = df_consolidado[
            df_consolidado["ID_Passagem"].notna()
            & df_consolidado["Status"].isin([
                "Aguardando Avaliação Técnica",
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)",
            ])
        ]

        if editaveis.empty:
            st.info("Não há passagens disponíveis para alteração ou cadastro de laudo no momento.")
        else:
            opcoes_laudo = [
                f"Máquina {r['ID']} (Passagem #{int(r['ID_Passagem'])}) — {r['Cliente_Nome']} [{r['Modelo']}]"
                for _, r in editaveis.iterrows()
            ]
            sel_laudo = st.selectbox("Selecione a Máquina / Passagem:", opcoes_laudo)
            row_sel = editaveis.iloc[opcoes_laudo.index(sel_laudo)]
            eqp_id = str(row_sel["ID"])
            id_pass = int(row_sel["ID_Passagem"])

            st.write(
                f"**Passagem:** #{id_pass} | **Cliente:** {row_sel['Cliente_Nome']} | **Modelo:** {row_sel['Modelo']} | **Status Atual:** {row_sel['Status']}"
            )

            if row_sel["Status"] in [
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)",
            ]:
                if st.button("🗑️ Excluir / Redefinir este Laudo (Corrigir Erro)"):
                    atualizar_passagem(id_pass, {
                        "Descricao_Laudo": "Pendente",
                        "Anomalias": "Nenhuma",
                        "Pecas_Solicitadas": json.dumps([]),
                        "Mecanico_Laudo": "Pendente",
                        "Data_Hora_Laudo": "Pendente",
                        "Status": "Aguardando Avaliação Técnica",
                    })
                    registrar_log("REDEFINIR_LAUDO", f"Laudo da passagem #{id_pass} (Máquina ID {eqp_id}) redefinido.")
                    st.session_state.flash_sucesso = "Laudo redefinido com sucesso! Agora você pode preenchê-lo novamente."
                    st.rerun()

            st.markdown("### Selecionar Peças para o Orçamento")
            df_est = carregar_dados("estoque")
            opcoes_pecas = [
                f"{row['Nome']} (Estoque: {row['Quantidade']})"
                for _, row in df_est.iterrows()
            ]

            peca_selecionada = st.selectbox("Escolha a peça do almoxarifado:", opcoes_pecas)
            qtd_peca = st.number_input("Quantidade necessária:", min_value=1, value=1, step=1)

            if "carrinho_pecas" not in st.session_state:
                st.session_state.carrinho_pecas = []

            if st.button("➕ Adicionar Peça"):
                nome_peca_limpo = peca_selecionada.split(" (Estoque:")[0]
                estoque_item = df_est[df_est["Nome"] == nome_peca_limpo].iloc[0]

                st.session_state.carrinho_pecas.append({
                    "peca": nome_peca_limpo,
                    "qtd": qtd_peca,
                    "preco_unit": estoque_item["Preco_Unitario"],
                })

                if qtd_peca > estoque_item["Quantidade"]:
                    st.warning(
                        f"⚠️ Aviso: A peça '{nome_peca_limpo}' está em falta no estoque (Estoque atual: {estoque_item['Quantidade']}, Pedido: {qtd_peca})."
                    )
                else:
                    st.success(f"✅ Adicionado: {qtd_peca}x {nome_peca_limpo}")

            if st.session_state.carrinho_pecas:
                st.write("**Peças Selecionadas:**")
                df_carrinho = pd.DataFrame(st.session_state.carrinho_pecas)
                df_carrinho.columns = ["Peça", "Quantidade", "Preço Unitário (R$)"]
                st.dataframe(df_carrinho, use_container_width=True, hide_index=True)

                if st.button("🗑️ Limpar Carrinho de Peças"):
                    st.session_state.carrinho_pecas = []
                    st.rerun()

            st.markdown("---")
            with st.form("form_laudo", clear_on_submit=True):
                laudo = st.text_input(
                    "Descrição Técnica do Serviço:",
                    value=row_sel["Descricao_Laudo"] if row_sel["Descricao_Laudo"] != "Pendente" else "",
                )
                anomalias = st.text_input(
                    "Observações / Anomalias Encontradas:",
                    value=row_sel["Anomalias"] if row_sel["Anomalias"] != "Nenhuma" else "",
                )

                enviar_secretaria = st.form_submit_button("Salvar e Enviar Laudo para Secretaria")

                if enviar_secretaria:
                    if not laudo.strip():
                        st.warning("Descreva o serviço a ser realizado.")
                    else:
                        pecas_sol = st.session_state.carrinho_pecas.copy()
                        falta_no_envio = False

                        for item in pecas_sol:
                            p_nome = item["peca"]
                            p_qtd = item["qtd"]
                            est_disp = df_est[df_est["Nome"] == p_nome]["Quantidade"].values[0]
                            if p_qtd > est_disp:
                                falta_no_envio = True

                        hora_laudo = agora_str()
                        novo_status = (
                            "Aguardando Precificação (Falta Peças no Estoque)"
                            if falta_no_envio
                            else "Aguardando Precificação (Secretaria)"
                        )

                        atualizar_passagem(id_pass, {
                            "Descricao_Laudo": laudo.strip(),
                            "Anomalias": anomalias.strip() if anomalias.strip() else "Nenhuma",
                            "Pecas_Solicitadas": json.dumps(pecas_sol),
                            "Mecanico_Laudo": st.session_state.usuario_logado,
                            "Data_Hora_Laudo": hora_laudo,
                            "Status": novo_status,
                        })

                        registrar_log(
                            "ENVIO_LAUDO_FALTA_PECAS" if falta_no_envio else "ENVIO_LAUDO",
                            f"Laudo enviado na passagem #{id_pass} (Máquina ID {eqp_id}) em {hora_laudo}.",
                        )
                        st.session_state.flash_sucesso = (
                            "Laudo enviado com sucesso! Há peças em falta no estoque; a Secretaria foi avisada."
                            if falta_no_envio
                            else f"Laudo enviado com sucesso por {st.session_state.usuario_logado}!"
                        )
                        st.session_state.carrinho_pecas = []
                        st.rerun()

    elif tela_ativa == "Execução":
        st.subheader("⚙️ Execução e Conclusão de Manutenções")

        df_consolidado = carregar_visao_consolidada_passagens()
        aprovadas_ou_manutencao = df_consolidado[
            df_consolidado["ID_Passagem"].notna()
            & df_consolidado["Status"].isin([
                "Cliente Aprovou (Pronto para Iniciar)",
                "Aguardando Peças",
                "Em Manutenção (Na Bancada)",
            ])
        ]

        if aprovadas_ou_manutencao.empty:
            st.info("Não há máquinas com orçamento aprovado aguardando execução ou em manutenção no momento.")
        else:
            for _, row in aprovadas_ou_manutencao.iterrows():
                id_pass = int(row["ID_Passagem"])
                with st.expander(
                    f"Máquina ID: {row['ID']} (Passagem #{id_pass}) - Cliente: {row['Cliente_Nome']} [{row['Status']}]"
                ):
                    st.write(f"**Modelo:** {row['Modelo']}")
                    st.write(f"**Laudo:** {row['Descricao_Laudo']}")
                    st.write(f"**Mecânico Responsável pelo Orçamento:** {fmt_data(row.get('Mecanico_Laudo'), 'Não informado')}")
                    if row["Anomalias"] != "Nenhuma":
                        st.warning(f"**Anomalias:** {row['Anomalias']}")

                    if row["Status"] == "Aguardando Peças":
                        st.warning("⏳ Esta máquina aguarda peças no estoque para iniciar a manutenção.")
                        if st.button(f"🔄 Verificar Estoque e Iniciar Manutenção (ID {row['ID']})", key=f"rever_pecas_{id_pass}"):
                            hora_inicio = agora_str()
                            atualizar_passagem(id_pass, {
                                "Status": "Em Manutenção (Na Bancada)",
                                "Mecanico_Execucao": st.session_state.usuario_logado,
                                "Data_Hora_Inicio_Servico": hora_inicio,
                            })
                            registrar_log("INICIO_SERVICO", f"Manutenção iniciada na passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_inicio}.")
                            st.session_state.flash_sucesso = "Peças disponíveis! Manutenção iniciada."
                            st.rerun()

                    elif row["Status"] == "Cliente Aprovou (Pronto para Iniciar)":
                        if st.button(f"▶️ Iniciar Manutenção (ID {row['ID']})", key=f"iniciar_{id_pass}"):
                            hora_inicio = agora_str()
                            atualizar_passagem(id_pass, {
                                "Status": "Em Manutenção (Na Bancada)",
                                "Mecanico_Execucao": st.session_state.usuario_logado,
                                "Data_Hora_Inicio_Servico": hora_inicio,
                            })
                            registrar_log("INICIO_SERVICO", f"Manutenção iniciada na passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_inicio}.")
                            st.session_state.flash_sucesso = f"Manutenção iniciada por {st.session_state.usuario_logado}!"
                            st.rerun()

                    elif row["Status"] == "Em Manutenção (Na Bancada)":
                        st.info(f"⚙️ Em execução por: **{fmt_data(row.get('Mecanico_Execucao'), 'N/A')}**")
                        if st.button(f"🏁 Concluir Serviço (ID {row['ID']})", key=f"concluir_{id_pass}"):
                            hora_conclusao = agora_str()
                            atualizar_passagem(id_pass, {
                                "Status": "Serviço Concluído (Aguardando Notificação ao Cliente)",
                                "Data_Hora_Conclusao_Servico": hora_conclusao,
                            })
                            registrar_log(
                                "CONCLUSAO_SERVICO",
                                f"Serviço concluído na passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_conclusao}. Aguardando notificação ao cliente pela Secretaria.",
                            )
                            st.session_state.flash_sucesso = (
                                "Serviço concluído! A Secretaria foi avisada para notificar o cliente."
                            )
                            st.rerun()

    elif tela_ativa == "Máquinas e Passagens":
        renderizar_tabela_com_busca()

    elif tela_ativa == "Histórico por Cliente":
        renderizar_visao_historica_cliente(contexto_key="mecanico")


# ---------------------------------------------------------
# VISÃO 2: SECRETARIA / ADMINISTRAÇÃO (COCKPIT ÚNICO ZERO-SCROLL)
# ---------------------------------------------------------
elif st.session_state.perfil_logado == "Secretaria (Administração)":
    df_maq_tab1 = carregar_visao_consolidada_passagens()
    df_pass_ativas = df_maq_tab1[df_maq_tab1["ID_Passagem"].notna()].copy()
    df_est = carregar_dados("estoque")

    # 1) FAIXA SUPERIOR DE INDICADORES (1 LINHA, 5 KPIS)
    total_precificar = int(
        df_pass_ativas["Status"].isin([
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)",
        ]).sum()
    ) if not df_pass_ativas.empty else 0

    total_cliente_pend = int(
        df_pass_ativas["Status"].isin([
            "Aguardando Envio ao Cliente",
            "Standby (Aguardando Resposta do Cliente)",
        ]).sum()
    ) if not df_pass_ativas.empty else 0

    total_concl_pend = int(
        df_pass_ativas["Status"].isin([
            "Serviço Concluído (Aguardando Notificação ao Cliente)",
            "Serviço Concluído (Aguardando Retirada)",
        ]).sum()
    ) if not df_pass_ativas.empty else 0

    total_est_critico = int((df_est["Quantidade"] <= df_est["Minimo"]).sum()) if not df_est.empty else 0

    receita_ativa = 0.0
    if not df_pass_ativas.empty:
        valid_rec = df_pass_ativas[df_pass_ativas["Status"] != "Orçamento Recusado"]
        receita_ativa = float(pd.to_numeric(valid_rec["Valor_Orcamento"], errors="coerce").fillna(0.0).sum())

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📥 Para Precificar", total_precificar)
    k2.metric("📤 Aguard. Cliente", total_cliente_pend)
    k3.metric("🏁 Notificar / Retirada", total_concl_pend)
    k4.metric("🚨 Estoque Crítico", total_est_critico)
    k5.metric("💰 Volume Orçado", fmt_valor(receita_ativa))

    # 2) PAINEL DUPLO LADO A LADO (EVITA ROLAGEM VERTICAL)
    col_esq, col_dir = st.columns([1.25, 1.15], gap="medium")

    # -----------------------------------------------------
    # COLUNA ESQUERDA: CENTRAL OPERACIONAL DE AÇÃO RÁPIDA (1-2 CLIQUES)
    # -----------------------------------------------------
    with col_esq:
        st.markdown(
            '<div class="cockpit-box-title">⚡ Central de Ação Rápida — Orçamentos & Fluxo de Atendimento</div>',
            unsafe_allow_html=True,
        )

        status_acao_sec = [
            "Aguardando Precificação (Falta Peças no Estoque)",
            "Aguardando Precificação (Secretaria)",
            "Aguardando Envio ao Cliente",
            "Standby (Aguardando Resposta do Cliente)",
            "Serviço Concluído (Aguardando Notificação ao Cliente)",
            "Serviço Concluído (Aguardando Retirada)",
        ]

        fila_sec = df_pass_ativas[df_pass_ativas["Status"].isin(status_acao_sec)].copy()

        etapa_filtro = st.selectbox(
            "Filtrar fila operacional:",
            [
                f"Todas as Pendências ({len(fila_sec)})",
                "1. Precificar Orçamento",
                "2. Enviar Orçamento ao Cliente",
                "3. Aprovação / Reprovação do Cliente",
                "4. Notificar Conclusão ao Cliente",
                "5. Confirmar Saída / Retirada",
            ],
            key="filtro_fila_sec",
        )

        mapa_etapas = {
            "1. Precificar Orçamento": [
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)",
            ],
            "2. Enviar Orçamento ao Cliente": ["Aguardando Envio ao Cliente"],
            "3. Aprovação / Reprovação do Cliente": ["Standby (Aguardando Resposta do Cliente)"],
            "4. Notificar Conclusão ao Cliente": ["Serviço Concluído (Aguardando Notificação ao Cliente)"],
            "5. Confirmar Saída / Retirada": ["Serviço Concluído (Aguardando Retirada)"],
        }

        if etapa_filtro in mapa_etapas:
            fila_filtrada = fila_sec[fila_sec["Status"].isin(mapa_etapas[etapa_filtro])]
        else:
            fila_filtrada = fila_sec

        if fila_filtrada.empty:
            st.success("✅ Nenhuma pendência nesta fila no momento!")
        else:
            st.dataframe(
                fila_filtrada[[
                    "ID_Passagem",
                    "ID",
                    "Cliente_Nome",
                    "Modelo",
                    "Status",
                    "Valor_Orcamento",
                ]],
                use_container_width=True,
                hide_index=True,
                height=175,
            )

            opcoes_pend = [
                f"#{int(r['ID_Passagem'])} | Máq. {r['ID']} ({r['Modelo']}) — {r['Cliente_Nome']} [{r['Status']}]"
                for _, r in fila_filtrada.iterrows()
            ]
            sel_pend = st.selectbox("Selecione o item para agir imediatamente:", opcoes_pend, key="sel_acao_rapida")
            row = fila_filtrada.iloc[opcoes_pend.index(sel_pend)]
            id_pass = int(row["ID_Passagem"])
            st_atual = row["Status"]

            with st.container(border=True):
                c_info1, c_info2 = st.columns([1.4, 1])
                c_info1.markdown(
                    f"**Máquina:** `{row['ID']}` — {row['Modelo']}  \n"
                    f"**Cliente:** {row['Cliente_Nome']} • 📞 `{row['Telefone']}`  \n"
                    f"**Laudo:** {fmt_data(row['Descricao_Laudo'])} | **Anomalias:** {fmt_data(row['Anomalias'], 'Nenhuma')}"
                )
                c_info2.markdown(
                    f"**Status:** `{st_atual}`  \n"
                    f"**Orçamento:** **{fmt_valor(row['Valor_Orcamento'])}**  \n"
                    f"**Mec. Laudo:** {fmt_data(row.get('Mecanico_Laudo'), 'N/A')}"
                )

                # AÇÃO 1: PRECIFICAR
                if st_atual in [
                    "Aguardando Precificação (Secretaria)",
                    "Aguardando Precificação (Falta Peças no Estoque)",
                ]:
                    if st_atual == "Aguardando Precificação (Falta Peças no Estoque)":
                        st.warning("⚠️ Atenção: este laudo possui peça(s) em quantidade acima do estoque atual.")

                    custo_pecas = 0.0
                    try:
                        pecas = json.loads(row["Pecas_Solicitadas"])
                        if pecas:
                            custo_pecas = sum(item["qtd"] * item["preco_unit"] for item in pecas)
                            resumo_p = ", ".join(f"{it['qtd']}x {it['peca']}" for it in pecas)
                            st.caption(f"Peças ({fmt_valor(custo_pecas)}): {resumo_p}")
                    except Exception:
                        pass

                    with st.form(key=f"form_calc_cockpit_{id_pass}", clear_on_submit=True):
                        fc1, fc2 = st.columns([1, 1.2])
                        mao_de_obra = fc1.number_input(
                            "Mão de Obra (R$)",
                            min_value=0.0,
                            value=100.0,
                            step=10.0,
                        )
                        valor_total = custo_pecas + mao_de_obra
                        fc2.markdown(f"**Total Final:** `{fmt_valor(valor_total)}`")
                        if fc2.form_submit_button("✅ Confirmar Cálculo & Liberar Envio", use_container_width=True):
                            atualizar_passagem(id_pass, {
                                "Valor_Orcamento": valor_total,
                                "Status": "Aguardando Envio ao Cliente",
                            })
                            registrar_log(
                                "PRECIFICACAO_ORCAMENTO",
                                f"Passagem #{id_pass} (Máquina ID {row['ID']}) precificada em {fmt_valor(valor_total)}.",
                            )
                            st.session_state.flash_sucesso = f"Orçamento #{id_pass} precificado em {fmt_valor(valor_total)}!"
                            st.rerun()

                # AÇÃO 2: CONFIRMAR ENVIO AO CLIENTE
                elif st_atual == "Aguardando Envio ao Cliente":
                    if st.button(f"📨 Confirmar Envio do Orçamento ao Cliente (#{id_pass})", key=f"env_cli_{id_pass}", use_container_width=True):
                        hora_envio = agora_str()
                        atualizar_passagem(id_pass, {
                            "Data_Hora_Envio_Orcamento": hora_envio,
                            "Status": "Standby (Aguardando Resposta do Cliente)",
                        })
                        registrar_log(
                            "ENVIO_ORCAMENTO_CLIENTE",
                            f"Orçamento da passagem #{id_pass} (Máquina ID {row['ID']}) enviado ao cliente '{row['Cliente_Nome']}' em {hora_envio}.",
                        )
                        st.session_state.flash_sucesso = f"Envio ao cliente confirmado em {hora_envio}!"
                        st.rerun()

                # AÇÃO 3: APROVAR OU REPROVAR
                elif st_atual == "Standby (Aguardando Resposta do Cliente)":
                    st.caption(f"Enviado ao cliente em: {fmt_data(row.get('Data_Hora_Envio_Orcamento'))}")
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Cliente APROVOU", key=f"ap_{id_pass}", use_container_width=True):
                        hora_resp = agora_str()
                        try:
                            pecas_req = json.loads(row["Pecas_Solicitadas"])
                        except Exception:
                            pecas_req = []

                        df_est_up = carregar_dados("estoque")
                        falta_estoque = False
                        for p in pecas_req:
                            p_nome = p["peca"]
                            p_qtd_pedida = p["qtd"]
                            estoque_atual = df_est_up[df_est_up["Nome"] == p_nome]["Quantidade"].values[0]
                            if p_qtd_pedida > estoque_atual:
                                falta_estoque = True
                            else:
                                e_idx = df_est_up[df_est_up["Nome"] == p_nome].index[0]
                                df_est_up.loc[e_idx, "Quantidade"] -= p_qtd_pedida

                        salvar_dataframe(df_est_up, "estoque")

                        if falta_estoque:
                            atualizar_passagem(id_pass, {
                                "Data_Hora_Resposta_Cliente": hora_resp,
                                "Status": "Aguardando Peças",
                            })
                            registrar_log(
                                "CLIENTE_APROVOU_FALTA_PECAS",
                                f"Cliente aprovou passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_resp} ('Aguardando Peças').",
                            )
                            st.session_state.flash_sucesso = "Cliente aprovou ('Aguardando Peças' no estoque)."
                        else:
                            atualizar_passagem(id_pass, {
                                "Data_Hora_Resposta_Cliente": hora_resp,
                                "Status": "Cliente Aprovou (Pronto para Iniciar)",
                            })
                            registrar_log(
                                "CLIENTE_APROVOU",
                                f"Cliente aprovou passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_resp}.",
                            )
                            st.session_state.flash_sucesso = "Aprovado! Peças baixadas e oficina notificada."
                        st.rerun()

                    if b2.button("❌ Cliente REPROVOU", key=f"rec_{id_pass}", use_container_width=True):
                        hora_resp = agora_str()
                        atualizar_passagem(id_pass, {
                            "Data_Hora_Resposta_Cliente": hora_resp,
                            "Status": "Orçamento Recusado",
                        })
                        registrar_log(
                            "CLIENTE_REPROVOU",
                            f"Cliente reprovou passagem #{id_pass} (Máquina ID {row['ID']}) em {hora_resp}.",
                        )
                        st.session_state.flash_sucesso = "Orçamento marcado como recusado pelo cliente."
                        st.rerun()

                # AÇÃO 4: NOTIFICAR CONCLUSÃO AO CLIENTE
                elif st_atual == "Serviço Concluído (Aguardando Notificação ao Cliente)":
                    st.caption(f"Serviço concluído em: {fmt_data(row.get('Data_Hora_Conclusao_Servico'))}")
                    if st.button(f"📲 Confirmar Notificação ao Cliente (#{id_pass})", key=f"notif_conc_{id_pass}", use_container_width=True):
                        hora_notif = agora_str()
                        atualizar_passagem(id_pass, {
                            "Data_Hora_Notificacao_Conclusao": hora_notif,
                            "Status": "Serviço Concluído (Aguardando Retirada)",
                        })
                        registrar_log(
                            "NOTIFICACAO_CONCLUSAO_CLIENTE",
                            f"Cliente '{row['Cliente_Nome']}' notificado da conclusão da passagem #{id_pass} em {hora_notif}.",
                        )
                        st.session_state.flash_sucesso = f"Cliente notificado em {hora_notif}! Aguardando retirada."
                        st.rerun()

                # AÇÃO 5: CONFIRMAR SAÍDA / RETIRADA
                elif st_atual == "Serviço Concluído (Aguardando Retirada)":
                    st.caption(f"Cliente notificado em: {fmt_data(row.get('Data_Hora_Notificacao_Conclusao'))}")
                    if st.button(f"🏁 Confirmar Saída / Retirada da Máquina (#{id_pass})", key=f"retirada_{id_pass}", use_container_width=True):
                        hora_saida = agora_str()
                        atualizar_passagem(id_pass, {
                            "Status": "Entregue / Retirado",
                            "Data_Hora_Saida": hora_saida,
                        })
                        registrar_log(
                            "SAIDA_MAQUINA",
                            f"Saída da passagem #{id_pass} (Máquina ID {row['ID']}) confirmada em {hora_saida}.",
                        )
                        st.session_state.flash_sucesso = f"Saída registrada em {hora_saida}! Ciclo encerrado."
                        st.rerun()

    # -----------------------------------------------------
    # COLUNA DIREITA: CONSULTAS, CLIENTES, ESTOQUE, EQUIPE & LOGS
    # -----------------------------------------------------
    with col_dir:
        st.markdown(
            '<div class="cockpit-box-title">📊 Painel Integrado — Máquinas, Clientes, Estoque & Auditoria</div>',
            unsafe_allow_html=True,
        )

        tab_geral, tab_cli, tab_est, tab_mec, tab_logs = st.tabs([
            "🚜 Máquinas",
            "👤 Clientes",
            "📦 Estoque",
            "👥 Mecânicos",
            "📜 Logs",
        ])

        with tab_geral:
            renderizar_tabela_com_busca("Visão Geral", compacto=True)

        with tab_cli:
            renderizar_visao_historica_cliente(contexto_key="secretaria_cockpit", compacto=True)

        with tab_est:
            criticos = df_est[df_est["Quantidade"] <= df_est["Minimo"]]
            if not criticos.empty:
                nomes_crit = ", ".join(f"{r['Nome']} ({r['Quantidade']}/{r['Minimo']})" for _, r in criticos.iterrows())
                st.warning(f"🚨 Estoque baixo: {nomes_crit}")

            st.dataframe(df_est, use_container_width=True, hide_index=True, height=175)

            sub_est_rep, sub_est_cad, sub_est_exc = st.tabs(["🔄 Repor", "➕ Nova Peça", "🗑️ Excluir"])
            with sub_est_rep:
                with st.form("form_repor_peca_cockpit", clear_on_submit=True):
                    c1, c2 = st.columns([1.5, 1])
                    peca_repor = c1.selectbox("Peça:", df_est["Nome"])
                    qtd_adicionar = c2.number_input("Qtd +:", min_value=1, value=5, step=1)
                    if st.form_submit_button("Confirmar Entrada no Estoque", use_container_width=True):
                        p_idx = df_est[df_est["Nome"] == peca_repor].index[0]
                        df_est.loc[p_idx, "Quantidade"] += qtd_adicionar
                        salvar_dataframe(df_est, "estoque")
                        registrar_log("REPOSICAO_ESTOQUE", f"Adicionadas {qtd_adicionar} unidade(s) de '{peca_repor}'.")
                        st.session_state.flash_sucesso = f"+{qtd_adicionar}x '{peca_repor}' adicionadas!"
                        st.rerun()

            with sub_est_cad:
                with st.form("nova_peca_form_cockpit", clear_on_submit=True):
                    nome_p = st.text_input("Nome da Nova Peça")
                    c1, c2, c3 = st.columns(3)
                    qtd_p = c1.number_input("Qtd", min_value=1, value=10, step=1)
                    min_p = c2.number_input("Mín.", min_value=1, value=3, step=1)
                    preco_p = c3.number_input("R$ Unit.", min_value=0.0, value=50.0, step=5.0)
                    if st.form_submit_button("Salvar Nova Peça", use_container_width=True):
                        if not nome_p.strip():
                            st.warning("Informe o nome da peça.")
                        else:
                            novo_id = f"PEC-{len(df_est) + 1:03d}"
                            nova_p = pd.DataFrame([{
                                "ID_Peca": novo_id,
                                "Nome": nome_p.strip(),
                                "Quantidade": qtd_p,
                                "Minimo": min_p,
                                "Preco_Unitario": preco_p,
                            }])
                            df_est = pd.concat([df_est, nova_p], ignore_index=True)
                            salvar_dataframe(df_est, "estoque")
                            registrar_log("CADASTRO_PECA", f"Peça '{nome_p.strip()}' ({novo_id}) cadastrada.")
                            st.session_state.flash_sucesso = f"Peça '{nome_p}' cadastrada!"
                            st.rerun()

            with sub_est_exc:
                peca_para_excluir = st.selectbox(
                    "Remover peça:",
                    ["-- Selecionar --"] + list(df_est["Nome"]),
                    key="exc_peca_cockpit",
                )
                if peca_para_excluir != "-- Selecionar --":
                    if st.button("⚠️ Confirmar Exclusão", key="btn_exc_peca_cockpit", use_container_width=True):
                        df_est = df_est[df_est["Nome"] != peca_para_excluir]
                        salvar_dataframe(df_est, "estoque")
                        registrar_log("EXCLUIR_PECA", f"Peça '{peca_para_excluir}' removida do estoque.")
                        st.session_state.flash_sucesso = f"Peça '{peca_para_excluir}' removida!"
                        st.rerun()

        with tab_mec:
            df_usr = carregar_dados("usuarios")
            mecanicos_df = df_usr[df_usr["Perfil"] == "Mecânico (Oficina)"]
            st.dataframe(mecanicos_df[["Usuario", "Nome"]], use_container_width=True, hide_index=True, height=145)

            sub_mec_cad, sub_mec_exc = st.tabs(["➕ Novo Mecânico", "🗑️ Remover"])
            with sub_mec_cad:
                with st.form("form_novo_mecanico_cockpit", clear_on_submit=True):
                    nome_mec = st.text_input("Nome Completo")
                    c1, c2 = st.columns(2)
                    user_mec = c1.text_input("Login")
                    senha_mec = c2.text_input("Senha", type="password")
                    if st.form_submit_button("Cadastrar Mecânico", use_container_width=True):
                        if not nome_mec.strip() or not user_mec.strip() or not senha_mec.strip():
                            st.warning("Preencha todos os campos.")
                        elif user_mec.strip() in df_usr["Usuario"].values:
                            st.error("Usuário já existe.")
                        else:
                            novo_mec_df = pd.DataFrame([{
                                "Usuario": user_mec.strip(),
                                "Senha": senha_mec.strip(),
                                "Perfil": "Mecânico (Oficina)",
                                "Nome": nome_mec.strip(),
                            }])
                            df_usr = pd.concat([df_usr, novo_mec_df], ignore_index=True)
                            salvar_dataframe(df_usr, "usuarios")
                            registrar_log("CADASTRO_MECANICO", f"Mecânico '{nome_mec.strip()}' cadastrado.")
                            st.session_state.flash_sucesso = f"Mecânico {nome_mec} cadastrado!"
                            st.rerun()

            with sub_mec_exc:
                mecs_para_remover = list(mecanicos_df["Nome"])
                if mecs_para_remover:
                    mec_escolhido = st.selectbox("Mecânico:", ["-- Selecionar --"] + mecs_para_remover, key="exc_mec_cockpit")
                    if mec_escolhido != "-- Selecionar --":
                        if st.button("⚠️ Remover Acesso", key="btn_exc_mec_cockpit", use_container_width=True):
                            df_usr = df_usr[df_usr["Nome"] != mec_escolhido]
                            salvar_dataframe(df_usr, "usuarios")
                            registrar_log("REMOVER_MECANICO", f"Acesso do mecânico '{mec_escolhido}' removido.")
                            st.session_state.flash_sucesso = f"Acesso de '{mec_escolhido}' removido!"
                            st.rerun()

        with tab_logs:
            df_logs = carregar_dados("logs")
            if df_logs.empty:
                st.info("Nenhum log registrado.")
            else:
                df_logs = df_logs.sort_values("ID_Log", ascending=False)
                c_l1, c_l2 = st.columns(2)
                filtro_acao = c_l1.selectbox(
                    "Ação:",
                    ["Todas"] + sorted(df_logs["Acao"].unique().tolist()),
                    key="filtro_log_cockpit",
                )
                busca_log = c_l2.text_input("Buscar:", key="busca_log_cockpit")

                df_log_view = df_logs.copy()
                if filtro_acao != "Todas":
                    df_log_view = df_log_view[df_log_view["Acao"] == filtro_acao]
                if busca_log.strip():
                    termo_l = busca_log.strip().lower()
                    df_log_view = df_log_view[
                        df_log_view["Usuario"].str.lower().str.contains(termo_l, na=False)
                        | df_log_view["Detalhes"].str.lower().str.contains(termo_l, na=False)
                    ]

                st.dataframe(
                    df_log_view[["ID_Log", "Data_Hora", "Usuario", "Acao", "Detalhes"]],
                    use_container_width=True,
                    hide_index=True,
                    height=195,
                )

                csv_logs = df_log_view.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Exportar Logs (CSV)",
                    data=csv_logs,
                    file_name=f"logs_oficina_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )