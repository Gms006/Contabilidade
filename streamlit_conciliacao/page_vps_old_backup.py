# -*- coding: utf-8 -*-
"""
PÃ¡gina Streamlit para conciliaÃ§Ã£o contÃ¡bil da VPS METALÃšRGICA
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import io
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, List

import pandas as pd
import streamlit as st

from vps.conciliador_vps import conciliar_vps
from vps.utils_vps import (
    carregar_contas_contabeis,
    carregar_lancamentos,
    carregar_extratos,
    fmt_valor,
)


# ============== Helpers locais (UI) ==============
def _fmt_val(v: float) -> str:
    return f"{float(v):0.2f}".replace(".", ",")


# ============== PLANILHAS EXEMPLO ==============
def _gerar_exemplo_contas_contabeis() -> bytes:
    """Gera planilha exemplo de Contas ContÃ¡beis com 4 abas."""
    # Aba RELATORIO FINANCEIRO - fornecedores
    df_financeiro = pd.DataFrame({
        'LANCAMENTOS': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO NORTE', 'SERVICOS GERAIS'],
        'CONTAS': [101, 102, 103, 104],
        'HISTORICO': [34, 34, 34, 34],
    })
    # Aba SICOOB - cadastro por histÃ³rico
    df_sicoob = pd.DataFrame({
        'LANCAMENTOS': ['TARIFA MENSAL', 'IOF', 'PIX RECEBIDO', 'TED RECEBIDA'],
        'CONTAS': [170, 171, 5, 5],
        'Historico': [11, 11, 2, 2],
    })
    # Aba BRADESCO - cadastro por histÃ³rico
    df_bradesco = pd.DataFrame({
        'LANCAMENTOS': ['TARIFA PACOTE', 'DEB PACOTE SERVICOS', 'PIX RECEBIDO', 'DEPOSITO'],
        'CONTAS': [170, 170, 5, 5],
        'Historico': [11, 11, 2, 9],
    })
    # Aba SICREDI - cadastro por histÃ³rico
    df_sicredi = pd.DataFrame({
        'LANCAMENTOS': ['TARIFA MENSAL', 'TAC', 'TED RECEBIDA', 'PIX RECEBIDO'],
        'CONTAS': [170, 170, 5, 5],
        'Historico': [11, 11, 2, 2],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_financeiro.to_excel(writer, index=False, sheet_name='RELATORIO FINANCEIRO')
        df_sicoob.to_excel(writer, index=False, sheet_name='SICOOB')
        df_bradesco.to_excel(writer, index=False, sheet_name='BRADESCO')
        df_sicredi.to_excel(writer, index=False, sheet_name='SICREDI')
    return buffer.getvalue()


def _gerar_exemplo_lancamentos() -> bytes:
    """Gera planilha exemplo de LanÃ§amentos."""
    df = pd.DataFrame({
        'FORNECEDOR': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO NORTE'],
        'NF': ['12345', '67890', '11111'],
        'Vencimento ': ['01/11/2025', '02/11/2025', '03/11/2025'],
        'Valor R$': [1500.00, 2300.50, 890.00],
        'Juros e multas': [0.00, 15.50, 0.00],
        'Valor pago': [1500.00, 2316.00, 890.00],
        'Forma de Pagamento ': ['PIX', 'BOLETO', 'PIX'],
        'Data de \npagamento': ['01/11/2025', '02/11/2025', '03/11/2025'],
        'PAGAMENTO': ['SICOOB', 'BRADESCO', 'SICREDI'],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='LANCAMENTOS')
    return buffer.getvalue()


def _gerar_exemplo_extratos() -> bytes:
    """Gera planilha exemplo de Extratos."""
    df = pd.DataFrame({
        'DATA': ['01/11/2025', '02/11/2025', '03/11/2025', '04/11/2025', '05/11/2025'],
        'HISTORICO': ['PIX ENVIADO FORNECEDOR ABC', 'PAG BOLETO DISTRIBUIDORA', 'TED ENVIADA ATACADO', 'TARIFA PACOTE SERVICOS', 'PIX RECEBIDO CLIENTE'],
        'VALOR': ['1.500,00D', '2.316,00D', '890,00D', '45,00D', '800,00C'],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='EXTRATOS')
    return buffer.getvalue()


# ============== PAGINA VPS ==============
def mostrar_pagina_vps():
    """Renderiza a pÃ¡gina de conciliaÃ§Ã£o da VPS METALÃšRGICA."""

    st.title("ðŸ­ ConciliaÃ§Ã£o ContÃ¡bil - VPS METALÃšRGICA")
    st.markdown("**VPS METALÃšRGICA**")
    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS
    # ==========================================================================
    tabs = st.tabs(["ðŸ“¤ Upload Arquivos", "ðŸ‘ï¸ PrÃ©-visualizaÃ§Ã£o", "ðŸ”„ ConciliaÃ§Ã£o", "ðŸ“Š Resultado", "ðŸ’¾ Export CSV", "âš ï¸ NÃ£o Classificados"])

    # ==========================================================================
    # ABA 0 - UPLOAD DE ARQUIVOS
    # ==========================================================================
    with tabs[0]:
        st.header("ðŸ“¤ Upload de Arquivos")
        st.markdown("FaÃ§a o upload dos arquivos necessÃ¡rios para a conciliaÃ§Ã£o.")
        st.divider()

        # Arquivos Base
        st.subheader("ðŸ“ Arquivos Base")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Contas ContÃ¡beis**")
            st.caption("Planilha com as abas: RELATORIO FINANCEIRO, SICOOB, BRADESCO, SICREDI")
            contas_file = st.file_uploader(
                "Contas ContÃ¡beis.xlsx",
                type=["xlsx"],
                key="upload_vps_contas",
                help="Planilha com mapeamento de fornecedores e histÃ³ricos bancÃ¡rios para contas contÃ¡beis"
            )
            st.download_button(
                "ðŸ“¥ Baixar Exemplo",
                data=_gerar_exemplo_contas_contabeis(),
                file_name="exemplo_contas_contabeis_vps.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            st.markdown("**LanÃ§amentos**")
            st.caption("Planilha financeira com os pagamentos realizados")
            lancamentos_file = st.file_uploader(
                "LanÃ§amentos.xlsx",
                type=["xlsx"],
                key="upload_vps_lancamentos",
                help="Planilha com fornecedor, NF, valores, datas e banco de pagamento"
            )
            st.download_button(
                "ðŸ“¥ Baixar Exemplo",
                data=_gerar_exemplo_lancamentos(),
                file_name="exemplo_lancamentos_vps.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.divider()

        # Extratos
        st.subheader("ðŸ¦ Extratos BancÃ¡rios")
        st.markdown("**Extrato Consolidado**")
        st.caption("Planilha Ãºnica com todas as movimentaÃ§Ãµes dos bancos (SICOOB, BRADESCO, SICREDI)")
        extratos_file = st.file_uploader(
            "Extratos.xlsx",
            type=["xlsx"],
            key="upload_vps_extratos",
            help="Planilha com Data, HistÃ³rico e Valor (formato C/D ou +/-)"
        )
        st.download_button(
            "ðŸ“¥ Baixar Exemplo",
            data=_gerar_exemplo_extratos(),
            file_name="exemplo_extratos_vps.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()

        # BotÃ£o carregar
        if st.button("âœ… Carregar Arquivos", type="primary", use_container_width=True):
            if not contas_file:
                st.error("âŒ Arquivo de Contas ContÃ¡beis Ã© obrigatÃ³rio!")
            elif not lancamentos_file:
                st.error("âŒ Arquivo de LanÃ§amentos Ã© obrigatÃ³rio!")
            elif not extratos_file:
                st.error("âŒ Arquivo de Extratos Ã© obrigatÃ³rio!")
            else:
                with st.spinner("Carregando arquivos..."):
                    try:
                        # Carrega contas contÃ¡beis
                        contas = carregar_contas_contabeis(contas_file)
                        st.session_state['vps_contas'] = contas

                        # Carrega lanÃ§amentos
                        df_lancamentos = carregar_lancamentos(lancamentos_file)
                        st.session_state['vps_lancamentos'] = df_lancamentos

                        # Carrega extratos
                        df_extratos = carregar_extratos(extratos_file)
                        st.session_state['vps_extratos'] = df_extratos

                        st.success("âœ… Arquivos carregados com sucesso!")
                        st.info(f"ðŸ“Š {len(df_lancamentos)} lanÃ§amentos e {len(df_extratos)} movimentaÃ§Ãµes de extrato carregadas.")

                    except Exception as e:
                        st.error(f"âŒ Erro ao carregar arquivos: {str(e)}")

    # ==========================================================================
    # ABA 1 - PRÃ‰-VISUALIZAÃ‡ÃƒO
    # ==========================================================================
    with tabs[1]:
        st.header("ðŸ‘ï¸ PrÃ©-visualizaÃ§Ã£o dos Dados")

        if 'vps_lancamentos' not in st.session_state:
            st.warning("âš ï¸ Carregue os arquivos primeiro na aba 'Upload Arquivos'")
        else:
            contas = st.session_state.get('vps_contas')
            df_lancamentos = st.session_state.get('vps_lancamentos')
            df_extratos = st.session_state.get('vps_extratos')
            
            # Contas ContÃ¡beis
            st.subheader("ðŸ“‹ Contas ContÃ¡beis")
            
            aba_contas = st.selectbox(
                "Selecione a aba:",
                ['RELATORIO_FINANCEIRO', 'SICOOB', 'BRADESCO', 'SICREDI'],
                key="preview_aba_contas"
            )
            
            if contas and isinstance(contas, dict) and aba_contas in contas and contas[aba_contas] is not None:
                st.dataframe(contas[aba_contas].head(20), use_container_width=True)
                st.caption(f"Total de registros: {len(contas[aba_contas])}")
            else:
                st.warning(f"Aba '{aba_contas}' nÃ£o encontrada ou vazia.")
            
            st.divider()
            
            # LanÃ§amentos
            st.subheader("ðŸ’° LanÃ§amentos (Pagamentos)")
            if df_lancamentos is not None and isinstance(df_lancamentos, pd.DataFrame) and not df_lancamentos.empty:
                st.dataframe(df_lancamentos.head(20), use_container_width=True)
                st.caption(f"Total: {len(df_lancamentos)} lanÃ§amentos")
                
                # EstatÃ­sticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_pago = df_lancamentos['VALOR_PAGO'].sum() if 'VALOR_PAGO' in df_lancamentos.columns else 0
                    st.metric("Total Pago", f"R$ {_fmt_val(total_pago)}")
                with col2:
                    total_juros = df_lancamentos['JUROS_MULTAS'].sum() if 'JUROS_MULTAS' in df_lancamentos.columns else 0
                    st.metric("Total Juros/Multas", f"R$ {_fmt_val(total_juros)}")
                with col3:
                    if 'BANCO' in df_lancamentos.columns:
                        bancos = df_lancamentos['BANCO'].value_counts()
                        st.metric("Bancos Utilizados", len(bancos))
                    else:
                        st.metric("Bancos Utilizados", 0)
            else:
                st.warning("âš ï¸ Nenhum lanÃ§amento carregado")

            st.divider()

            # Extratos
            st.subheader("ðŸ¦ Extratos BancÃ¡rios")
            if df_extratos is not None and isinstance(df_extratos, pd.DataFrame) and not df_extratos.empty:
                st.dataframe(df_extratos.head(20), use_container_width=True)
                st.caption(f"Total: {len(df_extratos)} movimentaÃ§Ãµes")
                
                # EstatÃ­sticas
                col1, col2 = st.columns(2)
                with col1:
                    if 'TIPO_MOVIMENTO' in df_extratos.columns and 'VALOR_ABS' in df_extratos.columns:
                        total_creditos = df_extratos[df_extratos['TIPO_MOVIMENTO'] == 'CREDITO']['VALOR_ABS'].sum()
                        st.metric("Total CrÃ©ditos", f"R$ {_fmt_val(total_creditos)}")
                    else:
                        st.metric("Total CrÃ©ditos", "R$ 0,00")
                with col2:
                    if 'TIPO_MOVIMENTO' in df_extratos.columns and 'VALOR_ABS' in df_extratos.columns:
                        total_debitos = df_extratos[df_extratos['TIPO_MOVIMENTO'] == 'DEBITO']['VALOR_ABS'].sum()
                        st.metric("Total DÃ©bitos", f"R$ {_fmt_val(total_debitos)}")
                    else:
                        st.metric("Total DÃ©bitos", "R$ 0,00")
            else:
                st.warning("âš ï¸ Nenhum extrato carregado")

            st.divider()

            # Contas ContÃ¡beis
            st.subheader("ðŸ“š Contas ContÃ¡beis")
            contas = st.session_state.get('vps_contas')

            if contas and isinstance(contas, dict):
                for aba_nome, df_aba in contas.items():
                    if df_aba is not None and isinstance(df_aba, pd.DataFrame):
                        with st.expander(f"Aba: {aba_nome}"):
                            st.dataframe(df_aba, use_container_width=True)
                            st.caption(f"Total: {len(df_aba)} registros")
            else:
                st.warning("âš ï¸ Contas contÃ¡beis nÃ£o carregadas corretamente")

    # ==========================================================================
    # ABA 2 - CONCILIAÃ‡ÃƒO
    # ==========================================================================
    with tabs[2]:
        st.header("ðŸ”„ Executar ConciliaÃ§Ã£o")

        if 'vps_lancamentos' not in st.session_state:
            st.warning("âš ï¸ Carregue os arquivos primeiro na aba 'Upload Arquivos'")
        else:
            st.markdown("""
            **Processo de ConciliaÃ§Ã£o:**
            1. Confronta lanÃ§amentos da planilha financeira com extratos bancÃ¡rios
            2. Identifica fornecedores, bancos, datas e valores
            3. Classifica contas contÃ¡beis e histÃ³ricos
            4. Gera lanÃ§amentos simples (1 dÃ©bito x 1 crÃ©dito) ou compostos (com juros/multas)
            5. Processa movimentaÃ§Ãµes nÃ£o conciliadas do extrato
            """)

            st.divider()

            if st.button("ðŸš€ Iniciar ConciliaÃ§Ã£o", type="primary", use_container_width=True):
                with st.spinner("Executando conciliaÃ§Ã£o..."):
                    try:
                        # Verifica se os dados foram carregados corretamente
                        df_lancamentos = st.session_state.get('vps_lancamentos')
                        df_extratos = st.session_state.get('vps_extratos')
                        contas = st.session_state.get('vps_contas')
                        
                        if not isinstance(df_lancamentos, pd.DataFrame):
                            st.error("âŒ LanÃ§amentos nÃ£o foram carregados corretamente. FaÃ§a o upload novamente.")
                            st.stop()
                        
                        if not isinstance(df_extratos, pd.DataFrame):
                            st.error("âŒ Extratos nÃ£o foram carregados corretamente. FaÃ§a o upload novamente.")
                            st.stop()
                        
                        if not isinstance(contas, dict):
                            st.error("âŒ Contas contÃ¡beis nÃ£o foram carregadas corretamente. FaÃ§a o upload novamente.")
                            st.stop()

                        # Executa conciliaÃ§Ã£o
                        df_resultado, stats = conciliar_vps(
                            df_lancamentos=df_lancamentos.copy(),
                            df_extrato=df_extratos.copy(),
                            contas_contabeis=contas
                        )

                        # Salva resultados
                        st.session_state['vps_resultado'] = df_resultado
                        st.session_state['vps_stats'] = stats

                        st.success("âœ… ConciliaÃ§Ã£o concluÃ­da!")

                        # Exibe estatÃ­sticas
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total LanÃ§amentos", stats['total_lancamentos'])
                        with col2:
                            st.metric("Conciliados", stats['conciliados_lancamento'])
                        with col3:
                            st.metric("NÃ£o Classificados", stats['nao_classificados'])
                        with col4:
                            st.metric("LanÃ§amentos Gerados", len(df_resultado))
                        
                        if stats['nao_classificados'] > 0:
                            st.warning(f"âš ï¸ {stats['nao_classificados']} lanÃ§amento(s) nÃ£o classificado(s). Verifique a aba 'NÃ£o Classificados'.")
                        
                        st.info("ðŸ‘‰ Acesse as outras abas para ver os detalhes.")

                    except Exception as e:
                        st.error(f"âŒ Erro na conciliaÃ§Ã£o: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

    # ==========================================================================
    # ABA 3 - RESULTADO
    # ==========================================================================
    with tabs[3]:
        st.header("ðŸ“Š Resultado da ConciliaÃ§Ã£o")

        if 'vps_resultado' not in st.session_state:
            st.warning("âš ï¸ Execute a conciliaÃ§Ã£o primeiro na aba 'ConciliaÃ§Ã£o'")
        else:
            df_resultado = st.session_state['vps_resultado']
            stats = st.session_state['vps_stats']

            # EstatÃ­sticas
            st.subheader("ðŸ“ˆ EstatÃ­sticas")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de LanÃ§amentos", len(df_resultado))
            with col2:
                ok = len(df_resultado[df_resultado.get('STATUS', 'OK') == 'OK'])
                st.metric("Classificados", ok)
            with col3:
                nao_class = stats['nao_classificados']
                st.metric("NÃ£o Classificados", nao_class)
            with col4:
                st.metric("Taxa de Sucesso", f"{(ok/(len(df_resultado)) * 100):.1f}%" if len(df_resultado) > 0 else "0%")

            st.divider()

            # VisualizaÃ§Ã£o dos lanÃ§amentos
            st.subheader("ðŸ“‹ LanÃ§amentos Gerados")

            # Filtro
            filtro = st.radio("Filtrar por:", ["Todos", "Classificados", "NÃ£o Classificados"], horizontal=True)

            if filtro == "Classificados":
                df_exibir = df_resultado[df_resultado.get('STATUS', 'OK') == 'OK']
            elif filtro == "NÃ£o Classificados":
                df_exibir = df_resultado[df_resultado.get('STATUS', 'OK') == 'NAO_CLASSIFICADO']
            else:
                df_exibir = df_resultado

            # Exibe tabela
            st.dataframe(df_exibir, use_container_width=True, height=400)
            st.caption(f"Exibindo {len(df_exibir)} de {len(df_resultado)} lanÃ§amentos")

    # ==========================================================================
    # ABA 4 - EXPORT CSV
    # ==========================================================================
    with tabs[4]:
        st.header("ðŸ’¾ Exportar CSV Padronizado")

        if 'vps_resultado' not in st.session_state:
            st.warning("âš ï¸ Execute a conciliaÃ§Ã£o primeiro")
        else:
            df_resultado = st.session_state['vps_resultado']
            stats = st.session_state['vps_stats']

            if stats['nao_classificados'] > 0:
                st.error(f"âŒ Existem {stats['nao_classificados']} lanÃ§amentos nÃ£o classificados!")
                st.warning("âš ï¸ Cadastre os fornecedores/histÃ³ricos faltantes na planilha de Contas ContÃ¡beis e refaÃ§a a conciliaÃ§Ã£o.")
            else:
                st.success("âœ… Todos os lanÃ§amentos foram classificados!")

                # Prepara CSV
                df_csv = df_resultado.copy()

                # Remove colunas extras (mantÃ©m apenas formato padrÃ£o)
                colunas_padrao = ['DATA', 'COD_CONTA_DEBITO', 'COD_CONTA_CREDITO', 'VALOR', 'COD_HISTORICO', 'COMPLEMENTO', 'INICIA_LOTE']
                df_csv = df_csv[[c for c in colunas_padrao if c in df_csv.columns]]

                # Remove linhas com STATUS != OK (se existir)
                if 'STATUS' in df_resultado.columns:
                    df_csv = df_resultado[df_resultado['STATUS'] == 'OK'][colunas_padrao]
                
                # Renomeia colunas para o padrÃ£o do SICOOB.csv
                df_csv = df_csv.rename(columns={
                    'DATA': 'Data',
                    'COD_CONTA_DEBITO': 'CÃ³d. Conta Debito',
                    'COD_CONTA_CREDITO': 'CÃ³d. Conta Credito',
                    'VALOR': 'Valor',
                    'COD_HISTORICO': 'CÃ³d. HistÃ³rico',
                    'COMPLEMENTO': 'Complemento HistÃ³rico',
                    'INICIA_LOTE': 'Inicia Lote'
                })

                # Converte para CSV com encoding Windows-1252 (padrÃ£o para softwares contÃ¡beis brasileiros)
                csv_buffer = io.BytesIO()
                df_csv.to_csv(csv_buffer, index=False, sep=';', encoding='cp1252', errors='replace')
                csv_data = csv_buffer.getvalue()

                # Preview
                st.subheader("ðŸ‘ï¸ Preview do CSV")
                st.dataframe(df_csv.head(20), use_container_width=True)
                st.caption(f"Total: {len(df_csv)} lanÃ§amentos no CSV")

                st.divider()

                # Download
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.download_button(
                        label="ðŸ“¥ Baixar CSV Padronizado",
                        data=csv_data,
                        file_name=f"vps_contabilizacao_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        type="primary",
                        use_container_width=True
                    )

    # ==========================================================================
    # ABA 5 - NÃƒO CLASSIFICADOS
    # ==========================================================================
    with tabs[5]:
        st.header("âš ï¸ LanÃ§amentos NÃ£o Classificados")

        if 'vps_resultado' not in st.session_state:
            st.warning("âš ï¸ Execute a conciliaÃ§Ã£o primeiro")
        else:
            df_resultado = st.session_state['vps_resultado']

            # Filtra nÃ£o classificados
            if 'STATUS' in df_resultado.columns:
                df_nao_class = df_resultado[df_resultado['STATUS'] == 'NAO_CLASSIFICADO'].copy()
            else:
                df_nao_class = pd.DataFrame()

            if len(df_nao_class) == 0:
                st.success("âœ… NÃ£o hÃ¡ lanÃ§amentos nÃ£o classificados!")
            else:
                st.error(f"âŒ {len(df_nao_class)} lanÃ§amentos nÃ£o foram classificados")

                st.markdown("""
                **AÃ§Ãµes necessÃ¡rias:**
                1. Identifique os fornecedores/histÃ³ricos nÃ£o cadastrados abaixo
                2. Adicione-os na planilha de Contas ContÃ¡beis
                3. FaÃ§a upload novamente e refaÃ§a a conciliaÃ§Ã£o
                """)

                st.divider()

                # Lista de nÃ£o classificados
                st.subheader("ðŸ“‹ Detalhes dos NÃ£o Classificados")
                st.dataframe(df_nao_class, use_container_width=True, height=400)

                # Download CSV com nÃ£o classificados (encoding cp1252 para compatibilidade)
                csv_buffer = io.BytesIO()
                df_nao_class.to_csv(csv_buffer, index=False, sep=';', encoding='cp1252', errors='replace')
                csv_data = csv_buffer.getvalue()

                st.download_button(
                    label="ðŸ“¥ Baixar Lista de NÃ£o Classificados",
                    data=csv_data,
                    file_name=f"vps_nao_classificados_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )


if __name__ == "__main__":
    mostrar_pagina_vps()

