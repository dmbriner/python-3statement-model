from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineItemMeta:
    label: str
    definition: str
    formula: str
    unit: str = "$M"


LINE_ITEM_META: dict[str, LineItemMeta] = {
    "revenue": LineItemMeta("Revenue", "Total sales recognized in the period.", "Price x Units sold"),
    "cogs": LineItemMeta("COGS", "Direct costs required to deliver the product or service.", "Revenue - Gross Profit"),
    "gross_profit": LineItemMeta("Gross Profit", "Profit after direct production or service costs.", "Revenue - COGS"),
    "opex": LineItemMeta("Operating Expenses", "Selling, general, administrative, and other operating costs.", "Revenue x OpEx %"),
    "ebitda": LineItemMeta("EBITDA", "Operating profit before depreciation and amortization.", "Gross Profit - Operating Expenses"),
    "depreciation": LineItemMeta("Depreciation", "Non-cash expense for using long-lived assets over time.", "Beginning PP&E x Depreciation %"),
    "ebit": LineItemMeta("EBIT", "Operating profit after depreciation.", "EBITDA - Depreciation"),
    "interest_expense": LineItemMeta("Interest Expense", "Cost of debt financing.", "Average Debt x Interest Rate"),
    "ebt": LineItemMeta("EBT", "Earnings before taxes.", "EBIT - Interest Expense"),
    "taxes": LineItemMeta("Taxes", "Income taxes on pre-tax profit.", "max(EBT, 0) x Tax Rate"),
    "net_income": LineItemMeta("Net Income", "Profit attributable to equity holders after interest and taxes.", "EBT - Taxes"),
    "eps": LineItemMeta("EPS", "Earnings per share.", "Net Income / Shares Outstanding", "$/share"),
    "cash": LineItemMeta("Cash", "Cash and cash equivalents on the balance sheet.", "Beginning Cash + CFO + CFI + CFF"),
    "accounts_receivable": LineItemMeta("Accounts Receivable", "Revenue billed but not yet collected.", "Revenue / 365 x DSO"),
    "inventory": LineItemMeta("Inventory", "Products held for sale or use in production.", "COGS / 365 x DIO"),
    "accounts_payable": LineItemMeta("Accounts Payable", "Amounts owed to suppliers.", "COGS / 365 x DPO"),
    "ppne": LineItemMeta("PP&E", "Net property, plant, and equipment.", "Beginning PP&E + CapEx - Depreciation"),
    "debt": LineItemMeta("Debt", "Interest-bearing borrowings outstanding.", "Beginning Debt - Repayment + Draws"),
    "nwc": LineItemMeta("Net Working Capital", "Operating capital tied up in receivables, inventory, and payables.", "AR + Inventory - AP"),
    "cfo": LineItemMeta("CFO", "Cash generated from core operations.", "Net Income + Depreciation - Change in NWC"),
    "cfi": LineItemMeta("CFI", "Cash invested in long-term assets.", "-CapEx"),
    "cff": LineItemMeta("CFF", "Cash from or returned to lenders and shareholders.", "Debt Draws - Debt Repayment - Dividends"),
    "fcf": LineItemMeta("Free Cash Flow", "Cash available to all capital providers after reinvestment.", "NOPAT + Depreciation - CapEx - Change in NWC"),
    "nopat": LineItemMeta("NOPAT", "After-tax operating profit before financing decisions.", "EBIT x (1 - Tax Rate)"),
    "gross_margin_%": LineItemMeta("Gross Margin", "Gross profit as a percent of revenue.", "Gross Profit / Revenue", "%"),
    "ebitda_margin_%": LineItemMeta("EBITDA Margin", "EBITDA as a percent of revenue.", "EBITDA / Revenue", "%"),
    "net_margin_%": LineItemMeta("Net Margin", "Net income as a percent of revenue.", "Net Income / Revenue", "%"),
    "tax_rate": LineItemMeta("Tax Rate", "Effective tax rate used in the model.", "Taxes / max(EBT, 1)", "%"),
    "capex": LineItemMeta("CapEx", "Cash spent on long-lived assets.", "Revenue x CapEx %"),
    "shares_outstanding": LineItemMeta("Shares Outstanding", "Diluted shares used for per-share valuation.", "Reported shares outstanding", "shares"),
    "enterprise_value": LineItemMeta("Enterprise Value", "Value of the operating business before debt and cash.", "Equity Value + Net Debt"),
    "equity_value": LineItemMeta("Equity Value", "Value attributable to common shareholders.", "Enterprise Value - Net Debt"),
    "value_per_share": LineItemMeta("Value per Share", "Equity value allocated across shares outstanding.", "Equity Value / Shares Outstanding", "$/share"),
}


SPECIAL_LABELS = {
    "cogs": "COGS",
    "ebitda": "EBITDA",
    "ebit": "EBIT",
    "ebt": "EBT",
    "eps": "EPS",
    "ppne": "PP&E",
    "cfo": "CFO",
    "cfi": "CFI",
    "cff": "CFF",
    "fcf": "FCF",
    "nopat": "NOPAT",
    "dso": "DSO",
    "dio": "DIO",
    "dpo": "DPO",
    "nwc": "NWC",
    "wacc": "WACC",
}


def format_line_item_label(key: str) -> str:
    if key in LINE_ITEM_META:
        return LINE_ITEM_META[key].label
    if key in SPECIAL_LABELS:
        return SPECIAL_LABELS[key]
    return key.replace("_", " ").title()
