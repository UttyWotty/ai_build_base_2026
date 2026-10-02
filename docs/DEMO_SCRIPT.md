# Demo script (3 minutes)

The video and the live demo follow this script. Every click is in the deployed app; nothing is edited in between.
Times are targets. The story is one week at the US plant, then one number for the whole period.

| Time | Screen | Say |
|---|---|---|
| 0:00 | Title card, then **Live**: "Bearing week at US1", autopilot on, press Run at 3 h/s | "A failure alert only helps if the repair can happen in time. That depends on stores, purchasing, and customer service, and that is where plants lose days." |
| 0:15 | The feed streams: stops, restarts, spare orders | "This is a plant running: machines stop and restart, spares get used and reordered." |
| 0:25 | At 25 Jul 02:00 the alert arrives; the clock pauses; the autopilot starts | "At two in the morning a new alert comes in: a spindle bearing wearing out on line 2. Nobody is awake. The copilot picks it up." |
| 0:35 | The team's tool calls appear with their names; the three briefs | "Gemini works as a team, built on Google's Agent Development Kit. A maintenance planner reads the vibration, a procurement lead checks spares and suppliers, a customer lead checks orders. All three at once." |
| 1:00 | The lead's answer, the verified line, the proposal with Approve | "The operations lead weighs them. The one bearing set on the shelf goes to the other line, whose alert is overdue. This one gets an air transfer from Germany for 650 dollars, because the supplier's order is late one time in three. Every number here was checked against the tools." |
| 1:25 | **Control room**, US1-L2-01: options table and customers at risk | "Here is what it weighed: every way to get the part, priced. Waiting for the supplier means 190 hours down and four customer orders at risk." |
| 1:40 | Scroll to the vibration chart; the **Supplier inbox**: read the Everline delay notice | "Why the alert: vibration climbing out of its normal band. And this morning the supplier wrote that the order slips to 8 August. Gemini reads it, and the plan updates." |
| 2:00 | Back to **Live**: Approve, press Run; at 26 Jul 10:00 the outcome appears in the feed | "A person approves. The next morning the spindle fails, as predicted, and the line is back in 26 hours instead of 230. 100,000 dollars saved on one alert." |
| 2:25 | **Track record** | "And not just once. Every alert of four months, scored against what really happened, including the times it was wrong: 662 hours of downtime avoided, 198 thousand dollars net." |
| 2:45 | **How it works** | "Gemini on Vertex AI, a team of agents on the Agent Development Kit, one service on Cloud Run. From an alert at 2 a.m. to an approved plan before anyone arrives." |

If the inspection photos are ready, add this after 1:40: on the Control room, open **Field inspection** on US1-L2-01 and click the sample photo. Say: "The technician sends a photo, and Gemini vision confirms the wear before any money is spent." Then open DE1-L2-04 (gearbox, same clock) and its photo. Gemini says the gears are intact and the oil needs flushing: "Not confirmed. This alert never became a failure, and the photo shows it before anyone pays for a gear set."

Before recording:
- Use a paid key or the deployed service on Vertex AI; a team run needs about twelve model calls.
- Warm the Cloud Run instance (`MIN_INSTANCES=1`) and load the page once.
- Press **Reset demo** on Approvals and **Reset** on the Supplier inbox, so the week starts clean.
- Rehearse once at 3 h/s: the alert arrives about 5 seconds after pressing Run.
