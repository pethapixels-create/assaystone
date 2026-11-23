import unittest

from pricing.discounts import apply_discount, bulk_price


class TestApplyDiscount(unittest.TestCase):
    def test_zero_percent(self):
        self.assertEqual(apply_discount(1999, 0), 1999)

    def test_full_percent(self):
        self.assertEqual(apply_discount(1999, 100), 0)

    def test_round_half_up(self):
        self.assertEqual(apply_discount(1999, 15), 1699)

    def test_round_half_cent(self):
        self.assertEqual(apply_discount(1, 50), 0)

    def test_negative_percent_raises(self):
        with self.assertRaises(ValueError):
            apply_discount(100, -1)

    def test_over_100_raises(self):
        with self.assertRaises(ValueError):
            apply_discount(100, 101)


class TestBulkPrice(unittest.TestCase):
    def test_under_ten(self):
        self.assertEqual(bulk_price(100, 9), 900)

    def test_ten_or_more(self):
        self.assertEqual(bulk_price(100, 10), 900)

    def test_ten_bulk_rounding(self):
        self.assertEqual(bulk_price(199, 10), 1791)


if __name__ == "__main__":
    unittest.main()
