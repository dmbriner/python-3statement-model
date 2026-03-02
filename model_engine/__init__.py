"""Python-powered 3-statement model engine."""

from .analyzer import HistoricalMetrics, analyze_historical_data, suggest_scenarios
from .config import ModelAssumptions
from .data import HistoricalData, load_historical_data, reporting_frame
from .export import build_excel_bytes, export_model_to_excel
from .integrity import IntegrityResult, check_integrity
from .line_items import LINE_ITEM_META, format_line_item_label
from .market_data import (
    AnalystSnapshot,
    CompanyProfile,
    CompanySearchResult,
    EarningsEvent,
    PeerCompany,
    PrecedentTransaction,
    ResearchPack,
    build_research_pack,
    fmp_enabled,
    resolve_company_profile,
    search_companies,
)
from .model import ModelOutput, run_three_statement_model
from .sensitivity import build_multi_output_sensitivity, build_sensitivity_table, build_tornado_chart
from .valuation import (
    DCFResult,
    LBOResult,
    MultipleValuationResult,
    run_dcf,
    run_lbo,
    run_multiple_valuation,
    run_precedent_transactions,
    valuation_summary_table,
    wacc_terminal_sensitivity,
)

__all__ = [
    # Config
    "ModelAssumptions",
    # Data
    "HistoricalData",
    "load_historical_data",
    "reporting_frame",
    # Analyzer
    "HistoricalMetrics",
    "analyze_historical_data",
    "suggest_scenarios",
    # Market data
    "CompanyProfile",
    "CompanySearchResult",
    "PeerCompany",
    "AnalystSnapshot",
    "EarningsEvent",
    "PrecedentTransaction",
    "ResearchPack",
    "search_companies",
    "resolve_company_profile",
    "build_research_pack",
    "fmp_enabled",
    # Presentation
    "LINE_ITEM_META",
    "format_line_item_label",
    # Model
    "ModelOutput",
    "run_three_statement_model",
    # Sensitivity
    "build_sensitivity_table",
    "build_multi_output_sensitivity",
    "build_tornado_chart",
    # Valuation
    "DCFResult",
    "MultipleValuationResult",
    "LBOResult",
    "run_dcf",
    "run_multiple_valuation",
    "run_precedent_transactions",
    "run_lbo",
    "valuation_summary_table",
    "wacc_terminal_sensitivity",
    # Integrity
    "IntegrityResult",
    "check_integrity",
    # Export
    "build_excel_bytes",
    "export_model_to_excel",
]
