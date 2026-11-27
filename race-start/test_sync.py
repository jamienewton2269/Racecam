import unittest
from sync_test import evaluate
def sample(delays):
    return [{"device":str(i),"target_utc_ms":10000,"gun_onset_utc_ms":10000+d} for i,d in enumerate(delays)]
class TestStartSync(unittest.TestCase):
    def test_pass(self):self.assertTrue(evaluate(sample([0,1999]))["within_2s"])
    def test_boundary(self):self.assertTrue(evaluate(sample([0,2000]))["within_2s"])
    def test_fail(self):self.assertFalse(evaluate(sample([0,2001]))["within_2s"])
    def test_shared_lateness(self):
        r=evaluate(sample([2500,2600]))
        self.assertTrue(r["within_2s"])
        self.assertEqual(r["earliest_error_ms"],2500)
    def test_mismatched_targets(self):
        x=sample([0,1]);x[1]["target_utc_ms"]=11000
        with self.assertRaises(ValueError):evaluate(x)
    def test_duplicate(self):
        x=sample([0,1]);x[1]["device"]=x[0]["device"]
        with self.assertRaises(ValueError):evaluate(x)
if __name__=="__main__":unittest.main()
