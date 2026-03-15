from __future__ import annotations

from datetime import date
from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from database import ExpenseDatabase
from models import ASSIGNMENT_TYPES, EXPENSE_TYPES, PAYMENT_METHODS
from utils import (
    compute_dashboard_metrics,
    filter_transactions,
    format_currency,
    month_key,
    month_label,
    prepare_expense_frame,
    prepare_income_frame,
    previous_month,
    safe_percentage,
)

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "expense_tracker.db"
PAGE_DESCRIPTIONS = {
    "Dashboard": "View your monthly summary, savings, budget status, and spending trends.",
    "Add Income": "Add, edit, and manage family or individual income sources.",
    "Add Expense": "Record shared or personal expenses with category and payment details.",
    "Reports": "Analyze spending by month, member, category, and export filtered data.",
    "Budget Settings": "Set overall and category budgets, then monitor overspending.",
    "Manage Members": "Add family members and custom categories used across the app.",
}
PAGE_TIPS = {
    "Dashboard": [
        "Check total income, expenses, and remaining balance for the month.",
        "Compare current performance with the previous month.",
    ],
    "Add Income": [
        "Use this page to save salary, freelance, rental, or family income.",
        "Edit or remove old entries from the table below the form.",
    ],
    "Add Expense": [
        "Record shared household costs or personal member expenses.",
        "Choose a category and payment method for better reports later.",
    ],
    "Reports": [
        "Filter by month, member, category, and expense type.",
        "Export the filtered table to CSV when needed.",
    ],
    "Budget Settings": [
        "Set one monthly overall budget and optional category budgets.",
        "Review overspending warnings based on actual expenses.",
    ],
    "Manage Members": [
        "Add or update family members used in income and expense records.",
        "Create custom categories for spending that is unique to your family.",
    ],
}

st.set_page_config(
    page_title="Monthly Expense Calculator",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_database() -> ExpenseDatabase:
    return ExpenseDatabase(DB_PATH)


def apply_theme(is_dark: bool) -> None:
    if is_dark:
        background = "#0f172a"
        surface = "#111827"
        card = "#1f2937"
        text = "#f8fafc"
        muted = "#94a3b8"
        accent = "#22c55e"
        secondary_background = "#182334"
        border = "rgba(148, 163, 184, 0.22)"
        input_text = "#f8fafc"
    else:
        background = "#e2e8f0"
        surface = "#f8fafc"
        card = "#e5eef7"
        text = "#0f172a"
        muted = "#475569"
        accent = "#15803d"
        secondary_background = "#eef4fb"
        border = "rgba(15, 23, 42, 0.12)"
        input_text = "#0f172a"

    st.markdown(
        f"""
        <style>
        :root {{
            color-scheme: {"dark" if is_dark else "light"};
        }}
        .stApp {{
            background: radial-gradient(circle at top left, rgba(34,197,94,0.08), transparent 30%), {background};
            color: {text};
        }}
        .stApp [data-testid="stAppViewContainer"] {{
            background: transparent;
            color: {text};
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {surface} 0%, {card} 100%);
            border-right: 1px solid {border};
        }}
        [data-testid="stSidebar"] > div:first-child {{
            background: linear-gradient(180deg, {surface} 0%, {card} 100%);
        }}
        [data-testid="stSidebar"] * {{
            color: {text};
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] .st-emotion-cache-10trblm,
        [data-testid="stSidebar"] .st-emotion-cache-16idsys {{
            color: {text};
        }}
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-testid="stRadio"] > div,
        [data-testid="stSidebar"] [data-testid="stExpander"],
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        .stDateInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {{
            background: {secondary_background};
            color: {input_text};
            border-color: {border};
        }}
        .stRadio label,
        .stCheckbox label,
        .stToggle label,
        .stSelectbox label,
        .stMultiSelect label,
        .stDateInput label,
        .stNumberInput label,
        .stTextInput label,
        .stTextArea label,
        .stMarkdown,
        .stSubheader,
        .stTitle,
        .stHeader,
        .stCaption,
        p,
        span,
        label {{
            color: {text};
        }}
        [data-testid="stMetric"],
        [data-testid="stDataFrame"],
        [data-testid="stForm"],
        [data-testid="stAlert"] {{
            color: {text};
        }}
        .metric-card {{
            background: {surface};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        }}
        .metric-label {{
            font-size: 0.85rem;
            color: {muted};
        }}
        .metric-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {text};
        }}
        .pill {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            background: rgba(34, 197, 94, 0.12);
            color: {accent};
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .section-title {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_reference_data(db: ExpenseDatabase) -> tuple[pd.DataFrame, pd.DataFrame]:
    members = db.get_members(active_only=False)
    categories = db.get_categories()
    return members, categories


def load_data(db: ExpenseDatabase) -> dict[str, pd.DataFrame]:
    incomes = prepare_income_frame(db.get_incomes())
    expenses = prepare_expense_frame(db.get_expenses())
    budgets = db.get_budgets()
    members, categories = load_reference_data(db)
    return {
        "incomes": incomes,
        "expenses": expenses,
        "budgets": budgets,
        "members": members,
        "categories": categories,
    }


def render_metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {f'<div class="metric-label">{help_text}</div>' if help_text else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_db_action(action, success_message: str) -> None:
    try:
        action()
    except sqlite3.IntegrityError as exc:
        st.error(f"Database constraint error: {exc}.")
    except Exception as exc:
        st.error(f"Unable to complete the action: {exc}.")
    else:
        st.success(success_message)
        st.rerun()


def sidebar_controls(data: dict[str, pd.DataFrame]) -> tuple[str, str, bool]:
    st.sidebar.title("Monthly Expense Calculator")
    st.sidebar.caption("Track shared and individual spending with local SQLite storage.")

    month_options = []
    for frame_name in ("incomes", "expenses"):
        if not data[frame_name].empty:
            month_options.extend(data[frame_name]["month"].dropna().unique().tolist())
    month_options = sorted(set(month_options), reverse=True)
    current = month_key()
    if current not in month_options:
        month_options.insert(0, current)

    selected_month = st.sidebar.selectbox(
        "Reporting month",
        month_options,
        format_func=month_label,
    )
    page = st.sidebar.radio(
        "Navigate",
        list(PAGE_DESCRIPTIONS.keys()),
    )
    st.sidebar.markdown("### What this page does")
    st.sidebar.info(PAGE_DESCRIPTIONS[page])
    for tip in PAGE_TIPS[page]:
        st.sidebar.caption(f"- {tip}")

    st.sidebar.markdown("### Section Guide")
    for page_name, description in PAGE_DESCRIPTIONS.items():
        expanded = page_name == page
        with st.sidebar.expander(page_name, expanded=expanded):
            st.caption(description)
            for tip in PAGE_TIPS[page_name]:
                st.caption(f"- {tip}")

    is_dark = st.sidebar.toggle("Dark mode", value=st.session_state.get("dark_mode", True))
    st.session_state["dark_mode"] = is_dark
    return selected_month, page, is_dark


def member_options_map(members_df: pd.DataFrame, include_all: bool = False) -> dict[str, int | None]:
    options: dict[str, int | None] = {}
    if include_all:
        options["All"] = None
    for _, row in members_df.iterrows():
        options[row["name"]] = int(row["id"])
    return options


def category_options_map(categories_df: pd.DataFrame, include_all: bool = False) -> dict[str, int | None]:
    options: dict[str, int | None] = {}
    if include_all:
        options["All"] = None
    for _, row in categories_df.iterrows():
        options[row["name"]] = int(row["id"])
    return options


def render_dashboard(db: ExpenseDatabase, data: dict[str, pd.DataFrame], selected_month: str) -> None:
    st.title("Dashboard")
    st.caption(f"Financial overview for {month_label(selected_month)}")

    metrics = compute_dashboard_metrics(data["incomes"], data["expenses"], data["budgets"], selected_month)
    previous_metrics = compute_dashboard_metrics(
        data["incomes"], data["expenses"], data["budgets"], previous_month(selected_month)
    )

    cols = st.columns(5)
    cards = [
        ("Monthly Income", format_currency(metrics["total_income"]), "Recurring and one-off income"),
        ("Family Expenses", format_currency(metrics["family_expenses"]), "Shared household spend"),
        ("Individual Expenses", format_currency(metrics["individual_expenses"]), "Member-specific spend"),
        ("Overall Expenses", format_currency(metrics["total_expenses"]), "All expenses combined"),
        ("Remaining Balance", format_currency(metrics["remaining_balance"]), "Income minus expenses"),
    ]
    for column, (label, value, help_text) in zip(cols, cards):
        with column:
            render_metric_card(label, value, help_text)

    st.markdown('<div class="section-title">Budget vs Actual</div>', unsafe_allow_html=True)
    budget_col, compare_col = st.columns([1.5, 1])
    with budget_col:
        budget_amount = metrics["overall_budget"]
        remaining = budget_amount - metrics["total_expenses"]
        progress = safe_percentage(metrics["total_expenses"], budget_amount) if budget_amount else 0
        st.metric("Overall Budget", format_currency(budget_amount), help="Set in Budget Settings")
        st.progress(min(progress / 100, 1.0))
        if budget_amount:
            if remaining < 0:
                st.error(f"Budget exceeded by {format_currency(abs(remaining))}.")
            else:
                st.success(f"{format_currency(remaining)} remaining in the monthly budget.")
        else:
            st.info("Set an overall budget to track spend against target.")

    with compare_col:
        income_delta = metrics["total_income"] - previous_metrics["total_income"]
        expense_delta = metrics["total_expenses"] - previous_metrics["total_expenses"]
        savings_delta = metrics["remaining_balance"] - previous_metrics["remaining_balance"]
        st.metric("Income vs Previous Month", format_currency(metrics["total_income"]), delta=format_currency(income_delta))
        st.metric("Expenses vs Previous Month", format_currency(metrics["total_expenses"]), delta=format_currency(expense_delta))
        st.metric("Savings vs Previous Month", format_currency(metrics["remaining_balance"]), delta=format_currency(savings_delta))

    monthly_expenses = data["expenses"][data["expenses"]["month"] == selected_month] if not data["expenses"].empty else pd.DataFrame()
    trend_df = (
        data["expenses"].groupby("month", as_index=False)["amount"].sum().sort_values("month")
        if not data["expenses"].empty
        else pd.DataFrame(columns=["month", "amount"])
    )

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-title">Monthly Expense Trend</div>', unsafe_allow_html=True)
        if not trend_df.empty:
            chart = px.line(
                trend_df,
                x="month",
                y="amount",
                markers=True,
                labels={"month": "Month", "amount": "Expenses"},
            )
            chart.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("Add expenses to unlock trend analytics.")

    with right:
        st.markdown('<div class="section-title">Top Categories</div>', unsafe_allow_html=True)
        if not monthly_expenses.empty:
            top_categories = (
                monthly_expenses.groupby("category", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=False)
                .head(5)
            )
            st.dataframe(top_categories, use_container_width=True, hide_index=True)
        else:
            st.info("No expenses recorded for this month.")

    st.markdown('<div class="section-title">Quick Summary</div>', unsafe_allow_html=True)
    summary_cols = st.columns(3)
    summary_cols[0].markdown(
        f'<span class="pill">Income sources: {len(data["incomes"][data["incomes"]["month"] == selected_month]) if not data["incomes"].empty else 0}</span>',
        unsafe_allow_html=True,
    )
    summary_cols[1].markdown(
        f'<span class="pill">Transactions: {len(monthly_expenses)}</span>',
        unsafe_allow_html=True,
    )
    summary_cols[2].markdown(
        f'<span class="pill">Active members: {len(data["members"][data["members"]["is_active"] == 1])}</span>',
        unsafe_allow_html=True,
    )


def render_income_page(db: ExpenseDatabase, data: dict[str, pd.DataFrame]) -> None:
    st.title("Add Income")
    members = data["members"][data["members"]["is_active"] == 1]
    member_map = member_options_map(members)

    with st.form("income_form", clear_on_submit=True):
        st.subheader("New Income Entry")
        col1, col2 = st.columns(2)
        entry_date = col1.date_input("Date", value=date.today())
        source = col2.text_input("Source", placeholder="Salary, freelance, rental income")
        amount = col1.number_input("Amount", min_value=0.0, step=100.0)
        assigned_type = col2.selectbox("Assigned to", ASSIGNMENT_TYPES)
        member_name = None
        if assigned_type == "Member":
            member_name = st.selectbox("Member", list(member_map.keys()))
        recurring = st.checkbox("Recurring monthly income")
        notes = st.text_area("Notes", placeholder="Optional notes")
        submitted = st.form_submit_button("Save Income")

        if submitted:
            if not source.strip() or amount <= 0:
                st.error("Source and amount are required.")
            elif assigned_type == "Member" and not member_name:
                st.error("Select a member for individual income.")
            else:
                run_db_action(
                    lambda: db.add_income(
                        entry_date.isoformat(),
                        source,
                        amount,
                        assigned_type,
                        member_map.get(member_name) if member_name else None,
                        recurring,
                        notes,
                    ),
                    "Income entry saved.",
                )

    st.subheader("Existing Income Entries")
    incomes = data["incomes"]
    if incomes.empty:
        st.info("No income entries yet.")
        return

    st.dataframe(incomes.drop(columns=["member_id"]), use_container_width=True, hide_index=True)
    options = {
        f'#{int(row["id"])} | {row["date"].strftime("%Y-%m-%d")} | {row["source"]} | {format_currency(row["amount"])}': int(row["id"])
        for _, row in incomes.iterrows()
    }
    selected_label = st.selectbox("Select income to edit or delete", list(options.keys()))
    selected_id = options[selected_label]
    record = incomes[incomes["id"] == selected_id].iloc[0]

    with st.form("edit_income_form"):
        st.subheader("Edit Income Entry")
        col1, col2 = st.columns(2)
        edit_date = col1.date_input("Edit date", value=record["date"].date(), key="income_edit_date")
        edit_source = col2.text_input("Edit source", value=record["source"])
        edit_amount = col1.number_input("Edit amount", min_value=0.0, value=float(record["amount"]), step=100.0)
        edit_assigned_type = col2.selectbox(
            "Edit assigned to",
            ASSIGNMENT_TYPES,
            index=ASSIGNMENT_TYPES.index(record["assigned_type"]),
        )
        edit_member_name = None
        if edit_assigned_type == "Member":
            default_member_index = 0
            member_names = list(member_map.keys())
            if record["assigned_to"] in member_names:
                default_member_index = member_names.index(record["assigned_to"])
            edit_member_name = st.selectbox("Edit member", member_names, index=default_member_index)
        edit_recurring = st.checkbox("Recurring monthly income", value=bool(record["recurring"]))
        edit_notes = st.text_area("Edit notes", value=record["notes"] or "")
        save_col, delete_col = st.columns(2)
        save_clicked = save_col.form_submit_button("Update Income")
        delete_clicked = delete_col.form_submit_button("Delete Income")

        if save_clicked:
            run_db_action(
                lambda: db.update_income(
                    selected_id,
                    edit_date.isoformat(),
                    edit_source,
                    edit_amount,
                    edit_assigned_type,
                    member_map.get(edit_member_name) if edit_assigned_type == "Member" else None,
                    edit_recurring,
                    edit_notes,
                ),
                "Income entry updated.",
            )
        if delete_clicked:
            run_db_action(lambda: db.delete_income(selected_id), "Income entry deleted.")


def render_expense_page(db: ExpenseDatabase, data: dict[str, pd.DataFrame]) -> None:
    st.title("Add Expense")
    members = data["members"][data["members"]["is_active"] == 1]
    member_map = member_options_map(members)
    categories = data["categories"]
    category_map = category_options_map(categories)

    with st.form("expense_form", clear_on_submit=True):
        st.subheader("New Expense Entry")
        col1, col2 = st.columns(2)
        entry_date = col1.date_input("Date", value=date.today())
        amount = col2.number_input("Amount", min_value=0.0, step=50.0)
        category_name = col1.selectbox("Category", list(category_map.keys()))
        description = col2.text_input("Description", placeholder="Monthly rent, groceries, school supplies")
        expense_type = col1.selectbox("Expense Type", EXPENSE_TYPES)
        member_name = None
        if expense_type == "Individual":
            member_name = col2.selectbox("Member name", list(member_map.keys()))
        payment_method = col1.selectbox("Payment method", PAYMENT_METHODS)
        recurring = col2.checkbox("Recurring monthly expense")
        submitted = st.form_submit_button("Save Expense")

        if submitted:
            if amount <= 0 or not category_name:
                st.error("Amount and category are required.")
            elif expense_type == "Individual" and not member_name:
                st.error("Select a member for individual expenses.")
            else:
                run_db_action(
                    lambda: db.add_expense(
                        entry_date.isoformat(),
                        amount,
                        int(category_map[category_name]),
                        description,
                        expense_type,
                        member_map.get(member_name) if expense_type == "Individual" else None,
                        payment_method,
                        recurring,
                    ),
                    "Expense entry saved.",
                )

    st.subheader("Existing Expense Entries")
    expenses = data["expenses"]
    if expenses.empty:
        st.info("No expense entries yet.")
        return

    st.dataframe(expenses.drop(columns=["category_id", "member_id"]), use_container_width=True, hide_index=True)
    options = {
        f'#{int(row["id"])} | {row["date"].strftime("%Y-%m-%d")} | {row["category"]} | {format_currency(row["amount"])}': int(row["id"])
        for _, row in expenses.iterrows()
    }
    selected_label = st.selectbox("Select expense to edit or delete", list(options.keys()))
    selected_id = options[selected_label]
    record = expenses[expenses["id"] == selected_id].iloc[0]

    with st.form("edit_expense_form"):
        st.subheader("Edit Expense Entry")
        col1, col2 = st.columns(2)
        edit_date = col1.date_input("Edit date", value=record["date"].date(), key="expense_edit_date")
        edit_amount = col2.number_input("Edit amount", min_value=0.0, value=float(record["amount"]), step=50.0)
        category_names = list(category_map.keys())
        category_index = category_names.index(record["category"]) if record["category"] in category_names else 0
        edit_category_name = col1.selectbox("Edit category", category_names, index=category_index)
        edit_description = col2.text_input("Edit description", value=record["description"] or "")
        edit_expense_type = col1.selectbox(
            "Edit expense type",
            EXPENSE_TYPES,
            index=EXPENSE_TYPES.index(record["expense_type"]),
        )
        edit_member_name = None
        if edit_expense_type == "Individual":
            member_names = list(member_map.keys())
            default_member_index = member_names.index(record["member_name"]) if record["member_name"] in member_names else 0
            edit_member_name = col2.selectbox("Edit member", member_names, index=default_member_index)
        edit_payment_method = col1.selectbox(
            "Edit payment method",
            PAYMENT_METHODS,
            index=PAYMENT_METHODS.index(record["payment_method"]) if record["payment_method"] in PAYMENT_METHODS else 0,
        )
        edit_recurring = col2.checkbox("Recurring monthly expense", value=bool(record["recurring"]))
        save_col, delete_col = st.columns(2)
        save_clicked = save_col.form_submit_button("Update Expense")
        delete_clicked = delete_col.form_submit_button("Delete Expense")

        if save_clicked:
            run_db_action(
                lambda: db.update_expense(
                    selected_id,
                    edit_date.isoformat(),
                    edit_amount,
                    int(category_map[edit_category_name]),
                    edit_description,
                    edit_expense_type,
                    member_map.get(edit_member_name) if edit_expense_type == "Individual" else None,
                    edit_payment_method,
                    edit_recurring,
                ),
                "Expense entry updated.",
            )
        if delete_clicked:
            run_db_action(lambda: db.delete_expense(selected_id), "Expense entry deleted.")


def render_reports_page(data: dict[str, pd.DataFrame], selected_month: str) -> None:
    st.title("Reports")
    expenses = data["expenses"]
    if expenses.empty:
        st.info("Add expenses to generate reports.")
        return

    member_names = ["All"] + sorted(expenses["member_name"].fillna("Family").unique().tolist())
    category_names = ["All"] + sorted(expenses["category"].unique().tolist())
    expense_types = ["All"] + EXPENSE_TYPES

    filter_cols = st.columns(5)
    member_filter = filter_cols[0].selectbox("Member", member_names)
    category_filter = filter_cols[1].selectbox("Category", category_names)
    expense_type_filter = filter_cols[2].selectbox("Expense Type", expense_types)
    search_term = filter_cols[3].text_input("Search", placeholder="Description or category")
    export_ready = filter_cols[4].empty()

    filtered = filter_transactions(
        expenses,
        selected_month,
        member_filter,
        category_filter,
        expense_type_filter,
        search_term,
    )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Category-wise Spending")
        if not filtered.empty:
            category_spend = filtered.groupby("category", as_index=False)["amount"].sum()
            fig = px.pie(category_spend, values="amount", names="category", hole=0.45)
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No matching records for the selected filters.")

    with chart_col2:
        st.subheader("Member-wise Expenses")
        if not filtered.empty:
            member_spend = filtered.groupby("member_name", as_index=False)["amount"].sum()
            fig = px.bar(member_spend, x="member_name", y="amount", color="member_name")
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for member comparison.")

    comparison_col1, comparison_col2 = st.columns(2)
    with comparison_col1:
        st.subheader("Family vs Individual")
        comparison = filtered.groupby("expense_type", as_index=False)["amount"].sum() if not filtered.empty else pd.DataFrame()
        if not comparison.empty:
            fig = px.bar(comparison, x="expense_type", y="amount", color="expense_type")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No comparison data to display.")

    with comparison_col2:
        st.subheader("Monthly Spending Breakdown")
        breakdown = (
            filtered.groupby(["date", "category", "member_name", "expense_type"], as_index=False)["amount"].sum()
            .sort_values("date", ascending=False)
            if not filtered.empty
            else pd.DataFrame()
        )
        if not breakdown.empty:
            breakdown["date"] = breakdown["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(breakdown, use_container_width=True, hide_index=True)
            export_ready.download_button(
                label="Export CSV",
                data=breakdown.to_csv(index=False).encode("utf-8"),
                file_name=f"expense_report_{selected_month}.csv",
                mime="text/csv",
            )
        else:
            st.info("No rows to export.")


def render_budget_page(db: ExpenseDatabase, data: dict[str, pd.DataFrame], selected_month: str) -> None:
    st.title("Budget Settings")
    budgets = db.get_budgets(selected_month)
    expenses = data["expenses"]
    categories = data["categories"]
    category_map = category_options_map(categories)
    month_expenses = expenses[expenses["month"] == selected_month] if not expenses.empty else pd.DataFrame()

    overall_current = 0.0
    if not budgets.empty:
        overall_rows = budgets[budgets["category_id"].isna()]
        if not overall_rows.empty:
            overall_current = float(overall_rows["amount"].iloc[0])

    with st.form("overall_budget_form"):
        st.subheader(f"Overall Budget for {month_label(selected_month)}")
        overall_amount = st.number_input("Overall monthly budget", min_value=0.0, value=overall_current, step=100.0)
        if st.form_submit_button("Save Overall Budget"):
            run_db_action(
                lambda: db.upsert_budget(selected_month, overall_amount, None),
                "Overall budget saved.",
            )

    with st.form("category_budget_form"):
        st.subheader("Category Budget")
        category_name = st.selectbox("Category", list(category_map.keys()))
        budget_amount = st.number_input("Category budget amount", min_value=0.0, step=50.0)
        if st.form_submit_button("Save Category Budget"):
            run_db_action(
                lambda: db.upsert_budget(selected_month, budget_amount, int(category_map[category_name])),
                "Category budget saved.",
            )

    st.subheader("Budget Performance")
    if budgets.empty:
        st.info("No budgets configured yet.")
    else:
        category_budgets = budgets[budgets["category_id"].notna()].copy()
        if category_budgets.empty:
            st.info("Set category budgets to see budget warnings.")
        else:
            spent_by_category = (
                month_expenses.groupby("category", as_index=False)["amount"].sum() if not month_expenses.empty else pd.DataFrame(columns=["category", "amount"])
            )
            performance = category_budgets.merge(
                spent_by_category,
                left_on="budget_name",
                right_on="category",
                how="left",
            ).fillna({"amount_y": 0.0})
            performance = performance.rename(columns={"amount_x": "budget_amount", "amount_y": "spent_amount"})
            performance["remaining"] = performance["budget_amount"] - performance["spent_amount"]
            performance["used_pct"] = performance.apply(
                lambda row: safe_percentage(row["spent_amount"], row["budget_amount"]),
                axis=1,
            )
            styled = performance[["budget_name", "budget_amount", "spent_amount", "remaining", "used_pct"]].copy()
            st.dataframe(styled, use_container_width=True, hide_index=True)
            overspent = performance[performance["remaining"] < 0]
            if not overspent.empty:
                for _, row in overspent.iterrows():
                    st.warning(f'{row["budget_name"]} exceeded by {format_currency(abs(row["remaining"]))}.')

    if not budgets.empty:
        st.subheader("Existing Budgets")
        st.dataframe(budgets, use_container_width=True, hide_index=True)
        budget_options = {
            f'#{int(row["id"])} | {row["budget_name"]} | {format_currency(row["amount"])}': int(row["id"])
            for _, row in budgets.iterrows()
        }
        selected_budget = st.selectbox("Budget to delete", list(budget_options.keys()))
        if st.button("Delete Selected Budget"):
            run_db_action(lambda: db.delete_budget(budget_options[selected_budget]), "Budget deleted.")


def render_members_page(db: ExpenseDatabase, data: dict[str, pd.DataFrame]) -> None:
    st.title("Manage Members")
    members = data["members"]
    categories = data["categories"]

    left, right = st.columns(2)
    with left:
        with st.form("member_form", clear_on_submit=True):
            st.subheader("Add Member")
            name = st.text_input("Name")
            role = st.text_input("Role", placeholder="Primary, Partner, Child")
            if st.form_submit_button("Save Member"):
                if not name.strip():
                    st.error("Member name is required.")
                else:
                    run_db_action(lambda: db.add_member(name, role), "Member added.")

        st.subheader("Members")
        st.dataframe(members, use_container_width=True, hide_index=True)
        if not members.empty:
            member_options = {
                f'#{int(row["id"])} | {row["name"]} | {"Active" if row["is_active"] else "Inactive"}': int(row["id"])
                for _, row in members.iterrows()
            }
            selected_member = st.selectbox("Select member", list(member_options.keys()))
            member_id = member_options[selected_member]
            record = members[members["id"] == member_id].iloc[0]
            with st.form("edit_member_form"):
                edit_name = st.text_input("Edit name", value=record["name"])
                edit_role = st.text_input("Edit role", value=record["role"] or "")
                edit_active = st.checkbox("Active", value=bool(record["is_active"]))
                update_col, delete_col = st.columns(2)
                if update_col.form_submit_button("Update Member"):
                    run_db_action(
                        lambda: db.update_member(member_id, edit_name, edit_role, edit_active),
                        "Member updated.",
                    )
                if delete_col.form_submit_button("Delete Member"):
                    run_db_action(lambda: db.delete_member(member_id), "Member deleted.")

    with right:
        with st.form("category_form", clear_on_submit=True):
            st.subheader("Add Custom Category")
            category_name = st.text_input("Category name", placeholder="Travel, Gifts, Repairs")
            if st.form_submit_button("Save Category"):
                if not category_name.strip():
                    st.error("Category name is required.")
                else:
                    run_db_action(lambda: db.add_category(category_name), "Category added.")

        st.subheader("Categories")
        st.dataframe(categories, use_container_width=True, hide_index=True)
        if not categories.empty:
            category_options = {
                f'#{int(row["id"])} | {row["name"]}': int(row["id"])
                for _, row in categories.iterrows()
            }
            selected_category = st.selectbox("Category to delete", list(category_options.keys()))
            if st.button("Delete Selected Category"):
                run_db_action(lambda: db.delete_category(category_options[selected_category]), "Category deleted.")


def main() -> None:
    db = get_database()
    data = load_data(db)
    selected_month, page, is_dark = sidebar_controls(data)
    apply_theme(is_dark)

    if page == "Dashboard":
        render_dashboard(db, data, selected_month)
    elif page == "Add Income":
        render_income_page(db, data)
    elif page == "Add Expense":
        render_expense_page(db, data)
    elif page == "Reports":
        render_reports_page(data, selected_month)
    elif page == "Budget Settings":
        render_budget_page(db, data, selected_month)
    elif page == "Manage Members":
        render_members_page(db, data)


if __name__ == "__main__":
    main()
