import random

import pandas as pd
import streamlit as st

from database.connection import agora_str
from repositories.oficina_repo import (
    carregar_tabela,
    obter_visao_consolidada,
    salvar_tabela_df,
)
from services.fluxo_service import (
    abrir_nova_passagem_com_fotos,
    concluir_servico_passagem,
    iniciar_servico_passagem,
    redefinir_laudo_passagem,
    salvar_laudo_passagem,
)
from services.midia_service import gerar_qrcode_base64, serializar_imagens
from ui.components import (
    exibir_banco_passagens_maquina,
    exibir_galeria_imagens,
    fmt_data,
    renderizar_tabela_com_busca,
    renderizar_visao_historica_cliente,
    validar_telefone,
)

TELAS_MECANICO = [
    "Entrada / Passagens",
    "Máquinas e Passagens",
    "Laudo Técnico",
    "Execução",
    "Etiqueta QR Code",
    "Histórico por Cliente",
]

ROTULOS_MECANICO = {
    "Entrada / Passagens": "➕ Entrada",
    "Máquinas e Passagens": "🔍 Máquinas",
    "Laudo Técnico": "🛠️ Laudo",
    "Execução": "⚙️ Execução",
    "Etiqueta QR Code": "🖨️ QR Code",
    "Histórico por Cliente": "👤 Clientes",
}

MODULOS_MECANICO_HUB = [
    {
        "icone": "➕",
        "titulo": "Entrada / Passagens",
        "destino": "Entrada / Passagens",
        "descricao": "Cadastrar máquina, abrir passagem e anexar fotos.",
    },
    {
        "icone": "🔍",
        "titulo": "Buscar Máquinas",
        "destino": "Máquinas e Passagens",
        "descricao": "Pesquisar máquinas, ler QR Code e ver fichas.",
    },
    {
        "icone": "🛠️",
        "titulo": "Laudo Técnico",
        "destino": "Laudo Técnico",
        "descricao": "Registrar laudo, peças, fotos e enviar.",
    },
    {
        "icone": "⚙️",
        "titulo": "Execução",
        "destino": "Execução",
        "descricao": "Iniciar ou concluir manutenções na bancada.",
    },
    {
        "icone": "🖨️",
        "titulo": "Etiqueta QR Code",
        "destino": "Etiqueta QR Code",
        "descricao": "Gerar e imprimir etiqueta com QR Code.",
    },
    {
        "icone": "👤",
        "titulo": "Histórico por Cliente",
        "destino": "Histórico por Cliente",
        "descricao": "Consultar máquinas e passagens por cliente.",
    },
]


def _render_entrada_passagens(is_mobile: bool, logar_acao) -> None:
    st.subheader("📝 Registrar Máquina e Passagens na Oficina")
    df_cli = carregar_tabela("clientes")
    opcoes_clientes = (
        ["-- Selecionar Cliente Existente --"]
        + list(df_cli["Nome"] + " (" + df_cli["Telefone"] + ")")
        + ["+ Cadastrar Novo Cliente"]
    )
    cliente_sel = st.selectbox("Proprietário da Máquina:", opcoes_clientes)
    id_cli_final, nome_cli_final, tel_cli_final = None, "", ""

    if cliente_sel == "+ Cadastrar Novo Cliente":
        with st.form("form_novo_cliente", clear_on_submit=True):
            novo_nome = st.text_input("Nome Completo do Cliente")
            novo_tel = st.text_input(
                "Telefone (Apenas Números com DDD, ex: 21999998888)"
            )
            if st.form_submit_button("Salvar Cliente", use_container_width=True):
                tel_valido = validar_telefone(novo_tel)
                if not novo_nome.strip():
                    st.error("O nome do cliente é obrigatório.")
                elif not tel_valido:
                    st.error(
                        "Telefone inválido! Digite 10 ou 11 dígitos com DDD."
                    )
                else:
                    novo_id_cli = f"CLI-{len(df_cli) + 1:03d}"
                    novo_c = pd.DataFrame([
                        {
                            "ID_Cliente": novo_id_cli,
                            "Nome": novo_nome.strip(),
                            "Telefone": tel_valido,
                        }
                    ])
                    salvar_tabela_df(
                        pd.concat([df_cli, novo_c], ignore_index=True),
                        "clientes",
                    )
                    logar_acao(
                        "CADASTRO_CLIENTE",
                        f"Cliente '{novo_nome.strip()}' ({novo_id_cli}) cadastrado.",
                    )
                    st.session_state.flash_sucesso = (
                        f"Cliente {novo_nome} cadastrado!"
                    )
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
    if modo_entrada.startswith("Cadastrar Nova Máquina"):
        with st.form("form_mec_cadastro", clear_on_submit=True):
            modelo = st.text_input("Modelo / Descrição do Equipamento")
            codigo_manual = st.text_input("Código da Máquina (Opcional)")
            obs_cadastro = st.text_area("Observações de Cadastro / Recepção")
            fotos_cadastro = st.file_uploader(
                "📷 Anexar Fotos na Chegada (opcional):",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="upload_fotos_chegada",
            )
            abrir_passagem_agora = st.checkbox(
                "Abrir 1ª passagem imediatamente", value=True
            )
            if st.form_submit_button(
                "Registrar Máquina", use_container_width=True
            ):
                if not id_cli_final:
                    st.error("Selecione um cliente proprietário.")
                elif not modelo.strip():
                    st.error("Preencha o modelo da máquina.")
                else:
                    codigo_num = (
                        codigo_manual.strip()
                        or f"{random.randint(1000, 9999)}"
                    )
                    df_maq = carregar_tabela("maquinas")
                    if (
                        not df_maq.empty
                        and codigo_num in df_maq["ID"].astype(str).values
                    ):
                        st.error(
                            f"Já existe máquina com o código {codigo_num}!"
                        )
                    else:
                        data_hora_atual = agora_str()
                        nova_maq = {
                            "ID": str(codigo_num),
                            "QR_Code": f"QR-EQP-{codigo_num}",
                            "ID_Cliente": id_cli_final,
                            "Cliente_Nome": nome_cli_final,
                            "Telefone": tel_cli_final,
                            "Modelo": modelo.strip(),
                            "Data_Hora_Cadastro": data_hora_atual,
                            "Obs_Cadastro": obs_cadastro,
                            "Fotos_Cadastro": serializar_imagens(
                                fotos_cadastro
                            ),
                        }
                        salvar_tabela_df(
                            pd.concat(
                                [df_maq, pd.DataFrame([nova_maq])],
                                ignore_index=True,
                            ),
                            "maquinas",
                        )
                        if abrir_passagem_agora:
                            id_pass, _ = abrir_nova_passagem_com_fotos(
                                str(codigo_num), "[]", logar_acao
                            )
                            logar_acao(
                                "ENTRADA_MAQUINA_PASSAGEM",
                                f"Máquina ID {codigo_num} cadastrada com passagem #{id_pass}.",
                            )
                            st.session_state.flash_sucesso = (
                                f"Máquina ID {codigo_num} cadastrada e passagem #{id_pass} aberta!"
                            )
                        else:
                            logar_acao(
                                "CADASTRO_MAQUINA_SEM_PASSAGEM",
                                f"Máquina ID {codigo_num} cadastrada sem passagem aberta.",
                            )
                            st.session_state.flash_sucesso = (
                                f"Máquina ID {codigo_num} cadastrada!"
                            )
                        st.rerun()
    else:
        df_maq_exist = carregar_tabela("maquinas")
        if df_maq_exist.empty:
            st.info("Nenhuma máquina cadastrada ainda.")
        else:
            df_filtrada = (
                df_maq_exist[df_maq_exist["ID_Cliente"] == id_cli_final]
                if id_cli_final
                else df_maq_exist
            )
            if df_filtrada.empty:
                df_filtrada = df_maq_exist
            opcoes_maq = [
                f"{r['ID']} — {r['Modelo']} (Cliente: {r['Cliente_Nome']})"
                for _, r in df_filtrada.iterrows()
            ]
            maq_sel = st.selectbox("Selecione a Máquina:", opcoes_maq)
            id_maq_sel = maq_sel.split(" — ")[0]
            row_maq_sel = df_maq_exist[df_maq_exist["ID"] == id_maq_sel].iloc[
                0
            ]

            exibir_galeria_imagens(
                row_maq_sel.get("Fotos_Cadastro"),
                "📸 Fotos no Cadastro",
                is_mobile=is_mobile,
            )
            exibir_banco_passagens_maquina(
                id_maq_sel,
                "Passagens Anteriores",
                is_mobile=is_mobile,
            )

            fotos_nova_pass = st.file_uploader(
                "📷 Anexar Fotos nesta Nova Passagem (opcional):",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="upload_fotos_nova_passagem",
            )
            if st.button("➕ Abrir Nova Passagem", use_container_width=True):
                id_pass, _ = abrir_nova_passagem_com_fotos(
                    id_maq_sel,
                    serializar_imagens(fotos_nova_pass),
                    logar_acao,
                )
                st.session_state.flash_sucesso = (
                    f"Nova passagem #{id_pass} aberta para máquina {id_maq_sel}!"
                )
                st.rerun()


def _render_etiqueta_qr() -> None:
    st.subheader("🖨️ Geração de QR Code Real & Impressão Direta")
    df_maq = carregar_tabela("maquinas")
    if df_maq.empty:
        st.info("Nenhuma máquina cadastrada.")
        return

    maq_etiqueta_id = st.selectbox("Selecione a máquina:", df_maq["ID"])
    maq_info = df_maq[df_maq["ID"] == maq_etiqueta_id].iloc[0]
    qr_b64 = gerar_qrcode_base64(str(maq_info["ID"]))
    st.markdown(
        f"""
        <div id="etiqueta-print" style="border: 2px dashed #1D5FA7; padding: 18px; border-radius: 10px; max-width: 320px; width: 100%; background-color: #FFFFFF; color: #0F3D75; text-align: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 18px; color: #0F3D75;">🔧 OFICINA CONECTADA</h3>
            <hr style="border: 1px solid #F5B700; margin: 10px 0;">
            <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Cliente:</b> {maq_info['Cliente_Nome']}</p>
            <p style="font-size: 13px; margin: 4px 0; text-align: left;"><b>Modelo:</b> {maq_info['Modelo']}</p>
            <p style="font-size: 12px; margin: 4px 0; text-align: left;"><b>Cadastro:</b> {fmt_data(maq_info.get('Data_Hora_Cadastro'))}</p>
            <div style="margin: 10px 0;">
                <img src="data:image/png;base64,{qr_b64}" width="150px" />
            </div>
            <h2 style="margin: 0; color: #0F3D75; background-color: #FFF8DB; border: 1px solid #F5B700; border-radius: 6px; padding: 4px; font-size: 22px;">ID: {maq_info['ID']}</h2>
        </div>
        <button onclick="window.print();" style="background-color: #0F3D75; color: #FFD166; padding: 11px 20px; border: 2px solid #F5B700; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px; width: 100%; max-width: 320px;">
            🖨️ Imprimir Etiqueta Diretamente
        </button>
        """,
        unsafe_allow_html=True,
    )


def _render_laudo_tecnico(is_mobile: bool, logar_acao) -> None:
    st.subheader("🛠️ Diagnóstico, Fotos e Envio de Laudo")
    df_consolidado = obter_visao_consolidada()
    editaveis = df_consolidado[
        df_consolidado["ID_Passagem"].notna()
        & df_consolidado["Status"].isin([
            "Aguardando Avaliação Técnica",
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)",
        ])
    ]
    if editaveis.empty:
        st.info("Não há passagens disponíveis para laudo no momento.")
        return

    opcoes_laudo = [
        f"Máquina {r['ID']} (Passagem #{int(r['ID_Passagem'])}) — {r['Cliente_Nome']} [{r['Modelo']}]"
        for _, r in editaveis.iterrows()
    ]
    sel_laudo = st.selectbox("Selecione a Máquina / Passagem:", opcoes_laudo)
    row_sel = editaveis.iloc[opcoes_laudo.index(sel_laudo)]
    eqp_id = str(row_sel["ID"])
    id_pass = int(row_sel["ID_Passagem"])

    exibir_galeria_imagens(
        row_sel.get("Fotos_Cadastro"),
        "📸 Fotos na Chegada",
        is_mobile=is_mobile,
    )
    exibir_galeria_imagens(
        row_sel.get("Fotos_Laudo"),
        "🛠️ Fotos do Laudo",
        is_mobile=is_mobile,
    )

    if row_sel["Status"] in [
        "Aguardando Precificação (Secretaria)",
        "Aguardando Precificação (Falta Peças no Estoque)",
    ]:
        if st.button("🗑️ Redefinir este Laudo", use_container_width=True):
            redefinir_laudo_passagem(id_pass, eqp_id, logar_acao)
            st.session_state.flash_sucesso = "Laudo redefinido!"
            st.rerun()

    df_est = carregar_tabela("estoque")
    opcoes_pecas = [
        f"{r['Nome']} (Estoque: {r['Quantidade']})"
        for _, r in df_est.iterrows()
    ]
    peca_sel = st.selectbox("Peça do almoxarifado:", opcoes_pecas)
    qtd_peca = st.number_input("Quantidade:", min_value=1, value=1, step=1)
    if "carrinho_pecas" not in st.session_state:
        st.session_state.carrinho_pecas = []

    if st.button("➕ Adicionar Peça", use_container_width=True):
        nome_p = peca_sel.split(" (Estoque:")[0]
        item_est = df_est[df_est["Nome"] == nome_p].iloc[0]
        st.session_state.carrinho_pecas.append({
            "peca": nome_p,
            "qtd": qtd_peca,
            "preco_unit": item_est["Preco_Unitario"],
        })
        st.rerun()

    if st.session_state.carrinho_pecas:
        st.dataframe(
            pd.DataFrame(st.session_state.carrinho_pecas),
            use_container_width=True,
            hide_index=True,
        )
        if st.button("🗑️ Limpar Carrinho", use_container_width=True):
            st.session_state.carrinho_pecas = []
            st.rerun()

    with st.form("form_laudo", clear_on_submit=True):
        laudo = st.text_input(
            "Descrição Técnica:",
            value=(
                row_sel["Descricao_Laudo"]
                if row_sel["Descricao_Laudo"] != "Pendente"
                else ""
            ),
        )
        anomalias = st.text_input(
            "Anomalias:",
            value=(
                row_sel["Anomalias"]
                if row_sel["Anomalias"] != "Nenhuma"
                else ""
            ),
        )
        fotos_laudo_up = st.file_uploader(
            "📷 Anexar Imagens ao Laudo:",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            key="upload_fotos_laudo",
        )
        if st.form_submit_button(
            "Salvar e Enviar Laudo", use_container_width=True
        ):
            if not laudo.strip():
                st.warning("Descreva o serviço.")
            else:
                est_map = dict(zip(df_est["Nome"], df_est["Quantidade"]))
                fotos_final = (
                    serializar_imagens(fotos_laudo_up)
                    if fotos_laudo_up
                    else (row_sel.get("Fotos_Laudo") or "[]")
                )
                _, falta = salvar_laudo_passagem(
                    id_passagem=id_pass,
                    id_maquina=eqp_id,
                    descricao_laudo=laudo,
                    anomalias=anomalias,
                    pecas_solicitadas=st.session_state.carrinho_pecas.copy(),
                    estoque_atual_map=est_map,
                    mecanico_nome=st.session_state.usuario_logado,
                    fotos_json=fotos_final,
                    logar_acao_fn=logar_acao,
                )
                st.session_state.carrinho_pecas = []
                st.session_state.flash_sucesso = (
                    "Laudo enviado (com alerta de falta de peças)!"
                    if falta
                    else "Laudo enviado!"
                )
                st.rerun()


def _render_execucao(is_mobile: bool, logar_acao) -> None:
    st.subheader("⚙️ Execução e Conclusão de Manutenções")
    df_consolidado = obter_visao_consolidada()
    aprovadas = df_consolidado[
        df_consolidado["ID_Passagem"].notna()
        & df_consolidado["Status"].isin([
            "Cliente Aprovou (Pronto para Iniciar)",
            "Aguardando Peças",
            "Em Manutenção (Na Bancada)",
        ])
    ]
    if aprovadas.empty:
        st.info("Nenhuma manutenção aguardando início ou em execução.")
        return

    for _, row in aprovadas.iterrows():
        id_pass = int(row["ID_Passagem"])
        with st.expander(
            f"Máquina {row['ID']} (#{id_pass}) - {row['Cliente_Nome']} [{row['Status']}]"
        ):
            st.write(
                f"**Modelo:** {row['Modelo']} | **Laudo:** {row['Descricao_Laudo']}"
            )
            exibir_galeria_imagens(
                row.get("Fotos_Laudo"),
                "🛠️ Fotos do Laudo",
                is_mobile=is_mobile,
            )
            if row["Status"] in [
                "Cliente Aprovou (Pronto para Iniciar)",
                "Aguardando Peças",
            ]:
                if st.button(
                    f"▶️ Iniciar Manutenção ({row['ID']})",
                    key=f"ini_{id_pass}",
                    use_container_width=True,
                ):
                    iniciar_servico_passagem(
                        id_pass,
                        str(row["ID"]),
                        st.session_state.usuario_logado,
                        logar_acao,
                    )
                    st.session_state.flash_sucesso = "Manutenção iniciada!"
                    st.rerun()
            elif row["Status"] == "Em Manutenção (Na Bancada)":
                if st.button(
                    f"🏁 Concluir Serviço ({row['ID']})",
                    key=f"conc_{id_pass}",
                    use_container_width=True,
                ):
                    concluir_servico_passagem(
                        id_pass, str(row["ID"]), logar_acao
                    )
                    st.session_state.flash_sucesso = "Serviço concluído!"
                    st.rerun()


def renderizar_visao_mecanico(
    is_mobile: bool,
    logar_acao,
    encerrar_sessao,
    render_grade,
    render_nav,
) -> None:
    tela_ativa = st.session_state.tela_mecanico
    if tela_ativa == "Início":
        render_nav(TELAS_MECANICO, "tela_mecanico", ROTULOS_MECANICO)
        render_grade(
            MODULOS_MECANICO_HUB,
            "tela_mecanico",
            f"🔧 {st.session_state.usuario_logado} — Módulos da Oficina",
            "Toque em um botão para abrir a tela correspondente.",
        )
        st.markdown(
            '<div class="login-mobile-only" style="margin-top: 10px;">',
            unsafe_allow_html=True,
        )
        if st.button(
            "🚪 Sair da Conta", key="mob_logout_mec", use_container_width=True
        ):
            encerrar_sessao()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    render_nav(TELAS_MECANICO, "tela_mecanico", ROTULOS_MECANICO)
    if tela_ativa == "Entrada / Passagens":
        _render_entrada_passagens(is_mobile, logar_acao)
    elif tela_ativa == "Etiqueta QR Code":
        _render_etiqueta_qr()
    elif tela_ativa == "Laudo Técnico":
        _render_laudo_tecnico(is_mobile, logar_acao)
    elif tela_ativa == "Execução":
        _render_execucao(is_mobile, logar_acao)
    elif tela_ativa == "Máquinas e Passagens":
        renderizar_tabela_com_busca(
            is_mobile=is_mobile,
            perfil_logado=st.session_state.perfil_logado,
            logar_acao_fn=logar_acao,
        )
    elif tela_ativa == "Histórico por Cliente":
        renderizar_visao_historica_cliente(
            contexto_key="mecanico", is_mobile=is_mobile
        )