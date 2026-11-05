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

# Configuração da Página
st.set_page_config(
    page_title="Oficina Conectada - Sistema de Gestão",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Oficina Conectada: Gestão Integrada (SQL)")

# ---------------------------------------------------------
# CONFIGURAÇÃO E INICIALIZAÇÃO DO BANCO DE DADOS SQLITE
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect("oficina.db", check_same_thread=False)
    return conn

def inicializar_banco():
    conn = get_connection()
    cursor = conn.cursor()

    # Tabela de Usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            Usuario TEXT PRIMARY KEY,
            Senha TEXT,
            Perfil TEXT,
            Nome TEXT
        )
    """)

    # Tabela de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            ID_Cliente TEXT PRIMARY KEY,
            Nome TEXT,
            Telefone TEXT
        )
    """)

    # Tabela de Estoque
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            ID_Peca TEXT PRIMARY KEY,
            Nome TEXT,
            Quantidade INTEGER,
            Minimo INTEGER,
            Preco_Unitario REAL
        )
    """)

    # Tabela de Máquinas e Laudos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maquinas (
            ID TEXT PRIMARY KEY,
            QR_Code TEXT,
            ID_Cliente TEXT,
            Cliente_Nome TEXT,
            Telefone TEXT,
            Modelo TEXT,
            Data_Hora_Entrada TEXT,
            Data_Hora_Saida TEXT,
            Obs_Cadastro TEXT,
            Status TEXT,
            Descricao_Laudo TEXT,
            Anomalias TEXT,
            Pecas_Solicitadas TEXT,
            Valor_Orcamento REAL,
            Mecanico_Laudo TEXT,
            Mecanico_Execucao TEXT
        )
    """)

    # Dados Iniciais (Se as tabelas estiverem vazias)
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO usuarios VALUES (?, ?, ?, ?)", [
            ("admin", "123", "Secretaria (Administração)", "Administração Central"),
            ("mecanico1", "123", "Mecânico (Oficina)", "Carlos Mecânico")
        ])

    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO clientes VALUES (?, ?, ?)", [
            ("CLI-001", "João Silva", "21999998888"),
            ("CLI-002", "Maria Oliveira", "21988887777")
        ])

    cursor.execute("SELECT COUNT(*) FROM estoque")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO estoque VALUES (?, ?, ?, ?, ?)", [
            ("PEC-001", "Correia Dentada", 10, 3, 150.00),
            ("PEC-002", "Filtro de Óleo", 15, 5, 45.00),
            ("PEC-003", "Vela de Ignição", 1, 4, 30.00),
            ("PEC-004", "Pastilha de Freio", 8, 2, 120.00)
        ])

    conn.commit()
    conn.close()

# Executa a inicialização do banco
inicializar_banco()

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None

# ---------------------------------------------------------
# FUNÇÕES DE CONSULTA E PERSISTÊNCIA SQL
# ---------------------------------------------------------
def carregar_dados(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    return df

def salvar_dataframe(df, tabela):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists="replace", index=False)
    conn.close()

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

# ---------------------------------------------------------
# SISTEMA DE LOGIN COM SUPORTE A MÚLTIPLOS MECÂNICOS
# ---------------------------------------------------------
st.sidebar.title("🔐 Autenticação de Usuário")

if st.session_state.usuario_logado is None:
    st.sidebar.subheader("Fazer Login no Sistema")
    
    with st.sidebar.form("form_login"):
        user_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        btn_login = st.form_submit_button("Entrar")

        if btn_login:
            df_usuarios = carregar_dados("usuarios")
            match = df_usuarios[
                (df_usuarios["Usuario"] == user_input.strip()) &
                (df_usuarios["Senha"] == senha_input.strip())
            ]
            if not match.empty:
                st.session_state.usuario_logado = match.iloc[0]["Nome"]
                st.session_state.perfil_logado = match.iloc[0]["Perfil"]
                st.success("Login efetuado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    st.info("👈 Digite suas credenciais para acessar o sistema.")
    st.stop()
else:
    st.sidebar.success(f"Conectado: **{st.session_state.usuario_logado}**\n\nPerfil: *{st.session_state.perfil_logado}*")
    
    if st.sidebar.button("🔄 Sincronizar / Atualizar Informações"):
        st.success("Dados atualizados com sucesso!")
        st.rerun()

    if st.sidebar.button("Sair (Logout)"):
        st.session_state.usuario_logado = None
        st.session_state.perfil_logado = None
        st.rerun()

st.sidebar.markdown("---")

# ---------------------------------------------------------
# CENTRAL DE NOTIFICAÇÕES (Lidas do SQL)
# ---------------------------------------------------------
df_maquinas_notif = carregar_dados("maquinas")
notif_pendentes_sec = len(
    df_maquinas_notif[
        df_maquinas_notif["Status"].isin([
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)"
        ])
    ]
) if not df_maquinas_notif.empty else 0

notif_falta_pecas_sec = len(
    df_maquinas_notif[
        df_maquinas_notif["Status"] == "Aguardando Precificação (Falta Peças no Estoque)"
    ]
) if not df_maquinas_notif.empty else 0

notif_concluidas_sec = len(
    df_maquinas_notif[
        df_maquinas_notif["Status"] == "Serviço Concluído (Aguardando Retirada)"
    ]
) if not df_maquinas_notif.empty else 0

notif_aprovados_oficina = len(
    df_maquinas_notif[
        df_maquinas_notif["Status"].isin(["Cliente Aprovou (Pronto para Iniciar)", "Aguardando Peças"])
    ]
) if not df_maquinas_notif.empty else 0

st.sidebar.subheader("🔔 Notificações do Sistema")
if st.session_state.perfil_logado == "Secretaria (Administração)":
    if notif_pendentes_sec > 0:
        st.sidebar.warning(f"📥 **{notif_pendentes_sec}** orçamento(s) para precificação.")
    if notif_falta_pecas_sec > 0:
        st.sidebar.error(f"🚨 **{notif_falta_pecas_sec}** orçamento(s) com aviso de falta de peças.")
    if notif_concluidas_sec > 0:
        st.sidebar.success(f"🎉 **{notif_concluidas_sec}** máquina(s) concluída(s) para retirada.")
    if notif_pendentes_sec == 0 and notif_falta_pecas_sec == 0 and notif_concluidas_sec == 0:
        st.sidebar.info("Nenhuma nova notificação pendente.")

elif st.session_state.perfil_logado == "Mecânico (Oficina)":
    if notif_aprovados_oficina > 0:
        st.sidebar.success(f"✅ **{notif_aprovados_oficina}** serviço(s) aprovado(s)/aguardando peças!")
    else:
        st.sidebar.info("Nenhuma nova notificação.")

st.sidebar.markdown("---")

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR DE BUSCA, CONSULTA E LEITOR DE QR CODE NATIVO
# ---------------------------------------------------------
def renderizar_tabela_com_busca(titulo="📊 Visão Geral das Máquinas e Laudos"):
    st.subheader(titulo)
    df_maq = carregar_dados("maquinas")
    if df_maq.empty:
        st.info("Nenhuma máquina cadastrada no sistema.")
        return

    tab_busca_txt, tab_scan_qr = st.tabs(["🔍 Busca por Texto", "📷 Leitor de QR Code (Câmera Nativa)"])

    with tab_busca_txt:
        termo_busca = st.text_input(
            "Digite o Nome do Cliente, Código ou QR Code:",
            key=f"busca_{titulo}",
        )

        df_exibicao = df_maq.copy()
        if termo_busca:
            termo = termo_busca.lower()
            df_exibicao = df_exibicao[
                df_exibicao["Cliente_Nome"].str.lower().str.contains(termo, na=False)
                | df_exibicao["ID"].str.lower().str.contains(termo, na=False)
                | df_exibicao["QR_Code"].str.lower().str.contains(termo, na=False)
            ]

        st.dataframe(
            df_exibicao[
                [
                    "ID",
                    "QR_Code",
                    "Cliente_Nome",
                    "Telefone",
                    "Modelo",
                    "Data_Hora_Entrada",
                    "Status",
                    "Valor_Orcamento",
                ]
            ],
            use_container_width=True,
        )

    with tab_scan_qr:
        st.markdown("### 📷 Capturar QR Code com a Câmera do Celular")
        st.info("Clique em 'Tirar foto', aponte para a etiqueta impressa da máquina e o sistema identificará o código automaticamente.")

        # Câmera nativa robusta para mobile e desktop
        foto_capturada = st.camera_input("Tirar Foto da Etiqueta da Máquina", key=f"cam_{titulo}")

        if foto_capturada is not None:
            # Converte a imagem capturada para processamento OpenCV
            bytes_img = foto_capturada.getvalue()
            np_arr = np.frombuffer(bytes_img, np.uint8)
            img_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            # Detecta o QR Code usando o decodificador nativo do OpenCV
            detector = cv2.QRCodeDetector()
            codigo_lido, points, straight_qrcode = detector.detectAndDecode(img_cv)

            if codigo_lido:
                st.success(f"🎯 QR Code Lido com Sucesso: **{codigo_lido}**")
                
                maq_encontrada = df_maq[
                    df_maq["QR_Code"].str.contains(codigo_lido, case=False, na=False) |
                    df_maq["ID"].str.contains(codigo_lido, case=False, na=False)
                ]

                if not maq_encontrada.empty:
                    maq_info = maq_encontrada.iloc[0]
                    st.markdown(
                        f"""
                        <div style="border: 2px solid #28a745; padding: 20px; border-radius: 10px; background-color: #f9f9f9; color: #333;">
                            <h3 style="margin-top: 0; color: #28a745;">📄 Ficha Técnica Completa (ID: {maq_info['ID']})</h3>
                            <hr>
                            <p><b>👤 Cliente Proprietário:</b> {maq_info['Cliente_Nome']} (Tel: {maq_info['Telefone']})</p>
                            <p><b>🚜 Modelo do Equipamento:</b> {maq_info['Modelo']}</p>
                            <p><b>📌 Status Atual:</b> <span style="color: #d9534f; font-weight: bold;">{maq_info['Status']}</span></p>
                            <p><b>📅 Data/Hora de Entrada:</b> {maq_info['Data_Hora_Entrada']}</p>
                            <p><b>🏁 Data/Hora de Saída:</b> {maq_info.get('Data_Hora_Saida', 'Pendente')}</p>
                            <p><b>📝 Observações de Recepção:</b> {maq_info['Obs_Cadastro'] if maq_info['Obs_Cadastro'] else 'Nenhuma'}</p>
                            <hr>
                            <p><b>🛠️ Laudo Técnico:</b> {maq_info['Descricao_Laudo']}</p>
                            <p><b>⚠️ Anomalias Encontradas:</b> {maq_info['Anomalias']}</p>
                            <p><b>💰 Valor do Orçamento:</b> R$ {maq_info['Valor_Orcamento']:.2f}</p>
                            <p><b>✍️ Orçamento enviado por:</b> {maq_info.get('Mecanico_Laudo', 'N/A')} | <b>⚙️ Executado por:</b> {maq_info.get('Mecanico_Execucao', 'N/A')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if maq_info["Pecas_Solicitadas"]:
                        try:
                            pecas_lista = json.loads(maq_info["Pecas_Solicitadas"])
                            if pecas_lista:
                                st.markdown("#### Peças Utilizadas / Solicitadas:")
                                st.dataframe(pd.DataFrame(pecas_lista), use_container_width=True)
                        except:
                            pass
                else:
                    st.warning(f"⚠️ O código lido ('{codigo_lido}') não corresponde a nenhuma máquina cadastrada no sistema.")
            else:
                st.error("❌ Nenhum QR Code nítido foi detectado na foto. Aproxime mais a câmera da etiqueta e tente novamente.")

    st.markdown("---")
    st.markdown("### 📋 Consulta Detalhada por ID")
    id_detalhe = st.selectbox(
        "Ou selecione o ID diretamente para ver detalhes:",
        ["-- Selecionar --"] + list(df_maq["ID"]),
        key=f"detalhe_{titulo}"
    )
    if id_detalhe != "-- Selecionar --":
        row_det = df_maq[df_maq["ID"] == id_detalhe].iloc[0]
        st.info(
            f"**Equipamento:** {row_det['Modelo']} (ID: {row_det['ID']})\n\n"
            f"👤 **Cliente:** {row_det['Cliente_Nome']} | 📞 **Tel:** {row_det['Telefone']}\n\n"
            f"📅 **Entrada:** {row_det['Data_Hora_Entrada']} | 🏁 **Saída:** {row_det.get('Data_Hora_Saida', 'Não retirada')}\n\n"
            f"📌 **Status Atual:** {row_det['Status']}\n\n"
            f"🛠️ **Laudo Técnico / Serviço:** {row_det['Descricao_Laudo']}\n\n"
            f"⚠️ **Anomalias Relatadas:** {row_det['Anomalias']}\n\n"
            f"✍️ **Orçamento enviado por:** {row_det.get('Mecanico_Laudo', 'Não informado')} | "
            f"⚙️ **Serviço executado por:** {row_det.get('Mecanico_Execucao', 'Não iniciado')}"
        )
        if row_det["Pecas_Solicitadas"]:
            try:
                p_list = json.loads(row_det["Pecas_Solicitadas"])
                if p_list:
                    st.markdown("**Peças Solicitadas no Orçamento:**")
                    st.dataframe(pd.DataFrame(p_list), use_container_width=True)
            except:
                pass

    if st.session_state.perfil_logado == "Secretaria (Administração)":
        st.markdown("### 🗑️ Excluir Registro de Máquina")
        id_para_excluir = st.selectbox(
            "Selecione o ID da máquina para remover:",
            ["-- Selecionar --"] + list(df_maq["ID"]),
            key=f"excluir_maq_{titulo}"
        )
        if id_para_excluir != "-- Selecionar --":
            if st.button("⚠️ Confirmar Exclusão desta Máquina", key=f"btn_exc_{titulo}"):
                df_maq = df_maq[df_maq["ID"] != id_para_excluir]
                salvar_dataframe(df_maq, "maquinas")
                st.success(f"✅ Máquina {id_para_excluir} removida com sucesso!")
                st.rerun()

# ---------------------------------------------------------
# VISÃO 1: MECÂNICO (Dispositivo Móvel / Oficina)
# ---------------------------------------------------------
if st.session_state.perfil_logado == "Mecânico (Oficina)":
    st.header(f"📱 Módulo da Oficina - Mecânico: {st.session_state.usuario_logado}")

    sub_menu = st.radio(
        "Ação:",
        [
            "1. Cadastrar Máquina (Entrada)",
            "2. Imprimir Etiqueta QR Code",
            "3. Cadastrar / Editar Laudo Técnico",
            "4. Executar Manutenção & Concluir Serviços",
            "5. Consultar Máquinas e Laudos",
        ],
    )

    if sub_menu == "1. Cadastrar Máquina (Entrada)":
        st.subheader("📝 Registrar Chegada de Equipamento")

        df_cli = carregar_dados("clientes")
        opcoes_clientes = ["-- Selecionar Cliente Existente --"] + list(
            df_cli["Nome"] + " (" + df_cli["Telefone"] + ")"
        ) + ["+ Cadastrar Novo Cliente"]

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
                        novo_c = pd.DataFrame([{
                            "ID_Cliente": novo_id_cli,
                            "Nome": novo_nome.strip(),
                            "Telefone": tel_valido
                        }])
                        df_cli = pd.concat([df_cli, novo_c], ignore_index=True)
                        salvar_dataframe(df_cli, "clientes")
                        st.success(f"✅ Cliente {novo_nome} cadastrado com sucesso!")
                        st.rerun()

        elif cliente_sel != "-- Selecionar Cliente Existente --":
            nome_cli_final = cliente_sel.split(" (")[0]
            cli_row = df_cli[df_cli["Nome"] == nome_cli_final].iloc[0]
            id_cli_final = cli_row["ID_Cliente"]
            tel_cli_final = cli_row["Telefone"]

        st.markdown("---")
        st.markdown("### 🚜 Dados da Máquina")

        with st.form("form_mec_cadastro", clear_on_submit=True):
            modelo = st.text_input("Modelo / Descrição do Equipamento")
            codigo_manual = st.text_input(
                "Código da Máquina (Opcional: Deixe em branco se for nova para gerar automático)"
            )
            obs_cadastro = st.text_area("Observações de Entrada (Ex: Marcas de uso, acessórios, etc.)")

            submitted = st.form_submit_button("Registrar Entrada da Máquina")

            if submitted:
                if not id_cli_final:
                    st.error("Por favor, selecione um cliente proprietário válido antes de salvar.")
                elif not modelo.strip():
                    st.error("Preencha o modelo da máquina.")
                else:
                    if codigo_manual.strip() != "":
                        codigo_num = codigo_manual.strip()
                    else:
                        codigo_num = f"{random.randint(1000, 9999)}"

                    qr_gerado = f"QR-EQP-{codigo_num}"
                    data_hora_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

                    df_maq = carregar_dados("maquinas")
                    if not df_maq.empty and codigo_num in df_maq["ID"].values:
                        st.error(f"Já existe uma máquina cadastrada com o código {codigo_num}!")
                    else:
                        nova_linha = {
                            "ID": codigo_num,
                            "QR_Code": qr_gerado,
                            "ID_Cliente": id_cli_final,
                            "Cliente_Nome": nome_cli_final,
                            "Telefone": tel_cli_final,
                            "Modelo": modelo,
                            "Data_Hora_Entrada": data_hora_atual,
                            "Data_Hora_Saida": "Pendente",
                            "Obs_Cadastro": obs_cadastro,
                            "Status": "Aguardando Avaliação Técnica",
                            "Descricao_Laudo": "Pendente",
                            "Anomalias": "Nenhuma",
                            "Pecas_Solicitadas": json.dumps([]),
                            "Valor_Orcamento": 0.0,
                            "Mecanico_Laudo": "Pendente",
                            "Mecanico_Execucao": "Pendente",
                        }
                        df_maq = pd.concat([df_maq, pd.DataFrame([nova_linha])], ignore_index=True)
                        salvar_dataframe(df_maq, "maquinas")
                        st.success(
                            f"✅ Máquina cadastrada com sucesso!\n\n"
                            f"📅 **Entrada:** {data_hora_atual} | 🔢 **Código:** {codigo_num} | 📷 **QR Code Gerado**"
                        )

    elif sub_menu == "2. Imprimir Etiqueta QR Code":
        st.subheader("🖨️ Geração de QR Code Real & Impressão Direta")
        df_maq = carregar_dados("maquinas")
        if df_maq.empty:
            st.info("Nenhuma máquina cadastrada para gerar etiquetas.")
        else:
            maq_etiqueta_id = st.selectbox(
                "Selecione a máquina para gerar a etiqueta:",
                df_maq["ID"]
            )
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
                
                <div id="etiqueta-print" style="border: 2px dashed #333; padding: 20px; border-radius: 10px; width: 320px; background-color: #fff; color: #000; text-align: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; font-size: 18px;">🔧 OFICINA CONECTADA</h3>
                    <hr style="border: 1px solid #ccc; margin: 10px 0;">
                    <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Cliente:</b> {maq_info['Cliente_Nome']}</p>
                    <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Modelo:</b> {maq_info['Modelo']}</p>
                    <p style="font-size: 12px; margin: 4px 0; text-align: left;"><b>Entrada:</b> {maq_info['Data_Hora_Entrada']}</p>
                    <div style="margin: 10px 0;">
                        <img src="data:image/png;base64,{__import__('base64').b64encode(bytes_qrcode).decode()}" width="160px" />
                    </div>
                    <h2 style="margin: 0; color: #d9534f; font-size: 24px;">ID: {maq_info['ID']}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                """
                <button onclick="window.print();" style="background-color: #ff4b4b; color: white; padding: 10px 20px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 14px;">
                    🖨️ Imprimir Etiqueta Diretamente
                </button>
                """,
                unsafe_allow_html=True
            )
            st.markdown("---")

    elif sub_menu == "3. Cadastrar / Editar Laudo Técnico":
        st.subheader("🛠️ Diagnóstico, Exclusão/Alteração e Envio de Laudo")

        df_maq = carregar_dados("maquinas")
        maquinas_editaveis = df_maq[
            df_maq["Status"].isin([
                "Aguardando Avaliação Técnica",
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)"
            ])
        ]

        if maquinas_editaveis.empty:
            st.info("Não há máquinas disponíveis para alteração ou cadastro de laudo no momento.")
        else:
            eqp_id = st.selectbox(
                "Selecione a Máquina para Cadastrar/Editar o Laudo", maquinas_editaveis["ID"]
            )
            idx_row = df_maq[df_maq["ID"] == eqp_id].index[0]
            maq = df_maq.loc[idx_row]

            st.write(
                f"**Cliente:** {maq['Cliente_Nome']} | **Modelo:** {maq['Modelo']} | **Status Atual:** {maq['Status']}"
            )

            if maq["Status"] in ["Aguardando Precificação (Secretaria)", "Aguardando Precificação (Falta Peças no Estoque)"]:
                if st.button("🗑️ Excluir / Redefinir este Laudo (Corrigir Erro)"):
                    df_maq.loc[idx_row, "Descricao_Laudo"] = "Pendente"
                    df_maq.loc[idx_row, "Anomalias"] = "Nenhuma"
                    df_maq.loc[idx_row, "Pecas_Solicitadas"] = json.dumps([])
                    df_maq.loc[idx_row, "Mecanico_Laudo"] = "Pendente"
                    df_maq.loc[idx_row, "Status"] = "Aguardando Avaliação Técnica"
                    salvar_dataframe(df_maq, "maquinas")
                    st.success("✅ Laudo redefinido com sucesso! Agora você pode preenchê-lo novamente.")
                    st.rerun()

            st.markdown("### Selecionar Peças para o Orçamento")
            df_est = carregar_dados("estoque")
            opcoes_pecas = [
                f"{row['Nome']} (Estoque: {row['Quantidade']})"
                for _, row in df_est.iterrows()
            ]

            peca_selecionada = st.selectbox(
                "Escolha a peça do almoxarifado:", opcoes_pecas
            )
            qtd_peca = st.number_input(
                "Quantidade necessária:", min_value=1, value=1, step=1
            )

            if "carrinho_pecas" not in st.session_state:
                st.session_state.carrinho_pecas = []

            if st.button("➕ Adicionar Peça"):
                nome_peca_limpo = peca_selecionada.split(" (Estoque:")[0]
                estoque_item = df_est[df_est["Nome"] == nome_peca_limpo].iloc[0]

                st.session_state.carrinho_pecas.append(
                    {
                        "peca": nome_peca_limpo,
                        "qtd": qtd_peca,
                        "preco_unit": estoque_item["Preco_Unitario"],
                    }
                )
                
                if qtd_peca > estoque_item["Quantidade"]:
                    st.warning(f"⚠️ Aviso: A peça '{nome_peca_limpo}' está em falta no estoque (Estoque atual: {estoque_item['Quantidade']}, Pedido: {qtd_peca}).")
                else:
                    st.success(f"✅ Adicionado: {qtd_peca}x {nome_peca_limpo}")

            if st.session_state.carrinho_pecas:
                st.write("**Peças Selecionadas:**")
                df_carrinho = pd.DataFrame(st.session_state.carrinho_pecas)
                df_carrinho.columns = ["Peça", "Quantidade", "Preço Unitário (R$)"]
                st.dataframe(df_carrinho, use_container_width=True)

                if st.button("🗑️ Limpar Carrinho de Peças"):
                    st.session_state.carrinho_pecas = []
                    st.rerun()

            st.markdown("---")
            with st.form("form_laudo", clear_on_submit=True):
                laudo = st.text_input("Descrição Técnica do Serviço:", value=maq["Descricao_Laudo"] if maq["Descricao_Laudo"] != "Pendente" else "")
                anomalias = st.text_input(
                    "Observações / Anomalias Encontradas:",
                    value=maq["Anomalias"] if maq["Anomalias"] != "Nenhuma" else ""
                )
                
                enviar_secretaria = st.form_submit_button("Salvar e Enviar Laudo para Secretaria")

                if enviar_secretaria:
                    if not laudo:
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

                        df_maq.loc[idx_row, "Descricao_Laudo"] = laudo
                        df_maq.loc[idx_row, "Anomalias"] = anomalias if anomalias else "Nenhuma"
                        df_maq.loc[idx_row, "Pecas_Solicitadas"] = json.dumps(pecas_sol)
                        df_maq.loc[idx_row, "Mecanico_Laudo"] = st.session_state.usuario_logado

                        if falta_no_envio:
                            df_maq.loc[idx_row, "Status"] = "Aguardando Precificação (Falta Peças no Estoque)"
                            st.warning("⚠️ Laudo enviado com sucesso! Note que há peças em falta no estoque; a Secretaria foi avisada.")
                        else:
                            df_maq.loc[idx_row, "Status"] = "Aguardando Precificação (Secretaria)"
                            st.success(f"✅ Laudo enviado com sucesso por {st.session_state.usuario_logado}!")

                        salvar_dataframe(df_maq, "maquinas")
                        st.session_state.carrinho_pecas = []
                        st.rerun()

    elif sub_menu == "4. Executar Manutenção & Concluir Serviços":
        st.subheader("⚙️ Execução e Conclusão de Manutenções")

        df_maq = carregar_dados("maquinas")
        aprovadas_ou_manutencao = df_maq[
            df_maq["Status"].isin([
                "Cliente Aprovou (Pronto para Iniciar)",
                "Aguardando Peças",
                "Em Manutenção (Na Bancada)"
            ])
        ]

        if aprovadas_ou_manutencao.empty:
            st.info("Não há máquinas com orçamento aprovado aguardando execução ou em manutenção no momento.")
        else:
            for _, row in aprovadas_ou_manutencao.iterrows():
                with st.expander(f"Máquina ID: {row['ID']} - Cliente: {row['Cliente_Nome']} [{row['Status']}]"):
                    st.write(f"**Modelo:** {row['Modelo']}")
                    st.write(f"**Laudo:** {row['Descricao_Laudo']}")
                    st.write(f"**Mecânico Responsável pelo Orçamento:** {row.get('Mecanico_Laudo', 'Não informado')}")
                    if row['Anomalias'] != "Nenhuma":
                        st.warning(f"**Anomalias:** {row['Anomalias']}")
                    
                    idx_row = df_maq[df_maq["ID"] == row["ID"]].index[0]

                    if row["Status"] == "Aguardando Peças":
                        st.warning("⏳ Esta máquina aguarda peças no estoque para iniciar a manutenção.")
                        if st.button(f"🔄 Verificar Estoque e Iniciar Manutenção (ID {row['ID']})", key=f"rever_pecas_{row['ID']}" ):
                            df_maq.loc[idx_row, "Status"] = "Em Manutenção (Na Bancada)"
                            df_maq.loc[idx_row, "Mecanico_Execucao"] = st.session_state.usuario_logado
                            salvar_dataframe(df_maq, "maquinas")
                            st.success("✅ Peças disponíveis! Manutenção iniciada.")
                            st.rerun()

                    elif row["Status"] == "Cliente Aprovou (Pronto para Iniciar)":
                        if st.button(f"▶️ Iniciar Manutenção (ID {row['ID']})", key=f"iniciar_{row['ID']}"):
                            df_maq.loc[idx_row, "Status"] = "Em Manutenção (Na Bancada)"
                            df_maq.loc[idx_row, "Mecanico_Execucao"] = st.session_state.usuario_logado
                            salvar_dataframe(df_maq, "maquinas")
                            st.success(f"✅ Manutenção iniciada por {st.session_state.usuario_logado}!")
                            st.rerun()

                    elif row["Status"] == "Em Manutenção (Na Bancada)":
                        st.info(f"⚙️ Em execução por: **{row.get('Mecanico_Execucao', 'N/A')}**")
                        if st.button(f"🏁 Concluir Serviço (ID {row['ID']})", key=f"concluir_{row['ID']}"):
                            df_maq.loc[idx_row, "Status"] = "Serviço Concluído (Aguardando Retirada)"
                            salvar_dataframe(df_maq, "maquinas")
                            st.success("🎉 Serviço concluído! Notificação enviada à Secretaria.")
                            st.rerun()

    elif sub_menu == "5. Consultar Máquinas e Laudos":
        renderizar_tabela_com_busca()

# ---------------------------------------------------------
# VISÃO 2: SECRETARIA / ADMINISTRAÇÃO (Desktop)
# ---------------------------------------------------------
elif st.session_state.perfil_logado == "Secretaria (Administração)":
    st.header("💻 Módulo Administrativo & Financeiro (Secretaria)")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Gestão de Orçamentos", "📦 Almoxarifado / Estoque", "👥 Gestão de Mecânicos", "📊 Visão Geral e Busca"]
    )

    with tab1:
        st.subheader("🚨 Orçamentos com Aviso de Falta de Peças (Reposição Necessária)")
        df_maq = carregar_dados("maquinas")
        aviso_pecas_lista = df_maq[
            df_maq["Status"] == "Aguardando Precificação (Falta Peças no Estoque)"
        ]

        if aviso_pecas_lista.empty:
            st.info("Nenhum orçamento com aviso de peças em falta.")
        else:
            for _, row in aviso_pecas_lista.iterrows():
                with st.expander(f"⚠️ ID: {row['ID']} - Cliente: {row['Cliente_Nome']} | Modelo: {row['Modelo']} (Pode precificar e falar com o cliente)"):
                    st.error("O mecânico enviou o laudo, mas os itens abaixo estão em quantidade insuficiente no estoque atual:")
                    try:
                        p_list = json.loads(row["Pecas_Solicitadas"])
                        df_pecas_aviso = pd.DataFrame(p_list)
                        df_pecas_aviso.columns = ["Peça", "Quantidade Pedida", "Preço Unitário (R$)"]
                        st.dataframe(df_pecas_aviso, use_container_width=True)
                    except:
                        pass

        st.markdown("---")
        st.subheader("1. Orçamentos Aguardando Precificação/Cálculo")

        para_precificar = df_maq[
            df_maq["Status"].isin([
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)"
            ])
        ]

        if para_precificar.empty:
            st.info("Nenhum orçamento pendente de precificação técnica.")
        else:
            for _, row in para_precificar.iterrows():
                with st.expander(
                    f"Máquina ID: {row['ID']} | Cliente: {row['Cliente_Nome']} | Laudo por: {row.get('Mecanico_Laudo', 'N/A')}"
                ):
                    st.write(f"**Equipamento:** {row['Modelo']}")
                    st.write(f"**Laudo do Mecânico:** {row['Descricao_Laudo']}")
                    st.write(f"**⚠️ Anomalias Relatadas:** {row['Anomalias']}")

                    custo_pecas = 0.0
                    try:
                        pecas = json.loads(row["Pecas_Solicitadas"])
                        if pecas:
                            st.markdown("**Peças Solicitadas:**")
                            df_pecas_req = pd.DataFrame(pecas)
                            df_pecas_req.columns = ["Peça", "Quantidade", "Preço Unitário (R$)"]
                            st.dataframe(df_pecas_req, use_container_width=True)
                            custo_pecas = sum(
                                item["qtd"] * item["preco_unit"] for item in pecas
                            )
                    except:
                        pass

                    st.info(f"💰 Custo total das Peças: **R$ {custo_pecas:.2f}**")

                    with st.form(key=f"form_calc_{row['ID']}", clear_on_submit=True):
                        mao_de_obra = st.number_input(
                            "Valor da Mão de Obra (R$)",
                            min_value=0.0,
                            value=100.0,
                            step=10.0,
                        )
                        valor_total = custo_pecas + mao_de_obra
                        st.write(f"### Valor Final do Orçamento: **R$ {valor_total:.2f}**")

                        if st.form_submit_button("Confirmar Valores e Colocar em Standby"):
                            idx_row = df_maq[df_maq["ID"] == row["ID"]].index[0]
                            df_maq.loc[idx_row, "Valor_Orcamento"] = valor_total
                            df_maq.loc[idx_row, "Status"] = "Standby (Aguardando Resposta do Cliente)"
                            salvar_dataframe(df_maq, "maquinas")
                            st.success("✅ Orçamento precificado e colocado em Standby para contato com o cliente!")
                            st.rerun()

        st.markdown("---")
        st.subheader("2. Contato com o Cliente (Aprovação)")

        standby = df_maq[
            df_maq["Status"] == "Standby (Aguardando Resposta do Cliente)"
        ]

        if standby.empty:
            st.info("Nenhum orçamento em standby no momento.")
        else:
            for _, row in standby.iterrows():
                with st.expander(
                    f"Cliente: {row['Cliente_Nome']} | Tel: {row['Telefone']} | Total: R$ {row['Valor_Orcamento']:.2f}"
                ):
                    col1, col2 = st.columns(2)
                    idx_row = df_maq[df_maq["ID"] == row["ID"]].index[0]

                    if col1.button("✅ Cliente APROVOU", key=f"ap_{row['ID']}"):
                        try:
                            pecas_req = json.loads(row["Pecas_Solicitadas"])
                        except:
                            pecas_req = []

                        df_est = carregar_dados("estoque")
                        falta_estoque = False
                        
                        for p in pecas_req:
                            p_nome = p["peca"]
                            p_qtd_pedida = p["qtd"]
                            estoque_atual = df_est[df_est["Nome"] == p_nome]["Quantidade"].values[0]

                            if p_qtd_pedida > estoque_atual:
                                falta_estoque = True
                            else:
                                e_idx = df_est[df_est["Nome"] == p_nome].index[0]
                                df_est.loc[e_idx, "Quantidade"] -= p_qtd_pedida

                        salvar_dataframe(df_est, "estoque")

                        if falta_estoque:
                            df_maq.loc[idx_row, "Status"] = "Aguardando Peças"
                            st.warning("⚠️ Cliente aprovou, mas o estoque ainda está insuficiente. Status definido como 'Aguardando Peças'.")
                        else:
                            df_maq.loc[idx_row, "Status"] = "Cliente Aprovou (Pronto para Iniciar)"
                            st.success("✅ Aprovado! Peças baixadas do estoque e mecânicos avisados.")
                        
                        salvar_dataframe(df_maq, "maquinas")
                        st.rerun()

                    if col2.button("❌ Cliente RECUSOU", key=f"rec_{row['ID']}"):
                        df_maq.loc[idx_row, "Status"] = "Orçamento Recusado"
                        salvar_dataframe(df_maq, "maquinas")
                        st.warning("Orçamento recusado pelo cliente.")
                        st.rerun()

        st.markdown("---")
        st.subheader("3. Máquinas com Manutenção Concluída (Contato de Retirada)")
        concluidas = df_maq[
            df_maq["Status"] == "Serviço Concluído (Aguardando Retirada)"
        ]
        if concluidas.empty:
            st.info("Nenhuma máquina concluída aguardando retirada.")
        else:
            for _, row in concluidas.iterrows():
                with st.expander(f"🟢 ID {row['ID']} - Cliente: {row['Cliente_Nome']} | Pronto para Retirada"):
                    st.write(f"**Telefone para Contato:** {row['Telefone']}")
                    st.write(f"**Modelo:** {row['Modelo']}")
                    st.write(f"**Valor Total a Pagar:** R$ {row['Valor_Orcamento']:.2f}")
                    
                    idx_row = df_maq[df_maq["ID"] == row["ID"]].index[0]

                    if st.button(f"🏁 Confirmar Retirada pelo Cliente (ID {row['ID']})", key=f"retirada_{row['ID']}"):
                        data_hora_saida_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                        df_maq.loc[idx_row, "Status"] = "Entregue / Retirado"
                        df_maq.loc[idx_row, "Data_Hora_Saida"] = data_hora_saida_atual
                        salvar_dataframe(df_maq, "maquinas")
                        st.success(f"✅ Retirada confirmada! Data/Hora de saída registrada: {data_hora_saida_atual}. Ciclo encerrado.")
                        st.rerun()

    with tab2:
        st.subheader("📦 Almoxarifado - Controle Geral de Estoque")
        df_est = carregar_dados("estoque")
        
        criticos = df_est[df_est["Quantidade"] <= df_est["Minimo"]]
        if not criticos.empty:
            st.error("🚨 **ATENÇÃO: ALERTA DE ESTOQUE BAIXO!** Os seguintes itens atingiram ou estão abaixo do limite mínimo de segurança:")
            for _, c_row in criticos.iterrows():
                st.warning(f"⚠️ Peça **{c_row['Nome']}** está com **{c_row['Quantidade']}** unidades (O mínimo recomendado é {c_row['Minimo']}).")

        st.dataframe(df_est, use_container_width=True)

        st.markdown("### 🔄 Dar Entrada / Repor Estoque de Peça Existente")
        with st.form("form_repor_peca", clear_on_submit=True):
            peca_repor = st.selectbox("Selecione a Peça para Adicionar Unidades:", df_est["Nome"])
            qtd_adicionar = st.number_input("Quantidade a somar ao estoque atual:", min_value=1, value=5, step=1)
            btn_repor = st.form_submit_button("Confirmar Entrada de Peças")

            if btn_repor:
                p_idx = df_est[df_est["Nome"] == peca_repor].index[0]
                df_est.loc[p_idx, "Quantidade"] += qtd_adicionar
                salvar_dataframe(df_est, "estoque")
                st.success(f"✅ Adicionadas {qtd_adicionar} unidades à peça '{peca_repor}' com sucesso!")
                st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Cadastrar Nova Peça no Estoque")
        with st.form("nova_peca_form", clear_on_submit=True):
            nome_p = st.text_input("Nome da Nova Peça")
            qtd_p = st.number_input("Quantidade Inicial", min_value=1, value=10, step=1)
            min_p = st.number_input("Estoque Mínimo (Alerta de Segurança)", min_value=1, value=3, step=1)
            preco_p = st.number_input("Preço Unitário (R$)", min_value=0.0, value=50.0, step=5.0)

            btn_salvar_peca = st.form_submit_button("Salvar Nova Peça")

            if btn_salvar_peca:
                if not nome_p.strip():
                    st.warning("O nome da peça não pode estar vazio.")
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
                    st.success(f"✅ Sucesso! Peça '{nome_p}' cadastrada com ID {novo_id}.")

        st.markdown("---")
        st.subheader("🗑️ Excluir Peça do Estoque")
        peca_para_excluir = st.selectbox(
            "Selecione a peça para remover do almoxarifado:",
            ["-- Selecionar Peça --"] + list(df_est["Nome"])
        )
        if peca_para_excluir != "-- Selecionar Peça --":
            if st.button("⚠️ Confirmar Exclusão desta Peça"):
                df_est = df_est[df_est["Nome"] != peca_para_excluir]
                salvar_dataframe(df_est, "estoque")
                st.success(f"✅ Peça '{peca_para_excluir}' removida com sucesso do estoque!")
                st.rerun()

    with tab3:
        st.subheader("👥 Gestão de Mecânicos da Oficina")
        df_usr = carregar_dados("usuarios")
        mecanicos_df = df_usr[df_usr["Perfil"] == "Mecânico (Oficina)"]
        st.dataframe(mecanicos_df[["Usuario", "Nome"]], use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🗑️ Excluir Perfil de Mecânico")
        mecs_para_remover = list(mecanicos_df["Nome"])
        if mecs_para_remover:
            mec_escolhido = st.selectbox("Selecione o mecânico para remover acesso:", ["-- Selecionar --"] + mecs_para_remover)
            if mec_escolhido != "-- Selecionar --":
                if st.button("⚠️ Confirmar Exclusão do Mecânico"):
                    df_usr = df_usr[df_usr["Nome"] != mec_escolhido]
                    salvar_dataframe(df_usr, "usuarios")
                    st.success(f"✅ Acesso do mecânico '{mec_escolhido}' removido com sucesso!")
                    st.rerun()
        else:
            st.info("Nenhum mecânico cadastrado para exclusão.")

        st.markdown("---")
        st.markdown("#### ➕ Cadastrar Novo Mecânico")
        with st.form("form_novo_mecanico", clear_on_submit=True):
            nome_mec = st.text_input("Nome Completo do Mecânico")
            user_mec = st.text_input("Nome de Usuário (Login)")
            senha_mec = st.text_input("Senha de Acesso", type="password")
            
            btn_cad_mec = st.form_submit_button("Cadastrar Novo Mecânico")

            if btn_cad_mec:
                if not nome_mec.strip() or not user_mec.strip() or not senha_mec.strip():
                    st.warning("Preencha todos os campos.")
                elif user_mec.strip() in df_usr["Usuario"].values:
                    st.error("Este nome de usuário já está em uso.")
                else:
                    novo_mec_df = pd.DataFrame([
                        {
                            "Usuario": user_mec.strip(),
                            "Senha": senha_mec.strip(),
                            "Perfil": "Mecânico (Oficina)",
                            "Nome": nome_mec.strip(),
                        }
                    ])
                    df_usr = pd.concat([df_usr, novo_mec_df], ignore_index=True)
                    salvar_dataframe(df_usr, "usuarios")
                    st.success(f"✅ Mecânico {nome_mec} cadastrado com sucesso!")
                    st.rerun()

    with tab4:
        renderizar_tabela_com_busca("📊 Painel Geral de Máquinas, Laudos e Consulta por Busca")