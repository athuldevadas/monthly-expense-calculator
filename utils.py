from __future__ import annotations

from datetime import date, datetime

import pandas as pd


def month_key(value: date | datetime | str | None = None) -> str:
    if value is None:
        value = date.today()
    parsed = pd.to_datetime(value)
    return parsed.strftime("%Y-%m")


def month_label(month_str: str) -> str:
    return pd.to_datetime(f"{month_str}-01").strftime("%B %Y")


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def safe_percentage(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100


def prepare_income_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared["month"] = prepared["date"].dt.strftime("%Y-%m")
    return prepared


def prepare_expense_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"])
    prepared["month"] = prepared["date"].dt.strftime("%Y-%m")
    prepared["member_name"] = prepared["member_name"].fillna("Family")
    return prepared


def filter_transactions(
    expenses_df: pd.DataFrame,
    selected_month: str,
    member_name: str,
    category_name: str,
    expense_type: str,
    search_term: str,
) -> pd.DataFrame:
    filtered = expenses_df.copy()
    if filtered.empty:
        return filtered
    filtered = filtered[filtered["month"] == selected_month]
    if member_name != "All":
        filtered = filtered[filtered["member_name"] == member_name]
    if category_name != "All":
        filtered = filtered[filtered["category"] == category_name]
    if expense_type != "All":
        filtered = filtered[filtered["expense_type"] == expense_type]
    if search_term:
        pattern = search_term.strip()
        filtered = filtered[
            filtered["description"].fillna("").str.contains(pattern, case=False, na=False)
            | filtered["category"].str.contains(pattern, case=False, na=False)
            | filtered["member_name"].fillna("").str.contains(pattern, case=False, na=False)
        ]
    return filtered


def compute_dashboard_metrics(
    incomes_df: pd.DataFrame,
    expenses_df: pd.DataFrame,
    budgets_df: pd.DataFrame,
    selected_month: str,
) -> dict[str, float]:
    monthly_income = incomes_df[incomes_df["month"] == selected_month] if not incomes_df.empty else incomes_df
    monthly_expenses = expenses_df[expenses_df["month"] == selected_month] if not expenses_df.empty else expenses_df

    total_income = float(monthly_income["amount"].sum()) if not monthly_income.empty else 0.0
    family_expenses = (
        float(monthly_expenses.loc[monthly_expenses["expense_type"] == "Family / Shared", "amount"].sum())
        if not monthly_expenses.empty
        else 0.0
    )
    individual_expenses = (
        float(monthly_expenses.loc[monthly_expenses["expense_type"] == "Individual", "amount"].sum())
        if not monthly_expenses.empty
        else 0.0
    )
    total_expenses = float(monthly_expenses["amount"].sum()) if not monthly_expenses.empty else 0.0
    remaining_balance = total_income - total_expenses

    monthly_budgets = budgets_df[budgets_df["budget_month"] == selected_month] if not budgets_df.empty else budgets_df
    overall_budget = (
        float(monthly_budgets.loc[monthly_budgets["category_id"].isna(), "amount"].sum())
        if not monthly_budgets.empty
        else 0.0
    )

    return {
        "total_income": total_income,
        "family_expenses": family_expenses,
        "individual_expenses": individual_expenses,
        "total_expenses": total_expenses,
        "remaining_balance": remaining_balance,
        "overall_budget": overall_budget,
        "budget_used_pct": safe_percentage(total_expenses, overall_budget) if overall_budget else 0.0,
    }


def previous_month(month_str: str) -> str:
    return (pd.Period(month_str, freq="M") - 1).strftime("%Y-%m")
