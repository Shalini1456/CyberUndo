# CyberUndo — “Ctrl + Z for Cybersecurity”

An interactive, dark-mode cybersecurity product prototype demonstrating instant blast radius containment and file access revocation.

## Key Features & Flow

1. **Share File**:
   - `Project_Final.pdf` → `Person A` (`alex.morgan@partnercorp.io`)
   - Instant token generation & tracking activation

2. **Activity Tracking**:
   - `SHARED` → `VIEWED` → `DOWNLOADED` (3x propagation)
   - Real-time audit telemetry logs with geo-IP tracking

3. **Blast Radius Analysis**:
   - Lineage: `You → Person A → 3 Downloads`
   - Real-time threat indicator: `Exposure: HIGH`

4. **Undo Killswitch (Revoke Access)**:
   - Red **REVOKE ACCESS** button with live glow animation
   - Keyboard shortcut: **`Ctrl + Z`** (or `Cmd + Z`) anytime

5. **Remediation Result**:
   - `ACCESS REVOKED`: Active socket sessions severed at the edge proxy
   - `LINK INVALIDATED`: Signed URL rendered `403 Forbidden`
   - `Exposure: CONTAINED / ZERO RISK`

## How to Run

Simply double-click [`index.html`](./index.html) to open in Google Chrome, Microsoft Edge, Firefox, or any modern web browser.

Alternatively, serve locally using Python:
```bash
python -m http.server 8080 --directory "C:\Users\Balakrishnan\.gemini\antigravity\scratch\cyberundo-prototype"
```
and open `http://localhost:8080` in your browser.
