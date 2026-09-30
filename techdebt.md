# Tech debt

Open items by priority, highest first. Each names the problem, the fix, and how to verify it.
Per convention, resolved items get wrapped in HTML comments rather than deleted.
Component-level limitations carried over from the imported packages are listed in P2.

---

## P0 - Next

- [ ] **Run the container once before the deadline.** `make image` (Docker Desktop) and one real `make deploy` have
  not run yet; the Dockerfile and the script were checked only for syntax. See `docs/HANDOVER.md`.
- [ ] **Proposals live in the container's file system** and reset when a Cloud Run instance restarts. Fine for a
  demo; Firestore or a Cloud Storage object would make approvals durable.
- [ ] **CI once GitHub Actions minutes reset on 2026-10-01.** `make setup`, `make lint`, and `make test` on every PR
  into `develop` and `main`. The tests need no model and no generated data.

## P1 - Known limitations

- [ ] **Docstrings in the imported packages still name the standalone make targets** (for example `make data` where
  this repository now has `make pdm-data`). The commands in `README.md` and `docs/components/` are correct.

- [ ] **The impact service has no service-level test.** Its rules are unit-tested and it was checked on the full data;
  a test with an in-memory world store (`WorldStore.register_frame`) would pin the query layer too.
- [ ] **The line-stops rule is coarse:** any asset outage stops its whole line, and lost output uses the running
  production order's rate. Good enough for ranking options; not a capacity model.

- [ ] **The web app test needs generated data** and is skipped without it, so CI will not run it. A small
  three-world fixture would let it run everywhere.

## P2 - Process

- [ ] **The 0.4.0 agent commit (4e40fe5) landed on develop without a PR.** Rewriting develop was not allowed, so it
  stays; every later change goes through a feature branch.

## P2 - Carried over from the components

- [ ] **pdm_oee:** the model store uses pickle; early warnings for long P-F modes score as false; the simulated plant is
  kind (OEE 82.7%); ten investigation questions only. See `docs/components/pdm.md`.
- [ ] **supply_ontology:** 24 evaluation questions only; the naive half of the consistency demo depends on the model on
  the day. See `docs/components/supply.md`.
