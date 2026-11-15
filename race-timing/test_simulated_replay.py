import unittest
from simulated_replay import pair,parse,correlated,crossing,run,ORIGIN_LAT,ORIGIN_LON

class ReplayTests(unittest.TestCase):
    def test_pair(self):
        r,g=pair(0,53.5,-3.05)
        self.assertEqual(parse(r)["type"],"RMC")
        self.assertEqual(parse(g)["type"],"GGA")
    def test_corrupt(self):
        self.assertIsNone(correlated(0,53.5,-3.05,True))
    def test_simulation_marker(self):
        self.assertTrue(correlated(0,53.5,-3.05)["simulated"])
        self.assertIsNone(correlated(0,53.5,-3.05)["accuracy_m"])
    def test_crossing(self):
        a=correlated(0,ORIGIN_LAT-0.0001,ORIGIN_LON)
        b=correlated(1,ORIGIN_LAT+0.0001,ORIGIN_LON)
        line=((-30,0),(30,0))
        self.assertEqual(crossing(a,b,line,line,1,1)["status"],"EARLY")
    def test_missing(self):
        b=correlated(1,ORIGIN_LAT+0.0001,ORIGIN_LON)
        self.assertEqual(crossing(None,b,((-30,0),(30,0)),((-30,0),(30,0)),1,1)["status"],"MISSING_FIX")
    def test_scenario(self):
        result=run()
        self.assertEqual(result["mode"],"SIMULATION_ONLY")
        self.assertFalse(result["official"])
        self.assertEqual(len(result["yachts"]),3)

if __name__=="__main__": unittest.main()
