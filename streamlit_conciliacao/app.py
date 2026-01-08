# -*- coding: utf-8 -*-
"""
Aplicacao principal - Sistema de Conciliacao Contabil
Neto Contabilidade - Conciliacao Financeira

Empresas suportadas:
- Tradicao Comercio e Servicos LTDA
- Drogarias (Reconciliador Financeiro)
- VPS METALURGICA
- Auditoria de Natureza
- Auditoria de Conciliacao Bancaria
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from pathlib import Path

# ==========================================================================
# CONFIGURACAO DA PAGINA
# ==========================================================================
st.set_page_config(
    page_title="Neto Contabilidade - Conciliacao",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================================
# CORES DA EMPRESA
# ==========================================================================
CORES = {
    "azul_escuro": "#1E2A38",
    "azul_medio": "#2D3E50",
    "dourado": "#D4AF37",
    "dourado_claro": "#E8C962",
    "dourado_hover": "#C9A227",
    "branco": "#FFFFFF",
    "cinza_claro": "#F5F7FA",
    "cinza_medio": "#E8ECF0",
    "texto": "#2C3E50",
    "sucesso": "#27AE60",
    "erro": "#E74C3C",
    "aviso": "#F39C12",
}


# ==========================================================================
# CSS PERSONALIZADO
# ==========================================================================
def aplicar_tema():
    """Aplica o tema visual da Neto Contabilidade."""
    st.markdown(f"""
    <style>
        /* ================================================================== */
        /* SIDEBAR - ESTILO COMPLETO MELHORADO                               */
        /* ================================================================== */
        
        /* Fundo do sidebar */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {CORES['azul_escuro']} 0%, {CORES['azul_medio']} 100%);
        }}
        
        [data-testid="stSidebar"] > div:first-child {{
            background: transparent;
        }}

        /* Todos os textos do sidebar */
        [data-testid="stSidebar"] * {{
            color: {CORES['branco']} !important;
        }}
        
        /* Titulos do sidebar */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {{
            color: {CORES['dourado']} !important;
            font-weight: 700 !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        
        /* Markdown no sidebar */
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown span,
        [data-testid="stSidebar"] .stMarkdown div {{
            color: {CORES['branco']} !important;
        }}
        
        /* Labels no sidebar */
        [data-testid="stSidebar"] label {{
            color: {CORES['branco']} !important;
            font-weight: 500 !important;
            font-size: 1rem !important;
        }}

        /* ================================================================== */
        /* RADIO BUTTONS DO SIDEBAR - MENU DE NAVEGACAO                       */
        /* ================================================================== */
        
        /* Container dos radio buttons */
        [data-testid="stSidebar"] [data-testid="stRadio"] {{
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 15px 10px;
            margin: 10px 0;
        }}
        
        /* Cada opcao do radio */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {{
            gap: 8px !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stRadio"] label {{
            background-color: rgba(255, 255, 255, 0.08) !important;
            border-radius: 10px !important;
            padding: 14px 18px !important;
            margin: 4px 0 !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            display: flex !important;
            align-items: center !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
            background-color: rgba(212, 175, 55, 0.2) !important;
            border-color: {CORES['dourado']} !important;
            transform: translateX(5px);
        }}
        
        /* Opcao selecionada */
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
        [data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] input:checked + div {{
            background-color: {CORES['dourado']} !important;
            border-color: {CORES['dourado']} !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] span,
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] p {{
            color: {CORES['azul_escuro']} !important;
            font-weight: 700 !important;
        }}
        
        /* Texto das opcoes do radio */
        [data-testid="stSidebar"] [data-testid="stRadio"] label span,
        [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
            color: {CORES['branco']} !important;
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.3px !important;
        }}
        
        /* Circulo do radio button */
        [data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {{
            border-color: {CORES['dourado']} !important;
            background-color: transparent !important;
        }}
        
        [data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] > div:first-child > div {{
            background-color: {CORES['dourado']} !important;
        }}

        /* ================================================================== */
        /* DIVIDERS NO SIDEBAR                                                */
        /* ================================================================== */
        
        [data-testid="stSidebar"] hr {{
            border-color: rgba(212, 175, 55, 0.4) !important;
            margin: 20px 0 !important;
        }}

        /* ================================================================== */
        /* HEADER PRINCIPAL                                                   */
        /* ================================================================== */
        
        .stApp header {{
            background-color: {CORES['azul_escuro']};
        }}

        /* ================================================================== */
        /* BOTOES PRIMARIOS                                                   */
        /* ================================================================== */
        
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {{
            background-color: {CORES['dourado']} !important;
            color: {CORES['azul_escuro']} !important;
            border: none !important;
            font-weight: 700 !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }}

        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {{
            background-color: {CORES['dourado_hover']} !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4);
        }}

        /* ================================================================== */
        /* TABS                                                               */
        /* ================================================================== */
        
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {CORES['cinza_claro']};
            padding: 8px;
            border-radius: 10px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 8px;
            color: {CORES['texto']};
            font-weight: 600;
            padding: 12px 24px;
            transition: all 0.3s ease;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: {CORES['azul_escuro']} !important;
            color: {CORES['branco']} !important;
        }}

        /* ================================================================== */
        /* METRICAS                                                           */
        /* ================================================================== */
        
        [data-testid="stMetricValue"] {{
            color: {CORES['azul_escuro']} !important;
            font-weight: 700 !important;
            font-size: 1.8rem !important;
        }}

        [data-testid="stMetricDelta"] svg {{
            color: {CORES['sucesso']} !important;
        }}

        /* ================================================================== */
        /* CARDS/CONTAINERS                                                   */
        /* ================================================================== */
        
        .stExpander {{
            background-color: {CORES['branco']};
            border: 1px solid {CORES['cinza_medio']};
            border-radius: 10px;
        }}

        /* ================================================================== */
        /* FILE UPLOADER                                                      */
        /* ================================================================== */
        
        [data-testid="stFileUploader"] {{
            background-color: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 12px;
        }}

        /* ================================================================== */
        /* DIVIDER GERAL                                                      */
        /* ================================================================== */
        
        hr {{
            border-color: {CORES['dourado']} !important;
            opacity: 0.3;
        }}

        /* ================================================================== */
        /* MENSAGENS DE STATUS                                                */
        /* ================================================================== */
        
        .stSuccess {{
            background-color: rgba(39, 174, 96, 0.1) !important;
            border-left: 4px solid {CORES['sucesso']} !important;
        }}

        .stError {{
            background-color: rgba(231, 76, 60, 0.1) !important;
            border-left: 4px solid {CORES['erro']} !important;
        }}

        .stWarning {{
            background-color: rgba(243, 156, 18, 0.1) !important;
            border-left: 4px solid {CORES['aviso']} !important;
        }}

        /* ================================================================== */
        /* DOWNLOAD BUTTON                                                    */
        /* ================================================================== */
        
        .stDownloadButton > button {{
            background-color: {CORES['sucesso']} !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
        }}

        .stDownloadButton > button:hover {{
            background-color: #219A52 !important;
            transform: translateY(-2px);
        }}

        /* ================================================================== */
        /* LOGO CONTAINER                                                     */
        /* ================================================================== */
        
        .logo-container {{
            text-align: center;
            padding: 25px 0;
            margin-bottom: 25px;
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
        }}

        .logo-container img {{
            max-width: 180px;
            height: auto;
        }}

        .empresa-titulo {{
            color: {CORES['dourado']};
            font-size: 1.2rem;
            font-weight: 700;
            text-align: center;
            margin-top: 12px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        
        /* ================================================================== */
        /* FOOTER DO SIDEBAR                                                  */
        /* ================================================================== */
        
        .sidebar-footer {{
            text-align: center;
            padding: 15px 0;
            color: rgba(255, 255, 255, 0.6) !important;
            font-size: 0.8rem;
        }}
        
        .sidebar-footer p {{
            color: rgba(255, 255, 255, 0.6) !important;
            margin: 3px 0;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_logo_sidebar():
    """Renderiza a logo na sidebar."""
    logo_path = Path(__file__).parent / "assets" / "logo.png"

    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=180)
    else:
        st.sidebar.markdown("""
        <div style="text-align: center; padding: 25px 0;">
            <h2 style="color: #D4AF37; margin: 0; font-size: 2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">NETO</h2>
            <p style="color: #FFFFFF; font-size: 0.9rem; margin: 5px 0; letter-spacing: 3px;">CONTABILIDADE</p>
        </div>
        """, unsafe_allow_html=True)

    st.sidebar.markdown("---")


# ==========================================================================
# IMPORTACAO DAS PAGINAS
# ==========================================================================
try:
    from page_tradicao import mostrar_pagina_tradicao
    from page_drogarias import mostrar_pagina_drogarias
    from page_vps import mostrar_pagina_vps
    from page_auditoria_natureza import mostrar_pagina_auditoria_natureza
    from page_auditoria_bancaria import mostrar_pagina_auditoria_bancaria
except ImportError:
    from streamlit_conciliacao.page_tradicao import mostrar_pagina_tradicao
    from streamlit_conciliacao.page_drogarias import mostrar_pagina_drogarias
    from streamlit_conciliacao.page_vps import mostrar_pagina_vps
    from streamlit_conciliacao.page_auditoria_natureza import mostrar_pagina_auditoria_natureza
    from streamlit_conciliacao.page_auditoria_bancaria import mostrar_pagina_auditoria_bancaria


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    """Funcao principal da aplicacao."""

    # Aplicar tema
    aplicar_tema()

    # Sidebar - Logo e navegacao
    render_logo_sidebar()

    st.sidebar.markdown("###  Selecione o Modulo")

    empresa = st.sidebar.radio(
        "Modulo:",
        [
            " Tradicao Comercio e Servicos",
            " Drogarias",
            " VPS METALURGICA",
            " Auditoria de Natureza",
            " Auditoria Bancaria"
        ],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # Renderizar pagina correspondente
    if "Tradicao" in empresa:
        mostrar_pagina_tradicao()
    elif "Drogarias" in empresa:
        mostrar_pagina_drogarias()
    elif "Natureza" in empresa:
        mostrar_pagina_auditoria_natureza()
    elif "Bancaria" in empresa:
        mostrar_pagina_auditoria_bancaria()
    else:
        mostrar_pagina_vps()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div class="sidebar-footer">
        <p style="color: rgba(255,255,255,0.7); margin: 0;"> Neto Contabilidade</p>
        <p style="color: rgba(255,255,255,0.5); margin: 3px 0; font-size: 0.75rem;">Sistema de Conciliacao v2.0</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
