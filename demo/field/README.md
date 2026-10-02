# Field input samples

Sample inputs for the multimodal demo. All of them are fictional and made for this project.
- `inbox/`: supplier messages as plain text, with From, Date (ISO, UTC), and Subject headers. Gemini reads them into
  delivery updates.
- `photos/`: inspection photos for alerts. The part of the file name before the first underscore is the asset id, so
  the app offers each photo on that asset's alerts.

## Inspection photos

The photos are generated images; nothing comes from a real plant. Save them as JPG or PNG, landscape, about 1024
pixels wide, with these exact names. Add the shared style to every prompt.

**Shared style:** Photorealistic maintenance inspection photo, taken with a phone on a factory workshop bench, neutral
white LED light, shallow depth of field. No text, no labels, no logos, no brand names, no people, no hands.

Gemini's reading of each photo, on 2026-10-02 with `gemini-3.8-flash`. Each was posted to
`POST /api/alerts/{id}/inspection` at the listed clock:

| File | Alert, clock | Truth in the data | Gemini's finding |
|---|---|---|---|
| `US1-L2-01_spindle_bearing_worn.jpg` | `AL-US1-L2-01-2026072502`, 2026-07-25 02:00 | Real (fails 26 Jul 10:00) | Confirmed, severe wear, 0.95 |
| `US1-L3-01_spindle_bearing_worn.jpg` | `AL-US1-L3-01-2026072017`, 2026-07-25 02:00 | Real (fails 26 Jul 07:40) | Confirmed, severe wear, 0.88 |
| `DE1-L2-04_gearbox_intact.jpg` | `AL-DE1-L2-04-2026072010`, 2026-07-25 02:00 | False (no failure) | Not confirmed, healthy, 0.88: teeth intact, dark oil; flush the oil before replacing the gear set |
| `DE1-L1-03_hydraulic_pump_wear.jpg` | `AL-DE1-L1-03-2026081901`, 2026-08-19 01:00 | Real (fails 25 Aug) | Confirmed, severe wear, 0.88 |
| `US1-L3-02_wrong_part_bearing.jpg` | `AL-US1-L3-02-2026071708`, 2026-07-17 09:00 | False (coolant pump) | Not confirmed, 0.95: the photo shows a bearing, not the coolant pump; inspect the impeller |

The gearbox photo is the false-alert case: the alert open next to the bearing conflict at 25 Jul 02:00 never led to a
failure, and Gemini says the gears look intact. The data has no false spindle-bearing alerts, so the bearing photo
on US1-L3-02 shows the other guard: Gemini notices when the wrong part was photographed. Photos are offered on every
alert of their asset, so the gearbox photo would also appear on the real DE1-L2-04 alert of 17 Sep.
