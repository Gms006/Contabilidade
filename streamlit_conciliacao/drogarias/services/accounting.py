# app/services/accounting.py
from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
import unicodedata


# ---------------- configurações de tarifa ----------------
# Tarifas mapeadas por **código contábil do fornecedor** (sempre string)
TARIFA_POR_CONTA_FORNECEDOR: Dict[str, float] = {
    "271": 1.39,   # DISTRIBUIDORA DE MEDICAMENTOS SANTA CRUZ
    "272": 1.79,   # SERVIMED COMERCIAL LTDA
    "274": 1.39,   # DROGA CENTER DISTRIBUIDORA LTDA
    "291": 1.39,   # PANPHARMA DISTRIBUIDORA DE MEDICAMENTOS
}
# Conta contábil usada quando há **apenas** tarifa (sem multa).
# Quando houver multa **e** tarifa, a tarifa será somada na conta de MULTAS E JUROS
CONTA_TARIFA_SOMENTE = "316"


# ---------------- utils ----------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _clean_text(x: object) -> str:
    if pd.isna(x):
        return ""
    s = _strip_accents(str(x)).strip().casefold()
    return "".join(ch for ch in s if ch.isalnum() or ch.isspace())

def _safe_text(x: object) -> str:
    if x is None:
        return ""
    sx = str(x).strip()
    if sx == "" or sx.lower() in {"nan", "none", "nat"}:
        return ""
    return sx

def _fmt_date_pt(d) -> str:
    ts = pd.to_datetime(d, errors="coerce")
    if pd.isna(ts):
        return ""
    return ts.strftime("%d/%m/%Y")

def _fmt_val(v: float) -> str:
    return f"{float(v):0.2f}".replace(".", ",")

def _fmt_conta(conta_code) -> str:
    if pd.isna(conta_code) or conta_code is None:
        return ""
    try:
        return str(int(float(str(conta_code).replace(",", "."))))
    except Exception:
        s = str(conta_code)
        s = s.split(",")[0].split(".")[0]
        return s.strip()

def _fmt_hist(x: object) -> str:
    sx = _safe_text(x)
    if sx == "":
        return ""
    try:
        return str(int(float(str(sx).replace(",", "."))))
    except Exception:
        return sx

def _fmt_nf(x: object) -> str:
    sx = _safe_text(x)
    if sx == "":
        return ""
    try:
        return str(int(float(str(sx).replace(",", "."))))
    except Exception:
        return sx

def _nz(x, default=0.0) -> float:
    try:
        v = float(x)
        if pd.isna(v):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


# ---------------- maps (plano de contas) ----------------
def build_maps(contas_df: pd.DataFrame) -> dict:
    c = contas_df.copy()
    c["_nome_norm"] = c["NOME"].map(_clean_text)
    c["_class_norm"] = c["CLASSIFICAÇÃO"].map(_clean_text)

    def as_map(name: str):
        sub = c[c["_class_norm"] == _clean_text(name)]
        return {
            r["_nome_norm"]: (str(r["CONTAS CONTABEIS"]), _fmt_hist(r.get("HISTORICO", "")))
            for _, r in sub.iterrows()
        }

    by_code = {
        _fmt_conta(r["CONTAS CONTABEIS"]): _fmt_hist(r.get("HISTORICO", ""))
        for _, r in c.iterrows()
    }

    return {
        "fornecedor": as_map("FORNECEDOR"),
        "cliente": as_map("CLIENTE"),
        "caixa_eq": as_map("CAIXA E EQUIVALENTES"),
        "multas_juros": as_map("MULTAS E JUROS"),
        "descontos": as_map("DESCONTOS"),
        "by_code": by_code,
    }

def _find_party_account(name: str, maps: dict) -> Tuple[str | None, str | None, str]:
    """
    Busca exata; se não achar, faz fuzzy (limiar 0.85) em FORNECEDOR e CLIENTE.
    Retorna (conta, historico, tipo), onde tipo ∈ {'FORNECEDOR','CLIENTE',''}.
    """
    from difflib import SequenceMatcher

    nn = _clean_text(name)
    # 1) Exata
    if nn in maps.get("fornecedor", {}):
        c, h = maps["fornecedor"][nn]
        return c, h, "FORNECEDOR"
    if nn in maps.get("cliente", {}):
        c, h = maps["cliente"][nn]
        return c, h, "CLIENTE"

    # 2) Aproximada
    def _best_match(target: str, candidates: dict, threshold: float = 0.85) -> Tuple[str | None, float]:
        best_key: str | None = None
        best_ratio: float = 0.0
        for cand in candidates.keys():
            ratio = SequenceMatcher(None, target, cand).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = cand
        if best_key is not None and best_ratio >= threshold:
            return best_key, best_ratio
        return None, 0.0

    key_for, ratio_for = _best_match(nn, maps.get("fornecedor", {}))
    key_cli, ratio_cli = _best_match(nn, maps.get("cliente", {}))

    if ratio_for > 0 or ratio_cli > 0:
        if ratio_for >= ratio_cli and key_for is not None:
            c, h = maps["fornecedor"][key_for]
            return c, h, "FORNECEDOR"
        if key_cli is not None:
            c, h = maps["cliente"][key_cli]
            return c, h, "CLIENTE"

    return None, None, ""

def _pick_bank_account(bank_name: str | None, maps: dict) -> str | None:
    if not bank_name:
        return None
    nn = _clean_text(bank_name)
    return (maps["caixa_eq"].get(nn) or (None, None))[0]

def _hist_for_account_code(code: str | None, maps: dict) -> str:
    if not code:
        return ""
    return maps.get("by_code", {}).get(_fmt_conta(code), "")


# ---------------- função auxiliar para encontrar pagamentos que exigem conta 316 ----------------
def _get_pagamentos_exigem_316(
    df_pag: pd.DataFrame,
    cols_pag: Dict[str, str],
    maps: dict
) -> List[Dict[str, str]]:
    """
    Retorna lista de dicionários com informações dos pagamentos que exigem conta 316
    (fornecedores com tarifa configurada E sem multa)
    """
    pagamentos_316 = []
    for _, rp in df_pag.iterrows():
        nome = _safe_text(rp.get(cols_pag.get("fornecedor", ""), ""))
        if not nome:
            continue
        conta_for, _, tipo = _find_party_account(nome, maps)
        if tipo != "FORNECEDOR" or not conta_for:
            continue
        code = _fmt_conta(conta_for)
        tarifa = TARIFA_POR_CONTA_FORNECEDOR.get(code, 0.0)
        if tarifa <= 0:
            continue
        # Se há multa, a tarifa vai para multas/juros, não precisa 316
        multa = _nz(rp.get("_multa"))
        if multa > 0:
            continue

        pagamentos_316.append({
            "data": _fmt_date_pt(rp.get("_data")),
            "fornecedor": nome,
            "nf": _safe_text(rp.get(cols_pag.get("doc", ""), "")),
            "conta_contabil": code,
            "valor_tarifa": _fmt_val(tarifa),
        })
    return pagamentos_316


# ---------------- validação antes de exportar ----------------
def validate_accounts(
    df_pag: pd.DataFrame,
    cols_pag: Dict[str, str],
    contas_df: pd.DataFrame,
    banco_padrao: str | None,
    conta_caixa_nome: str | None,
    df_ext_entradas: pd.DataFrame | None = None,
    df_ext_saidas: pd.DataFrame | None = None,   # opcional: validar nomes vindos do extrato
) -> dict:
    maps = build_maps(contas_df)

    # Fornecedores faltantes (pagamentos e saídas do extrato)
    fornecedores_faltantes: List[str] = []
    if cols_pag.get("fornecedor") in df_pag:
        for name in sorted(set(df_pag[cols_pag["fornecedor"]].astype(str))):
            conta, _, _ = _find_party_account(name, maps)
            if not conta:
                fornecedores_faltantes.append(name)

    if df_ext_saidas is not None and not df_ext_saidas.empty:
        for nn in sorted(set(df_ext_saidas.get("_hist_norm", pd.Series(dtype=str)))):
            if nn and nn not in maps["fornecedor"]:
                orig = df_ext_saidas.loc[df_ext_saidas["_hist_norm"] == nn].iloc[0].get("HISTÓRICO", "")
                fornecedores_faltantes.append(str(orig))

    # Clientes faltantes (entradas do extrato)
    clientes_faltantes: List[str] = []
    if df_ext_entradas is not None and not df_ext_entradas.empty:
        for nn in sorted(set(df_ext_entradas.get("_hist_norm", pd.Series(dtype=str)))):
            if nn and nn not in maps["cliente"]:
                orig = df_ext_entradas.loc[df_ext_entradas["_hist_norm"] == nn].iloc[0].get("HISTÓRICO", "")
                clientes_faltantes.append(str(orig))

    banco_padrao_faltante = None
    if banco_padrao and not _pick_bank_account(banco_padrao, maps):
        banco_padrao_faltante = banco_padrao

    caixa_faltante = None
    if conta_caixa_nome and not _pick_bank_account(conta_caixa_nome, maps):
        caixa_faltante = conta_caixa_nome

    multa_s = df_pag.get("_multa", pd.Series([], dtype=float))
    desc_s = df_pag.get("_descontos", pd.Series([], dtype=float))

    precisa_multas_juros = pd.to_numeric(multa_s, errors="coerce").fillna(0).ne(0).any()
    precisa_descontos = pd.to_numeric(desc_s, errors="coerce").fillna(0).ne(0).any()

    # Verificar se conta 316 existe no plano
    conta_316_existe = _fmt_conta(CONTA_TARIFA_SOMENTE) in maps["by_code"]
    pagamentos_exigem_316 = _get_pagamentos_exigem_316(df_pag, cols_pag, maps)
    precisa_tarifa_316 = len(pagamentos_exigem_316) > 0 and not conta_316_existe

    partes_faltantes = sorted(set(fornecedores_faltantes) | set(clientes_faltantes))
    total_problemas = 0
    total_problemas += len(fornecedores_faltantes)
    total_problemas += len(clientes_faltantes)
    if banco_padrao_faltante:
        total_problemas += 1
    if caixa_faltante:
        total_problemas += 1
    if bool(precisa_multas_juros and not maps["multas_juros"]):
        total_problemas += 1
    if bool(precisa_descontos and not maps["descontos"]):
        total_problemas += 1
    if precisa_tarifa_316:
        total_problemas += 1

    return {
        "fornecedores_faltantes": fornecedores_faltantes,
        "clientes_faltantes": clientes_faltantes,
        "partes_faltantes": partes_faltantes,
        "banco_padrao_faltante": banco_padrao_faltante,
        "caixa_faltante": caixa_faltante,
        "precisa_multas_juros": bool(precisa_multas_juros and not maps["multas_juros"]),
        "precisa_descontos": bool(precisa_descontos and not maps["descontos"]),
        "precisa_tarifa": precisa_tarifa_316,
        "pagamentos_exigem_316": pagamentos_exigem_316,
        "conta_316_existe": conta_316_existe,
        "total_problemas": total_problemas,
        "tem_bloqueadores": any([
            fornecedores_faltantes, clientes_faltantes,
            banco_padrao_faltante, caixa_faltante,
            (precisa_multas_juros and not maps["multas_juros"]),
            (precisa_descontos and not maps["descontos"]),
            precisa_tarifa_316,
        ]),
    }


# ---------------- helpers de emissão ----------------
_COLS_OUT = [
    "Lote", "Data", "CodHistorico", "Fornecedor", "NF", "Classificaçao",
    "VALOR ORG", "MULTA E JUROS", "DESCONTOS", "Valor pago", "Crédito", "Débito",
]

def _hist_from_accounts(row: dict, maps: dict, row_kind: str) -> str:
    """
    CodHistorico:
      - pagamento_caixa: '1' (exceção exigida).
      - deposito_extrato: histórico da conta de CRÉDITO (CLIENTE); se vazio, da conta de DÉBITO (banco).
      - demais: histórico do DÉBITO; se vazio, do CRÉDITO.
    """
    if row_kind == "pagamento_caixa":
        return "1"

    if row_kind == "deposito_extrato":
        h = _hist_for_account_code(row.get("Crédito"), maps)  # cliente
        if _safe_text(h) != "":
            return _fmt_hist(h)
        h = _hist_for_account_code(row.get("Débito"), maps)   # banco (fallback)
        return _fmt_hist(h)

    # padrão
    for code in (row.get("Débito"), row.get("Crédito")):
        h = _hist_for_account_code(code, maps)
        if _safe_text(h) != "":
            return _fmt_hist(h)
    return ""

def _add_row(
    out: list,
    base: dict,
    maps: dict,
    row_kind: str = "",
    cod_hist_override: str | None = None,
):
    row = {k: base.get(k, "") for k in _COLS_OUT}

    if row_kind in {"saque_extrato", "deposito_extrato"}:
        row["Fornecedor"] = ""  # linhas do extrato não exibem fornecedor

    row["NF"] = _fmt_nf(row.get("NF", ""))

    if row.get("Crédito"):
        row["Crédito"] = _fmt_conta(row["Crédito"])
    if row.get("Débito"):
        row["Débito"] = _fmt_conta(row["Débito"])

    if cod_hist_override is not None and _safe_text(cod_hist_override) != "":
        row["CodHistorico"] = _fmt_hist(cod_hist_override)
    else:
        row["CodHistorico"] = _hist_from_accounts(row, maps, row_kind)

    out.append(row)

def _ensure_valores(rp: pd.Series, inferir_descontos: bool = True) -> Tuple[float, float, float]:
    val_pago = _nz(rp.get("_valor"))
    val_org = rp.get("_valor_original")
    multa = _nz(rp.get("_multa"))
    desc = _nz(rp.get("_descontos"))

    if pd.isna(val_org) or val_org in ("", None) or _nz(val_org) == 0:
        val_org = val_pago + desc - multa
    else:
        val_org = _nz(val_org)

    if inferir_descontos and desc == 0:
        calc = round(val_org + multa - val_pago, 2)
        if calc > 0:
            desc = calc

    return float(val_org), float(multa), float(desc)


# ---------------- lógica de tarifa (ajuste de valores) ----------------
def _aplicar_tarifa(conta_for: str | None, val_org: float, multa: float) -> Tuple[float, float, float, bool]:
    """
    Recebe conta do fornecedor, valor original e multa.
    Retorna (val_org_ajustado, multa_ajustada, tarifa, tem_tarifa).
    Regras:
      - Se a conta do fornecedor tiver tarifa configurada:
          * val_org -= tarifa (nunca negativo)
          * Se multa > 0  -> multa += tarifa (usar conta de MULTAS E JUROS; sem linha 316)
          * Se multa == 0 -> criar linha separada em 316 (tratado nos emissores)
    """
    if not conta_for:
        return val_org, multa, 0.0, False
    code = _fmt_conta(conta_for)
    tarifa = TARIFA_POR_CONTA_FORNECEDOR.get(code, 0.0)
    if tarifa <= 0:
        return val_org, multa, 0.0, False

    # Ajusta valor original (nunca negativo)
    val_org_aj = round(val_org - tarifa, 2)
    if val_org_aj < 0:
        val_org_aj = 0.0

    if multa > 0:
        # Com multa: soma tarifa na multa
        multa_aj = round(multa + tarifa, 2)
        return val_org_aj, multa_aj, tarifa, True
    else:
        # Sem multa: tarifa vai para linha separada (conta 316)
        return val_org_aj, multa, tarifa, True


# ---------------- geração do CSV ----------------
def build_entries(
    matches_df: pd.DataFrame,
    df_pag: pd.DataFrame,
    cols_pag: Dict[str, str],
    df_ext_saidas: pd.DataFrame,
    cols_ext: Dict[str, str],   # não usado aqui, mas mantido por compatibilidade
    contas_df: pd.DataFrame,
    df_ext_entradas: pd.DataFrame | None = None,
    banco_padrao: str | None = "Sicoob",
    conta_caixa_nome: str | None = "Caixa",
    gerar_pendentes: bool = True,
    inferir_descontos: bool = True,
) -> pd.DataFrame:

    maps = build_maps(contas_df)
    conta_banco = _pick_bank_account(banco_padrao, maps)
    conta_caixa = _pick_bank_account(conta_caixa_nome, maps)
    if not conta_banco:
        raise ValueError(f"Banco padrão '{banco_padrao}' não encontrado em CAIXA E EQUIVALENTES.")
    if not conta_caixa:
        raise ValueError(f"Conta Caixa '{conta_caixa_nome}' não encontrada em CAIXA E EQUIVALENTES.")

    # Verificação prévia: se há pagamentos que exigem conta 316 e ela não existe
    pagamentos_exigem_316 = _get_pagamentos_exigem_316(df_pag, cols_pag, maps)
    conta_316_existe = _fmt_conta(CONTA_TARIFA_SOMENTE) in maps["by_code"]
    if pagamentos_exigem_316 and not conta_316_existe:
        raise ValueError(
            f"Existem pagamentos com TARIFA que exigem a conta '{CONTA_TARIFA_SOMENTE}', "
            f"mas ela não está cadastrada no plano de contas. "
            f"Cadastre-a na classificação 'MULTAS E JUROS'."
        )

    out: List[dict] = []
    P = df_pag.set_index("_idx_pag", drop=False)

    # ===== 1) Conciliados (pagamento pelo BANCO) =====
    for _, m in matches_df.iterrows():
        lote = "1"
        for ip in m["idx_pag"]:
            rp = P.loc[ip]
            nome = _safe_text(rp.get(cols_pag["fornecedor"], ""))
            nf = _safe_text(rp.get(cols_pag.get("doc", ""), ""))
            val_pago = _nz(rp.get("_valor"))
            val_org, multa, desc = _ensure_valores(rp, inferir_descontos=inferir_descontos)

            conta_for, hist_parte, tipo = _find_party_account(nome, maps)
            if tipo != "FORNECEDOR" or not conta_for:
                raise ValueError(f"Fornecedor '{nome}' não está cadastrado como FORNECEDOR.")

            # ---- aplicar tarifa
            val_org, multa, tarifa, tem_tarifa = _aplicar_tarifa(conta_for, val_org, multa)
            data_ref = rp["_data"]

            has_desc = (desc != 0)
            has_multa = (multa != 0)
            has_tarifa_somente = (tem_tarifa and _nz(rp.get("_multa")) == 0)

            if not has_desc and not has_multa and not has_tarifa_somente:
                # linha única
                _add_row(
                    out,
                    {
                        "Lote": lote,
                        "Data": _fmt_date_pt(data_ref),
                        "Fornecedor": nome,
                        "NF": nf,
                        "Classificaçao": "",
                        "VALOR ORG": _fmt_val(val_org),
                        "Valor pago": _fmt_val(val_pago),
                        "Crédito": conta_banco,
                        "Débito": conta_for,
                    },
                    maps,
                    row_kind="pagamento_banco",
                )
            else:
                # 1) valor original (ajustado)
                _add_row(
                    out,
                    {
                        "Lote": lote,
                        "Data": _fmt_date_pt(data_ref),
                        "Fornecedor": nome,
                        "NF": nf,
                        "Classificaçao": "",
                        "VALOR ORG": _fmt_val(val_org),
                        "Débito": conta_for,
                    },
                    maps,
                    row_kind="pagamento_banco",
                )
                # 2) descontos
                if has_desc:
                    if not maps["descontos"]:
                        raise ValueError("Há descontos mas não existe conta em 'DESCONTOS' no plano.")
                    conta_desc, _ = next(iter(maps["descontos"].values()))
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "DESCONTOS": _fmt_val(desc),
                            "Crédito": conta_desc,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                # 3) tarifa (somente quando **não** há multa)
                if has_tarifa_somente:
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "MULTA E JUROS": _fmt_val(tarifa),
                            "Débito": CONTA_TARIFA_SOMENTE,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                # 4) multas/juros (pode ser multa original OU multa+tarifa)
                if has_multa:
                    if not maps["multas_juros"]:
                        raise ValueError("Há multas/juros mas não existe conta em 'MULTAS E JUROS' no plano.")
                    conta_mj, _ = next(iter(maps["multas_juros"].values()))
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "MULTA E JUROS": _fmt_val(multa),
                            "Débito": conta_mj,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                # 5) pagamento (crédito banco) — histórico do fornecedor
                hist_override = hist_parte or _hist_for_account_code(conta_for, maps)
                _add_row(
                    out,
                    {
                        "Data": _fmt_date_pt(rp["_data"]),
                        "Fornecedor": nome,
                        "NF": _fmt_nf(nf),
                        "Valor pago": _fmt_val(val_pago),
                        "Crédito": conta_banco,
                    },
                    maps,
                    row_kind="pagamento_banco",
                    cod_hist_override=hist_override,
                )

        # fim do loop de pagamentos do match
        lote = ""

    # ===== 2) Pendentes =====
    if gerar_pendentes:
        # 2a) Pagamentos sem saída => CAIXA (Crédito=Caixa; Débito=Fornecedor)
        used_p = set(i for ids in matches_df["idx_pag"] for i in ids) if not matches_df.empty else set()
        pend_pag = df_pag.loc[~df_pag["_idx_pag"].isin(used_p)].copy()

        for _, rp in pend_pag.iterrows():
            nome = _safe_text(rp.get(cols_pag["fornecedor"], ""))
            nf = _safe_text(rp.get(cols_pag.get("doc", ""), ""))
            val_pago = _nz(rp.get("_valor"))
            val_org, multa, desc = _ensure_valores(rp, inferir_descontos=inferir_descontos)

            conta_for, hist_parte, tipo_part = _find_party_account(nome, maps)
            if not conta_for or tipo_part != "FORNECEDOR":
                raise ValueError(f"Fornecedor '{nome}' não está cadastrado no plano de contas como FORNECEDOR.")

            # aplicar tarifa
            val_org, multa, tarifa, tem_tarifa = _aplicar_tarifa(conta_for, val_org, multa)
            has_desc = (desc != 0)
            has_multa = (multa != 0)
            has_tarifa_somente = (tem_tarifa and _nz(rp.get("_multa")) == 0)

            if not has_desc and not has_multa and not has_tarifa_somente:
                _add_row(
                    out,
                    {
                        "Lote": "1",
                        "Data": _fmt_date_pt(rp["_data"]),
                        "Fornecedor": nome,
                        "NF": _fmt_nf(nf),
                        "Classificaçao": "",
                        "VALOR ORG": _fmt_val(val_org),
                        "Valor pago": _fmt_val(val_pago),
                        "Crédito": conta_caixa,
                        "Débito": conta_for,
                    },
                    maps,
                    row_kind="pagamento_caixa",
                )
            else:
                _add_row(
                    out,
                    {
                        "Lote": "1",
                        "Data": _fmt_date_pt(rp["_data"]),
                        "Fornecedor": nome,
                        "NF": _fmt_nf(nf),
                        "Classificaçao": "",
                        "VALOR ORG": _fmt_val(val_org),
                        "Débito": conta_for,
                    },
                    maps,
                    row_kind="pagamento_caixa",
                )
                if has_desc:
                    if not maps["descontos"]:
                        raise ValueError("Há descontos mas não existe conta em 'DESCONTOS' no plano.")
                    conta_desc, _ = next(iter(maps["descontos"].values()))
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "DESCONTOS": _fmt_val(desc),
                            "Crédito": conta_desc,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                if has_tarifa_somente:
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "MULTA E JUROS": _fmt_val(tarifa),
                            "Débito": CONTA_TARIFA_SOMENTE,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                if has_multa:
                    if not maps["multas_juros"]:
                        raise ValueError("Há multas/juros mas não existe conta em 'MULTAS E JUROS' no plano.")
                    conta_mj, _ = next(iter(maps["multas_juros"].values()))
                    _add_row(
                        out,
                        {
                            "Data": _fmt_date_pt(rp["_data"]),
                            "Fornecedor": nome,
                            "NF": _fmt_nf(nf),
                            "MULTA E JUROS": _fmt_val(multa),
                            "Débito": conta_mj,
                        },
                        maps,
                        row_kind="pagamento_caixa",
                    )
                _add_row(
                    out,
                    {
                        "Data": _fmt_date_pt(rp["_data"]),
                        "Fornecedor": nome,
                        "NF": _fmt_nf(nf),
                        "Valor pago": _fmt_val(val_pago),
                        "Crédito": conta_caixa,
                    },
                    maps,
                    row_kind="pagamento_caixa",
                )

    # ===== 3) Saídas do extrato sem pagamento (Banco × Conta alvo) =====
    used_e = set(i for ids in matches_df["idx_ext"] for i in ids) if not matches_df.empty else set()
    pend_ext = df_ext_saidas.loc[~df_ext_saidas["_idx_ext"].isin(used_e)]

    for _, re in pend_ext.iterrows():
        valor = _nz(re["_valor"])
        hist_norm = _clean_text(re.get("_hist_norm", ""))

        if hist_norm in maps["fornecedor"]:
            conta_for, hist_for = maps["fornecedor"][hist_norm]
            cod_hist = hist_for
        elif maps["multas_juros"]:
            conta_for, cod_hist = next(iter(maps["multas_juros"].values()))
        else:
            conta_for, cod_hist = "", ""

        _add_row(
            out,
            {
                "Lote": "1",
                "Data": _fmt_date_pt(re["_data"]),
                "NF": "",
                "VALOR ORG": _fmt_val(valor),
                "Valor pago": _fmt_val(valor),
                "Crédito": conta_banco,   # CRÉDITO banco
                "Débito": conta_for,      # DÉBITO conta alvo (fornecedor/despesa)
            },
            maps,
            row_kind="saque_extrato",
            cod_hist_override=cod_hist,  # histórico da conta alvo
        )

    # ===== 4) Entradas (depósitos) — CRÉDITO = Cliente ; DÉBITO = Banco =====
    if df_ext_entradas is not None and not df_ext_entradas.empty:
        for _, re in df_ext_entradas.iterrows():
            valor = _nz(re["_valor"])
            hist_norm = _clean_text(re.get("_hist_norm", ""))

            if hist_norm in maps["cliente"]:
                conta_cli, hist_cli = maps["cliente"][hist_norm]  # histórico correto do CLIENTE
            else:
                conta_cli, hist_cli = "", ""

            _add_row(
                out,
                {
                    "Lote": "1",
                    "Data": _fmt_date_pt(re["_data"]),
                    "NF": "",
                    "VALOR ORG": _fmt_val(valor),
                    "Valor pago": _fmt_val(valor),
                    "Crédito": conta_cli,     # CRÉDITO = CLIENTE
                    "Débito": conta_banco,    # DÉBITO  = BANCO
                },
                maps,
                row_kind="deposito_extrato",
                cod_hist_override=hist_cli,  # força histórico do CLIENTE
            )

    # ===== DataFrame final =====
    df_out = pd.DataFrame(out, columns=_COLS_OUT)

    # Sanitização final
    if not df_out.empty:
        df_out["CodHistorico"] = df_out["CodHistorico"].map(_fmt_hist)
        df_out["NF"] = df_out["NF"].map(_fmt_nf)

        # Só preencher Crédito=Caixa em linhas de pagamento pelo CAIXA com Valor pago
        caixa_code = _fmt_conta(conta_caixa)
        mask_caixa = df_out["CodHistorico"] == "1"
        mask_valor_pago = df_out["Valor pago"].astype(str).str.strip() != ""
        df_out.loc[mask_caixa & mask_valor_pago & (df_out["Crédito"] == ""), "Crédito"] = caixa_code

    return df_out
