"""
Módulo para padronização de extratos bancários
Converte extratos em formato bruto para o formato padronizado esperado pelo sistema
"""

import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
import re


def is_transaction_line(valor):
    """
    Verifica se uma linha é uma transação válida (termina com C ou D)
    """
    if pd.isna(valor):
        return False
    
    valor_str = str(valor).strip()
    if not valor_str:
        return False
    
    # Remove espaços non-breaking
    valor_str = valor_str.replace('\xa0', ' ').strip()
    
    # Verifica se termina com C ou D
    last_char = valor_str[-1].upper()
    return last_char in ['C', 'D']


def is_saldo_line(historico):
    """
    Verifica se é uma linha de saldo que deve ser ignorada
    """
    if pd.isna(historico):
        return False
    
    hist_upper = str(historico).upper()
    
    # Mantém SALDO ANTERIOR
    if 'SALDO ANTERIOR' in hist_upper and 'BLOQUEADO' not in hist_upper:
        return False
    
    # Ignora outros saldos e linhas especiais
    keywords = ['ABERTURA', 'ENCERRAMENTO', 'SALDO DO DIA', 'SALDO BLOQUEADO']
    return any(kw in hist_upper for kw in keywords)


def extract_main_historico(historico):
    """
    Extrai apenas o histórico principal, removendo detalhes após "|"
    """
    if pd.isna(historico):
        return ""
    
    hist = str(historico).strip()
    
    # Remove tudo após "|" se existir
    pipe_pos = hist.find('|')
    if pipe_pos > 0:
        hist = hist[:pipe_pos].strip()
    
    return hist


def parse_valor_cd(valor):
    """
    Converte valor no formato "1.234,56 C" ou "1.234,56 D" para float
    C = positivo, D = negativo
    """
    if pd.isna(valor):
        return 0.0
    
    valor_str = str(valor).strip()
    valor_str = valor_str.replace('\xa0', ' ').strip()
    
    if not valor_str:
        return 0.0
    
    # Pega o último caractere (C ou D)
    last_char = valor_str[-1].upper()
    
    # Remove o C/D e espaços
    body = valor_str[:-1].strip()
    
    # Remove separadores de milhares (.)
    body = body.replace('.', '')
    
    # Troca vírgula por ponto (padrão Python)
    body = body.replace(',', '.')
    
    # Remove espaços restantes
    body = body.replace(' ', '')
    
    if not body:
        return 0.0
    
    try:
        valor_float = float(body)
        
        # Se for D (débito), torna negativo
        if last_char == 'D':
            valor_float = -abs(valor_float)
        else:
            valor_float = abs(valor_float)
        
        return valor_float
    except:
        return 0.0


def parse_date_smart(data_val, last_date=None):
    """
    Tenta parsear a data de forma inteligente
    Se falhar, usa a última data válida
    """
    if pd.isna(data_val):
        return last_date
    
    # Se já é datetime, retorna
    if isinstance(data_val, datetime):
        return data_val
    
    # Tenta converter string
    try:
        data_str = str(data_val).strip()
        
        # Formato dd/mm/yyyy
        if '/' in data_str and len(data_str) == 10:
            parts = data_str.split('/')
            if len(parts) == 3:
                dia = int(parts[0])
                mes = int(parts[1])
                ano = int(parts[2])
                return datetime(ano, mes, dia)
        
        # Tenta parsear direto
        return pd.to_datetime(data_val, dayfirst=True)
    
    except:
        return last_date


def standardize_bank_extract(file_content, file_name="extrato.xlsx"):
    """
    Padroniza um extrato bancário bruto para o formato esperado
    
    Args:
        file_content: BytesIO ou caminho do arquivo
        file_name: Nome do arquivo (para determinar tipo)
    
    Returns:
        BytesIO com a planilha padronizada
    """
    
    # Lê o arquivo Excel
    if isinstance(file_content, str):
        df = pd.read_excel(file_content, header=None)
    else:
        df = pd.read_excel(file_content, header=None)
    
    # Encontra o cabeçalho
    header_row = None
    for idx in range(min(10, len(df))):
        row_str = ' '.join([str(x).upper() for x in df.iloc[idx] if pd.notna(x)])
        if 'DATA' in row_str and 'VALOR' in row_str:
            header_row = idx
            break
    
    if header_row is None:
        raise ValueError("Não foi possível encontrar o cabeçalho (DATA, VALOR) no extrato")
    
    # Identifica colunas (assume ordem: DATA, DOCUMENTO, HISTORICO, VALOR)
    col_data = 0
    col_doc = 1
    col_hist = 2
    col_valor = 3
    
    # Processa as transações
    transactions = []
    last_date = None
    
    start_row = header_row + 1
    n_rows = len(df)
    
    # Identifica todas as linhas de transação
    transaction_rows = []
    for idx in range(start_row, n_rows):
        valor = df.iloc[idx, col_valor]
        if is_transaction_line(valor):
            historico = df.iloc[idx, col_hist]
            if not is_saldo_line(historico):
                transaction_rows.append(idx)
    
    # Processa cada transação
    for row_idx in transaction_rows:
        # Data
        data_val = df.iloc[row_idx, col_data]
        data = parse_date_smart(data_val, last_date)
        if data:
            last_date = data
        
        # Documento
        documento = df.iloc[row_idx, col_doc]
        doc_str = str(documento).strip() if pd.notna(documento) else ""
        
        # Histórico - APENAS da linha principal
        historico = df.iloc[row_idx, col_hist]
        hist_str = extract_main_historico(historico)
        
        # Verifica se é linha de saldo (double check)
        if is_saldo_line(hist_str):
            continue
        
        # Valor
        valor = df.iloc[row_idx, col_valor]
        valor_float = parse_valor_cd(valor)
        
        # Adiciona apenas se valor != 0
        if valor_float != 0.0:
            transactions.append({
                'DATA': data,
                'DOCUMENTO': doc_str,
                'HISTÓRICO': hist_str,
                'VALOR': valor_float
            })
    
    if not transactions:
        raise ValueError("Nenhuma transação válida encontrada no extrato")
    
    # Cria DataFrame padronizado
    df_padrao = pd.DataFrame(transactions)
    
    # Ordena por data e documento
    df_padrao = df_padrao.sort_values(['DATA', 'DOCUMENTO'], ascending=True)
    
    # Formata a data
    df_padrao['DATA'] = pd.to_datetime(df_padrao['DATA'])
    
    # Cria arquivo Excel em memória
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_padrao.to_excel(writer, sheet_name='Sheet 1', index=False)
        
        # Formata a planilha
        worksheet = writer.sheets['Sheet 1']
        
        # Define largura das colunas
        worksheet.column_dimensions['A'].width = 12  # DATA
        worksheet.column_dimensions['B'].width = 18  # DOCUMENTO
        worksheet.column_dimensions['C'].width = 60  # HISTÓRICO
        worksheet.column_dimensions['D'].width = 14  # VALOR
        
        # Aplica formato de data e número
        from openpyxl.styles import numbers
        
        for row in range(2, len(df_padrao) + 2):
            # Data
            worksheet[f'A{row}'].number_format = 'DD/MM/YYYY'
            # Valor
            worksheet[f'D{row}'].number_format = '#,##0.00'
    
    output.seek(0)
    return output


def detect_if_needs_standardization(file_content):
    """
    Detecta se um arquivo precisa de padronização ou já está no formato correto
    
    Returns:
        bool: True se precisa padronizar, False se já está correto
    """
    try:
        df = pd.read_excel(file_content, header=None)
        
        # Verifica se a primeira linha tem o cabeçalho esperado
        first_row = df.iloc[0].tolist()
        first_row_str = [str(x).upper().strip() for x in first_row if pd.notna(x)]
        
        # Se primeira linha for DATA, DOCUMENTO, HISTÓRICO, VALOR -> já está padronizado
        if (len(first_row_str) == 4 and 
            'DATA' in first_row_str[0] and 
            'DOCUMENTO' in first_row_str[1] and 
            'HIST' in first_row_str[2] and 
            'VALOR' in first_row_str[3]):
            
            # Verifica se os valores são números (não têm C/D)
            if len(df) > 1:
                valor_sample = str(df.iloc[1, 3])
                if not (valor_sample.endswith('C') or valor_sample.endswith('D')):
                    return False  # Já está padronizado
        
        return True  # Precisa padronizar
    
    except:
        return True  # Em caso de erro, assume que precisa padronizar
