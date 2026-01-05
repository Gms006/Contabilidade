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

    payments_month_first:
        True  -> interpreta '07/01/2025' como 01/jul/2025 (MM/DD/AAAA)
        False -> interpreta '07/01/2025' como 07/jan/2025 (DD/MM/AAAA)
    """
    required = [
        "Data pagamento",
        "Nome do fornecedor",
        "Nota fiscal",
        "Valor",
        "Multa e juros",
        "Valor a pagar",
    ]
    df = pd.read_excel(file, engine="openpyxl")

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Pagamentos.xlsx sem colunas obrigatórias: {missing}")

    df = df.copy()

    # Coluna opcional
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
    """
    required = ["CONTAS CONTABEIS", "NOME", "CLASSIFICAÇÃO", "HISTORICO"]
    df = pd.read_excel(file, engine="openpyxl")

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Contas Contábeis.xlsx sem colunas obrigatórias: {missing}")

    df = df.copy()
    df["_nome_norm"] = df["NOME"].map(_clean_text)
    df["_class_norm"] = df["CLASSIFICAÇÃO"].map(_clean_text)

    cols = {"conta": "CONTAS CONTABEIS", "nome": "NOME", "classif": "CLASSIFICAÇÃO", "historico": "HISTORICO"}
    return df, cols
