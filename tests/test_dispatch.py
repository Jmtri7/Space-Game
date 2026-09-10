"""Story dispatches — game/world/dispatch.py (gap F inbox comms).
Shared setup lives in tests/harness.py."""
from tests.harness import *  # noqa: F401,F403
from game.world.dispatch import pending_dispatches, receive_dispatch, received_flag

DISPATCHES = {
    "_comment": "ignored",
    "open": {"sender": "A", "subject": "S", "body": "B"},
    "gated": {"sender": "C", "subject": "T", "requires_flag": "act_pressure"},
    "chained": {"sender": "D", "subject": "U", "requires_flag": "dispatch:open"},
    "mission": {"sender": "E", "subject": "V", "requires_flag": "go",
                "on_receive_flags": ["got_v"], "on_receive_rep": {"free_carrier": 5},
                "start_mission": "m1"},
}
MISSIONS = {"m1": {"title": "M1", "stages": [
    {"text": "step", "complete_flag": "done_step",
     "one_way_message": {"sender": "E", "text": "go do it"}}]}}


class TestDispatch(unittest.TestCase):

    def test_ungated_dispatch_is_pending_immediately(self):
        p = Possessions()
        pend = pending_dispatches(DISPATCHES, p)
        self.assertIn("open", [d for d, _ in pend])
        self.assertNotIn("_comment", [d for d, _ in pend])
        self.assertNotIn("gated", [d for d, _ in pend])

    def test_received_dispatch_drops_out_of_pending(self):
        p = Possessions()
        receive_dispatch("open", DISPATCHES["open"], p, {})
        self.assertTrue(p.flags[received_flag("open")])
        self.assertNotIn("open", [d for d, _ in pending_dispatches(DISPATCHES, p)])

    def test_a_dispatch_can_gate_on_another_being_received(self):
        p = Possessions()
        self.assertNotIn("chained", [d for d, _ in pending_dispatches(DISPATCHES, p)])
        receive_dispatch("open", DISPATCHES["open"], p, {})
        self.assertIn("chained", [d for d, _ in pending_dispatches(DISPATCHES, p)])

    def test_receive_applies_flags_rep_and_starts_the_mission(self):
        p = Possessions()
        p.flags["go"] = True
        sender, subject, body, advanced = receive_dispatch("mission", DISPATCHES["mission"], p, MISSIONS)
        self.assertEqual(sender, "E")
        self.assertTrue(p.flags["got_v"])
        self.assertEqual(p.reputation_with("free_carrier"), 5)
        self.assertEqual(p.missions.get("m1"), 0)
        self.assertEqual(advanced, ("m1", 0))

    def test_rep_gate_below(self):
        p = Possessions()
        d = {"x": {"sender": "A", "subject": "S", "requires_rep_below": "ninefold_combine:0"}}
        self.assertEqual(pending_dispatches(d, p), [])  # standing 0 is not < 0
        p.adjust_reputation("ninefold_combine", -5)
        self.assertEqual([n for n, _ in pending_dispatches(d, p)], ["x"])


class TestLongSilenceActTwoPlumbing(unittest.TestCase):
    """Act II reactivity plumbing (PLAN Phase 7.1) against the real story
    config: the reactivation-front dispatch chain arrives in story order, and
    the two courier missions leave an on_end_flags trace."""

    def setUp(self):
        from game.utils import get_dispatches, get_missions
        self.d = get_dispatches("the_long_silence")
        self.m = get_missions("the_long_silence")

    def _pending(self, p):
        return [n for n, _ in pending_dispatches(self.d, p)]

    def test_reactivation_front_chain_is_story_ordered(self):
        p = Possessions()
        self.assertNotIn("relay_front_kiln", self._pending(p))
        p.flags["jumped_to:verdance"] = True
        self.assertIn("relay_front_kiln", self._pending(p))
        self.assertNotIn("relay_front_verdance", self._pending(p))
        p.flags["beacon_ossuary_lit"] = True
        self.assertIn("relay_front_verdance", self._pending(p))
        self.assertNotIn("relay_front_ossuary", self._pending(p))
        p.flags["act_span"] = True
        self.assertIn("relay_front_ossuary", self._pending(p))
        self.assertNotIn("relay_front_span", self._pending(p))
        p.flags["jumped_to:the_span"] = True
        self.assertIn("relay_front_span", self._pending(p))

    def test_courier_missions_now_leave_a_trace(self):
        self.assertEqual(self.m["carrier_relief_run"]["on_end_flags"], ["relief_run_done"])
        self.assertEqual(self.m["combine_evacuation"]["on_end_flags"], ["evac_run_done"])
