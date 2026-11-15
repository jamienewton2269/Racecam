import copy, tempfile, unittest
from pathlib import Path
from snapshot import validate, save_cache, load_cache, SnapshotError
S={"schema_version":1,"race_id":"r1","snapshot_id":"r1-v1","revision":1,"issued_at_utc":"2026-11-15T12:00:00Z","start_at_utc":"2026-11-15T12:15:00Z","handicap":{"method":"time_on_time","rule_id":"club","rule_version":"1"},"course":{"marks":[]},"entries":[{"entry_id":"e1","yacht_id":"y1","camera_id":"c1","display_name":"Boat","rating":"0.95"}]}
class TestSnapshot(unittest.TestCase):
 def test_valid(self):self.assertEqual(validate(S)["revision"],1)
 def test_cache(self):
  with tempfile.TemporaryDirectory() as d:
   p=str(Path(d)/"race.json");save_cache(p,S);self.assertEqual(load_cache(p),S)
 def test_duplicate(self):
  d=copy.deepcopy(S);e=copy.deepcopy(d["entries"][0]);e["entry_id"]="e2";e["yacht_id"]="y2";d["entries"].append(e)
  with self.assertRaises(SnapshotError):validate(d)
 def test_invalid_rating(self):
  for rating in ("NaN","0","-1","infinity","bad"):
   d=copy.deepcopy(S);d["entries"][0]["rating"]=rating
   with self.assertRaises(SnapshotError):validate(d)
 def test_unknown_method(self):
  d=copy.deepcopy(S);d["handicap"]["method"]="unknown"
  with self.assertRaises(SnapshotError):validate(d)
 def test_schema(self):
  d=copy.deepcopy(S);d["schema_version"]=0
  with self.assertRaises(SnapshotError):validate(d)
 def test_start(self):
  d=copy.deepcopy(S);d["start_at_utc"]="2026-11-15T11:00:00Z"
  with self.assertRaises(SnapshotError):validate(d)
if __name__=="__main__":unittest.main()
