import datetime
import random
import re
import io
import qrcode
import pandas as pd
import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner

# Configuração da Página
st.set_page_config(
    page_title="Oficina Conectada - Sistema de Gestão",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Oficina Conectada: Gestão Integrada")

# ---------------------------------------------------------
# INICIALIZAÇÃO DOS DADOS DA SESSÃO (BANCO DE DADOS SIMULADO)
# ---------------------------------------------------------
if "usuarios" not in st.session_state:
    st.session_state.usuarios = pd.DataFrame(
        {
            "Usuario": ["admin", "mecanico1"],
            "Senha": ["123", "123"],
            "Perfil": ["Secretaria (Administração)", "Mecânico (Oficina)"],
            "Nome": ["Administração Central", "Carlos Mecânico"],
        }
    )

if "clientes" not in st.session_state:
    st.session_state.clientes = pd.DataFrame(
        {
            "ID_Cliente": ["CLI-001", "CLI-002"],
            "Nome": ["João Silva", "Maria Oliveira"],
            "Telefone": ["21999998888", "21988887777"],
        }
    )

if "estoque" not in st.session_state:
    st.session_state.estoque = pd.DataFrame(
        {
            "ID_Peca": ["PEC-001", "PEC-002", "PEC-003", "PEC-004"],
            "Nome": [
                "Correia Dentada",
                "Filtro de Óleo",
                "Vela de Ignição",
                "Pastilha de Freio",
            ],
            "Quantidade": [10, 15, 1, 8],
            "Minimo": [3, 5, 4, 2],
            "Preco_Unitario": [150.00, 45.00, 30.00, 120.00],
        }
    )

if "maquinas" not in st.session_state:
    st.session_state.maquinas = pd.DataFrame(
        columns=[
            "ID",
            "QR_Code",
            "ID_Cliente",
            "Cliente_Nome",
            "Telefone",
            "Modelo",
            "Data_Hora_Entrada",
            "Data_Hora_Saida",
            "Obs_Cadastro",
            "Status",
            "Descricao_Laudo",
            "Anomalias",
            "Pecas_Solicitadas",
            "Valor_Orcamento",
            "Mecanico_Laudo",
            "Mecanico_Execucao",
        ]
    )

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "perfil_logado" not in st.session_state:
    st.session_state.perfil_logado = None

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

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR DE VALIDAÇÃO DE TELEFONE (APENAS NÚMEROS)
# ---------------------------------------------------------
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
            match = st.session_state.usuarios[
                (st.session_state.usuarios["Usuario"] == user_input.strip()) &
                (st.session_state.usuarios["Senha"] == senha_input.strip())
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
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.usuario_logado = None
        st.session_state.perfil_logado = None
        st.rerun()

st.sidebar.markdown("---")

# ---------------------------------------------------------
# CENTRAL DE NOTIFICAÇÕES
# ---------------------------------------------------------
st.sidebar.subheader("🔔 Notificações do Sistema")
notif_pendentes_sec = len(
    st.session_state.maquinas[
        st.session_state.maquinas["Status"].isin([
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)"
        ])
    ]
)
notif_falta_pecas_sec = len(
    st.session_state.maquinas[
        st.session_state.maquinas["Status"] == "Aguardando Precificação (Falta Peças no Estoque)"
    ]
)
notif_concluidas_sec = len(
    st.session_state.maquinas[
        st.session_state.maquinas["Status"] == "Serviço Concluído (Aguardando Retirada)"
    ]
)
notif_aprovados_oficina = len(
    st.session_state.maquinas[
        st.session_state.maquinas["Status"].isin(["Cliente Aprovou (Pronto para Iniciar)", "Aguardando Peças"])
    ]
)

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
# FUNÇÃO AUXILIAR DE BUSCA, CONSULTA E LEITOR DE QR CODE REAL
# ---------------------------------------------------------
def renderizar_tabela_com_busca(titulo="📊 Visão Geral das Máquinas e Laudos"):
    st.subheader(titulo)
    if st.session_state.maquinas.empty:
        st.info("Nenhuma máquina cadastrada no sistema.")
        return

    tab_busca_txt, tab_scan_qr = st.tabs(["🔍 Busca por Texto", "📷 Leitor de QR Code (Câmera Real)"])

    with tab_busca_txt:
        termo_busca = st.text_input(
            "Digite o Nome do Cliente, Código ou QR Code:",
            key=f"busca_{titulo}",
        )

        df_exibicao = st.session_state.maquinas.copy()
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
        st.markdown("### 📷 Scanner de QR Code com a Câmera do Celular")
        st.info("Aponte a câmera para o QR Code gerado na aba de impressão para abrir a ficha técnica instantaneamente.")

        # Ativa a câmera real do dispositivo móvel/computador via componente nativo
        codigo_lido = qrcode_scanner(key=f"scanner_{titulo}")

        if codigo_lido:
            st.success(f"🎯 QR Code Lido com Sucesso: **{codigo_lido}**")
            
            # Tenta encontrar a máquina pelo código exato do QR ou contendo no texto lido
            maq_encontrada = st.session_state.maquinas[
                st.session_state.maquinas["QR_Code"].str.contains(codigo_lido, case=False, na=False) |
                st.session_state.maquinas["ID"].str.contains(codigo_lido, case=False, na=False)
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
                if len(maq_info["Pecas_Solicitadas"]) > 0:
                    st.markdown("#### Peças Utilizadas / Solicitadas:")
                    st.dataframe(pd.DataFrame(maq_info["Pecas_Solicitadas"]), use_container_width=True)
            else:
                st.warning(f"⚠️ O código lido ('{codigo_lido}') não corresponde a nenhuma máquina cadastrada no sistema.")

    st.markdown("---")
    st.markdown("### 📋 Consulta Detalhada por ID")
    id_detalhe = st.selectbox(
        "Ou selecione o ID diretamente para ver detalhes:",
        ["-- Selecionar --"] + list(st.session_state.maquinas["ID"]),
        key=f"detalhe_{titulo}"
    )
    if id_detalhe != "-- Selecionar --":
        row_det = st.session_state.maquinas[st.session_state.maquinas["ID"] == id_detalhe].iloc[0]
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
        if len(row_det["Pecas_Solicitadas"]) > 0:
            st.markdown("**Peças Solicitadas no Orçamento:**")
            st.dataframe(pd.DataFrame(row_det["Pecas_Solicitadas"]), use_container_width=True)

    if st.session_state.perfil_logado == "Secretaria (Administração)":
        st.markdown("### 🗑️ Excluir Registro de Máquina")
        id_para_excluir = st.selectbox(
            "Selecione o ID da máquina para remover:",
            ["-- Selecionar --"] + list(st.session_state.maquinas["ID"]),
            key=f"excluir_maq_{titulo}"
        )
        if id_para_excluir != "-- Selecionar --":
            if st.button("⚠️ Confirmar Exclusão desta Máquina", key=f"btn_exc_{titulo}"):
                st.session_state.maquinas = st.session_state.maquinas[
                    st.session_state.maquinas["ID"] != id_para_excluir
                ]
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

        st.markdown("### 👤 Dados do Proprietário (Cliente)")
        opcoes_clientes = ["-- Selecionar Cliente Existente --"] + list(
            st.session_state.clientes["Nome"] + " (" + st.session_state.clientes["Telefone"] + ")"
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
                        novo_id_cli = f"CLI-{len(st.session_state.clientes) + 1:03d}"
                        st.session_state.clientes = pd.concat(
                            [
                                st.session_state.clientes,
                                pd.DataFrame(
                                    [
                                        {
                                            "ID_Cliente": novo_id_cli,
                                            "Nome": novo_nome.strip(),
                                            "Telefone": tel_valido,
                                        }
                                    ]
                                ),
                            ],
                            ignore_index=True,
                        )
                        st.success(f"✅ Cliente {novo_nome} cadastrado com sucesso!")
                        st.rerun()

        elif cliente_sel != "-- Selecionar Cliente Existente --":
            nome_cli_final = cliente_sel.split(" (")[0]
            cli_row = st.session_state.clientes[
                st.session_state.clientes["Nome"] == nome_cli_final
            ].iloc[0]
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

                    if not st.session_state.maquinas.empty and codigo_num in st.session_state.maquinas["ID"].values:
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
                            "Pecas_Solicitadas": [],
                            "Valor_Orcamento": 0.0,
                            "Mecanico_Laudo": "Pendente",
                            "Mecanico_Execucao": "Pendente",
                        }
                        st.session_state.maquinas = pd.concat(
                            [st.session_state.maquinas, pd.DataFrame([nova_linha])],
                            ignore_index=True,
                        )
                        st.success(
                            f"✅ Máquina cadastrada com sucesso!\n\n"
                            f"📅 **Entrada:** {data_hora_atual} | 🔢 **Código:** {codigo_num} | 📷 **QR Code Gerado**"
                        )

    elif sub_menu == "2. Imprimir Etiqueta QR Code":
        st.subheader("🖨️ Geração de QR Code Real & Impressão Direta")
        if st.session_state.maquinas.empty:
            st.info("Nenhuma máquina cadastrada para gerar etiquetas.")
        else:
            maq_etiqueta_id = st.selectbox(
                "Selecione a máquina para gerar a etiqueta:",
                st.session_state.maquinas["ID"]
            )
            maq_info = st.session_state.maquinas[
                st.session_state.maquinas["ID"] == maq_etiqueta_id
            ].iloc[0]

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

        maquinas_editaveis = st.session_state.maquinas[
            st.session_state.maquinas["Status"].isin([
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
            idx = st.session_state.maquinas[
                st.session_state.maquinas["ID"] == eqp_id
            ].index[0]
            maq = st.session_state.maquinas.loc[idx]

            st.write(
                f"**Cliente:** {maq['Cliente_Nome']} | **Modelo:** {maq['Modelo']} | **Status Atual:** {maq['Status']}"
            )

            if maq["Status"] in ["Aguardando Precificação (Secretaria)", "Aguardando Precificação (Falta Peças no Estoque)"]:
                if st.button("🗑️ Excluir / Redefinir este Laudo (Corrigir Erro)"):
                    st.session_state.maquinas.loc[idx, "Descricao_Laudo"] = "Pendente"
                    st.session_state.maquinas.loc[idx, "Anomalias"] = "Nenhuma"
                    st.session_state.maquinas.loc[idx, "Pecas_Solicitadas"] = []
                    st.session_state.maquinas.loc[idx, "Mecanico_Laudo"] = "Pendente"
                    st.session_state.maquinas.loc[idx, "Status"] = "Aguardando Avaliação Técnica"
                    st.success("✅ Laudo redefinido com sucesso! Agora você pode preenchê-lo novamente.")
                    st.rerun()

            st.markdown("### Selecionar Peças para o Orçamento")
            opcoes_pecas = [
                f"{row['Nome']} (Estoque: {row['Quantidade']})"
                for _, row in st.session_state.estoque.iterrows()
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
                estoque_item = st.session_state.estoque[
                    st.session_state.estoque["Nome"] == nome_peca_limpo
                ].iloc[0]

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
                            est_disp = st.session_state.estoque[
                                st.session_state.estoque["Nome"] == p_nome
                            ]["Quantidade"].values[0]
                            if p_qtd > est_disp:
                                falta_no_envio = True

                        st.session_state.maquinas.loc[idx, "Descricao_Laudo"] = laudo
                        st.session_state.maquinas.loc[idx, "Anomalias"] = anomalias if anomalias else "Nenhuma"
                        st.session_state.maquinas.at[idx, "Pecas_Solicitadas"] = pecas_sol
                        st.session_state.maquinas.loc[idx, "Mecanico_Laudo"] = st.session_state.usuario_logado

                        if falta_no_envio:
                            st.session_state.maquinas.loc[idx, "Status"] = "Aguardando Precificação (Falta Peças no Estoque)"
                            st.warning("⚠️ Laudo enviado com sucesso! Note que há peças em falta no estoque; a Secretaria foi avisada.")
                        else:
                            st.session_state.maquinas.loc[idx, "Status"] = "Aguardando Precificação (Secretaria)"
                            st.success(f"✅ Laudo enviado com sucesso por {st.session_state.usuario_logado}!")

                        st.session_state.carrinho_pecas = []
                        st.rerun()

    elif sub_menu == "4. Executar Manutenção & Concluir Serviços":
        st.subheader("⚙️ Execução e Conclusão de Manutenções")

        aprovadas_ou_manutencao = st.session_state.maquinas[
            st.session_state.maquinas["Status"].isin([
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
                    
                    idx = st.session_state.maquinas[
                        st.session_state.maquinas["ID"] == row["ID"]
                    ].index[0]

                    if row["Status"] == "Aguardando Peças":
                        st.warning("⏳ Esta máquina aguarda peças no estoque para iniciar a manutenção.")
                        if st.button(f"🔄 Verificar Estoque e Iniciar Manutenção (ID {row['ID']})", key=f"rever_pecas_{row['ID']}" ):
                            st.session_state.maquinas.loc[idx, "Status"] = "Em Manutenção (Na Bancada)"
                            st.session_state.maquinas.loc[idx, "Mecanico_Execucao"] = st.session_state.usuario_logado
                            st.success("✅ Peças disponíveis! Manutenção iniciada.")
                            st.rerun()

                    elif row["Status"] == "Cliente Aprovou (Pronto para Iniciar)":
                        if st.button(f"▶️ Iniciar Manutenção (ID {row['ID']})", key=f"iniciar_{row['ID']}"):
                            st.session_state.maquinas.loc[idx, "Status"] = "Em Manutenção (Na Bancada)"
                            st.session_state.maquinas.loc[idx, "Mecanico_Execucao"] = st.session_state.usuario_logado
                            st.success(f"✅ Manutenção iniciada por {st.session_state.usuario_logado}!")
                            st.rerun()

                    elif row["Status"] == "Em Manutenção (Na Bancada)":
                        st.info(f"⚙️ Em execução por: **{row.get('Mecanico_Execucao', 'N/A')}**")
                        if st.button(f"🏁 Concluir Serviço (ID {row['ID']})", key=f"concluir_{row['ID']}"):
                            st.session_state.maquinas.loc[idx, "Status"] = "Serviço Concluído (Aguardando Retirada)"
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
        aviso_pecas_lista = st.session_state.maquinas[
            st.session_state.maquinas["Status"] == "Aguardando Precificação (Falta Peças no Estoque)"
        ]

        if aviso_pecas_lista.empty:
            st.info("Nenhum orçamento com aviso de peças em falta.")
        else:
            for _, row in aviso_pecas_lista.iterrows():
                with st.expander(f"⚠️ ID: {row['ID']} - Cliente: {row['Cliente_Nome']} | Modelo: {row['Modelo']} (Pode precificar e falar com o cliente)"):
                    st.error("O mecânico enviou o laudo, mas os itens abaixo estão em quantidade insuficiente no estoque atual:")
                    df_pecas_aviso = pd.DataFrame(row["Pecas_Solicitadas"])
                    df_pecas_aviso.columns = ["Peça", "Quantidade Pedida", "Preço Unitário (R$)"]
                    st.dataframe(df_pecas_aviso, use_container_width=True)

        st.markdown("---")
        st.subheader("1. Orçamentos Aguardando Precificação/Cálculo")

        para_precificar = st.session_state.maquinas[
            st.session_state.maquinas["Status"].isin([
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

                    pecas = row["Pecas_Solicitadas"]
                    custo_pecas = 0.0

                    if len(pecas) > 0:
                        st.markdown("**Peças Solicitadas:**")
                        df_pecas_req = pd.DataFrame(pecas)
                        df_pecas_req.columns = ["Peça", "Quantidade", "Preço Unitário (R$)"]
                        st.dataframe(df_pecas_req, use_container_width=True)
                        custo_pecas = sum(
                            item["qtd"] * item["preco_unit"] for item in pecas
                        )

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
                            idx = st.session_state.maquinas[
                                st.session_state.maquinas["ID"] == row["ID"]
                            ].index[0]
                            st.session_state.maquinas.loc[
                                idx, "Valor_Orcamento"
                            ] = valor_total
                            st.session_state.maquinas.loc[idx, "Status"] = (
                                "Standby (Aguardando Resposta do Cliente)"
                            )
                            st.success("✅ Orçamento precificado e colocado em Standby para contato com o cliente!")
                            st.rerun()

        st.markdown("---")
        st.subheader("2. Contato com o Cliente (Aprovação)")

        standby = st.session_state.maquinas[
            st.session_state.maquinas["Status"]
            == "Standby (Aguardando Resposta do Cliente)"
        ]

        if standby.empty:
            st.info("Nenhum orçamento em standby no momento.")
        else:
            for _, row in standby.iterrows():
                with st.expander(
                    f"Cliente: {row['Cliente_Nome']} | Tel: {row['Telefone']} | Total: R$ {row['Valor_Orcamento']:.2f}"
                ):
                    col1, col2 = st.columns(2)
                    idx = st.session_state.maquinas[
                        st.session_state.maquinas["ID"] == row["ID"]
                    ].index[0]

                    if col1.button("✅ Cliente APROVOU", key=f"ap_{row['ID']}"):
                        pecas_req = row["Pecas_Solicitadas"]
                        falta_estoque = False
                        
                        for p in pecas_req:
                            p_nome = p["peca"]
                            p_qtd_pedida = p["qtd"]
                            estoque_atual = st.session_state.estoque[
                                st.session_state.estoque["Nome"] == p_nome
                            ]["Quantidade"].values[0]

                            if p_qtd_pedida > estoque_atual:
                                falta_estoque = True
                            else:
                                e_idx = st.session_state.estoque[
                                    st.session_state.estoque["Nome"] == p_nome
                                ].index[0]
                                st.session_state.estoque.loc[e_idx, "Quantidade"] -= p_qtd_pedida

                        if falta_estoque:
                            st.session_state.maquinas.loc[idx, "Status"] = "Aguardando Peças"
                            st.warning("⚠️ Cliente aprovou, mas o estoque ainda está insuficiente. Status definido como 'Aguardando Peças' até que o almoxarifado seja reposto.")
                        else:
                            st.session_state.maquinas.loc[idx, "Status"] = "Cliente Aprovou (Pronto para Iniciar)"
                            st.success("✅ Aprovado! Peças baixadas do estoque e mecânicos avisados.")
                        st.rerun()

                    if col2.button("❌ Cliente RECUSOU", key=f"rec_{row['ID']}"):
                        st.session_state.maquinas.loc[idx, "Status"] = "Orçamento Recusado"
                        st.warning("Orçamento recusado pelo cliente.")
                        st.rerun()

        st.markdown("---")
        st.subheader("3. Máquinas com Manutenção Concluída (Contato de Retirada)")
        concluidas = st.session_state.maquinas[
            st.session_state.maquinas["Status"] == "Serviço Concluído (Aguardando Retirada)"
        ]
        if concluidas.empty:
            st.info("Nenhuma máquina concluída aguardando retirada.")
        else:
            for _, row in concluidas.iterrows():
                with st.expander(f"🟢 ID {row['ID']} - Cliente: {row['Cliente_Nome']} | Pronto para Retirada"):
                    st.write(f"**Telefone para Contato:** {row['Telefone']}")
                    st.write(f"**Modelo:** {row['Modelo']}")
                    st.write(f"**Valor Total a Pagar:** R$ {row['Valor_Orcamento']:.2f}")
                    
                    idx = st.session_state.maquinas[
                        st.session_state.maquinas["ID"] == row["ID"]
                    ].index[0]

                    if st.button(f"🏁 Confirmar Retirada pelo Cliente (ID {row['ID']})", key=f"retirada_{row['ID']}"):
                        data_hora_saida_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                        st.session_state.maquinas.loc[idx, "Status"] = "Entregue / Retirado"
                        st.session_state.maquinas.loc[idx, "Data_Hora_Saida"] = data_hora_saida_atual
                        st.success(f"✅ Retirada confirmada! Data/Hora de saída registrada: {data_hora_saida_atual}. Ciclo encerrado.")
                        st.rerun()

    with tab2:
        st.subheader("📦 Almoxarifado - Controle Geral de Estoque")
        
        criticos = st.session_state.estoque[
            st.session_state.estoque["Quantidade"] <= st.session_state.estoque["Minimo"]
        ]
        if not criticos.empty:
            st.error("🚨 **ATENÇÃO: ALERTA DE ESTOQUE BAIXO!** Os seguintes itens atingiram ou estão abaixo do limite mínimo de segurança:")
            for _, c_row in criticos.iterrows():
                st.warning(f"⚠️ Peça **{c_row['Nome']}** está com **{c_row['Quantidade']}** unidades (O mínimo recomendado é {c_row['Minimo']}).")

        st.dataframe(st.session_state.estoque, use_container_width=True)

        st.markdown("### 🔄 Dar Entrada / Repor Estoque de Peça Existente")
        with st.form("form_repor_peca", clear_on_submit=True):
            peca_repor = st.selectbox("Selecione a Peça para Adicionar Unidades:", st.session_state.estoque["Nome"])
            qtd_adicionar = st.number_input("Quantidade a somar ao estoque atual:", min_value=1, value=5, step=1)
            btn_repor = st.form_submit_button("Confirmar Entrada de Peças")

            if btn_repor:
                p_idx = st.session_state.estoque[st.session_state.estoque["Nome"] == peca_repor].index[0]
                st.session_state.estoque.loc[p_idx, "Quantidade"] += qtd_adicionar
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
                    novo_id = f"PEC-{len(st.session_state.estoque) + 1:03d}"
                    nova_p = {
                        "ID_Peca": novo_id,
                        "Nome": nome_p.strip(),
                        "Quantidade": qtd_p,
                        "Minimo": min_p,
                        "Preco_Unitario": preco_p,
                    }
                    st.session_state.estoque = pd.concat(
                        [st.session_state.estoque, pd.DataFrame([nova_p])],
                        ignore_index=True,
                    )
                    st.success(f"✅ Sucesso! Peça '{nome_p}' cadastrada com ID {novo_id}.")

        st.markdown("---")
        st.subheader("🗑️ Excluir Peça do Estoque")
        peca_para_excluir = st.selectbox(
            "Selecione a peça para remover do almoxarifado:",
            ["-- Selecionar Peça --"] + list(st.session_state.estoque["Nome"])
        )
        if peca_para_excluir != "-- Selecionar Peça --":
            if st.button("⚠️ Confirmar Exclusão desta Peça"):
                st.session_state.estoque = st.session_state.estoque[
                    st.session_state.estoque["Nome"] != peca_para_excluir
                ]
                st.success(f"✅ Peça '{peca_para_excluir}' removida com sucesso do estoque!")
                st.rerun()

    with tab3:
        st.subheader("👥 Gestão de Mecânicos da Oficina")
        st.markdown("Cadastre ou remova perfis de mecânicos do sistema.")
        
        st.markdown("#### Mecânicos Atualmente Cadastrados:")
        mecanicos_df = st.session_state.usuarios[st.session_state.usuarios["Perfil"] == "Mecânico (Oficina)"]
        st.dataframe(mecanicos_df[["Usuario", "Nome"]], use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🗑️ Excluir Perfil de Mecânico")
        mecs_para_remover = list(mecanicos_df["Nome"])
        if mecs_para_remover:
            mec_escolhido = st.selectbox("Selecione o mecânico para remover acesso:", ["-- Selecionar --"] + mecs_para_remover)
            if mec_escolhido != "-- Selecionar --":
                if st.button("⚠️ Confirmar Exclusão do Mecânico"):
                    st.session_state.usuarios = st.session_state.usuarios[
                        st.session_state.usuarios["Nome"] != mec_escolhido
                    ]
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
                elif user_mec.strip() in st.session_state.usuarios["Usuario"].values:
                    st.error("Este nome de usuário já está em uso.")
                else:
                    novo_mec_df = pd.DataFrame(
                        [
                            {
                                "Usuario": user_mec.strip(),
                                "Senha": senha_mec.strip(),
                                "Perfil": "Mecânico (Oficina)",
                                "Nome": nome_mec.strip(),
                            }
                        ]
                    )
                    st.session_state.usuarios = pd.concat(
                        [st.session_state.usuarios, novo_mec_df],
                        ignore_index=True,
                    )
                    st.success(f"✅ Mecânico {nome_mec} cadastrado com sucesso!")
                    st.rerun()

    with tab4:
        renderizar_tabela_com_busca("📊 Painel Geral de Máquinas, Laudos e Consulta por Busca")