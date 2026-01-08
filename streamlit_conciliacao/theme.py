# -*- coding: utf-8 -*-
"""
Módulo de configuração de tema e estilos para Neto Contabilidade.
"""

from pathlib import Path
import base64

# =============================================================================
# CONSTANTES DE CORES - IDENTIDADE VISUAL NETO CONTABILIDADE
# =============================================================================

CORES = {
    "azul_escuro": "#2D3E50",
    "azul_medio": "#3A5068", 
    "azul_claro": "#4A6278",
    "dourado": "#C9A96E",
    "dourado_claro": "#D4BA85",
    "dourado_escuro": "#B8985D",
    "branco": "#FFFFFF",
    "cinza_claro": "#F5F7FA",
    "cinza_medio": "#E8ECF0",
    "texto": "#2D3E50",
    "texto_secundario": "#5A6978",
    "sucesso": "#28A745",
    "erro": "#DC3545",
    "alerta": "#FFC107",
}


# =============================================================================
# FUNÇÕES DE ESTILO
# =============================================================================

def get_logo_base64() -> str:
    """Retorna a logo em base64 para uso no HTML."""
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def get_custom_css() -> str:
    """Retorna o CSS customizado."""
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def aplicar_tema(st) -> None:
    """Aplica o tema personalizado da Neto Contabilidade."""
    
    # CSS customizado inline para garantir aplicação
    custom_css = f"""
    <style>
        /* Importar fonte profissional */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Aplicar fonte global */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {CORES['azul_escuro']} 0%, {CORES['azul_medio']} 100%);
        }}
        
        section[data-testid="stSidebar"] * {{
            color: {CORES['branco']} !important;
        }}
        
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: {CORES['dourado']} !important;
        }}
        
        section[data-testid="stSidebar"] .stRadio label span {{
            color: {CORES['branco']} !important;
        }}
        
        section[data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.2);
        }}
        
        /* Main content */
        .main .block-container {{
            padding-top: 2rem;
            max-width: 1200px;
        }}
        
        /* Headers */
        h1 {{
            color: {CORES['azul_escuro']} !important;
            font-weight: 700 !important;
        }}
        
        h2 {{
            color: {CORES['azul_medio']} !important;
            font-weight: 600 !important;
            border-bottom: 2px solid {CORES['dourado']};
            padding-bottom: 8px;
        }}
        
        h3 {{
            color: {CORES['azul_claro']} !important;
            font-weight: 600 !important;
        }}
        
        /* Botões primários */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, {CORES['dourado']} 0%, {CORES['dourado_escuro']} 100%) !important;
            border: none !important;
            color: {CORES['azul_escuro']} !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.5rem !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }}
        
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {{
            background: linear-gradient(135deg, {CORES['dourado_claro']} 0%, {CORES['dourado']} 100%) !important;
            box-shadow: 0 4px 15px rgba(201, 169, 110, 0.4) !important;
            transform: translateY(-1px) !important;
        }}
        
        /* Download buttons */
        .stDownloadButton > button {{
            background: {CORES['azul_escuro']} !important;
            color: {CORES['branco']} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}
        
        .stDownloadButton > button:hover {{
            background: {CORES['azul_medio']} !important;
            box-shadow: 0 4px 15px rgba(45, 62, 80, 0.3) !important;
        }}
        
        /* File uploader */
        .stFileUploader {{
            border: 2px dashed {CORES['azul_medio']} !important;
            border-radius: 12px !important;
            padding: 1rem !important;
        }}
        
        .stFileUploader:hover {{
            border-color: {CORES['dourado']} !important;
            background: rgba(201, 169, 110, 0.05) !important;
        }}
        
        /* Métricas */
        [data-testid="stMetric"] {{
            background: {CORES['branco']};
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border-left: 4px solid {CORES['dourado']};
        }}
        
        [data-testid="stMetricLabel"] {{
            color: {CORES['texto_secundario']} !important;
        }}
        
        [data-testid="stMetricValue"] {{
            color: {CORES['azul_escuro']} !important;
            font-weight: 700 !important;
        }}
        
        /* DataFrames */
        .stDataFrame {{
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
        }}
        
        /* Alerts */
        .stAlert {{
            border-radius: 10px !important;
        }}
        
        /* Success message */
        .stSuccess {{
            background-color: rgba(40, 167, 69, 0.1) !important;
            border-left: 4px solid {CORES['sucesso']} !important;
        }}
        
        /* Error message */
        .stError {{
            background-color: rgba(220, 53, 69, 0.1) !important;
            border-left: 4px solid {CORES['erro']} !important;
        }}
        
        /* Warning message */
        .stWarning {{
            background-color: rgba(255, 193, 7, 0.1) !important;
            border-left: 4px solid {CORES['alerta']} !important;
        }}
        
        /* Info message */
        .stInfo {{
            background-color: rgba(45, 62, 80, 0.08) !important;
            border-left: 4px solid {CORES['azul_escuro']} !important;
        }}
        
        /* Expanders */
        .streamlit-expanderHeader {{
            background: {CORES['cinza_medio']} !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}
        
        /* Selectbox */
        .stSelectbox [data-baseweb="select"] {{
            border-radius: 8px !important;
        }}
        
        /* Radio buttons in sidebar */
        section[data-testid="stSidebar"] .stRadio > div {{
            background: rgba(255, 255, 255, 0.1) !important;
            border-radius: 10px !important;
            padding: 0.5rem !important;
        }}
        
        section[data-testid="stSidebar"] .stRadio > div > div {{
            padding: 0.3rem 0 !important;
        }}
        
        /* Dividers */
        hr {{
            border-color: {CORES['cinza_medio']} !important;
        }}
        
        /* Cards customizados */
        .card-empresa {{
            background: {CORES['branco']};
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-left: 4px solid {CORES['dourado']};
            margin: 1rem 0;
        }}
        
        /* Status badges */
        .badge-success {{
            background: {CORES['sucesso']};
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        .badge-error {{
            background: {CORES['erro']};
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        .badge-warning {{
            background: {CORES['alerta']};
            color: {CORES['azul_escuro']};
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem 0;
            margin-top: 3rem;
            border-top: 1px solid {CORES['cinza_medio']};
            color: {CORES['texto_secundario']};
        }}
        
        /* Animação de entrada */
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .main .block-container {{
            animation: slideIn 0.5s ease-out;
        }}
    </style>
    """
    
    st.markdown(custom_css, unsafe_allow_html=True)


def render_logo_sidebar(st) -> None:
    """Renderiza a logo na sidebar."""
    logo_base64 = get_logo_base64()
    
    if logo_base64:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem 0;">
                <img src="data:image/png;base64,{logo_base64}" 
                     style="width: 180px; margin-bottom: 0.5rem;">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Fallback se não encontrar a logo
        st.markdown(
            f"""
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="color: {CORES['dourado']}; margin: 0;">NC</h2>
                <p style="color: {CORES['branco']}; font-size: 0.9rem; margin: 0;">NETO CONTABILIDADE</p>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_header(st, titulo: str, subtitulo: str = "") -> None:
    """Renderiza um header estilizado."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: {CORES['azul_escuro']}; margin-bottom: 0.3rem;">{titulo}</h1>
            {f'<p style="color: {CORES["texto_secundario"]}; font-size: 1.1rem;">{subtitulo}</p>' if subtitulo else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_card(st, titulo: str, conteudo: str, icone: str = "📄") -> None:
    """Renderiza um card estilizado."""
    st.markdown(
        f"""
        <div class="card-empresa">
            <h3 style="color: {CORES['azul_escuro']}; margin: 0 0 0.5rem 0;">
                {icone} {titulo}
            </h3>
            <p style="color: {CORES['texto_secundario']}; margin: 0;">{conteudo}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_status_badge(st, texto: str, tipo: str = "success") -> None:
    """Renderiza um badge de status."""
    st.markdown(
        f'<span class="badge-{tipo}">{texto}</span>',
        unsafe_allow_html=True
    )


def render_footer(st) -> None:
    """Renderiza o footer."""
    st.markdown(
        f"""
        <div class="footer">
            <p style="margin: 0;">
                <strong style="color: {CORES['dourado']};">Neto Contabilidade</strong>
            </p>
            <p style="margin: 0.3rem 0 0 0; font-size: 0.85rem;">
                Sistema de Conciliação Contábil • v2.0 • Dezembro/2025
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section_header(st, titulo: str, icone: str = "📋") -> None:
    """Renderiza um header de seção."""
    st.markdown(
        f"""
        <h2 style="display: flex; align-items: center; gap: 0.5rem; 
                   color: {CORES['azul_escuro']}; border-bottom: 2px solid {CORES['dourado']};
                   padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0;">
            <span>{icone}</span> {titulo}
        </h2>
        """,
        unsafe_allow_html=True
    )
