#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para refatorar page_drogarias.py de 6 tabs para 3 tabs
"""

def refactor_to_3_tabs():
    # Ler arquivo backup
    with open('streamlit_conciliacao/page_drogarias_backup.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Arquivo original: {len(lines)} linhas")
    
    # Nova versão limpa
    result = []
    
    # Parte 1: Tudo até antes das tabs (linhas 1-134)
    result.extend(lines[0:134])
    print(f"✓ Cabeçalho copiado: linhas 1-134")
    
    # Parte 2: Nova definição de 3 tabs
    result.append('    tabs = st.tabs(["🏠 Processo", "📊 Resultados", "⚙️ Avançado"])\n')
    result.append('\n')
    result.append('    # ====== TAB 0: PROCESSO ======\n')
    print(f"✓ Definição das 3 tabs adicionada")
    
    # Parte 3: Manter tabs[0] original (Upload) - linhas 140-303
    result.extend(lines[139:303])
    print(f"✓ Tab 0 (Processo) copiada: linhas 140-303")
    
    # Parte 4: Adicionar tabs[1] e tabs[2] vazias por enquanto
    result.append('\n')
    result.append('    # ====== TAB 1: RESULTADOS ======\n')
    result.append('    with tabs[1]:\n')
    result.append('        if "drog_matches" in st.session_state:\n')
    result.append('            st.info("Funcionalidade em implementação...")\n')
    result.append('        else:\n')
    result.append('            st.info("📁 Faça upload de todos os arquivos na aba **Processo** para continuar.")\n')
    result.append('\n')
    result.append('    # ====== TAB 2: AVANÇADO ======\n')
    result.append('    with tabs[2]:\n')
    result.append('        if "drog_df_pag" in st.session_state:\n')
    result.append('            st.info("Funcionalidade em implementação...")\n')
    result.append('        else:\n')
    result.append('            st.info("📁 Faça upload de todos os arquivos na aba **Processo** para continuar.")\n')
    print(f"✓ Tabs 1 e 2 (placeholders) adicionadas")
    
    # Escrever arquivo limpo
    with open('streamlit_conciliacao/page_drogarias.py', 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print(f"\n✅ REFATORAÇÃO CONCLUÍDA")
    print(f"   Original: {len(lines)} linhas")
    print(f"   Refatorado: {len(result)} linhas")
    print(f"   Redução: {len(lines) - len(result)} linhas")
    print(f"\n📋 Estrutura:")
    print(f"   - 3 tabs: Processo, Resultados, Avançado")
    print(f"   - Tab 0: Upload e processamento funcionais")
    print(f"   - Tabs 1 e 2: Placeholders para próxima etapa")

if __name__ == "__main__":
    refactor_to_3_tabs()
