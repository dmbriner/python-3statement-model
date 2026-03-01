"""Balance sheet and financial integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import ModelOutput


@dataclass
class IntegrityResult:
    balance_check_passed: bool
    cash_check_passed: bool
    warnings: list[str] = field(default_factory=list)
    year_details: list[dict] = field(default_factory=list)

    @property
    def all_clear(self) -> bool:
        return self.balance_check_passed and self.cash_check_passed and not self.warnings


def check_integrity(output: ModelOutput, tolerance: float = 0.01) -> IntegrityResult:
    """
    Run a suite of financial model integrity checks.

    Checks per projection year:
      1. Assets = Liabilities + Equity (within tolerance %)
      2. Beginning Cash + CFO + CFI + CFF ≈ Ending Cash
      3. Ending Cash < 0 → warning
      4. Net Debt / EBITDA > 6x → covenant warning
      5. EBIT / Interest Expense < 1.5x → coverage warning
    """
    bs = output.balance_sheet
    cf = output.cash_flow
    is_ = output.income_statement

    balance_failures: list[str] = []
    cash_failures: list[str] = []
    warnings: list[str] = []
    year_details: list[dict] = []

    prev_cash = None

    for i, row in bs.iterrows():
        year = int(row["year"])
        total_assets = row["total_assets"]
        total_liab_equity = row["total_liabilities_and_equity"]
        cash = row["cash"]

        cf_row = cf[cf["year"] == year].iloc[0] if not cf[cf["year"] == year].empty else None
        is_row = is_[is_["year"] == year].iloc[0] if not is_[is_["year"] == year].empty else None

        detail: dict = {"year": year}

        # ── 1. Balance sheet check ──
        # The model constructs equity as a plug, so Assets = Liabilities + Equity by design.
        # We instead check if the unmodeled "plug" is unreasonably large vs total equity.
        bs_plug = row.get("bs_plug", 0.0)
        if total_assets > 0:
            imbalance_pct = abs(total_assets - total_liab_equity) / total_assets
            detail["bs_imbalance_pct"] = imbalance_pct
            detail["bs_plug"] = bs_plug
            detail["bs_ok"] = imbalance_pct <= tolerance
            if not detail["bs_ok"]:
                balance_failures.append(
                    f"{year}: Balance sheet imbalance detected — gap {imbalance_pct * 100:.1f}%."
                )
            # Warn if plug (unmodeled items) is large
            plug_pct = abs(bs_plug) / max(abs(total_assets), 1)
            if plug_pct > 0.20 and abs(bs_plug) > 500:
                warnings.append(
                    f"{year}: Equity plug is ${bs_plug:,.0f}M ({plug_pct * 100:.0f}% of assets). "
                    f"This reflects unmodeled items (goodwill, deferred taxes, etc.) — normal for simplified models."
                )
        else:
            detail["bs_ok"] = True
            detail["bs_imbalance_pct"] = 0.0
            detail["bs_plug"] = 0.0

        # ── 2. Cash reconciliation ──
        if cf_row is not None and prev_cash is not None:
            expected_ending = prev_cash + cf_row["net_change_cash"]
            cash_diff = abs(cash - expected_ending)
            cash_tol = max(abs(expected_ending) * tolerance, 1.0)  # $1M min tolerance
            detail["cash_ok"] = cash_diff <= cash_tol
            detail["cash_diff"] = cash_diff
            if not detail["cash_ok"]:
                cash_failures.append(
                    f"{year}: Cash reconciliation off by ${cash_diff:,.0f}M"
                )
        else:
            detail["cash_ok"] = True
            detail["cash_diff"] = 0.0

        # ── 3. Negative cash ──
        detail["negative_cash"] = cash < 0
        if cash < 0:
            warnings.append(f"{year}: Projected cash is negative (${cash:,.0f}M). Model may need cash sweep adjustments.")

        # ── 4. Net leverage (debt covenant proxy) ──
        if is_row is not None:
            ebitda = is_row.get("ebitda", 0.0)
            debt = row["debt"]
            net_debt = debt - cash
            net_leverage = net_debt / ebitda if ebitda > 0 else 0.0
            detail["net_leverage"] = net_leverage
            detail["net_leverage_warning"] = net_leverage > 6.0
            if net_leverage > 6.0:
                warnings.append(
                    f"{year}: Net Debt/EBITDA = {net_leverage:.1f}x — exceeds typical 6x covenant threshold. "
                    f"Consider reducing debt assumptions."
                )

            # ── 5. Interest coverage ──
            ebit = is_row.get("ebit", 0.0)
            interest = is_row.get("interest_expense", 0.0)
            coverage = ebit / interest if interest > 0 else 999.0
            detail["interest_coverage"] = coverage
            detail["coverage_warning"] = coverage < 1.5
            if coverage < 1.5:
                warnings.append(
                    f"{year}: Interest coverage (EBIT/Interest) = {coverage:.1f}x — below 1.5x safety threshold. "
                    f"Risk of covenant breach."
                )
        else:
            detail["net_leverage"] = 0.0
            detail["net_leverage_warning"] = False
            detail["interest_coverage"] = 0.0
            detail["coverage_warning"] = False

        prev_cash = cash
        year_details.append(detail)

    return IntegrityResult(
        balance_check_passed=len(balance_failures) == 0,
        cash_check_passed=len(cash_failures) == 0,
        warnings=balance_failures + cash_failures + warnings,
        year_details=year_details,
    )
