# -*- coding: utf-8 -*-
"""
Componentes reutilizáveis de UI para o projeto de conciliação.
"""

import streamlit as st
import pandas as pd
from io import BytesIO


def render_status_header(files_status: dict, results: dict = None):
    """
    Renderiza header fixo com status dos arquivos, métricas e botões de ação.
    
    Args:
        files_status: dict com status dos arquivos {'pagamentos': bool, 'extrato': bool, 'contas': bool}
        results: dict com resultados da conciliação (opcional)
    """
    st.markdown("""
    <style>
    .status-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .status-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-ok {
        border-left: 4px solid #10b981;
    }
    .status-pending {
        border-left: 4px solid #f59e0b;
    }
    .status-error {
        border-left: 4px solid #ef4444;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f2937;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Container principal
    with st.container():
        # Status dos arquivos
        st.markdown("### 📋 Status dos Arquivos")
        col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
        
        with col1:
            if files_status.get('pagamentos'):
                st.success("✓ Pagamentos")
            else:
                st.warning("⏳ Pagamentos")
        
        with col2:
            if files_status.get('extrato'):
                st.success("✓ Extrato")
            else:
                st.warning("⏳ Extrato")
        
        with col3:
            if files_status.get('contas'):
                st.success("✓ Contas")
            else:
                st.warning("⏳ Contas")
        
        with col4:
            # Botões de ação
            if all(files_status.values()):
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if not results:
                        if st.button("🚀 PROCESSAR", type="primary", use_container_width=True, key="btn_process_header"):
                            return "process"
                    else:
                        st.success(f"✓ Conciliado ({results.get('taxa', 0):.1f}%)")
                
                with col_btn2:
                    if results and results.get('csv_data'):
                        st.download_button(
                            "⬇️ BAIXAR CSV",
                            data=results['csv_data'],
                            file_name=results.get('csv_filename', 'conciliacao.csv'),
                            mime="text/csv",
                            use_container_width=True,
                            key="btn_download_header"
                        )
        
        # Métricas se houver resultados
        if results and results.get('stats'):
            st.divider()
            st.markdown("### 📊 Resumo")
            col1, col2, col3, col4 = st.columns(4)
            
            stats = results['stats']
            with col1:
                st.metric("Conciliados", stats.get('conciliados', 0))
            with col2:
                st.metric("Total Pagamentos", stats.get('total_pagamentos', 0))
            with col3:
                st.metric("Saídas Extrato", stats.get('total_saidas', 0))
            with col4:
                pct = stats.get('taxa_conciliacao', 0)
                st.metric("Taxa", f"{pct:.1f}%", delta=None if pct < 90 else f"+{pct-90:.1f}%")
    
    return None


def render_upload_section(file_type: str, key_prefix: str, help_text: str = "", accepted_formats: list = ["xlsx", "xlsm"]):
    """
    Renderiza seção de upload com visual moderno.
    
    Args:
        file_type: Tipo do arquivo (ex: "Pagamentos", "Extrato")
        key_prefix: Prefixo para as keys do Streamlit
        help_text: Texto de ajuda adicional
        accepted_formats: Lista de formatos aceitos
    
    Returns:
        uploaded_file: Arquivo enviado ou None
    """
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{file_type}**")
            if help_text:
                st.caption(help_text)
        
        uploaded_file = st.file_uploader(
            f"{file_type}.xlsx",
            type=accepted_formats,
            key=f"{key_prefix}_upload",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            st.success(f"✓ {uploaded_file.name}")
        else:
            st.info(f"↑ Arraste o arquivo aqui ou clique para selecionar")
    
    return uploaded_file


def render_config_section(defaults: dict = None):
    """
    Renderiza seção de configurações de forma compacta.
    
    Args:
        defaults: dict com valores padrão {'banco': 'Sicoob', 'caixa': 'Caixa', 'strict': True}
    
    Returns:
        dict com configurações selecionadas
    """
    if defaults is None:
        defaults = {'banco': 'Sicoob', 'caixa': 'Caixa', 'strict': True}
    
    with st.expander("⚙️ Configurações Avançadas", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Contas Bancárias**")
            banco = st.text_input(
                "Banco padrão (CAIXA E EQUIVALENTES)",
                value=defaults.get('banco', 'Sicoob'),
                key="config_banco"
            )
            caixa = st.text_input(
                "Conta Caixa (CAIXA E EQUIVALENTES)",
                value=defaults.get('caixa', 'Caixa'),
                key="config_caixa"
            )
        
        with col2:
            st.markdown("**Parâmetros de Conciliação**")
            strict = st.checkbox(
                "Matching rigoroso (Data + Valor exatos)",
                value=defaults.get('strict', True),
                help="Se desmarcado, permite tolerância de dias",
                key="config_strict"
            )
            
            tolerance = 0
            if not strict:
                tolerance = st.slider(
                    "Tolerância em dias",
                    min_value=0,
                    max_value=7,
                    value=2,
                    key="config_tolerance"
                )
    
    return {
        'banco': banco,
        'caixa': caixa,
        'strict': strict,
        'tolerance': tolerance
    }


def render_validation_warnings(validation_result: dict):
    """
    Renderiza avisos de validação de forma visual.
    
    Args:
        validation_result: dict com resultados da validação
    """
    if not validation_result:
        return
    
    issues = validation_result.get('issues', [])
    warnings = validation_result.get('warnings', [])
    
    if issues:
        with st.expander(f"⚠️ {len(issues)} Problema(s) Detectado(s)", expanded=True):
            for issue in issues:
                st.error(f"• {issue}")
    
    if warnings:
        with st.expander(f"ℹ️ {len(warnings)} Aviso(s)", expanded=False):
            for warning in warnings:
                st.warning(f"• {warning}")


def render_results_summary(matches_df: pd.DataFrame, pend_data: dict, cols_pag: dict, cols_ext: dict):
    """
    Renderiza resumo dos resultados de conciliação.
    
    Args:
        matches_df: DataFrame com matches
        pend_data: dict com dados pendentes
        cols_pag: dict com mapeamento de colunas de pagamentos
        cols_ext: dict com mapeamento de colunas de extrato
    """
    st.markdown("### 📈 Grupos Conciliados")
    
    if not matches_df.empty:
        # Exibe tabela de matches de forma mais compacta
        st.dataframe(
            matches_df,
            use_container_width=True,
            height=300
        )
    else:
        st.info("Nenhum grupo conciliado encontrado.")
    
    st.divider()
    
    # Pendências lado a lado
    col1, col2 = st.columns(2)
    
    with col1:
        unmatched_pag = pend_data.get('unmatched_pagamentos', pd.DataFrame())
        st.markdown(f"**💰 Pagamentos Pendentes: {len(unmatched_pag)}**")
        
        if not unmatched_pag.empty and len(unmatched_pag) > 0:
            display_cols = ['_data', '_valor']
            if cols_pag.get('fornecedor') in unmatched_pag.columns:
                display_cols.append(cols_pag['fornecedor'])
            
            st.dataframe(
                unmatched_pag[display_cols],
                use_container_width=True,
                height=250
            )
        else:
            st.success("✓ Todos os pagamentos conciliados!")
    
    with col2:
        unmatched_ext = pend_data.get('unmatched_extrato', pd.DataFrame())
        st.markdown(f"**🏦 Saídas Sem Pagamento: {len(unmatched_ext)}**")
        
        if not unmatched_ext.empty and len(unmatched_ext) > 0:
            display_cols = ['_data', '_valor']
            if cols_ext.get('historico') in unmatched_ext.columns:
                display_cols.append(cols_ext['historico'])
            
            st.dataframe(
                unmatched_ext[display_cols],
                use_container_width=True,
                height=250
            )
        else:
            st.success("✓ Todas as saídas conciliadas!")


def render_quality_analysis(pend_data: dict):
    """
    Renderiza análise de qualidade da conciliação.
    
    Args:
        pend_data: dict com dados pendentes e estatísticas
    """
    stats = pend_data.get('stats', {})
    pct = stats.get('pct_conciliacao', 0)
    
    # Card de qualidade com cor baseada na taxa
    if pct >= 95:
        st.success(f"### ✓ Excelente: Taxa de {pct:.1f}%")
        st.markdown("A conciliação está com qualidade excelente. Poucas pendências encontradas.")
    elif pct >= 85:
        st.warning(f"### ⚠️ Bom: Taxa de {pct:.1f}%")
        st.markdown("A conciliação está boa, mas há algumas pendências que merecem atenção.")
    elif pct >= 70:
        st.error(f"### ⚠️ Regular: Taxa de {pct:.1f}%")
        st.markdown("Há várias pendências. Recomenda-se revisar os dados de entrada.")
    else:
        st.error(f"### ✗ Crítico: Taxa de {pct:.1f}%")
        st.markdown("Taxa de conciliação muito baixa. Verifique os dados de entrada e configurações.")
    
    # Métricas detalhadas
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Pagamentos pelo Caixa",
            len(pend_data.get('unmatched_pagamentos', []))
        )
    
    with col2:
        st.metric(
            "Saídas não identificadas",
            len(pend_data.get('unmatched_extrato', []))
        )
    
    with col3:
        st.metric(
            "Itens Conciliados",
            stats.get('matches', 0)
        )
