import datetime
import json

import streamlit as st

from repositories.logs_repo import listar_logs
from repositories.oficina_repo import (
    carregar_tabela,
    obter_visao_consolidada,
    salvar_tabela_df,
)
from services.fluxo_service import (
    confirmar_saida_maquina,
    enviar_orcamento_ao_cliente,
    notificar_conclusao_cliente,
    precificar_passagem,
    processar_resposta_cliente,
)
from ui.components import (
    exibir_galeria_imagens,
    fmt_valor,
    renderizar_tabela_com_busca,
    renderizar_visao_historica_cliente,
)

TELAS_SECRETARIA = [
    "Cockpit",
    "Máquinas e Passagens",
    "Histórico por Cliente",
    "Estoque",
    "Mecânicos",
    "Logs",
]

ROTULOS_SECRETARIA = {
    "Cockpit": "⚡ Cockpit",
    "Máquinas e Passagens": "🔍 Máquinas",
    "Histórico por Cliente": "👤 Clientes",
    "Estoque": "📦 Estoque",
    "Mecânicos": "👥 Mecânicos",
    "Logs": "📜 Logs",
}

MODULOS_SECRETARIA_HUB = [
    {
        "icone": "⚡",
        "titulo": "Orçamentos / Cockpit",
        "destino": "Cockpit",
        "descricao": "Precificação, envio, aprovação e saída.",
    },
    {
        "icone": "🔍",
        "titulo": "Buscar Máquinas",
        "destino": "Máquinas e Passagens",
        "descricao": "Consultar máquinas, QR Code e fotos.",
    },
    {
        "icone": "👤",
        "titulo": "Histórico por Cliente",
        "destino": "Histórico por Cliente",
        "descricao": "Máquinas e passagens por cliente.",
    },
    {
        "icone": "📦",
        "titulo": "Estoque",
        "destino": "Estoque",
        "descricao": "Reposição, alertas e cadastro de peças.",
    },
    {
        "icone": "👥",
        "titulo": "Mecânicos",
        "destino": "Mecânicos",
        "descricao": "Gerenciar usuários da oficina.",
    },
    {
        "icone": "📜",
        "titulo": "Logs",
        "destino": "Logs",
        "descricao": "Auditoria e exportação CSV.",
    },
]


def _render_cockpit(df_pass_ativas, is_mobile: bool, logar_acao) -> None:
    st.markdown(
        '<div class="cockpit-box-title">⚡ Central de Orçamentos & Fluxo</div>',
        unsafe_allow_html=True,
    )
    status_acao = [
        "Aguardando Precificação (Falta Peças no Estoque)",
        "Aguardando Precificação (Secretaria)",
        "Aguardando Envio ao Cliente",
        "Standby (Aguardando Resposta do Cliente)",
        "Serviço Concluído (Aguardando Notificação ao Cliente)",
        "Serviço Concluído (Aguardando Retirada)",
    ]
    fila = df_pass_ativas[df_pass_ativas["Status"].isin(status_acao)].copy()
    if fila.empty:
        st.success("✅ Nenhuma pendência na fila no momento!")
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
        height=180,
    )
    opcoes_pend = [
        f"#{int(r['ID_Passagem'])} | Máq. {r['ID']} ({r['Modelo']}) — {r['Cliente_Nome']} [{r['Status']}]"
        for _, r in fila.iterrows()
    ]
    sel_pend = st.selectbox("Selecione o item para agir:", opcoes_pend)
    row = fila.iloc[opcoes_pend.index(sel_pend)]
    id_pass = int(row["ID_Passagem"])
    st_atual = row["Status"]

    exibir_galeria_imagens(
        row.get("Fotos_Cadastro"),
        "📸 Fotos na Chegada",
        is_mobile=is_mobile,
        cols_qtd=2,
    )
    exibir_galeria_imagens(
        row.get("Fotos_Laudo"),
        "🛠️ Fotos do Laudo",
        is_mobile=is_mobile,
        cols_qtd=2,
    )

    if st_atual in [
        "Aguardando Precificação (Secretaria)",
        "Aguardando Precificação (Falta Peças no Estoque)",
    ]:
        custo_pecas = 0.0
        try:
            pecas = json.loads(row["Pecas_Solicitadas"])
            if pecas:
                custo_pecas = sum(
                    item["qtd"] * item["preco_unit"] for item in pecas
                )
        except Exception:
            pass
        with st.form(key=f"form_calc_{id_pass}", clear_on_submit=True):
            mao_de_obra = st.number_input(
                "Mão de Obra (R$)", min_value=0.0, value=100.0, step=10.0
            )
            valor_total = custo_pecas + mao_de_obra
            st.markdown(f"**Total Final:** `{fmt_valor(valor_total)}`")
            if st.form_submit_button(
                "✅ Confirmar Cálculo & Liberar Envio", use_container_width=True
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
            confirmar_saida_maquina(id_pass, str(row["ID"]), logar_acao)
            st.session_state.flash_sucesso = "Saída registrada!"
            st.rerun()


def renderizar_visao_secretaria(
    is_mobile: bool,
    logar_acao,
    encerrar_sessao,
    render_grade,
    render_nav,
) -> None:
    tela_sec_ativa = st.session_state.tela_secretaria
    if tela_sec_ativa == "Início":
        render_nav(TELAS_SECRETARIA, "tela_secretaria", ROTULOS_SECRETARIA)
        render_grade(
            MODULOS_SECRETARIA_HUB,
            "tela_secretaria",
            "💻 Administração / Secretaria — Painel Inicial",
            "Toque em um botão para abrir a tela correspondente.",
        )
        st.markdown(
            '<div class="login-mobile-only" style="margin-top: 10px;">',
            unsafe_allow_html=True,
        )
        if st.button(
            "🚪 Sair da Conta", key="mob_logout_sec", use_container_width=True
        ):
            encerrar_sessao()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    render_nav(TELAS_SECRETARIA, "tela_secretaria", ROTULOS_SECRETARIA)
    df_pass_ativas = obter_visao_consolidada()
    df_pass_ativas = df_pass_ativas[
        df_pass_ativas["ID_Passagem"].notna()
    ].copy()
    df_est = carregar_tabela("estoque")

    if tela_sec_ativa == "Máquinas e Passagens":
        renderizar_tabela_com_busca(
            "🔍 Buscar Máquinas e Passagens",
            compacto=is_mobile,
            is_mobile=is_mobile,
            perfil_logado=st.session_state.perfil_logado,
            logar_acao_fn=logar_acao,
        )
    elif tela_sec_ativa == "Histórico por Cliente":
        renderizar_visao_historica_cliente(
            contexto_key="sec_tela",
            compacto=is_mobile,
            is_mobile=is_mobile,
        )
    elif tela_sec_ativa == "Estoque":
        st.dataframe(
            df_est, use_container_width=True, hide_index=True, height=220
        )
        with st.form("form_repor_peca", clear_on_submit=True):
            peca_repor = st.selectbox("Peça:", df_est["Nome"])
            qtd_add = st.number_input(
                "Qtd a adicionar:", min_value=1, value=5, step=1
            )
            if st.form_submit_button(
                "Confirmar Entrada no Estoque", use_container_width=True
            ):
                idx_p = df_est[df_est["Nome"] == peca_repor].index[0]
                df_est.loc[idx_p, "Quantidade"] += qtd_add
                salvar_tabela_df(df_est, "estoque")
                logar_acao(
                    "REPOSICAO_ESTOQUE",
                    f"+{qtd_add} unidade(s) de '{peca_repor}'.",
                )
                st.session_state.flash_sucesso = (
                    f"+{qtd_add}x '{peca_repor}' adicionadas!"
                )
                st.rerun()
    elif tela_sec_ativa == "Mecânicos":
        df_usr = carregar_tabela("usuarios")
        st.dataframe(
            df_usr[df_usr["Perfil"] == "Mecânico (Oficina)"][
                ["Usuario", "Nome"]
            ],
            use_container_width=True,
            hide_index=True,
            height=200,
        )
    elif tela_sec_ativa == "Logs":
        df_logs = listar_logs()
        if df_logs.empty:
            st.info("Nenhum log registrado.")
        else:
            st.dataframe(
                df_logs, use_container_width=True, hide_index=True, height=260
            )
            st.download_button(
                label="⬇️ Exportar Logs (CSV)",
                data=df_logs.to_csv(index=False).encode("utf-8"),
                file_name=f"logs_oficina_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        _render_cockpit(df_pass_ativas, is_mobile, logar_acao)