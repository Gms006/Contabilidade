# -*- coding: utf-8 -*-
"""
Conciliador de extratos bancários para Tradição Comércio e Serviços.
VERSÃO CORRIGIDA - Gera lançamentos em linha única (Débito + Crédito na mesma linha)
"""

from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import re

from .utils_tradicao import (
    normalizar_texto,
    fmt_data,
    fmt_valor,
    parse_valor,
)


# ==========================================================================
# CONSTANTES
# ==========================================================================

CONTA_SICOOB = 543
CONTA_BB = 495
CONTA_CAIXA = 5


# ==========================================================================
# FUNÇÕES AUXILIARES
# ==========================================================================

def _normalizar(texto: str) -> str:
    """Normaliza texto para comparação."""
    if pd.isna(texto):
        return ""
    texto = str(texto).upper().strip()
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def _criar_complemento(nf: Any, pagamento: str) -> str:
    """Cria complemento no formato 'NF PAGAMENTO'."""
    nf_str = ""
    if pd.notna(nf) and str(nf).strip():
        nf_str = str(nf).split('.')[0] if '.' in str(nf) else str(nf)
    
    pag_str = str(pagamento).strip() if pd.notna(pagamento) else ""
    
    if nf_str and pag_str:
        return f"{nf_str} {pag_str}"[:50]
    elif pag_str:
        return pag_str[:50]
    elif nf_str:
        return nf_str[:50]
    return ""


def _buscar_conta_financeiro(pagamento: str, df_financeiro: pd.DataFrame) -> int:
    """Busca conta contábil na aba FINANCEIRO pelo nome do pagamento."""
    if df_financeiro.empty or not pagamento:
        return 0
    
    pag_norm = _normalizar(pagamento)
    
    # Busca exata - nome da conta contido no pagamento
    for _, row in df_financeiro.iterrows():
        conta_nome = _normalizar(row.get('CONTAS', ''))
        if conta_nome and conta_nome in pag_norm:
            conta = row.get('CONTA_CONTABIL', 0)
            if pd.notna(conta) and int(conta) > 0:
                return int(conta)
    
    # Busca reversa - pagamento contido no nome da conta
    for _, row in df_financeiro.iterrows():
        conta_nome = _normalizar(row.get('CONTAS', ''))
        if conta_nome and pag_norm in conta_nome:
            conta = row.get('CONTA_CONTABIL', 0)
            if pd.notna(conta) and int(conta) > 0:
                return int(conta)
    
    # Busca parcial por palavras
    for _, row in df_financeiro.iterrows():
        conta_nome = _normalizar(row.get('CONTAS', ''))
        if conta_nome:
            palavras = conta_nome.split()
            for palavra in palavras:
                if len(palavra) >= 4 and palavra in pag_norm:
                    conta = row.get('CONTA_CONTABIL', 0)
                    if pd.notna(conta) and int(conta) > 0:
                        return int(conta)
    
    return 0


def _buscar_conta_banco(historico: str, df_banco: pd.DataFrame, tipo: str = 'SAIDA') -> Tuple[int, int]:
    """
    Busca conta contábil e código de histórico na aba do banco.
    Retorna (conta_contabil, cod_historico)
    
    O DataFrame carregado por utils_tradicao tem colunas:
    - HISTORICO (ou HISTORICO_NORM)
    - CONTA_CONTABIL
    - COD_HISTORICO
    """
    if df_banco.empty or not historico:
        return 0, 34 if tipo == 'SAIDA' else 2  # padrão
    
    hist_norm = _normalizar(historico)
    default_cod = 34 if tipo == 'SAIDA' else 2
    
    # Colunas padronizadas pelo utils_tradicao
    col_desc = 'HISTORICO'
    col_conta = 'CONTA_CONTABIL'
    col_hist = 'COD_HISTORICO'
    
    # Busca exata - descrição do banco contida no histórico do extrato
    for _, row in df_banco.iterrows():
        desc = _normalizar(row.get(col_desc, ''))
        if desc and desc in hist_norm:
            conta = row.get(col_conta, 0)
            cod_hist = row.get(col_hist, default_cod)
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                return int(conta), cod_hist
    
    # Busca reversa - histórico contido na descrição do banco
    for _, row in df_banco.iterrows():
        desc = _normalizar(row.get(col_desc, ''))
        if desc and hist_norm in desc:
            conta = row.get(col_conta, 0)
            cod_hist = row.get(col_hist, default_cod)
            if pd.notna(conta) and int(conta) > 0:
                cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                return int(conta), cod_hist
    
    # Busca parcial por palavras-chave (mínimo 4 caracteres)
    for _, row in df_banco.iterrows():
        desc = _normalizar(row.get(col_desc, ''))
        if desc:
            palavras = [p for p in desc.split() if len(p) >= 4]
            for palavra in palavras:
                if palavra in hist_norm:
                    conta = row.get(col_conta, 0)
                    cod_hist = row.get(col_hist, default_cod)
                    if pd.notna(conta) and int(conta) > 0:
                        cod_hist = int(cod_hist) if pd.notna(cod_hist) else default_cod
                        return int(conta), cod_hist
    
    return 0, default_cod


def _identificar_tipo_movimento(historico: str, credito: float, debito: float) -> str:
    """Identifica se é entrada, saída ou tarifa."""
    hist_norm = _normalizar(historico)
    
    # Tarifas/Taxas
    palavras_tarifa = ['TARIFA', 'TAXA', 'DEB PACOTE', 'IOF', 'DEB.IOF', 'SEGURO', 'TAR PROCESSAMENTO']
    if any(p in hist_norm for p in palavras_tarifa):
        return 'TARIFA'
    
    # Entrada (crédito no extrato)
    if credito > 0 and debito == 0:
        return 'ENTRADA'
    
    # Saída (débito no extrato)
    if debito > 0:
        return 'SAIDA'
    
    return 'OUTRO'


def _encontrar_na_movimentacao(data_ext, valor_ext: float, df_mov: pd.DataFrame) -> Optional[pd.Series]:
    """Encontra lançamento correspondente na planilha de movimentação."""
    if df_mov.empty:
        return None
    
    try:
        if hasattr(data_ext, 'date'):
            data_busca = data_ext.date()
        else:
            data_busca = pd.to_datetime(data_ext, dayfirst=True).date()
    except:
        return None
    
    for idx, row in df_mov.iterrows():
        data_mov = row.get('DATA')
        if pd.isna(data_mov):
            continue
        
        try:
            if hasattr(data_mov, 'date'):
                data_mov_date = data_mov.date()
            else:
                data_mov_date = pd.to_datetime(data_mov, dayfirst=True).date()
        except:
            continue
        
        valor_mov = float(row.get('VALOR', 0) or 0)
        
        if data_mov_date == data_busca and abs(valor_mov - valor_ext) < 0.02:
            return row
    
    return None


# ==========================================================================
# FUNÇÃO PRINCIPAL DE CONCILIAÇÃO
# ==========================================================================

def conciliar_tradicao(
    df_extrato_sicoob: Optional[pd.DataFrame],
    df_extrato_bb: Optional[pd.DataFrame],
    movimentacao: Dict[str, pd.DataFrame],
    contas: Dict[str, pd.DataFrame],
) -> Tuple[pd.DataFrame, List[dict]]:
    """
    Realiza a conciliação dos extratos bancários com a planilha de movimentação.
    GERA LANÇAMENTOS EM LINHA ÚNICA (Débito e Crédito na mesma linha)
    """
    resultado: List[dict] = []
    nao_encontrados: List[dict] = []
    
    # Obter DataFrames de contas
    df_financeiro = contas.get('financeiro', pd.DataFrame())
    df_sicoob_saidas = contas.get('sicoob_saidas', pd.DataFrame())
    df_sicoob_entradas = contas.get('sicoob_entradas', pd.DataFrame())
    df_bb_saidas = contas.get('bb_saidas', pd.DataFrame())
    df_bb_entradas = contas.get('bb_entradas', pd.DataFrame())
    
    # Obter movimentação
    df_mov_sicoob = movimentacao.get('pag_sicoob', pd.DataFrame())
    df_mov_bb = movimentacao.get('pag_bb', pd.DataFrame())
    
    # ==========================================================================
    # 1) PROCESSAR EXTRATO SICOOB
    # ==========================================================================
    if df_extrato_sicoob is not None and not df_extrato_sicoob.empty:
        for _, ext in df_extrato_sicoob.iterrows():
            data = ext.get('Data')
            historico = str(ext.get('Historico', ''))
            credito = float(ext.get('Credito', 0) or 0)
            debito = float(ext.get('Debito', 0) or 0)
            valor = debito if debito > 0 else credito
            
            if valor == 0:
                continue
            
            # Converter data
            try:
                if isinstance(data, str):
                    data_fmt = data
                else:
                    data_fmt = fmt_data(data)
            except:
                data_fmt = str(data)
            
            tipo = _identificar_tipo_movimento(historico, credito, debito)
            
            # ------------------------------------------------------------------
            # TARIFAS/TAXAS - Saída do banco
            # ------------------------------------------------------------------
            if tipo == 'TARIFA':
                conta, cod_hist = _buscar_conta_banco(historico, df_sicoob_saidas, 'SAIDA')
                
                if conta == 0:
                    # Tentar buscar no financeiro
                    conta = _buscar_conta_financeiro(historico, df_financeiro)
                    cod_hist = 11  # Padrão para tarifas
                
                if conta == 0:
                    nao_encontrados.append({
                        'Data': data_fmt,
                        'Banco': 'SICOOB',
                        'Movimento': 'SAIDA',
                        'Historico': historico,
                        'Valor': valor,
                        'Tipo': 'Tarifa não classificada'
                    })
                    continue
                
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': conta,
                    'Cod Conta Credito': CONTA_SICOOB,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': historico[:50],
                    'Inicia Lote': 1
                })
            
            # ------------------------------------------------------------------
            # ENTRADAS - Crédito no banco, Débito na conta origem
            # ------------------------------------------------------------------
            elif tipo == 'ENTRADA':
                conta, cod_hist = _buscar_conta_banco(historico, df_sicoob_entradas, 'ENTRADA')
                
                if conta == 0:
                    # Tentar buscar no financeiro
                    conta = _buscar_conta_financeiro(historico, df_financeiro)
                    cod_hist = 2  # Recebimento
                
                if conta == 0:
                    nao_encontrados.append({
                        'Data': data_fmt,
                        'Banco': 'SICOOB',
                        'Movimento': 'ENTRADA',
                        'Historico': historico,
                        'Valor': valor,
                        'Tipo': 'Entrada não classificada'
                    })
                    continue
                
                # Entrada: Débito banco, Crédito conta cliente
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': CONTA_SICOOB,
                    'Cod Conta Credito': conta,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': historico[:50],
                    'Inicia Lote': 1
                })
            
            # ------------------------------------------------------------------
            # SAÍDAS - Débito na conta fornecedor, Crédito no banco
            # ------------------------------------------------------------------
            elif tipo == 'SAIDA':
                # Buscar na movimentação para pegar nome do fornecedor e NF
                match = _encontrar_na_movimentacao(data, valor, df_mov_sicoob)
                
                if match is not None:
                    pagamento = match.get('PAGAMENTO', '')
                    nf = match.get('NF', '')
                    
                    # Buscar conta no financeiro pelo nome do pagamento
                    conta = _buscar_conta_financeiro(pagamento, df_financeiro)
                    
                    if conta == 0:
                        # Tentar buscar no banco
                        conta, _ = _buscar_conta_banco(historico, df_sicoob_saidas, 'SAIDA')
                    
                    if conta == 0:
                        nao_encontrados.append({
                            'Data': data_fmt,
                            'Banco': 'SICOOB',
                            'Movimento': 'SAIDA',
                            'Historico': historico,
                            'Pagamento': pagamento,
                            'Valor': valor,
                            'Tipo': 'Conta não encontrada'
                        })
                        continue
                    
                    complemento = _criar_complemento(nf, pagamento)
                    cod_hist = 34  # Pagamento via banco
                    
                else:
                    # Não encontrou na movimentação, buscar no banco
                    conta, cod_hist = _buscar_conta_banco(historico, df_sicoob_saidas, 'SAIDA')
                    
                    if conta == 0:
                        conta = _buscar_conta_financeiro(historico, df_financeiro)
                        cod_hist = 34
                    
                    if conta == 0:
                        nao_encontrados.append({
                            'Data': data_fmt,
                            'Banco': 'SICOOB',
                            'Movimento': 'SAIDA',
                            'Historico': historico,
                            'Valor': valor,
                            'Tipo': 'Lançamento não encontrado na movimentação'
                        })
                        continue
                    
                    complemento = historico[:50]
                
                # Saída: Débito fornecedor, Crédito banco
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': conta,
                    'Cod Conta Credito': CONTA_SICOOB,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': complemento,
                    'Inicia Lote': 1
                })
    
    # ==========================================================================
    # 2) PROCESSAR EXTRATO BANCO DO BRASIL
    # ==========================================================================
    if df_extrato_bb is not None and not df_extrato_bb.empty:
        for _, ext in df_extrato_bb.iterrows():
            data = ext.get('Data')
            historico = str(ext.get('Historico', ''))
            credito = float(ext.get('Credito', 0) or 0)
            debito = float(ext.get('Debito', 0) or 0)
            valor = debito if debito > 0 else credito
            
            if valor == 0 or pd.isna(data):
                continue
            
            try:
                if isinstance(data, str):
                    data_fmt = data
                else:
                    data_fmt = fmt_data(data)
            except:
                data_fmt = str(data)
            
            tipo = _identificar_tipo_movimento(historico, credito, debito)
            
            # ------------------------------------------------------------------
            # TARIFAS/TAXAS
            # ------------------------------------------------------------------
            if tipo == 'TARIFA':
                conta, cod_hist = _buscar_conta_banco(historico, df_bb_saidas, 'SAIDA')
                
                if conta == 0:
                    conta = _buscar_conta_financeiro(historico, df_financeiro)
                    cod_hist = 11
                
                if conta == 0:
                    nao_encontrados.append({
                        'Data': data_fmt,
                        'Banco': 'BB',
                        'Movimento': 'SAIDA',
                        'Historico': historico,
                        'Valor': valor,
                        'Tipo': 'Tarifa não classificada'
                    })
                    continue
                
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': conta,
                    'Cod Conta Credito': CONTA_BB,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': historico[:50],
                    'Inicia Lote': 1
                })
            
            # ------------------------------------------------------------------
            # ENTRADAS
            # ------------------------------------------------------------------
            elif tipo == 'ENTRADA':
                conta, cod_hist = _buscar_conta_banco(historico, df_bb_entradas, 'ENTRADA')
                
                if conta == 0:
                    conta = _buscar_conta_financeiro(historico, df_financeiro)
                    cod_hist = 2
                
                if conta == 0:
                    nao_encontrados.append({
                        'Data': data_fmt,
                        'Banco': 'BB',
                        'Movimento': 'ENTRADA',
                        'Historico': historico,
                        'Valor': valor,
                        'Tipo': 'Entrada não classificada'
                    })
                    continue
                
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': CONTA_BB,
                    'Cod Conta Credito': conta,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': historico[:50],
                    'Inicia Lote': 1
                })
            
            # ------------------------------------------------------------------
            # SAÍDAS
            # ------------------------------------------------------------------
            elif tipo == 'SAIDA':
                match = _encontrar_na_movimentacao(data, valor, df_mov_bb)
                
                if match is not None:
                    pagamento = match.get('PAGAMENTO', '')
                    nf = match.get('NF', '')
                    
                    conta = _buscar_conta_financeiro(pagamento, df_financeiro)
                    
                    if conta == 0:
                        conta, _ = _buscar_conta_banco(historico, df_bb_saidas, 'SAIDA')
                    
                    if conta == 0:
                        nao_encontrados.append({
                            'Data': data_fmt,
                            'Banco': 'BB',
                            'Movimento': 'SAIDA',
                            'Historico': historico,
                            'Pagamento': pagamento,
                            'Valor': valor,
                            'Tipo': 'Conta não encontrada'
                        })
                        continue
                    
                    complemento = _criar_complemento(nf, pagamento)
                    cod_hist = 34
                    
                else:
                    conta, cod_hist = _buscar_conta_banco(historico, df_bb_saidas, 'SAIDA')
                    
                    if conta == 0:
                        conta = _buscar_conta_financeiro(historico, df_financeiro)
                        cod_hist = 34
                    
                    if conta == 0:
                        nao_encontrados.append({
                            'Data': data_fmt,
                            'Banco': 'BB',
                            'Movimento': 'SAIDA',
                            'Historico': historico,
                            'Valor': valor,
                            'Tipo': 'Lançamento não encontrado na movimentação'
                        })
                        continue
                    
                    complemento = historico[:50]
                
                resultado.append({
                    'Data': data_fmt,
                    'Cod Conta Debito': conta,
                    'Cod Conta Credito': CONTA_BB,
                    'Valor': fmt_valor(valor),
                    'Cod Historico': cod_hist,
                    'Complemento Historico': complemento,
                    'Inicia Lote': 1
                })
    
    # ==========================================================================
    # 3) MONTAR DATAFRAME FINAL
    # ==========================================================================
    cols = [
        "Data",
        "Cod Conta Debito",
        "Cod Conta Credito",
        "Valor",
        "Cod Historico",
        "Complemento Historico",
        "Inicia Lote"
    ]
    
    df_resultado = pd.DataFrame(resultado)
    if not df_resultado.empty:
        # Ordenar por data
        df_resultado['_data_sort'] = pd.to_datetime(df_resultado['Data'], format='%d/%m/%Y', errors='coerce')
        df_resultado = df_resultado.sort_values('_data_sort')
        df_resultado = df_resultado.drop(columns=['_data_sort'])
        df_resultado = df_resultado[cols]
    else:
        df_resultado = pd.DataFrame(columns=cols)
    
    return df_resultado, nao_encontrados
