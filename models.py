from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MEMBERS = [
    ("User", "Primary"),
    ("Spouse", "Partner"),
    ("Child 1", "Child"),
]

DEFAULT_CATEGORIES = [
    "Rent / Mortgage",
    "Groceries",
    "Utilities",
    "Transport",
    "Medical",
    "Education",
    "Insurance",
    "Dining",
    "Entertainment",
    "Shopping",
    "Subscriptions",
    "Savings / Investments",
    "Miscellaneous",
]

PAYMENT_METHODS = [
    "Cash",
    "Debit Card",
    "Credit Card",
    "Bank Transfer",
    "UPI / Digital Wallet",
    "Auto Debit",
    "Other",
]

EXPENSE_TYPES = ["Family / Shared", "Individual"]
ASSIGNMENT_TYPES = ["Family", "Member"]


@dataclass(frozen=True)
class BudgetScope:
    OVERALL: str = "overall"
    CATEGORY: str = "category"
