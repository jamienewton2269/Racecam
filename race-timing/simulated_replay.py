"""Deterministic, SIMULATION_ONLY moving-line race start demonstration."""
from datetime import datetime, timezone, timedelta
from math import cos, radians
import json

ORIGIN_LAT=53.5
ORIGIN_LON=-3.05
METRES_PER_DEG_LAT=111195.0
METRES_PER_DEG_LON=METRES_PER_DEG_LAT*cos(radians(ORIGIN_LAT))

def nmea(payload):
    checksum=0
    for char in payload: checksum^=ord(char)
    return f"${payload}*{checksum:02X}"

def coord(value,latitude):
    deg=int(abs(value))
    minute=(abs(value)-deg)*60
    return (f"{deg:02d}" if latitude else f"{deg:03d}")+f"{minute:07.4f}",("N" if value>=0 else "S") if latitude else ("E" if value>=0 else "W")

def parse(sentence):
    if not sentence.startswith("$") or sentence.count("*")!=1: raise ValueError("framing")
    payload,check=sentence[1:].split("*")
    checksum=0
    for char in payload: checksum^=ord(char)
    if len(check)!=2 or int(check,16)!=checksum: raise ValueError("checksum")
    f=payload.split(",")
    if f[0] not in ("GPRMC","GNRMC","GPGGA","GNGGA"): raise ValueError("type")
    if f[0].endswith("RMC"):
        if f[2]!="A": raise ValueError("invalid RMC")
        lat,lon=decode_coord(f[3],f[4],True),decode_coord(f[5],f[6],False)
        stamp=datetime.strptime(f[9]+f[1][:6],"%d%m%y%H%M%S").replace(tzinfo=timezone.utc)
        return {"type":"RMC","lat":lat,"lon":lon,"utc":stamp.isoformat(),"clock":f[1][:6]}
    if int(f[6])<1: raise ValueError("invalid GGA")
    return {"type":"GGA","lat":decode_coord(f[2],f[3],True),"lon":decode_coord(f[4],f[5],False),"clock":f[1][:6],"satellites":int(f[7]),"hdop":float(f[8])}

def decode_coord(raw,hemisphere,latitude):
    digits=2 if latitude else 3
    deg=int(raw[:digits]);minutes=float(raw[digits:])
    limit=90 if latitude else 180
    if minutes<0 or minutes>=60 or deg>limit or (deg==limit and minutes!=0): raise ValueError("coordinates")
    if hemisphere not in (("N","S") if latitude else ("E","W")): raise ValueError("hemisphere")
    return (deg+minutes/60)*(-1 if hemisphere in ("S","W") else 1)

def pair(epoch,lat,lon,corrupt=False):
    stamp=datetime(2026,11,15,12,0,tzinfo=timezone.utc)+timedelta(seconds=epoch)
    la,ns=coord(lat,True);lo,ew=coord(lon,False)
    clock=stamp.strftime("%H%M%S")
    rmc=nmea(f"GPRMC,{clock},A,{la},{ns},{lo},{ew},0.0,000.0,{stamp.strftime('%d%m%y')},,,A")
    gga=nmea(f"GPGGA,{clock},{la},{ns},{lo},{ew},1,09,0.9,0.0,M,0.0,M,,")
    if corrupt: rmc=rmc[:-2]+("00" if rmc[-2:]!="00" else "FF")
    return rmc,gga

def correlated(epoch,lat,lon,corrupt=False):
    r,g=pair(epoch,lat,lon,corrupt)
    try: a,b=parse(r),parse(g)
    except ValueError: return None
    if a["clock"]!=b["clock"] or abs(a["lat"]-b["lat"])>0.00002 or abs(a["lon"]-b["lon"])>0.00002: return None
    return {"epoch":epoch,"lat":a["lat"],"lon":a["lon"],"utc":a["utc"],"satellites":b["satellites"],"hdop":b["hdop"],"simulated":True,"accuracy_m":None}

def crossing(prev,cur,previous_line,current_line,start_epoch,accuracy_assumption_m):
    if not prev or not cur: return {"status":"MISSING_FIX"}
    if cur["epoch"]-prev["epoch"]!=1: return {"status":"STALE_FIX"}
    if accuracy_assumption_m<=0: raise ValueError("invalid assumption")
    # Two moving buoy endpoints; interpolate line and yacht simultaneously.
    def signed(f,line):
        ax,ay=line[0];bx,by=line[1]
        x=(f["lon"]-ORIGIN_LON)*METRES_PER_DEG_LON
        y=(f["lat"]-ORIGIN_LAT)*METRES_PER_DEG_LAT
        return ((bx-ax)*(y-ay)-(by-ay)*(x-ax))/((bx-ax)**2+(by-ay)**2)**0.5
    d0=signed(prev,previous_line);d1=signed(cur,current_line)
    if d0*d1>0: return {"status":"NO_CROSSING"}
    if abs(d0)<=accuracy_assumption_m or abs(d1)<=accuracy_assumption_m:
        return {"status":"INDETERMINATE","reason":"assumed_position_uncertainty"}
    fraction=abs(d0)/(abs(d0)+abs(d1))
    epoch=prev["epoch"]+fraction
    return {"status":"EARLY" if epoch<start_epoch else "AFTER_START","crossing_epoch":round(epoch,3),"simulated":True}

def run():
    start=5
    boats={"Early":4.1,"Late":6.1,"Missing":4.1}
    events=[]
    for name,cross_at in boats.items():
        fixes=[]
        for t in range(10):
            lat=ORIGIN_LAT+(t-cross_at)*0.00010
            fixes.append(correlated(t,lat,ORIGIN_LON,corrupt=(name=="Missing" and t==4)))
        results=[]
        for t in range(1,10):
            line0=((-30,0.05*(t-1)),(30,0.05*(t-1)))
            line1=((-30,0.05*t),(30,0.05*t))
            result=crossing(fixes[t-1],fixes[t],line0,line1,start,accuracy_assumption_m=1.0)
            if result["status"] not in ("NO_CROSSING",):
                results.append(result)
        events.append({"yacht":name,"events":results})
    return {"mode":"SIMULATION_ONLY","official":False,"assumed_accuracy_m":1.0,"start_epoch":start,"yachts":events}

if __name__=="__main__": print(json.dumps(run(),indent=2))
