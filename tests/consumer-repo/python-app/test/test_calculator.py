import unittest

from regression_consumer.calculator import add


class TestCalculator(unittest.TestCase):
    def test_add_returns_the_sum(self) -> None:
        self.assertEqual(add(2, 3), 5)

    def test_add_with_zero(self) -> None:
        self.assertEqual(add(0, 5), 5)
        self.assertEqual(add(-5, 0), -5)

    def test_add_with_negative_operands(self) -> None:
        self.assertEqual(add(-7, 2), -5)
        self.assertEqual(add(-4, -6), -10)

    def test_add_with_large_integers(self) -> None:
        large_number = 10**100
        self.assertEqual(add(large_number, 1), large_number + 1)
