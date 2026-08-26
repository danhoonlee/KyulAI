# WSL Serving Migration Audit

Date: 2026-07-22

## Conclusion

No missing production frontend asset, model artifact, persistent wedding record, authentication
database, RAG configuration, or CafeDeCafe route was found in the Mac-to-WSL migration.

## Verified parity

- `src/frontend/wedding`: checksum-identical between Mac and WSL, including pages, maps, calendar,
  Open Graph images, cover raster assets, and every self-hosted font file.
- `runtime/wedding/rsvp-submissions.jsonl`: checksum-identical; 1 RSVP and 1 guestbook record, with
  no malformed JSONL records.
- `runtime/wedding/admin-token.txt`: checksum-identical.
- `data/imperialax_auth.sqlite3`: checksum-identical; 5 users, 13 entitlements, 29 sessions, and 1
  access request.
- `.env.local` and Nangman `.env`: checksum-identical; secret values were not printed.
- DD Laminate, Injection, and ImperialAX frontend directories: checksum-identical.
- Laminate RAG source and `data/rag`: checksum-identical.
- Canonical Laminate and all six deployed Injection model directories: checksum-identical.
- Nangman source/configuration: checksum-identical after excluding runtime logs, virtualenv, cache,
  and the actively updated database.
- Nangman WSL database is ahead of the former Mac database as expected: 310 documents and 1,628
  chunks on WSL versus 284 documents and 1,602 chunks on Mac.

## Runtime verification

- `imperialax-laminate.service`: active and enabled.
- `imperialax-injection.service`: active and enabled.
- `cafedecafe-nangman.service`: active and enabled.
- `cafedecafe-nangman-sync.timer`: active and enabled, with a 15-minute schedule.
- `cafedecafe-cloudflared.service`: active and enabled.
- No failed WSL user services were present.
- Recent Laminate, Injection, CafeDeCafe Tunnel, Nangman, and Nangman sync logs contained no
  matching error, exception, traceback, failure, or HTTP 5xx entries.
- Wedding page variants, guestbook/admin APIs, fonts, maps, calendar, Open Graph image, legacy
  Laminate/DD URLs, Injection URL, and Nangman health endpoint responded successfully.
- Public Laminate readiness reported all five canonical/u3 models as loaded.
- Public Injection readiness reported all six ML/DL models as loaded.

## Intentionally not migrated as production state

- `/Users/danlee/Wedding/mobile_wedding_invitation_donghoon_seyeon.html` is an older June 30
  prototype and is superseded by `src/frontend/wedding/index.html`.
- Mac-only historical server logs, temporary distillation outputs, and Codex/OMX session state are
  not required by WSL serving.
- The WSL checkout still contains obsolete `luvelox_app.py` and
  `services/luvelox_auth_store.py` files that are absent from the current Mac tree. They are extra
  legacy files, not missing migration content, and are not used by the active service composition.

## Remaining operational risks

The audit originally identified three operational gaps. Follow-up remediation completed the
following work:

1. A daily rotating backup now writes consistent SQLite and JSONL snapshots to the Windows disk,
   retains 14 archives, and verifies SHA-256 and restore integrity. The first real archive passed
   extraction and database integrity tests.
2. WSL user lingering is enabled, and the Windows login Startup script includes all serving and
   backup services. A UAC-elevated installer is prepared on the Windows desktop to add the remaining
   pre-login Task Scheduler trigger.
3. The former Mac DD, Injection, Nangman API, and Nangman sync launch agents are disabled and their
   listeners are stopped. Their plist files remain available for emergency rollback. All public
   WSL endpoints remained healthy after the Mac processes stopped.
