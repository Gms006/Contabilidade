# -*- coding: utf-8 -*-
"""
Aplicação principal - Sistema de Conciliação Contábil
Neto Contabilidade - Conciliação Financeira

Empresas suportadas:
- Tradição Comércio e Serviços LTDA
- Drogarias (Reconciliador Financeiro)
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from pathlib import Path

# ==========================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================================================
st.set_page_config(
    page_title="Neto Contabilidade - Conciliação",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================================================
# CORES DA EMPRESA
# ==========================================================================
CORES = {
    "azul_escuro": "#2D3E50",
    "azul_medio": "#34495E",
    "dourado": "#C9A96E",
    "dourado_claro": "#D4BA85",
    "dourado_hover": "#B8956A",
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
        /* Header principal */
        .stApp header {{
            background-color: {CORES['azul_escuro']};
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {CORES['azul_escuro']} 0%, {CORES['azul_medio']} 100%);
        }}
        
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stRadio label {{
            color: {CORES['branco']} !important;
        }}
        
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{
            color: {CORES['dourado']} !important;
        }}
        
        /* Botões primários */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {{
            background-color: {CORES['dourado']} !important;
            color: {CORES['azul_escuro']} !important;
            border: none !important;
            font-weight: 600 !important;
        }}
        
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {{
            background-color: {CORES['dourado_hover']} !important;
        }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: {CORES['cinza_claro']};
            padding: 8px;
            border-radius: 8px;
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 6px;
            color: {CORES['texto']};
            font-weight: 500;
            padding: 10px 20px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background-color: {CORES['azul_escuro']} !important;
            color: {CORES['branco']} !important;
        }}
        
        /* Métricas */
        [data-testid="stMetricValue"] {{
            color: {CORES['azul_escuro']} !important;
            font-weight: 700 !important;
        }}
        
        [data-testid="stMetricDelta"] svg {{
            color: {CORES['sucesso']} !important;
        }}
        
        /* Cards/containers */
        .stExpander {{
            background-color: {CORES['branco']};
            border: 1px solid {CORES['cinza_medio']};
            border-radius: 8px;
        }}
        
        /* File uploader */
        [data-testid="stFileUploader"] {{
            background-color: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 10px;
        }}
        
        /* Divider */
        hr {{
            border-color: {CORES['dourado']} !important;
            opacity: 0.3;
        }}
        
        /* Success/Error/Warning messages */
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
        
        /* Download button */
        .stDownloadButton > button {{
            background-color: {CORES['sucesso']} !important;
            color: white !important;
            border: none !important;
        }}
        
        .stDownloadButton > button:hover {{
            background-color: #219A52 !important;
        }}
        
        /* Radio buttons na sidebar */
        [data-testid="stSidebar"] .stRadio > div {{
            background-color: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 10px;
        }}
        
        /* Logo container */
        .logo-container {{
            text-align: center;
            padding: 20px 0;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(201, 169, 110, 0.3);
        }}
        
        .logo-container img {{
            max-width: 180px;
            height: auto;
        }}
        
        /* Título da empresa */
        .empresa-titulo {{
            color: {CORES['dourado']};
            font-size: 1.1rem;
            font-weight: 600;
            text-align: center;
            margin-top: 10px;
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
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="color: #C9A96E; margin: 0;"></h2>
            <h3 style="color: #C9A96E; margin: 5px 0;">NETO</h3>
            <p style="color: #FFFFFF; font-size: 0.8rem; margin: 0;">CONTABILIDADE</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")


# ==========================================================================
# IMPORTAÇÃO DAS PÁGINAS
# ==========================================================================
try:
    from page_tradicao import mostrar_pagina_tradicao
    from page_drogarias import mostrar_pagina_drogarias
except ImportError:
    from page_tradicao import mostrar_pagina_tradicao
    from page_drogarias import mostrar_pagina_drogarias


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    """Função principal da aplicação."""
    
    # Aplicar tema
    aplicar_tema()
    
    # Sidebar - Logo e navegação
    render_logo_sidebar()
    
    st.sidebar.markdown("###  Selecione a Empresa")
    
    empresa = st.sidebar.radio(
        "Empresa:",
        ["Tradição Comércio e Serviços", "Drogarias"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # Renderizar página correspondente
    if empresa == "Tradição Comércio e Serviços":
        mostrar_pagina_tradicao()
    else:
        mostrar_pagina_drogarias()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 10px 0; color: #999; font-size: 0.75rem;">
        <p style="margin: 0;">Neto Contabilidade</p>
        <p style="margin: 0;">Sistema de Conciliação v2.0</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
