# -*- coding: utf-8 -*-
"""
Página Streamlit para Auditoria de Conciliação Bancária - VPS METALÚRGICA

Esta página permite:
- Upload de arquivos de extrato e razão para múltiplos bancos
- Execução da auditoria com verificação de:
  - Lançamentos faltantes (no extrato mas não contabilizados)
  - Lançamentos indevidos (contabilizados mas não existem no extrato)
- Verificação cruzada entre bancos
- Download de relatórios Excel
"""

import streamlit as st
import pandas as pd
from io import BytesIO

# Importar módulo de auditoria
from auditoria_bancaria import (
    executar_auditoria_completa,
    gerar_excel_auditoria,
    gerar_excel_cruzamento,
    formatar_valor_br,
    formatar_data_br
)


def inicializar_estado():
    """Inicializa variáveis de estado da sessão."""
    if 'auditoria_arquivos' not in st.session_state:
        st.session_state.auditoria_arquivos = {}
    if 'auditoria_resultados' not in st.session_state:
        st.session_state.auditoria_resultados = None


def mostrar_upload_arquivos():
    """Mostra interface de upload de arquivos por banco."""
    st.subheader(" Upload de Arquivos por Banco")
    
    st.info("""
    **Instruções:**
    - Para cada banco, faça upload do **Extrato Bancário** e do **Razão Contábil**
    - Os arquivos devem ser em formato Excel (.xlsx ou .xls)
    - A auditoria será executada para todos os bancos com arquivos completos
    """)
    
    bancos = ['BRADESCO', 'SICOOB', 'SICREDI']
    codigos = {'BRADESCO': '7', 'SICOOB': '809', 'SICREDI': '808'}
    
    cols = st.columns(3)
    
    for i, banco in enumerate(bancos):
        with cols[i]:
            st.markdown(f"###  {banco}")
            st.caption(f"Código reduzido: {codigos[banco]}")
            
            extrato = st.file_uploader(
                f"Extrato {banco}",
                type=['xlsx', 'xls'],
                key=f"extrato_{banco}"
            )
            
            razao = st.file_uploader(
                f"Razão {banco}",
                type=['xlsx', 'xls'],
                key=f"razao_{banco}"
            )
            
            if extrato and razao:
                st.session_state.auditoria_arquivos[banco] = {
                    'extrato': extrato,
                    'razao': razao
                }
                st.success(f" {banco} pronto")
            elif extrato or razao:
                st.warning(" Falta um arquivo")
            else:
                st.caption("Nenhum arquivo")
    
    # Mostrar resumo
    st.markdown("---")
    bancos_prontos = [b for b in bancos if b in st.session_state.auditoria_arquivos]
    
    if bancos_prontos:
        st.success(f"**{len(bancos_prontos)} banco(s) pronto(s) para auditoria:** {', '.join(bancos_prontos)}")
        return True
    else:
        st.warning(" Faça upload dos arquivos de pelo menos um banco para iniciar a auditoria.")
        return False


def executar_auditoria():
    """Executa a auditoria e mostra resultados."""
    if not st.session_state.auditoria_arquivos:
        st.error("Nenhum arquivo foi carregado.")
        return
    
    with st.spinner(" Executando auditoria... Isso pode levar alguns segundos."):
        try:
            resultados = executar_auditoria_completa(st.session_state.auditoria_arquivos)
            st.session_state.auditoria_resultados = resultados
            st.success(" Auditoria concluída com sucesso!")
        except Exception as e:
            st.error(f" Erro durante a auditoria: {e}")
            return


def mostrar_resultados():
    """Mostra os resultados da auditoria."""
    resultados = st.session_state.auditoria_resultados
    
    if not resultados:
        st.info("Execute a auditoria para ver os resultados.")
        return
    
    # Filtrar bancos (remover chave especial _cruzamento)
    bancos = [k for k in resultados.keys() if not k.startswith('_')]
    
    # Tabs para cada banco + cruzamento
    tab_names = bancos.copy()
    if not resultados.get('_cruzamento', pd.DataFrame()).empty:
        tab_names.append(" Cruzamento")
    
    tabs = st.tabs(tab_names)
    
    for i, banco in enumerate(bancos):
        with tabs[i]:
            resultado = resultados[banco]
            
            if 'erro' in resultado:
                st.error(f"Erro ao processar {banco}: {resultado['erro']}")
                continue
            
            info = resultado.get('info', {})
            stats = resultado.get('stats', {})
            
            # Informações da conta
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Código Reduzido", info.get('codigo_reduzido', 'N/A'))
            with col2:
                st.metric("Conta Contábil", info.get('codigo_contabil', 'N/A'))
            with col3:
                st.metric("Nome da Conta", info.get('nome_conta', 'N/A')[:30] + '...' if len(info.get('nome_conta', '')) > 30 else info.get('nome_conta', 'N/A'))
            
            st.markdown("---")
            
            # Métricas
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric(" Extrato", stats.get('total_extrato', 0))
            with col2:
                st.metric(" Razão", stats.get('total_razao', 0))
            with col3:
                st.metric(" Conciliados", stats.get('ok', 0))
            with col4:
                st.metric(" Faltantes", stats.get('faltantes', 0), delta=f"-{stats.get('faltantes', 0)}" if stats.get('faltantes', 0) > 0 else None, delta_color="inverse")
            with col5:
                st.metric(" Indevidos", stats.get('indevidos', 0), delta=f"-{stats.get('indevidos', 0)}" if stats.get('indevidos', 0) > 0 else None, delta_color="inverse")
            
            st.markdown("---")
            
            # Sub-tabs para detalhes
            sub_tabs = st.tabs([" Conciliação", " Faltantes", " Indevidos", " Download"])
            
            with sub_tabs[0]:
                df_conc = resultado.get('conciliacao', pd.DataFrame())
                if not df_conc.empty:
                    # Formatar para exibição
                    df_display = df_conc.copy()
                    df_display['data'] = df_display['data'].apply(formatar_data_br)
                    
                    # Colorir por status
                    def highlight_status(row):
                        if row['status'] == 'OK':
                            return ['background-color: #d4edda'] * len(row)
                        elif row['status'] == 'FALTANTE':
                            return ['background-color: #fff3cd'] * len(row)
                        else:  # INDEVIDO
                            return ['background-color: #f8d7da'] * len(row)
                    
                    st.dataframe(
                        df_display.style.apply(highlight_status, axis=1),
                        use_container_width=True,
                        height=400
                    )
                else:
                    st.info("Nenhum lançamento para conciliar.")
            
            with sub_tabs[1]:
                df_falt = resultado.get('faltantes', pd.DataFrame())
                if not df_falt.empty:
                    df_display = df_falt.copy()
                    df_display['data'] = df_display['data'].apply(formatar_data_br)
                    st.warning(f"**{len(df_falt)} lançamento(s) no extrato que não foram contabilizados:**")
                    st.dataframe(df_display, use_container_width=True, height=400)
                else:
                    st.success(" Nenhum lançamento faltante!")
            
            with sub_tabs[2]:
                df_ind = resultado.get('indevidos', pd.DataFrame())
                if not df_ind.empty:
                    df_display = df_ind.copy()
                    df_display['data'] = df_display['data'].apply(formatar_data_br)
                    st.error(f"**{len(df_ind)} lançamento(s) contabilizado(s) mas não existem no extrato:**")
                    st.dataframe(df_display, use_container_width=True, height=400)
                else:
                    st.success(" Nenhum lançamento indevido!")
            
            with sub_tabs[3]:
                excel_bytes = gerar_excel_auditoria(resultado, info, banco)
                st.download_button(
                    label=f" Baixar Relatório {banco}",
                    data=excel_bytes,
                    file_name=f"auditoria_{banco.lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Tab de cruzamento entre bancos
    df_cruz = resultados.get('_cruzamento', pd.DataFrame())
    if not df_cruz.empty:
        with tabs[-1]:
            st.subheader(" Lançamentos Cruzados Entre Bancos")
            st.warning(f"""
            **Atenção:** Foram encontrados **{len(df_cruz)} lançamento(s)** que foram contabilizados no banco errado!
            
            Isso significa que uma transação de um banco foi lançada na conta contábil de outro banco.
            """)
            
            df_display = df_cruz.copy()
            df_display['data'] = df_display['data'].apply(formatar_data_br)
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # Download
            excel_cruz = gerar_excel_cruzamento(df_cruz)
            st.download_button(
                label=" Baixar Relatório de Cruzamento",
                data=excel_cruz,
                file_name="auditoria_cruzamento_bancos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def main():
    """Função principal da página."""
    st.set_page_config(
        page_title="Auditoria Bancária - VPS",
        page_icon="",
        layout="wide"
    )
    
    st.title(" Auditoria de Conciliação Bancária")
    st.markdown("**VPS METALÚRGICA** - Sistema de Auditoria com Verificação Cruzada")
    
    inicializar_estado()
    
    # Tabs principais
    tab1, tab2 = st.tabs([" Upload de Arquivos", " Resultados"])
    
    with tab1:
        pronto = mostrar_upload_arquivos()
        
        if pronto:
            st.markdown("---")
            if st.button(" Executar Auditoria", type="primary", use_container_width=True):
                executar_auditoria()
                st.rerun()
    
    with tab2:
        mostrar_resultados()


if __name__ == "__main__":
    main()
