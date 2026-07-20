from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .models import ChildPlan, NisaPlan, ProjectPlan, SocialInsuranceMode
from .plan_review import apply_wife_work_preset, check_plan
from .tax import estimate_net_salary
from .widgets import NumberEdit


class SimpleInputPage(QScrollArea):
    """A small guided form that creates a coherent baseline plan."""

    changed = Signal()
    applyRequested = Signal()

    WORK_PRESETS = (
        ("標準復職（育休後は時短、段階的に復帰）", "standard"),
        ("早期復職（早めに現在年収へ戻る）", "early"),
        ("育児優先（パート・時短期間を長めにする）", "care"),
        ("詳細設定をそのまま使う", "custom"),
    )

    def __init__(self, plan: ProjectPlan, parent: QWidget | None = None):
        super().__init__(parent)
        self._loading = False
        self._plan = plan
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("simpleInputScroll")

        content = QWidget()
        content.setObjectName("simpleInputContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 22)
        layout.setSpacing(12)

        intro = QLabel(
            "まずは今の家計と大きな予定だけ入力します。"
            "細かな税金・教育費・住宅条件は詳細設定で後から変更できます。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(
            "background:#eaf3ff; color:#174a7c; padding:12px; border-radius:8px;"
        )
        layout.addWidget(intro)

        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(12)
        top_grid.setVerticalSpacing(12)
        top_grid.addWidget(self._build_current_group(), 0, 0)
        top_grid.addWidget(self._build_flow_group(), 0, 1)
        top_grid.addWidget(self._build_family_group(), 1, 0)
        top_grid.addWidget(self._build_investment_group(), 1, 1)
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 1)
        layout.addLayout(top_grid)

        review_group = QGroupBox("入力内容のチェック")
        review_layout = QVBoxLayout(review_group)
        review_note = QLabel(
            "計算前に、二重計上・現金不足・出産時の投資増額・未確定の住み替えなどを確認します。"
        )
        review_note.setWordWrap(True)
        review_note.setStyleSheet("color:#5f6670;")
        self.review_list = QListWidget()
        self.review_list.setMinimumHeight(120)
        review_layout.addWidget(review_note)
        review_layout.addWidget(self.review_list)
        layout.addWidget(review_group)

        action_row = QHBoxLayout()
        action_hint = QLabel(
            "このボタンで詳細設定にも反映し、基準・慎重・楽観の3プランを計算します。"
        )
        action_hint.setWordWrap(True)
        action_hint.setStyleSheet("color:#5f6670;")
        self.apply_button = QPushButton("この内容で人生プランを計算")
        self.apply_button.setObjectName("primaryButton")
        self.apply_button.setMinimumHeight(44)
        self.apply_button.clicked.connect(
            lambda _checked=False: self.applyRequested.emit()
        )
        action_row.addWidget(action_hint, 1)
        action_row.addWidget(self.apply_button)
        layout.addLayout(action_row)
        layout.addStretch()

        self.setWidget(content)
        self._connect_changes()
        self.load(plan)

    def _build_current_group(self) -> QGroupBox:
        group = QGroupBox("1. 今の収入・預金・生活費")
        form = QFormLayout(group)
        self.husband_income = NumberEdit(0, "円/年")
        self.wife_income = NumberEdit(0, "円/年")
        self.husband_cash = NumberEdit(0)
        self.wife_cash = NumberEdit(0)
        self.living_monthly = NumberEdit(0, "円/月", maximum=2_000_000)
        self.includes_personal = QCheckBox(
            "生活費に夫婦のお小遣い・外食・娯楽を含む"
        )
        self.husband_personal = NumberEdit(0, "円/月")
        self.wife_personal = NumberEdit(0, "円/月")
        form.addRow("夫の現在年収", self.husband_income)
        form.addRow("妻の現在年収", self.wife_income)
        form.addRow("夫の現在預金", self.husband_cash)
        form.addRow("妻の現在預金", self.wife_cash)
        form.addRow("家族全体の生活費（住宅費込み）", self.living_monthly)
        form.addRow(self.includes_personal)
        form.addRow("夫の別枠の個人支出", self.husband_personal)
        form.addRow("妻の別枠の個人支出", self.wife_personal)
        return group

    def _build_flow_group(self) -> QGroupBox:
        group = QGroupBox("現在の月のお金の流れ")
        layout = QVBoxLayout(group)
        note = QLabel(
            "入力した数字から、夫と妻の預金が毎月どれくらい増減するかを概算します。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5f6670;")
        self.husband_flow = QLabel()
        self.wife_flow = QLabel()
        for label in (self.husband_flow, self.wife_flow):
            label.setWordWrap(True)
            label.setTextFormat(label.TextFormat.RichText)
            label.setStyleSheet(
                "background:#f6f8fb; border:1px solid #dce3ec; "
                "padding:11px; border-radius:8px;"
            )
        self.household_flow = QLabel()
        self.household_flow.setWordWrap(True)
        self.household_flow.setStyleSheet(
            "background:#fff8e7; color:#6b4d08; padding:9px; border-radius:7px;"
        )
        layout.addWidget(note)
        layout.addWidget(self.husband_flow)
        layout.addWidget(self.wife_flow)
        layout.addWidget(self.household_flow)
        layout.addStretch()
        return group

    def _build_family_group(self) -> QGroupBox:
        group = QGroupBox("2. 家族と働き方")
        form = QFormLayout(group)
        self.child_count = QComboBox()
        self.child_count.addItem("子どもの予定なし", 0)
        self.child_count.addItem("1人", 1)
        self.child_count.addItem("2人", 2)
        self.child_count.addItem("3人", 3)
        self.first_child_offset = NumberEdit(5, "年後", maximum=40)
        self.child_spacing = NumberEdit(2, "年差", maximum=15)
        self.wife_work_preset = QComboBox()
        for label, value in self.WORK_PRESETS:
            self.wife_work_preset.addItem(label, value)
        self.include_move = QCheckBox(
            "詳細設定にある住み替え予定を基準プランへ含める"
        )
        move_note = QLabel(
            "未確定ならチェックを外してください。住み替えは比較シナリオで確認できます。"
        )
        move_note.setWordWrap(True)
        move_note.setStyleSheet("color:#5f6670;")
        form.addRow("将来ほしい子ども", self.child_count)
        form.addRow("第一子は", self.first_child_offset)
        form.addRow("きょうだいの間隔", self.child_spacing)
        form.addRow("妻の出産後の働き方", self.wife_work_preset)
        form.addRow(self.include_move)
        form.addRow(move_note)
        return group

    def _build_investment_group(self) -> QGroupBox:
        group = QGroupBox("3. 家計負担とNISA")
        form = QFormLayout(group)
        self.husband_household = NumberEdit(0, "円/月")
        self.wife_household = NumberEdit(0, "円/月")
        self.husband_child_increment = NumberEdit(0, "円/月・1人")
        self.shortfall_husband_percent = NumberEdit(
            50, "%", minimum=0, maximum=100
        )
        self.shortfall_wife_label = QLabel("妻 50%")
        self.husband_nisa = NumberEdit(0, "円/月", maximum=300_000)
        self.wife_nisa = NumberEdit(0, "円/月", maximum=300_000)
        self.minimum_cash = NumberEdit(1_000_000)
        form.addRow("夫の通常の家計負担", self.husband_household)
        form.addRow("妻の通常の家計負担", self.wife_household)
        form.addRow("子ども1人につき夫が増やす額", self.husband_child_increment)
        form.addRow("家計不足を夫が出す割合", self.shortfall_husband_percent)
        form.addRow("残りの割合", self.shortfall_wife_label)
        form.addRow("夫NISA", self.husband_nisa)
        form.addRow("妻NISA", self.wife_nisa)
        form.addRow("各自に必ず残す現金", self.minimum_cash)
        return group

    def _number_edits(self) -> tuple[NumberEdit, ...]:
        return (
            self.husband_income,
            self.wife_income,
            self.husband_cash,
            self.wife_cash,
            self.living_monthly,
            self.husband_personal,
            self.wife_personal,
            self.husband_household,
            self.wife_household,
            self.husband_child_increment,
            self.shortfall_husband_percent,
            self.husband_nisa,
            self.wife_nisa,
            self.minimum_cash,
            self.first_child_offset,
            self.child_spacing,
        )

    def _connect_changes(self) -> None:
        for editor in self._number_edits():
            editor.edit.editingFinished.connect(self._field_changed)
        self.includes_personal.toggled.connect(self._field_changed)
        self.child_count.currentIndexChanged.connect(self._field_changed)
        self.wife_work_preset.currentIndexChanged.connect(self._field_changed)
        self.include_move.toggled.connect(self._field_changed)

    def _field_changed(self, *_args) -> None:
        if self._loading:
            return
        self._update_enabled_fields()
        self._refresh_preview()
        self.changed.emit()

    def _update_enabled_fields(self) -> None:
        personal_is_separate = not self.includes_personal.isChecked()
        self.husband_personal.setEnabled(personal_is_separate)
        self.wife_personal.setEnabled(personal_is_separate)
        count = int(self.child_count.currentData() or 0)
        self.first_child_offset.setEnabled(count > 0)
        self.child_spacing.setEnabled(count > 1)
        husband_percent = self.shortfall_husband_percent.value()
        self.shortfall_wife_label.setText(f"妻 {100-husband_percent:,.0f}%")

    @staticmethod
    def _nisa(plan: ProjectPlan, owner: str) -> NisaPlan:
        account = next(
            (item for item in plan.nisa_accounts if item.owner == owner),
            None,
        )
        if account is None:
            account = NisaPlan(owner=owner, monthly_contribution=0)
            plan.nisa_accounts.append(account)
        return account

    @staticmethod
    def _update_current_income(plan: ProjectPlan, owner: str, income: float) -> None:
        person = plan.husband if owner == "husband" else plan.wife
        person.annual_gross_income = income
        active = [
            period
            for period in plan.income_periods
            if period.owner == owner and period.active(person.current_age)
        ]
        if active:
            max(active, key=lambda item: item.start_age).annual_gross_income = income
            return
        plan.income_periods.append(
            __import__("lifecanvas.models", fromlist=["IncomePeriod"]).IncomePeriod(
                owner=owner,
                label="現在の勤務",
                start_age=person.current_age,
                end_age=person.retirement_age,
                annual_gross_income=income,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            )
        )

    def apply_to(self, plan: ProjectPlan) -> None:
        wallet = plan.wallets
        wallet.mode = "separate"
        plan.initial_cash = 0
        wallet.initial_husband_cash = self.husband_cash.value()
        wallet.initial_wife_cash = self.wife_cash.value()
        wallet.husband_household_monthly = self.husband_household.value()
        wallet.wife_household_monthly = self.wife_household.value()
        wallet.husband_child_household_increment_monthly = (
            self.husband_child_increment.value()
        )
        wallet.wife_child_household_increment_monthly = 0
        husband_percent = self.shortfall_husband_percent.value()
        wallet.household_shortfall_husband_percent = husband_percent
        wallet.household_shortfall_wife_percent = 100 - husband_percent
        wallet.minimum_personal_cash = self.minimum_cash.value()
        wallet.target_personal_cash = self.minimum_cash.value()

        includes_personal = self.includes_personal.isChecked()
        plan.living_cost.monthly_amount = self.living_monthly.value()
        plan.living_cost.scope = "includes_initial_housing"
        plan.living_cost.includes_personal_spending = includes_personal
        wallet.husband_personal_spending_monthly = (
            0 if includes_personal else self.husband_personal.value()
        )
        wallet.wife_personal_spending_monthly = (
            0 if includes_personal else self.wife_personal.value()
        )

        self._update_current_income(plan, "husband", self.husband_income.value())
        self._update_current_income(plan, "wife", self.wife_income.value())

        husband_nisa = self._nisa(plan, "husband")
        wife_nisa = self._nisa(plan, "wife")
        husband_nisa.monthly_contribution = self.husband_nisa.value()
        wife_nisa.monthly_contribution = self.wife_nisa.value()
        # Hidden future changes are removed in simple mode so childbirth does not
        # unexpectedly increase investments.
        husband_nisa.contribution_changes = {}
        wife_nisa.contribution_changes = {}

        child_count = int(self.child_count.currentData() or 0)
        first = self.first_child_offset.int_value()
        spacing = max(1, self.child_spacing.int_value())
        names = ["第一子", "第二子", "第三子"]
        plan.children = [
            ChildPlan(name=names[index], birth_offset=first + spacing * index)
            for index in range(child_count)
        ]
        apply_wife_work_preset(plan, self.wife_work_preset.currentData())

        if not self.include_move.isChecked():
            plan.housing.move_mode = "none"
            plan.housing.move_offset = None

        plan.rules.minimum_cash_reserve = wallet.minimum_personal_cash

    def load(self, plan: ProjectPlan) -> None:
        self._loading = True
        self._plan = plan
        try:
            wallet = plan.wallets
            self.husband_income.set_value(plan.husband.annual_gross_income)
            self.wife_income.set_value(plan.wife.annual_gross_income)
            self.husband_cash.set_value(wallet.initial_husband_cash)
            self.wife_cash.set_value(wallet.initial_wife_cash)
            self.living_monthly.set_value(plan.living_cost.monthly_amount)
            self.includes_personal.setChecked(
                plan.living_cost.includes_personal_spending
            )
            self.husband_personal.set_value(
                wallet.husband_personal_spending_monthly
            )
            self.wife_personal.set_value(wallet.wife_personal_spending_monthly)
            self.husband_household.set_value(wallet.husband_household_monthly)
            self.wife_household.set_value(wallet.wife_household_monthly)
            self.husband_child_increment.set_value(
                wallet.husband_child_household_increment_monthly
            )
            self.shortfall_husband_percent.set_value(
                wallet.household_shortfall_husband_percent
            )
            self.minimum_cash.set_value(wallet.minimum_personal_cash)
            self.husband_nisa.set_value(
                self._nisa(plan, "husband").monthly_contribution
            )
            self.wife_nisa.set_value(
                self._nisa(plan, "wife").monthly_contribution
            )
            count_index = self.child_count.findData(min(3, len(plan.children)))
            self.child_count.setCurrentIndex(max(0, count_index))
            if plan.children:
                offsets = sorted(child.birth_offset for child in plan.children)
                self.first_child_offset.set_value(offsets[0])
                self.child_spacing.set_value(
                    offsets[1] - offsets[0] if len(offsets) > 1 else 2
                )
            preset_index = self.wife_work_preset.findData(plan.wife_work_preset)
            self.wife_work_preset.setCurrentIndex(max(0, preset_index))
            self.include_move.setChecked(plan.housing.move_mode != "none")
            self._update_enabled_fields()
        finally:
            self._loading = False
        self._refresh_preview()

    @staticmethod
    def _money(value: float) -> str:
        sign = "+" if value >= 0 else "−"
        return f"{sign}{abs(value)/10_000:,.1f}万円"

    def _refresh_preview(self) -> None:
        husband_net = estimate_net_salary(
            self.husband_income.value(),
            SocialInsuranceMode.EMPLOYEE,
            self._plan.rules,
        ).net / 12
        wife_net = estimate_net_salary(
            self.wife_income.value(),
            SocialInsuranceMode.EMPLOYEE,
            self._plan.rules,
        ).net / 12
        household_cost = self.living_monthly.value()
        husband_request = self.husband_household.value()
        wife_request = self.wife_household.value()
        requested_total = husband_request + wife_request
        normal_paid = min(household_cost, requested_total)
        if requested_total > 0:
            husband_normal = normal_paid * husband_request / requested_total
            wife_normal = normal_paid - husband_normal
        else:
            husband_normal = 0.0
            wife_normal = 0.0
        shortfall = max(0.0, household_cost - normal_paid)
        husband_ratio = self.shortfall_husband_percent.value() / 100
        husband_household = husband_normal + shortfall * husband_ratio
        wife_household = wife_normal + shortfall * (1 - husband_ratio)
        husband_personal = (
            0 if self.includes_personal.isChecked() else self.husband_personal.value()
        )
        wife_personal = (
            0 if self.includes_personal.isChecked() else self.wife_personal.value()
        )
        husband_change = (
            husband_net
            - husband_household
            - husband_personal
            - self.husband_nisa.value()
        )
        wife_change = (
            wife_net
            - wife_household
            - wife_personal
            - self.wife_nisa.value()
        )
        self.husband_flow.setText(
            "<b>夫</b><br>"
            f"手取り 約{husband_net/10_000:,.1f}万円 − 家計{husband_household/10_000:,.1f}万円 "
            f"− 個人{husband_personal/10_000:,.1f}万円 − NISA{self.husband_nisa.value()/10_000:,.1f}万円"
            f"<br><b>毎月の預金増減 {self._money(husband_change)}</b>"
        )
        self.wife_flow.setText(
            "<b>妻</b><br>"
            f"手取り 約{wife_net/10_000:,.1f}万円 − 家計{wife_household/10_000:,.1f}万円 "
            f"− 個人{wife_personal/10_000:,.1f}万円 − NISA{self.wife_nisa.value()/10_000:,.1f}万円"
            f"<br><b>毎月の預金増減 {self._money(wife_change)}</b>"
        )
        self.household_flow.setText(
            f"家族の生活費 月{household_cost/10_000:,.1f}万円／"
            f"通常負担で足りない額 月{shortfall/10_000:,.1f}万円"
        )

        self.review_list.clear()
        try:
            trial = self._plan.model_copy(deep=True)
            self.apply_to(trial)
            checks = check_plan(trial)
        except (TypeError, ValueError) as exc:
            self.review_list.addItem(f"入力エラー：{exc}")
            return
        if not checks:
            self.review_list.addItem(
                "大きな矛盾は見つかりません。基準プランとして計算できます。"
            )
            return
        for check in checks:
            prefix = "⚠" if check.level == "warning" else "確認"
            self.review_list.addItem(
                f"{prefix} {check.title}：{check.detail} {check.suggestion}"
            )
