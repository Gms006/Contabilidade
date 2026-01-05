# -*- coding: utf-8 -*-
"""
Extratores de PDF para Banco do Brasil e SICOOB.
Versão simplificada para integração com Streamlit.
"""

from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime
from typing import Any, List, Optional, Tuple
import io

import pandas as pd

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class ExtratorBB:
    """Extrator de extratos do Banco do Brasil em PDF."""
    
    def __init__(self):
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber não está instalado. Execute: pip install pdfplumber")
        self.movimentacoes = []
        self.info_conta = {}
    
    def extrair_texto(self, pdf_file: Any) -> str:
        """Extrai texto do PDF."""
        texto = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        return texto
    
    def extrair_periodo(self, texto: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extrai período do extrato."""
        match = re.search(r'Per[ií]odo:\s*(\d{2}/\d{2}/\d{4})\s*(?:a|-)\s*(\d{2}/\d{2}/\d{4})', 
                         texto, re.IGNORECASE)
        if match:
            inicio = datetime.strptime(match.group(1), '%d/%m/%Y')
            fim = datetime.strptime(match.group(2), '%d/%m/%Y')
            return inicio, fim
        return None, None
    
    def parse_valor(self, valor_str: str) -> float:
        """Converte string de valor para float."""
        if not valor_str:
            return 0.0
        valor_str = valor_str.replace('R$', '').strip()
        valor_str = valor_str.replace('.', '').replace(',', '.')
        try:
            return float(valor_str)
        except:
            return 0.0
    
    def extrair_lancamentos(self, texto: str, periodo_fim: datetime) -> List[dict]:
        """Extrai lançamentos do texto do PDF."""
        lancamentos = []
        linhas = texto.split('\n')
        
        # Padrões de linha de lançamento BB
        # Data | Documento | Histórico | Valor (C/D) | Saldo
        padrao_data = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        padrao_valor = re.compile(r'([\d.,]+)\s*$')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            match_data = padrao_data.match(linha)
            if match_data:
                try:
                    data = datetime.strptime(match_data.group(1), '%d/%m/%Y')
                    
                    # Extrair resto da linha
                    resto = linha[10:].strip()
                    
                    # Tentar extrair documento e histórico
                    partes = resto.split()
                    if len(partes) >= 3:
                        documento = partes[0]
                        
                        # O último valor geralmente é o saldo
                        valores = re.findall(r'[\d.,]+', resto)
                        if len(valores) >= 2:
                            # Determinar crédito/débito baseado no contexto
                            historico = ' '.join(partes[1:-2]) if len(partes) > 3 else partes[1]
                            
                            lancamentos.append({
                                'Data': data,
                                'Documento': documento,
                                'Historico': historico,
                                'Credito': 0,
                                'Debito': 0,
                                'Saldo': 0
                            })
                except Exception as e:
                    continue
        
        return lancamentos
    
    def processar_pdf(self, pdf_file: Any) -> pd.DataFrame:
        """Processa PDF e retorna DataFrame formatado."""
        texto = self.extrair_texto(pdf_file)
        inicio, fim = self.extrair_periodo(texto)
        
        if fim is None:
            fim = datetime.now()
        
        lancamentos = self.extrair_lancamentos(texto, fim)
        
        if not lancamentos:
            return pd.DataFrame(columns=['Data', 'Documento', 'Historico', 'Credito', 'Debito', 'Saldo'])
        
        df = pd.DataFrame(lancamentos)
        df['Banco'] = 'BB'
        return df


class ExtratorSicoob:
    """Extrator de extratos do SICOOB em PDF."""
    
    def __init__(self):
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber não está instalado. Execute: pip install pdfplumber")
        self.movimentacoes = []
        self.info_conta = {}
    
    def extrair_texto(self, pdf_file: Any) -> str:
        """Extrai texto do PDF."""
        texto = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        return texto
    
    def extrair_periodo(self, texto: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extrai período do extrato."""
        # Formato SICOOB: Periodo: DD/MM/YYYY - DD/MM/YYYY
        match = re.search(r'Periodo:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})', 
                         texto, re.IGNORECASE)
        if match:
            inicio = datetime.strptime(match.group(1), '%d/%m/%Y')
            fim = datetime.strptime(match.group(2), '%d/%m/%Y')
            return inicio, fim
        return None, None
    
    def parse_valor(self, valor_str: str) -> Tuple[float, str]:
        """Converte string de valor para float e tipo (C/D)."""
        if not valor_str:
            return 0.0, ''
        
        valor_str = valor_str.replace('R$', '').strip()
        tipo = 'C' if valor_str.endswith('C') else 'D' if valor_str.endswith('D') else ''
        valor_str = re.sub(r'[CD]$', '', valor_str).strip()
        valor_str = valor_str.replace('.', '').replace(',', '.')
        
        try:
            return float(valor_str), tipo
        except:
            return 0.0, ''
    
    def extrair_lancamentos(self, texto: str) -> List[dict]:
        """Extrai lançamentos do texto do PDF."""
        lancamentos = []
        linhas = texto.split('\n')
        
        padrao_data = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            
            match_data = padrao_data.match(linha)
            if match_data:
                try:
                    data = datetime.strptime(match_data.group(1), '%d/%m/%Y')
                    resto = linha[10:].strip()
                    
                    # Extrair valores com C ou D
                    valores_cd = re.findall(r'([\d.,]+[CD])', resto)
                    
                    # Extrair histórico
                    historico = re.sub(r'[\d.,]+[CD]?', '', resto).strip()
                    historico = ' '.join(historico.split())
                    
                    credito = 0.0
                    debito = 0.0
                    
                    for val_str in valores_cd:
                        val, tipo = self.parse_valor(val_str)
                        if tipo == 'C':
                            credito = val
                        elif tipo == 'D':
                            debito = val
                    
                    if credito > 0 or debito > 0:
                        lancamentos.append({
                            'Data': data,
                            'Documento': '',
                            'Historico': historico[:100],
                            'Credito': credito,
                            'Debito': debito,
                            'Saldo': 0
                        })
                except Exception as e:
                    continue
        
        return lancamentos
    
    def processar_pdf(self, pdf_file: Any) -> pd.DataFrame:
        """Processa PDF e retorna DataFrame formatado."""
        texto = self.extrair_texto(pdf_file)
        lancamentos = self.extrair_lancamentos(texto)
        
        if not lancamentos:
            return pd.DataFrame(columns=['Data', 'Documento', 'Historico', 'Credito', 'Debito', 'Saldo'])
        
        df = pd.DataFrame(lancamentos)
        df['Banco'] = 'SICOOB'
        return df


def processar_pdf_extrato(pdf_file: Any, banco: str = 'auto') -> pd.DataFrame:
    """
    Função utilitária para processar PDF de extrato.
    
    Args:
        pdf_file: Arquivo PDF
        banco: 'BB', 'SICOOB' ou 'auto' para detecção automática
    
    Returns:
        DataFrame com colunas: Data, Documento, Historico, Credito, Debito, Saldo
    """
    if not PDF_AVAILABLE:
        raise ImportError("pdfplumber não está instalado. Execute: pip install pdfplumber")
    
    # Detecção automática
    if banco == 'auto':
        nome_arquivo = getattr(pdf_file, 'name', str(pdf_file)).upper()
        if 'BB' in nome_arquivo or 'BRASIL' in nome_arquivo:
            banco = 'BB'
        elif 'SICOOB' in nome_arquivo:
            banco = 'SICOOB'
        else:
            # Tentar detectar pelo conteúdo
            banco = 'SICOOB'  # Default
    
    if banco == 'BB':
        extrator = ExtratorBB()
    else:
        extrator = ExtratorSicoob()
    
    return extrator.processar_pdf(pdf_file)
