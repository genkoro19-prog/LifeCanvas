from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Detailed settings: do not mistake widgets on a hidden tab for intentionally hidden legacy controls.
replace_once(
    "src/lifecanvas/detailed_settings.py",
    '''        widgets = self._take_widgets(legacy_scroll)\n        for widget in widgets:\n            if widget.isHidden() and widget.property("forceCompactVisible") is not True:\n                continue\n            category = self._category_for(widget)\n            page = pages[category]\n''',
    '''        self.category_widget_counts = {category: 0 for category in self.CATEGORIES}\n        widgets = self._take_widgets(legacy_scroll)\n        for widget in widgets:\n            if widget.property("skipCompactSettings") is True:\n                continue\n            category = self._category_for(widget)\n            self.category_widget_counts[category] += 1\n            page = pages[category]\n''',
)
replace_once(
    "src/lifecanvas/detailed_settings.py",
    '''    def _category_for(cls, widget: QWidget) -> str:\n        title = widget.title() if isinstance(widget, QGroupBox) else ""\n''',
    '''    def _category_for(cls, widget: QWidget) -> str:\n        explicit = widget.property("settingsCategory")\n        if explicit in cls.CATEGORIES:\n            return str(explicit)\n        title = widget.title() if isinstance(widget, QGroupBox) else ""\n''',
)

# Explicitly tag each existing settings card instead of relying only on title heuristics.
replace_once(
    "src/lifecanvas/guided_ui.py",
    '''        self.detailed_settings = DetailedSettingsPage(legacy_detail)\n''',
    '''        self._tag_detailed_settings_categories()\n        self.detailed_settings = DetailedSettingsPage(legacy_detail)\n''',
)
replace_once(
    "src/lifecanvas/guided_ui.py",
    '''    def _simplify_guided_investment_group(self) -> None:\n''',
    '''    def _tag_detailed_settings_categories(self) -> None:\n        def parent_of(name: str):\n            widget = getattr(self, name, None)\n            return widget.parentWidget() if widget is not None else None\n\n        assignments = [\n            (parent_of("start_month"), "基本情報"),\n            (getattr(self, "husband_age_income", None), "収入・働き方"),\n            (getattr(self, "wife_age_income", None), "収入・働き方"),\n            (getattr(self, "wallet_editor", None), "家計・預金"),\n            (parent_of("h_nisa_before"), "NISA・投資"),\n            (getattr(self, "child_editor", None), "子ども・教育"),\n            (getattr(self, "housing_editor", None), "住宅"),\n            (getattr(self, "car_editor", None), "車"),\n            (getattr(self, "cashflow_event_editor", None), "借入・イベント"),\n            (getattr(self, "personal_debt_editor", None), "借入・イベント"),\n            (parent_of("h_retire"), "年金・計算条件"),\n            (parent_of("h_retirement_lump"), "年金・計算条件"),\n        ]\n        for widget, category in assignments:\n            if widget is not None:\n                widget.setProperty("settingsCategory", category)\n\n        # These old cards are replaced by the newer editors above.\n        for widget in (\n            parent_of("first_child_offset"),\n            parent_of("loan_amount"),\n            getattr(self, "husband_income_editor", None),\n        ):\n            if widget is not None:\n                widget.setProperty("skipCompactSettings", True)\n\n    def _simplify_guided_investment_group(self) -> None:\n''',
)
replace_once(
    "src/lifecanvas/guided_ui.py",
    '''        wife_household = min(\n            self.quick_policy.wife_cap.value(),\n            max(0.0, wife_after_priority - self.quick_policy.wife_threshold.value()),\n            self.guided_input.living_monthly.value(),\n        )\n''',
    '''        wife_candidate = (\n            wife_after_priority\n            if wife_after_priority > self.quick_policy.wife_threshold.value()\n            else 0.0\n        )\n        wife_household = min(\n            self.quick_policy.wife_cap.value(),\n            wife_candidate,\n            self.guided_input.living_monthly.value(),\n        )\n''',
)
replace_once(
    "src/lifecanvas/guided_ui.py",
    '''            f"家族の生活費 月{self.guided_input.living_monthly.value()/10_000:,.1f}万円／"\n            f"妻は月{self.quick_policy.wife_threshold.value()/10_000:,.1f}万円を残し、"\n            f"上限{self.quick_policy.wife_cap.value()/10_000:,.1f}万円まで拠出／残額は夫負担"\n''',
    '''            f"家族の生活費 月{self.guided_input.living_monthly.value()/10_000:,.1f}万円／"\n            f"妻の余剰が月{self.quick_policy.wife_threshold.value()/10_000:,.1f}万円以下なら拠出0円、"\n            f"超えた月は余剰全体を上限{self.quick_policy.wife_cap.value()/10_000:,.1f}万円まで拠出／残額は夫負担"\n''',
)

# Calculation semantics: the threshold is a gate, not a monthly deduction.
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                wife_candidate = max(0.0, wife_flow_remaining - wallets.wife_contribution_threshold_monthly)\n''',
    '''                wife_candidate = (\n                    wife_flow_remaining\n                    if wife_flow_remaining > wallets.wife_contribution_threshold_monthly\n                    else 0.0\n                )\n''',
)
replace_once(
    "src/lifecanvas/policy_engine.py",
    '''                    wife_extra_available = max(0.0, wife_flow_remaining - wallets.wife_contribution_threshold_monthly)\n''',
    '''                    wife_extra_available = max(0.0, wife_flow_remaining)\n''',
)

# Labels and defaults now describe the gate correctly and avoid the old 7万円 sample cap.
replace_once(
    "src/lifecanvas/wallet_editor.py",
    '''        form.addRow("家計に入れず残す余裕", self.wife_contribution_threshold)\n''',
    '''        form.addRow("家計拠出を始める余剰基準", self.wife_contribution_threshold)\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        form.addRow("妻側に残す余裕", self.wife_threshold)\n''',
    '''        form.addRow("妻の家計拠出開始基準", self.wife_threshold)\n''',
)
replace_once(
    "src/lifecanvas/quick_policy_editor.py",
    '''        note = QLabel("妻は借入・個人支出・本人NISAを優先し、超過分だけ家計へ入れます。")\n''',
    '''        note = QLabel("妻は借入・個人支出・本人NISAを優先し、余剰が基準を超えた月は余剰全体を上限まで家計へ入れます。")\n''',
)
replace_once(
    "src/lifecanvas/models.py",
    '''    wife_household_monthly: float = Field(default=100_000, ge=0)\n''',
    '''    wife_household_monthly: float = Field(default=150_000, ge=0)\n''',
)
replace_once(
    "src/lifecanvas/models.py",
    '''    def validate_settings(self) -> "WalletPlan":\n        if self.husband_minimum_cash == 1_000_000 and self.minimum_personal_cash != 1_000_000:\n''',
    '''    def validate_settings(self) -> "WalletPlan":\n        legacy_equal_split = (\n            abs(self.household_shortfall_husband_percent - 50) < 0.01\n            and abs(self.household_shortfall_wife_percent - 50) < 0.01\n        )\n        if legacy_equal_split:\n            self.household_shortfall_husband_percent = 100\n            self.household_shortfall_wife_percent = 0\n            if self.wife_household_monthly <= 100_000:\n                self.wife_household_monthly = 150_000\n        if self.husband_minimum_cash == 1_000_000 and self.minimum_personal_cash != 1_000_000:\n''',
)
replace_once(
    "src/lifecanvas/sample.py",
    '''            wife_household_monthly=70_000,\n''',
    '''            wife_household_monthly=150_000,\n''',
)
replace_once(
    "src/lifecanvas/sample.py",
    '''            household_shortfall_husband_percent=50,\n            household_shortfall_wife_percent=50,\n''',
    '''            household_shortfall_husband_percent=100,\n            household_shortfall_wife_percent=0,\n''',
)

# Regression tests for actual category population and threshold-gate behavior.
replace_once(
    "tests/test_compact_policy_ui.py",
    '''        assert window.detailed_settings.categories.count() == 9\n        assert window.detailed_settings.recalculate_button.isVisibleTo(window.detailed_settings)\n''',
    '''        assert window.detailed_settings.categories.count() == 9\n        counts = window.detailed_settings.category_widget_counts\n        for category in (\n            "収入・働き方",\n            "家計・預金",\n            "NISA・投資",\n            "子ども・教育",\n            "住宅",\n            "車",\n            "借入・イベント",\n            "年金・計算条件",\n        ):\n            assert counts[category] > 0, category\n        assert window.detailed_settings.recalculate_button.isVisibleTo(window.detailed_settings)\n''',
)
replace_once(
    "tests/test_household_policy_phases.py",
    '''def test_debt_is_paid_before_wife_household_contribution(monkeypatch):\n''',
    '''def test_threshold_is_gate_not_monthly_deduction(monkeypatch):\n    plan, rows = _plan(wife_income=1_800_000)\n    plan.wallets.wife_household_monthly = 1_000_000\n    row = _run(plan, rows, monkeypatch)\n    annual_surplus = (\n        row.wife_personal_income\n        - row.wife_debt_payment\n        - row.wife_personal_spending\n        - row.wife_base_nisa_contributed\n    )\n    monthly_surplus = annual_surplus / 12\n    assert monthly_surplus > plan.wallets.wife_contribution_threshold_monthly\n    assert row.wife_household_paid == pytest.approx(annual_surplus)\n\n\ndef test_debt_is_paid_before_wife_household_contribution(monkeypatch):\n''',
)

print("Applied category and spouse cash-allocation feedback fixes.")
