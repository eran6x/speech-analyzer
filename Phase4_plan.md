# Speech Analyzer — Phase 4 Plan

**Licensing, distribution & open-sourcing.** Deferred from earlier work so it
doesn't block Phase 3. These are documentation/packaging changes, not product
features.

---

## 1. AGPLv3 LICENSE file

Add a top-level `LICENSE` containing the **full, unmodified** standard text of
the GNU Affero General Public License, Version 3 (19 November 2007) — the
canonical text from <https://www.gnu.org/licenses/agpl-3.0.txt>. Do not
paraphrase or trim it; license validity depends on the exact text.

## 2. README — License & Commercial Use section

Add a section to `README.md`:

> ## Commercial Use
>
> This software is licensed under AGPLv3. If you wish to use this software in a
> commercial or proprietary environment without disclosing your source code,
> please contact me at **eran@cyberung.com** to purchase a commercial license.

Also add a short "License" note linking to the `LICENSE` file and stating the
project is AGPLv3 (copyleft: network use counts as distribution, so hosted/SaaS
deployments must offer their source).

## 3. Supporting changes (optional, same phase)

- **Copyright/license header** in source files (or at least the entry points
  `backend/app/main.py` and `frontend/src/main.jsx`): a short SPDX line —
  `# SPDX-License-Identifier: AGPL-3.0-or-later`.
- **`package.json`** — set `"license": "AGPL-3.0-or-later"`.
- **License badge** in the README header.
- **`AUTHORS`/copyright holder** — record the copyright owner (for the dual-license
  offer to be enforceable, the owner must hold rights to all contributions; add a
  brief CONTRIBUTING/CLA note if outside contributions are expected).

## Notes

- AGPLv3 + a paid commercial license is a standard **dual-licensing** model; it
  only works if a single party owns (or has CLA-backed rights to) the code.
- No code behavior changes — purely legal/metadata.
