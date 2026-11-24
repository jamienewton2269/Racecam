#!/usr/bin/env python3
"""Publish a prebuilt, signed Android APK to an immutable GitHub release."""
import argparse, hashlib, json, os, pathlib, re, subprocess, tempfile
def run(*args):
    return subprocess.check_output(args, text=True).strip()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("apk",type=pathlib.Path)
    p.add_argument("--channel",choices=["stable","beta"],required=True)
    p.add_argument("--repo",default="jamienewton2269/Racecam")
    p.add_argument("--notes",required=True)
    a=p.parse_args()
    apk=a.apk.resolve(strict=True)
    info=run("aapt","dump","badging",str(apk))
    match=re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'",info)
    if not match: raise SystemExit("Cannot read APK identity")
    package,code,version=match.groups()
    if package!="org.sailinguk.racecam": raise SystemExit("Wrong package")
    cert=run("apksigner","verify","--print-certs",str(apk))
    fingerprints=re.findall(r"Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]+)",cert)
    if len(fingerprints)!=1 or fingerprints[0].lower()!=os.environ["JNS_APK_CERT_SHA256"].lower(): raise SystemExit("Unexpected signing certificate")
    tag=f"racecam-{a.channel}-{code}"
    with tempfile.TemporaryDirectory() as d:
        root=pathlib.Path(d)
        asset=root/"racecam.apk"
        asset.write_bytes(apk.read_bytes())
        manifest={"schema":1,"package":package,"versionCode":int(code),"versionName":version,"channel":a.channel,"sha256":hashlib.sha256(asset.read_bytes()).hexdigest(),"size":asset.stat().st_size,"url":f"https://github.com/{a.repo}/releases/download/{tag}/racecam.apk","notes":a.notes}
        m=root/"manifest.json"
        m.write_text(json.dumps(manifest,sort_keys=True,separators=(",",":"))+"\n")
        sig=root/"manifest.sig"
        subprocess.run(["openssl","dgst","-sha256","-sign",os.environ["JNS_MANIFEST_KEY"],"-out",str(sig),str(m)],check=True)
        subprocess.run(["gh","release","create",tag,"--repo",a.repo,"--draft","--title",f"RaceCam {version} ({a.channel})","--notes",a.notes,str(asset),str(m),str(sig)],check=True)
        print("Draft release created; review before publishing:",tag)
if __name__=="__main__": main()
