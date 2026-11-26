import json
import streamlit as st

from repositories.oficina_repo import carregar_tabela
from services.fluxo_service import (
    calcular_custo_pecas_json,
    confirmar_saida_maquina,
    enviar_orcamento_ao_cliente,
    notificar_conclusao_cliente,
    precificar_passagem,
    processar_resposta_cliente,
)
from ui.components import exibir_galeria_imagens, fmt_valor


def _render_kpi_card(
    icone: str,
    valor: str,
    label: str,
    tag: str,
    variante: str = "azul",
) -> str:
    borda_classe = (
        "destaque-amarelo" if variante == "amarelo" else "destaque-azul"
    )
    icone_classe = "amarelo" if variante == "amarelo" else ""
    return f"""
        <div class="sec-kpi-card {borda_classe}">
            <div class="sec-kpi-top">
                <span class="sec-kpi-icone {icone_classe}">{icone}</span>
                <span class="sec-kpi-tag">{tag}</span>
            </div>
            <div class="sec-kpi-valor">{valor}</div>
            <div class="sec-kpi-label">{label}</div>
        </div>
    """


def _render_kpi_row_desktop(df_pass_ativas, df_est) -> None:
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

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        _render_kpi_card(
            "🧾",
            str(aguardando_prec),
            "Orçamentos p/ Precificar",
            "Fila",
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
            variante="azul",
        ),
        unsafe_allow_html=True,
    )


def _render_cockpit_desktop(df_pass_ativas, df_est, logar_acao) -> None:
    st.markdown(
        """
        <div class="sec-topbar">
            <div>
                <p class="sec-topbar-title">Painel da Secretaria • Gestão de Fluxo e Orçamentos</p>
                <p class="sec-topbar-sub">Acompanhamento de passagens, aprovação de clientes, retirada e estoque</p>
            </div>
            <span class="sec-pill-amarelo">Visão Desktop</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_kpi_row_desktop(df_pass_ativas, df_est)
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    status_acao = [
        "Aguardando Precificação (Falta Peças no Estoque)",
        "Aguardando Precificação (Secretaria)",
        "Aguardando Envio ao Cliente",
        "Standby (Aguardando Resposta do Cliente)",
        "Serviço Concluído (Aguardando Notificação ao Cliente)",
        "Serviço Concluído (Aguardando Retirada)",
    ]
    fila = df_pass_ativas[df_pass_ativas["Status"].isin(status_acao)].copy()

    col_esq, col_dir = st.columns([1.35, 1])

    with col_esq:
        st.markdown(
            """
            <div class="sec-panel-card">
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Fila Operacional de Passagens</p>
                </div>
            """,
            unsafe_allow_html=True,
        )
        if fila.empty:
            st.success("✅ Nenhuma pendência na fila no momento!")
            st.markdown("</div>", unsafe_allow_html=True)
            return

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
            height=250,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Resumo rápido de estoque crítico na parte inferior esquerda (estilo cards inferiores do print)
        st.markdown(
            """
            <div class="sec-panel-card">
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
                df_est[["ID_Peca", "Nome", "Quantidade", "Minimo", "Preco_Unitario"]],
                use_container_width=True,
                hide_index=True,
                height=160,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_dir:
        st.markdown(
            """
            <div class="sec-panel-card">
                <div class="sec-panel-header">
                    <p class="sec-panel-title">Ação Rápida na Passagem</p>
                </div>
            """,
            unsafe_allow_html=True,
        )
        opcoes_pend = [
            f"#{int(r['ID_Passagem'])} | Máq. {r['ID']} — {r['Cliente_Nome']} [{r['Status']}]"
            for _, r in fila.iterrows()
        ]
        sel_pend = st.selectbox(
            "Selecione a passagem:", opcoes_pend, key="sec_desk_sel_pend"
        )
        row = fila.iloc[opcoes_pend.index(sel_pend)]
        id_pass = int(row["ID_Passagem"])
        st_atual = row["Status"]

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

        if st_atual in [
            "Aguardando Precificação (Secretaria)",
            "Aguardando Precificação (Falta Peças no Estoque)",
        ]:
            custo_pecas = calcular_custo_pecas_json(row.get("Pecas_Solicitadas"))
            with st.form(key=f"form_calc_desk_{id_pass}", clear_on_submit=True):
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
                use_container_width=True,
            ):
                enviar_orcamento_ao_cliente(
                    id_pass, str(row["ID"]), row["Cliente_Nome"], logar_acao
                )
                st.session_state.flash_sucesso = "Envio ao cliente confirmado!"
                st.rerun()
        elif st_atual == "Standby (Aguardando Resposta do Cliente)":
            b1, b2 = st.columns(2)
            if b1.button("✅ Cliente APROVOU", use_container_width=True):
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
            if b2.button("❌ Cliente REPROVOU", use_container_width=True):
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
                use_container_width=True,
            ):
                confirmar_saida_maquina(
                    id_pass, str(row["ID"]), logar_acao
                )
                st.session_state.flash_sucesso = "Saída registrada!"
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)