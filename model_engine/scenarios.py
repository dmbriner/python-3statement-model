"""Scenario presets and driver explanations for the 3-statement model."""

from __future__ import annotations

from .config import ModelAssumptions

# ---------------------------------------------------------------------------
# Scenario presets (UPS-anchored)
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, ModelAssumptions] = {
    "Base": ModelAssumptions(
        projection_years=5,
        revenue_growth=[0.045, 0.040, 0.035, 0.030, 0.030],
        gross_margin=[0.220, 0.223, 0.225, 0.226, 0.227],
        opex_pct_revenue=[0.152, 0.151, 0.150, 0.149, 0.148],
        capex_pct_revenue=[0.055, 0.055, 0.054, 0.053, 0.052],
        tax_rate=0.24,
        dso_days=[34, 34, 33, 33, 33],
        dio_days=[8, 8, 8, 7, 7],
        dpo_days=[31, 31, 32, 32, 32],
        depreciation_pct_ppne=0.14,
        interest_rate_on_debt=0.052,
        debt_amortization=[350, 350, 400, 400, 450],
        dividend_payout_ratio=0.38,
        target_min_cash_pct_revenue=0.03,
    ),
    "Bull": ModelAssumptions(
        projection_years=5,
        revenue_growth=[0.065, 0.060, 0.055, 0.050, 0.045],
        gross_margin=[0.230, 0.235, 0.238, 0.240, 0.242],
        opex_pct_revenue=[0.148, 0.146, 0.144, 0.143, 0.142],
        capex_pct_revenue=[0.053, 0.052, 0.051, 0.050, 0.050],
        tax_rate=0.24,
        dso_days=[33, 33, 32, 32, 32],
        dio_days=[8, 7, 7, 7, 7],
        dpo_days=[32, 33, 33, 34, 34],
        depreciation_pct_ppne=0.14,
        interest_rate_on_debt=0.052,
        debt_amortization=[400, 450, 500, 550, 600],
        dividend_payout_ratio=0.38,
        target_min_cash_pct_revenue=0.03,
    ),
    "Bear": ModelAssumptions(
        projection_years=5,
        revenue_growth=[0.010, 0.010, 0.015, 0.020, 0.025],
        gross_margin=[0.205, 0.207, 0.210, 0.212, 0.213],
        opex_pct_revenue=[0.158, 0.157, 0.156, 0.155, 0.154],
        capex_pct_revenue=[0.057, 0.057, 0.056, 0.056, 0.055],
        tax_rate=0.24,
        dso_days=[35, 35, 35, 34, 34],
        dio_days=[9, 9, 8, 8, 8],
        dpo_days=[30, 30, 31, 31, 31],
        depreciation_pct_ppne=0.14,
        interest_rate_on_debt=0.052,
        debt_amortization=[300, 300, 300, 350, 350],
        dividend_payout_ratio=0.38,
        target_min_cash_pct_revenue=0.03,
    ),
}

# ---------------------------------------------------------------------------
# Driver explanations — 5 core value drivers
# ---------------------------------------------------------------------------

DRIVER_EXPLANATIONS: dict[str, dict] = {
    "revenue_growth": {
        "name": "Revenue Growth",
        "icon": "📦",
        "driver_description": (
            "Revenue growth = more packages shipped (volume) × higher price per package (yield). "
            "At its core, UPS earns money every time it picks up and delivers a box."
        ),
        "beginner_tip": (
            "Think of UPS as a toll road for packages. Revenue grows when either more cars (packages) "
            "use the road, or the toll (price per package) goes up. Both levers matter."
        ),
        "ups_context": (
            "UPS has pursued a 'better not bigger' strategy — deliberately exiting low-margin Amazon volume "
            "while growing SMB (small business) and healthcare logistics, which carry higher yields. "
            "Volume headwinds from Amazon departure weigh on near-term growth, but mix improvement supports margins."
        ),
        "base_logic": "Moderate recovery: 3–4.5% CAGR as SMB and healthcare channels offset Amazon volume loss.",
        "bull_logic": "Strong recovery: 4.5–6.5% CAGR driven by e-commerce acceleration, pricing power, and healthcare wins.",
        "bear_logic": "Sluggish growth: 1–2.5% CAGR as macro softness, competition from FedEx, and volume declines persist.",
        "assumption_key": "revenue_growth",
    },
    "gross_margin": {
        "name": "Gross Margin",
        "icon": "📊",
        "driver_description": (
            "Gross margin = (Revenue − COGS) / Revenue. COGS for UPS is dominated by transportation "
            "costs: fuel, aircraft/vehicle operation, and labor in sorting/delivery."
        ),
        "beginner_tip": (
            "Gross margin tells you how much of each dollar of revenue UPS keeps after paying direct costs. "
            "A 22% gross margin means for every $100 of revenue, $22 is left to cover overhead and earn profit."
        ),
        "ups_context": (
            "UPS has a largely fixed-cost network (planes, hubs, routes). When volume rises, those fixed "
            "costs spread across more packages → margin expands (operating leverage). The 2023 Teamsters contract "
            "added significant labor costs, creating margin headwind that UPS is working to offset via pricing and automation."
        ),
        "base_logic": "Gradual improvement: 22.0% → 22.7% as pricing gains and automation offset labor inflation.",
        "bull_logic": "Stronger expansion: 23.0% → 24.2% as volume recovery drives operating leverage and premium mix grows.",
        "bear_logic": "Compression: 20.5% → 21.3% as volume declines leave fixed costs underabsorbed and pricing power weakens.",
        "assumption_key": "gross_margin",
    },
    "capex_pct_revenue": {
        "name": "Capital Intensity",
        "icon": "🏗️",
        "driver_description": (
            "Capital expenditure (capex) measures how much UPS reinvests in its physical network each year: "
            "aircraft, delivery vehicles, sorting hubs, and technology. Capex as % of revenue shows "
            "how capital-intensive the business is relative to its size."
        ),
        "beginner_tip": (
            "Capex is money spent on long-lived assets — things that will be used for many years. "
            "Unlike wages (an operating expense), capex shows up on the balance sheet and is depreciated over time. "
            "High capex companies need to continuously invest just to stay competitive."
        ),
        "ups_context": (
            "UPS spends ~5–6% of revenue on capex annually. Major investments include: next-generation aircraft "
            "(replacing old 727s with more fuel-efficient planes), automated sorting facilities, and electric delivery "
            "vehicles. PP&E depreciation (~14% of PP&E balance annually) flows back through the income statement as a non-cash charge."
        ),
        "base_logic": "Moderate: 5.2–5.5% of revenue. Maintains network while tapering growth investment.",
        "bull_logic": "Slightly lower: 5.0–5.3%. Strong FCF generation allows efficient reinvestment at higher utilization.",
        "bear_logic": "Higher: 5.5–5.7%. Maintenance capex stays elevated even as revenue growth slows.",
        "assumption_key": "capex_pct_revenue",
    },
    "working_capital": {
        "name": "Working Capital",
        "icon": "🔄",
        "driver_description": (
            "Net Working Capital (NWC) = Accounts Receivable + Inventory − Accounts Payable. "
            "Changes in NWC consume or release cash. When NWC grows, cash is tied up; when it shrinks, cash is freed."
        ),
        "beginner_tip": (
            "Imagine a store that buys $100 of inventory (cash out), waits 8 days to sell it, then "
            "waits 34 more days to collect from customers — but pays its own suppliers in 31 days. "
            "That gap is working capital. Shorter gaps = more cash-efficient business."
        ),
        "ups_context": (
            "DSO (Days Sales Outstanding) ≈ 33–35 days: UPS collects from business customers within ~5 weeks. "
            "DIO (Days Inventory Outstanding) ≈ 7–9 days: UPS is primarily a service company — minimal physical inventory. "
            "DPO (Days Payable Outstanding) ≈ 30–34 days: UPS pays suppliers in ~30 days, a typical corporate standard."
        ),
        "base_logic": "Stable: Gradual improvement in DSO (34→33 days) as billing processes improve. AP days nudge higher.",
        "bull_logic": "Improving: Faster collections (DSO compresses), better AP terms. NWC release supports FCF.",
        "bear_logic": "Slight deterioration: Customers slow payments (DSO rises to 35 days). No improvement in AP terms.",
        "assumption_key": "working_capital",
    },
    "financing": {
        "name": "Financing Behavior",
        "icon": "🏦",
        "driver_description": (
            "How UPS funds itself and returns cash to shareholders: debt issuance/repayment, dividends, "
            "and cash sweep logic (using excess cash to pay down debt)."
        ),
        "beginner_tip": (
            "A company can do three things with cash: reinvest it (capex), pay shareholders (dividends/buybacks), "
            "or pay back lenders (debt repayment). UPS carries ~$21B of debt and pays substantial dividends. "
            "The 'cash sweep' means any extra cash above a minimum buffer automatically reduces debt."
        ),
        "ups_context": (
            "UPS carries ~$21B in long-term debt (common for capital-intensive businesses). Annual debt "
            "amortization: $350–450M base case. Interest rate: ~5.2% blended average on the debt stack. "
            "UPS has historically paid ~$5/share in dividends — a strong commitment to income investors. "
            "Dividend payout ratio of ~38% is sustainable even in softer earnings environments."
        ),
        "base_logic": "Steady: $350–450M annual amortization. Dividend at 38% of NI. Cash sweep when cash > 1.5× minimum.",
        "bull_logic": "Accelerated paydown: Higher NI and FCF allow $400–600M annual debt reduction.",
        "bear_logic": "Constrained: Lower NI limits debt paydown to $300–350M. Dividends maintained via commitment.",
        "assumption_key": "financing",
    },
}
