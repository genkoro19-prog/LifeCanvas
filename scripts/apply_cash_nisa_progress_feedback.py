from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:160]!r}")
    write(path, text.replace(old, new, 1))


def replace_between(path: str, start: str, end: str, new_block: str) -> None:
    text = read(path)
    start_index = text.find(start)
    if start_index < 0:
        raise RuntimeError(f"Start marker not found in {path}: {start!r}")
    end_index = text.find(end, start_index)
    if end_index < 0:
        raise RuntimeError(f"End marker not found in {path}: {end!r}")
    write(path, text[:start_index] + new_block + text[end_index:])


# ---------------------------------------------------------------------------
# Models: wife cash target, husband minimum-line diagnostics, NISA book progress
# ---------------------------------------------------------------------------
replace_once(
    "src/lifecanvas/models.py",
    '''    wife_contribution_threshold_monthly: float = Field(default=30_000, ge=0)\n    wife_use_existing_cash_for_household: bool = False\n    husband_minimum_cash: float = Field(default=1_000_000, ge=0)\n''',
    '''    wife_contribution_threshold_monthly: float = Field(default=30_000, ge=0)\n    wife_use_existing_cash_for_household: bool = False\n    wife_target_cash: float = Field(default=3_000_000, ge=0)\n    husband_minimum_cash: float = Field(default=1_000_000, ge=0)\n''',
)
replace_once(
    "src/lifecanvas/models.py",
    '''    husband_cash_end: float = 0\n    wife_cash_end: float = 0\n    husband_nisa_contributed: float = 0\n''',
    '''    husband_cash_end: float = 0\n    wife_cash_end: float = 0\n    husband_minimum_cash_shortfall: float = 0\n    husband_minimum_cash_breach_months: int = 0\n    husband_nisa_contributed: float = 0\n''',
)
replace_once(
    "src/lifecanvas/models.py",
    '''    spouse_nisa_transfer: float = 0\n    husband_nisa_market_value: float = 0\n    wife_nisa_market_value: float = 0\n''',
    '''    spouse_nisa_transfer: float = 0\n    husband_nisa_cumulative_contributed: float = 0\n    wife_nisa_cumulative_contributed: float = 0\n    husband_nisa_market_value: float = 0\n    wife_nisa_market_value: float = 0\n''',
)


# ---------------------------------------------------------------------------
# Detailed wallet UI
# ---------------------------------------------------------------------------
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''        self.wife_contribution_threshold = NumberEdit(30_000, "円/月")\n        self.wife_household_monthly = NumberEdit(100_000, "円/月")\n        self.use_wife_cash = QCheckBox("収入不足時に妻の既存預金も家計へ使う")\n''',
    '''        self.wife_contribution_threshold = NumberEdit(30_000, "円/月")\n        self.wife_household_monthly = NumberEdit(100_000, "円/月")\n        self.wife_target_cash = NumberEdit(3_000_000)\n        self.use_wife_cash = QCheckBox("収入不足時に妻の既存預金も家計へ使う")\n''',
)
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''        form.addRow("家計拠出を始める余剰基準", self.wife_contribution_threshold)\n        form.addRow("家計負担上限", self.wife_household_monthly)\n        form.addRow(self.use_wife_cash)\n''',
    '''        form.addRow("家計拠出を始める余剰基準", self.wife_contribution_threshold)\n        form.addRow("家計負担上限", self.wife_household_monthly)\n        form.addRow("妻の目標預金", self.wife_target_cash)\n        form.addRow(self.use_wife_cash)\n''',
)
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '        self.auto_invest = QCheckBox("夫の目標預金を超えた余剰を夫NISAへ自動追加する")\n',
    '        self.auto_invest = QCheckBox("夫婦それぞれの目標預金を超えた余剰を本人NISAへ自動追加する")\n',
)
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''            self.wife_contribution_threshold,\n            self.wife_household_monthly,\n            self.auto_extra_cap,\n''',
    '''            self.wife_contribution_threshold,\n            self.wife_household_monthly,\n            self.wife_target_cash,\n            self.auto_extra_cap,\n''',
)
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''            self.wife_contribution_threshold.set_value(wallet.wife_contribution_threshold_monthly)\n            self.wife_household_monthly.set_value(wallet.wife_household_monthly)\n            self.husband_household_monthly.set_value(wallet.husband_household_monthly)\n''',
    '''            self.wife_contribution_threshold.set_value(wallet.wife_contribution_threshold_monthly)\n            self.wife_household_monthly.set_value(wallet.wife_household_monthly)\n            self.wife_target_cash.set_value(wallet.wife_target_cash)\n            self.husband_household_monthly.set_value(wallet.husband_household_monthly)\n''',
)
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''            wife_contribution_threshold_monthly=self.wife_contribution_threshold.value(),\n            wife_use_existing_cash_for_household=self.use_wife_cash.isChecked(),\n            husband_minimum_cash=self.husband_minimum_cash.value(),\n''',
    '''            wife_contribution_threshold_monthly=self.wife_contribution_threshold.value(),\n            wife_use_existing_cash_for_household=self.use_wife_cash.isChecked(),\n            wife_target_cash=self.wife_target_cash.value(),\n            husband_minimum_cash=self.husband_minimum_cash.value(),\n''',
)


# ---------------------------------------------------------------------------
# Quick policy UI
# ---------------------------------------------------------------------------
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '        policy = QGroupBox("育休時の家計と夫の預金")\n',
    '        policy = QGroupBox("育休時の家計と夫婦の預金")\n',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        self.wife_cap = NumberEdit(100_000, "円/月")\n        self.husband_minimum = NumberEdit(1_000_000)\n''',
    '''        self.wife_cap = NumberEdit(100_000, "円/月")\n        self.wife_target = NumberEdit(3_000_000)\n        self.husband_minimum = NumberEdit(1_000_000)\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        form.addRow("妻の家計負担上限", self.wife_cap)\n        form.addRow("夫の最低維持預金", self.husband_minimum)\n''',
    '''        form.addRow("妻の家計負担上限", self.wife_cap)\n        form.addRow("妻の目標預金", self.wife_target)\n        form.addRow("夫の最低維持預金", self.husband_minimum)\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''            self.wife_cap,\n            self.husband_minimum,\n''',
    '''            self.wife_cap,\n            self.wife_target,\n            self.husband_minimum,\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        wallet.wife_household_monthly = self.wife_cap.value()\n        wallet.husband_minimum_cash = self.husband_minimum.value()\n''',
    '''        wallet.wife_household_monthly = self.wife_cap.value()\n        wallet.wife_target_cash = self.wife_target.value()\n        wallet.husband_minimum_cash = self.husband_minimum.value()\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        self.wife_cap.set_value(wallet.wife_household_monthly)\n        self.husband_minimum.set_value(wallet.husband_minimum_cash)\n''',
    '''        self.wife_cap.set_value(wallet.wife_household_monthly)\n        self.wife_target.set_value(wallet.wife_target_cash)\n        self.husband_minimum.set_value(wallet.husband_minimum_cash)\n''',
)


# ---------------------------------------------------------------------------
# Policy engine: reserve monthly cash growth, target-gated wife auto-invest,
# minimum-line diagnostics, cumulative NISA principal and milestone events.
# ---------------------------------------------------------------------------
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''    spouse_transfer: float = 0.0\n    planned_nisa: float = 0.0\n''',
    '''    spouse_transfer: float = 0.0\n    planned_nisa: float = 0.0\n    husband_minimum_breach_months: int = 0\n    husband_minimum_shortfall_max: float = 0.0\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''def _nisa_room(state: NisaState | None) -> float:\n    if state is None:\n        return 0.0\n    annual = max(0.0, state.plan.annual_limit - state.annual_purchased)\n    lifetime = max(0.0, state.plan.lifetime_limit - state.used_lifetime_limit)\n    return min(annual, lifetime)\n\n\n''',
    '''def _nisa_room(state: NisaState | None) -> float:\n    if state is None:\n        return 0.0\n    annual = max(0.0, state.plan.annual_limit - state.annual_purchased)\n    lifetime = max(0.0, state.plan.lifetime_limit - state.used_lifetime_limit)\n    return min(annual, lifetime)\n\n\ndef _nisa_milestone_events(\n    owner_label: str,\n    before: float,\n    after: float,\n    lifetime_limit: float,\n) -> list[str]:\n    if lifetime_limit <= 0:\n        return []\n    events: list[str] = []\n    for ratio, label in ((0.25, "1/4"), (0.5, "1/2"), (1.0, "1/1（満額）")):\n        threshold = lifetime_limit * ratio\n        if before + 1 < threshold <= after + 1:\n            events.append(\n                f"{owner_label}NISA {label}到達（買付元本累計{after/10_000:,.0f}万円）"\n            )\n    return events\n\n\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            for state in states.values():\n                state.begin_year()\n            year = YearAllocation()\n''',
    '''            for state in states.values():\n                state.begin_year()\n            husband_lifetime_before = husband_state.used_lifetime_limit if husband_state else 0.0\n            wife_lifetime_before = wife_state.used_lifetime_limit if wife_state else 0.0\n            year = YearAllocation()\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            for _month in range(months):\n                husband_cash += husband_monthly_income + household_monthly_surplus\n                wife_cash += wife_monthly_income\n''',
    '''            for _month in range(months):\n                husband_month_opening = husband_cash\n                husband_cash += husband_monthly_income + household_monthly_surplus\n                wife_cash += wife_monthly_income\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                husband_cash, paid, unmet = _pay_from_cash(husband_cash, wallets.husband_personal_spending_monthly)\n                year.husband_spending += paid\n                year.husband_unmet += unmet\n''',
    '''                husband_spending_available = max(0.0, husband_cash - wallets.husband_minimum_cash)\n                husband_spending_desired = wallets.husband_personal_spending_monthly\n                paid = min(husband_spending_available, husband_spending_desired)\n                husband_cash -= paid\n                year.husband_spending += paid\n                year.husband_unmet += husband_spending_desired - paid\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                saving_reserve = 0.0\n                if husband_cash < wallets.husband_target_cash:\n                    saving_reserve = min(wallets.husband_monthly_saving_until_target, wallets.husband_target_cash - husband_cash)\n                husband_base_desired = husband_state.plan.monthly_for_offset(raw.offset) if husband_state else 0.0\n                year.planned_nisa += husband_base_desired\n                husband_cash, husband_base = _buy_from_cash(\n                    husband_cash,\n                    husband_state,\n                    husband_base_desired,\n                    reserve=wallets.husband_minimum_cash + saving_reserve,\n                )\n''',
    '''                if husband_month_opening < wallets.husband_target_cash:\n                    husband_cash_goal = min(\n                        wallets.husband_target_cash,\n                        max(\n                            wallets.husband_minimum_cash,\n                            husband_month_opening + wallets.husband_monthly_saving_until_target,\n                        ),\n                    )\n                else:\n                    husband_cash_goal = max(\n                        wallets.husband_minimum_cash,\n                        wallets.husband_target_cash,\n                    )\n                husband_base_desired = husband_state.plan.monthly_for_offset(raw.offset) if husband_state else 0.0\n                year.planned_nisa += husband_base_desired\n                husband_cash, husband_base = _buy_from_cash(\n                    husband_cash,\n                    husband_state,\n                    husband_base_desired,\n                    reserve=husband_cash_goal,\n                )\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                if wallets.auto_invest_enabled:\n                    # Wife surplus remains in the wife's cash account. Only her configured\n                    # base NISA is paid from her own income; husband-funded additions are\n                    # processed by the explicit spouse-transfer rule below.\n                    husband_extra_desired = min(\n''',
    '''                if wallets.auto_invest_enabled:\n                    wife_extra_desired = min(\n                        wallets.auto_extra_monthly_cap,\n                        max(0.0, wife_cash - wallets.wife_target_cash),\n                    )\n                    wife_cash, wife_extra = _buy_from_cash(\n                        wife_cash,\n                        wife_state,\n                        wife_extra_desired,\n                        reserve=wallets.wife_target_cash,\n                    )\n                    year.wife_extra_nisa += wife_extra\n                    year.planned_nisa += wife_extra_desired\n\n                    husband_extra_desired = min(\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                        year.wife_extra_nisa += actual_transfer\n                        year.planned_nisa += transfer_desired\n                absolute_month += 1\n''',
    '''                        year.wife_extra_nisa += actual_transfer\n                        year.planned_nisa += transfer_desired\n\n                husband_shortfall = max(0.0, wallets.husband_minimum_cash - husband_cash)\n                if husband_shortfall > 1:\n                    year.husband_minimum_breach_months += 1\n                    year.husband_minimum_shortfall_max = max(\n                        year.husband_minimum_shortfall_max, husband_shortfall\n                    )\n                absolute_month += 1\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            events = _clean_finance_messages(list(raw.events))\n            warnings = _clean_finance_messages(list(raw.warnings))\n''',
    '''            husband_cumulative = husband_state.used_lifetime_limit if husband_state else 0.0\n            wife_cumulative = wife_state.used_lifetime_limit if wife_state else 0.0\n            events = _clean_finance_messages(list(raw.events))\n            warnings = _clean_finance_messages(list(raw.warnings))\n            if husband_state:\n                events.extend(\n                    _nisa_milestone_events(\n                        "夫",\n                        husband_lifetime_before,\n                        husband_cumulative,\n                        husband_state.plan.lifetime_limit,\n                    )\n                )\n            if wife_state:\n                events.extend(\n                    _nisa_milestone_events(\n                        "妻",\n                        wife_lifetime_before,\n                        wife_cumulative,\n                        wife_state.plan.lifetime_limit,\n                    )\n                )\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            if husband_cash < wallets.husband_minimum_cash:\n                warnings.append(\n                    f"夫の預金が最低維持預金を{(wallets.husband_minimum_cash-husband_cash)/10_000:,.0f}万円下回る"\n                )\n''',
    '''            if year.husband_minimum_breach_months:\n                warnings.append(\n                    f"夫の最低維持預金を最大{year.husband_minimum_shortfall_max/10_000:,.0f}万円下回る"\n                    f"（{year.husband_minimum_breach_months}か月）"\n                )\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            row.husband_cash_end = max(0.0, husband_cash)\n            row.wife_cash_end = max(0.0, wife_cash)\n            row.husband_nisa_contributed = husband_contributed\n''',
    '''            row.husband_cash_end = max(0.0, husband_cash)\n            row.wife_cash_end = max(0.0, wife_cash)\n            row.husband_minimum_cash_shortfall = year.husband_minimum_shortfall_max\n            row.husband_minimum_cash_breach_months = year.husband_minimum_breach_months\n            row.husband_nisa_contributed = husband_contributed\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''            row.spouse_nisa_transfer = year.spouse_transfer\n            row.husband_nisa_market_value = husband_market\n''',
    '''            row.spouse_nisa_transfer = year.spouse_transfer\n            row.husband_nisa_cumulative_contributed = husband_cumulative\n            row.wife_nisa_cumulative_contributed = wife_cumulative\n            row.husband_nisa_market_value = husband_market\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''    else:\n        floor = 0.0\n        values = [row.wife_cash_end for row in results]\n''',
    '''    else:\n        floor = plan.wallets.wife_target_cash\n        values = [row.wife_cash_end for row in results]\n''',
)


# ---------------------------------------------------------------------------
# Annual table and dashboard: yearly contributions, cumulative principal,
# progress, market value, minimum cash status and full-year visibility.
# ---------------------------------------------------------------------------
replace_once(
    "src/lifecanvas/revision_ui.py",
    '''from .wallet_engine import SimulationEngine, recommend_monthly_contributions\n\n# Keep all inherited calculation and export paths on the revised implementations.\n''',
    '''from .wallet_engine import SimulationEngine, recommend_monthly_contributions\n\n\ndef _nisa_limit(plan, owner: str) -> float:\n    return next(\n        (account.lifetime_limit for account in plan.nisa_accounts if account.owner == owner),\n        0.0,\n    )\n\n\ndef _nisa_progress_text(cumulative: float, lifetime_limit: float) -> str:\n    if lifetime_limit <= 0:\n        return "-"\n    ratio = max(0.0, min(1.0, cumulative / lifetime_limit))\n    milestone = "1/1" if ratio >= 1 else "1/2" if ratio >= 0.5 else "1/4" if ratio >= 0.25 else ""\n    return f"{milestone + ' ' if milestone else ''}{ratio*100:.0f}%"\n\n\ndef _nisa_reached_year(results, attribute: str, lifetime_limit: float, ratio: float) -> str:\n    threshold = lifetime_limit * ratio\n    row = next((item for item in results if getattr(item, attribute, 0.0) + 1 >= threshold), None)\n    return f"{row.calendar_year}年" if row else "期間内未到達"\n\n\n# Keep all inherited calculation and export paths on the revised implementations.\n''',
)
replace_between(
    "src/lifecanvas/revision_ui.py",
    "    def _configure_annual_table(self) -> None:\n",
    "    def _refresh_table(self) -> None:\n",
    '''    def _configure_annual_table(self) -> None:\n        headers = [\n            "年",\n            "夫/妻",\n            "夫年収",\n            "妻年収",\n            "給付",\n            "家計費",\n            "夫負担",\n            "妻負担",\n            "家計不足",\n            "夫個人支出",\n            "妻個人支出",\n            "夫預金増減",\n            "妻預金増減",\n            "夫預金",\n            "夫最低ライン",\n            "妻預金",\n            "夫NISA年額",\n            "夫NISA累計",\n            "夫NISA進捗",\n            "夫NISA評価",\n            "妻NISA年額",\n            "妻NISA累計",\n            "妻NISA進捗",\n            "妻NISA評価",\n            "投資合計",\n            "純資産",\n        ]\n        self.year_table.setColumnCount(len(headers))\n        self.year_table.setHorizontalHeaderLabels(headers)\n        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)\n        self.year_table.setAlternatingRowColors(True)\n\n''',
)
replace_between(
    "src/lifecanvas/revision_ui.py",
    "    def _refresh_table(self) -> None:\n",
    "    def _refresh_dashboard(self) -> None:\n",
    '''    def _refresh_table(self) -> None:\n        self.year_table.setRowCount(len(self.results))\n        separate = self.plan.wallets.mode == "separate"\n        husband_limit = _nisa_limit(self.plan, "husband")\n        wife_limit = _nisa_limit(self.plan, "wife")\n        for row_index, result in enumerate(self.results):\n            if result.husband_minimum_cash_breach_months:\n                minimum_status = (\n                    f"▲{man(result.husband_minimum_cash_shortfall)} "\n                    f"({result.husband_minimum_cash_breach_months}月)"\n                )\n            else:\n                minimum_status = "OK"\n            if separate:\n                values = [\n                    str(result.calendar_year),\n                    f"{result.husband_age}/{result.wife_age}",\n                    man(result.husband_gross),\n                    man(result.wife_gross),\n                    man(result.benefits),\n                    man(result.household_cost_net),\n                    man(result.husband_household_paid),\n                    man(result.wife_household_paid),\n                    man(result.household_shortfall),\n                    man(result.husband_personal_spending),\n                    man(result.wife_personal_spending),\n                    man(result.husband_savings_change),\n                    man(result.wife_savings_change),\n                    man(result.husband_cash_end),\n                    minimum_status,\n                    man(result.wife_cash_end),\n                    man(result.husband_nisa_contributed),\n                    man(result.husband_nisa_cumulative_contributed),\n                    _nisa_progress_text(result.husband_nisa_cumulative_contributed, husband_limit),\n                    man(result.husband_nisa_market_value),\n                    man(result.wife_nisa_contributed),\n                    man(result.wife_nisa_cumulative_contributed),\n                    _nisa_progress_text(result.wife_nisa_cumulative_contributed, wife_limit),\n                    man(result.wife_nisa_market_value),\n                    man(result.investments_market_value),\n                    man(result.net_worth),\n                ]\n            else:\n                values = [\n                    str(result.calendar_year),\n                    f"{result.husband_age}/{result.wife_age}",\n                    man(result.husband_gross),\n                    man(result.wife_gross),\n                    man(result.benefits),\n                    man(result.consumption_total),\n                    "-", "-", "-", "-", "-", "-", "-",\n                    man(result.cash_end),\n                    "-",\n                    "-",\n                    man(result.nisa_contributed),\n                    man(result.investments_book_value),\n                    "-",\n                    man(result.investments_market_value),\n                    "-", "-", "-", "-",\n                    man(result.investments_market_value),\n                    man(result.net_worth),\n                ]\n            for column, value in enumerate(values):\n                self.year_table.setItem(row_index, column, QTableWidgetItem(value))\n        if self.results:\n            self.year_table.selectRow(0)\n\n''',
)
replace_once(
    "src/lifecanvas/revision_ui.py",
    '''                + f"妻NISA {man(final.wife_nisa_market_value)}"\n            )\n            self.dashboard_summary.setPlainText(wallet_text)\n''',
    '''                + f"妻NISA {man(final.wife_nisa_market_value)}"\n                + "\\n【NISA買付元本と到達年】\\n"\n                + f"夫 累計{man(final.husband_nisa_cumulative_contributed)} / "\n                + f"1/4 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 0.25)} / "\n                + f"1/2 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 0.5)} / "\n                + f"1/1 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 1.0)}\\n"\n                + f"妻 累計{man(final.wife_nisa_cumulative_contributed)} / "\n                + f"1/4 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 0.25)} / "\n                + f"1/2 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 0.5)} / "\n                + f"1/1 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 1.0)}"\n            )\n            self.dashboard_summary.setPlainText(wallet_text)\n''',
)


# Timeline: surface NISA 1/4, 1/2 and full milestones from simulation events.
replace_once(
    "src/lifecanvas/compact_timeline.py",
    '''                elif any(name and name in text for name in car_names):\n                    events.append(LifeEvent(result.offset, "car", text))\n            if result.warnings:\n''',
    '''                elif any(name and name in text for name in car_names):\n                    events.append(LifeEvent(result.offset, "car", text))\n                elif "NISA 1/" in text:\n                    events.append(LifeEvent(result.offset, "assets", text))\n            if result.warnings:\n''',
)


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------
replace_once(
    "tests/test_revision_features.py",
    '    assert window.year_table.columnCount() == 19\n',
    '    assert window.year_table.columnCount() == 26\n',
)
replace_once(
    "tests/test_compact_policy_ui.py",
    '''        assert window.quick_policy is not None\n        assert window.personal_debt_editor is not None\n''',
    '''        assert window.quick_policy is not None\n        assert window.quick_policy.wife_target.value() == window.plan.wallets.wife_target_cash\n        assert window.personal_debt_editor is not None\n''',
)
append_tests = '''\n\ndef test_husband_monthly_cash_goal_is_reserved_before_base_nisa(monkeypatch):\n    plan, rows = _plan(wife_income=0, household=0)\n    plan.wallets.initial_husband_cash = 1_000_000\n    plan.wallets.husband_minimum_cash = 1_000_000\n    plan.wallets.husband_target_cash = 2_000_000\n    plan.wallets.husband_monthly_saving_until_target = 50_000\n    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")\n    husband.monthly_contribution = 500_000\n    husband.annual_limit = 100_000_000\n    husband.lifetime_limit = 100_000_000\n    rows[0].husband_gross = 4_200_000\n    rows[0].salary_net = 4_200_000\n    rows[0].total_income = 4_200_000\n    row = _run(plan, rows, monkeypatch)\n    assert row.husband_cash_end == pytest.approx(1_600_000)\n    assert row.husband_minimum_cash_breach_months == 0\n\n\ndef test_husband_minimum_line_breach_is_reported(monkeypatch):\n    plan, rows = _plan(wife_income=0, household=600_000)\n    plan.wallets.initial_husband_cash = 1_000_000\n    plan.wallets.husband_minimum_cash = 1_000_000\n    plan.husband.annual_gross_income = 0\n    rows[0].husband_gross = 0\n    rows[0].salary_net = 0\n    rows[0].total_income = 0\n    row = _run(plan, rows, monkeypatch)\n    assert row.husband_cash_end == pytest.approx(400_000)\n    assert row.husband_minimum_cash_shortfall == pytest.approx(600_000)\n    assert row.husband_minimum_cash_breach_months == 12\n    assert any("最低維持預金" in warning for warning in row.warnings)\n\n\ndef test_wife_target_cash_gates_automatic_extra_nisa(monkeypatch):\n    plan, rows = _plan(wife_income=1_200_000, household=0)\n    plan.wallets.initial_wife_cash = 2_900_000\n    plan.wallets.wife_personal_spending_monthly = 0\n    plan.wallets.wife_target_cash = 3_000_000\n    plan.wallets.auto_invest_enabled = True\n    plan.wallets.spouse_nisa_transfer_enabled = False\n    plan.wallets.husband_target_cash = 100_000_000\n    wife = next(account for account in plan.nisa_accounts if account.owner == "wife")\n    wife.monthly_contribution = 0\n    wife.annual_limit = 100_000_000\n    wife.lifetime_limit = 100_000_000\n    row = _run(plan, rows, monkeypatch)\n    assert row.wife_cash_end == pytest.approx(3_000_000)\n    assert row.wife_additional_nisa_contributed == pytest.approx(1_100_000)\n\n\ndef test_nisa_cumulative_progress_and_milestone_events(monkeypatch):\n    plan, rows = _plan(wife_income=0, household=0, years=5)\n    plan.wallets.husband_minimum_cash = 0\n    plan.wallets.husband_target_cash = 0\n    plan.wallets.husband_monthly_saving_until_target = 0\n    husband = next(account for account in plan.nisa_accounts if account.owner == "husband")\n    husband.monthly_contribution = 300_000\n    monkeypatch.setattr(\n        policy_engine,\n        "HousingSimulationEngine",\n        lambda _plan: type("RawEngine", (), {"run": lambda self: rows})(),\n    )\n    results = SimulationEngine(plan).run()\n    assert results[0].husband_nisa_contributed == pytest.approx(3_600_000)\n    assert results[1].husband_nisa_cumulative_contributed == pytest.approx(7_200_000)\n    assert any("夫NISA 1/4" in event for event in results[1].events)\n    assert any("夫NISA 1/2" in event for event in results[2].events)\n    assert results[4].husband_nisa_cumulative_contributed == pytest.approx(18_000_000)\n    assert any("夫NISA 1/1" in event for event in results[4].events)\n'''
path = "tests/test_household_policy_phases.py"
text = read(path)
if "test_husband_monthly_cash_goal_is_reserved_before_base_nisa" not in text:
    write(path, text.rstrip() + append_tests + "\n")


# ---------------------------------------------------------------------------
# Implementation notes
# ---------------------------------------------------------------------------
path = "docs/IMPLEMENTATION_HOUSEHOLD_NISA_DEBT_UI.md"
text = read(path)
addition = '''\n## 追加フィードバック: 預金目標とNISA進捗\n\n- 妻の目標預金を追加し、詳細設定・かんたん入力の双方から編集可能にした\n- 自動追加投資ON時は、妻の目標預金を超えた部分だけを妻本人NISAへ追加する\n- 夫の基本NISA計算前に、前月残高へ月間基本貯金額を積み上げた現金目標を確保する\n- 夫の個人支出は最低維持預金を割り込ませない\n- 家計・借入などで最低維持預金を割った月数と最大不足額を年別に記録する\n- 年別表へ夫婦それぞれのNISA年額、買付元本累計、進捗、評価額を追加した\n- NISA買付元本が1/4、1/2、1/1へ到達した年を結果画面と年表へ表示する\n'''
if "## 追加フィードバック: 預金目標とNISA進捗" not in text:
    write(path, text.rstrip() + "\n" + addition)

print("Applied wife target, husband cash floor, and NISA progress feedback.")
