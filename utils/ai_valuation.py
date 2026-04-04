import json
import logging
import os
from typing import Dict, Optional

import streamlit as st

# Note: Using the blueprint:python_openai integration
# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
from openai import OpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None


class AIValuationAnalyzer:
    """
    AI-powered fundamental analysis and valuation using multiple investment frameworks
    """

    def __init__(self):
        global openai_client
        if openai_client is None:
            try:
                openai_client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                openai_client = None
        self.client: Optional[OpenAI] = openai_client
        self.model = "gpt-5"

    def analyze_fundamentals(
        self, metrics: Dict, valuation_model: str = "comprehensive"
    ) -> Optional[Dict]:
        """
        Analyze company fundamentals using AI
        Args:
            metrics: Dictionary with financial metrics
            valuation_model: Type of analysis - 'growth', 'value', 'dcf', 'comprehensive'
        Returns:
            Dictionary with AI analysis results
        """
        try:
            if not metrics:
                return None

            # Prepare financial data summary
            financial_summary = self._prepare_financial_summary(metrics)

            # Select appropriate prompt based on valuation model
            if valuation_model == "growth":
                prompt = self._get_growth_investing_prompt(financial_summary, metrics)
            elif valuation_model == "value":
                prompt = self._get_value_investing_prompt(financial_summary, metrics)
            elif valuation_model == "dcf":
                prompt = self._get_dcf_prompt(financial_summary, metrics)
            else:  # comprehensive
                prompt = self._get_comprehensive_prompt(financial_summary, metrics)

            # Call OpenAI API
            if self.client is None:
                logger.error("OpenAI client is not initialized")
                return {
                    "error": "OpenAI client not available",
                    "symbol": metrics.get("symbol", "N/A"),
                    "valuation_model": valuation_model,
                }

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst with deep knowledge of "
                        "fundamental analysis, valuation models, and investment strategies. "
                        "Provide detailed, data-driven analysis with specific insights. "
                        "Always respond in JSON format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=4096,
            )

            # Parse response
            content = response.choices[0].message.content
            if not isinstance(content, (str, bytes, bytearray)):
                logger.error(f"Invalid response content type: {type(content)}")
                return None

            result = json.loads(content)
            result["valuation_model"] = valuation_model
            result["symbol"] = metrics.get("symbol", "N/A")

            return result

        except Exception as e:
            logger.error(f"Error in AI valuation analysis: {str(e)}")
            return {
                "error": str(e),
                "symbol": metrics.get("symbol", "N/A"),
                "valuation_model": valuation_model,
            }

    def _prepare_financial_summary(self, metrics: Dict) -> str:
        """Prepare a concise financial summary for AI analysis"""
        summary_parts = []

        summary_parts.append(
            f"Company: {metrics.get('company_name', metrics.get('symbol', 'Unknown'))}"
        )
        summary_parts.append(f"Symbol: {metrics.get('symbol', 'N/A')}")
        summary_parts.append(f"Sector: {metrics.get('sector', 'N/A')}")
        summary_parts.append(f"Industry: {metrics.get('industry', 'N/A')}")
        summary_parts.append(f"Period: {metrics.get('period', 'N/A')}")

        if metrics.get("current_price"):
            summary_parts.append(f"Current Price: ${metrics['current_price']:.2f}")
        if metrics.get("market_cap"):
            summary_parts.append(f"Market Cap: ${metrics['market_cap']:,.0f}")
        if metrics.get("pe_ratio"):
            summary_parts.append(f"P/E Ratio: {metrics['pe_ratio']:.2f}")

        # Revenue data
        if "revenue" in metrics:
            revenue_str = "Revenue: " + ", ".join(
                [f"${r / 1e9:.2f}B" if r else "N/A" for r in metrics["revenue"][:8]]
            )
            summary_parts.append(revenue_str)

        # Net income data
        if "net_income" in metrics:
            ni_str = "Net Income: " + ", ".join(
                [
                    f"${ni / 1e9:.2f}B"
                    if ni and ni > 0
                    else f"-${abs(ni) / 1e9:.2f}B"
                    if ni
                    else "N/A"
                    for ni in metrics["net_income"][:8]
                ]
            )
            summary_parts.append(ni_str)

        # Operating income
        if "operating_income" in metrics:
            oi_str = "Operating Income: " + ", ".join(
                [f"${oi / 1e9:.2f}B" if oi else "N/A" for oi in metrics["operating_income"][:8]]
            )
            summary_parts.append(oi_str)

        # Cash flow
        if "free_cashflow" in metrics:
            fcf_str = "Free Cash Flow: " + ", ".join(
                [f"${fcf / 1e9:.2f}B" if fcf else "N/A" for fcf in metrics["free_cashflow"][:8]]
            )
            summary_parts.append(fcf_str)

        return "\n".join(summary_parts)

    def _get_comprehensive_prompt(self, financial_summary: str, metrics: Dict) -> str:
        """Get comprehensive analysis prompt"""
        return f"""Analyze the following company's financials and provide
        a comprehensive investment analysis.

        {financial_summary}

Provide your analysis in JSON format with the following structure:
{{
    "overall_rating": "Strong Buy/Buy/Hold/Sell/Strong Sell",
    "confidence_score": 0-100,
    "key_strengths": ["strength 1", "strength 2", ...],
    "key_weaknesses": ["weakness 1", "weakness 2", ...],
    "revenue_analysis": "detailed analysis of revenue trends",
    "profitability_analysis": "detailed analysis of profitability and margins",
    "growth_potential": "assessment of future growth potential",
    "valuation_assessment": "is the stock fairly valued, undervalued, or overvalued?",
    "risk_factors": ["risk 1", "risk 2", ...],
    "investment_thesis": "comprehensive investment thesis",
    "target_price_range": {{"low": number, "mid": number, "high": number}},
    "time_horizon": "recommended holding period"
}}

Focus on data-driven insights based on the historical trends and current metrics."""

    def _get_growth_investing_prompt(self, financial_summary: str, metrics: Dict) -> str:
        """Get growth investing focused prompt"""
        return f"""Analyze this company from a GROWTH INVESTING perspective
        (think Peter Lynch, Phil Fisher style).

        {financial_summary}

Provide your analysis in JSON format with the following structure:
{{
    "growth_rating": "Exceptional/Strong/Moderate/Weak/Poor",
    "confidence_score": 0-100,
    "revenue_growth_analysis": "detailed assessment of revenue growth rate and sustainability",
    "earnings_growth_analysis": "analysis of earnings growth trends and quality",
    "growth_drivers": ["driver 1", "driver 2", ...],
    "scalability_assessment": "can the company scale efficiently?",
    "competitive_moat": "assessment of competitive advantages",
    "management_effectiveness": "assessment based on financial execution",
    "growth_sustainability": "is the growth sustainable long-term?",
    "expansion_opportunities": ["opportunity 1", "opportunity 2", ...],
    "growth_risks": ["risk 1", "risk 2", ...],
    "peg_ratio_assessment": "is the growth priced in or is there upside?",
    "investment_recommendation": "detailed recommendation for growth investors",
    "estimated_annual_growth_rate": "X-Y% range for next 3-5 years"
}}

Focus on growth metrics, scalability, and future potential."""

    def _get_value_investing_prompt(self, financial_summary: str, metrics: Dict) -> str:
        """Get value investing focused prompt"""
        return f"""Analyze this company from a VALUE INVESTING perspective
        (think Warren Buffett, Benjamin Graham style).

        {financial_summary}

Provide your analysis in JSON format with the following structure:
{{
    "value_rating": "Exceptional Value/Good Value/Fair Value/Overvalued/Significantly Overvalued",
    "confidence_score": 0-100,
    "intrinsic_value_assessment": "Yes - brief explanation or No - brief explanation",
    "margin_of_safety": "estimated margin of safety percentage",
    "quality_of_earnings": "assessment of earnings quality and sustainability",
    "balance_sheet_strength": "analysis of financial health and debt levels",
    "cash_generation": "analysis of cash flow generation capability",
    "dividend_analysis": "if applicable, dividend sustainability and growth",
    "economic_moat": "assessment of durable competitive advantages",
    "management_quality": "capital allocation and shareholder focus",
    "downside_protection": "what protects against permanent capital loss?",
    "value_catalysts": ["catalyst 1", "catalyst 2", ...],
    "value_risks": ["risk 1", "risk 2", ...],
    "investment_recommendation": "detailed recommendation for value investors",
    "fair_value_estimate": "estimated fair value per share"
}}

Focus on safety, quality, valuation multiples, and downside protection."""

    def _get_dcf_prompt(self, financial_summary: str, metrics: Dict) -> str:
        """Get DCF valuation focused prompt"""
        return f"""Perform a DISCOUNTED CASH FLOW (DCF) valuation analysis for this company.

        {financial_summary}

Provide your analysis in JSON format with the following structure:
{{
    "dcf_valuation_rating": "Highly Undervalued/Undervalued/Fair/Overvalued/Highly Overvalued",
    "confidence_score": 0-100,
    "cash_flow_analysis": "analysis of historical and projected free cash flows",
    "growth_assumptions": "assumptions for revenue and FCF growth",
    "discount_rate": "recommended WACC or discount rate with justification",
    "terminal_value_approach": "perpetuity growth or exit multiple approach",
    "terminal_growth_rate": "assumed perpetual growth rate",
    "dcf_fair_value": "calculated fair value per share",
    "sensitivity_analysis": {{"conservative": number, "base": number, "optimistic": number}},
    "key_value_drivers": ["driver 1", "driver 2", ...],
    "dcf_assumptions": ["assumption 1", "assumption 2", ...],
    "model_limitations": ["limitation 1", "limitation 2", ...],
    "investment_recommendation": "buy/hold/sell based on DCF",
    "upside_downside_ratio": "potential upside vs downside"
}}

Focus on cash flow projections, appropriate discount rates, and terminal value calculations."""


@st.cache_data(ttl=3600)
def get_market_comparables(_self, symbol: str, sector: str, industry: str) -> Optional[str]:
    """
    Get AI-powered market comparables analysis
    """
    try:
        prompt = (
            f"Provide valuation multiples and metrics for companies in the {industry} "
            f"industry within the {sector} sector. "
            "\n\nInclude typical ranges for:\n"
            "- P/E ratios\n"
            "- P/B ratios\n"
            "- Revenue growth rates\n"
            "- Profit margins\n"
            "- Return on equity\n\n"
            "Respond in JSON format with:\n"
            "{\n"
            '    "industry": "industry name",\n'
            '    "sector": "sector name",\n'
            '    "typical_pe_range": {"low": number, "high": number},\n'
            '    "typical_growth_rate": "X-Y%",\n'
            '    "typical_profit_margin": "X-Y%",\n'
            '    "key_industry_metrics": ["metric 1", "metric 2", ...],\n'
            '    "industry_outlook": "brief outlook"\n'
            "}"
        )

        if _self.client is None:
            logger.error("OpenAI client is not initialized")
            return None

        response = _self.client.chat.completions.create(
            model=_self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst expert in industry analysis "
                        "and valuation multiples."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=2048,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error getting market comparables: {str(e)}")
        return None


ai_valuation_analyzer = AIValuationAnalyzer()
