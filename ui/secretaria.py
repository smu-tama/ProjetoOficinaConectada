import pandas as pd
import streamlit as st

from repositories.oficina_repo import (
    carregar_tabela,
    obter_visao_consolidada,
    salvar_tabela_df,
)
from services.fluxo_service import (
    calcular_custo_pecas_json,
    confirmar_saida_maquina,
    enviar_orcamento_ao_cliente,
    notificar_conclusao_cliente,
    precificar_passagem,
    processar_resposta_cliente,
    repor_estoque_peca,
)
from ui.components import exibir_galeria_imagens, fmt_valor

TELAS_SECRETARIA = [
    "Cockpit",
    "Almoxarifado",
    "Máquinas e Passagens",
    "Logs do Sistema",
]

ROTULOS_SECRETARIA = {
    "Cockpit": "⚡ Cockpit & Orçamentos",
    "Almoxarifado": "📦 Almoxarifado & Estoque",
    "Máquinas e Passagens": "🛠️ Máquinas e Passagens",
    "Logs do Sistema": "📜 Logs do Sistema",
}

STATUS_FILA_SECRETARIA = [
    "Aguardando Precificação (Falta Peças no Estoque)",
    "Aguardando Precificação (Secretaria)",
    "Aguardando Envio ao Cliente",
    "Standby (Aguardando Resposta do Cliente)",
    "Serviço Concluído (Aguardando Notificação ao Cliente)",
    "Serviço Concluído (Aguardando Retirada)",
]


def _render_menu_lateral_secretaria() -> str:
    """Renderiza os botões de navegação individual na barra lateral."""
    if "tela_secretaria" not in st.session_state:
        st.session_state.tela_secretaria = "Cockpit"

    if st.session_state.tela_secretaria == "Início":
        st.session_state.tela_secretaria = "Cockpit"

    st.sidebar.markdown("### 🗂️ Telas da Secretaria")
    for nome_tela in TELAS_SECRETARIA:
        ativa = st.session_state.tela_secretaria == nome_tela
        rotulo = (
            f"🟡 {ROTULOS_SECRETARIA.get(nome_tela, nome_tela)}"
            if ativa
            else ROTULOS_SECRETARIA.get(nome_tela, nome_tela)
        )
        if st.sidebar.button(
            rotulo,
            key=f"sec_side_nav_{nome_tela}",
            use_container_width=True,
        ):
            st.session_state.tela_secretaria = nome_tela
            st.rerun()

    st.sidebar.markdown("---")
    return st.session_state.tela_secretaria


def _render_kpi_card(
    icone: str,
    valor: str,
    label: str,
    tag: str,
    pct_barra: int = 50,
    variante: str = "azul",
) -> str:
    borda_classe = (
        "destaque-amarelo" if variante == "amarelo" else "destaque-azul"
    )
    icone_classe = "amarelo" if variante == "amarelo" else ""
    cor_barra = "#F5B700" if variante == "amarelo" else "#1D5FA7"
    largura_segura = max(8, min(100, int(pct_barra)))
    return f"""
        <div class="sec-kpi-card {borda_classe}">
            <div class="sec-kpi-top">
                <span class="sec-kpi-icone {icone_classe}">{icone}</span>
                <span class="sec-kpi-tag">{tag}</span>
            </div>
            <div class="sec-kpi-valor">{valor}</div>
            <div class="sec-kpi-label">{label}</div>
            <div class="sec-mini-track">
                <div class="sec-mini-fill" style="width: {largura_segura}%; background: {cor_barra};"></div>
            </div>
        </div>
    """


def _render_kpi_row_desktop(df_pass_ativas, df_est) -> None:
    total_ativas = max(len(df_pass_ativas), 1)
    aguardando_prec = len(
        df_pass_ativas[
            df_pass_ativas["Status"].isin([
                "Aguardando Precificação (Secretaria)",
                "Aguardando Precificação (Falta Peças no Estoque)",
            ])
        ]
    )
    aguardando_resp = len(
        df_pass_ativas[
            df_pass_ativas["Status"] == "Standby (Aguardando Resposta do Cliente)"
        ]
    )
    prontas_retirada = len(
        df_pass_ativas[
            df_pass_ativas["Status"].isin([
                "Serviço Concluído (Aguardando Notificação ao Cliente)",
                "Serviço Concluído (Aguardando Retirada)",
            ])
        ]
    )
    pecas_criticas = (
        len(df_est[df_est["Quantidade"] <= df_est["Minimo"]])
        if not df_est.empty
        else 0
    )
    total_est = max(len(df_est), 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        _render_kpi_card(
            "🧾",
            str(aguardando_prec),
            "Orçamentos p/ Precificar",
            "Fila",
            pct_barra=int((aguardando_prec / total_ativas) * 100),
            variante="amarelo",
        ),
        unsafe_allow_html=True,
    )
    c2.markdown(
        _render_kpi_card(
            "⏳",
            str(aguardando_resp),
            "Aguardando Cliente",
            "Standby",
            pct_barra=int((aguardando_resp / total_ativas) * 100),
            variante="azul",
        ),
        unsafe_allow_html=True,
    )
    c3.markdown(
        _render_kpi_card(
            "📦",
            str(prontas_retirada),
            "Concluídas / Retirada",
            "Entrega",
            pct_barra=int((prontas_retirada / total_ativas) * 100),
            variante="amarelo",
        ),
        unsafe_allow_html=True,
    )
    c4.markdown(
        _render_kpi_card(
            "⚠️",
            str(pecas_criticas),
            "Estoque no Mínimo",
            "Almoxarifado",
            pct_barra=int((pecas_criticas / total_est) * 100),
            variante="azul",
        ),
        unsafe_allow_html=True,
    )


def _render_anel_status_desktop(status_atual: str) -> None:
    mapa_progresso = {
        "Aguardando Precificação (Secretaria)": 25,
        "Aguardando Precificação (Falta Peças no Estoque)": 25,
        "Aguardando Envio ao Cliente": 45,
        "Standby (Aguardando Resposta do Cliente)": 65,
        "Serviço Concluído (Aguardando Notificação ao Cliente)": 85,
        "Serviço Concluído (Aguardando Retirada)": 95,
    }
    pct = mapa_progresso.get(str(status_atual), 50)
    st.markdown(
        f"""
        <div class="sec-ring-box">
            <div class="sec-ring-circle" style="background: conic-gradient(#F5B700 {pct}%, #EAF2FC {pct}% 100%);">
                <div class="sec-ring-inner">{pct}%</div>
            </div>
            <div class="sec-ring-meta">
                <div class="sec-ring-label">Etapa do Fluxo</div>
                <div class="sec-ring-status">{status_atual}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_acoes_passagem(row, is_mobile: bool, logar_acao, prefixo: str) -> None:
    id_pass = int(row["ID_Passagem"])
    st_atual = row["Status"]

    if st_atual in [
        "Aguardando Precificação (Secretaria)",
        "Aguardando Precificação (Falta Peças no Estoque)",
    ]:
        custo_pecas = calcular_custo_pecas_json(row.get("Pecas_Solicitadas"))
        with st.form(key=f"form_calc_{prefixo}_{id_pass}", clear_on_submit=True):
            mao_de_obra = st.number_input(
                "Mão de Obra (R$)", min_value=0.0, value=100.0, step=10.0
            )
            valor_total = custo_pecas + mao_de_obra
            st.markdown(f"**Total Final:** `{fmt_valor(valor_total)}`")
            if st.form_submit_button(
                "✅ Confirmar Cálculo & Liberar Envio",
                use_container_width=True,
            ):
                precificar_passagem(
                    id_pass, str(row["ID"]), valor_total, logar_acao
                )
                st.session_state.flash_sucesso = (
                    f"Orçamento #{id_pass} precificado!"
                )
                st.rerun()
    elif st_atual == "Aguardando Envio ao Cliente":
        if st.button(
            f"📨 Confirmar Envio ao Cliente (#{id_pass})",
            key=f"btn_env_{prefixo}_{id_pass}",
            use_container_width=True,
        ):
            enviar_orcamento_ao_cliente(
                id_pass, str(row["ID"]), row["Cliente_Nome"], logar_acao
            )
            st.session_state.flash_sucesso = "Envio ao cliente confirmado!"
            st.rerun()
    elif st_atual == "Standby (Aguardando Resposta do Cliente)":
        b1, b2 = st.columns(2)
        if b1.button(
            "✅ Cliente APROVOU",
            key=f"btn_aprov_{prefixo}_{id_pass}",
            use_container_width=True,
        ):
            novo_st = processar_resposta_cliente(
                id_pass,
                str(row["ID"]),
                row["Cliente_Nome"],
                True,
                row["Pecas_Solicitadas"],
                logar_acao,
            )
            st.session_state.flash_sucesso = (
                f"Aprovação registrada ({novo_st})!"
            )
            st.rerun()
        if b2.button(
            "❌ Cliente REPROVOU",
            key=f"btn_reprov_{prefixo}_{id_pass}",
            use_container_width=True,
        ):
            processar_resposta_cliente(
                id_pass,
                str(row["ID"]),
                row["Cliente_Nome"],
                False,
                row["Pecas_Solicitadas"],
                logar_acao,
            )
            st.session_state.flash_sucesso = "Orçamento recusado."
            st.rerun()
    elif (
        st_atual
        == "Serviço Concluído (Aguardando Notificação ao Cliente)"
    ):
        if st.button(
            f"📲 Confirmar Notificação ao Cliente (#{id_pass})",
            key=f"btn_notif_{prefixo}_{id_pass}",
            use_container_width=True,
        ):
            notificar_conclusao_cliente(
                id_pass, str(row["ID"]), row["Cliente_Nome"], logar_acao
            )
            st.session_state.flash_sucesso = "Cliente notificado!"
            st.rerun()
    elif st_atual == "Serviço Concluído (Aguardando Retirada)":
        if st.button(
            f"🏁 Confirmar Saída / Retirada (#{id_pass})",
            key=f"btn_saida_{prefixo}_{id_pass}",
            use_container_width=True,
        ):
            confirmar_saida_maquina(
                id_pass, str(row["ID"]), logar_acao
            )
            st.session_state.flash_sucesso = "Saída registrada!"
            st.rerun()


def _render_cockpit_mobile(df_pass_ativas, logar_acao) -> None:
    st.markdown(
        """
        <div class="mob-hub-hero">
            <h3>⚡ Central da Secretaria</h3>
            <p>Orçamentos, aprovação de clientes e retirada</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    fila = df_pass_ativas[
        df_pass_ativas["Status"].isin(STATUS_FILA_SECRETARIA)
    ].copy()
    if fila.empty:
        st.success("✅ Nenhuma pendência na fila no momento!")
        return

    opcoes_pend = [
        f"#{int(r['ID_Passagem'])} | Máq. {r['ID']} — {r['Cliente_Nome']}"
        for _, r in fila.iterrows()
    ]
    sel_pend = st.selectbox(
        "Selecione a passagem:", opcoes_pend, key="sec_mob_sel_pend"
    )
    row = fila.iloc[opcoes_pend.index(sel_pend)]

    st.markdown(
        f"""
        <div class="mob-sec-card">
            <div class="mob-sec-card-header">
                <b>#{int(row['ID_Passagem'])} • {row['Cliente_Nome']}</b>
                <span class="mob-sec-badge">{row['Status']}</span>
            </div>
            <div style="font-size: 0.82rem; color: #132238;">
                <b>Máquina:</b> {row['Modelo']} (ID {row['ID']})<br>
                <b>Orçamento:</b> {fmt_valor(row['Valor_Orcamento'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    exibir_galeria_imagens(
        row.get("Fotos_Cadastro"),
        "📸 Fotos na Chegada",
        is_mobile=True,
        cols_qtd=2,
    )
    exibir_galeria_imagens(
        row.get("Fotos_Laudo"),
        "🛠️ Fotos do Laudo",
        is_mobile=True,
        cols_qtd=2,
    )
    _render_acoes_passagem(
        row, is_mobile=True, logar_acao=logar_acao, prefixo="mob"
    )


def _render_cockpit_desktop(df_pass_ativas, df_est, logar_acao) -> None:
    soma_orcamentos = (
        float(df_pass_ativas["Valor_Orcamento"].fillna(0).sum())
        if not df_pass_ativas.empty and "Valor_Orcamento" in df_pass_ativas.columns
        else 0.0
    )

    st.markdown(
        f"""
        <div class="sec-topbar">
            <div>
                <p class="sec-topbar-title">Painel da Secretaria • Gestão de Fluxo e Orçamentos</p>
                <p class="sec-topbar-sub">Acompanhamento de passagens, aprovação de clientes, retirada e estoque</p>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span class="sec-pill-azul">Em aberto: {fmt_valor(soma_orcamentos)}</span>
                <span class="sec-pill-amarelo">Visão Desktop</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_kpi_row_desktop(df_pass_ativas, df_est)
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    fila = df_pass_ativas[
        df_pass_ativas["Status"].isin(STATUS_FILA_SECRETARIA)
    ].copy()

    col_esq, col_dir = st.columns([1.35, 1])

    with col_esq:
        with st.container(border=True):
            st.markdown(
                """
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Fila Operacional de Passagens</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if fila.empty:
                st.success("✅ Nenhuma pendência na fila no momento!")
            else:
                st.dataframe(
                    fila[
                        [
                            "ID_Passagem",
                            "ID",
                            "Cliente_Nome",
                            "Modelo",
                            "Status",
                            "Valor_Orcamento",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=265,
                )

    with col_dir:
        with st.container(border=True):
            st.markdown(
                """
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Ação Rápida na Passagem</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if fila.empty:
                st.info("Sem passagens pendentes para ação no momento.")
            else:
                opcoes_pend = [
                    f"#{int(r['ID_Passagem'])} | Máq. {r['ID']} — {r['Cliente_Nome']} [{r['Status']}]"
                    for _, r in fila.iterrows()
                ]
                sel_pend = st.selectbox(
                    "Selecione a passagem:", opcoes_pend, key="sec_desk_sel_pend"
                )
                row = fila.iloc[opcoes_pend.index(sel_pend)]

                _render_anel_status_desktop(row["Status"])

                st.caption(
                    f"Máquina: **{row['Modelo']}** • Orçamento atual: **{fmt_valor(row['Valor_Orcamento'])}**"
                )
                exibir_galeria_imagens(
                    row.get("Fotos_Cadastro"),
                    "📸 Fotos na Chegada",
                    is_mobile=False,
                    cols_qtd=2,
                )
                exibir_galeria_imagens(
                    row.get("Fotos_Laudo"),
                    "🛠️ Fotos do Laudo",
                    is_mobile=False,
                    cols_qtd=2,
                )
                _render_acoes_passagem(
                    row, is_mobile=False, logar_acao=logar_acao, prefixo="desk"
                )

    col_inf_esq, col_inf_dir = st.columns(2)

    with col_inf_esq:
        with st.container(border=True):
            st.markdown(
                """
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Resumo do Almoxarifado</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if df_est.empty:
                st.info("Nenhuma peça cadastrada.")
            else:
                st.dataframe(
                    df_est[
                        ["ID_Peca", "Nome", "Quantidade", "Minimo", "Preco_Unitario"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=175,
                )

    with col_inf_dir:
        with st.container(border=True):
            st.markdown(
                """
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Panorama de Aprovação e Retirada</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if df_pass_ativas.empty or "Status" not in df_pass_ativas.columns:
                st.info("Nenhuma passagem ativa no momento.")
            else:
                resumo_st = (
                    df_pass_ativas["Status"]
                    .value_counts()
                    .reset_index()
                )
                resumo_st.columns = ["Status", "Quantidade"]
                st.dataframe(
                    resumo_st,
                    use_container_width=True,
                    hide_index=True,
                    height=175,
                )


def _render_almoxarifado_secretaria(logar_acao) -> None:
    st.markdown(
        """
        <div class="sec-topbar">
            <div>
                <p class="sec-topbar-title">Almoxarifado • Entrada de Peças, Edição e Cadastro</p>
                <p class="sec-topbar-sub">Controle de estoque mínimo, reposição rápida e alteração de peças</p>
            </div>
            <span class="sec-pill-amarelo">Estoque</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_est = carregar_tabela("estoque").copy()

    with st.container(border=True):
        st.markdown(
            '<div class="sec-panel-header"><p class="sec-panel-title">Peças Cadastradas</p></div>',
            unsafe_allow_html=True,
        )
        if df_est.empty:
            st.info("Nenhuma peça cadastrada no estoque ainda.")
        else:
            st.dataframe(df_est, use_container_width=True, hide_index=True)

    col_ent, col_edit = st.columns(2)

    with col_ent:
        with st.container(border=True):
            st.markdown(
                '<div class="sec-panel-header"><p class="sec-panel-title">Dar Entrada / Repor Estoque</p></div>',
                unsafe_allow_html=True,
            )
            if df_est.empty:
                st.info("Cadastre uma peça primeiro ao lado.")
            else:
                peca_entrada = st.selectbox(
                    "Selecione a peça:",
                    df_est["Nome"].tolist(),
                    key="alm_sel_entrada",
                )
                qtd_entrada = st.number_input(
                    "Quantidade para adicionar:",
                    min_value=1,
                    value=1,
                    step=1,
                    key="alm_qtd_entrada",
                )
                if st.button(
                    "➕ Registrar Entrada no Estoque",
                    key="alm_btn_entrada",
                    use_container_width=True,
                ):
                    if callable(repor_estoque_peca) and callable(logar_acao):
                        repor_estoque_peca(
                            peca_entrada, int(qtd_entrada), logar_acao
                        )
                    else:
                        idx = df_est[df_est["Nome"] == peca_entrada].index[0]
                        df_est.loc[idx, "Quantidade"] = (
                            int(df_est.loc[idx, "Quantidade"])
                            + int(qtd_entrada)
                        )
                        salvar_tabela_df(df_est, "estoque")
                        if callable(logar_acao):
                            logar_acao(
                                "REPOSICAO_ESTOQUE",
                                f"Adicionadas {int(qtd_entrada)} unidade(s) de '{peca_entrada}'.",
                            )
                    st.session_state.flash_sucesso = (
                        f"+{int(qtd_entrada)} unidade(s) adicionadas em '{peca_entrada}'!"
                    )
                    st.rerun()

    with col_edit:
        with st.container(border=True):
            st.markdown(
                '<div class="sec-panel-header"><p class="sec-panel-title">Alterar Dados da Peça</p></div>',
                unsafe_allow_html=True,
            )
            if df_est.empty:
                st.info("Nenhuma peça disponível para alterar.")
            else:
                peca_alterar = st.selectbox(
                    "Peça para alterar:",
                    df_est["Nome"].tolist(),
                    key="alm_sel_alterar",
                )
                idx_alt = df_est[df_est["Nome"] == peca_alterar].index[0]
                row_alt = df_est.loc[idx_alt]

                with st.form("form_alterar_peca_sec"):
                    novo_nome = st.text_input(
                        "Nome da Peça:", value=str(row_alt["Nome"])
                    )
                    nova_qtd = st.number_input(
                        "Quantidade Atual:",
                        min_value=0,
                        value=int(row_alt.get("Quantidade", 0) or 0),
                        step=1,
                    )
                    novo_min = st.number_input(
                        "Estoque Mínimo:",
                        min_value=0,
                        value=int(row_alt.get("Minimo", 0) or 0),
                        step=1,
                    )
                    novo_preco = st.number_input(
                        "Preço Unitário (R$):",
                        min_value=0.0,
                        value=float(row_alt.get("Preco_Unitario", 0.0) or 0.0),
                        step=1.0,
                    )
                    if st.form_submit_button(
                        "💾 Salvar Alterações da Peça",
                        use_container_width=True,
                    ):
                        if not novo_nome.strip():
                            st.error("O nome da peça não pode ficar vazio.")
                        else:
                            df_est.loc[idx_alt, "Nome"] = novo_nome.strip()
                            df_est.loc[idx_alt, "Quantidade"] = int(nova_qtd)
                            df_est.loc[idx_alt, "Minimo"] = int(novo_min)
                            df_est.loc[idx_alt, "Preco_Unitario"] = float(
                                novo_preco
                            )
                            salvar_tabela_df(df_est, "estoque")
                            if callable(logar_acao):
                                logar_acao(
                                    "ALTERAR_PECA",
                                    f"Peça '{novo_nome.strip()}' atualizada (Qtd: {int(nova_qtd)}, Mín: {int(novo_min)}, Preço: {float(novo_preco):.2f}).",
                                )
                            st.session_state.flash_sucesso = (
                                f"Peça '{novo_nome.strip()}' atualizada!"
                            )
                            st.rerun()

    with st.container(border=True):
        st.markdown(
            '<div class="sec-panel-header"><p class="sec-panel-title">Cadastrar Nova Peça</p></div>',
            unsafe_allow_html=True,
        )
        with st.form("form_nova_peca_sec", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n_nome = c1.text_input("Nome da Nova Peça")
            n_qtd = c2.number_input("Qtd Inicial", min_value=0, value=1, step=1)
            n_min = c3.number_input("Mínimo", min_value=0, value=1, step=1)
            n_preco = c4.number_input(
                "Preço Unit. (R$)", min_value=0.0, value=10.0, step=1.0
            )
            if st.form_submit_button(
                "➕ Cadastrar Peça", use_container_width=True
            ):
                if not n_nome.strip():
                    st.error("Informe o nome da peça.")
                elif not df_est.empty and n_nome.strip().lower() in (
                    df_est["Nome"].astype(str).str.strip().str.lower().values
                ):
                    st.error("Já existe uma peça com esse nome.")
                else:
                    prox_id = f"PEC-{len(df_est) + 1:03d}"
                    if "ID_Peca" in df_est.columns and not df_est.empty:
                        prox_id = f"PEC-{len(df_est) + 1:03d}"
                    nova_linha = {
                        "ID_Peca": prox_id,
                        "Nome": n_nome.strip(),
                        "Quantidade": int(n_qtd),
                        "Minimo": int(n_min),
                        "Preco_Unitario": float(n_preco),
                    }
                    colunas_existentes = (
                        list(df_est.columns)
                        if not df_est.empty
                        else list(nova_linha.keys())
                    )
                    linha_filtrada = {
                        k: v for k, v in nova_linha.items() if k in colunas_existentes
                    }
                    df_att = pd.concat(
                        [df_est, pd.DataFrame([linha_filtrada])],
                        ignore_index=True,
                    )
                    salvar_tabela_df(df_att, "estoque")
                    if callable(logar_acao):
                        logar_acao(
                            "CADASTRO_PECA",
                            f"Nova peça '{n_nome.strip()}' cadastrada (Qtd: {int(n_qtd)}).",
                        )
                    st.session_state.flash_sucesso = (
                        f"Peça '{n_nome.strip()}' cadastrada!"
                    )
                    st.rerun()


def _render_maquinas_passagens_secretaria(df_pass_ativas) -> None:
    st.markdown(
        """
        <div class="sec-topbar">
            <div>
                <p class="sec-topbar-title">Máquinas e Passagens • Visão Consolidada</p>
                <p class="sec-topbar-sub">Consulta geral de equipamentos, clientes, status e valores</p>
            </div>
            <span class="sec-pill-amarelo">Operação</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        if df_pass_ativas is None or df_pass_ativas.empty:
            st.info("Nenhum registro encontrado.")
            return

        busca = st.text_input(
            "Buscar por ID da máquina, cliente, modelo ou status:",
            key="sec_busca_passagens",
        )
        df_show = df_pass_ativas.copy()
        if busca and busca.strip():
            termo = busca.strip().lower()
            mascara = df_show.apply(
                lambda r: termo in " ".join(str(v) for v in r.values).lower(),
                axis=1,
            )
            df_show = df_show[mascara]

        st.dataframe(df_show, use_container_width=True, hide_index=True)


def _render_logs_secretaria() -> None:
    st.markdown(
        """
        <div class="sec-topbar">
            <div>
                <p class="sec-topbar-title">Logs do Sistema • Auditoria de Ações</p>
                <p class="sec-topbar-sub">Histórico de logins, orçamentos, aprovações, saídas e estoque</p>
            </div>
            <span class="sec-pill-amarelo">Auditoria</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        try:
            df_logs = carregar_tabela("logs")
        except Exception:
            df_logs = pd.DataFrame()

        if df_logs is None or df_logs.empty:
            st.info("Nenhum log registrado até o momento.")
            return

        filtro_log = st.text_input(
            "Filtrar logs por usuário, ação ou detalhes:",
            key="sec_filtro_logs",
        )
        df_l = df_logs.iloc[::-1].copy()
        if filtro_log and filtro_log.strip():
            termo = filtro_log.strip().lower()
            mascara = df_l.apply(
                lambda r: termo in " ".join(str(v) for v in r.values).lower(),
                axis=1,
            )
            df_l = df_l[mascara]

        st.dataframe(
            df_l.head(200),
            use_container_width=True,
            hide_index=True,
            height=420,
        )


def renderizar_cockpit_secretaria(
    df_pass_ativas, df_est, is_mobile: bool, logar_acao
) -> None:
    if is_mobile:
        _render_cockpit_mobile(df_pass_ativas, logar_acao)
    else:
        _render_cockpit_desktop(df_pass_ativas, df_est, logar_acao)


def renderizar_visao_secretaria(
    is_mobile: bool = False,
    logar_acao=None,
    df_pass_ativas=None,
    df_est=None,
    render_nav=None,
    **kwargs,
) -> None:
    """Renderiza a visão da Secretaria com navegação lateral entre telas."""
    tela_atual = _render_menu_lateral_secretaria()

    dados_passagens = (
        df_pass_ativas if df_pass_ativas is not None else obter_visao_consolidada()
    )
    dados_estoque = df_est if df_est is not None else carregar_tabela("estoque")

    if tela_atual == "Almoxarifado":
        _render_almoxarifado_secretaria(logar_acao=logar_acao)
    elif tela_atual == "Máquinas e Passagens":
        _render_maquinas_passagens_secretaria(dados_passagens)
    elif tela_atual == "Logs do Sistema":
        _render_logs_secretaria()
    else:
        renderizar_cockpit_secretaria(
            df_pass_ativas=dados_passagens,
            df_est=dados_estoque,
            is_mobile=is_mobile,
            logar_acao=logar_acao,
        )