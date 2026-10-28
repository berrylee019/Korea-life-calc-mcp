"""계산 검증 테스트 (python -m unittest test_main -v)
기대값은 main.py와 별개로 손계산/공식 예시로 정했습니다."""
import inspect
import unittest

import main


class WeeklyHoliday(unittest.TestCase):
    def test_full_time(self):
        r = main.calculate_weekly_holiday_pay(40, 10_320)
        self.assertIn("1주 주휴수당: 8시간 × 10,320원 = 82,560원", r)
        self.assertIn("209시간", r)
        self.assertIn("2,156,880원", r)  # 고시 월환산액

    def test_part_time(self):
        self.assertIn("= 41,280원", main.calculate_weekly_holiday_pay(20, 10_320))
        self.assertIn("= 30,960원", main.calculate_weekly_holiday_pay(15, 10_320))

    def test_not_eligible(self):
        self.assertIn("15시간 미만", main.calculate_weekly_holiday_pay(14.5, 10_320))
        self.assertIn("개근하지 않아", main.calculate_weekly_holiday_pay(40, 10_320, False))

    def test_over_40_capped(self):
        r = main.calculate_weekly_holiday_pay(48, 10_000)
        self.assertIn("= 80,000원", r)

    def test_default_min_wage_and_warning(self):
        self.assertIn("10,320원", main.calculate_weekly_holiday_pay(40, 0, True, 2026))
        self.assertIn("10,700원", main.calculate_weekly_holiday_pay(40, 0, True, 2027))
        self.assertIn("최저시급", main.calculate_weekly_holiday_pay(40, 9_000, True, 2026))

    def test_invalid(self):
        self.assertTrue(main.calculate_weekly_holiday_pay(0, 10_000).startswith("[입력 확인]"))
        self.assertTrue(main.calculate_weekly_holiday_pay(40, 0, True, 2030).startswith("[입력 확인]"))


class Severance(unittest.TestCase):
    def test_basic(self):
        # 3개월(8~10월)=92일, 재직 1,096일(윤년 포함)
        r = main.calculate_severance_pay("2022-11-01", "2025-10-31", 9_000_000)
        expected = round(9_000_000 / 92 * 30 * 1096 / 365)
        self.assertIn(f"{expected:,}원", r)
        self.assertIn("(92일)", r)
        self.assertIn("1,096일", r)

    def test_bonus_and_leave(self):
        r = main.calculate_severance_pay("2022-11-01", "2025-10-31", 9_000_000, 1_200_000, 400_000)
        base = 9_000_000 + 1_200_000 * 3 / 12 + 400_000 * 3 / 12
        self.assertIn(f"{round(base / 92 * 30 * 1096 / 365):,}원", r)

    def test_ordinary_wage_floor(self):
        r = main.calculate_severance_pay("2022-11-01", "2025-10-31", 9_000_000, daily_ordinary_wage=120_000)
        self.assertIn("통상임금", r)
        self.assertIn(f"{round(120_000 * 30 * 1096 / 365):,}원", r)

    def test_one_year_boundary(self):
        short = main.calculate_severance_pay("2025-03-01", "2026-02-27", 9_000_000)
        self.assertIn("1년 미만", short)
        ok = main.calculate_severance_pay("2025-03-01", "2026-02-28", 9_000_000)
        self.assertNotIn("1년 미만", ok)
        self.assertIn("퇴직금:", ok)

    def test_weekly_hours_and_invalid(self):
        self.assertIn("15시간 미만", main.calculate_severance_pay("2020-01-01", "2025-12-31", 3_000_000, weekly_hours=10))
        self.assertTrue(main.calculate_severance_pay("2025-13-01", "2025-12-31", 1).startswith("[입력 확인]"))
        self.assertTrue(main.calculate_severance_pay("2025-12-31", "2025-01-01", 1).startswith("[입력 확인]"))
        self.assertTrue(main.calculate_severance_pay("2022-01-01", "2025-01-01", 0).startswith("[입력 확인]"))

    def test_add_months_clamp(self):
        from datetime import date
        self.assertEqual(main.add_months(date(2025, 5, 31), -3), date(2025, 2, 28))
        self.assertEqual(main.add_months(date(2024, 5, 31), -3), date(2024, 2, 29))
        self.assertEqual(main.add_months(date(2025, 11, 1), -3), date(2025, 8, 1))


class Brokerage(unittest.TestCase):
    def test_sale(self):
        self.assertIn("4,500,000원", main.calculate_brokerage_fee("매매", 900_000_000))   # 국토부 예시 450만
        self.assertIn("상한 중개보수(부가세 별도): 250,000원", main.calculate_brokerage_fee("매매", 49_000_000))  # 한도 적용
        self.assertIn("상한 중개보수(부가세 별도): 240,000원", main.calculate_brokerage_fee("매매", 40_000_000))
        self.assertIn("상한 중개보수(부가세 별도): 800,000원", main.calculate_brokerage_fee("매매", 190_000_000))  # 한도 적용
        self.assertIn("상한 중개보수(부가세 별도): 800,000원", main.calculate_brokerage_fee("매매", 200_000_000))  # 0.4%
        self.assertIn("상한 중개보수(부가세 별도): 10,500,000원", main.calculate_brokerage_fee("매매", 1_500_000_000))

    def test_lease(self):
        self.assertIn("상한 중개보수(부가세 별도): 2,400,000원", main.calculate_brokerage_fee("전세", 600_000_000))  # 국토부 예시 240만
        self.assertIn("상한 중개보수(부가세 별도): 900,000원", main.calculate_brokerage_fee("전세", 300_000_000))

    def test_monthly_rent_conversion(self):
        r = main.calculate_brokerage_fee("월세", 10_000_000, 500_000)   # 1천만+50만×100=6천만
        self.assertIn("60,000,000원", r)
        self.assertIn("상한 중개보수(부가세 별도): 240,000원", r)
        r2 = main.calculate_brokerage_fee("월세", 5_000_000, 300_000)  # 100배=3,500만(<5천만) → ×70 = 2,600만
        self.assertIn("26,000,000원", r2)
        self.assertIn("상한 중개보수(부가세 별도): 130,000원", r2)

    def test_invalid(self):
        self.assertTrue(main.calculate_brokerage_fee("상가", 1).startswith("[입력 확인]"))
        self.assertTrue(main.calculate_brokerage_fee("매매", 0).startswith("[입력 확인]"))


class AcquisitionTax(unittest.TestCase):
    def test_single_home(self):
        r = main.calculate_acquisition_tax(750_000_000, 1, False, 84.9 + 1)   # 85.9㎡ 초과
        self.assertIn("취득세: 15,000,000원", r)
        self.assertIn("지방교육세: 1,500,000원", r)
        self.assertIn("농어촌특별세: 1,500,000원", r)
        self.assertIn("합계: 18,000,000원", r)

    def test_small_home_exempt_rural(self):
        r = main.calculate_acquisition_tax(500_000_000, 1, False, 84)
        self.assertIn("취득세: 5,000,000원", r)
        self.assertIn("지방교육세: 500,000원", r)
        self.assertIn("농어촌특별세: 0원", r)
        self.assertIn("합계: 5,500,000원", r)

    def test_sliding_rate_and_top(self):
        self.assertIn("취득세율 1.67%", main.calculate_acquisition_tax(700_000_000, 1))
        self.assertIn("취득세율 3%", main.calculate_acquisition_tax(1_000_000_000, 1))
        self.assertIn("취득세율 1%", main.calculate_acquisition_tax(600_000_000, 1))
        self.assertIn("취득세율 3%", main.calculate_acquisition_tax(900_000_000 + 1, 1))

    def test_surcharge(self):
        r = main.calculate_acquisition_tax(1_000_000_000, 2, True, 90)   # 조정 2주택 8%
        self.assertIn("취득세: 80,000,000원", r)
        self.assertIn("지방교육세: 4,000,000원", r)
        self.assertIn("농어촌특별세: 6,000,000원", r)
        self.assertIn("합계: 90,000,000원", r)
        r3 = main.calculate_acquisition_tax(1_000_000_000, 3, True, 90)   # 조정 3주택 12%
        self.assertIn("합계: 134,000,000원", r3)   # 12% + 0.4% + 1.0% = 13.4%
        r3s = main.calculate_acquisition_tax(1_000_000_000, 3, True, 80)  # 85㎡ 이하
        self.assertIn("합계: 124,000,000원", r3s)
        self.assertIn("취득세율 8%", main.calculate_acquisition_tax(1_000_000_000, 3, False))
        self.assertIn("취득세율 12%", main.calculate_acquisition_tax(1_000_000_000, 4, False))
        self.assertIn("취득세율 12%", main.calculate_acquisition_tax(1_000_000_000, 1, False, 84, True))

    def test_two_homes_non_regulated_and_temporary(self):
        self.assertIn("취득세율 1%", main.calculate_acquisition_tax(500_000_000, 2, False))
        self.assertIn("취득세율 1%", main.calculate_acquisition_tax(500_000_000, 2, True, 84, False, True))

    def test_invalid(self):
        self.assertTrue(main.calculate_acquisition_tax(0).startswith("[입력 확인]"))
        self.assertTrue(main.calculate_acquisition_tax(1, 0).startswith("[입력 확인]"))


class Registry(unittest.TestCase):
    def test_tools(self):
        import fastmcp
        reg = getattr(fastmcp, "REG", None)
        if reg is None:
            self.skipTest("등록 정보 검사는 테스트용 스텁 fastmcp에서만 실행합니다")
        self.assertEqual(set(reg), {"calculate_weekly_holiday_pay", "calculate_severance_pay",
                                    "calculate_brokerage_fee", "calculate_acquisition_tax",
                                    "get_rate_reference"})
        for name, (kw, fn) in reg.items():
            self.assertEqual(set(kw["annotations"]),
                             {"title", "readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"})
            self.assertLessEqual(len(kw["description"]), 1024, name)
            self.assertIn("한국 생활 법정 계산기 - Korea Life Calc", kw["description"])
            self.assertNotIn("kakao", name.lower())
            self.assertTrue(inspect.signature(fn).parameters is not None)

    def test_reference(self):
        r = main.get_rate_reference()
        for s in ("10,320원", "10,700원", "209시간", "한도 250,000원", "한도 300,000원", "6억 이하 1%"):
            self.assertIn(s, r)


if __name__ == "__main__":
    unittest.main()
