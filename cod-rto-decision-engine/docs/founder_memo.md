# Founder Memo: COD RTO Decision Pilot

**To:** Founder  
**Date:** October 30, 2026  
**Subject:** A cautious, margin-aware way to route COD orders

## Recommendation

Start with a two-week shadow/pilot policy, not automatic cancellation by pincode. Ship low-signal orders normally; ask for confirmation or offer a prepaid saving when several delivery-quality signals stack up; send only the strongest cases to a human hold/cancel queue. First-time status alone never triggers a penalty. The prototype is in `app.py`; policy settings and economics are editable in `config.yaml`.

## What the sample says

The file contains 2,018 COD rows dated April 1 through September 30, 2026: 1,444 delivered, 573 RTO, and one still in transit. The raw RTO rate is 28.4%, close to the 28% business estimate. Three points stood out:

- **Delivery quality signals are much stronger than first-time status.** Forty-one rows have an obvious test/placeholder name (`test`, `qwerty`, `asdf`, `abc`, `xyz`, or `na`); 26 were RTO (63.4%). Among 187 rows with a placeholder or location-incomplete address, 116 were RTO (62.0%). These groups overlap, are small, and need live validation; they are flags for confirmation, not proof of fraud.
- **First-time buyers are riskier, but most still succeed.** 460 of 1,518 first orders were RTO (30.3%) versus 113 of 500 repeat orders (22.6%). Thus 69.7% of first orders were delivered. Cancelling first orders wholesale would sacrifice genuine orders and marketing’s acquisition investment.
- **The file itself needs cleaning before production use.** There are 30 duplicated order-ID groups (30 extra rows), 12 missing pincodes, 32 phone values that do not normalize to 10 digits, and three zero-value orders. Some rows have placeholder names/addresses. We should de-duplicate and confirm source-system definitions before claiming these are representative customer behaviors.

## Proposed rules and September replay

The rules start from the sample’s 28.4% RTO rate and add configurable points for a placeholder name, weak address, invalid phone/pincode, or recorded prior RTO. A repeat customer with orders and no prior RTO gets a small reduction; a first order gets no penalty. Thresholds are `0.38` prepaid nudge, `0.52` confirmation, and `0.72` hold/cancel. These are pilot score thresholds, **not calibrated probabilities**. The highest bucket should remain a human decision until a time-based validation set proves calibration.

On the 334 supplied September rows, the replay assigned 273 Ship as-is, 1 Ship after confirmation, 56 Nudge to prepaid, and 4 Hold / cancel. Their observed RTO rates were 21.3%, 100% (one order), 44.6%, and 75.0%, respectively. This is an in-sample selection check, not a causal result: the policy did not change those historical outcomes, the confirmation group is only one order, and September is only a subset of the stated 3,000 monthly volume.

For live orders, send the confirmation/nudge within five minutes of checkout and before warehouse handoff. Use the customer's stored language preference; the mock defaults to Hinglish because the sample has no language-preference field. YES/NO instructions should stay short, and ambiguous replies get one clarification prompt before the 24-hour timeout.

Under the configured scenario assumptions (65% confirmation response, 60% RTO-risk reduction after confirmation, and 35% prepaid uptake), that September replay estimates ₹1,388 in RTO cost avoided, ₹418 in genuine delivered contribution lost on non-responders/cancellations, and ₹490 in prepaid discounts: **about ₹479 net positive**. This depends on uncalibrated risk scores and should be treated as an illustration, not booked savings.

## The rupee trade-off

Each RTO costs ₹65 forward shipping + ₹65 return shipping + ₹25 packaging/handling + 8% × ₹180 expected damage = **₹169.40**. A delivered ₹649 order contributes about 62% × ₹649 = **₹402.38** gross margin. Ignoring future customer value, canceling beats shipping only when the chance of RTO is above ₹402.38 / (₹402.38 + ₹169.40) = **70.4%**. That is why a high hold/cancel threshold is appropriate and why the current engine only recommends a hold; it does not cancel automatically.

For prepaid, the supplied 28% COD versus 4% prepaid RTO rates imply ₹169.40 × 24% = **₹40.66** expected RTO cost avoided per order that actually switches to prepaid. A **₹25** discount leaves about **₹15.66** before payment fees and conversion effects. At the modeled 35% take rate, that is only about ₹5.48 expected net benefit per nudged order; offer it selectively, and stop if measured fees or discount cost erase the benefit.

Marketing’s ₹300+ acquisition cost matters because a cancelled first order may end a customer relationship. It is already spent at dispatch time, so it is not an incremental cost saved by shipping; do not double-count it in the immediate decision. The direct expected loss from cancelling a genuine ₹649 order is about ₹402 in contribution, and future repeat value is unknown. That missing lifetime-value data is a reason to protect first orders with confirmation/nudge rather than cancel them on a weak signal.

At 3,000 monthly orders and 55% COD, the rough baseline is 1,650 COD orders × 28% = 462 RTOs, or about **₹78,263/month** in direct RTO cost. This is a scale estimate from the assignment assumptions, not a forecast of savings from this policy.

## What could go wrong

Names and address rules can flag legitimate customers, particularly where addresses use local landmarks or Hinglish. A reply is not proof of deliverability; a high response rate can still leave undelivered COD parcels. The sample is duplicated and stale (no October 29 data), and its scores are not calibrated. Discounts may subsidize customers who would have paid COD anyway. Monitor action and reply rates, payment completion, delivery/RTO by action and pincode, false-cancel complaints, discount spend, and net contribution. Alert on schema changes, duplicate IDs, missing contact fields, and any bucket whose observed outcomes drift from the assumptions.

## Next two weeks

Run the policy in shadow mode on live orders, with no automatic cancellation. Deduplicate orders and freeze a time-based holdout; collect WhatsApp sent/delivered/reply/payment timestamps and final courier outcomes. Calibrate risk bands and cancellation economics on held-out data, then test confirmation and the ₹25 nudge with a controlled comparison. Add pincode rules only with adequate order counts and confidence intervals, and measure repeat purchase/LTV before changing first-order treatment. Keep the optional LLM disabled until privacy approval; it should interpret address text, never make the financial decision.