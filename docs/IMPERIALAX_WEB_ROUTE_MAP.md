# ImperialAX Web Route Map

Last reviewed: 2026-08-15

This file is the canonical inventory for public ImperialAX web pages. Route changes must update this table and the host-aware regression tests in the same change.

| Host | Canonical route | Locale | Surface | Status |
| --- | --- | --- | --- | --- |
| `ai.imperialax.com` | `/`, `/index.html`, `/en` | English | Login and module workspace | Active; all three serve the same UI |
| `ai.imperialax.com` | `/ko`, `/index.ko.html` | Korean | Login and module workspace | Active |
| `ai.imperialax.com` | `/admin`, `/admin.html` | English | Account and entitlement administration | Active; `/admin` redirects to `/admin.html` |
| `ai.imperialax.com` | `/admin.ko.html` | Korean | Account and entitlement administration | Active |
| `ai.imperialax.com` | `/optimization.html` | English | Laminate optimization | Active |
| `ai.imperialax.com` | `/optimization.ko.html` | Korean | Laminate optimization | Active |
| `laminate.imperialax.com` | `/`, `/ko` | Korean | Established Laminate forecast | Active |
| `laminate.imperialax.com` | `/en` | English | Established Laminate forecast | Active |
| `laminate.imperialax.com` | `/v2`, `/v2/ko` | Korean | Redesigned Laminate forecast | Review generation |
| `laminate.imperialax.com` | `/v2/en` | English | Redesigned Laminate forecast | Review generation |
| `injection.imperialax.com` | `/`, `/ko` | Korean | Established Injection forecast | Active |
| `injection.imperialax.com` | `/en` | English | Established Injection forecast | Active |
| `injection.imperialax.com` | `/v2` | English | Redesigned Injection forecast | Review generation |
| `injection.imperialax.com` | `/v2/ko` | Korean | Redesigned Injection forecast | Review generation |
| `injection.imperialax.com` | `/v2/en` | English | Redesigned Injection forecast | Review generation |

## Legacy and auxiliary routes

- `/login-v2.html` redirects to `/index.html`; `/login-v2.ko.html` redirects to `/index.ko.html` so a second login design cannot drift from the workspace entry.
- Signup, self-service password recovery, and demo login links are shown only when the matching server capability is enabled.
- Wedding pages own `/wedding/*`. The bare `/admin` route is resolved by host so `ai.imperialax.com/admin` can never open or redirect to Wedding Admin.
- Direct `.html` module routes remain compatibility aliases. New navigation should use the canonical root/locale paths above.

## Change checklist

1. Update this inventory and the relevant host-aware route test.
2. Verify Korean and English HTML, CSS, JavaScript, logo assets, and authentication gate requests.
3. Verify empty, loading, success, validation, and error states on desktop and mobile.
4. Confirm Assistant context identifies the active product before and after prediction.
5. Confirm hidden or unsupported DOE conditions are absent from selectors and still rejected by the API.
6. Deploy only after route, model-contract, and browser smoke tests pass.
