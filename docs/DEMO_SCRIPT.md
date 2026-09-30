# Demo script (3 minutes)

The video and the live demo follow this script. Every click is in the deployed app; nothing is edited in between.
Times are targets. Keep the top-bar clock on "Bearing squeeze at US1" unless a step says otherwise.

| Time | Screen | Say |
|---|---|---|
| 0:00 | Title card, then Live at "Bearing week at US1", press Run at 3 h/s | "A failure alert is only useful if the repair can happen in time. That depends on stores, purchasing, and customer service, and that is where plants lose days." |
| 0:20 | The feed streams; at 25 Jul 02:00 the alert arrives, the clock pauses, the autopilot starts | "The plant runs; machines stop and restart. At 02:00 a new alert arrives, and the copilot picks it up on its own." |
| 0:35 | Conflict banner, spare and supplier cards | "One bearing set on the shelf, two spindles wearing out. The replacement is with a supplier who was on time 66% of the time in the last 90 days. That comes from a governed metric, and here is its SQL fingerprint." |
| 0:55 | Select the US1-L2-01 alert; options table | "Here is every way to get the part, priced. Waiting for the open order costs 190 hours and 94 thousand dollars, with four customer orders at risk. An air transfer from our German site costs 650 dollars." |
| 1:20 | Sensor chart | "This is why the model raised the alert: spindle vibration climbing past its normal range over the week." |
| 1:35 | Click "Draft the plan with the copilot" | "Now Gemini, through Google's Agent Development Kit, investigates on its own. Watch each tool call appear as it happens: impact, sensors, the supplier, then the proposal." |
| 2:00 | The live tool timeline, then the answer and the verified badge | "Every number in the answer is checked against the tools. The trace shows exactly what it looked at. It did not order anything; it made a proposal." |
| 2:20 | Approve in the autopilot panel, press Run; at 26 Jul 10:00 the feed shows the outcome | "A person approves. DE1's bearing is on its way. The next morning the spindle fails, as predicted, and the line is back in 26 hours instead of 230." |
| 2:35 | Top bar: "Hydraulic pump wear at DE1" | "On a calm day it stays calm: the spare is in stock, so the repair goes into a planned slot at no extra cost." |
| 2:50 | How it works tab | "Gemini on Vertex AI, the Agent Development Kit, Cloud Run. From an alert to an approved plan in under a minute." |

Before recording:
- Warm the Cloud Run instance (`MIN_INSTANCES=1`) and load the page once.
- Clear old proposals if needed. They live in the container and reset on restart.
- Run `make eval` the same day and quote the score only if it is current.
