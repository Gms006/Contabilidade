# -*- coding: utf-8 -*-
"""
Pagina Streamlit para conciliacao contabil da Tradicao Comercio e Servicos.
Interface atualizada com 3 abas principais e botao CSV no topo.
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

    # Botao de download CSV no topo
    if 'trad_csv_data' in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label=" BAIXAR CSV FINAL",
                data=st.session_state['trad_csv_data'],
                file_name=st.session_state.get('trad_csv_filename', 'lancamentos_tradicao.csv'),
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS - INTERFACE SIMPLIFICADA
    # ==========================================================================
    tabs = st.tabs([" Processo", " Resultados", " Avançado"])

    # ====== TAB 0: PROCESSO ======
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

        # Logica do botao CONCILIAR
        if btn:
            with st.spinner("Processando conciliacao..."):
                try:
                    df_resultado, nao_encontrados = conciliar_tradicao(
                        df_extrato_sicoob=df_extrato_sicoob,
                        df_extrato_bb=df_extrato_bb,
                        movimentacao=movimentacao,
                        contas=contas
                    )

                    # Salvar no session_state
                    st.session_state['trad_resultado'] = df_resultado
                    st.session_state['trad_nao_encontrados'] = nao_encontrados
                    st.session_state['trad_df_pag'] = movimentacao  # Para tab avancado
                    st.session_state['trad_df_contas'] = contas

                    if df_extrato_sicoob is not None:
                        st.session_state['trad_df_ext_sicoob'] = df_extrato_sicoob
                    if df_extrato_bb is not None:
                        st.session_state['trad_df_ext_bb'] = df_extrato_bb

                    # Gerar CSV
                    if not df_resultado.empty:
                        buf = BytesIO()
                        df_resultado.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
                        csv_data = buf.getvalue()

                        st.session_state['trad_csv_data'] = csv_data
                        st.session_state['trad_csv_filename'] = "lancamentos_contabeis_tradicao.csv"

                        st.success(" **CSV gerado com sucesso!** Use o botao BAIXAR CSV no topo da pagina.")
                        st.rerun()

                except Exception as e:
                    st.error(f" Erro ao processar: {e}")
                    import traceback
                    with st.expander(" Detalhes do Erro"):
                        st.code(traceback.format_exc())

    # ====== TAB 1: RESULTADOS ======
    with tabs[1]:
        if 'trad_resultado' in st.session_state:
            df_resultado = st.session_state['trad_resultado']
            nao_encontrados = st.session_state.get('trad_nao_encontrados', [])

            # Dashboard de metricas
            st.subheader(" Dashboard de Conciliacao")

            total_lanc = len(df_resultado)
            total_nao_enc = len(nao_encontrados)
            total_ok = total_lanc - total_nao_enc
            pct_ok = (total_ok / total_lanc * 100) if total_lanc > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(" Classificados", total_ok)
            with col2:
                st.metric(" Total Lancamentos", total_lanc)
            with col3:
                st.metric(" Nao Classificados", total_nao_enc)
            with col4:
                st.metric(" Taxa Classificacao", f"{pct_ok:.1f}%")

            st.divider()

            # Resultado
            st.subheader(" Lancamentos Classificados")
            if not df_resultado.empty:
                # Mostrar preview
                st.dataframe(df_resultado.head(20), use_container_width=True, height=400)
                st.caption(f"Mostrando 20 de {len(df_resultado)} lancamentos")
            else:
                st.info("Nenhum lancamento processado")

            st.divider()

            # Nao encontrados
            if nao_encontrados:
                st.subheader(f" Lancamentos Nao Classificados ({len(nao_encontrados)})")
                st.warning("Os itens abaixo nao foram encontrados no plano de contas:")
                
                if isinstance(nao_encontrados, list) and len(nao_encontrados) > 0:
                    if isinstance(nao_encontrados[0], dict):
                        df_nao_encontrados = pd.DataFrame(nao_encontrados)
                        st.dataframe(df_nao_encontrados, use_container_width=True)
                        
                        # Botao para baixar nao classificados
                        csv_nao_enc = df_nao_encontrados.to_csv(sep=";", index=False, encoding="utf-8-sig")
                        st.download_button(
                            " Baixar nao classificados",
                            data=csv_nao_enc.encode("utf-8-sig"),
                            file_name="lancamentos_nao_classificados.csv",
                            mime="text/csv"
                        )
                    else:
                        for item in nao_encontrados[:20]:
                            st.write(f" {item}")
                        if len(nao_encontrados) > 20:
                            st.caption(f"... e mais {len(nao_encontrados) - 20} itens")
                
                with st.expander(" Como corrigir"):
                    st.markdown("""
                    1. **Fornecedores**: Cadastre na aba FINANCEIRO da planilha de Contas Contabeis
                    2. **Tarifas**: Cadastre na aba do banco correspondente (SICOOB ou BANCO DO BRASIL)
                    3. **Entradas**: Cadastre clientes ou contas de receita
                    4. Apos cadastrar, recarregue os arquivos e processe novamente
                    """)
            else:
                st.success(" Todos os lancamentos foram classificados!")
                st.balloons()

            st.divider()

            # Analise de qualidade
            st.subheader(" Analise de Qualidade")

            if pct_ok >= 95:
                st.success(f" **Excelente**: {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("A maioria dos lancamentos foram classificados com sucesso.")
            elif pct_ok >= 85:
                st.warning(f" **Bom**: {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("Alguns lancamentos precisam de atencao.")
            else:
                st.error(f" **Critico**: Apenas {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("Muitos lancamentos nao foram classificados. Revise o plano de contas.")

        else:
            st.info(" Faca upload de todos os arquivos e clique em **PROCESSAR** na aba Processo para ver os resultados.")

    # ====== TAB 2: AVANCADO ======
    with tabs[2]:
        if "trad_df_pag" in st.session_state:
            st.header(" Configuracoes Avancadas")

            # Validacoes de Cadastros
            if "trad_validation_result" in st.session_state:
                validation_result = st.session_state["trad_validation_result"]

                st.subheader(" Validacao de Cadastros")

                if validation_result and validation_result.get("tem_bloqueadores"):
                    st.error(" **PROBLEMAS DETECTADOS** - Corrija antes de exportar")

                    if validation_result.get("fornecedores_faltantes"):
                        with st.expander(
                            f" Fornecedores sem Conta ({len(validation_result['fornecedores_faltantes'])})",
                            expanded=True
                        ):
                            for forn in validation_result["fornecedores_faltantes"]:
                                st.warning(f" {forn}")

                    if validation_result.get("clientes_faltantes"):
                        with st.expander(
                            f" Clientes sem Conta ({len(validation_result['clientes_faltantes'])})",
                            expanded=True
                        ):
                            for cli in validation_result["clientes_faltantes"]:
                                st.warning(f" {cli}")

                    if validation_result.get("contas_especiais_faltantes"):
                        with st.expander(
                            f" Contas Especiais Faltantes ({len(validation_result['contas_especiais_faltantes'])})",
                            expanded=True
                        ):
                            for conta in validation_result["contas_especiais_faltantes"]:
                                st.error(f" {conta}")
                else:
                    st.success(" Todas as validacoes passaram!")

            st.divider()

            # Pre-visualizacao expandida dos dados
            st.subheader(" Pre-visualizacao dos Dados")

            if "trad_df_pag" in st.session_state:
                with st.expander(" Pagamentos (completo)", expanded=False):
                    df_pag = st.session_state["trad_df_pag"]
                    if isinstance(df_pag, dict):
                        for key, df in df_pag.items():
                            st.markdown(f"**{key}**")
                            st.dataframe(df, use_container_width=True, height=200)
                    else:
                        st.dataframe(df_pag, use_container_width=True, height=400)

            if "trad_df_ext_sicoob" in st.session_state:
                with st.expander(" Extrato SICOOB (completo)", expanded=False):
                    df_sicoob = st.session_state["trad_df_ext_sicoob"]
                    st.dataframe(df_sicoob, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_sicoob)} registros")

            if "trad_df_ext_bb" in st.session_state:
                with st.expander(" Extrato BB (completo)", expanded=False):
                    df_bb = st.session_state["trad_df_ext_bb"]
                    st.dataframe(df_bb, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_bb)} registros")

            if "trad_df_contas" in st.session_state:
                with st.expander(" Plano de Contas (completo)", expanded=False):
                    df_contas = st.session_state["trad_df_contas"]
                    if isinstance(df_contas, dict):
                        for key, df in df_contas.items():
                            st.markdown(f"**{key}**")
                            st.dataframe(df, use_container_width=True, height=200)
                    else:
                        st.dataframe(df_contas, use_container_width=True, height=400)

        else:
            st.info(" Faca upload de todos os arquivos na aba **Processo** para acessar configuracoes avancadas.")
