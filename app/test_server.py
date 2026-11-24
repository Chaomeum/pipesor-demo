import unittest

from server import ORDERS, count_by_status, paid_total


class OrderSummaryTest(unittest.TestCase):
    def test_counts_orders_by_status(self):
        self.assertEqual(count_by_status(ORDERS), {"PAID": 1, "PENDING": 1})

    def test_adds_only_paid_orders(self):
        self.assertEqual(paid_total(ORDERS), 1250.00)

    def test_empty_list(self):
        self.assertEqual(paid_total([]), 0)


if __name__ == "__main__":
    unittest.main()
