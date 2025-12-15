# -*- coding: utf-8 -*-
"""
Pagina Streamlit para conciliacao contabil da Tradicao Comercio e Servicos.
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

from tradicao.conciliador_tradicao import conciliar_tradicao
from tradicao.utils_tradicao import (
    carregar_contas_contabeis,
    carregar_planilha_movimentacao,
    carregar_extrato,
)

try:
    from tradicao.extrator_pdf import processar_pdf_extrato, PDF_AVAILABLE
except ImportError:
    PDF_AVAILABLE = False


# ============== Helpers locais (UI) ==============
def _fmt_val(v: float) -> str:
    return f"{float(v):0.2f}".replace(".", ",")


# ============== PLANILHAS EXEMPLO ==============
def _gerar_exemplo_contas_contabeis() -> bytes:
    """Gera planilha exemplo de Contas Contabeis com 3 abas."""
    # Aba FINANCEIRO - fornecedores
    df_financeiro = pd.DataFrame({
        'PAGAMENTO': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO NORTE', 'SERVICOS GERAIS'],
        'CONTA': [101, 102, 103, 104],
        'HISTORICO': ['Pagamento fornecedor', 'Pagamento fornecedor', 'Pagamento fornecedor', 'Pagamento servicos'],
    })
    # Aba BANCO DO BRASIL - cadastro por historico
    df_bb = pd.DataFrame({
        'HISTORICO': ['TARIFA PACOTE', 'DEB PACOTE SERVICOS', 'PIX RECEBIDO', 'DEPOSITO'],
        'CONTA': [170, 170, 5, 5],
        'TIPO': ['SAIDA', 'SAIDA', 'ENTRADA', 'ENTRADA'],
    })
    # Aba SICOOB - cadastro por historico
    df_sicoob = pd.DataFrame({
        'HISTORICO': ['TARIFA MENSAL', 'IOF', 'PIX RECEBIDO', 'TED RECEBIDA'],
        'CONTA': [170, 171, 5, 5],
        'TIPO': ['SAIDA', 'SAIDA', 'ENTRADA', 'ENTRADA'],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_financeiro.to_excel(writer, index=False, sheet_name='FINANCEIRO')
        df_bb.to_excel(writer, index=False, sheet_name='BANCO DO BRASIL')
        df_sicoob.to_excel(writer, index=False, sheet_name='SICOOB')
    return buffer.getvalue()


def _gerar_exemplo_movimentacao() -> bytes:
    """Gera planilha exemplo de Movimentacao com as abas necessarias."""
    # Aba PAG SICOOB
    df_pag_sicoob = pd.DataFrame({
        'DATA': ['01/11/2025', '02/11/2025', '03/11/2025'],
        'PAGAMENTO': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO NORTE'],
        'NF': ['12345', '67890', '11111'],
        'VALOR': [1500.00, 2300.50, 890.00],
    })
    # Aba PAG BB
    df_pag_bb = pd.DataFrame({
        'DATA': ['04/11/2025', '05/11/2025'],
        'PAGAMENTO': ['SERVICOS GERAIS', 'FORNECEDOR ABC LTDA'],
        'NF': ['22222', '33333'],
        'VALOR': [3200.00, 1800.00],
    })
    # Aba CAIXA EMPRESA (saidas)
    df_caixa_saidas = pd.DataFrame({
        'DATA': ['01/11/2025', '03/11/2025'],
        'PAGAMENTO': ['DESPESA DIVERSA', 'MATERIAL ESCRITORIO'],
        'NF': ['', '44444'],
        'VALOR': [150.00, 89.90],
    })
    # Aba CAIXA EMPRESA (entradas)
    df_caixa_entradas = pd.DataFrame({
        'DATA': ['02/11/2025', '04/11/2025'],
        'PAGAMENTO': ['VENDA BALCAO', 'RECEBIMENTO CLIENTE'],
        'NF': ['55555', '66666'],
        'VALOR': [500.00, 1200.00],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_pag_sicoob.to_excel(writer, index=False, sheet_name='PAG SICOOB')
        df_pag_bb.to_excel(writer, index=False, sheet_name='PAG BB')
        df_caixa_saidas.to_excel(writer, index=False, sheet_name='CAIXA EMPRESA')
    return buffer.getvalue()


def _gerar_exemplo_extrato() -> bytes:
    """Gera planilha exemplo de Extrato Bancario."""
    df = pd.DataFrame({
        'Data': ['01/11/2025', '02/11/2025', '03/11/2025', '04/11/2025', '05/11/2025'],
        'Historico': ['PIX ENVIADO FORNECEDOR ABC', 'PAG BOLETO DISTRIBUIDORA', 'TED ENVIADA ATACADO', 'TARIFA PACOTE SERVICOS', 'PIX RECEBIDO CLIENTE'],
        'Debito': [1500.00, 2300.50, 890.00, 45.00, 0],
        'Credito': [0, 0, 0, 0, 800.00],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Extrato')
    return buffer.getvalue()


# ============== PAGINA TRADICAO ==============
def mostrar_pagina_tradicao():
    """Renderiza a pagina de conciliacao da Tradicao."""

    st.title(" Conciliacao Contabil - Tradicao")
    st.markdown("**Tradicao Comercio e Servicos LTDA**")
    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS
    # ==========================================================================
    tabs = st.tabs([" Upload Arquivos", " Pre-visualizacao", " Conciliacao", " Resultado", " Export CSV", " Nao Classificados"])

    # ==========================================================================
    # ABA 0 - UPLOAD DE ARQUIVOS
    # ==========================================================================
    with tabs[0]:
        st.header(" Upload de Arquivos")
        st.markdown("Faca o upload dos arquivos necessarios para a conciliacao.")
        st.divider()

        # Arquivos Base
        st.subheader(" Arquivos Base")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Contas Contabeis**")
            st.caption("Planilha com as abas: FINANCEIRO, BANCO DO BRASIL, SICOOB")
            contas_file = st.file_uploader(
                "Contas Contabeis.xlsx",
                type=["xlsx"],
                key="trad_contas",
                help="Planilha com as abas: FINANCEIRO, BANCO DO BRASIL, SICOOB"
            )
            if contas_file:
                st.success(f" {contas_file.name}")
            else:
                st.warning(" Aguardando arquivo...")

        with col2:
            st.markdown("**Movimentacao Financeira**")
            st.caption("Planilha com as abas: PAG SICOOB, PAG BB, CAIXA EMPRESA")
            mov_file = st.file_uploader(
                "Movimentacao.xlsx",
                type=["xlsx"],
                key="trad_mov",
                help="Planilha com as abas: PAG SICOOB, PAG BB, CAIXA EMPRESA"
            )
            if mov_file:
                st.success(f" {mov_file.name}")
            else:
                st.warning(" Aguardando arquivo...")

        st.divider()

        # Extratos Bancarios
        st.subheader(" Extratos Bancarios")
        col_sicoob, col_bb = st.columns(2)

        with col_sicoob:
            st.markdown("**Extrato SICOOB**")
            tipo_sicoob = st.radio(
                "Tipo de arquivo:",
                ["Excel", "PDF"],
                key="trad_tipo_sicoob",
                horizontal=True
            )
            if tipo_sicoob == "Excel":
                extrato_sicoob = st.file_uploader("Extrato SICOOB (.xlsx)", type=["xlsx"], key="trad_ext_sicoob")
            else:
                if PDF_AVAILABLE:
                    extrato_sicoob = st.file_uploader("Extrato SICOOB (.pdf)", type=["pdf"], key="trad_ext_sicoob_pdf")
                else:
                    st.warning(" PDF nao disponivel")
                    extrato_sicoob = None

            if extrato_sicoob:
                st.success(f" {extrato_sicoob.name}")

        with col_bb:
            st.markdown("**Extrato Banco do Brasil**")
            tipo_bb = st.radio(
                "Tipo de arquivo:",
                ["Excel", "PDF"],
                key="trad_tipo_bb",
                horizontal=True
            )
            if tipo_bb == "Excel":
                extrato_bb = st.file_uploader("Extrato BB (.xlsx)", type=["xlsx"], key="trad_ext_bb")
            else:
                if PDF_AVAILABLE:
                    extrato_bb = st.file_uploader("Extrato BB (.pdf)", type=["pdf"], key="trad_ext_bb_pdf")
                else:
                    st.warning(" PDF nao disponivel")
                    extrato_bb = None

            if extrato_bb:
                st.success(f" {extrato_bb.name}")

        st.divider()

        # ======================================================================
        # PLANILHAS EXEMPLO
        # ======================================================================
        st.subheader(" Planilhas Exemplo")
        st.info("""
        **IMPORTANTE:** Baixe as planilhas exemplo abaixo para entender o formato correto dos arquivos.
        Seus arquivos devem seguir **exatamente** estas estruturas de colunas e abas para que o sistema funcione corretamente.
        """)

        col_ex1, col_ex2, col_ex3 = st.columns(3)

        with col_ex1:
            st.markdown("**Contas Contabeis**")
            st.caption("Abas: FINANCEIRO, BANCO DO BRASIL, SICOOB")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_contas_contabeis(),
                file_name="EXEMPLO_Contas_Contabeis_Tradicao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_contas_trad"
            )

        with col_ex2:
            st.markdown("**Movimentacao**")
            st.caption("Abas: PAG SICOOB, PAG BB, CAIXA EMPRESA")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_movimentacao(),
                file_name="EXEMPLO_Movimentacao_Tradicao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_mov_trad"
            )

        with col_ex3:
            st.markdown("**Extrato Bancario**")
            st.caption("Colunas: Data, Historico, Debito, Credito")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_extrato(),
                file_name="EXEMPLO_Extrato_Bancario.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_ext_trad"
            )

        st.divider()

        # Status dos arquivos
        st.subheader(" Status dos Arquivos")
        col_st1, col_st2, col_st3, col_st4 = st.columns(4)
        with col_st1:
            if contas_file:
                st.success(" Contas OK")
            else:
                st.error(" Contas pendente")
        with col_st2:
            if mov_file:
                st.success(" Movimentacao OK")
            else:
                st.error(" Movimentacao pendente")
        with col_st3:
            if extrato_sicoob:
                st.success(" SICOOB OK")
            else:
                st.info(" SICOOB opcional")
        with col_st4:
            if extrato_bb:
                st.success(" BB OK")
            else:
                st.info(" BB opcional")

        # Verificar arquivos
        arquivos_ok = contas_file is not None and mov_file is not None
        tem_extrato = extrato_sicoob is not None or extrato_bb is not None

        if arquivos_ok and tem_extrato:
            st.success(" **Todos os arquivos carregados! Navegue para as proximas abas.**")
            btn = st.button(" Conciliar e Gerar CSV", type="primary", key="trad_btn")
        elif arquivos_ok and not tem_extrato:
            st.warning(" Faca upload de pelo menos um extrato bancario (SICOOB ou BB).")
            btn = False
        else:
            st.warning(" Faca upload dos arquivos base (Contas e Movimentacao).")
            btn = False

    # ==========================================================================
    # PROCESSAR ARQUIVOS (se todos carregados)
    # ==========================================================================
    if arquivos_ok and tem_extrato:
        try:
            contas = carregar_contas_contabeis(contas_file)
            movimentacao = carregar_planilha_movimentacao(mov_file)

            df_extrato_sicoob = None
            df_extrato_bb = None

            if extrato_sicoob:
                if tipo_sicoob == "PDF" and PDF_AVAILABLE:
                    df_extrato_sicoob = processar_pdf_extrato(extrato_sicoob, 'SICOOB')
                else:
                    df_extrato_sicoob = carregar_extrato(extrato_sicoob, 'SICOOB')

            if extrato_bb:
                if tipo_bb == "PDF" and PDF_AVAILABLE:
                    df_extrato_bb = processar_pdf_extrato(extrato_bb, 'BB')
                else:
                    df_extrato_bb = carregar_extrato(extrato_bb, 'BB')

        except Exception as e:
            st.error(f" Erro na leitura: {e}")
            contas = None
            movimentacao = None
        else:
            # ====== PRE-VISUALIZACAO ======
            with tabs[1]:
                st.header(" Pre-visualizacao dos Dados")

                qtd_sicoob = len(movimentacao.get('pag_sicoob', pd.DataFrame()))
                qtd_bb = len(movimentacao.get('pag_bb', pd.DataFrame()))
                qtd_caixa = len(movimentacao.get('caixa_saidas', pd.DataFrame()))

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Fornecedores", len(contas.get('financeiro', [])))
                with col_m2:
                    st.metric("Pag. SICOOB", qtd_sicoob)
                with col_m3:
                    st.metric("Pag. BB", qtd_bb)
                with col_m4:
                    st.metric("Pag. Caixa", qtd_caixa)

                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(" Movimentacao SICOOB")
                    df_pag_sicoob = movimentacao.get('pag_sicoob', pd.DataFrame())
                    if not df_pag_sicoob.empty:
                        st.dataframe(df_pag_sicoob.head(10), use_container_width=True)
                    else:
                        st.info("Sem dados")

                    st.subheader(" Movimentacao BB")
                    df_pag_bb = movimentacao.get('pag_bb', pd.DataFrame())
                    if not df_pag_bb.empty:
                        st.dataframe(df_pag_bb.head(10), use_container_width=True)
                    else:
                        st.info("Sem dados")

                with col2:
                    st.subheader(" Extrato SICOOB")
                    if df_extrato_sicoob is not None and not df_extrato_sicoob.empty:
                        st.dataframe(df_extrato_sicoob.head(10), use_container_width=True)
                    else:
                        st.info("Sem extrato SICOOB")

                    st.subheader(" Extrato BB")
                    if df_extrato_bb is not None and not df_extrato_bb.empty:
                        st.dataframe(df_extrato_bb.head(10), use_container_width=True)
                    else:
                        st.info("Sem extrato BB")

            # ====== BOTAO: CONCILIAR/GERAR ======
            if btn:
                with st.spinner("Processando conciliacao..."):
                    try:
                        df_resultado, nao_encontrados = conciliar_tradicao(
                            df_extrato_sicoob=df_extrato_sicoob,
                            df_extrato_bb=df_extrato_bb,
                            movimentacao=movimentacao,
                            contas=contas
                        )
                        st.session_state['trad_resultado'] = df_resultado
                        st.session_state['trad_nao_encontrados'] = nao_encontrados
                    except Exception as e:
                        st.error(f" Erro ao processar: {e}")
                        import traceback
                        st.code(traceback.format_exc())

            # ====== CONCILIACAO ======
            with tabs[2]:
                if 'trad_resultado' in st.session_state:
                    df_resultado = st.session_state['trad_resultado']
                    nao_encontrados = st.session_state.get('trad_nao_encontrados', [])

                    total_lanc = len(df_resultado)
                    total_nao_enc = len(nao_encontrados)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(" Lancamentos Gerados", total_lanc)
                    with col2:
                        st.metric(" Nao Classificados", total_nao_enc)
                    with col3:
                        taxa = round((total_lanc / (total_lanc + total_nao_enc) * 100), 1) if (total_lanc + total_nao_enc) > 0 else 0
                        st.metric(" Taxa Sucesso", f"{taxa}%")
                    with col4:
                        if total_nao_enc == 0:
                            st.success(" Pronto")
                        else:
                            st.warning(" Pendencias")

                    if not df_resultado.empty and '_tipo' in df_resultado.columns:
                        tipos = df_resultado['_tipo'].value_counts()
                        for tipo, qtd in tipos.items():
                            st.write(f"**{tipo}**: {qtd} lancamentos")
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

            # ====== RESULTADO ======
            with tabs[3]:
                if 'trad_resultado' in st.session_state:
                    df_resultado = st.session_state['trad_resultado']

                    if not df_resultado.empty:
                        export_df = df_resultado.drop(columns="_tipo", errors="ignore")

                        st.subheader(" Previa do CSV Final")
                        st.dataframe(export_df.head(30), use_container_width=True)

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            total_debitos = export_df[export_df['Cod Conta Debito'] != '']['Valor'].apply(
                                lambda x: float(str(x).replace(',', '.')) if x else 0
                            ).sum()
                            st.metric("Total Debitos", f"R$ {_fmt_val(total_debitos)}")
                        with col2:
                            total_creditos = export_df[export_df['Cod Conta Credito'] != '']['Valor'].apply(
                                lambda x: float(str(x).replace(',', '.')) if x else 0
                            ).sum()
                            st.metric("Total Creditos", f"R$ {_fmt_val(total_creditos)}")
                        with col3:
                            st.metric("Total Lancamentos", len(export_df))
                    else:
                        st.warning("Nenhum lancamento gerado.")
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

            # ====== EXPORT CSV ======
            with tabs[4]:
                if 'trad_resultado' in st.session_state:
                    df_resultado = st.session_state['trad_resultado']
                    nao_encontrados = st.session_state.get('trad_nao_encontrados', [])

                    if nao_encontrados:
                        st.error(f" **EXPORTACAO BLOQUEADA** - {len(nao_encontrados)} lancamentos nao classificados!")
                        st.warning("Cadastre as contas na aba Nao Classificados e processe novamente.")
                    elif not df_resultado.empty:
                        export_df = df_resultado.drop(columns="_tipo", errors="ignore")
                        st.success(" Pronto para exportar!")

                        col1, col2 = st.columns(2)
                        with col1:
                            csv_data = export_df.to_csv(sep=";", index=False, encoding="utf-8-sig").encode("utf-8-sig")
                            st.download_button(
                                " **Baixar CSV Final**",
                                data=csv_data,
                                file_name="conciliacao_tradicao.csv",
                                mime="text/csv",
                                type="primary"
                            )
                        with col2:
                            buffer = BytesIO()
                            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                                export_df.to_excel(writer, index=False, sheet_name="Conciliacao")
                            st.download_button(
                                " Baixar Excel",
                                data=buffer.getvalue(),
                                file_name="conciliacao_tradicao.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning("Nenhum lancamento para exportar.")
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

            # ====== NAO CLASSIFICADOS ======
            with tabs[5]:
                if 'trad_nao_encontrados' in st.session_state:
                    nao_encontrados = st.session_state['trad_nao_encontrados']

                    if nao_encontrados:
                        st.error(f" {len(nao_encontrados)} lancamentos nao foram classificados!")
                        st.markdown("**Cadastre as contas contabeis para os seguintes lancamentos:**")

                        df_nao_encontrados = pd.DataFrame(nao_encontrados)
                        st.dataframe(df_nao_encontrados, use_container_width=True)

                        st.subheader(" Resumo por Tipo")
                        tipos = df_nao_encontrados['Tipo'].value_counts()
                        for tipo, qtd in tipos.items():
                            st.write(f" **{tipo}**: {qtd}")

                        csv_nao_enc = df_nao_encontrados.to_csv(sep=";", index=False, encoding="utf-8-sig")
                        st.download_button(
                            " Baixar nao classificados",
                            data=csv_nao_enc.encode("utf-8-sig"),
                            file_name="lancamentos_nao_classificados.csv",
                            mime="text/csv"
                        )

                        with st.expander(" Como corrigir"):
                            st.markdown("""
                            1. **Fornecedores**: Cadastre na aba FINANCEIRO da planilha de Contas Contabeis
                            2. **Tarifas**: Cadastre na aba do banco correspondente (SICOOB ou BANCO DO BRASIL)
                            3. **Entradas**: Cadastre clientes ou contas de receita
                            4. Apos cadastrar, recarregue os arquivos e processe novamente
                            """)
                    else:
                        st.success(" **Todos os lancamentos foram classificados!**")
                        st.balloons()
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

    else:
        for i in range(1, 6):
            with tabs[i]:
                st.warning(" Faca upload de todos os arquivos na aba Upload Arquivos para continuar.")
                
                if i == 1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info("""
                        **Arquivos necessarios:**
                        - Contas Contabeis.xlsx (FINANCEIRO, BANCO DO BRASIL, SICOOB)
                        - Movimentacao.xlsx (PAG SICOOB, PAG BB, CAIXA EMPRESA)
                        - Pelo menos um extrato bancario (SICOOB ou BB)
                        """)
                    with col2:
                        st.info("""
                        **Formatos aceitos:**
                        - Excel (.xlsx)
                        - PDF (se disponivel)
                        """)