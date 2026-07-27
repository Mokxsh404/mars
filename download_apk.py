#!/usr/bin/env python3
import urllib.request
import json
import time
import os
import sys

print("Monitoring GitHub Actions APK Build...")

repo = "Mokxsh404/mars"
api_url = f"https://api.github.com/repos/{repo}/actions/runs"

for i in range(40):
    try:
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode())
        
        runs = [r for r in data.get('workflow_runs', []) if r.get('name') == 'Build Android APK']
        if runs:
            latest = runs[0]
            status = latest.get('status')
            conclusion = latest.get('conclusion')
            print(f"[{i*5}s] Build Status: {status} | Conclusion: {conclusion}")
            
            if status == 'completed':
                if conclusion == 'success':
                    print("Build succeeded! Fetching release APK link...")
                    rel_url = f"https://api.github.com/repos/{repo}/releases"
                    r_req = urllib.request.Request(rel_url, headers={'User-Agent': 'Mozilla/5.0'})
                    r_res = urllib.request.urlopen(r_req)
                    releases = json.loads(r_res.read().decode())
                    
                    if releases and 'assets' in releases[0]:
                        for asset in releases[0]['assets']:
                            if asset['name'] == 'MarsRover-HC05-Control.apk':
                                dl_url = asset['browser_download_url']
                                print(f"Downloading APK from {dl_url}...")
                                target = os.path.join(os.getcwd(), 'MarsRover-HC05-Control.apk')
                                urllib.request.urlretrieve(dl_url, target)
                                print(f"\nSUCCESS! APK saved directly to your folder:")
                                print(f"-> {target}\n")
                                sys.exit(0)
                    print("Release asset link found at: https://github.com/Mokxsh404/mars/releases")
                    sys.exit(0)
                else:
                    print(f"Build finished with status: {conclusion}")
                    break
    except Exception as e:
        print(f"Checking status: {e}")
    time.sleep(5)

print("\nDirect Release Link: https://github.com/Mokxsh404/mars/releases")
