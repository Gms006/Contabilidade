# -*- coding: utf-8 -*-
"""
Pagina Streamlit para conciliacao contabil da VPS METALURGICA
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
    """Gera planilha exemplo de Contas Contabeis com 4 abas."""
    df_financeiro = pd.DataFrame({
        'LANCAMENTOS': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO NORTE', 'SERVICOS GERAIS'],
        'CONTAS': [101, 102, 103, 104],
        'HISTORICO': [34, 34, 34, 34],
    })
    df_sicoob = pd.DataFrame({
        'LANCAMENTOS': ['TARIFA MENSAL', 'IOF', 'PIX RECEBIDO', 'TED RECEBIDA'],
        'CONTAS': [170, 171, 5, 5],
        'Historico': [11, 11, 2, 2],
    })
    df_bradesco = pd.DataFrame({
        'LANCAMENTOS': ['TARIFA PACOTE', 'DEB PACOTE SERVICOS', 'PIX RECEBIDO', 'DEPOSITO'],
        'CONTAS': [170, 170, 5, 5],
        'Historico': [11, 11, 2, 9],
    })
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
    """Gera planilha exemplo de Lancamentos."""
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
    """Renderiza a pagina de conciliacao da VPS METALURGICA."""

    st.title("Conciliacao Contabil - VPS METALURGICA")
    st.markdown("**VPS METALURGICA**")

    # Botao de download CSV no topo
    if 'vps_csv_data' in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="BAIXAR CSV FINAL",
                data=st.session_state['vps_csv_data'],
                file_name=st.session_state.get('vps_csv_filename', 'lancamentos_vps.csv'),
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS - INTERFACE SIMPLIFICADA
    # ==========================================================================
    tabs = st.tabs(["Processo", "Resultados", "Avancado"])

    # ====== TAB 0: PROCESSO ======
    with tabs[0]:
        st.header("Upload de Arquivos")
        st.markdown("Faca o upload dos arquivos necessarios para a conciliacao.")
        st.divider()

        # Arquivos Base
        st.subheader("Arquivos Base")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Contas Contabeis**")
            st.caption("Planilha com as abas: RELATORIO FINANCEIRO, SICOOB, BRADESCO, SICREDI")
            contas_file = st.file_uploader(
                "Contas Contabeis.xlsx",
                type=["xlsx"],
                key="upload_vps_contas",
                help="Planilha com mapeamento de fornecedores e historicos bancarios para contas contabeis"
            )
            if contas_file:
                st.success(f" {contas_file.name}")
            else:
                st.warning("Aguardando arquivo...")

        with col2:
            st.markdown("**Lancamentos**")
            st.caption("Planilha financeira com os pagamentos realizados")
            lancamentos_file = st.file_uploader(
                "Lancamentos.xlsx",
                type=["xlsx"],
                key="upload_vps_lancamentos",
                help="Planilha com fornecedor, NF, valores, datas e banco de pagamento"
            )
            if lancamentos_file:
                st.success(f" {lancamentos_file.name}")
            else:
                st.warning("Aguardando arquivo...")

        st.divider()

        # Extratos
        st.subheader("Extratos Bancarios")
        st.markdown("**Extrato Consolidado**")
        st.caption("Planilha unica com todas as movimentacoes dos bancos (SICOOB, BRADESCO, SICREDI)")
        extratos_file = st.file_uploader(
            "Extratos.xlsx",
            type=["xlsx"],
            key="upload_vps_extratos",
            help="Planilha com Data, Historico e Valor (formato C/D ou +/-)"
        )
        if extratos_file:
            st.success(f" {extratos_file.name}")
        else:
            st.warning("Aguardando arquivo...")

        st.divider()

        # Planilhas Exemplo
        st.subheader("Planilhas Exemplo")
        st.info("""
        **IMPORTANTE:** Baixe as planilhas exemplo abaixo para entender o formato correto dos arquivos.
        Seus arquivos devem seguir **exatamente** estas estruturas de colunas e abas para que o sistema funcione corretamente.
        """)

        col_ex1, col_ex2, col_ex3 = st.columns(3)

        with col_ex1:
            st.markdown("**Contas Contabeis**")
            st.caption("Abas: RELATORIO FINANCEIRO, SICOOB, BRADESCO, SICREDI")
            st.download_button(
                "Baixar Exemplo",
                data=_gerar_exemplo_contas_contabeis(),
                file_name="EXEMPLO_Contas_Contabeis_VPS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_contas_vps"
            )

        with col_ex2:
            st.markdown("**Lancamentos**")
            st.caption("Colunas: FORNECEDOR, NF, Vencimento, Valor, etc")
            st.download_button(
                "Baixar Exemplo",
                data=_gerar_exemplo_lancamentos(),
                file_name="EXEMPLO_Lancamentos_VPS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_lanc_vps"
            )

        with col_ex3:
            st.markdown("**Extratos**")
            st.caption("Colunas: DATA, HISTORICO, VALOR")
            st.download_button(
                "Baixar Exemplo",
                data=_gerar_exemplo_extratos(),
                file_name="EXEMPLO_Extratos_VPS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_ext_vps"
            )

        st.divider()

        # Status dos arquivos
        st.subheader("Status dos Arquivos")
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            if contas_file:
                st.success("Contas OK")
            else:
                st.error("Contas pendente")
        with col_st2:
            if lancamentos_file:
                st.success("Lancamentos OK")
            else:
                st.error("Lancamentos pendente")
        with col_st3:
            if extratos_file:
                st.success("Extratos OK")
            else:
                st.error("Extratos pendente")

        # Verificar arquivos e botao
        arquivos_ok = contas_file is not None and lancamentos_file is not None and extratos_file is not None

        if arquivos_ok:
            st.success("**Todos os arquivos carregados!**")
            btn = st.button("CONCILIAR E GERAR CSV", type="primary", key="vps_btn", use_container_width=True)
        else:
            st.warning("Faca upload de todos os arquivos para continuar.")
            btn = False

    # ==========================================================================
    # PROCESSAR ARQUIVOS (se todos carregados)
    # ==========================================================================
    if arquivos_ok:
        try:
            # Carrega arquivos
            contas = carregar_contas_contabeis(contas_file)
            df_lancamentos = carregar_lancamentos(lancamentos_file)
            df_extratos = carregar_extratos(extratos_file)

            # Salva no session_state
            st.session_state['vps_contas'] = contas
            st.session_state['vps_lancamentos'] = df_lancamentos
            st.session_state['vps_extratos'] = df_extratos

            # Logica do botao CONCILIAR
            if btn:
                with st.spinner("Processando conciliacao..."):
                    try:
                        # Executa conciliacao
                        df_resultado, stats = conciliar_vps(
                            df_lancamentos=df_lancamentos.copy(),
                            df_extrato=df_extratos.copy(),
                            contas_contabeis=contas
                        )

                        # Salva resultados
                        st.session_state['vps_resultado'] = df_resultado
                        st.session_state['vps_stats'] = stats

                        # Gerar CSV
                        if not df_resultado.empty:
                            # Prepara CSV
                            df_csv = df_resultado.copy()
                            colunas_padrao = ['DATA', 'COD_CONTA_DEBITO', 'COD_CONTA_CREDITO', 'VALOR', 'COD_HISTORICO', 'COMPLEMENTO', 'INICIA_LOTE']
                            df_csv = df_csv[[c for c in colunas_padrao if c in df_csv.columns]]

                            if 'STATUS' in df_resultado.columns:
                                df_csv = df_resultado[df_resultado['STATUS'] == 'OK'][[c for c in colunas_padrao if c in df_resultado.columns]]

                            df_csv = df_csv.rename(columns={
                                'DATA': 'Data',
                                'COD_CONTA_DEBITO': 'Cod. Conta Debito',
                                'COD_CONTA_CREDITO': 'Cod. Conta Credito',
                                'VALOR': 'Valor',
                                'COD_HISTORICO': 'Cod. Historico',
                                'COMPLEMENTO': 'Complemento Historico',
                                'INICIA_LOTE': 'Inicia Lote'
                            })

                            csv_buffer = io.BytesIO()
                            df_csv.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
                            csv_data = csv_buffer.getvalue()

                            st.session_state['vps_csv_data'] = csv_data
                            st.session_state['vps_csv_filename'] = f"lancamentos_vps_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"

                            st.success("CSV gerado com sucesso! Use o botao BAIXAR CSV no topo da pagina.")
                            st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao processar: {e}")
                        import traceback
                        with st.expander("Detalhes do Erro"):
                            st.code(traceback.format_exc())

        except Exception as e:
            st.error(f"Erro na leitura: {e}")
            import traceback
            with st.expander("Detalhes do Erro"):
                st.code(traceback.format_exc())

    # ====== TAB 1: RESULTADOS ======
    with tabs[1]:
        if 'vps_resultado' in st.session_state:
            df_resultado = st.session_state['vps_resultado']
            stats = st.session_state['vps_stats']

            # Dashboard de metricas
            st.subheader("Dashboard de Conciliacao")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Lancamentos", stats['total_lancamentos'])
            with col2:
                st.metric("Conciliados", stats['conciliados_lancamento'])
            with col3:
                st.metric("Nao Classificados", stats['nao_classificados'])
            with col4:
                ok = len(df_resultado[df_resultado.get('STATUS', 'OK') == 'OK']) if 'STATUS' in df_resultado.columns else len(df_resultado)
                taxa = (ok / len(df_resultado) * 100) if len(df_resultado) > 0 else 0
                st.metric("Taxa Sucesso", f"{taxa:.1f}%")

            st.divider()

            # Resultado
            st.subheader("Lancamentos Gerados")

            # Filtro
            filtro = st.radio("Filtrar por:", ["Todos", "Classificados", "Nao Classificados"], horizontal=True)

            if 'STATUS' in df_resultado.columns:
                if filtro == "Classificados":
                    df_exibir = df_resultado[df_resultado['STATUS'] == 'OK']
                elif filtro == "Nao Classificados":
                    df_exibir = df_resultado[df_resultado['STATUS'] == 'NAO_CLASSIFICADO']
                else:
                    df_exibir = df_resultado
            else:
                df_exibir = df_resultado

            st.dataframe(df_exibir, use_container_width=True, height=400)
            st.caption(f"Exibindo {len(df_exibir)} de {len(df_resultado)} lancamentos")

            st.divider()

            # Nao classificados
            if stats['nao_classificados'] > 0:
                st.subheader(f"Lancamentos Nao Classificados ({stats['nao_classificados']})")
                st.warning("Os itens abaixo nao foram encontrados no plano de contas:")

                if 'STATUS' in df_resultado.columns:
                    df_nao_class = df_resultado[df_resultado['STATUS'] == 'NAO_CLASSIFICADO'].copy()
                    st.dataframe(df_nao_class, use_container_width=True)

                    # Botao para baixar nao classificados
                    csv_buffer = io.BytesIO()
                    df_nao_class.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
                    st.download_button(
                        "Baixar Nao Classificados",
                        data=csv_buffer.getvalue(),
                        file_name="lancamentos_nao_classificados_vps.csv",
                        mime="text/csv"
                    )

                with st.expander("Como corrigir"):
                    st.markdown("""
                    1. **Fornecedores**: Cadastre na aba RELATORIO FINANCEIRO da planilha de Contas Contabeis
                    2. **Tarifas bancarias**: Cadastre na aba do banco correspondente (SICOOB, BRADESCO ou SICREDI)
                    3. **Entradas**: Cadastre clientes ou contas de receita
                    4. Apos cadastrar, recarregue os arquivos e processe novamente
                    """)
            else:
                st.success("Todos os lancamentos foram classificados!")
                st.balloons()

            st.divider()

            # Analise de qualidade
            st.subheader("Analise de Qualidade")
            ok = len(df_resultado[df_resultado.get('STATUS', 'OK') == 'OK']) if 'STATUS' in df_resultado.columns else len(df_resultado)
            pct_ok = (ok / len(df_resultado) * 100) if len(df_resultado) > 0 else 0

            if pct_ok >= 95:
                st.success(f"**Excelente**: {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("A maioria dos lancamentos foram classificados com sucesso.")
            elif pct_ok >= 85:
                st.warning(f"**Bom**: {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("Alguns lancamentos precisam de atencao.")
            else:
                st.error(f"**Critico**: Apenas {pct_ok:.1f}% dos lancamentos classificados")
                st.caption("Muitos lancamentos nao foram classificados. Revise o plano de contas.")

        else:
            st.info("Faca upload de todos os arquivos e clique em **PROCESSAR** na aba Processo para ver os resultados.")

    # ====== TAB 2: AVANCADO ======
    with tabs[2]:
        if 'vps_lancamentos' in st.session_state:
            st.header("Configuracoes Avancadas")

            st.divider()

            # Pre-visualizacao expandida dos dados
            st.subheader("Pre-visualizacao dos Dados")

            # Lancamentos
            if 'vps_lancamentos' in st.session_state:
                with st.expander("Lancamentos (completo)", expanded=False):
                    df_lanc = st.session_state['vps_lancamentos']
                    st.dataframe(df_lanc, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_lanc)} registros")

                    # Estatisticas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_pago = df_lanc['VALOR_PAGO'].sum() if 'VALOR_PAGO' in df_lanc.columns else 0
                        st.metric("Total Pago", f"R$ {_fmt_val(total_pago)}")
                    with col2:
                        total_juros = df_lanc['JUROS_MULTAS'].sum() if 'JUROS_MULTAS' in df_lanc.columns else 0
                        st.metric("Total Juros/Multas", f"R$ {_fmt_val(total_juros)}")
                    with col3:
                        if 'BANCO' in df_lanc.columns:
                            bancos = df_lanc['BANCO'].value_counts()
                            st.metric("Bancos Utilizados", len(bancos))

            # Extratos
            if 'vps_extratos' in st.session_state:
                with st.expander("Extratos Bancarios (completo)", expanded=False):
                    df_ext = st.session_state['vps_extratos']
                    st.dataframe(df_ext, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_ext)} movimentacoes")

                    # Estatisticas
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'TIPO_MOVIMENTO' in df_ext.columns and 'VALOR_ABS' in df_ext.columns:
                            total_creditos = df_ext[df_ext['TIPO_MOVIMENTO'] == 'CREDITO']['VALOR_ABS'].sum()
                            st.metric("Total Creditos", f"R$ {_fmt_val(total_creditos)}")
                    with col2:
                        if 'TIPO_MOVIMENTO' in df_ext.columns and 'VALOR_ABS' in df_ext.columns:
                            total_debitos = df_ext[df_ext['TIPO_MOVIMENTO'] == 'DEBITO']['VALOR_ABS'].sum()
                            st.metric("Total Debitos", f"R$ {_fmt_val(total_debitos)}")

            # Contas Contabeis
            if 'vps_contas' in st.session_state:
                contas = st.session_state['vps_contas']
                if contas and isinstance(contas, dict):
                    with st.expander("Plano de Contas (completo)", expanded=False):
                        for aba_nome, df_aba in contas.items():
                            if df_aba is not None and isinstance(df_aba, pd.DataFrame):
                                st.markdown(f"**{aba_nome}**")
                                st.dataframe(df_aba, use_container_width=True, height=200)
                                st.caption(f"Total: {len(df_aba)} registros")
                                st.divider()

        else:
            st.info("Faca upload de todos os arquivos na aba **Processo** para acessar configuracoes avancadas.")


if __name__ == "__main__":
    mostrar_pagina_vps()
