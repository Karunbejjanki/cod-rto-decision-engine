import unittest

from src.decision_engine import DEFAULT_CONFIG, assess_order, estimate_impact, estimate_rto_cost


def sample_order(**overrides):
    order = {
        "order_id": "TEST-1",
        "customer_name": "Asha Mehta",
        "phone": "9876543210",
        "address": "12 MG Road, near Hanuman Mandir",
        "city": "Pune",
        "pincode": "411001",
        "order_value": "649",
        "customer_prior_orders": "0",
        "customer_prior_rto": "0",
        "final_status": "RTO",
    }
    order.update(overrides)
    return order


class DecisionEngineTests(unittest.TestCase):
    def test_final_status_does_not_change_pre_dispatch_decision(self):
        delivered = assess_order(sample_order(final_status="DELIVERED"))
        returned = assess_order(sample_order(final_status="RTO"))
        self.assertEqual(delivered["action"], returned["action"])
        self.assertEqual(delivered["risk"], returned["risk"])

    def test_first_order_is_not_penalized(self):
        decision = assess_order(sample_order())
        self.assertTrue(decision["first_order"])
        self.assertEqual(decision["risk"], 0.284)

    def test_combined_placeholder_signals_route_to_hold(self):
        decision = assess_order(
            sample_order(customer_name="Test Order", address="xyz", phone="123", pincode="")
        )
        self.assertEqual(decision["action"], "hold_cancel")
        self.assertGreaterEqual(decision["risk"], 0.72)

    def test_config_thresholds_are_operator_editable(self):
        config = {"policy": {"thresholds": {"nudge_prepaid": 0.20}}}
        decision = assess_order(sample_order(), config)
        self.assertEqual(decision["action"], "nudge_prepaid")

    def test_rto_cost_includes_expected_damaged_product(self):
        self.assertAlmostEqual(estimate_rto_cost(DEFAULT_CONFIG), 169.4)

    def test_llm_can_only_add_high_confidence_risk_signals(self):
        order = sample_order()
        weak = assess_order(order, llm_review={"confidence": 0.79, "address_incomplete": True})
        strong = assess_order(order, llm_review={"confidence": 0.90, "address_incomplete": True})
        self.assertEqual(weak["risk"], 0.284)
        self.assertGreater(strong["risk"], weak["risk"])

    def test_prepaid_discount_is_included_in_net_impact(self):
        decision = assess_order(
            sample_order(customer_prior_rto="1", customer_prior_orders="2")
        )
        if decision["action"] == "nudge_prepaid":
            impact = estimate_impact(decision)
            self.assertGreater(impact["discount_cost_inr"], 0)


if __name__ == "__main__":
    unittest.main()