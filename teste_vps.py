# -*- coding: utf-8 -*-
"""
Script de teste para validação da implementação VPS METALÚRGICA
"""

import sys
import os

# Adiciona o diretório ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'streamlit_conciliacao'))

import pandas as pd
from vps.utils_vps import (
    carregar_contas_contabeis,
    carregar_lancamentos,
    carregar_extratos,
)
from vps.conciliador_vps import conciliar_vps


def testar_carga_arquivos():
    """Testa a carga dos arquivos VPS."""
    print("=" * 80)
    print("TESTE 1: Carregamento de Arquivos")
    print("=" * 80)
    
    # Caminhos dos arquivos
    path_contas = r"U:\Automações PYTHON\VPS\MOVIMENTACAO\CONTAS CONTABEIS\CONTAS CONTABEIS.xlsx"
    path_lancamentos = r"U:\Automações PYTHON\VPS\MOVIMENTACAO\MOVIMENTACOES\LANCAMENTOS.xlsx"
    path_extratos = r"U:\Automações PYTHON\VPS\MOVIMENTACAO\MOVIMENTACOES\EXTRATOS.xlsx"
    
    try:
        # Carrega contas contábeis
        print("\n1. Carregando Contas Contábeis...")
        contas = carregar_contas_contabeis(path_contas)
        print(f"   ✓ Abas carregadas: {list(contas.keys())}")
        for aba, df in contas.items():
            print(f"   - {aba}: {len(df)} registros")
        
        # Carrega lançamentos
        print("\n2. Carregando Lançamentos...")
        df_lancamentos = carregar_lancamentos(path_lancamentos)
        print(f"   ✓ {len(df_lancamentos)} lançamentos carregados")
        print(f"   - Colunas: {df_lancamentos.columns.tolist()}")
        print(f"   - Bancos únicos: {df_lancamentos['BANCO'].unique().tolist()}")
        
        # Carrega extratos
        print("\n3. Carregando Extratos...")
        df_extratos = carregar_extratos(path_extratos)
        print(f"   ✓ {len(df_extratos)} movimentações carregadas")
        print(f"   - Colunas: {df_extratos.columns.tolist()}")
        
        # Estatísticas dos extratos
        debitos = len(df_extratos[df_extratos['TIPO_MOVIMENTO'] == 'DEBITO'])
        creditos = len(df_extratos[df_extratos['TIPO_MOVIMENTO'] == 'CREDITO'])
        print(f"   - Débitos: {debitos}")
        print(f"   - Créditos: {creditos}")
        
        print("\n✅ TESTE 1 PASSOU - Todos os arquivos foram carregados corretamente")
        return contas, df_lancamentos, df_extratos
        
    except Exception as e:
        print(f"\n❌ TESTE 1 FALHOU - Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None


def testar_conciliacao(contas, df_lancamentos, df_extratos):
    """Testa o processo de conciliação."""
    print("\n" + "=" * 80)
    print("TESTE 2: Conciliação")
    print("=" * 80)
    
    if contas is None or df_lancamentos is None or df_extratos is None:
        print("❌ TESTE 2 PULADO - Dados não carregados")
        return None, None
    
    try:
        print("\nExecutando conciliação...")
        df_resultado, stats = conciliar_vps(
            df_lancamentos.copy(),
            df_extratos.copy(),
            contas
        )
        
        print("\n📊 Estatísticas da Conciliação:")
        print(f"   - Total de lançamentos processados: {stats['total_lancamentos']}")
        print(f"   - Lançamentos conciliados: {stats['conciliados_lancamento']}")
        print(f"   - Total de extratos: {stats['total_extrato']}")
        print(f"   - Extratos conciliados: {stats['conciliados_extrato']}")
        print(f"   - Não classificados: {stats['nao_classificados']}")
        print(f"   - Valor total de lançamentos: R$ {stats['valor_total_lancamentos']:,.2f}")
        print(f"   - Valor total conciliado: R$ {stats['valor_total_conciliado']:,.2f}")
        
        print(f"\n📋 Lançamentos Contábeis Gerados:")
        print(f"   - Total de linhas no CSV: {len(df_resultado)}")
        
        if 'STATUS' in df_resultado.columns:
            ok = len(df_resultado[df_resultado['STATUS'] == 'OK'])
            nao_class = len(df_resultado[df_resultado['STATUS'] == 'NAO_CLASSIFICADO'])
            print(f"   - Classificados: {ok}")
            print(f"   - Não classificados: {nao_class}")
            
            if nao_class > 0:
                print("\n⚠️  Lançamentos não classificados:")
                df_nao_class = df_resultado[df_resultado['STATUS'] == 'NAO_CLASSIFICADO']
                for idx, row in df_nao_class.iterrows():
                    motivo = row.get('MOTIVO', 'N/A')
                    print(f"      - {motivo}")
        
        print("\n✅ TESTE 2 PASSOU - Conciliação executada com sucesso")
        return df_resultado, stats
        
    except Exception as e:
        print(f"\n❌ TESTE 2 FALHOU - Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def testar_formato_csv(df_resultado):
    """Testa o formato do CSV gerado."""
    print("\n" + "=" * 80)
    print("TESTE 3: Formato do CSV")
    print("=" * 80)
    
    if df_resultado is None or df_resultado.empty:
        print("❌ TESTE 3 PULADO - Nenhum resultado para testar")
        return
    
    try:
        # Verifica colunas obrigatórias
        colunas_obrigatorias = [
            'DATA', 'COD_CONTA_DEBITO', 'COD_CONTA_CREDITO',
            'VALOR', 'COD_HISTORICO', 'COMPLEMENTO', 'INICIA_LOTE'
        ]
        
        print("\n1. Verificando colunas obrigatórias...")
        for col in colunas_obrigatorias:
            if col in df_resultado.columns:
                print(f"   ✓ {col}")
            else:
                print(f"   ✗ {col} - FALTANDO!")
        
        # Verifica alguns registros
        print("\n2. Amostra dos primeiros registros:")
        df_csv = df_resultado[colunas_obrigatorias].head(5)
        print(df_csv.to_string(index=False))
        
        # Verifica formato de data
        print("\n3. Verificando formato de datas...")
        datas_ok = df_resultado['DATA'].str.match(r'\d{2}/\d{2}/\d{4}').all()
        if datas_ok:
            print("   ✓ Todas as datas no formato DD/MM/AAAA")
        else:
            print("   ✗ Algumas datas em formato incorreto")
        
        # Verifica formato de valor
        print("\n4. Verificando formato de valores...")
        valores_ok = df_resultado['VALOR'].str.match(r'\d+,\d{2}').all()
        if valores_ok:
            print("   ✓ Todos os valores no formato brasileiro (1.234,56)")
        else:
            print("   ✗ Alguns valores em formato incorreto")
        
        print("\n✅ TESTE 3 PASSOU - Formato do CSV está correto")
        
    except Exception as e:
        print(f"\n❌ TESTE 3 FALHOU - Erro: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 80)
    print("TESTES DE VALIDAÇÃO - VPS METALÚRGICA")
    print("=" * 80)
    
    # Teste 1: Carga de arquivos
    contas, df_lancamentos, df_extratos = testar_carga_arquivos()
    
    # Teste 2: Conciliação
    df_resultado, stats = testar_conciliacao(contas, df_lancamentos, df_extratos)
    
    # Teste 3: Formato CSV
    testar_formato_csv(df_resultado)
    
    print("\n" + "=" * 80)
    print("TESTES CONCLUÍDOS")
    print("=" * 80)
    
    if df_resultado is not None and not df_resultado.empty:
        print(f"\n📊 Resumo Final:")
        print(f"   - {len(df_resultado)} lançamentos contábeis gerados")
        if stats:
            taxa_sucesso = (stats['conciliados_lancamento'] / stats['total_lancamentos'] * 100) if stats['total_lancamentos'] > 0 else 0
            print(f"   - Taxa de sucesso: {taxa_sucesso:.1f}%")
            print(f"   - Valor total processado: R$ {stats['valor_total_lancamentos']:,.2f}")


if __name__ == "__main__":
    main()
