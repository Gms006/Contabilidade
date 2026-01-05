# app/services/parsing.py
from __future__ import annotations
import pandas as pd
import numpy as np
from dateutil import parser
from typing import Tuple
import unicodedata


# ----------------- normalização básica -----------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _clean_text(x: object) -> str:
    if pd.isna(x):
        return ""
    s = _strip_accents(str(x)).strip().casefold()
    # somente letras, números e espaço -> chave estável para nomes
    return "".join(ch for ch in s if ch.isalnum() or ch.isspace())


# ----------------- conversões BR -----------------
def to_float_brl(x: object) -> float:
    """
    Converte números no padrão brasileiro (vírgula decimal) para float.
    Aceita strings com espaços/pontos de milhar e sinal.
    """
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)

    s = str(x).replace("\xa0", "").strip().replace(" ", "")
    # mantém apenas dígitos, vírgula, ponto e sinal
    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s:
        return np.nan

    # se tem vírgula de decimal e pontos de milhar -> remove pontos
    if s.count(",") == 1 and s.count(".") >= 1:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return np.nan


def _to_datetime_any(x: object, *, dayfirst: bool) -> pd.Timestamp | pd.NaT:
    """
    Conversor robusto:
    - aceita Timestamp/datetime/strings
    - aceita números-seriais do Excel (dias desde 1899-12-30)
    - controla ambiguidade via `dayfirst`
    """
    if x is None or (isinstance(x, float) and np.isnan(x)) or (isinstance(x, str) and x.strip() == ""):
        return pd.NaT

    # número-serial do Excel (comum em xlsx)
    if isinstance(x, (int, float, np.integer, np.floating)):
        try:
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(x), unit="D")
        except Exception:
            pass

    # tenta com pandas diretamente
    try:
        dt = pd.to_datetime(x, dayfirst=dayfirst, errors="coerce")
        if not pd.isna(dt):
            return dt
    except Exception:
        pass

    # fallback via dateutil
    try:
        return pd.to_datetime(parser.parse(str(x), dayfirst=dayfirst))
    except Exception:
        return pd.NaT


def to_date_brl(x: object, *, dayfirst: bool = True) -> pd.Timestamp | pd.NaT:
    """Wrapper para manter compatibilidade com nome antigo."""
    return _to_datetime_any(x, dayfirst=dayfirst)


# ----------------- PAGAMENTOS -----------------
def load_payments(file, payments_month_first: bool = True) -> tuple[pd.DataFrame, dict]:
    """
    Lê a planilha de pagamentos no layout:
      Data pagamento | Nome do fornecedor | Nota fiscal | Valor | Multa e juros | [Descontos] | Valor a pagar
    'Descontos' é opcional e vira 0 quando ausente.
    
    Usa busca flexível de colunas (case-insensitive e variações).

    payments_month_first:
        True  -> interpreta '07/01/2025' como 01/jul/2025 (MM/DD/AAAA)
        False -> interpreta '07/01/2025' como 07/jan/2025 (DD/MM/AAAA)
    """
    df = pd.read_excel(file, engine="openpyxl")
    
    # Mapeamento flexível de colunas
    col_data = _find_column_flexible(df, [
        "data pagamento", "data de pagamento", "data_pagamento", "dt_pagamento", 
        "data pag", "dt pag", "data", "date"
    ])
    col_fornecedor = _find_column_flexible(df, [
        "nome do fornecedor", "fornecedor", "nome fornecedor", "razao social", 
        "razão social", "nome", "supplier"
    ])
    col_nota = _find_column_flexible(df, [
        "nota fiscal", "nf", "nota", "num nota", "numero nota", "nf-e", 
        "numero nf", "doc", "documento"
    ])
    col_valor = _find_column_flexible(df, [
        "valor", "vlr", "valor titulo", "valor do titulo", "value", "amount"
    ])
    col_multa = _find_column_flexible(df, [
        "multa e juros", "multa juros", "juros", "multa", "acrescimos", "acréscimos"
    ])
    col_valor_pagar = _find_column_flexible(df, [
        "valor a pagar", "valor pagar", "vlr pagar", "valor pago", "vlr pago", 
        "valor liquido", "valor líquido", "total"
    ])
    col_descontos = _find_column_flexible(df, [
        "descontos", "desconto", "desc", "abatimentos", "abatimento"
    ])
    
    # Validação: colunas essenciais devem existir
    missing = []
    if col_data is None:
        missing.append("Data pagamento (ou variações: data de pagamento, data_pagamento, data pag)")
    if col_fornecedor is None:
        missing.append("Nome do fornecedor (ou variações: fornecedor, razao social)")
    if col_nota is None:
        missing.append("Nota fiscal (ou variações: nf, nota, numero nota)")
    if col_valor is None:
        missing.append("Valor (ou variações: vlr, valor titulo)")
    if col_multa is None:
        missing.append("Multa e juros (ou variações: multa juros, juros, acrescimos)")
    if col_valor_pagar is None:
        missing.append("Valor a pagar (ou variações: valor pagar, valor pago, valor liquido)")
    
    if missing:
        raise ValueError(
            f"Pagamentos.xlsx sem colunas obrigatórias: {', '.join(missing)}.\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
    
    # Renomeia para o padrão interno
    rename_map = {
        col_data: "Data pagamento",
        col_fornecedor: "Nome do fornecedor",
        col_nota: "Nota fiscal",
        col_valor: "Valor",
        col_multa: "Multa e juros",
        col_valor_pagar: "Valor a pagar"
    }
    
    # Adiciona descontos ao mapa se existir
    if col_descontos:
        rename_map[col_descontos] = "Descontos"
    
    df = df.rename(columns=rename_map).copy()

    # Coluna opcional: se não existir, cria
    if "Descontos" not in df.columns:
        df["Descontos"] = 0

    # Remove linhas totalmente vazias (sem data, valor e fornecedor)
    mask_keep = (
        df["Data pagamento"].astype(str).str.strip().ne("") |
        df["Valor a pagar"].astype(str).str.strip().ne("") |
        df["Nome do fornecedor"].astype(str).str.strip().ne("")
    )
    df = df.loc[mask_keep].reset_index(drop=True)

    # Colunas internas para a lógica
    df["_idx_pag"] = np.arange(len(df))
    # month-first => dayfirst=False
    df["_data"] = df["Data pagamento"].map(lambda v: to_date_brl(v, dayfirst=not payments_month_first))
    df["_valor"] = df["Valor a pagar"].map(to_float_brl)        # valor liquidado (para conciliação)
    df["_valor_original"] = df["Valor"].map(to_float_brl)       # valor do título (linha principal)
    df["_multa"] = df["Multa e juros"].map(to_float_brl)
    df["_descontos"] = df["Descontos"].map(to_float_brl)
    df["_forn_norm"] = df["Nome do fornecedor"].map(_clean_text)
    df["_doc"] = df["Nota fiscal"].astype(str)                  # NF sempre texto

    cols = {
        "data": "Data pagamento",
        "valor": "Valor a pagar",
        "valor_original": "Valor",
        "multa": "Multa e juros",
        "descontos": "Descontos",
        "fornecedor": "Nome do fornecedor",
        "doc": "Nota fiscal",
        "banco": None,
    }
    return df, cols


# ----------------- EXTRATO -----------------
def _find_column_flexible(df: pd.DataFrame, possible_names: list[str]) -> str | None:
    """
    Procura uma coluna no DataFrame usando vários nomes possíveis (case-insensitive).
    Retorna o nome real da coluna encontrada ou None.
    """
    df_cols_lower = {col.lower(): col for col in df.columns if isinstance(col, str)}
    for name in possible_names:
        normalized = name.lower().strip()
        if normalized in df_cols_lower:
            return df_cols_lower[normalized]
    return None


def _normalize_extrato_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Padroniza colunas do extrato para: DATA | DOCUMENTO | HISTÓRICO | VALOR.
    Busca flexível por nomes de colunas (case-insensitive e variações).
    Remove linhas de 'saldo', cria _hist_norm, _data e _valor_raw.
    """
    df = df_raw.copy()
    
    # Mapeamento flexível de colunas
    col_data = _find_column_flexible(df, ["data", "dt", "date", "dt_movimento", "data_movimento"])
    col_doc = _find_column_flexible(df, ["documento", "doc", "numero", "num_doc", "numero_documento"])
    col_hist = _find_column_flexible(df, ["historico", "histórico", "descricao", "descrição", "hist", "description"])
    col_valor = _find_column_flexible(df, ["valor", "value", "vlr", "amount", "montante"])
    
    # Validação: todas as colunas essenciais devem existir
    missing = []
    if col_data is None:
        missing.append("DATA (ou variações: data, dt, date)")
    if col_doc is None:
        missing.append("DOCUMENTO (ou variações: documento, doc, numero)")
    if col_hist is None:
        missing.append("HISTÓRICO (ou variações: historico, histórico, descricao)")
    if col_valor is None:
        missing.append("VALOR (ou variações: valor, value, vlr)")
    
    if missing:
        raise ValueError(
            f"Extrato bancário sem colunas obrigatórias: {', '.join(missing)}.\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
    
    # Renomeia para o padrão interno
    rename_map = {
        col_data: "DATA",
        col_doc: "DOCUMENTO",
        col_hist: "HISTÓRICO",
        col_valor: "VALOR"
    }
    df = df.rename(columns=rename_map)
    
    # Mantém apenas as colunas padronizadas
    df = df[["DATA", "DOCUMENTO", "HISTÓRICO", "VALOR"]].copy()

    # Normalizações
    df["_hist_norm"] = df["HISTÓRICO"].map(_clean_text)
    df = df[~df["_hist_norm"].str.contains("saldo", na=False)].copy()
    df["_data"] = df["DATA"].map(lambda v: to_date_brl(v, dayfirst=True))  # extrato é BR (DD/MM/AAAA)
    df["_valor_raw"] = df["VALOR"].map(to_float_brl)
    return df


def load_bank(file) -> tuple[pd.DataFrame, dict]:
    """Retorna somente as SAÍDAS do extrato (valores negativos)."""
    df_raw = pd.read_excel(file, engine="openpyxl")
    df = _normalize_extrato_df(df_raw)
    df = df[pd.to_numeric(df["_valor_raw"], errors="coerce") < 0].copy()  # SAÍDAS
    df["_idx_ext"] = np.arange(len(df))
    df["_valor"] = df["_valor_raw"].abs()  # casar com valor pago positivo

    cols = {"data": "DATA", "doc": "DOCUMENTO", "historico": "HISTÓRICO", "valor": "VALOR", "saldo": None}
    return df, cols


def load_bank_split(file) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Separa extrato em SAÍDAS (débitos) e ENTRADAS (créditos)."""
    df_raw = pd.read_excel(file, engine="openpyxl")
    df = _normalize_extrato_df(df_raw)
    df["_idx_base"] = np.arange(len(df))

    saidas = df[pd.to_numeric(df["_valor_raw"], errors="coerce") < 0].copy()
    entradas = df[pd.to_numeric(df["_valor_raw"], errors="coerce") > 0].copy()

    saidas["_idx_ext"] = np.arange(len(saidas))
    entradas["_idx_cred"] = np.arange(len(entradas))
    saidas["_valor"] = saidas["_valor_raw"].abs()
    entradas["_valor"] = entradas["_valor_raw"].abs()

    cols = {"data": "DATA", "doc": "DOCUMENTO", "historico": "HISTÓRICO", "valor": "VALOR", "saldo": None}
    return saidas, entradas, cols


# ----------------- CONTAS -----------------
def load_chart_of_accounts(file) -> tuple[pd.DataFrame, dict]:
    """
    Lê o plano de contas com colunas:
      CONTAS CONTABEIS | NOME | CLASSIFICAÇÃO | HISTORICO
    Normaliza chaves para uso pelos mapas (accounting.build_maps).
    
    Usa busca flexível de colunas (case-insensitive e variações).
    """
    df = pd.read_excel(file, engine="openpyxl")
    
    # Mapeamento flexível de colunas
    col_conta = _find_column_flexible(df, [
        "contas contabeis", "contas contábeis", "conta contabil", "conta contábil",
        "codigo conta", "código conta", "conta", "account", "cod_conta"
    ])
    col_nome = _find_column_flexible(df, [
        "nome", "descricao", "descrição", "desc", "description", "name"
    ])
    col_classif = _find_column_flexible(df, [
        "classificacao", "classificação", "classif", "class", "tipo", "category"
    ])
    col_historico = _find_column_flexible(df, [
        "historico", "histórico", "hist", "history", "observacao", "observação", "obs"
    ])
    
    # Validação: colunas essenciais devem existir
    missing = []
    if col_conta is None:
        missing.append("CONTAS CONTABEIS (ou variações: conta contabil, codigo conta)")
    if col_nome is None:
        missing.append("NOME (ou variações: descricao, description)")
    if col_classif is None:
        missing.append("CLASSIFICAÇÃO (ou variações: classificacao, tipo)")
    if col_historico is None:
        missing.append("HISTORICO (ou variações: histórico, observacao)")
    
    if missing:
        raise ValueError(
            f"Contas Contábeis.xlsx sem colunas obrigatórias: {', '.join(missing)}.\n"
            f"Colunas encontradas: {list(df.columns)}"
        )
    
    # Renomeia para o padrão interno
    rename_map = {
        col_conta: "CONTAS CONTABEIS",
        col_nome: "NOME",
        col_classif: "CLASSIFICAÇÃO",
        col_historico: "HISTORICO"
    }
    df = df.rename(columns=rename_map).copy()
    
    df["_nome_norm"] = df["NOME"].map(_clean_text)
    df["_class_norm"] = df["CLASSIFICAÇÃO"].map(_clean_text)

    cols = {"conta": "CONTAS CONTABEIS", "nome": "NOME", "classif": "CLASSIFICAÇÃO", "historico": "HISTORICO"}
    return df, cols
