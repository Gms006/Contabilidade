# app/services/matching.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List
import pandas as pd
import logging

__all__ = ["MatchParams", "match_transactions", "explain_mismatch"]

logger = logging.getLogger(__name__)


@dataclass
class MatchParams:
    """
    Parâmetros do matching.

    strict_date_matching=True  -> casa apenas Data + Valor exatos (regra padrão exigida).
    strict_date_matching=False -> casa por Valor exato permitindo tolerância de dias na data.
    """
    tolerance_days: int = 0              # tolerância de dias (apenas se strict_date_matching=False)
    tolerance_value: float = 0.0         # reservado (não usamos; valor é sempre exato)
    strict_date_matching: bool = True    # modo padrão
    allow_multiple_matches: bool = False # mantido p/ compat.; casamos 1:1 (FIFO)


# ---------------- utils ----------------
def _normalize_date_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()

def _round_money(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").round(2)

def _safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _row_idx(row: pd.Series, col_name: str, fallback_name: str | None = None) -> int:
    """Retorna o índice salvo (_idx_pag/_idx_ext) ou cai no row.name."""
    if col_name in row:
        try:
            return int(row[col_name])
        except Exception:
            pass
    if fallback_name and fallback_name in row:
        try:
            return int(row[fallback_name])
        except Exception:
            pass
    try:
        return int(row.name)
    except Exception:
        return 0

def _date_diff_days(date1, date2) -> int:
    """Diferença absoluta em dias entre duas datas."""
    try:
        d1 = pd.to_datetime(date1).normalize()
        d2 = pd.to_datetime(date2).normalize()
        return abs((d1 - d2).days)
    except Exception:
        return 999  # valor alto indica erro/indeterminado


# -------------- diagnóstico opcional --------------
def explain_mismatch(row_pag: pd.Series, extrato_df: pd.DataFrame, params: MatchParams | None = None) -> List[str]:
    """
    Explica por que um pagamento não encontrou saída correspondente.
    Usa as mesmas normalizações do matching.
    """
    motivos: List[str] = []
    params = params or MatchParams()

    if extrato_df is None or extrato_df.empty:
        return ["Extrato vazio/sem saídas."]

    data_pag = row_pag.get("_data", pd.NaT)
    valor_pag = _safe_float(row_pag.get("_valor", 0))

    e = extrato_df.copy()
    e["_dkey"] = _normalize_date_series(e["_data"])
    e["_vkey"] = _round_money(e["_valor"])

    dkey = pd.to_datetime(data_pag, errors="coerce").normalize()
    vkey = round(valor_pag, 2)

    same_value = e[e["_vkey"] == vkey]
    if same_value.empty:
        motivos.append(f"Não há saídas com valor exato de {vkey:.2f}.")
        approx = e[(e["_vkey"] >= vkey * 0.99) & (e["_vkey"] <= vkey * 1.01)]
        if not approx.empty:
            motivos.append(f"Existem {len(approx)} saídas com valor similar (±1%).")
        return motivos

    same_date_value = same_value[same_value["_dkey"] == dkey]
    if not same_date_value.empty:
        motivos.append("Há saída com mesma data e valor, possivelmente já utilizada por outro pagamento (FIFO).")
        return motivos

    # sem data exata
    if params.strict_date_matching:
        datas = ", ".join(sorted(same_value["_dkey"].dt.strftime("%d/%m/%Y").unique()))
        motivos.append(f"Valor encontrado, mas não na data exata {dkey.strftime('%d/%m/%Y')}.")
        if datas:
            motivos.append(f"Datas disponíveis para este valor: {datas}.")
    else:
        inside_tol = []
        for _, r in same_value.iterrows():
            if _date_diff_days(dkey, r["_dkey"]) <= params.tolerance_days:
                inside_tol.append(True)
        if not inside_tol:
            motivos.append(f"Valor encontrado, porém fora da tolerância de ±{params.tolerance_days} dia(s).")

    return motivos


# -------------- matching principal --------------
def match_transactions(
    df_pag: pd.DataFrame,
    df_ext: pd.DataFrame,
    cols_pag: Dict[str, str],
    cols_ext: Dict[str, str],
    params: MatchParams | Dict[str, Any] | None = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Concilia por (Data + Valor).
      - Padrão: estrito (data e valor iguais), com FIFO para duplicados utilizando cumcount().
      - Opcional: tolerância de dias (valor exato e data dentro de ±tolerance_days).

    Retorna:
      - matches_df: colunas [data_ref, valor_ref, idx_pag(list), idx_ext(list), rule]
      - pend_data: dict com 'unmatched_pagamentos', 'unmatched_extrato', 'detalhes' e 'stats'
    """
    # parâmetros
    if params is None:
        params = MatchParams()
    elif isinstance(params, dict):
        params = MatchParams(**params)

    logger.info(
        "Matching start | strict_date=%s tolerance_days=%d",
        params.strict_date_matching, params.tolerance_days
    )

    # cópias
    P = df_pag.copy()
    E = df_ext.copy()

    # chaves normalizadas
    P["_dkey"] = _normalize_date_series(P["_data"])
    E["_dkey"] = _normalize_date_series(E["_data"])
    P["_vkey"] = _round_money(P["_valor"])
    E["_vkey"] = _round_money(E["_valor"])

    matches_rows: List[dict] = []
    used_pag_idx: set[int] = set()
    used_ext_idx: set[int] = set()

    if params.strict_date_matching:
        # chave composta + ordinal (FIFO)
        P["_k"] = list(zip(P["_dkey"], P["_vkey"]))
        E["_k"] = list(zip(E["_dkey"], E["_vkey"]))
        P["_ord"] = P.groupby("_k").cumcount()
        E["_ord"] = E.groupby("_k").cumcount()

        M = pd.merge(
            P[["_idx_pag", "_k", "_ord", "_data", "_valor"]],
            E[["_idx_ext", "_k", "_ord", "_data", "_valor"]],
            on=["_k", "_ord"],
            how="inner",
            suffixes=("_p", "_e"),
        )

        for _, r in M.iterrows():
            matches_rows.append(
                {
                    "data_ref": r["_data_p"],       # sempre a data do pagamento
                    "valor_ref": r["_valor_p"],
                    "idx_pag": [int(r["_idx_pag"])],
                    "idx_ext": [int(r["_idx_ext"])],
                    "rule": "data+valor exato (FIFO)",
                }
            )
            used_pag_idx.add(int(r["_idx_pag"]))
            used_ext_idx.add(int(r["_idx_ext"]))

    else:
        # tolerância de dias (valor exato)
        for _, p in P.iterrows():
            if p["_idx_pag"] in used_pag_idx:
                continue
            pag_date = p["_dkey"]
            pag_value = p["_vkey"]

            candidates = E[(E["_vkey"] == pag_value) & (~E["_idx_ext"].isin(used_ext_idx))].copy()
            if candidates.empty:
                continue

            candidates["_days_diff"] = candidates["_dkey"].apply(lambda d: _date_diff_days(pag_date, d))
            valid = candidates[candidates["_days_diff"] <= params.tolerance_days].sort_values(
                ["_days_diff", "_idx_ext"]
            )
            if valid.empty:
                continue

            row = valid.iloc[0]
            matches_rows.append(
                {
                    "data_ref": p["_data"],        # data do pagamento
                    "valor_ref": p["_valor"],
                    "idx_pag": [int(p["_idx_pag"])],
                    "idx_ext": [int(row["_idx_ext"])],
                    "rule": f"valor exato + data ±{int(row['_days_diff'])}d",
                }
            )
            used_pag_idx.add(int(p["_idx_pag"]))
            used_ext_idx.add(int(row["_idx_ext"]))

    matches_df = pd.DataFrame(matches_rows, columns=["data_ref", "valor_ref", "idx_pag", "idx_ext", "rule"])

    # pendências + diagnóstico
    unmatched_pag = P.loc[~P["_idx_pag"].isin(used_pag_idx)].copy()
    unmatched_ext = E.loc[~E["_idx_ext"].isin(used_ext_idx)].copy()

    detalhes: List[dict] = []
    if not unmatched_pag.empty:
        for _, row in unmatched_pag.iterrows():
            motivos = explain_mismatch(row, E, params)
            detalhes.append(
                {
                    "tipo": "pagamento",
                    "linha": int(_row_idx(row, "_idx_pag")),
                    "fornecedor": str(row.get(cols_pag.get("fornecedor", ""), "")),
                    "data": row.get("_data"),
                    "valor": _safe_float(row.get("_valor", 0.0)),
                    "motivos": "; ".join(motivos),
                }
            )

    total_pag = len(P)
    total_ext = len(E)
    matched_count = len(matches_df)
    pct = round((matched_count / total_pag * 100), 1) if total_pag else 0.0

    pend_data: Dict[str, Any] = {
        "unmatched_pagamentos": unmatched_pag,
        "unmatched_extrato": unmatched_ext,
        "detalhes": detalhes,
        "stats": {
            "total_pagamentos": total_pag,
            "total_saidas": total_ext,
            "matches": matched_count,
            "pct_conciliacao": pct,
            "pendentes_pagamento": len(unmatched_pag),
            "pendentes_extrato": len(unmatched_ext),
        },
    }

    if pct < 85:
        logger.warning("Taxa de conciliação baixa: %.1f%% (esperado > 95%%)", pct)
        pend_data["alerta_qualidade"] = (
            f"Taxa de conciliação de {pct:.1f}% está abaixo do esperado (>95%). "
            "Verifique se a data dos pagamentos foi interpretada corretamente e se os valores do extrato são negativos (saídas)."
        )

    logger.info(
        "Matching concluído | pagamentos=%d saídas=%d matches=%d (%.1f%%) pend_pag=%d pend_ext=%d",
        total_pag, total_ext, matched_count, pct, len(unmatched_pag), len(unmatched_ext),
    )

    return matches_df, pend_data
