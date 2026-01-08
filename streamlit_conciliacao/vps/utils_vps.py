# -*- coding: utf-8 -*-
"""
Utilitários para conciliação VPS METALÚRGICA
Funções para leitura de planilhas e normalização de dados
"""

from __future__ import annotations

import pandas as pd
import re
from typing import Dict, Tuple, Optional
from datetime import datetime
import unicodedata


# ==========================================================================
# CONSTANTES
# ==========================================================================

CONTA_SICOOB = 809
CONTA_BRADESCO = 7
CONTA_SICREDI = 808
CONTA_CAIXA = 5


# Mapeamento de bancos para contas contábeis
BANCOS_CONTAS = {
    'SICOOB': CONTA_SICOOB,
    'BRADESCO': CONTA_BRADESCO,
    'SICREDI': CONTA_SICREDI,
    'CAIXA': CONTA_CAIXA,
}


# ==========================================================================
# FUNÇÕES DE NORMALIZAÇÃO
# ==========================================================================

def normalizar_texto(texto: str) -> str:
    """Normaliza texto removendo acentos, caracteres especiais e convertendo para maiúsculas."""
    if pd.isna(texto) or not texto:
        return ""
    
    # Remove acentos
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join([c for c in texto if not unicodedata.combining(c)])
    
    # Converte para maiúsculas e remove espaços extras
    texto = texto.upper().strip()
    
    # Remove caracteres especiais, mantém apenas alfanuméricos e espaços
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto


def limpar_complemento(texto: str) -> str:
    """
    Limpa texto do complemento para exportação CSV.
    Remove acentos e caracteres especiais que causam problemas no software contábil.
    Mantém: letras (sem acento), números, espaços, hífen, barra, ponto.
    """
    if pd.isna(texto) or not texto:
        return ""
    
    texto = str(texto).strip()
    
    # Mapeamento de caracteres acentuados para sem acento
    mapa_acentos = {
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
    }
    
    # Substitui acentos
    resultado = []
    for char in texto:
        if char in mapa_acentos:
            resultado.append(mapa_acentos[char])
        elif char.isalnum() or char in ' -/.,:;()_':
            resultado.append(char)
        else:
            resultado.append(' ')
    
    texto = ''.join(resultado)
    
    # Remove espaços extras e quebras de linha
    texto = re.sub(r'[\n\r]+', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    
    return texto[:60]  # Limita tamanho do complemento


def parse_valor(valor_str) -> float:
    """
    Converte valor string no formato brasileiro para float.
    Aceita formatos:
    - "1.234,56" (padrão BR)
    - "1.234,56C" (crédito)
    - "1.234,56D" (débito)
    - "1234.56" (padrão US)
    """
    if pd.isna(valor_str):
        return 0.0
    
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    valor_str = str(valor_str).strip()
    
    # Remove espaços e caracteres invisíveis
    valor_str = valor_str.replace('\xa0', '').replace(' ', '')
    
    # Verifica se há indicador C/D no final
    is_credito = valor_str.endswith('C')
    is_debito = valor_str.endswith('D')
    
    if is_credito or is_debito:
        valor_str = valor_str[:-1].strip()
    
    # Detecta formato brasileiro (vírgula como decimal)
    if ',' in valor_str:
        # Remove pontos de milhar e substitui vírgula por ponto
        valor_str = valor_str.replace('.', '').replace(',', '.')
    
    try:
        valor = float(valor_str)
        # Se for débito, retorna negativo
        if is_debito:
            valor = -abs(valor)
        # Se for crédito, garante positivo
        elif is_credito:
            valor = abs(valor)
        return valor
    except (ValueError, TypeError):
        return 0.0


def parse_valor_extrato(valor_str) -> Tuple[float, str]:
    """
    Converte valor do extrato e identifica o tipo (CREDITO/DEBITO).
    Retorna: (valor_float, tipo)
    """
    if pd.isna(valor_str):
        return 0.0, 'OUTRO'
    
    if isinstance(valor_str, (int, float)):
        valor = float(valor_str)
        return abs(valor), 'CREDITO' if valor >= 0 else 'DEBITO'
    
    valor_str = str(valor_str).strip()
    
    # Verifica se há indicador C/D no final
    is_credito = valor_str.endswith('C')
    is_debito = valor_str.endswith('D')
    
    if is_credito:
        valor = abs(parse_valor(valor_str))
        return valor, 'CREDITO'
    elif is_debito:
        valor = abs(parse_valor(valor_str))
        return valor, 'DEBITO'
    else:
        # Se não tem indicador, usa o sinal do número
        valor = parse_valor(valor_str)
        if valor < 0:
            return abs(valor), 'DEBITO'
        else:
            return valor, 'CREDITO'


def fmt_data(data) -> str:
    """Formata data no padrão DD/MM/AAAA. Corrige anos inválidos (ex: 2027 -> 2025)."""
    if pd.isna(data):
        return ""
    
    try:
        if isinstance(data, str):
            # Tenta parse de diferentes formatos
            dt = pd.to_datetime(data, dayfirst=True)
        else:
            dt = pd.to_datetime(data)
        
        # Corrige anos fora do intervalo esperado (provavelmente erro de digitação)
        ano = dt.year
        if ano > 2025:
            # Corrige para 2025 (provavelmente erro: 2027 -> 2025)
            dt = dt.replace(year=2025)
        elif ano < 2020:
            # Data muito antiga, mantém original mas pode ser erro
            pass
        
        return dt.strftime("%d/%m/%Y")
    except:
        return str(data)


def fmt_valor(valor: float) -> str:
    """Formata valor no padrão brasileiro sem separador de milhar (1234,56)."""
    if pd.isna(valor):
        return "0,00"
    
    # Formata com 2 casas decimais e substitui ponto por vírgula
    # SEM separador de milhar para compatibilidade com software contábil
    valor_str = f"{abs(float(valor)):.2f}"
    return valor_str.replace('.', ',')


# ==========================================================================
# FUNÇÕES DE LEITURA DE PLANILHAS
# ==========================================================================

def carregar_contas_contabeis(arquivo) -> Dict[str, pd.DataFrame]:
    """
    Carrega a planilha de contas contábeis.
    Retorna dicionário com as abas: RELATORIO FINANCEIRO, SICOOB, BRADESCO, SICREDI
    
    Estrutura das abas:
    - RELATORIO FINANCEIRO: LANCAMENTOS (fornecedor) | CONTAS (conta contábil) | Historico (não usado)
    - SICOOB/BRADESCO/SICREDI: LANCAMENTOS (histórico movimento) | CONTAS (conta contábil) | Historico (código histórico)
    """
    try:
        # Lê todas as abas
        excel_file = pd.ExcelFile(arquivo)
        contas = {}
        
        # Aba RELATORIO FINANCEIRO
        if 'RELATORIO FINANCEIRO' in excel_file.sheet_names:
            df = pd.read_excel(arquivo, sheet_name='RELATORIO FINANCEIRO')
            # Guarda nomes originais para mapeamento
            colunas_originais = df.columns.tolist()
            # Padroniza nomes de colunas
            df.columns = df.columns.str.upper().str.strip()
            # Renomeia para padrão esperado
            df = df.rename(columns={
                'LANCAMENTOS': 'FORNECEDOR',
                'CONTAS': 'CONTA_CONTABIL',
            })
            # Não usa COD_HISTORICO da planilha - será definido pelo tipo de operação
            contas['RELATORIO_FINANCEIRO'] = df
        
        # Abas de bancos (SICOOB, BRADESCO, SICREDI)
        for banco in ['SICOOB', 'BRADESCO', 'SICREDI']:
            if banco in excel_file.sheet_names:
                df = pd.read_excel(arquivo, sheet_name=banco)
                # Guarda nomes originais
                colunas_originais = df.columns.tolist()
                
                # Cria novo DataFrame com colunas padronizadas
                df_novo = pd.DataFrame()
                
                # Mapeia colunas baseado na posição e nome original
                for i, col in enumerate(colunas_originais):
                    col_upper = str(col).upper().strip()
                    if col_upper == 'LANCAMENTOS':
                        df_novo['HISTORICO'] = df[col]  # Descrição do movimento bancário
                    elif col_upper == 'CONTAS':
                        df_novo['CONTA_CONTABIL'] = df[col]
                    elif col_upper == 'HISTORICO':
                        df_novo['COD_HISTORICO'] = df[col]  # Código numérico do histórico
                    else:
                        df_novo[col_upper] = df[col]
                
                contas[banco] = df_novo
        
        return contas
    
    except Exception as e:
        raise Exception(f"Erro ao carregar contas contábeis: {str(e)}")


def carregar_lancamentos(arquivo) -> pd.DataFrame:
    """
    Carrega a planilha de lançamentos (pagamentos da empresa).
    """
    try:
        df = pd.read_excel(arquivo)
        
        # Padroniza nomes de colunas
        df.columns = df.columns.str.upper().str.strip()
        df.columns = df.columns.str.replace('\n', ' ').str.replace('  ', ' ')
        
        # Renomeia colunas para padrão esperado
        rename_map = {
            'FORMA DE PAGAMENTO': 'FORMA_PAGAMENTO',
            'DATA DE PAGAMENTO': 'DATA_PAGAMENTO',
            'JUROS E MULTAS': 'JUROS_MULTAS',
            'VALOR R$': 'VALOR_ORIGINAL',
            'VALOR PAGO': 'VALOR_PAGO',
            'VENCIMENTO': 'DATA_VENCIMENTO',
            'DESCONTOS OBTIDOS': 'DESCONTOS_OBTIDOS',
            'DESCONTO': 'DESCONTOS_OBTIDOS'
        }
        
        for old, new in rename_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # Remove espaços extras em nomes de colunas
        df.columns = [c.strip() for c in df.columns]
        
        # Converte datas
        if 'DATA_PAGAMENTO' in df.columns:
            df['DATA_PAGAMENTO'] = pd.to_datetime(df['DATA_PAGAMENTO'], errors='coerce')
        
        if 'DATA_VENCIMENTO' in df.columns:
            df['DATA_VENCIMENTO'] = pd.to_datetime(df['DATA_VENCIMENTO'], errors='coerce')
        
        # Converte valores
        for col in ['VALOR_ORIGINAL', 'JUROS_MULTAS', 'VALOR_PAGO', 'DESCONTOS_OBTIDOS']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: parse_valor(x) if pd.notna(x) else 0.0)
        
        # Normaliza nomes de fornecedores para matching
        if 'FORNECEDOR' in df.columns:
            df['FORNECEDOR_NORM'] = df['FORNECEDOR'].apply(normalizar_texto)
        
        # Normaliza banco/pagamento
        if 'PAGAMENTO' in df.columns:
            df['BANCO'] = df['PAGAMENTO'].str.upper().str.strip()
        
        return df
    
    except Exception as e:
        raise Exception(f"Erro ao carregar lançamentos: {str(e)}")


def carregar_extratos(arquivo) -> pd.DataFrame:
    """
    Carrega a planilha de extratos bancários consolidados.
    Carrega TODAS as abas (SICOOB, BRADESCO, SICREDI) e consolida em um único DataFrame.
    """
    try:
        # Carrega todas as abas do arquivo de extratos
        xls = pd.ExcelFile(arquivo)
        
        dfs = []
        for aba in xls.sheet_names:
            df_aba = pd.read_excel(xls, sheet_name=aba)
            
            # Padroniza nomes de colunas
            df_aba.columns = df_aba.columns.str.upper().str.strip()
            
            # Adiciona coluna para identificar o banco de origem
            df_aba['BANCO_ORIGEM'] = aba.upper()
            
            dfs.append(df_aba)
        
        # Concatena todos os DataFrames
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
        else:
            df = pd.DataFrame()
        
        # Renomeia colunas para padrão esperado
        rename_map = {
            'HISTORICO': 'HISTORICO',
            'DATA': 'DATA',
            'VALOR': 'VALOR'
        }
        
        for old, new in rename_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        # Converte datas
        if 'DATA' in df.columns:
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
        
        # Processa valores (pode estar com C/D ou sinal)
        if 'VALOR' in df.columns:
            df[['VALOR_ABS', 'TIPO_MOVIMENTO']] = df['VALOR'].apply(
                lambda x: pd.Series(parse_valor_extrato(x))
            )
        
        # Normaliza histórico para matching
        if 'HISTORICO' in df.columns:
            df['HISTORICO_NORM'] = df['HISTORICO'].apply(normalizar_texto)
        
        return df
    
    except Exception as e:
        raise Exception(f"Erro ao carregar extratos: {str(e)}")


def buscar_conta_fornecedor(fornecedor: str, df_contas: pd.DataFrame) -> Tuple[int, int]:
    """
    Busca conta contábil e código de histórico para um fornecedor.
    Retorna: (conta_contabil, cod_historico)
    """
    if df_contas is None or df_contas.empty or not fornecedor:
        return 0, 34  # Padrão: histórico 34 para pagamentos
    
    fornecedor_norm = normalizar_texto(fornecedor)
    
    # Busca exata - fornecedor contido no cadastro
    for _, row in df_contas.iterrows():
        conta_nome = normalizar_texto(str(row.get('FORNECEDOR', '')))
        if conta_nome and conta_nome in fornecedor_norm:
            conta = row.get('CONTA_CONTABIL', 0)
            cod_hist = row.get('COD_HISTORICO', 34)
            
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else 34
                return int(conta), cod_hist
    
    # Busca reversa - cadastro contido no fornecedor
    for _, row in df_contas.iterrows():
        conta_nome = normalizar_texto(str(row.get('FORNECEDOR', '')))
        if conta_nome and fornecedor_norm in conta_nome:
            conta = row.get('CONTA_CONTABIL', 0)
            cod_hist = row.get('COD_HISTORICO', 34)
            
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else 34
                return int(conta), cod_hist
    
    # Busca parcial por palavras (mínimo 4 caracteres)
    for _, row in df_contas.iterrows():
        conta_nome = normalizar_texto(str(row.get('FORNECEDOR', '')))
        if conta_nome:
            palavras = [p for p in conta_nome.split() if len(p) >= 4]
            for palavra in palavras:
                if palavra in fornecedor_norm:
                    conta = row.get('CONTA_CONTABIL', 0)
                    cod_hist = row.get('COD_HISTORICO', 34)
                    
                    if pd.notna(conta) and int(conta) > 0:
                        cod_hist = int(cod_hist) if pd.notna(cod_hist) else 34
                        return int(conta), cod_hist
    
    return 0, 34


def buscar_conta_banco(historico: str, df_banco: pd.DataFrame, tipo: str = 'DEBITO') -> Tuple[int, int]:
    """
    Busca conta contábil e código de histórico na planilha de um banco específico.
    Retorna: (conta_contabil, cod_historico)
    """
    if df_banco is None or df_banco.empty or not historico:
        # Padrões: 34 para saídas, 2 para entradas
        return 0, 34 if tipo == 'DEBITO' else 2
    
    historico_norm = normalizar_texto(historico)
    default_cod = 34 if tipo == 'DEBITO' else 2
    
    # Busca exata - histórico do cadastro contido no histórico do extrato
    for _, row in df_banco.iterrows():
        hist_cadastro = normalizar_texto(str(row.get('HISTORICO', '')))
        if hist_cadastro and hist_cadastro in historico_norm:
            conta = row.get('CONTA_CONTABIL', 0)
            cod_hist = row.get('COD_HISTORICO', default_cod)
            
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                return int(conta), cod_hist
    
    # Busca reversa - histórico do extrato contido no cadastro
    for _, row in df_banco.iterrows():
        hist_cadastro = normalizar_texto(str(row.get('HISTORICO', '')))
        if hist_cadastro and historico_norm in hist_cadastro:
            conta = row.get('CONTA_CONTABIL', 0)
            cod_hist = row.get('COD_HISTORICO', default_cod)
            
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                return int(conta), cod_hist
    
    # Busca parcial por palavras (mínimo 4 caracteres)
    for _, row in df_banco.iterrows():
        hist_cadastro = normalizar_texto(str(row.get('HISTORICO', '')))
        if hist_cadastro:
            palavras = [p for p in hist_cadastro.split() if len(p) >= 4]
            for palavra in palavras:
                if palavra in historico_norm:
                    conta = row.get('CONTA_CONTABIL', 0)
                    cod_hist = row.get('COD_HISTORICO', default_cod)
                    
                    if pd.notna(conta) and int(conta) > 0:
                        cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                        return int(conta), cod_hist
    
    return 0, default_cod
