#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para adicionar funcionalidade completa na Tab 2 (Avançado)
"""

def add_tab2_advanced():
    with open('streamlit_conciliacao/page_drogarias.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar onde está a Tab 2
    tab2_index = -1
    for i, line in enumerate(lines):
        if '# ====== TAB 2: AVANÇADO ======' in line:
            tab2_index = i
            break
    
    if tab2_index == -1:
        print("❌ Não encontrou Tab 2")
        return
    
    # Remover placeholder atual
    tab2_end = len(lines)  # Vai até o final do arquivo
    
    # Conteúdo novo para Tab 2
    new_tab2 = '''    # ====== TAB 2: AVANÇADO ======
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
                        from io import BytesIO
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
'''
    
    # Construir novo arquivo
    result = lines[:tab2_index] + [new_tab2]
    
    with open('streamlit_conciliacao/page_drogarias.py', 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print("✅ Tab 2 (Avançado) implementada com sucesso!")
    print(f"   Linhas antes: {len(lines)}")
    print(f"   Linhas depois: {len(result)}")

if __name__ == "__main__":
    add_tab2_advanced()
