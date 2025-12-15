# -*- coding: utf-8 -*-
"""Utilitários para o módulo de conciliação da Tradição."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparação (maiúsculas, sem acentos extras, sem espaços extras)."""
    if pd.isna(texto) or texto is None:
        return ""
    texto = str(texto).upper().strip()
    # Remove espaços múltiplos
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def carregar_contas_contabeis(arquivo: Any) -> Dict[str, pd.DataFrame]:
    """
    Carrega a planilha de contas contábeis com as três abas.
    
    Retorna um dicionário com:
    - 'financeiro': DataFrame com colunas [CONTA_CONTABIL, CONTAS]
    - 'bb_saidas': DataFrame com saídas do BB (HISTORICO, CONTA_CONTABIL, COD_HISTORICO)
    - 'bb_entradas': DataFrame com entradas do BB (HISTORICO, CONTA_CONTABIL, COD_HISTORICO)
    - 'sicoob_saidas': DataFrame com saídas do SICOOB (HISTORICO, CONTA_CONTABIL, COD_HISTORICO)
    - 'sicoob_entradas': DataFrame com entradas do SICOOB (HISTORICO, CONTA_CONTABIL, COD_HISTORICO)
    """
    contas = {}
    
    # Carregar aba FINANCEIRO
    # Estrutura original: CONTAS | CONTA CONTABIL
    df_fin = pd.read_excel(arquivo, sheet_name='FINANCEIRO')
    df_fin.columns = ['CONTAS', 'CONTA_CONTABIL']  # Manter ordem correta!
    df_fin['CONTAS_NORM'] = df_fin['CONTAS'].apply(normalizar_texto)
    df_fin['CONTA_CONTABIL'] = pd.to_numeric(df_fin['CONTA_CONTABIL'], errors='coerce').fillna(0).astype(int)
    contas['financeiro'] = df_fin
    
    # Carregar aba BANCO DO BRASIL
    # Estrutura: SAIDAS | CONTA CONTABIL | COD Historico | ENTRADAS | CONTA CONTABIL.1 | CONTA CONTABIL2
    # Onde CONTA CONTABIL2 é o COD Historico para entradas
    df_bb = pd.read_excel(arquivo, sheet_name='BANCO DO BRASIL')
    
    # Separar saídas - incluindo COD Historico
    try:
        df_bb_saidas = df_bb[['SAIDAS', 'CONTA CONTABIL', 'COD Historico']].copy()
        df_bb_saidas.columns = ['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO']
    except:
        df_bb_saidas = df_bb[['SAIDAS', 'CONTA CONTABIL']].copy()
        df_bb_saidas.columns = ['HISTORICO', 'CONTA_CONTABIL']
        df_bb_saidas['COD_HISTORICO'] = 34  # Default para saídas
    df_bb_saidas = df_bb_saidas.dropna(subset=['HISTORICO'])
    df_bb_saidas['HISTORICO_NORM'] = df_bb_saidas['HISTORICO'].apply(normalizar_texto)
    df_bb_saidas['CONTA_CONTABIL'] = pd.to_numeric(df_bb_saidas['CONTA_CONTABIL'], errors='coerce').fillna(0).astype(int)
    df_bb_saidas['COD_HISTORICO'] = pd.to_numeric(df_bb_saidas['COD_HISTORICO'], errors='coerce').fillna(34).astype(int)
    contas['bb_saidas'] = df_bb_saidas
    
    # Separar entradas - CONTA CONTABIL2 é o COD Historico para entradas
    try:
        df_bb_entradas = df_bb[['ENTRADAS', 'CONTA CONTABIL.1', 'CONTA CONTABIL2']].copy()
        df_bb_entradas.columns = ['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO']
    except:
        try:
            df_bb_entradas = df_bb[['ENTRADAS', 'CONTA CONTABIL.1']].copy()
            df_bb_entradas.columns = ['HISTORICO', 'CONTA_CONTABIL']
            df_bb_entradas['COD_HISTORICO'] = 2  # Default para entradas
        except:
            df_bb_entradas = pd.DataFrame(columns=['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO'])
    df_bb_entradas = df_bb_entradas.dropna(subset=['HISTORICO'])
    df_bb_entradas['HISTORICO_NORM'] = df_bb_entradas['HISTORICO'].apply(normalizar_texto)
    df_bb_entradas['CONTA_CONTABIL'] = pd.to_numeric(df_bb_entradas['CONTA_CONTABIL'], errors='coerce').fillna(0).astype(int)
    df_bb_entradas['COD_HISTORICO'] = pd.to_numeric(df_bb_entradas['COD_HISTORICO'], errors='coerce').fillna(2).astype(int)
    contas['bb_entradas'] = df_bb_entradas
    
    # Carregar aba SICOOB
    # Estrutura: SAIDAS | CONTA CONTABIL | COD Historico | ENTRADAS | CONTA CONTABIL.1 | CONTA CONTABIL2
    df_sicoob = pd.read_excel(arquivo, sheet_name='SICOOB')
    
    # Separar saídas - incluindo COD Historico
    try:
        df_sicoob_saidas = df_sicoob[['SAIDAS', 'CONTA CONTABIL', 'COD Historico']].copy()
        df_sicoob_saidas.columns = ['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO']
    except:
        df_sicoob_saidas = df_sicoob[['SAIDAS', 'CONTA CONTABIL']].copy()
        df_sicoob_saidas.columns = ['HISTORICO', 'CONTA_CONTABIL']
        df_sicoob_saidas['COD_HISTORICO'] = 34  # Default para saídas
    df_sicoob_saidas = df_sicoob_saidas.dropna(subset=['HISTORICO'])
    df_sicoob_saidas['HISTORICO_NORM'] = df_sicoob_saidas['HISTORICO'].apply(normalizar_texto)
    df_sicoob_saidas['CONTA_CONTABIL'] = pd.to_numeric(df_sicoob_saidas['CONTA_CONTABIL'], errors='coerce').fillna(0).astype(int)
    df_sicoob_saidas['COD_HISTORICO'] = pd.to_numeric(df_sicoob_saidas['COD_HISTORICO'], errors='coerce').fillna(34).astype(int)
    contas['sicoob_saidas'] = df_sicoob_saidas
    
    # Separar entradas - CONTA CONTABIL2 é o COD Historico para entradas  
    try:
        df_sicoob_entradas = df_sicoob[['ENTRADAS', 'CONTA CONTABIL.1', 'CONTA CONTABIL2']].copy()
        df_sicoob_entradas.columns = ['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO']
    except:
        try:
            df_sicoob_entradas = df_sicoob[['ENTRADAS', 'CONTA CONTABIL.1']].copy()
            df_sicoob_entradas.columns = ['HISTORICO', 'CONTA_CONTABIL']
            df_sicoob_entradas['COD_HISTORICO'] = 2  # Default para entradas
        except:
            df_sicoob_entradas = pd.DataFrame(columns=['HISTORICO', 'CONTA_CONTABIL', 'COD_HISTORICO'])
    df_sicoob_entradas = df_sicoob_entradas.dropna(subset=['HISTORICO'])
    df_sicoob_entradas['HISTORICO_NORM'] = df_sicoob_entradas['HISTORICO'].apply(normalizar_texto)
    df_sicoob_entradas['CONTA_CONTABIL'] = pd.to_numeric(df_sicoob_entradas['CONTA_CONTABIL'], errors='coerce').fillna(0).astype(int)
    df_sicoob_entradas['COD_HISTORICO'] = pd.to_numeric(df_sicoob_entradas['COD_HISTORICO'], errors='coerce').fillna(2).astype(int)
    contas['sicoob_entradas'] = df_sicoob_entradas
    
    return contas


def carregar_planilha_movimentacao(arquivo: Any) -> Dict[str, pd.DataFrame]:
    """
    Carrega a planilha de movimentação com as abas PAG SICOOB, PAG BB, CAIXA EMPRESA.
    
    Retorna um dicionário com DataFrames para cada aba.
    """
    movimentacao = {}
    
    # Carregar PAG SICOOB
    try:
        df_sicoob = pd.read_excel(arquivo, sheet_name='PAG SICOOB')
        # Selecionar apenas colunas relevantes
        colunas_relevantes = ['DATA', 'PAGAMENTO', 'VALOR', 'NF', 'DATA NF', 'OBS']
        df_sicoob = df_sicoob[[c for c in colunas_relevantes if c in df_sicoob.columns]]
        df_sicoob = df_sicoob.dropna(subset=['DATA', 'PAGAMENTO', 'VALOR'], how='all')
        df_sicoob = df_sicoob[df_sicoob['DATA'].notna() & df_sicoob['VALOR'].notna()]
        df_sicoob['DATA'] = pd.to_datetime(df_sicoob['DATA'], errors='coerce')
        df_sicoob['VALOR'] = pd.to_numeric(df_sicoob['VALOR'], errors='coerce').abs()
        df_sicoob['PAGAMENTO_NORM'] = df_sicoob['PAGAMENTO'].apply(normalizar_texto)
        df_sicoob['BANCO'] = 'SICOOB'
        movimentacao['pag_sicoob'] = df_sicoob
    except Exception as e:
        print(f"Erro ao carregar PAG SICOOB: {e}")
        movimentacao['pag_sicoob'] = pd.DataFrame()
    
    # Carregar PAG BB
    try:
        df_bb = pd.read_excel(arquivo, sheet_name='PAG BB')
        colunas_relevantes = ['DATA', 'PAGAMENTO', 'VALOR', 'NF', 'DATA NF', 'OBS']
        df_bb = df_bb[[c for c in colunas_relevantes if c in df_bb.columns]]
        df_bb = df_bb.dropna(subset=['DATA', 'PAGAMENTO', 'VALOR'], how='all')
        df_bb = df_bb[df_bb['DATA'].notna() & df_bb['VALOR'].notna()]
        df_bb['DATA'] = pd.to_datetime(df_bb['DATA'], errors='coerce')
        df_bb['VALOR'] = pd.to_numeric(df_bb['VALOR'], errors='coerce').abs()
        df_bb['PAGAMENTO_NORM'] = df_bb['PAGAMENTO'].apply(normalizar_texto)
        df_bb['BANCO'] = 'BB'
        movimentacao['pag_bb'] = df_bb
    except Exception as e:
        print(f"Erro ao carregar PAG BB: {e}")
        movimentacao['pag_bb'] = pd.DataFrame()
    
    # Carregar CAIXA EMPRESA (tem duas seções: saídas e entradas)
    try:
        df_caixa = pd.read_excel(arquivo, sheet_name='CAIXA EMPRESA')
        
        # Saídas do caixa (colunas A-E)
        df_saidas = df_caixa[['DATA PG', 'PAGAMENTO', 'VALOR', 'NF', 'DATA NF']].copy()
        df_saidas.columns = ['DATA', 'PAGAMENTO', 'VALOR', 'NF', 'DATA NF']
        df_saidas = df_saidas[df_saidas['DATA'].notna() & df_saidas['VALOR'].notna()]
        df_saidas['DATA'] = pd.to_datetime(df_saidas['DATA'], errors='coerce')
        df_saidas['VALOR'] = pd.to_numeric(df_saidas['VALOR'], errors='coerce').abs()
        df_saidas['PAGAMENTO_NORM'] = df_saidas['PAGAMENTO'].apply(normalizar_texto)
        df_saidas['TIPO'] = 'SAIDA'
        
        # Entradas do caixa (colunas H-M)
        colunas_entrada = ['DATA', 'PAGAMENTO.1', 'VALOR.1', 'NF.1', 'DATA NF.1']
        if all(c in df_caixa.columns for c in colunas_entrada):
            df_entradas = df_caixa[colunas_entrada].copy()
            df_entradas.columns = ['DATA', 'PAGAMENTO', 'VALOR', 'NF', 'DATA NF']
            df_entradas = df_entradas[df_entradas['DATA'].notna() & df_entradas['VALOR'].notna()]
            df_entradas['DATA'] = pd.to_datetime(df_entradas['DATA'], errors='coerce')
            df_entradas['VALOR'] = pd.to_numeric(df_entradas['VALOR'], errors='coerce').abs()
            df_entradas['PAGAMENTO_NORM'] = df_entradas['PAGAMENTO'].apply(normalizar_texto)
            df_entradas['TIPO'] = 'ENTRADA'
        else:
            df_entradas = pd.DataFrame()
        
        movimentacao['caixa_saidas'] = df_saidas
        movimentacao['caixa_entradas'] = df_entradas
        
    except Exception as e:
        print(f"Erro ao carregar CAIXA EMPRESA: {e}")
        movimentacao['caixa_saidas'] = pd.DataFrame()
        movimentacao['caixa_entradas'] = pd.DataFrame()
    
    return movimentacao


def carregar_extrato(arquivo: Any, banco: str = 'auto') -> pd.DataFrame:
    """
    Carrega extrato bancário em formato padronizado.
    
    Args:
        arquivo: Arquivo Excel do extrato
        banco: 'BB', 'SICOOB' ou 'auto' para detecção automática
    
    Retorna DataFrame com colunas: Data, Documento, Historico, Credito, Debito, Saldo
    """
    # Ler com header na linha 4 (índice 3) - padrão dos extratos gerados
    df = pd.read_excel(arquivo, header=3)
    
    # Renomear colunas
    if len(df.columns) >= 6:
        df.columns = ['Data', 'Documento', 'Historico', 'Credito', 'Debito', 'Saldo']
    else:
        # Tentar outros formatos
        df = pd.read_excel(arquivo, header=0)
        if 'Data' not in df.columns:
            raise ValueError("Formato de extrato não reconhecido")
    
    # Remover linha de cabeçalho duplicada se existir
    df = df[df['Data'] != 'Data']
    
    # Remover linha de TOTAIS
    df = df[~df['Historico'].astype(str).str.upper().str.contains('TOTAIS', na=False)]
    
    # Converter tipos
    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    df['Credito'] = pd.to_numeric(df['Credito'], errors='coerce').fillna(0)
    df['Debito'] = pd.to_numeric(df['Debito'], errors='coerce').fillna(0)
    df['Saldo'] = pd.to_numeric(df['Saldo'], errors='coerce')
    
    # Detectar banco se auto
    if banco == 'auto':
        nome_arquivo = getattr(arquivo, 'name', str(arquivo)).upper()
        if 'BB' in nome_arquivo or 'BRASIL' in nome_arquivo:
            banco = 'BB'
        elif 'SICOOB' in nome_arquivo:
            banco = 'SICOOB'
        else:
            # Tentar detectar pelo conteúdo
            banco = 'SICOOB'  # Default
    
    df['Banco'] = banco
    
    # Remover linhas sem data
    df = df[df['Data'].notna()]
    
    return df


def buscar_conta_contabil(
    historico: str,
    pagamento: str,
    contas: Dict[str, pd.DataFrame],
    banco: str,
    tipo_movimento: str,  # 'SAIDA' ou 'ENTRADA'
    valor: float = 0
) -> Tuple[int, str]:
    """
    Busca a conta contábil para um lançamento.
    
    Ordem de busca:
    1. Se for tarifa (conta 170), preserva a classificação do banco
    2. Busca na planilha de movimentação (FINANCEIRO) pelo nome do pagamento
    3. Busca na planilha do banco específico pelo histórico
    4. Retorna 0 se não encontrar (indica que precisa cadastrar)
    
    Retorna: (conta_contabil, fonte_da_conta)
    """
    historico_norm = normalizar_texto(historico)
    pagamento_norm = normalizar_texto(pagamento)
    
    # Verificar se é tarifa - palavras-chave de tarifas
    palavras_tarifa = ['TARIFA', 'TAXA', 'DEB PACOTE', 'DEB.IOF', 'IOF', 'TAR PROCESSAMENTO', 
                       'TARIFA PACOTE', 'TARIFA DEVOL', 'TARIFA FORNEC']
    is_tarifa = any(palavra in historico_norm for palavra in palavras_tarifa)
    
    # Se for tarifa, buscar primeiro no banco
    if is_tarifa:
        if banco == 'BB':
            df_banco = contas.get('bb_saidas', pd.DataFrame())
        else:
            df_banco = contas.get('sicoob_saidas', pd.DataFrame())
        
        if not df_banco.empty:
            # Busca por correspondência parcial no histórico
            for _, row in df_banco.iterrows():
                hist_banco = str(row.get('HISTORICO_NORM', ''))
                if hist_banco and hist_banco in historico_norm:
                    conta = int(row['CONTA_CONTABIL'])
                    if conta == 170:
                        return (170, f'Tarifa - {banco}')
            
            # Se não encontrou específico, verificar se é tarifa genérica
            for _, row in df_banco.iterrows():
                hist_banco = str(row.get('HISTORICO_NORM', ''))
                for palavra in palavras_tarifa:
                    if palavra in hist_banco and palavra in historico_norm:
                        return (int(row['CONTA_CONTABIL']), f'Tarifa - {banco}')
        
        # Tarifa genérica
        return (170, 'Tarifa Padrão')
    
    # Buscar primeiro na planilha FINANCEIRO pelo nome do pagamento
    df_fin = contas.get('financeiro', pd.DataFrame())
    if not df_fin.empty and pagamento_norm:
        for _, row in df_fin.iterrows():
            conta_nome = str(row.get('CONTAS_NORM', ''))
            if conta_nome and conta_nome in pagamento_norm:
                return (int(row['CONTA_CONTABIL']), 'Financeiro')
            # Busca reversa - pagamento contém nome da conta
            if pagamento_norm and pagamento_norm in conta_nome:
                return (int(row['CONTA_CONTABIL']), 'Financeiro')
    
    # Buscar na planilha do banco pelo histórico
    if tipo_movimento == 'SAIDA':
        if banco == 'BB':
            df_banco = contas.get('bb_saidas', pd.DataFrame())
        else:
            df_banco = contas.get('sicoob_saidas', pd.DataFrame())
    else:  # ENTRADA
        if banco == 'BB':
            df_banco = contas.get('bb_entradas', pd.DataFrame())
        else:
            df_banco = contas.get('sicoob_entradas', pd.DataFrame())
    
    if not df_banco.empty:
        for _, row in df_banco.iterrows():
            hist_banco = str(row.get('HISTORICO_NORM', ''))
            if hist_banco and hist_banco in historico_norm:
                return (int(row['CONTA_CONTABIL']), f'{banco}')
    
    # Não encontrou
    return (0, 'Não encontrado')


def fmt_data(data: Any) -> str:
    """Formata data para dd/mm/aaaa."""
    if pd.isna(data):
        return ""
    return pd.to_datetime(data).strftime("%d/%m/%Y")


def fmt_valor(valor: float) -> str:
    """Formata valor como string '123,45'."""
    return f"{abs(valor):.2f}".replace(".", ",")


def parse_valor(valor: Any) -> float:
    """Converte valor para float."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip()
    if not s or s.lower() == "nan":
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def clean_nota(nota: Any) -> str:
    """Limpa e formata número da nota fiscal."""
    if pd.isna(nota) or nota is None:
        return ""
    nota_str = str(nota).strip()
    # Remove .0 de números float
    if nota_str.endswith('.0'):
        nota_str = nota_str[:-2]
    return nota_str


def criar_complemento(nota: Any, pagamento: str) -> str:
    """Cria o complemento do histórico no formato 'NF + PAGAMENTO'."""
    nota_limpa = clean_nota(nota)
    pagamento_limpo = str(pagamento).strip() if pagamento else ""
    
    if nota_limpa and pagamento_limpo:
        return f"{nota_limpa} {pagamento_limpo}"
    elif nota_limpa:
        return nota_limpa
    elif pagamento_limpo:
        return pagamento_limpo
    return ""
