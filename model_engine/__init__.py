"""Python-powered 3-statement model engine."""

from .analyzer import HistoricalMetrics, analyze_historical_data, suggest_scenarios
from .config import ModelAssumptions
from .data import load_historical_data
from .export import export_model_to_excel
from .integrity import IntegrityResult, check_integrity
from .model import ModelOutput, run_three_statement_model
from .sensitivity import build_multi_output_sensitivity, build_sensitivity_table, build_tornado_chart
from .valuation import DCFResult, run_dcf, wacc_terminal_sensitivity

__all__ = [
    # Config
    "ModelAssumptions",
    # Data
    "load_historical_data",
    # Analyzer
    "HistoricalMetrics",
    "analyze_historical_data",
    "suggest_scenarios",
    # Model
    "ModelOutput",
    "run_three_statement_model",
    # Sensitivity
    "build_sensitivity_table",
    "build_multi_output_sensitivity",
    "build_tornado_chart",
    # Valuation
    "DCFResult",
    "run_dcf",
    "wacc_terminal_sensitivity",
    # Integrity
    "IntegrityResult",
    "check_integrity",
    # Export
    "export_model_to_excel",
]
