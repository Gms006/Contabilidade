# -*- coding: utf-8 -*-
"""
Pagina Streamlit para conciliacao financeira da Drogarias.
Baseado no reconciliador original.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from io import BytesIO
import unicodedata

import streamlit as st
import pandas as pd

# === Imports dos servicos ===
try:
    from drogarias.services.parsing import load_payments, load_bank_split, load_chart_of_accounts
    from drogarias.services.matching import match_transactions, MatchParams
    from services.standardize_extract import standardize_bank_extract, detect_if_needs_standardization
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
    
    # Botão de download CSV no topo - DESTAQUE
    if 'drog_csv_data' in st.session_state:
        st.success("✅ CSV gerado com sucesso!")
        st.download_button(
            label="📥 BAIXAR CSV FINAL",
            data=st.session_state['drog_csv_data'],
            file_name=st.session_state.get('drog_csv_filename', 'lancamentos_drogarias.csv'),
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
    
    st.divider()

    # ==========================================================================
    # TABS PRINCIPAIS
    # ==========================================================================
    tabs = st.tabs(["🏠 Processo", "📊 Resultados", "⚙️ Avançado"])

    # ====== TAB 0: PROCESSO ======
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
            
            # Checkbox para padronização automática
            auto_padronizar = st.checkbox(
                "📋 Padronizar extrato automaticamente",
                value=True,
                key="drog_auto_pad",
                help="Se o extrato estiver no formato bruto do banco, ele será padronizado automaticamente"
            )
            
            up_ext = st.file_uploader(
                "Extrato Sicoob.xlsx",
                type=["xlsx", "xlsm"],
                key="drog_ext",
                help="Extrato bancario do Sicoob (pode ser bruto ou já padronizado)"
            )
            
            if up_ext:
                # Guarda o nome original do arquivo
                original_name = up_ext.name

                # Verifica se precisa padronizar
                if auto_padronizar:
                    try:
                        # Reseta o ponteiro do arquivo
                        up_ext.seek(0)

                        if detect_if_needs_standardization(up_ext):
                            with st.spinner("Padronizando extrato..."):
                                up_ext.seek(0)
                                extrato_padronizado = standardize_bank_extract(up_ext, original_name)
                                
                                # Salva no session_state para usar depois
                                st.session_state['drog_extrato_padronizado'] = extrato_padronizado
                                st.session_state['drog_extrato_padronizado_nome'] = original_name

                                # Substitui o arquivo original pelo padronizado
                                up_ext = extrato_padronizado

                                st.success(f"✅ {original_name} (padronizado)")
                                st.info("💡 Extrato foi padronizado automaticamente")
                        else:
                            # Marca que não precisa padronizar
                            if 'drog_extrato_padronizado' in st.session_state:
                                del st.session_state['drog_extrato_padronizado']
                            st.success(f" {original_name}")
                            st.info("ℹ️ Extrato já está no formato correto")
                    except Exception as e:
                        st.error(f"❌ Erro ao padronizar: {str(e)}")
                        st.warning("⚠️ Usando extrato original sem padronização")
                        if 'drog_extrato_padronizado' in st.session_state:
                            del st.session_state['drog_extrato_padronizado']
                        up_ext.seek(0)
                        st.success(f" {original_name}")
                else:
                    # Desativa padronização
                    if 'drog_extrato_padronizado' in st.session_state:
                        del st.session_state['drog_extrato_padronizado']
                    st.success(f" {original_name}")
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

        # Status e Botão PROCESSAR
        if up_pag and up_ext and up_contas:
            st.success("✅ **Todos os arquivos carregados!**")
            btn = st.button("🚀 CONCILIAR E GERAR CSV", type="primary", key="drog_btn", use_container_width=True)
        else:
            st.warning("⚠️ Faça upload de todos os arquivos para continuar.")
            btn = False

        st.divider()

        # Configurações Avançadas
        with st.expander("⚙️ Configurações Avançadas", expanded=False):
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                banco_padrao = st.text_input("Banco padrão (CAIXA E EQUIVALENTES)", value="Sicoob", key="drog_banco")
            with col_cfg2:
                conta_caixa = st.text_input("Conta Caixa (CAIXA E EQUIVALENTES)", value="Caixa", key="drog_caixa")
 
            st.subheader("📊 Parâmetros de Matching")
            col_match1, col_match2 = st.columns(2)
            with col_match1:
                strict_matching = st.checkbox(
                    "Matching rigoroso (Data + Valor exatos)", value=True,
                    help="Se desmarcado, permite tolerância de dias",
                    key="drog_strict"
                )
            with col_match2:
                tolerance_days = 0 if strict_matching else st.slider("Tolerância em dias", 0, 7, 2, key="drog_tol")

    # ==========================================================================
    # PROCESSAR ARQUIVOS (se todos carregados)
    # ==========================================================================
    if up_pag and up_ext and up_contas:
        try:
            df_pag, cols_pag = load_payments(up_pag)
            df_ext_saidas, df_ext_entradas, cols_ext = load_bank_split(up_ext)
            df_contas, cols_contas = load_chart_of_accounts(up_contas)

            # Salvar no session_state para usar nas tabs
            st.session_state['drog_df_pag'] = df_pag
            st.session_state['drog_cols_pag'] = cols_pag
            st.session_state['drog_df_ext_saidas'] = df_ext_saidas
            st.session_state['drog_df_ext_entradas'] = df_ext_entradas
            st.session_state['drog_cols_ext'] = cols_ext
            st.session_state['drog_df_contas'] = df_contas
            st.session_state['drog_banco_padrao'] = banco_padrao
            st.session_state['drog_conta_caixa'] = conta_caixa

            # Validacao
            validation_result = validate_accounts(
                df_pag, cols_pag, df_contas, banco_padrao, conta_caixa,
                df_ext_entradas=df_ext_entradas, df_ext_saidas=df_ext_saidas
            )
            st.session_state['drog_validation_result'] = validation_result

            # Lógica do botão CONCILIAR
            if btn:
                if validation_result and validation_result.get("tem_bloqueadores"):
                    st.error("⚠️ **Não é possível conciliar!** Corrija os problemas na aba Avançado.")
                    st.stop()

                # Fazer matching
                params = MatchParams(
                    strict_date_matching=strict_matching,
                    tolerance_days=tolerance_days,
                )
                matches, pend_data = match_transactions(df_pag, df_ext_saidas, cols_pag, cols_ext, params)

                # Salvar no session_state
                st.session_state['drog_matches'] = matches
                st.session_state['drog_pend_data'] = pend_data

                # Gerar CSV
                try:
                    entries = build_entries(
                        matches, df_pag, cols_pag, df_ext_saidas, cols_ext, df_contas,
                        df_ext_entradas=df_ext_entradas, banco_padrao=banco_padrao,
                        conta_caixa_nome=conta_caixa, gerar_pendentes=True,
                    )

                    if not entries.empty:
                        buf = BytesIO()
                        entries.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
                        csv_data = buf.getvalue()

                        # Salvar CSV no session_state
                        st.session_state['drog_csv_data'] = csv_data
                        st.session_state['drog_csv_filename'] = "lancamentos_contabeis_drogarias.csv"

                        st.success("✅ CSV gerado com sucesso! Use o botão 'BAIXAR CSV' no topo da página.")

                except Exception as e:
                    st.error(f"❌ Erro ao gerar CSV: {e}")

        except Exception as e:
            st.error(f"❌ Erro na leitura: {e}")
            import traceback
            with st.expander("🔍 Detalhes do Erro"):
                st.code(traceback.format_exc())

    # ====== TAB 1: RESULTADOS ======
    with tabs[1]:
        if 'drog_matches' in st.session_state:
            matches = st.session_state['drog_matches']
            pend_data = st.session_state['drog_pend_data']
            cols_pag = st.session_state['drog_cols_pag']
            cols_ext = st.session_state['drog_cols_ext']

            # Dashboard de métricas
            stats = pend_data.get("stats", {})
            st.subheader("📊 Dashboard de Conciliação")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✓ Conciliados", stats.get("matches", 0))
            with col2:
                st.metric("📄 Total Pagamentos", stats.get("total_pagamentos", 0))
            with col3:
                st.metric("💳 Saídas Extrato", stats.get("total_saidas", 0))
            with col4:
                pct = stats.get('pct_conciliacao', 0)
                delta_color = "normal" if pct >= 90 else "inverse"
                st.metric("🎯 Taxa Conciliação", f"{pct:.1f}%")

            st.divider()

            # Grupos conciliados
            st.subheader("✓ Grupos Conciliados")
            if not matches.empty:
                st.dataframe(matches, use_container_width=True, height=300)
            else:
                st.info("Nenhum match encontrado")

            st.divider()

            # Pendências lado a lado
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"⏳ Pagamentos Pendentes: {len(pend_data['unmatched_pagamentos'])}")
                if not pend_data["unmatched_pagamentos"].empty:
                    st.dataframe(
                        pend_data["unmatched_pagamentos"][["_data", "_valor", cols_pag["fornecedor"]]],
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.success("Todos os pagamentos foram conciliados!")

            with col2:
                st.subheader(f"❓ Saídas sem Pagamento: {len(pend_data['unmatched_extrato'])}")
                if not pend_data["unmatched_extrato"].empty:
                    st.dataframe(
                        pend_data["unmatched_extrato"][["_data", "_valor", cols_ext["historico"]]],
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.success("Todas as saídas foram identificadas!")

            st.divider()

            # Análise de qualidade
            st.subheader("📈 Análise de Qualidade")
            pct_conciliacao = stats.get("pct_conciliacao", 0)
            
            if pct_conciliacao >= 95:
                st.success(f"✓ **Excelente**: Taxa de conciliação de {pct_conciliacao:.1f}%")
                st.caption("A maioria dos lançamentos foram conciliados com sucesso.")
            elif pct_conciliacao >= 85:
                st.warning(f"⚠ **Bom**: Taxa de conciliação de {pct_conciliacao:.1f}%")
                st.caption("Há algumas pendências que merecem atenção.")
            else:
                st.error(f"✗ **Crítico**: Taxa de apenas {pct_conciliacao:.1f}%")
                st.caption("Muitos lançamentos não foram conciliados. Revise os dados.")
                
        else:
            st.info("📁 Faça upload de todos os arquivos e clique em **PROCESSAR** na aba Processo para ver os resultados.")

    # ====== TAB 2: AVANÇADO ======
    with tabs[2]:
        if 'drog_df_pag' in st.session_state:
            st.header("⚙️ Configurações Avançadas")
            
            # Validações de Cadastros
            if 'drog_validation_result' in st.session_state:
                validation_result = st.session_state['drog_validation_result']
                
                st.subheader("🔍 Validação de Cadastros")
                
                if validation_result and validation_result.get("tem_bloqueadores"):
                    st.error("⚠️ **PROBLEMAS DETECTADOS** - Corrija antes de exportar")
                    
                    # Fornecedores faltantes
                    if validation_result.get("fornecedores_faltantes"):
                        with st.expander(
                            f"❌ Fornecedores sem Conta ({len(validation_result['fornecedores_faltantes'])})",
                            expanded=True
                        ):
                            for forn in validation_result['fornecedores_faltantes']:
                                st.warning(f"• {forn}")
                    
                    # Clientes faltantes
                    if validation_result.get("clientes_faltantes"):
                        with st.expander(
                            f"❌ Clientes sem Conta ({len(validation_result['clientes_faltantes'])})",
                            expanded=True
                        ):
                            for cli in validation_result['clientes_faltantes']:
                                st.warning(f"• {cli}")
                    
                    # Contas especiais faltantes
                    if validation_result.get("contas_especiais_faltantes"):
                        with st.expander(
                            f"❌ Contas Especiais Faltantes ({len(validation_result['contas_especiais_faltantes'])})",
                            expanded=True
                        ):
                            for conta in validation_result['contas_especiais_faltantes']:
                                st.error(f"• {conta}")
                else:
                    st.success("✓ Todas as validações passaram!")
            
            st.divider()
            
            # Pré-visualização expandida dos dados
            st.subheader("📋 Pré-visualização dos Dados")
            
            # Pagamentos
            if 'drog_df_pag' in st.session_state:
                with st.expander("💳 Pagamentos (completo)", expanded=False):
                    df_pag = st.session_state['drog_df_pag']
                    st.dataframe(df_pag, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_pag)} registros")
            
            # Extrato - Saídas
            if 'drog_df_ext_saidas' in st.session_state:
                with st.expander("📤 Extrato - Saídas (completo)", expanded=False):
                    df_saidas = st.session_state['drog_df_ext_saidas']
                    st.dataframe(df_saidas, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_saidas)} registros")
            
            # Extrato - Entradas
            if 'drog_df_ext_entradas' in st.session_state:
                with st.expander("📥 Extrato - Entradas (completo)", expanded=False):
                    df_entradas = st.session_state['drog_df_ext_entradas']
                    st.dataframe(df_entradas, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_entradas)} registros")
                    
                    # Botão para baixar entradas
                    if not df_entradas.empty:
                        buf = BytesIO()
                        df_entradas.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
                        st.download_button(
                            "⬇️ Baixar Entradas CSV",
                            data=buf.getvalue(),
                            file_name="entradas_extrato.csv",
                            mime="text/csv"
                        )
            
            # Plano de contas
            if 'drog_df_contas' in st.session_state:
                with st.expander("📊 Plano de Contas (completo)", expanded=False):
                    df_contas = st.session_state['drog_df_contas']
                    st.dataframe(df_contas, use_container_width=True, height=400)
                    st.caption(f"Total: {len(df_contas)} contas")
                    
        else:
            st.info("📁 Faça upload de todos os arquivos na aba **Processo** para acessar configurações avançadas.")
