# 📱 Mars Rover Mobile App — Setup Guide

Your mobile controller app is ready! Here's how to use it on your Android phone.

---

## Option 1: Quick Install as PWA (Recommended — No APK Needed!)

This is the **easiest and fastest** method. Your web app works like a native app.

### Steps:
1. **Host the files** — You need the `index.html`, `manifest.json`, and `sw.js` served over HTTPS. The easiest way:
   - Upload the 3 files to **GitHub Pages** (free):
     - Push `index.html`, `manifest.json`, `sw.js` to a GitHub repo
     - Go to **Settings → Pages → Deploy from main branch**
     - Your app will be live at `https://yourusername.github.io/mars_rover/`
   
   - **OR** use a free host like [Netlify](https://netlify.com): just drag & drop the 3 files.

2. **Open the URL on your phone** in Chrome

3. **Install as App**:
   - Chrome will show an "Add to Home Screen" banner, **tap it**
   - OR tap the **3-dot menu (⋮) → "Install app"** or **"Add to Home Screen"**
   
4. **Done!** The app icon appears on your home screen and launches fullscreen like a native app.

---

## Option 2: Convert to APK (Actual .apk File)

If you want a real APK file to install or share:

### Method A: Using PWABuilder (Easiest)
1. Host your app (see Option 1 step 1)
2. Go to **[PWABuilder.com](https://www.pwabuilder.com/)**
3. Paste your hosted URL
4. Click **"Package for stores"** → Select **Android**
5. Download the generated `.apk` file
6. Transfer to phone and install (enable "Install from Unknown Sources")

### Method B: Using Bubblewrap CLI
```bash
npm install -g @aspect/aspect-build-cli
npm install -g @aspect/aspect-build-cli
npx @nicolo-ribaudo/pwa2apk https://your-hosted-url.com/
```

### Method C: Using Android WebView App (Manual APK)
1. Install **Android Studio**
2. Create a new project with **Empty Activity**
3. Replace `MainActivity.java` with a WebView loading your hosted URL
4. Build the APK

---

## ⚡ How Bluetooth Works on Phone

The app uses **Web Bluetooth API** (works in Chrome on Android).

- Tap **CONNECT** → Chrome shows a Bluetooth pairing dialog
- Select your **HC-05** module
- **Important**: HC-05 is Classic Bluetooth (SPP). Web Bluetooth only supports **BLE (Bluetooth Low Energy)**.

### If HC-05 doesn't appear:
Your HC-05 uses Classic Bluetooth, which Web Bluetooth can't directly connect to. Solutions:

1. **Replace HC-05 with HM-10 (BLE module)** — drop-in replacement, same wiring, works perfectly with Web Bluetooth.
2. **Use a BLE-to-Serial bridge** like an ESP32 or nRF52 board.
3. **Use the Desktop Python GUI** (`rover_control_gui.py`) which supports Classic Bluetooth via pyserial.

---

## 🎮 Controls

| Action | Touch | Keyboard |
|--------|-------|----------|
| Forward | Hold ▲ button | Hold W or ↑ |
| Reverse | Hold ▼ button | Hold S or ↓ |
| Left | Hold ◄ button | Hold A or ← |
| Right | Hold ► button | Hold D or → |
| Stop | Release any button | Release key / Space |

**Hold-to-Move**: The rover moves ONLY while you hold the button. Releasing immediately sends STOP.

---

## Files Created

| File | Purpose |
|------|---------|
| `index.html` | Main mobile app (controller + telemetry dashboard) |
| `manifest.json` | PWA manifest for Android install |
| `sw.js` | Service worker for offline support & installability |
