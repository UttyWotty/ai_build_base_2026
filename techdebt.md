# Tech debt

Open items by priority, highest first. Each names the problem, the fix, and how to verify it.
Per convention, resolved items get wrapped in HTML comments rather than deleted.
Component-level limitations carried over from the imported packages are listed in P3.

---

## P0 - Before the 2026-10-18 submission

- [ ] **Run `make deploy` once against a real project** as soon as the Google Cloud account exists. The image was
  built and served locally; the deploy script was checked only for syntax. See `docs/HANDOVER.md`.
  - **Blocked on funding (2026-10-02):** waiting for the competition credits, company sponsorship under the company
    name, or a second team member to share the cost. The demo video, the full evaluation, the live team run, and the
    final write-up all follow the deploy.
- [ ] **Full Gemini evaluation.** The AI Studio free tier allows about 20 requests per model per day. An agent run
  takes about five, and a team run about twelve, so `make eval` cannot finish on it. Run it on a paid key or on Vertex
  AI after the deploy, and put the score in the README.
- [ ] **A live team run end to end.** The three specialists have run live on Gemini; the lead's step then hit a Gemini
  503 overload. It passes offline with a scripted model. Run "Draft the plan with the copilot" once on a paid key or
  Vertex AI.

## P1 - For the finals (Top 200 architecture sprints, Top 50 round)

- [ ] **Durable state on Google Cloud.** Proposals, inspections, and supplier updates live in JSON files in the
  container and reset when an instance restarts. Move them to Firestore.
- [ ] **Google Cloud native data path.** BigQuery for the conformed tables, Pub/Sub for the live sensor and event
  stream, Vertex AI for the failure model, and Cloud Monitoring for the agent's latency and errors.
- [ ] **Delete the Streamlit app** (`src/backend/copilot/ui`, `make app`) and its tests after the first successful
  Cloud Run deploy of the React version.
- [ ] **Team runs cost about twelve model calls.** Cache specialists' briefs per alert and clock, or let the lead
  skip specialists whose brief would not change.

## P2 - Known limitations

- [ ] **Decisions are applied independently.** A transfer is not charged for the sister site's later needs, and an
  arrived transfer is reserved for its alert even if another alert's deadline comes first.
- [ ] **The line-stops rule is coarse:** any asset outage stops its whole line, and lost output uses the running
  production order's rate. Good enough for ranking options; not a capacity model.
- [ ] **The impact service has no service-level test.** Its rules are unit-tested and it was checked on the full data;
  a test with an in-memory world store (`WorldStore.register_frame`) would pin the query layer too.
- [ ] **The Streamlit page test needs generated data** and is skipped without it, so CI will not run it.
- [ ] **The frontend bundle is about 780 KB** (Recharts and Markdown). Code-split the charts if load time matters.
- [ ] **Docstrings in the imported packages still name the standalone make targets** (for example `make data` where
  this repository now has `make pdm-data`). The commands in `README.md` and `docs/components/` are correct.

## P3 - Process and carried over

- [ ] **The 0.4.0 agent commit (4e40fe5) landed on develop without a PR,** and PR #19 was merged with a failing test
  (fixed in #20). Merges now run only after `make lint` and `make test` succeed.
- [ ] **pdm_oee:** the model store uses pickle; early warnings for long P-F modes score as false; the simulated plant is
  kind (OEE 82.7%); ten investigation questions only. See `docs/components/pdm.md`.
- [ ] **supply_ontology:** 24 evaluation questions only; the naive half of the consistency demo depends on the model on
  the day. See `docs/components/supply.md`.

<!-- - [ ] **Run the container once before the deadline.** `make image` (Docker Desktop) and one real `make deploy` have
  not run yet; the Dockerfile and the script were checked only for syntax. Resolved 2026-09-30: the image was built and
  served locally. -->
<!-- - [ ] **A quota error broke every autopilot triage.** Resolved: fallback across Gemini models, plain-language errors,
  and an autopilot that stops itself. -->
<!-- - [ ] **CI, now that GitHub Actions minutes have reset (2026-10-01).** `make setup`, `make lint`, and `make test` on
  every PR into `develop` and `main`, with Python 3.11 and Node 22. The tests need no model and no generated data. Resolved 2026-10-02:
  `.github/workflows/ci.yml`, green once on its PR, then switched to manual runs to save Actions minutes. -->
<!-- - [ ] **Sample inspection photos (in progress, the team is generating them).** The field-inspection feature is built
  and unit-tested, but it has not been run on a real photo. The prompts and file names are in `demo/field/README.md`.
  - **Fix:** put the images in `demo/field/photos/` with the listed names.
  - **Verify:** each photo is read by Gemini on its alert. The worn bearing, pump, and gearbox photos should confirm the
    prediction; the healthy US1-L3-02 bearing should not.
  Resolved 2026-10-02: five photos in demo/field/photos, each read by Gemini on its alert; the results are in
  demo/field/README.md. The gearbox photo is the false-alert case, since the data has no false bearing alert. -->
