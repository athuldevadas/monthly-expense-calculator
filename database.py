from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from models import DEFAULT_CATEGORIES, DEFAULT_MEMBERS


class ExpenseDatabase:
    def __init__(self, db_path: str | Path = "expense_tracker.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Any:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    role TEXT DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS incomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT NOT NULL,
                    source TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    assigned_type TEXT NOT NULL CHECK(assigned_type IN ('Family', 'Member')),
                    member_id INTEGER,
                    recurring INTEGER NOT NULL DEFAULT 0,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    category_id INTEGER NOT NULL,
                    description TEXT DEFAULT '',
                    expense_type TEXT NOT NULL CHECK(expense_type IN ('Family / Shared', 'Individual')),
                    member_id INTEGER,
                    payment_method TEXT DEFAULT '',
                    recurring INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT,
                    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    budget_month TEXT NOT NULL,
                    category_id INTEGER,
                    amount REAL NOT NULL CHECK(amount >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
                    UNIQUE (budget_month, category_id)
                );

                CREATE INDEX IF NOT EXISTS idx_incomes_date ON incomes(entry_date);
                CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(entry_date);
                CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
                CREATE INDEX IF NOT EXISTS idx_budgets_month ON budgets(budget_month);
                """
            )
            self._seed_defaults(conn)

    def _seed_defaults(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            "INSERT OR IGNORE INTO members(name, role, is_active) VALUES (?, ?, 1)",
            DEFAULT_MEMBERS,
        )
        conn.executemany(
            "INSERT OR IGNORE INTO categories(name, is_default) VALUES (?, 1)",
            [(category,) for category in DEFAULT_CATEGORIES],
        )

    def query_df(self, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self.connect() as conn:
            conn.execute(query, params)

    def execute_many(self, query: str, params: list[tuple[Any, ...]]) -> None:
        with self.connect() as conn:
            conn.executemany(query, params)

    def get_members(self, active_only: bool = False) -> pd.DataFrame:
        query = "SELECT id, name, role, is_active, created_at FROM members"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY is_active DESC, name"
        return self.query_df(query)

    def add_member(self, name: str, role: str) -> None:
        self.execute(
            "INSERT INTO members(name, role, is_active) VALUES (?, ?, 1)",
            (name.strip(), role.strip()),
        )

    def update_member(self, member_id: int, name: str, role: str, is_active: bool) -> None:
        self.execute(
            """
            UPDATE members
            SET name = ?, role = ?, is_active = ?
            WHERE id = ?
            """,
            (name.strip(), role.strip(), int(is_active), member_id),
        )

    def delete_member(self, member_id: int) -> None:
        self.execute("DELETE FROM members WHERE id = ?", (member_id,))

    def get_categories(self) -> pd.DataFrame:
        return self.query_df(
            "SELECT id, name, is_default, created_at FROM categories ORDER BY name"
        )

    def add_category(self, name: str) -> None:
        self.execute(
            "INSERT INTO categories(name, is_default) VALUES (?, 0)",
            (name.strip(),),
        )

    def delete_category(self, category_id: int) -> None:
        self.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    def get_incomes(self) -> pd.DataFrame:
        return self.query_df(
            """
            SELECT
                i.id,
                i.entry_date AS date,
                i.source,
                i.amount,
                i.assigned_type,
                COALESCE(m.name, 'Family') AS assigned_to,
                i.member_id,
                i.recurring,
                i.notes
            FROM incomes i
            LEFT JOIN members m ON m.id = i.member_id
            ORDER BY i.entry_date DESC, i.id DESC
            """
        )

    def add_income(
        self,
        entry_date: str,
        source: str,
        amount: float,
        assigned_type: str,
        member_id: int | None,
        recurring: bool,
        notes: str,
    ) -> None:
        self.execute(
            """
            INSERT INTO incomes(entry_date, source, amount, assigned_type, member_id, recurring, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_date, source.strip(), amount, assigned_type, member_id, int(recurring), notes.strip()),
        )

    def update_income(
        self,
        income_id: int,
        entry_date: str,
        source: str,
        amount: float,
        assigned_type: str,
        member_id: int | None,
        recurring: bool,
        notes: str,
    ) -> None:
        self.execute(
            """
            UPDATE incomes
            SET entry_date = ?, source = ?, amount = ?, assigned_type = ?, member_id = ?,
                recurring = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                entry_date,
                source.strip(),
                amount,
                assigned_type,
                member_id,
                int(recurring),
                notes.strip(),
                income_id,
            ),
        )

    def delete_income(self, income_id: int) -> None:
        self.execute("DELETE FROM incomes WHERE id = ?", (income_id,))

    def get_expenses(self) -> pd.DataFrame:
        return self.query_df(
            """
            SELECT
                e.id,
                e.entry_date AS date,
                e.amount,
                c.name AS category,
                e.category_id,
                e.description,
                e.expense_type,
                COALESCE(m.name, 'Family') AS member_name,
                e.member_id,
                e.payment_method,
                e.recurring
            FROM expenses e
            JOIN categories c ON c.id = e.category_id
            LEFT JOIN members m ON m.id = e.member_id
            ORDER BY e.entry_date DESC, e.id DESC
            """
        )

    def add_expense(
        self,
        entry_date: str,
        amount: float,
        category_id: int,
        description: str,
        expense_type: str,
        member_id: int | None,
        payment_method: str,
        recurring: bool,
    ) -> None:
        self.execute(
            """
            INSERT INTO expenses(entry_date, amount, category_id, description, expense_type, member_id, payment_method, recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_date,
                amount,
                category_id,
                description.strip(),
                expense_type,
                member_id,
                payment_method,
                int(recurring),
            ),
        )

    def update_expense(
        self,
        expense_id: int,
        entry_date: str,
        amount: float,
        category_id: int,
        description: str,
        expense_type: str,
        member_id: int | None,
        payment_method: str,
        recurring: bool,
    ) -> None:
        self.execute(
            """
            UPDATE expenses
            SET entry_date = ?, amount = ?, category_id = ?, description = ?, expense_type = ?,
                member_id = ?, payment_method = ?, recurring = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                entry_date,
                amount,
                category_id,
                description.strip(),
                expense_type,
                member_id,
                payment_method,
                int(recurring),
                expense_id,
            ),
        )

    def delete_expense(self, expense_id: int) -> None:
        self.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))

    def get_budgets(self, budget_month: str | None = None) -> pd.DataFrame:
        query = """
            SELECT
                b.id,
                b.budget_month,
                b.amount,
                b.category_id,
                COALESCE(c.name, 'Overall Budget') AS budget_name
            FROM budgets b
            LEFT JOIN categories c ON c.id = b.category_id
        """
        params: tuple[Any, ...] = ()
        if budget_month:
            query += " WHERE b.budget_month = ?"
            params = (budget_month,)
        query += " ORDER BY b.budget_month DESC, budget_name"
        return self.query_df(query, params)

    def upsert_budget(self, budget_month: str, amount: float, category_id: int | None = None) -> None:
        with self.connect() as conn:
            if category_id is None:
                existing = conn.execute(
                    "SELECT id FROM budgets WHERE budget_month = ? AND category_id IS NULL",
                    (budget_month,),
                ).fetchone()
            else:
                existing = conn.execute(
                    "SELECT id FROM budgets WHERE budget_month = ? AND category_id = ?",
                    (budget_month, category_id),
                ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE budgets SET amount = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (amount, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO budgets(budget_month, category_id, amount) VALUES (?, ?, ?)",
                    (budget_month, category_id, amount),
                )

    def delete_budget(self, budget_id: int) -> None:
        self.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
