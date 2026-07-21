from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import complete_ui as complete_ui_module
from . import final_ui as final_ui_module
from .age_income_editor import AgeIncomeEditor
from .housing_editor_v2 import HousingEditor
from .ito_sample import build_ito_family_plan
from .pdf_report_v2 import export_pdf
from .plotting import configure_japanese_matplotlib
from .rent_engine import is_rental_move
from .sample import build_genki_family_plan
from .ui import MetricCard, man
from .wallet_editor import WalletEditor
from .wallet_engine import SimulationEngine, recommend_monthly_contributions


def _nisa_limit(plan, owner: str) -> float:
    return next(
        (account.lifetime_limit for account in plan.nisa_accounts if account.owner == owner),
        0.0,
    )


def _nisa_progress_text(cumulative: float, lifetime_limit: float) -> str:
    if lifetime_limit <= 0:
        return "-"
    ratio = max(0.0, min(1.0, cumulative / lifetime_limit))
    milestone = "1/1" if ratio >= 1 else "1/2" if ratio >= 0.5 else "1/4" if ratio >= 0.25 else ""
    return f"{milestone + ' ' if milestone else ''}{ratio*100:.0f}%"


def _nisa_reached_year(results, attribute: str, lifetime_limit: float, ratio: float) -> str:
    threshold = lifetime_limit * ratio
    row = next((item for item in results if getattr(item, attribute, 0.0) + 1 >= threshold), None)
    return f"{row.calendar_year}年" if row else "期間内未到達"


# Keep all inherited calculation and export paths on the revised implementations.
complete_ui_module.SimulationEngine = SimulationEngine
final_ui_module.SimulationEngine = SimulationEngine
final_ui_module.HousingEditor = HousingEditor
final_ui_module.export_pdf = export_pdf

from .final_ui import LifeCanvasWindow as BaseLifeCanvasWindow


class LifeCanvasWindow(BaseLifeCanvasWindow):
    """Desktop UI with separate husband/wife savings and household-cost sharing."""

    def _install_completion_actions(self) -> None:
        root_layout = self.centralWidget().layout()
        actions = QHBoxLayout()
        guide = QLabel("大きな前提だけ入力して、結果を見ながら調整します。")
        guide.setObjectName("sectionNote")
        self.refresh_status = QLabel("最新")
        self.refresh_status.setObjectName("statusFresh")

        self.sample_combo = QComboBox()
        self.sample_combo.setObjectName("sampleSelector")
        self.sample_combo.addItem("大原家サンプル", "genki")
        self.sample_combo.addItem("伊藤家サンプル（仮設定）", "ito")
        load_sample_button = QPushButton("サンプルを読み込む")
        load_sample_button.clicked.connect(self.load_selected_sample)

        pdf_button = QPushButton("PDFレポート")
        pdf_button.setObjectName("pdfButton")
        pdf_button.clicked.connect(self.export_report)

        actions.addWidget(guide)
        actions.addStretch()
        actions.addWidget(self.refresh_status)
        actions.addWidget(self.sample_combo)
        actions.addWidget(load_sample_button)
        actions.addWidget(pdf_button)
        root_layout.insertLayout(2, actions)

    def _build_dashboard(self) -> QWidget:
        """Build a vertically scrollable result page with no floating overlays."""

        configure_japanese_matplotlib()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("resultScroll")

        page = QWidget()
        page.setObjectName("resultContent")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 12, 14, 18)

        cards = QGridLayout()
        cards.setHorizontalSpacing(10)
        cards.setVerticalSpacing(10)
        self.card_retirement = MetricCard("夫の定年時純資産")
        self.card_cash = MetricCard("最低手元現金")
        self.card_shortage = MetricCard("資金ショート")
        self.card_move = MetricCard("将来の住まい")
        self.card_outlook = MetricCard("将来判定")
        self.card_final = MetricCard("最終年の純資産")
        card_items = [
            self.card_outlook,
            self.card_cash,
            self.card_shortage,
            self.card_retirement,
            self.card_move,
            self.card_final,
        ]
        for index, card in enumerate(card_items):
            row, column = divmod(index, 3)
            card.setMinimumWidth(0)
            cards.addWidget(card, row, column)
            cards.setColumnStretch(column, 1)
        layout.addLayout(cards)

        graph_title = QLabel("資産・負債の推移")
        graph_title.setObjectName("sectionTitle")
        layout.addWidget(graph_title)

        self.figure = Figure(figsize=(11.5, 5.6))
        self.figure.patch.set_facecolor("#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(430)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.canvas)

        result_label = QLabel("判定と確認ポイント")
        result_label.setObjectName("sectionTitle")
        layout.addWidget(result_label)
        self.dashboard_summary = QTextEdit()
        self.dashboard_summary.setReadOnly(True)
        self.dashboard_summary.setMinimumHeight(235)
        self.dashboard_summary.setMaximumHeight(315)
        layout.addWidget(self.dashboard_summary)

        warning_label = QLabel("年ごとの注意")
        warning_label.setObjectName("sectionTitle")
        layout.addWidget(warning_label)
        self.dashboard_warnings = QListWidget()
        self.dashboard_warnings.setMinimumHeight(145)
        self.dashboard_warnings.setMaximumHeight(185)
        layout.addWidget(self.dashboard_warnings)

        layout.addStretch()
        scroll.setWidget(page)
        return scroll

    def _build_setup(self) -> QWidget:
        scroll = super()._build_setup()
        layout = scroll.widget().layout()

        old_index = layout.indexOf(self.husband_income_editor)
        self.husband_income_editor.hide()
        self.husband_age_income = AgeIncomeEditor(
            self.plan,
            owner="husband",
            title="夫の収入計画（年齢ごと）",
        )
        self.wife_age_income = AgeIncomeEditor(
            self.plan,
            owner="wife",
            title="妻の収入計画（年齢ごと）",
        )
        layout.insertWidget(max(0, old_index), self.husband_age_income)
        layout.insertWidget(max(0, old_index + 1), self.wife_age_income)

        self.wallet_editor = WalletEditor(self.plan)
        layout.insertWidget(max(0, old_index + 2), self.wallet_editor)
        self.wallet_editor.recommendationRequested.connect(self._recommend_investment)
        self.wallet_editor.mode.currentIndexChanged.connect(
            self._sync_cash_input_visibility
        )

        work_group = self.w_before.parentWidget()
        if hasattr(work_group, "setTitle"):
            work_group.setTitle("定年の基本設定")
        work_form = work_group.layout()
        for field in (self.w_before, self.w_nursery, self.w_elementary, self.w_junior):
            label = work_form.labelForField(field) if hasattr(work_form, "labelForField") else None
            if label:
                label.hide()
            field.hide()
        self._sync_cash_input_visibility()
        return scroll

    def _connect_auto_refresh(self) -> None:
        super()._connect_auto_refresh()
        self.child_editor.changed.connect(self._schedule_refresh)
        self.husband_age_income.changed.connect(self._schedule_refresh)
        self.wife_age_income.changed.connect(self._schedule_refresh)
        self.wallet_editor.changed.connect(self._schedule_refresh)

    def _sync_cash_input_visibility(self, *_args) -> None:
        if not hasattr(self, "wallet_editor"):
            return
        separate = self.wallet_editor.mode.currentData() == "separate"
        form = self.initial_cash.parentWidget().layout()
        label = form.labelForField(self.initial_cash) if hasattr(form, "labelForField") else None
        self.initial_cash.setVisible(not separate)
        if label:
            label.setVisible(not separate)

    def _apply_inputs(self) -> None:
        super()._apply_inputs()
        other_periods = [
            period
            for period in self.plan.income_periods
            if period.owner not in ("husband", "wife")
        ]
        husband_periods = self.husband_age_income.periods(self.plan)
        wife_periods = self.wife_age_income.periods(self.plan)
        self.plan.income_periods = [*other_periods, *husband_periods, *wife_periods]

        husband_current = next(
            (
                period
                for period in husband_periods
                if period.active(self.plan.husband.current_age)
            ),
            None,
        )
        wife_current = next(
            (
                period
                for period in wife_periods
                if period.active(self.plan.wife.current_age)
            ),
            None,
        )
        self.plan.husband.annual_gross_income = (
            husband_current.annual_gross_income if husband_current else 0
        )
        self.plan.wife.annual_gross_income = (
            wife_current.annual_gross_income if wife_current else 0
        )

        wallet = self.wallet_editor.value()
        if wallet.mode == "separate" and self.plan.initial_cash > 0:
            # Migrate the old single cash field once. New inputs live only in the two accounts.
            if wallet.initial_husband_cash + wallet.initial_wife_cash == 0:
                husband_ratio = wallet.household_shortfall_husband_percent / 100.0
                wallet.initial_husband_cash = self.plan.initial_cash * husband_ratio
                wallet.initial_wife_cash = self.plan.initial_cash - wallet.initial_husband_cash
                self.wallet_editor.initial_husband_cash.set_value(wallet.initial_husband_cash)
                self.wallet_editor.initial_wife_cash.set_value(wallet.initial_wife_cash)
            self.plan.initial_cash = 0
            self.initial_cash.set_value(0)
        self.plan.wallets = wallet
        self.plan.rules.minimum_cash_reserve = wallet.minimum_personal_cash

    def _sync_inputs_from_plan(self) -> None:
        super()._sync_inputs_from_plan()
        if hasattr(self, "husband_age_income"):
            self.husband_age_income.load(self.plan)
        if hasattr(self, "wife_age_income"):
            self.wife_age_income.load(self.plan)
        if hasattr(self, "wallet_editor"):
            self.wallet_editor.load(self.plan)
            self._sync_cash_input_visibility()

    def _recommend_investment(self) -> None:
        try:
            self._apply_inputs()
            recommendation = recommend_monthly_contributions(self.plan)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "おすすめ投資額", str(exc))
            return

        self.wallet_editor.show_recommendation(
            recommendation.husband_monthly,
            recommendation.wife_monthly,
            recommendation.note,
        )
        if self.plan.wallets.mode != "separate":
            return

        answer = QMessageBox.question(
            self,
            "おすすめ投資額を反映",
            "試算した月額を夫婦それぞれのNISA設定へ反映しますか？\n\n"
            f"夫：月{recommendation.husband_monthly/10_000:,.1f}万円\n"
            f"妻：月{recommendation.wife_monthly/10_000:,.1f}万円",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        for account in self.plan.nisa_accounts:
            if account.owner == "husband":
                account.monthly_contribution = recommendation.husband_monthly
            else:
                account.monthly_contribution = recommendation.wife_monthly
            account.contribution_changes = {}

        self.h_nisa_before.set_value(recommendation.husband_monthly)
        self.h_nisa_after.set_value(recommendation.husband_monthly)
        self.w_nisa.set_value(recommendation.wife_monthly)
        self.recalculate()

    def _selected_sample(self):
        if self.sample_combo.currentData() == "ito":
            return build_ito_family_plan()
        return build_genki_family_plan()

    def load_selected_sample(self) -> None:
        label = self.sample_combo.currentText()
        answer = QMessageBox.question(
            self,
            "サンプルを読み込む",
            f"現在の入力内容を「{label}」へ置き換えますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.plan = self._selected_sample()
        self.current_file = None
        self._sync_inputs_from_plan()
        self.recalculate()

    def reset_to_sample(self) -> None:
        self.load_selected_sample()

    def _configure_annual_table(self) -> None:
        headers = [
            "年",
            "夫/妻",
            "夫年収",
            "妻年収",
            "給付",
            "家計費",
            "夫負担",
            "妻負担",
            "家計不足",
            "夫個人支出",
            "妻個人支出",
            "夫預金増減",
            "妻預金増減",
            "夫預金",
            "夫最低ライン",
            "妻預金",
            "夫NISA年額",
            "夫NISA累計",
            "夫NISA進捗",
            "夫NISA評価",
            "妻NISA年額",
            "妻NISA累計",
            "妻NISA進捗",
            "妻NISA評価",
            "投資合計",
            "純資産",
        ]
        self.year_table.setColumnCount(len(headers))
        self.year_table.setHorizontalHeaderLabels(headers)
        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.year_table.setAlternatingRowColors(True)

    def _refresh_table(self) -> None:
        self.year_table.setRowCount(len(self.results))
        separate = self.plan.wallets.mode == "separate"
        husband_limit = _nisa_limit(self.plan, "husband")
        wife_limit = _nisa_limit(self.plan, "wife")
        for row_index, result in enumerate(self.results):
            if result.husband_minimum_cash_breach_months:
                minimum_status = (
                    f"▲{man(result.husband_minimum_cash_shortfall)} "
                    f"({result.husband_minimum_cash_breach_months}月)"
                )
            else:
                minimum_status = "OK"
            if separate:
                values = [
                    str(result.calendar_year),
                    f"{result.husband_age}/{result.wife_age}",
                    man(result.husband_gross),
                    man(result.wife_gross),
                    man(result.benefits),
                    man(result.household_cost_net),
                    man(result.husband_household_paid),
                    man(result.wife_household_paid),
                    man(result.household_shortfall),
                    man(result.husband_personal_spending),
                    man(result.wife_personal_spending),
                    man(result.husband_savings_change),
                    man(result.wife_savings_change),
                    man(result.husband_cash_end),
                    minimum_status,
                    man(result.wife_cash_end),
                    man(result.husband_nisa_contributed),
                    man(result.husband_nisa_cumulative_contributed),
                    _nisa_progress_text(result.husband_nisa_cumulative_contributed, husband_limit),
                    man(result.husband_nisa_market_value),
                    man(result.wife_nisa_contributed),
                    man(result.wife_nisa_cumulative_contributed),
                    _nisa_progress_text(result.wife_nisa_cumulative_contributed, wife_limit),
                    man(result.wife_nisa_market_value),
                    man(result.investments_market_value),
                    man(result.net_worth),
                ]
            else:
                values = [
                    str(result.calendar_year),
                    f"{result.husband_age}/{result.wife_age}",
                    man(result.husband_gross),
                    man(result.wife_gross),
                    man(result.benefits),
                    man(result.consumption_total),
                    "-", "-", "-", "-", "-", "-", "-",
                    man(result.cash_end),
                    "-",
                    "-",
                    man(result.nisa_contributed),
                    man(result.investments_book_value),
                    "-",
                    man(result.investments_market_value),
                    "-", "-", "-", "-",
                    man(result.investments_market_value),
                    man(result.net_worth),
                ]
            for column, value in enumerate(values):
                self.year_table.setItem(row_index, column, QTableWidgetItem(value))
        if self.results:
            self.year_table.selectRow(0)

    def _refresh_dashboard(self) -> None:
        super()._refresh_dashboard()
        if is_rental_move(self.plan):
            move_year = self.plan.start_year + (self.plan.housing.move_offset or 0)
            self.card_move.value.setText("賃貸へ移る")
            self.card_move.note.setText(f"{move_year}年・月額家賃を反映")

        if self.plan.wallets.mode == "separate" and self.results:
            cash_points = [
                (row.husband_cash_end, "夫", row.calendar_year)
                for row in self.results
            ] + [
                (row.wife_cash_end, "妻", row.calendar_year)
                for row in self.results
            ]
            minimum_cash, owner, year = min(cash_points, key=lambda item: item[0])
            self.card_cash.value.setText(man(minimum_cash))
            self.card_cash.note.setText(f"{owner}・{year}年")

            current = self.results[0]
            final = self.results[-1]
            months = max(1, current.months)
            wallet_text = (
                self.dashboard_summary.toPlainText().rstrip()
                + "\n\n【現在年の夫】\n"
                + f"月の入金 {man(current.husband_personal_income/months)} / "
                + f"家計 {man(current.husband_household_paid/months)} / "
                + f"個人支出 {man(current.husband_personal_spending/months)} / "
                + f"NISA {man(current.husband_nisa_contributed/months)} / "
                + f"預金増減 {man(current.husband_savings_change/months)}\n"
                + "【現在年の妻】\n"
                + f"月の入金 {man(current.wife_personal_income/months)} / "
                + f"家計 {man(current.wife_household_paid/months)} / "
                + f"個人支出 {man(current.wife_personal_spending/months)} / "
                + f"NISA {man(current.wife_nisa_contributed/months)} / "
                + f"預金増減 {man(current.wife_savings_change/months)}\n"
                + "【最終残高】\n"
                + f"夫預金 {man(final.husband_cash_end)} / "
                + f"妻預金 {man(final.wife_cash_end)} / "
                + f"夫NISA {man(final.husband_nisa_market_value)} / "
                + f"妻NISA {man(final.wife_nisa_market_value)}"
                + "\n【NISA買付元本と到達年】\n"
                + f"夫 累計{man(final.husband_nisa_cumulative_contributed)} / "
                + f"1/4 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 0.25)} / "
                + f"1/2 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 0.5)} / "
                + f"1/1 {_nisa_reached_year(self.results, 'husband_nisa_cumulative_contributed', _nisa_limit(self.plan, 'husband'), 1.0)}\n"
                + f"妻 累計{man(final.wife_nisa_cumulative_contributed)} / "
                + f"1/4 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 0.25)} / "
                + f"1/2 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 0.5)} / "
                + f"1/1 {_nisa_reached_year(self.results, 'wife_nisa_cumulative_contributed', _nisa_limit(self.plan, 'wife'), 1.0)}"
            )
            self.dashboard_summary.setPlainText(wallet_text)

        if self.figure.axes:
            axis = self.figure.axes[0]
            legend = axis.get_legend()
            if legend:
                legend.remove()
            axis.legend(
                ncol=2,
                loc="upper left",
                frameon=False,
                fontsize=9,
            )
            axis.margins(x=0.01)
            self.figure.subplots_adjust(left=0.075, right=0.985, bottom=0.14, top=0.88)
            self.canvas.draw_idle()


def run_app() -> None:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()
