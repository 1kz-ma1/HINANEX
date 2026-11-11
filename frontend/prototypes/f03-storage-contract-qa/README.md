# F03/P-02 independent storage contract QA prototype (Issue #356)

**DRAFT / local-only / no GIS, RegionExport, public deployment or live alerts.**

Source: owner-reviewed `HINANEX_F03_事前準備UI_レビュー修正版_20261104.zip`, extracted and SHA-256 verified on 2026-11-11. `index.html`, `styles.css`, `app.js` originated from that owner ZIP; this folder is a **separate B QA experiment** and does not replace the owner-approved source ZIP. The original ZIP stays intact outside the repo. See `frontend/docs/F03_P02_STORAGE_CONTRACT_QA_20261111.md` for diff and risks.

## What changed for Issue #356

- Original owner ZIP **automatically read** `localStorage` on initial page load, contrary to the Issue #356 opt-in read requirement. This B prototype does **not touch storage on startup**. Only the user's explicit **「保存済み設定を確認（任意）」** action reads it. This changes user flow intentionally; whether to adopt in the real product requires an owner decision.
- Explicit **「この地域を保存」** now checks read-back before showing `保存しました`.
- A rejected write preserves the previous saved region. An accepted write or deletion whose read-back fails instead shows an unconfirmed status, never a stale saved badge. Invalid saved data can also be explicitly deleted without first saving another region.
- Strictly reject extra keys, altered schema, corrupt JSON; never display invalid saved record as a confirmed region.
- Explain plaintext same-origin localStorage, shared-device exposure, no guaranteed backups/transfer, automatic expiration absent.
- Keep the owner prototype's **one field only**, `hinanex.preparedness.demo.v1`, `schema_version:1`, **no auto expiration**. **DO NOT** reuse PR #311's key or attempt migration. PR #311 is three fields / 180-day recheck and remains a separate E Draft.

## Run actual HTTP Chrome

```bash
cd frontend
node --test tests/f03-storage-contract.test.js
node --test tests/f03-storage-http-chrome.test.js
```

The second test starts a real HTTP server and Chrome using the Chrome DevTools Protocol, with a persistent browser user-data-dir. It tests explicit read/save/update/reload/restart/delete, corrupt schema, storage denial/quota/read-back, no unexpected HTTP and plaintext localStorage. Failure cases inject exceptions or no-op methods; persistence is verified against real localStorage rather than an in-memory replacement. Test requires local Google Chrome or Chromium and a local policy that permits HTTP loopback. If policy blocks `127.0.0.1`, report **BLOCKED** rather than a PASS. The regular `npm test` includes both tests in the GitHub `test` workflow.

On Windows, set `F03_CHROME_BIN` to the Chrome executable's absolute path. Set optional `F03_EVIDENCE_DIR` to an output directory to capture full-page real HTTP PNGs at 320/375/390/430px, with SHA-256 logged. The browser closes gracefully before reusing its profile. This is a browser restart equivalent, not a physical device reboot.

Final QA on 2026-11-11: real HTTP Chrome **16 PASS / 0 FAIL / 0 NOT_RUN**. The detailed report records the source commit, CI logs, screenshots, failures found before fixes and untested acceptance areas.

To inspect manually:

```bash
cd frontend/prototypes/f03-storage-contract-qa
python -m http.server 8000 --bind 127.0.0.1
# Open http://127.0.0.1:8000/index.html in Chrome
```

1. Start with no consent and do not press the read button: no storage operations occur.
2. Choose a sample region and press save; click the read button or reload then click it to verify.
3. Change and save; delete and verify; browser storage settings may also be used to inspect `localStorage`.

**These are three synthetic selectable municipal labels**; they do not establish disaster data accuracy or safety. The links are illustrative official-site entry points only, and not evidence of live external-site availability. Safari, Android physical devices, legal/privacy review and accessibility acceptance are separate gates.
