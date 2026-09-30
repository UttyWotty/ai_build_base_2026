# Tech debt

Open items by priority, highest first. Each names the problem, the fix, and how to verify it.
Per convention, resolved items get wrapped in HTML comments rather than deleted.
Component-level limitations carried over from the imported packages are listed in P2.

---

## P0 - Next

- [ ] **CI once GitHub Actions minutes reset on 2026-10-01.** `make setup`, `make lint`, and `make test` on every PR
  into `develop` and `main`. The tests need no model and no generated data.

## P1 - Known limitations

- [ ] **Docstrings in the imported packages still name the standalone make targets** (for example `make data` where
  this repository now has `make pdm-data`). The commands in `README.md` and `docs/components/` are correct.

## P2 - Carried over from the components

- [ ] **pdm_oee:** the model store uses pickle; early warnings for long P-F modes score as false; the simulated plant is
  kind (OEE 82.7%); ten investigation questions only. See `docs/components/pdm.md`.
- [ ] **supply_ontology:** 24 evaluation questions only; the naive half of the consistency demo depends on the model on
  the day. See `docs/components/supply.md`.
