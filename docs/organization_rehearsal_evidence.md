# Organization maintenance rehearsal evidence

This document records the boundary of the source-only organization-maintenance
rehearsal. It is not a scheduled native receipt and it does not grant local
LogicGuard or organization-snapshot authority.

The rehearsal uses the real maintenance/contribution cycle once against a
disposable source and machine with `push=false`. It must prove all eleven
organization checkpoints, snapshot compare-and-swap, contribution reuse,
postflight, temporary cleanup, preservation of the configured organization
source, preservation of the real local authority pointer, unchanged remote
refs, and no new scheduled-wrapper run.

The authoritative machine-readable result is the content-addressed receipt
under `.local/assurance/organization-rehearsal/`; `current.json` is only its
pointer. The release readiness owner re-verifies that receipt against the
current repository, configured source, and toolchain identities. A missing,
stale, failed, or `not_applicable` rehearsal blocks release. The receipt never
replaces the one future top-level organization wrapper receipt.

The unrelated `assets/readme-hero/hero.png` change remains outside the
organization exchange surface. It is preserved as a source-repository dirty
entry in the rehearsal evidence and is never staged, copied into a packet, or
treated as a card input.
