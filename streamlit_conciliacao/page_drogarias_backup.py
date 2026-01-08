# -*- coding: utf-8 -*-
"""
Pagina Streamlit para conciliacao financeira da Drogarias.
Baseado no reconciliador original.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import os
import sys
from io import BytesIO
import unicodedata

import streamlit as st
import pandas as pd

# === Imports dos servicos ===
try:
    from drogarias.services.parsing import load_payments, load_bank_split, load_chart_of_accounts
    from drogarias.services.matching import match_transactions, MatchParams
    from drogarias.services.accounting import (
        build_entries,
        validate_accounts,
        build_maps,
        _pick_bank_account,
        TARIFA_POR_CONTA_FORNECEDOR,
        CONTA_TARIFA_SOMENTE,
        _get_pagamentos_exigem_316,
    )
except ImportError:
    from drogarias.services.parsing import load_payments, load_bank_split, load_chart_of_accounts
    from drogarias.services.matching import match_transactions, MatchParams
    from drogarias.services.accounting import (
        build_entries,
        validate_accounts,
        build_maps,
        _pick_bank_account,
        TARIFA_POR_CONTA_FORNECEDOR,
        CONTA_TARIFA_SOMENTE,
        _get_pagamentos_exigem_316,
    )


# ============== Helpers locais (UI) ==============
def _clean_name(s: object) -> str:
    """Normalizacao simples (sem acento, minusculo, apenas letras/numeros/espaco)."""
    if s is None:
        return ""
    txt = "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c))
    txt = txt.strip().casefold()
    return "".join(ch for ch in txt if ch.isalnum() or ch.isspace())


def _nz(x, default=0.0) -> float:
    try:
        v = float(x)
        if pd.isna(v):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _fmt_val(v: float) -> str:
    return f"{float(v):0.2f}".replace(".", ",")


# ============== PLANILHAS EXEMPLO ==============
def _gerar_exemplo_pagamentos() -> bytes:
    """Gera planilha exemplo de Pagamentos."""
    df = pd.DataFrame({
        'DATA': ['01/11/2025', '02/11/2025', '03/11/2025', '04/11/2025'],
        'FORNECEDOR': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO MEDICAMENTOS', 'LABORATORIO PHARMA'],
        'NF': ['12345', '67890', '11111', '22222'],
        'VALOR': [1500.00, 2300.50, 890.00, 3200.00],
        'MULTA E JUROS': [0.00, 15.50, 0.00, 25.00],
        'DESCONTO': [50.00, 0.00, 10.00, 0.00],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pagamentos')
    return buffer.getvalue()


def _gerar_exemplo_extrato() -> bytes:
    """Gera planilha exemplo de Extrato Bancario."""
    df_saidas = pd.DataFrame({
        'DATA': ['01/11/2025', '02/11/2025', '03/11/2025', '04/11/2025', '05/11/2025'],
        'HISTORICO': ['PIX ENVIADO FORNECEDOR ABC', 'PAG BOLETO DISTRIBUIDORA', 'TRANSF TED ATACADO', 'PIX ENVIADO LABORATORIO', 'TARIFA PACOTE SERVICOS'],
        'VALOR': [1450.00, 2316.00, 880.00, 3225.00, 45.00],
        'TIPO': ['SAIDA', 'SAIDA', 'SAIDA', 'SAIDA', 'SAIDA'],
    })
    df_entradas = pd.DataFrame({
        'DATA': ['01/11/2025', '03/11/2025'],
        'HISTORICO': ['PIX RECEBIDO CLIENTE JOSE', 'DEPOSITO EM DINHEIRO'],
        'VALOR': [500.00, 1000.00],
        'TIPO': ['ENTRADA', 'ENTRADA'],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_saidas.to_excel(writer, index=False, sheet_name='Saidas')
        df_entradas.to_excel(writer, index=False, sheet_name='Entradas')
    return buffer.getvalue()


def _gerar_exemplo_contas() -> bytes:
    """Gera planilha exemplo de Contas Contabeis."""
    df = pd.DataFrame({
        'NOME': ['FORNECEDOR ABC LTDA', 'DISTRIBUIDORA XYZ', 'ATACADO MEDICAMENTOS', 'LABORATORIO PHARMA', 'CLIENTE JOSE', 'Sicoob', 'Caixa', 'MULTAS E JUROS', 'DESCONTOS'],
        'CONTAS CONTABEIS': [101, 102, 103, 104, 201, 301, 302, 310, 320],
        'HISTORICO': [1, 1, 1, 1, 2, 3, 3, 4, 5],
        'CLASSIFICACAO': ['FORNECEDOR', 'FORNECEDOR', 'FORNECEDOR', 'FORNECEDOR', 'CLIENTE', 'CAIXA E EQUIVALENTES', 'CAIXA E EQUIVALENTES', 'MULTAS E JUROS', 'DESCONTOS'],
    })
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contas')
    return buffer.getvalue()


# ============== PAGINA DROGARIAS ==============
def mostrar_pagina_drogarias():
    """Renderiza a pagina de conciliacao da Drogarias."""

    st.title(" Conciliacao Financeira - Drogarias")
    st.markdown("**Drogarias - Conciliacao de Pagamentos e Extratos**")
    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS
    # ==========================================================================
    tabs = st.tabs([" Upload Arquivos", " Pre-visualizacao", " Conciliacao", " Qualidade", " Export CSV", " Validacoes"])

    # ==========================================================================
    # ABA 0 - UPLOAD DE ARQUIVOS
    # ==========================================================================
    with tabs[0]:
        st.header(" Upload de Arquivos")
        st.markdown("Faca o upload dos arquivos necessarios para a conciliacao.")
        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader(" Pagamentos")
            st.caption("Planilha com os pagamentos realizados")
            up_pag = st.file_uploader(
                "Pagamentos.xlsx",
                type=["xlsx", "xlsm"],
                key="drog_pag",
                help="Arquivo Excel com os pagamentos"
            )
            if up_pag:
                st.success(f" {up_pag.name}")
            else:
                st.warning(" Aguardando arquivo...")

        with col2:
            st.subheader(" Extrato Bancario")
            st.caption("Extrato do banco Sicoob")
            up_ext = st.file_uploader(
                "Extrato Sicoob.xlsx",
                type=["xlsx", "xlsm"],
                key="drog_ext",
                help="Extrato bancario do Sicoob"
            )
            if up_ext:
                st.success(f" {up_ext.name}")
            else:
                st.warning(" Aguardando arquivo...")

        with col3:
            st.subheader(" Contas Contabeis")
            st.caption("Plano de contas contabeis")
            up_contas = st.file_uploader(
                "Contas Contabeis.xlsx",
                type=["xlsx", "xlsm"],
                key="drog_contas",
                help="Planilha com o plano de contas"
            )
            if up_contas:
                st.success(f" {up_contas.name}")
            else:
                st.warning(" Aguardando arquivo...")

        st.divider()

        # ======================================================================
        # PLANILHAS EXEMPLO
        # ======================================================================
        st.subheader(" Planilhas Exemplo")
        st.info("""
        **IMPORTANTE:** Baixe as planilhas exemplo abaixo para entender o formato correto dos arquivos.
        Seus arquivos devem seguir **exatamente** estas estruturas de colunas para que o sistema funcione corretamente.
        """)

        col_ex1, col_ex2, col_ex3 = st.columns(3)

        with col_ex1:
            st.markdown("**Pagamentos**")
            st.caption("Colunas: DATA, FORNECEDOR, NF, VALOR, MULTA E JUROS, DESCONTO")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_pagamentos(),
                file_name="EXEMPLO_Pagamentos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_pag"
            )

        with col_ex2:
            st.markdown("**Extrato Bancario**")
            st.caption("Abas: Saidas e Entradas. Colunas: DATA, HISTORICO, VALOR, TIPO")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_extrato(),
                file_name="EXEMPLO_Extrato_Sicoob.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_ext"
            )

        with col_ex3:
            st.markdown("**Contas Contabeis**")
            st.caption("Colunas: NOME, CONTAS CONTABEIS, HISTORICO, CLASSIFICACAO")
            st.download_button(
                " Baixar Exemplo",
                data=_gerar_exemplo_contas(),
                file_name="EXEMPLO_Contas_Contabeis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ex_contas"
            )

        st.divider()

        # Configuracoes
        st.subheader(" Configuracoes")
        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            banco_padrao = st.text_input("Banco padrao (CAIXA E EQUIVALENTES)", value="Sicoob", key="drog_banco")
        with col_cfg2:
            conta_caixa = st.text_input("Conta Caixa (CAIXA E EQUIVALENTES)", value="Caixa", key="drog_caixa")

        st.subheader(" Parametros de Matching")
        col_match1, col_match2 = st.columns(2)
        with col_match1:
            strict_matching = st.checkbox(
                "Matching rigoroso (Data + Valor exatos)", value=True,
                help="Se desmarcado, permite tolerancia de dias",
                key="drog_strict"
            )
        with col_match2:
            tolerance_days = 0 if strict_matching else st.slider("Tolerancia em dias", 0, 7, 2, key="drog_tol")

        st.divider()

        # Status dos arquivos
        st.subheader(" Status dos Arquivos")
        col_st1, col_st2, col_st3 = st.columns(3)
        with col_st1:
            if up_pag:
                st.success(" Pagamentos OK")
            else:
                st.error(" Pagamentos pendente")
        with col_st2:
            if up_ext:
                st.success(" Extrato OK")
            else:
                st.error(" Extrato pendente")
        with col_st3:
            if up_contas:
                st.success(" Contas OK")
            else:
                st.error(" Contas pendente")

        if up_pag and up_ext and up_contas:
            st.success(" **Todos os arquivos carregados! Navegue para as proximas abas.**")
            btn = st.button(" Conciliar e Gerar CSV", type="primary", key="drog_btn")
        else:
            st.warning(" Faca upload de todos os arquivos para continuar.")
            btn = False

    # ==========================================================================
    # PROCESSAR ARQUIVOS (se todos carregados)
    # ==========================================================================
    if up_pag and up_ext and up_contas:
        try:
            df_pag, cols_pag = load_payments(up_pag)
            df_ext_saidas, df_ext_entradas, cols_ext = load_bank_split(up_ext)
            df_contas, cols_contas = load_chart_of_accounts(up_contas)

            # Validacao
            validation_result = validate_accounts(
                df_pag, cols_pag, df_contas, banco_padrao, conta_caixa,
                df_ext_entradas=df_ext_entradas, df_ext_saidas=df_ext_saidas
            )

        except Exception as e:
            st.error(f" Erro na leitura: {e}")
            validation_result = None
        else:
            # ====== PRE-VISUALIZACAO ======
            with tabs[1]:
                st.header(" Pre-visualizacao dos Dados")
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Pagamentos", len(df_pag))
                with col_m2:
                    st.metric("Saidas Extrato", len(df_ext_saidas))
                with col_m3:
                    st.metric("Entradas Extrato", len(df_ext_entradas))
                with col_m4:
                    if validation_result and validation_result["tem_bloqueadores"]:
                        st.metric("Problemas", validation_result['total_problemas'], delta="Corrigir!")
                    else:
                        st.metric("Validacao", "OK")

                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(" Pagamentos (amostra)")
                    st.dataframe(df_pag.head(10), use_container_width=True)
                    st.subheader(" Extrato Saidas (amostra)")
                    st.dataframe(df_ext_saidas.head(10), use_container_width=True)
                with col2:
                    st.subheader(" Extrato Entradas (amostra)")
                    st.dataframe(df_ext_entradas.head(10), use_container_width=True)
                    st.subheader(" Contas Contabeis (amostra)")
                    st.dataframe(df_contas.head(10), use_container_width=True)

            # ====== VALIDACOES ======
            with tabs[5]:
                st.subheader(" Validacao de Cadastros")

                if validation_result is None:
                    st.error("Erro na validacao - verifique os arquivos carregados")
                elif validation_result["tem_bloqueadores"]:
                    st.error(" **EXPORTACAO BLOQUEADA** - Corrija os problemas abaixo:")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total de Problemas", validation_result["total_problemas"], delta=None)

                    if validation_result["fornecedores_faltantes"]:
                        st.subheader(" Fornecedores sem Conta Cadastrada")
                        for fornecedor in validation_result["fornecedores_faltantes"]:
                            st.write(f" **{fornecedor}**")

                    if validation_result["clientes_faltantes"]:
                        st.subheader(" Clientes sem Conta Cadastrada")
                        for cliente in validation_result["clientes_faltantes"]:
                            st.write(f" **{cliente}**")

                    problemas_especiais = []
                    if validation_result["banco_padrao_faltante"]:
                        problemas_especiais.append(f"Banco padrao: {validation_result['banco_padrao_faltante']}")
                    if validation_result["caixa_faltante"]:
                        problemas_especiais.append(f"Conta Caixa: {validation_result['caixa_faltante']}")
                    if validation_result["precisa_multas_juros"]:
                        problemas_especiais.append("Conta para MULTAS E JUROS")
                    if validation_result["precisa_descontos"]:
                        problemas_especiais.append("Conta para DESCONTOS")
                    if problemas_especiais:
                        st.subheader(" Contas Especiais Faltantes")
                        for problema in problemas_especiais:
                            st.write(f" **{problema}**")

                    if validation_result.get("precisa_tarifa"):
                        st.subheader(" Problema com TARIFA - Conta 316 Nao Encontrada")
                        st.warning(f"Cadastre a conta **{CONTA_TARIFA_SOMENTE}** com CLASSIFICACAO = MULTAS E JUROS")

                else:
                    st.success(" **Todas as validacoes aprovadas!**")
                    st.success(" O sistema esta pronto para gerar o CSV!")

            # ====== BOTAO: CONCILIAR/GERAR ======
            if btn:
                if validation_result and validation_result["tem_bloqueadores"]:
                    st.error(" **Nao e possivel conciliar!** Corrija os problemas na aba Validacoes.")
                    st.stop()

                params = MatchParams(
                    strict_date_matching=strict_matching,
                    tolerance_days=tolerance_days,
                )
                matches, pend_data = match_transactions(df_pag, df_ext_saidas, cols_pag, cols_ext, params)

                st.session_state['drog_matches'] = matches
                st.session_state['drog_pend_data'] = pend_data
                st.session_state['drog_df_pag'] = df_pag
                st.session_state['drog_cols_pag'] = cols_pag
                st.session_state['drog_df_ext_saidas'] = df_ext_saidas
                st.session_state['drog_cols_ext'] = cols_ext
                st.session_state['drog_df_contas'] = df_contas
                st.session_state['drog_df_ext_entradas'] = df_ext_entradas
                st.session_state['drog_banco_padrao'] = banco_padrao
                st.session_state['drog_conta_caixa'] = conta_caixa

            # ====== CONCILIACAO ======
            with tabs[2]:
                if 'drog_matches' in st.session_state:
                    matches = st.session_state['drog_matches']
                    pend_data = st.session_state['drog_pend_data']
                    cols_pag = st.session_state['drog_cols_pag']

                    stats = pend_data.get("stats", {})
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(" Conciliados", stats.get("matches", 0))
                    with col2:
                        st.metric(" Total Pagamentos", stats.get("total_pagamentos", 0))
                    with col3:
                        st.metric(" Saidas Extrato", stats.get("total_saidas", 0))
                    with col4:
                        st.metric(" Taxa Conciliacao", f"{stats.get('pct_conciliacao', 0):.1f}%")

                    st.subheader(" Grupos Conciliados")
                    if not matches.empty:
                        st.dataframe(matches, use_container_width=True)
                    else:
                        st.info("Nenhum match encontrado")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f" Pagamentos Pendentes: {len(pend_data['unmatched_pagamentos'])}")
                        if not pend_data["unmatched_pagamentos"].empty:
                            st.dataframe(pend_data["unmatched_pagamentos"][["_data", "_valor", cols_pag["fornecedor"]]], use_container_width=True)

                    with col2:
                        st.subheader(f" Saidas sem Pagamento: {len(pend_data['unmatched_extrato'])}")
                        if not pend_data["unmatched_extrato"].empty:
                            st.dataframe(pend_data["unmatched_extrato"][["_data", "_valor", "HISTORICO"]], use_container_width=True)
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

            # ====== QUALIDADE ======
            with tabs[3]:
                if 'drog_pend_data' in st.session_state:
                    pend_data = st.session_state['drog_pend_data']
                    stats = pend_data.get("stats", {})
                    st.subheader(" Analise de Qualidade")

                    if stats.get("pct_conciliacao", 0) >= 95:
                        st.success(f" **Excelente**: Taxa de {stats.get('pct_conciliacao', 0):.1f}%")
                    elif stats.get("pct_conciliacao", 0) >= 85:
                        st.warning(f" **Bom**: Taxa de {stats.get('pct_conciliacao', 0):.1f}%")
                    else:
                        st.error(f" **Critico**: Taxa de apenas {stats.get('pct_conciliacao', 0):.1f}%")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(" Pagamentos pelo Caixa", len(pend_data['unmatched_pagamentos']))
                        st.metric(" Saidas nao identificadas", len(pend_data['unmatched_extrato']))
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")

            # ====== EXPORT CSV ======
            with tabs[4]:
                if 'drog_matches' in st.session_state:
                    matches = st.session_state['drog_matches']
                    df_pag = st.session_state['drog_df_pag']
                    cols_pag = st.session_state['drog_cols_pag']
                    df_ext_saidas = st.session_state['drog_df_ext_saidas']
                    cols_ext = st.session_state['drog_cols_ext']
                    df_contas = st.session_state['drog_df_contas']
                    df_ext_entradas = st.session_state['drog_df_ext_entradas']
                    banco_padrao = st.session_state['drog_banco_padrao']
                    conta_caixa = st.session_state['drog_conta_caixa']

                    try:
                        entries = build_entries(
                            matches, df_pag, cols_pag, df_ext_saidas, cols_ext, df_contas,
                            df_ext_entradas=df_ext_entradas, banco_padrao=banco_padrao,
                            conta_caixa_nome=conta_caixa, gerar_pendentes=True,
                        )

                        st.subheader(" Previa do CSV Final")
                        st.dataframe(entries.head(20), use_container_width=True)

                        col1, col2 = st.columns(4)[:2]
                        with col1:
                            st.metric(" Total de Linhas", len(entries))
                        with col2:
                            linhas_com_valor = len(entries[entries["Valor pago"].astype(str).str.strip() != ""])
                            st.metric(" Linhas com Valor", linhas_com_valor)

                        if not entries.empty:
                            buf = BytesIO()
                            entries.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
                            st.download_button(
                                " **Baixar CSV Final**",
                                data=buf.getvalue(),
                                file_name="lancamentos_contabeis_drogarias.csv",
                                mime="text/csv",
                                type="primary",
                            )
                            st.success(" **CSV gerado com sucesso!**")

                    except Exception as e:
                        st.error(f" Erro ao gerar CSV: {e}")
                else:
                    st.info(" Clique em Conciliar e Gerar CSV na aba Upload para processar.")
    else:
        for i in range(1, 6):
            with tabs[i]:
                st.warning(" Faca upload de todos os arquivos na aba Upload Arquivos para continuar.")