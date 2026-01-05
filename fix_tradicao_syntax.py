#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Correção de sintaxe page_tradicao.py - remover else: vazio
"""

with open('streamlit_conciliacao/page_tradicao.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar e remover o bloco problemático (linhas 329-332)
result = []
skip = False
for i, line in enumerate(lines):
    line_num = i + 1
    
    # Pular linhas 329-332
    if 329 <= line_num <= 332:
        skip = True
        continue
    
    result.append(line)

with open('streamlit_conciliacao/page_tradicao.py', 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f"✓ Removido bloco problemático (linhas 329-332)")
print(f"✓ Linhas: {len(lines)} → {len(result)}")
