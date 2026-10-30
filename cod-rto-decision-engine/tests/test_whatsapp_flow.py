import unittest

from src.whatsapp_flow import opening_message, simulate_reply


class WhatsAppFlowTests(unittest.TestCase):
    def test_confirmation_yes_and_no(self):
        self.assertEqual(simulate_reply("confirm", "yes")["status"], "ship_as_is")
        self.assertEqual(simulate_reply("confirm", "no")["status"], "cancel")

    def test_confirmation_random_reply_asks_for_clarification(self):
        self.assertEqual(simulate_reply("confirm", "maybe")["status"], "clarify")

    def test_confirmation_timeout_holds_and_cancels(self):
        result = simulate_reply("confirm", "", elapsed_hours=24)
        self.assertEqual(result["status"], "hold_cancel")

    def test_prepaid_nudge_yes_requires_payment(self):
        self.assertEqual(simulate_reply("nudge_prepaid", "yes")["status"], "awaiting_payment")
        self.assertEqual(simulate_reply("nudge_prepaid", "yes", paid=True)["status"], "ship_prepaid")

    def test_prepaid_decline_keeps_cod(self):
        self.assertEqual(simulate_reply("nudge_prepaid", "no")["status"], "ship_as_is")

    def test_prepaid_unpaid_timeout_holds(self):
        result = simulate_reply("nudge_prepaid", "yes", elapsed_hours=24, paid=False)
        self.assertEqual(result["status"], "hold_cancel")

    def test_message_language_and_discount(self):
        text = opening_message("nudge_prepaid", "English", "ORDER-1", discount=25)
        self.assertIn("Rs 25", text)
        self.assertIn("NO to keep COD", text)


if __name__ == "__main__":
    unittest.main()