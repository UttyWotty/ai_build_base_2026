# Demo script (under 3 minutes)

The video and the live demo follow this script, recorded in the deployed app with nothing edited on screen.
It is in four parts: what to set up once, what to check before each take, the take itself, and what to undo after.
The story is one week at the US plant, then one number for the whole period, and it runs about 2:50.

App: https://ops-copilot-432875717420.asia-southeast1.run.app
Service `ops-copilot` in region `asia-southeast1`. The commands below read the project id from `PROJECT_ID`.

## 1. Once, before the first take

Run these in a terminal with gcloud logged in, after `export PROJECT_ID=<your project id>`. Each `services update` starts a new revision and
causes a gap of about 20 seconds, so do them before recording, never between takes.

1. Keep one instance warm, so no take hits a cold start (stays on through judging, 19 Oct to 6 Nov):

   ```
   gcloud run services update ops-copilot --project "$PROJECT_ID" --region asia-southeast1 --min-instances 1
   ```

2. Raise the usage limit for recording. Every Gemini-backed click counts as one call (the team run, a supplier
   message, a photo, an "Ask about this" question), and the public limit is 10 per visitor per hour. A full take uses
   about 4, so 40 allows several retakes:

   ```
   gcloud run services update ops-copilot --project "$PROJECT_ID" --region asia-southeast1 --update-env-vars USAGE_LIMIT_PER_VISITOR=40
   ```

3. Open the app once and check the health page: `<app>/health` shows `{"status":"ok"}`.
4. Set up the recorder: macOS Cmd+Shift+5, "Record selected portion" around the browser window, Options > microphone on.
   Browser zoom 100 to 110 percent, one window, no other tabs or bookmarks bar in view.

## 2. Before every take (30 seconds)

1. **Approvals** > **Reset demo** (clears drafted plans and outcomes).
2. **Supplier inbox** > **Reset** (clears read messages, inspections, and operator verdicts).
3. Reload the page, so the clock and the feed start fresh.
4. **Live**: click **Bearing week at US1** (the small link under the clock, top right) so the clock goes back to
   24 Jul 12:00, click **3 h/s** (the default is 1 h/s), and leave **Autopilot** ticked.

## 3. The take

| Time | Screen and click | Say |
|---|---|---|
| 0:00 | **Live**, press **Run**. The feed streams stops, restarts, spare orders | "Two a.m. Two machines are about to fail, and there's one spare bearing on the shelf. Predicting failures is the easy part. Deciding who gets the part, what it costs, and which customers slip takes four departments. OSI decides before anyone arrives." |
| 0:18 | The alert arrives, the clock pauses, the autopilot starts. Now click **1 h/s** (see the clock rule below) | "A spindle bearing on line 2 is wearing out. Nobody is awake. The copilot picks it up." |
| 0:25 | The team's tool calls appear with their names, then the three briefs | "Gemini works as a team, built on Google's Agent Development Kit. A maintenance planner reads the vibration, a procurement lead checks spares and suppliers, a customer lead checks orders. All three at once." |
| 0:45 | The proposal appears: press **Pause** at once. Then show the lead's answer and the verified line; do not approve yet | "The operations lead weighs them. The one bearing set on the shelf goes to the other line, whose alert is overdue. This one gets an air transfer from Germany for 650 dollars, because the supplier is late one time in three. Every number here was checked against the tools." |
| 1:05 | **Control room**, alert US1-L2-01: **Every way to get the spare** and customers at risk | "Here is what it weighed: every way to get the part, priced. Waiting for the supplier means 190 hours down and four customer orders at risk." |
| 1:15 | Scroll to the vibration chart. Then **Supplier inbox**: the Everline notice, **Read with Gemini** | "Why the alert: vibration climbing out of its normal band. And this morning the supplier wrote that the order slips to 8 August. Gemini reads it, and the plan updates." |
| 1:33 | **Control room**, US1-L2-01, **Field inspection**: click the **Sample** photo | "The technician sends a photo, and Gemini vision confirms the wear before any money is spent." |
| 1:43 | Alert DE1-L2-04 (gearbox, same clock), **Field inspection**, its **Sample** photo | "A gearbox alert in Germany, same night. Gemini sees intact gears: not confirmed." |
| 1:52 | Optional: **Operator verdict**, type "Gear teeth intact on inspection", **Mark as false alert** | "The engineer marks it false. The next alert on this gearbox carries that note and asks for an inspection first. It is never hidden." |
| 2:02 | **Approvals**: **Approve**. Then **Live**, **Run**; about 22 seconds later (26 Jul 10:00) the outcome appears in the feed: press **Pause** | "A person approves. The next morning the spindle fails, as predicted, and the line is back in 26 hours instead of 230. 100,000 dollars saved on one alert." |
| 2:22 | **Track record** | "And not just once. Every alert of four months, scored against what really happened, including the times it was wrong: 662 hours of downtime avoided, 198 thousand dollars net." |
| 2:38 | **How it works** | "Not another failure predictor: a team of Gemini agents that decides when parts are scarce, and proves it paid off, mistakes included. On Vertex AI and Cloud Run." |
| 2:50 | End | |

If time runs long, drop the optional verdict row first (10 seconds), then the DE1-L2-04 photo (9 seconds).

The clock rule (learned in a rehearsal on 2026-10-13): the clock pauses only while the team works. Once the
proposal appears it runs on, and at 26 Jul 10:00 the spindle fails. If that happens before you approve, the run shows
the emergency buy instead of the saving, and the take must restart from section 2. At 3 h/s you have about 10
seconds to press Pause; switching to 1 h/s while the team works gives about 30. The Live panel also forgets the
proposal when you leave the page, which is why the approval happens on **Approvals**.

Notes for the take:
- The team run takes 45 to 95 seconds on Gemini, longer than its narration. Keep talking over the tool calls, or cut
  the wait when editing; the times above assume the wait is cut.
- Name a specific alert in anything you type. A question such as "how many alerts are open" once came back
  unverified.
- If a step shows a usage-limit message, the 40 calls for the hour are used up: wait, or raise the limit again.
- To retake, go back to section 2.

## 4. After recording

1. Put the usage limit back to the public value (keep the warm instance until judging ends on 6 Nov):

   ```
   gcloud run services update ops-copilot --project "$PROJECT_ID" --region asia-southeast1 --update-env-vars USAGE_LIMIT_PER_VISITOR=10
   ```

2. Run section 2 once more, so judges find the demo clean.
3. Upload the video (YouTube unlisted, Vimeo, or a public Drive link), under 3 minutes.
4. Put the video URL into the deck's closing slide, `README.md`, and `docs/SUBMISSION.md`; re-export the deck from
   Share > Export > PDF and replace `docs/OSI-deck.pdf`; cut a patch release.
5. After judging (6 Nov): set `--min-instances 0`.
