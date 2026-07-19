from __future__ import annotations

from .models import (
    CarPlan,
    ChildPlan,
    EducationCostPlan,
    HousingPlan,
    LivingCostPlan,
    MortgagePlan,
    NisaPlan,
    PersonPlan,
    ProjectPlan,
    SocialInsuranceMode,
    SystemRules,
    WifeWorkStage,
)


def build_genki_family_plan() -> ProjectPlan:
    return ProjectPlan(
        name="大原家ライフプラン",
        start_year=2026,
        start_month=9,
        simulation_years=45,
        initial_cash=1_200_000,
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
            retirement_age=55,
            pension_start_age=65,
            annual_pension=1_200_000,
            social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
        ),
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
                label="連続育児休業",
                start_offset=5,
                end_offset=10,
                annual_gross_income=0,
                annual_benefit=1_500_000,
                social_insurance_mode=SocialInsuranceMode.NONE,
            ),
            WifeWorkStage(
                key="nursery",
                label="短時間パート（第二子保育園）",
                start_offset=10,
                end_offset=12,
                annual_gross_income=576_000,
                social_insurance_mode=SocialInsuranceMode.DEPENDENT,
            ),
            WifeWorkStage(
                key="elementary",
                label="パート（第二子小学生）",
                start_offset=12,
                end_offset=18,
                annual_gross_income=960_000,
                social_insurance_mode=SocialInsuranceMode.DEPENDENT,
            ),
            WifeWorkStage(
                key="junior_high",
                label="週4〜5日パート（第二子中学生以降）",
                start_offset=18,
                end_offset=27,
                annual_gross_income=2_200_000,
                social_insurance_mode=SocialInsuranceMode.EMPLOYEE,
            ),
            WifeWorkStage(
                key="retired",
                label="退職",
                start_offset=27,
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
            move_offset=26,
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
                contribution_changes={5: 100_000},
                annual_return_percent=4.0,
            ),
            NisaPlan(
                owner="wife",
                monthly_contribution=30_000,
                annual_return_percent=4.0,
            ),
        ],
        living_cost=LivingCostPlan(
            monthly_amount=250_000,
            scope="includes_initial_housing",
            annual_child_increment=0,
        ),
        rules=SystemRules(minimum_cash_reserve=1_200_000),
    )


def create_sample_plan() -> ProjectPlan:
    return build_genki_family_plan()
