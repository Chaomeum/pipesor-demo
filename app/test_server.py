import unittest

from server import ORDERS, order_summary


class OrderSummaryTest(unittest.TestCase):
    def test_counts_orders_by_status(self):
        self.assertEqual(order_summary(ORDERS)["byStatus"], {"PAID": 1, "PENDING": 1})

    def test_adds_only_paid_orders(self):
        self.assertEqual(order_summary(ORDERS)["paidTotal"], 1250.00)

    def test_empty_list(self):
        self.assertEqual(order_summary([]), {"count": 0, "byStatus": {}, "paidTotal": 0})


if __name__ == "__main__":
    unittest.main()
