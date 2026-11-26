import streamlit as st

from repositories.oficina_repo import carregar_tabela, obter_visao_consolidada
from services.fluxo_service import (
    calcular_custo_pecas_json,
    confirmar_saida_maquina,
    enviar_orcamento_ao_cliente,
    notificar_conclusao_cliente,
    precificar_passagem,
    processar_resposta_cliente,
)
from ui.components import exibir_galeria_imagens, fmt_valor

STATUS_FILA_SECRETARIA = [
    "Aguardando Precificação (Falta Peças no Estoque)",
    "Aguardando Precificação (Secretaria)",
    "Aguardando Envio ao Cliente",
    "Standby (Aguardando Resposta do Cliente)",
    "Serviço Concluído (Aguardando Notificação ao Cliente)",
    "Serviço Concluído (Aguardando Retirada)",
]


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
    """Renderiza a visão principal da Secretaria compatível com a chamada do app.py."""
    if "tela_secretaria" not in st.session_state:
        st.session_state.tela_secretaria = "Início"

    if callable(render_nav):
        render_nav()

    dados_passagens = (
        df_pass_ativas if df_pass_ativas is not None else obter_visao_consolidada()
    )
    dados_estoque = df_est if df_est is not None else carregar_tabela("estoque")

    renderizar_cockpit_secretaria(
        df_pass_ativas=dados_passagens,
        df_est=dados_estoque,
        is_mobile=is_mobile,
        logar_acao=logar_acao,
    )