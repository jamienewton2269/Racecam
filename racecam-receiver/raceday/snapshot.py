"""RaceDay handicap snapshot validation and atomic offline cache. Standard library only."""
import json, os, tempfile
from decimal import Decimal, InvalidOperation
from datetime import datetime

class SnapshotError(ValueError): pass

def validate(data):
    if not isinstance(data,dict) or data.get("schema_version") != 1:
        raise SnapshotError("Unsupported schema")
    for key in ("race_id","snapshot_id"):
        if not isinstance(data.get(key),str) or not data[key]:
            raise SnapshotError("Missing "+key)
    if type(data.get("revision")) is not int or data["revision"] < 1:
        raise SnapshotError("Invalid revision")
    try:
        issued=datetime.fromisoformat(data["issued_at_utc"].replace("Z","+00:00"))
        start=datetime.fromisoformat(data["start_at_utc"].replace("Z","+00:00"))
        if not all(data[k].endswith("Z") for k in ("issued_at_utc","start_at_utc")) or start < issued:
            raise ValueError()
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        raise SnapshotError("Invalid UTC start/issue time") from exc
    h=data.get("handicap")
    if not isinstance(h,dict) or h.get("method")!="time_on_time" or not h.get("rule_id") or not h.get("rule_version"):
        raise SnapshotError("Unsupported or incomplete handicap rule")
    course=data.get("course")
    if not isinstance(course,dict) or not isinstance(course.get("marks"),list):
        raise SnapshotError("Invalid course")
    entries=data.get("entries")
    if not isinstance(entries,list) or not entries:
        raise SnapshotError("Missing entries")
    seen={k:set() for k in ("entry_id","yacht_id","camera_id")}
    for e in entries:
        if not isinstance(e,dict): raise SnapshotError("Invalid entry")
        for k in seen:
            v=e.get(k)
            if not isinstance(v,str) or not v or v in seen[k]:
                raise SnapshotError("Missing/duplicate "+k)
            seen[k].add(v)
        if not isinstance(e.get("display_name"),str) or not e["display_name"].strip():
            raise SnapshotError("Missing yacht name")
        if not isinstance(e.get("rating"),str):
            raise SnapshotError("Rating must be decimal string")
        try: rating=Decimal(e["rating"])
        except InvalidOperation as exc: raise SnapshotError("Invalid rating") from exc
        if not rating.is_finite() or rating<=0: raise SnapshotError("Invalid rating")
    return data

def save_cache(path,snapshot):
    validate(snapshot)
    directory=os.path.dirname(os.path.abspath(path))
    os.makedirs(directory,mode=0o700,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".racecam-",dir=directory)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(snapshot,f,sort_keys=True)
            f.flush();os.fsync(f.fileno())
        os.chmod(tmp,0o600)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def load_cache(path):
    with open(path,encoding="utf-8") as f:return validate(json.load(f))
