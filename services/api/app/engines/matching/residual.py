"""Residual cause classifier (3e): why a strong match doesn't net to zero.

Most suggestions are correct pairs that miss the 0.5% tolerance because of a legitimate residual. Policy keeps
them with a person, but the person shouldn't have to work out the cause each time. Deterministic and explainable
on purpose: every label states the arithmetic that justifies it. The local LLM judge only writes the reviewer
note on top (and is measured against this baseline).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engines.benchmark.model import Line

WHT_RATES = (0.05, 0.10, 0.125, 0.15, 0.20, 0.25, 0.30)
FEES_USD = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 100)
WHT_TOL = 0.0005  # residual / gross within 0.05 pp of a statutory rate
FEE_TOL_USD = 0.75
FX_MAX = 0.01  # FX source differences beyond 1% are not "just a rate difference"


@dataclass(frozen=True)
class Residual:
    cause: str  # withholding_tax | bank_fee | fx_rate_difference | rounding | unexplained
    label: str  # short, for chips and bulk actions ("Withholding tax 10%")
    detail: str  # the arithmetic, for the reviewer and the audit trail
    residual_usd: float
    residual_pct: float


def classify(a: Line, b: Line) -> Residual:
    gross = max(abs(a.amount_usd), abs(b.amount_usd))
    residual = abs(a.amount_usd + b.amount_usd)
    pct = residual / gross if gross else 0.0
    if residual < 0.01:
        return Residual("rounding", "Nets to zero", "No residual.", residual, pct)
    for rate in WHT_RATES:
        if abs(pct - rate) <= WHT_TOL:
            short = "receiver" if abs(b.amount_usd) < abs(a.amount_usd) else "payer"
            return Residual(
                "withholding_tax",
                f"Withholding tax {100 * rate:g}%",
                f"Residual ${residual:,.2f} is {100 * pct:.2f}% of ${gross:,.2f}: the statutory {100 * rate:g}% "
                f"withholding rate (the {short} side is net of tax).",
                residual,
                pct,
            )
    fx_fits = a.currency != b.currency and pct <= FX_MAX
    for fee in FEES_USD:
        if abs(residual - fee) <= FEE_TOL_USD and fx_fits:
            # Both stories fit the arithmetic (e.g. $25 on $10,000 is also a 0.25% rate gap): say so, don't guess.
            return Residual(
                "fee_or_fx",
                f"Bank fee ${fee} or FX {100 * pct:.2f}%",
                f"Residual ${residual:,.2f} equals a ${fee} transfer fee and is also a {100 * pct:.2f}% "
                f"{a.currency}/{b.currency} rate difference: check the bank statement.",
                residual,
                pct,
            )
        if abs(residual - fee) <= FEE_TOL_USD:
            return Residual(
                "bank_fee",
                f"Bank fee ${fee}",
                f"Residual ${residual:,.2f} matches a ${fee} transfer fee deducted in transit.",
                residual,
                pct,
            )
    if a.currency != b.currency and pct <= FX_MAX:
        return Residual(
            "fx_rate_difference",
            f"FX difference {100 * pct:.2f}%",
            f"{a.currency}/{b.currency} booked at different rate sources: {100 * pct:.2f}% (${residual:,.2f}).",
            residual,
            pct,
        )
    if pct <= 0.0005 or residual <= 1.0:
        return Residual("rounding", "Rounding", f"Residual ${residual:,.2f} is rounding.", residual, pct)
    return Residual(
        "unexplained",
        "Unexplained residual",
        f"Residual ${residual:,.2f} ({100 * pct:.2f}%) matches no fee, tax or FX pattern: investigate.",
        residual,
        pct,
    )
