# -*- coding: utf-8 -*-
"""
Conciliador de extratos bancários para VPS METALÚRGICA
Realiza conciliação bancária e contábil entre lançamentos e extratos
"""

from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re

from .utils_vps import (
    normalizar_texto,
    limpar_complemento,
    fmt_data,
    fmt_valor,
    parse_valor,
    buscar_conta_fornecedor,
    buscar_conta_banco,
    BANCOS_CONTAS,
    CONTA_CAIXA,
    CONTA_SICOOB,
    CONTA_BRADESCO,
    CONTA_SICREDI,
)


# ==========================================================================
# FUNÇÕES DE CONCILIAÇÃO
# ==========================================================================

def _criar_complemento(nf: Any, fornecedor: str) -> str:
    """Cria complemento no formato 'NF FORNECEDOR' sem caracteres especiais."""
    nf_str = ""
    if pd.notna(nf) and str(nf).strip():
        nf_str = str(nf).split('.')[0] if '.' in str(nf) else str(nf)
    
    fornecedor_str = str(fornecedor).strip() if pd.notna(fornecedor) else ""
    
    if nf_str and fornecedor_str:
        complemento = f"{nf_str} {fornecedor_str}"
    elif fornecedor_str:
        complemento = fornecedor_str
    elif nf_str:
        complemento = nf_str
    else:
        return ""
    
    # Limpa caracteres especiais e acentos
    return limpar_complemento(complemento)


def _identificar_banco(pagamento: str) -> str:
    """Identifica qual banco baseado no campo PAGAMENTO."""
    if pd.isna(pagamento):
        return 'OUTRO'
    
    pagamento_upper = str(pagamento).upper().strip()
    
    for banco in ['SICOOB', 'BRADESCO', 'SICREDI', 'CAIXA']:
        if banco in pagamento_upper:
            return banco
    
    return 'OUTRO'


def _encontrar_no_extrato(data_lanc, valor_lanc: float, historico_busca: str, 
                         df_extrato: pd.DataFrame, tipo: str = 'DEBITO',
                         tolerancia_dias: int = 3) -> Optional[pd.Series]:
    """
    Encontra movimentação correspondente no extrato bancário.
    """
    if df_extrato.empty:
        return None
    
    try:
        if hasattr(data_lanc, 'date'):
            data_busca = data_lanc.date()
        else:
            data_busca = pd.to_datetime(data_lanc, dayfirst=True).date()
    except:
        return None
    
    historico_norm = normalizar_texto(historico_busca)
    
    # Busca por valor e data (com tolerância)
    for idx, row in df_extrato.iterrows():
        # Já foi conciliado?
        if row.get('CONCILIADO', False):
            continue
        
        # Verifica tipo de movimento
        if row.get('TIPO_MOVIMENTO') != tipo:
            continue
        
        # Verifica valor
        valor_ext = row.get('VALOR_ABS', 0)
        if abs(valor_ext - valor_lanc) > 0.01:  # Tolerância de 1 centavo
            continue
        
        # Verifica data
        data_ext = row.get('DATA')
        if pd.isna(data_ext):
            continue
        
        try:
            if hasattr(data_ext, 'date'):
                data_ext_date = data_ext.date()
            else:
                data_ext_date = pd.to_datetime(data_ext, dayfirst=True).date()
        except:
            continue
        
        # Calcula diferença de dias
        diff_dias = abs((data_ext_date - data_busca).days)
        if diff_dias > tolerancia_dias:
            continue
        
        # Verifica se o histórico é compatível (opcional, melhora precisão)
        historico_ext = normalizar_texto(str(row.get('HISTORICO', '')))
        
        # Se encontrou match, retorna
        return row
    
    return None


def _processar_lancamento(row_lanc: pd.Series, df_contas_financeiro: pd.DataFrame,
                         df_extrato: pd.DataFrame, contas_bancos: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Processa um lançamento da planilha de pagamentos.
    Retorna lista de lançamentos contábeis (pode ser lançamento simples ou composto).
    """
    lancamentos = []
    
    # Extrai dados do lançamento
    fornecedor = row_lanc.get('FORNECEDOR', '')
    nf = row_lanc.get('NF', '')
    data_pag = row_lanc.get('DATA_PAGAMENTO')
    valor_original = row_lanc.get('VALOR_ORIGINAL', 0)
    juros_multas = row_lanc.get('JUROS_MULTAS', 0)
    descontos = row_lanc.get('DESCONTOS_OBTIDOS', 0)
    valor_pago = row_lanc.get('VALOR_PAGO', 0)
    banco = row_lanc.get('BANCO', '')
    
    # Valida dados essenciais
    if pd.isna(data_pag) or valor_pago <= 0:
        return lancamentos
    
    # Identifica o banco
    banco_identificado = _identificar_banco(banco)
    
    # Define conta bancária e código de histórico
    # Para Relatório Financeiro: Pagamento Banco=34, Pagamento Caixa=1, Recebimento=2
    if banco_identificado == 'CAIXA':
        conta_banco = CONTA_CAIXA
        cod_historico = 1  # Pagamento pelo caixa
    else:
        conta_banco = BANCOS_CONTAS.get(banco_identificado, 0)
        cod_historico = 34  # Pagamento pelo banco
    
    if conta_banco == 0:
        # Banco não identificado, não processa
        return lancamentos
    
    # Busca conta do fornecedor (ignora histórico da planilha, usa padrões fixos)
    conta_fornecedor, _ = buscar_conta_fornecedor(fornecedor, df_contas_financeiro)
    
    if conta_fornecedor == 0:
        # Fornecedor não cadastrado, marca como não classificado
        lancamentos.append({
            'DATA': fmt_data(data_pag),
            'COD_CONTA_DEBITO': '',
            'COD_CONTA_CREDITO': conta_banco,
            'VALOR': fmt_valor(valor_pago),
            'COD_HISTORICO': cod_historico,
            'COMPLEMENTO': _criar_complemento(nf, fornecedor),
            'INICIA_LOTE': '1',
            'STATUS': 'NAO_CLASSIFICADO',
            'MOTIVO': f'Fornecedor não cadastrado: {fornecedor}',
            'FORNECEDOR': fornecedor,
            'NF': nf,
        })
        return lancamentos
    
    # Cria complemento
    complemento = _criar_complemento(nf, fornecedor)
    
    # Verifica se há juros/multas ou descontos
    tem_juros = juros_multas > 0.01
    tem_desconto = descontos > 0.01
    
    if tem_juros or tem_desconto:
        # Lançamento composto: valor original + juros/multas - descontos
        # Primeiro lançamento: valor original (débito fornecedor)
        lancamentos.append({
            'DATA': fmt_data(data_pag),
            'COD_CONTA_DEBITO': conta_fornecedor,
            'COD_CONTA_CREDITO': '',
            'VALOR': fmt_valor(valor_original),
            'COD_HISTORICO': cod_historico,
            'COMPLEMENTO': complemento,
            'INICIA_LOTE': '1',
            'STATUS': 'OK',
        })
        
        # Segundo lançamento: juros/multas (débito conta 168)
        if tem_juros:
            lancamentos.append({
                'DATA': fmt_data(data_pag),
                'COD_CONTA_DEBITO': 168,
                'COD_CONTA_CREDITO': '',
                'VALOR': fmt_valor(juros_multas),
                'COD_HISTORICO': cod_historico,
                'COMPLEMENTO': complemento,
                'INICIA_LOTE': '',
                'STATUS': 'OK',
            })
        
        # Terceiro lançamento: descontos obtidos (crédito conta 265)
        if tem_desconto:
            lancamentos.append({
                'DATA': fmt_data(data_pag),
                'COD_CONTA_DEBITO': '',
                'COD_CONTA_CREDITO': 265,
                'VALOR': fmt_valor(descontos),
                'COD_HISTORICO': cod_historico,
                'COMPLEMENTO': complemento,
                'INICIA_LOTE': '',
                'STATUS': 'OK',
            })
        
        # Último lançamento: crédito bancário (valor efetivamente pago)
        lancamentos.append({
            'DATA': fmt_data(data_pag),
            'COD_CONTA_DEBITO': '',
            'COD_CONTA_CREDITO': conta_banco,
            'VALOR': fmt_valor(valor_pago),
            'COD_HISTORICO': cod_historico,
            'COMPLEMENTO': complemento,
            'INICIA_LOTE': '',
            'STATUS': 'OK',
        })
    else:
        # Lançamento simples: débito fornecedor (valor original), crédito banco (valor pago)
        # Normalmente valor_original = valor_pago quando não há juros/descontos
        lancamentos.append({
            'DATA': fmt_data(data_pag),
            'COD_CONTA_DEBITO': conta_fornecedor,
            'COD_CONTA_CREDITO': conta_banco,
            'VALOR': fmt_valor(valor_original if valor_original > 0 else valor_pago),
            'COD_HISTORICO': cod_historico,
            'COMPLEMENTO': complemento,
            'INICIA_LOTE': '1',
            'STATUS': 'OK',
        })
    
    # Marca no extrato como conciliado (se encontrado)
    mov_extrato = _encontrar_no_extrato(
        data_pag, valor_pago, fornecedor, df_extrato, 'DEBITO'
    )
    
    if mov_extrato is not None:
        idx = mov_extrato.name
        df_extrato.at[idx, 'CONCILIADO'] = True
        df_extrato.at[idx, 'TIPO_CONCILIACAO'] = 'LANCAMENTO'
    
    return lancamentos


def _processar_extrato_nao_conciliado(df_extrato: pd.DataFrame, 
                                      contas_bancos: Dict[str, pd.DataFrame],
                                      df_lancamentos: pd.DataFrame = None,
                                      df_contas_financeiro: pd.DataFrame = None) -> List[Dict]:
    """
    Processa TODAS as movimentações do extrato que não foram conciliadas com lançamentos.
    Busca nas abas dos bancos (SICOOB, BRADESCO, SICREDI) para classificar.
    Usa a coluna BANCO_ORIGEM para determinar a conta bancária correta.
    """
    lancamentos = []
    
    # Filtra apenas não conciliados
    df_nao_conciliado = df_extrato[df_extrato.get('CONCILIADO', False) == False].copy()
    
    for idx, row in df_nao_conciliado.iterrows():
        data = row.get('DATA')
        historico = row.get('HISTORICO', '')
        valor = row.get('VALOR_ABS', 0)
        tipo = row.get('TIPO_MOVIMENTO', 'OUTRO')
        banco_origem = row.get('BANCO_ORIGEM', '').upper()
        
        if pd.isna(data) or valor <= 0:
            continue
        
        # Determina a conta bancária baseado no BANCO_ORIGEM (aba de onde veio o movimento)
        conta_banco = CONTA_SICOOB  # Padrão
        if banco_origem == 'SICOOB':
            conta_banco = CONTA_SICOOB  # 809
        elif banco_origem == 'BRADESCO':
            conta_banco = CONTA_BRADESCO  # 7
        elif banco_origem == 'SICREDI':
            conta_banco = CONTA_SICREDI  # 808
        
        # Busca em TODAS as abas de bancos para encontrar a conta contábil
        conta_encontrada = 0
        cod_hist_encontrado = 34 if tipo == 'DEBITO' else 2
        
        # Tenta encontrar nas abas dos bancos (SICOOB, BRADESCO, SICREDI)
        for banco_nome, df_banco in contas_bancos.items():
            if banco_nome == 'RELATORIO_FINANCEIRO':
                continue
            
            if df_banco is None or df_banco.empty:
                continue
                
            conta, cod_hist = buscar_conta_banco(historico, df_banco, tipo)
            if conta > 0:
                conta_encontrada = conta
                cod_hist_encontrado = cod_hist
                break
        
        # Se não encontrou nos bancos, tenta no Relatório Financeiro
        if conta_encontrada == 0 and df_contas_financeiro is not None and not df_contas_financeiro.empty:
            conta_forn, _ = buscar_conta_fornecedor(historico, df_contas_financeiro)
            if conta_forn > 0:
                conta_encontrada = conta_forn
        
        if conta_encontrada == 0:
            # Não classificado - ainda gera o lançamento mas sem conta definida
            lancamentos.append({
                'DATA': fmt_data(data),
                'COD_CONTA_DEBITO': '',
                'COD_CONTA_CREDITO': '',
                'VALOR': fmt_valor(valor),
                'COD_HISTORICO': cod_hist_encontrado,
                'COMPLEMENTO': limpar_complemento(historico) if historico else '',
                'INICIA_LOTE': '1',
                'STATUS': 'NAO_CLASSIFICADO',
                'MOTIVO': f'Histórico não cadastrado: {historico}',
                'HISTORICO': historico,
                'BANCO_ORIGEM': banco_origem,
            })
        else:
            # Cria lançamento baseado no tipo de movimento
            if tipo == 'DEBITO':
                # Saída: débito na conta classificada, crédito no banco
                lancamentos.append({
                    'DATA': fmt_data(data),
                    'COD_CONTA_DEBITO': conta_encontrada,
                    'COD_CONTA_CREDITO': conta_banco,
                    'VALOR': fmt_valor(valor),
                    'COD_HISTORICO': cod_hist_encontrado,
                    'COMPLEMENTO': limpar_complemento(historico) if historico else '',
                    'INICIA_LOTE': '1',
                    'STATUS': 'OK',
                })
            else:
                # Entrada (CREDITO): débito no banco, crédito na conta classificada
                lancamentos.append({
                    'DATA': fmt_data(data),
                    'COD_CONTA_DEBITO': conta_banco,
                    'COD_CONTA_CREDITO': conta_encontrada,
                    'VALOR': fmt_valor(valor),
                    'COD_HISTORICO': cod_hist_encontrado,
                    'COMPLEMENTO': limpar_complemento(historico) if historico else '',
                    'INICIA_LOTE': '1',
                    'STATUS': 'OK',
                })
        
        # Marca como processado
        df_extrato.at[idx, 'CONCILIADO'] = True
        df_extrato.at[idx, 'TIPO_CONCILIACAO'] = 'EXTRATO_DIRETO'
    
    return lancamentos


def conciliar_vps(df_lancamentos: pd.DataFrame, df_extrato: pd.DataFrame,
                  contas_contabeis: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict]:
    """
    Realiza conciliação completa da VPS METALÚRGICA.
    
    Retorna:
        - DataFrame com lançamentos contábeis no formato CSV
        - Dicionário com estatísticas e informações da conciliação
    """
    
    # Inicializa coluna de conciliação no extrato
    df_extrato['CONCILIADO'] = False
    df_extrato['TIPO_CONCILIACAO'] = ''
    
    # Lista para acumular todos os lançamentos
    todos_lancamentos = []
    
    # Contador de grupo para manter lançamentos compostos juntos
    grupo_contador = 0
    
    # Estatísticas
    stats = {
        'total_lancamentos': len(df_lancamentos),
        'total_extrato': len(df_extrato),
        'conciliados_lancamento': 0,
        'conciliados_extrato': 0,
        'nao_classificados': 0,
        'valor_total_lancamentos': 0,
        'valor_total_conciliado': 0,
    }
    
    # 1. Processa todos os lançamentos da planilha (PRIORIDADE)
    df_contas_financeiro = contas_contabeis.get('RELATORIO_FINANCEIRO', pd.DataFrame())
    
    # Contador de ordem global para manter sequência absoluta
    ordem_global = 0
    
    for idx, row in df_lancamentos.iterrows():
        lancamentos_gerados = _processar_lancamento(
            row, df_contas_financeiro, df_extrato, contas_contabeis
        )
        
        # Adiciona identificador de grupo e ordem para manter lançamentos compostos juntos
        for lanc in lancamentos_gerados:
            lanc['_GRUPO'] = grupo_contador
            lanc['_ORDEM'] = ordem_global
            ordem_global += 1
        grupo_contador += 1
        
        todos_lancamentos.extend(lancamentos_gerados)
        
        # Atualiza estatísticas
        valor_pago = row.get('VALOR_PAGO', 0)
        stats['valor_total_lancamentos'] += valor_pago
        
        # Verifica se foi classificado
        tem_nao_classificado = any(l.get('STATUS') == 'NAO_CLASSIFICADO' for l in lancamentos_gerados)
        if tem_nao_classificado:
            stats['nao_classificados'] += 1
        else:
            stats['conciliados_lancamento'] += 1
            stats['valor_total_conciliado'] += valor_pago
    
    # 2. Processa movimentações do extrato não conciliadas
    lancamentos_extrato = _processar_extrato_nao_conciliado(
        df_extrato, 
        contas_contabeis,
        df_lancamentos,
        df_contas_financeiro
    )
    
    # Adiciona identificador de grupo e ordem para cada lançamento do extrato
    for lanc in lancamentos_extrato:
        lanc['_GRUPO'] = grupo_contador
        lanc['_ORDEM'] = ordem_global
        ordem_global += 1
        grupo_contador += 1
    
    todos_lancamentos.extend(lancamentos_extrato)
    
    # Conta não classificados do extrato
    nao_class_extrato = sum(1 for l in lancamentos_extrato if l.get('STATUS') == 'NAO_CLASSIFICADO')
    stats['nao_classificados'] += nao_class_extrato
    
    # Conta conciliados do extrato
    stats['conciliados_extrato'] = len(df_extrato[df_extrato['CONCILIADO'] == True])
    
    # 3. Converte para DataFrame
    if todos_lancamentos:
        df_resultado = pd.DataFrame(todos_lancamentos)
        
        # Ordena por data, grupo e ordem interna para manter lançamentos compostos juntos
        if 'DATA' in df_resultado.columns:
            # Converte data para ordenação
            df_resultado['_DATA_SORT'] = pd.to_datetime(
                df_resultado['DATA'], format='%d/%m/%Y', errors='coerce'
            )
            # Ordena por DATA, GRUPO e ORDEM (para manter lançamentos compostos na sequência correta)
            colunas_ordenacao = ['_DATA_SORT', '_GRUPO', '_ORDEM']
            colunas_ordenacao = [c for c in colunas_ordenacao if c in df_resultado.columns]
            df_resultado = df_resultado.sort_values(colunas_ordenacao)
            
            # Remove colunas auxiliares
            colunas_remover = ['_DATA_SORT', '_GRUPO', '_ORDEM']
            colunas_remover = [c for c in colunas_remover if c in df_resultado.columns]
            df_resultado = df_resultado.drop(columns=colunas_remover)
        else:
            # Remove colunas auxiliares se existirem
            colunas_remover = ['_GRUPO', '_ORDEM']
            colunas_remover = [c for c in colunas_remover if c in df_resultado.columns]
            if colunas_remover:
                df_resultado = df_resultado.drop(columns=colunas_remover)
        
        # Reseta o índice após ordenação
        df_resultado = df_resultado.reset_index(drop=True)
        
        # Reordena colunas para formato padrão CSV
        colunas_csv = [
            'DATA', 'COD_CONTA_DEBITO', 'COD_CONTA_CREDITO', 
            'VALOR', 'COD_HISTORICO', 'COMPLEMENTO', 'INICIA_LOTE'
        ]
        
        # Mantém colunas extras para análise
        colunas_extras = [c for c in df_resultado.columns if c not in colunas_csv]
        df_resultado = df_resultado[colunas_csv + colunas_extras]
        
    else:
        df_resultado = pd.DataFrame()
    
    return df_resultado, stats
