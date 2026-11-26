from functools import partial
from pathlib import Path

import streamlit as st

from database.connection import inicializar_banco
from ui.mecanico import renderizar_visao_mecanico
from ui.navegacao import (
    criar_logger_sessao,
    detectar_mobile,
    encerrar_sessao,
    renderizar_autenticacao,
    renderizar_barra_navegacao_ativa,
    renderizar_grade_botoes_inicial,
    renderizar_notificacoes_sidebar,
)
from ui.secretaria import renderizar_visao_secretaria

st.set_page_config(
    page_title="Oficina Conectada - Sistema de Gestão",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="auto",
)

CSS_PATH = Path(__file__).resolve().parent / "assets" / "styles.css"
if CSS_PATH.exists():
    st.markdown(
        f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

inicializar_banco()

st.markdown(
    """
    <div class="oficina-header">
        <h1>🔧 Oficina Conectada: Gestão Integrada (SQL)</h1>
        <span>Branco • Azul • Amarelo</span>
    </div>
    """,
    unsafe_allow_html=True,
)

for chave, padrao in {
    "usuario_logado": None,
    "perfil_logado": None,
    "flash_sucesso": None,
    "tela_mecanico": "Início",
    "tela_secretaria": "Início",
}.items():
    if chave not in st.session_state:
        st.session_state[chave] = padrao

if st.session_state.flash_sucesso:
    st.success(st.session_state.flash_sucesso)
    st.session_state.flash_sucesso = None

is_mobile = detectar_mobile()
logar_acao = criar_logger_sessao()
logout_fn = partial(encerrar_sessao, logar_acao)
grade_fn = partial(renderizar_grade_botoes_inicial, is_mobile=is_mobile)

if not renderizar_autenticacao(is_mobile=is_mobile, logar_acao=logar_acao):
    st.stop()

renderizar_notificacoes_sidebar()

perfil = st.session_state.perfil_logado
if perfil == "Mecânico (Oficina)":
    renderizar_visao_mecanico(
        is_mobile=is_mobile,
        logar_acao=logar_acao,
        encerrar_sessao=logout_fn,
        render_grade=grade_fn,
        render_nav=renderizar_barra_navegacao_ativa,
    )
elif perfil == "Secretaria (Administração)":
    renderizar_visao_secretaria(
        is_mobile=is_mobile,
        logar_acao=logar_acao,
        encerrar_sessao=logout_fn,
        render_grade=grade_fn,
        render_nav=renderizar_barra_navegacao_ativa,
    )