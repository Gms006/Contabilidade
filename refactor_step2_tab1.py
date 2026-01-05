#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para adicionar funcionalidade completa na Tab 1 (Resultados)
"""

def add_tab1_results():
    with open('streamlit_conciliacao/page_drogarias.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar onde está a Tab 1
    tab1_index = -1
    for i, line in enumerate(lines):
        if '# ====== TAB 1: RESULTADOS ======' in line:
            tab1_index = i
            break
    
    if tab1_index == -1:
        print("❌ Não encontrou Tab 1")
        return
    
    # Remover placeholder atual (4 linhas: comentário, with tabs[1], if, else)
    # Encontrar fim do placeholder
    tab1_end = tab1_index + 1
    for i in range(tab1_index + 1, len(lines)):
        if '# ====== TAB 2' in lines[i]:
            tab1_end = i
            break
    
    # Conteúdo novo para Tab 1
    new_tab1 = '''    # ====== TAB 1: RESULTADOS ======
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

'''
    
    # Construir novo arquivo
    result = lines[:tab1_index] + [new_tab1] + lines[tab1_end:]
    
    with open('streamlit_conciliacao/page_drogarias.py', 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print("✅ Tab 1 (Resultados) implementada com sucesso!")
    print(f"   Linhas antes: {len(lines)}")
    print(f"   Linhas depois: {len(result)}")

if __name__ == "__main__":
    add_tab1_results()
