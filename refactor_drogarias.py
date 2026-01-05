"""Script para refatorar page_drogarias.py removendo código duplicado"""

def refactor_page():
    # Ler arquivo original
    with open('streamlit_conciliacao/page_drogarias_backup.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar linhas chave
    result = []
    skip_mode = False
    skip_until_line = -1
    
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # Manter todas as linhas até a seção de tabs
        if line_num < 144:  # Antes do título
            result.append(line)
            continue
            
        # Quando encontrar a definição das 3 tabs novas, começamos a copiar apenas o que importa
        if 'tabs = st.tabs([' in line and '"🏠 Processo"' in line:
            result.append(line)
            # Continuar normalmente após as tabs
            continue
            
        # Pular todo o código antigo das abas 2, 3, 4, 5
        # Manter apenas: aba 0 (Processo), aba 1 (Resultados), aba 2 (Avançado)
        
        # Se encontrar 'with tabs[1]:' dentro da seção else (quando não há arquivos)
        if line_num >= 400 and 'else:' in line and not skip_mode:
            result.append(line)
            # Adicionar apenas mensagem simples para as 3 abas
            result.append('        with tabs[1]:\n')
            result.append('            st.info("📁 Faça upload de todos os arquivos na aba **Processo** para continuar.")\n')
            result.append('        with tabs[2]:\n')
            result.append('            st.info("📁 Faça upload de todos os arquivos na aba **Processo** para continuar.")\n')
            skip_mode = True
            skip_until_line = len(lines)  # Pular até o fim
            continue
            
        if skip_mode and line_num < skip_until_line:
            continue
            
        result.append(line)
    
    # Escrever arquivo refatorado
    with open('streamlit_conciliacao/page_drogarias.py', 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print(f"Refatoração concluída!")
    print(f"Linhas originais: {len(lines)}")
    print(f"Linhas resultantes: {len(result)}")

if __name__ == "__main__":
    refactor_page()
