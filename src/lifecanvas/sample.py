from __future__ import annotations

from .models import (
    CarPlan,
    ChildPlan,
    EducationCostPlan,
    HousingPlan,
    IncomePeriod,
    LivingCostPlan,
    MortgagePlan,
    NisaPlan,
    OneTimeIncome,
    PersonPlan,
    ProjectPlan,
    SocialInsuranceMode,
    SystemRules,
    WalletPlan,
    WifeWorkStage,
)


def build_genki_family_plan() -> ProjectPlan:
    """Return a realistic baseline rather than a worst-case stress test."""

    return ProjectPlan(
        name="大原家ライフプラン",
        start_year=2026,
        start_month=9,
        simulation_years=45,
        # Separate-wallet mode uses the two explicit balances below.
        initial_cash=0,
        husband=PersonPlan(
            name="夫",
            current_age=34,
            annual_gross_income=6_200_000,
            retirement_age=60,
            pension_start_age=65,
            annual_pension=1_800_000,
            social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
        ),
        wife=PersonPlan(
            name="妻",
            current_age=28,
            annual_gross_income=3_500_000,
            retirement_age=60,
            pension_start_age=65,
            annual_pension=1_200_000,
            social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
        ),
        income_periods=[
            IncomePeriod(
                owner="husband",
                label="現在の勤務",
                start_age=34,
                end_age=60,
                annual_gross_income=6_200_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            IncomePeriod(
                owner="husband",
                label="定年後の継続雇用",
                start_age=60,
                end_age=65,
                annual_gross_income=2_200_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            IncomePeriod(
                owner="wife",
                label="出産前の勤務",
                start_age=28,
                end_age=33,
                annual_gross_income=3_500_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            IncomePeriod(
                owner="wife",
                label="産休・育休",
                start_age=33,
                end_age=35,
                annual_gross_income=0,
                annual_benefit=1_925_000,
                social_insurance_mode=SocialInsuranceMode.NONE,
            ),
            IncomePeriod(
                owner="wife",
                label="標準復職・時短勤務",
                start_age=35,
                end_age=41,
                annual_gross_income=2_625_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            IncomePeriod(
                owner="wife",
                label="小学生期の勤務",
                start_age=41,
                end_age=47,
                annual_gross_income=3_150_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            IncomePeriod(
                owner="wife",
                label="通常勤務へ復帰",
                start_age=47,
                end_age=60,
                annual_gross_income=3_500_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
        ],
        one_time_incomes=[
            OneTimeIncome(owner="husband", label="夫の退職金", age=60, amount=0),
            OneTimeIncome(owner="wife", label="妻の退職金", age=60, amount=0),
        ],
        # Compatibility data for older screens. Current calculations prefer income_periods.
        wife_work_stages=[
            WifeWorkStage(
                key="full_time",
                label="出産前の正社員",
                start_offset=0,
                end_offset=5,
                annual_gross_income=3_500_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            WifeWorkStage(
                key="childcare_leave",
                label="産休・育休",
                start_offset=5,
                end_offset=7,
                annual_gross_income=0,
                annual_benefit=1_925_000,
                social_insurance_mode=SocialInsuranceMode.NONE,
            ),
            WifeWorkStage(
                key="nursery",
                label="標準復職・時短勤務",
                start_offset=7,
                end_offset=13,
                annual_gross_income=2_625_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            WifeWorkStage(
                key="elementary",
                label="小学生期の勤務",
                start_offset=13,
                end_offset=19,
                annual_gross_income=3_150_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            WifeWorkStage(
                key="junior_high",
                label="通常勤務へ復帰",
                start_offset=19,
                end_offset=32,
                annual_gross_income=3_500_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            WifeWorkStage(
                key="retired",
                label="退職",
                start_offset=32,
                annual_gross_income=0,
                social_insurance_mode=SocialInsuranceMode.NONE,
            ),
        ],
        children=[
            ChildPlan(name="第一子", birth_offset=5),
            ChildPlan(name="第二子", birth_offset=6),
        ],
        education=EducationCostPlan(),
        housing=HousingPlan(
            purchase_price=31_700_000,
            mortgage=MortgagePlan(
                principal=31_700_000,
                term_years=40,
                initial_rate_percent=1.68,
                annual_rate_step_percent=0.2,
                max_rate_percent=3.0,
                property_tax_annual=120_000,
                insurance_annual=20_000,
                maintenance_annual=0,
            ),
            # The retirement move is uncertain, so it is not part of the baseline.
            move_mode="none",
            move_offset=None,
            move_cost=1_000_000,
            new_home_monthly_cost=150_000,
            old_home_net_rent_annual=750_000,
        ),
        car=CarPlan(
            purchase_offset=1,
            purchase_price=1_500_000,
            annual_running_cost=350_000,
            replacement_cycle_years=7,
            replacement_price=1_200_000,
        ),
        nisa_accounts=[
            NisaPlan(
                owner="husband",
                monthly_contribution=60_000,
                # The legacy detail field expects a five-year value. Keeping the
                # same amount avoids a hidden childbirth-time increase or stop.
                contribution_changes={5: 60_000},
                annual_return_percent=4.0,
            ),
            NisaPlan(
                owner="wife",
                monthly_contribution=30_000,
                contribution_changes={},
                annual_return_percent=4.0,
            ),
        ],
        living_cost=LivingCostPlan(
            monthly_amount=250_000,
            scope="includes_initial_housing",
            annual_child_increment=0,
            includes_personal_spending=True,
        ),
        wallets=WalletPlan(
            mode="separate",
            initial_husband_cash=600_000,
            initial_wife_cash=600_000,
            husband_household_monthly=180_000,
            wife_household_monthly=150_000,
            husband_child_household_increment_monthly=30_000,
            wife_child_household_increment_monthly=0,
            # The ¥250k living-cost input already includes allowances and leisure.
            husband_personal_spending_monthly=0,
            wife_personal_spending_monthly=0,
            household_shortfall_husband_percent=100,
            household_shortfall_wife_percent=0,
            minimum_personal_cash=1_000_000,
            target_personal_cash=1_000_000,
            auto_invest_enabled=False,
        ),
        wife_work_preset="standard",
        rules=SystemRules(minimum_cash_reserve=1_000_000),
    )


def create_sample_plan() -> ProjectPlan:
    return build_genki_family_plan()
