import json
import re

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_back_camera_input import back_camera_input

from repositories.oficina_repo import (
    carregar_tabela,
    excluir_maquina_e_historico,
    obter_historico_por_cliente,
    obter_passagens_por_maquina,
    obter_visao_consolidada,
)
from services.midia_service import decodificar_imagens, ler_qrcode_de_bytes


def validar_telefone(tel_str: str) -> str | None:
    apenas_numeros = re.sub(r"\D", "", tel_str or "")
    if 10 <= len(apenas_numeros) <= 11:
        return apenas_numeros
    return None


def fmt_data(val, fallback: str = "Pendente") -> str:
    if (
        val is None
        or (isinstance(val, float) and np.isnan(val))
        or str(val).strip() in ("", "None", "nan")
    ):
        return fallback
    return str(val)


def fmt_valor(val) -> str:
    try:
        return f"R$ {float(val):.2f}"
    except Exception:
        return "R$ 0.00"


def exibir_galeria_imagens(
    json_str: str,
    titulo: str = "📷 Fotos Anexadas",
    is_mobile: bool = False,
    cols_qtd: int = 3,
) -> None:
    imagens = decodificar_imagens(json_str)
    if not imagens:
        return

    st.markdown(f"**{titulo} ({len(imagens)})**")
    qtd_col = 2 if is_mobile else min(cols_qtd, len(imagens))
    for i in range(0, len(imagens), qtd_col):
        row_cols = st.columns(qtd_col)
        for idx_c, item in enumerate(imagens[i : i + qtd_col]):
            row_cols[idx_c].image(
                item["bytes"], caption=item["nome"], use_container_width=True
            )


def renderizar_cronologia_html(passagem) -> str:
    return f"""
        <hr style="border-color: #C8D9EE; margin: 8px 0;">
        <p style="margin: 3px 0;"><b>📅 Chegada:</b> {fmt_data(passagem.get('Data_Hora_Entrada'))} | <b>📋 Laudo:</b> {fmt_data(passagem.get('Data_Hora_Laudo'))}</p>
        <p style="margin: 3px 0;"><b>📤 Enviado Cliente:</b> {fmt_data(passagem.get('Data_Hora_Envio_Orcamento'))} | <b>✍️ Resposta:</b> {fmt_data(passagem.get('Data_Hora_Resposta_Cliente'))}</p>
        <p style="margin: 3px 0;"><b>▶️ Início Serviço:</b> {fmt_data(passagem.get('Data_Hora_Inicio_Servico'))} | <b>🏁 Conclusão:</b> {fmt_data(passagem.get('Data_Hora_Conclusao_Servico'))}</p>
        <p style="margin: 3px 0;"><b>📲 Notificado:</b> {fmt_data(passagem.get('Data_Hora_Notificacao_Conclusao'))} | <b>🚚 Saída:</b> {fmt_data(passagem.get('Data_Hora_Saida'))}</p>
    """


def renderizar_cronologia_texto(passagem) -> str:
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


def exibir_banco_passagens_maquina(
    id_maquina: str,
    titulo_secao: str = "🗂️ Histórico de Passagens da Máquina",
    is_mobile: bool = False,
) -> None:
    df_p = obter_passagens_por_maquina(id_maquina)
    st.markdown(f"**{titulo_secao} ({len(df_p)} registrada(s))**")
    if df_p.empty:
        st.info("Esta máquina possui 0 passagens/orçamentos registrados.")
        return

    df_resumo = df_p[
        [
            "ID_Passagem",
            "Status",
            "Valor_Orcamento",
            "Data_Hora_Entrada",
            "Data_Hora_Conclusao_Servico",
            "Data_Hora_Saida",
        ]
    ].copy()
    st.dataframe(
        df_resumo, use_container_width=True, hide_index=True, height=180
    )

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
    exibir_galeria_imagens(
        p.get("Fotos_Laudo"),
        "🛠️ Fotos Anexadas no Laudo",
        is_mobile=is_mobile,
        cols_qtd=3,
    )
    if p.get("Pecas_Solicitadas"):
        try:
            p_list = json.loads(p["Pecas_Solicitadas"])
            if p_list:
                st.dataframe(
                    pd.DataFrame(p_list),
                    use_container_width=True,
                    hide_index=True,
                    height=130,
                )
        except Exception:
            pass


def renderizar_ficha_completa_maquina(
    maq_info, is_mobile: bool = False
) -> None:
    id_maq = str(maq_info["ID"])
    df_p = obter_passagens_por_maquina(id_maq)
    ultima = df_p.iloc[0] if not df_p.empty else None

    status_atual = (
        ultima["Status"] if ultima is not None else "Sem Passagem Aberta"
    )
    laudo_atual = ultima["Descricao_Laudo"] if ultima is not None else "N/A"
    anomalias_atual = ultima["Anomalias"] if ultima is not None else "Nenhuma"
    valor_atual = (
        float(ultima["Valor_Orcamento"]) if ultima is not None else 0.0
    )
    mec_laudo = fmt_data(
        ultima.get("Mecanico_Laudo") if ultima is not None else None, "N/A"
    )
    mec_exec = fmt_data(
        ultima.get("Mecanico_Execucao") if ultima is not None else None, "N/A"
    )
    cronologia_html = (
        renderizar_cronologia_html(ultima)
        if ultima is not None
        else "<hr><p><i>Nenhuma passagem registrada para esta máquina ainda.</i></p>"
    )

    st.markdown(
        f"""
        <div style="border: 2px solid #1D5FA7; border-left: 6px solid #F5B700; padding: 14px; border-radius: 10px; background-color: #FFFFFF; color: #132238; font-size: 0.9rem;">
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

    exibir_galeria_imagens(
        maq_info.get("Fotos_Cadastro"),
        "📸 Fotos na Chegada / Cadastro",
        is_mobile=is_mobile,
        cols_qtd=3,
    )
    exibir_banco_passagens_maquina(id_maq, is_mobile=is_mobile)


def renderizar_visao_historica_cliente(
    contexto_key: str = "default",
    compacto: bool = False,
    is_mobile: bool = False,
) -> None:
    df_cli = carregar_tabela("clientes")
    if df_cli.empty:
        st.info("Nenhum cliente cadastrado no sistema.")
        return

    c_busca, c_sel = (
        st.columns([1, 1.4]) if not is_mobile else (st.container(), st.container())
    )
    filtro_cli = c_busca.text_input(
        "Buscar cliente (nome/ID/tel):",
        key=f"filtro_cli_{contexto_key}",
    )

    df_cli_view = df_cli.copy()
    if filtro_cli.strip():
        termo = filtro_cli.strip().lower()
        df_cli_view = df_cli_view[
            df_cli_view["Nome"].str.lower().str.contains(termo, na=False)
            | df_cli_view["ID_Cliente"]
            .str.lower()
            .str.contains(termo, na=False)
            | df_cli_view["Telefone"]
            .astype(str)
            .str.lower()
            .str.contains(termo, na=False)
        ]

    if df_cli_view.empty:
        st.warning("Nenhum cliente corresponde ao filtro informado.")
        return

    opcoes_cli = [
        f"{r['ID_Cliente']} — {r['Nome']} ({r['Telefone']})"
        for _, r in df_cli_view.iterrows()
    ]
    sel_cli = c_sel.selectbox(
        "Cliente:", opcoes_cli, key=f"sel_cli_{contexto_key}"
    )
    cli_row = df_cli_view.iloc[opcoes_cli.index(sel_cli)]
    id_cli = str(cli_row["ID_Cliente"])

    maquinas_cli, passagens_cli = obter_historico_por_cliente(id_cli)

    status_encerrados = {"Entregue / Retirado", "Orçamento Recusado"}
    em_andamento_qtd = (
        int((~passagens_cli["Status"].isin(status_encerrados)).sum())
        if not passagens_cli.empty
        else 0
    )

    total_orcado = 0.0
    if not passagens_cli.empty:
        validos = passagens_cli[
            passagens_cli["Status"] != "Orçamento Recusado"
        ]
        total_orcado = float(
            pd.to_numeric(validos["Valor_Orcamento"], errors="coerce")
            .fillna(0.0)
            .sum()
        )

    if is_mobile:
        m1, m2 = st.columns(2)
        m1.metric("Máquinas", len(maquinas_cli))
        m2.metric("Passagens", len(passagens_cli))
        m3, m4 = st.columns(2)
        m3.metric("Em Andamento", em_andamento_qtd)
        m4.metric("Total Orçado", fmt_valor(total_orcado))
    else:
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
            maquinas_cli[
                [
                    "ID",
                    "Modelo",
                    "Total_Passagens",
                    "Ultimo_Status",
                    "Data_Hora_Cadastro",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            height=altura_tab,
        )

    st.markdown("**🗂️ Histórico de Passagens**")
    if passagens_cli.empty:
        st.info("Nenhuma passagem registrada para as máquinas deste cliente.")
        return

    col_f1, col_f2 = (
        st.columns(2) if not is_mobile else (st.container(), st.container())
    )
    ids_maq_cli = ["Todas"] + sorted(
        maquinas_cli["ID"].astype(str).unique().tolist()
    )
    status_cli = ["Todos"] + sorted(
        passagens_cli["Status"].dropna().astype(str).unique().tolist()
    )

    filtro_maq = col_f1.selectbox(
        "Máquina:", ids_maq_cli, key=f"f_maq_{contexto_key}"
    )
    filtro_st = col_f2.selectbox(
        "Status:", status_cli, key=f"f_st_{contexto_key}"
    )

    passagens_filtradas = passagens_cli.copy()
    if filtro_maq != "Todas":
        passagens_filtradas = passagens_filtradas[
            passagens_filtradas["ID_Maquina"].astype(str) == filtro_maq
        ]
    if filtro_st != "Todos":
        passagens_filtradas = passagens_filtradas[
            passagens_filtradas["Status"] == filtro_st
        ]

    if passagens_filtradas.empty:
        st.info("Nenhuma passagem encontrada com os filtros selecionados.")
        return

    st.dataframe(
        passagens_filtradas[
            [
                "ID_Passagem",
                "ID_Maquina",
                "Modelo",
                "Status",
                "Valor_Orcamento",
                "Data_Hora_Entrada",
                "Data_Hora_Saida",
            ]
        ],
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
    p = passagens_filtradas[
        passagens_filtradas["ID_Passagem"] == sel_pass_cli
    ].iloc[0]
    st.caption(
        f"**Laudo:** {fmt_data(p.get('Descricao_Laudo'))} | **Anomalias:** {fmt_data(p.get('Anomalias'), 'Nenhuma')} | "
        f"**Mecânicos:** {fmt_data(p.get('Mecanico_Laudo'), 'Pendente')} / {fmt_data(p.get('Mecanico_Execucao'), 'Pendente')}"
    )
    st.markdown(renderizar_cronologia_texto(p))
    exibir_galeria_imagens(
        p.get("Fotos_Laudo"),
        "🛠️ Fotos do Laudo",
        is_mobile=is_mobile,
        cols_qtd=3,
    )


def renderizar_tabela_com_busca(
    titulo: str = "📊 Visão Geral das Máquinas e Passagens",
    compacto: bool = False,
    is_mobile: bool = False,
    perfil_logado: str | None = None,
    logar_acao_fn=None,
) -> None:
    if not compacto:
        st.subheader(titulo)
    df_maq_base = carregar_tabela("maquinas")
    if df_maq_base.empty:
        st.info("Nenhuma máquina cadastrada no sistema.")
        return

    df_maq = obter_visao_consolidada()
    altura_tabela = 200 if (compacto or is_mobile) else 320

    tab_busca_txt, tab_ficha_id, tab_scan_qr = st.tabs([
        "🔍 Buscar Máquinas",
        "📋 Ficha & Passagens",
        "📷 Leitor QR",
    ])

    with tab_busca_txt:
        termo_busca = st.text_input(
            "Buscar por Cliente, ID da Máquina, Modelo ou Status:",
            key=f"busca_{titulo}_{compacto}",
        )
        df_exibicao = df_maq.copy()
        if termo_busca:
            termo = termo_busca.lower()
            df_exibicao = df_exibicao[
                df_exibicao["Cliente_Nome"]
                .str.lower()
                .str.contains(termo, na=False)
                | df_exibicao["ID"].str.lower().str.contains(termo, na=False)
                | df_exibicao["Modelo"]
                .str.lower()
                .str.contains(termo, na=False)
                | df_exibicao["Status"]
                .str.lower()
                .str.contains(termo, na=False)
            ]

        cols_tab = (
            ["ID", "Cliente_Nome", "Modelo", "Status", "Valor_Orcamento"]
            if is_mobile
            else [
                "ID",
                "Cliente_Nome",
                "Modelo",
                "ID_Passagem",
                "Status",
                "Valor_Orcamento",
                "Data_Hora_Entrada",
            ]
        )
        st.dataframe(
            df_exibicao[cols_tab],
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
            renderizar_ficha_completa_maquina(row_maq, is_mobile=is_mobile)

            if perfil_logado == "Secretaria (Administração)":
                if st.button(
                    "🗑️ Excluir Máquina e Histórico",
                    key=f"btn_exc_{id_detalhe}_{compacto}",
                    use_container_width=True,
                ):
                    excluir_maquina_e_historico(str(id_detalhe))
                    if logar_acao_fn:
                        logar_acao_fn(
                            "EXCLUIR_MAQUINA",
                            f"Máquina ID {id_detalhe} e suas passagens removidas do cadastro.",
                        )
                    st.session_state.flash_sucesso = (
                        f"Máquina {id_detalhe} removida com sucesso!"
                    )
                    st.rerun()

    with tab_scan_qr:
        foto_capturada = back_camera_input(key=f"back_cam_{titulo}_{compacto}")
        if foto_capturada is not None:
            codigo_lido = ler_qrcode_de_bytes(foto_capturada.getvalue())
            if codigo_lido:
                st.success(f"🎯 QR Code Lido: **{codigo_lido}**")
                maq_encontrada = df_maq_base[
                    df_maq_base["QR_Code"].str.contains(
                        codigo_lido, case=False, na=False
                    )
                    | df_maq_base["ID"].str.contains(
                        codigo_lido, case=False, na=False
                    )
                ]
                if not maq_encontrada.empty:
                    renderizar_ficha_completa_maquina(
                        maq_encontrada.iloc[0], is_mobile=is_mobile
                    )
                else:
                    st.warning(f"⚠️ Código '{codigo_lido}' não encontrado.")
            else:
                st.error("❌ Nenhum QR Code nítido detectado.")