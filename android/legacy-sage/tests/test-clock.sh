#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/android/os"
cat > "$TMP/android/os/SystemClock.java" <<'EOF'
package android.os;
public class SystemClock {
 public static long now=10000;
 public static long elapsedRealtime(){return now;}
}
EOF
cat > "$TMP/TestClock.java" <<'EOF'
import org.sailinguk.racecam.RaceStartClock;
import android.os.SystemClock;
public class TestClock {
 static void check(boolean ok,String name){if(!ok)throw new AssertionError(name);System.out.println("PASS "+name);}
 public static void main(String[] args){
  RaceStartClock c=new RaceStartClock();
  long utc=1790000000000L;
  check(!c.apply("race",1,"a","start",utc+10000),"reject unsynchronised start");
  c.updateClock(utc,9900,10000);
  check(c.apply("race",1,"a","start",utc+10000),"accept start");
  check(c.remainingMs()==9950,"monotonic countdown");
  check(!c.apply("race",1,"a","start",utc+10000),"reject duplicate revision");
  check(c.apply("race",2,"b","postpone",0),"postpone");
  check(!c.isScheduled()&&!c.consumeGun(),"cancel original gun");
  check(c.apply("race",3,"c","new_start",utc+20000),"replacement start");
  SystemClock.now=29950;
  check(c.consumeGun()&&!c.consumeGun(),"single starting event");
  check(c.apply("race",4,"d","new_start",utc+30000),"second schedule");
  SystemClock.now=42000;
  check(!c.consumeGun(),"suppress late event");
  check(!c.apply("other",5,"e","start",utc+60000),"reject wrong epoch");
 }
}
EOF
javac -d "$TMP" "$TMP/android/os/SystemClock.java" src/org/sailinguk/racecam/RaceStartClock.java "$TMP/TestClock.java"
java -cp "$TMP" TestClock
