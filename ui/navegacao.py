import streamlit as st

from repositories.logs_repo import registrar_log
from repositories.oficina_repo import carregar_tabela

try:
    from streamlit_javascript import st_javascript

    HAS_ST_JS = True
except Exception:
    HAS_ST_JS = False


def detectar_mobile() -> bool:
    """Detecta se a largura da janela corresponde a dispositivo mobile (<= 768px)."""
    if not HAS_ST_JS:
        return False
    try:
        largura_tela = st_javascript("window.innerWidth", key="detect_inner_width")
    except Exception:
        largura_tela = None

    # Salva no session_state para não perder o valor entre reruns
    if isinstance(largura_tela, (int, float)) and largura_tela > 0:
        st.session_state["largura_tela_cache"] = largura_tela

    largura_final = st.session_state.get("largura_tela_cache")
    return bool(largura_final and largura_final <= 768)


def criar_logger_sessao():
    """Retorna uma função (acao, detalhes) vinculada ao usuário e perfil atuais."""

    def _logar(acao: str, detalhes: str) -> None:
        registrar_log(
            acao=acao,
            detalhes=detalhes,
            usuario=st.session_state.get("usuario_logado"),
            perfil=st.session_state.get("perfil_logado"),
        )

    return _logar


def encerrar_sessao(logar_acao) -> None:
    """Registra logout e limpa os estados de autenticação e tela."""
    nome_saindo = st.session_state.get("usuario_logado")
    if nome_saindo:
        logar_acao("LOGOUT", f"Usuário '{nome_saindo}' encerrou a sessão.")
    st.session_state.usuario_logado = None
    st.session_state.perfil_logado = None
    st.session_state.tela_mecanico = "Início"
    st.session_state.tela_secretaria = "Início"


def _processar_login(usuario_txt: str, senha_txt: str) -> None:
    df_usuarios = carregar_tabela("usuarios")
    match = df_usuarios[
        (df_usuarios["Usuario"] == usuario_txt.strip())
        & (df_usuarios["Senha"] == senha_txt.strip())
    ]
    if not match.empty:
        nome_usuario = match.iloc[0]["Nome"]
        perfil_usuario = match.iloc[0]["Perfil"]
        st.session_state.usuario_logado = nome_usuario
        st.session_state.perfil_logado = perfil_usuario
        st.session_state.tela_mecanico = "Início"
        st.session_state.tela_secretaria = "Início"
        st.session_state.flash_sucesso = "Login efetuado com sucesso!"
        registrar_log(
            acao="LOGIN",
            detalhes=f"Usuário '{usuario_txt.strip()}' ({nome_usuario}) entrou no sistema.",
            usuario=nome_usuario,
            perfil=perfil_usuario,
        )
        st.rerun()
    else:
        registrar_log(
            acao="LOGIN_FALHA",
            detalhes=f"Tentativa de login inválida com usuário '{usuario_txt.strip()}'.",
        )
        st.error("Usuário ou senha incorretos.")


def renderizar_autenticacao(is_mobile: bool, logar_acao) -> bool:
    """Renderiza login quando não autenticado ou status/logout na sidebar.

    Retorna True se o usuário está autenticado e o fluxo pode prosseguir.
    """
    st.sidebar.markdown("### 🔐 Autenticação de Usuário")

    if st.session_state.usuario_logado is None:
        st.sidebar.subheader("Fazer Login no Sistema")
        with st.sidebar.form("form_login_side"):
            user_input_s = st.text_input("Usuário")
            senha_input_s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                _processar_login(user_input_s, senha_input_s)

        st.markdown('<div class="login-mobile-only">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### 🔐 Entrar no Sistema")
            with st.form("form_login_mobile"):
                user_input_m = st.text_input("Usuário", key="mob_user")
                senha_input_m = st.text_input(
                    "Senha", type="password", key="mob_pass"
                )
                if st.form_submit_button("Entrar", use_container_width=True):
                    _processar_login(user_input_m, senha_input_m)
        st.markdown("</div>", unsafe_allow_html=True)

        if not is_mobile:
            st.info(
                "👈 Digite suas credenciais na barra lateral para acessar o sistema."
            )
        return False

    st.sidebar.success(
        f"Conectado: **{st.session_state.usuario_logado}**\n\nPerfil: *{st.session_state.perfil_logado}*"
    )
    if st.sidebar.button("Sair (Logout)", use_container_width=True):
        encerrar_sessao(logar_acao)
        st.rerun()
    st.sidebar.markdown("---")
    return True


def renderizar_notificacoes_sidebar() -> None:
    """Exibe notificações de pendências na sidebar conforme o perfil ativo."""
    df_passagens = carregar_tabela("passagens_oficina")
    st.sidebar.subheader("🔔 Notificações do Sistema")

    perfil = st.session_state.get("perfil_logado")
    if perfil == "Secretaria (Administração)":
        pend_prec = (
            len(
                df_passagens[
                    df_passagens["Status"].isin([
                        "Aguardando Precificação (Secretaria)",
                        "Aguardando Precificação (Falta Peças no Estoque)",
                    ])
                ]
            )
            if not df_passagens.empty
            else 0
        )
        pend_env = (
            len(
                df_passagens[
                    df_passagens["Status"] == "Aguardando Envio ao Cliente"
                ]
            )
            if not df_passagens.empty
            else 0
        )
        pend_notif = (
            len(
                df_passagens[
                    df_passagens["Status"]
                    == "Serviço Concluído (Aguardando Notificação ao Cliente)"
                ]
            )
            if not df_passagens.empty
            else 0
        )
        if pend_prec > 0:
            st.sidebar.warning(
                f"📥 **{pend_prec}** orçamento(s) para precificação."
            )
        if pend_env > 0:
            st.sidebar.info(
                f"📤 **{pend_env}** orçamento(s) para enviar ao cliente."
            )
        if pend_notif > 0:
            st.sidebar.warning(
                f"📲 **{pend_notif}** concluído(s) para notificar."
            )
        if pend_prec == 0 and pend_env == 0 and pend_notif == 0:
            st.sidebar.info("Nenhuma pendência no momento.")
    elif perfil == "Mecânico (Oficina)":
        aprov_of = (
            len(
                df_passagens[
                    df_passagens["Status"].isin([
                        "Cliente Aprovou (Pronto para Iniciar)",
                        "Aguardando Peças",
                    ])
                ]
            )
            if not df_passagens.empty
            else 0
        )
        if aprov_of > 0:
            st.sidebar.success(
                f"✅ **{aprov_of}** serviço(s) aprovado(s)/aguardando peças!"
            )
        else:
            st.sidebar.info("Nenhuma nova notificação.")
    st.sidebar.markdown("---")


def _renderizar_grade_mobile(
    modulos_config: list[dict],
    chave_estado: str,
    titulo_hub: str,
    subtitulo_hub: str,
) -> None:
    st.markdown(
        f"""
        <div class="mob-hub-hero">
            <h3>{titulo_hub}</h3>
            <p>{subtitulo_hub}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i in range(0, len(modulos_config), 2):
        grupo = modulos_config[i : i + 2]
        cols = st.columns(len(grupo), gap="small")
        for idx, mod in enumerate(grupo):
            variante_badge = "amarelo" if idx % 2 == 1 else ""
            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="mob-tile-card">
                        <div class="mob-tile-badge {variante_badge}">{mod['icone']}</div>
                        <div class="mob-tile-label">{mod['titulo']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Abrir",
                    key=f"mob_tile_btn_{chave_estado}_{mod['destino']}",
                    use_container_width=True,
                ):
                    st.session_state[chave_estado] = mod["destino"]
                    st.rerun()


def renderizar_grade_botoes_inicial(
    modulos_config: list[dict],
    chave_estado: str,
    titulo_hub: str,
    subtitulo_hub: str,
    is_mobile: bool = False,
) -> None:
    """Renderiza a grade inicial de botões dos módulos."""
    if is_mobile:
        _renderizar_grade_mobile(
            modulos_config=modulos_config,
            chave_estado=chave_estado,
            titulo_hub=titulo_hub,
            subtitulo_hub=subtitulo_hub,
        )
        return

    st.markdown(
        f"""
        <div class="hub-banner">
            <h3>{titulo_hub}</h3>
            <p>{subtitulo_hub}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for i in range(0, len(modulos_config), 3):
        grupo = modulos_config[i : i + 3]
        cols = st.columns(len(grupo), gap="medium")
        for idx, mod in enumerate(grupo):
            with cols[idx]:
                if st.button(
                    f"{mod['icone']} {mod['titulo']}",
                    key=f"grade_btn_{chave_estado}_{mod['destino']}",
                    use_container_width=True,
                ):
                    st.session_state[chave_estado] = mod["destino"]
                    st.rerun()
                st.caption(mod["descricao"])

def renderizar_barra_navegacao_ativa(
    opcoes_telas: list[str],
    chave_estado: str,
    rotulos_curtos: dict[str, str],
    is_mobile: bool = False,
) -> None:
    """Renderiza navegação enxuta sem empilhar botões no mobile."""
    tela_atual = st.session_state.get(chave_estado, "Início")

    # Na tela "Início" não precisa exibir barra superior nem botão de voltar
    if tela_atual == "Início":
        return

    if is_mobile:
        if st.button(
            "🏠 Voltar à Grade Inicial",
            key=f"mob_home_{chave_estado}",
            use_container_width=True,
        ):
            st.session_state[chave_estado] = "Início"
            st.rerun()
        return

    st.markdown(
        '<div class="painel-nav-desktop-label">🧭 Painel Superior de Navegação</div>',
        unsafe_allow_html=True,
    )
    c_home, c_nav = st.columns([1, 5])
    if c_home.button(
        "🏠 Início", key=f"desk_home_{chave_estado}", use_container_width=True
    ):
        st.session_state[chave_estado] = "Início"
        st.rerun()
    cols = c_nav.columns(len(opcoes_telas))
    for idx, nome_tela in enumerate(opcoes_telas):
        ativa = nome_tela == tela_atual
        rotulo = (
            f"🟡 {rotulos_curtos.get(nome_tela, nome_tela)}"
            if ativa
            else rotulos_curtos.get(nome_tela, nome_tela)
        )
        if cols[idx].button(
            rotulo,
            key=f"top_nav_{chave_estado}_{idx}",
            use_container_width=True,
        ):
            st.session_state[chave_estado] = nome_tela
            st.rerun()