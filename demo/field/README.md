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

| File | Should Gemini confirm the alert? | Prompt |
|---|---|---|
| `US1-L2-01_spindle_bearing_worn.jpg` | Yes (the main demo alert) | Close-up of a CNC machine spindle angular-contact ball bearing, removed from the spindle and resting on a steel bench. The outer raceway shows clear spalling and pitting, brown and blue heat discolouration, and fine metal flakes and darkened grease around it. Some balls look dull and scuffed. |
| `US1-L3-01_spindle_bearing_worn.jpg` | Yes (the other alert in the conflict) | Close-up of a CNC spindle bearing set partly disassembled on a bench: one bearing with a visibly worn, pitted outer race and dark, contaminated grease, next to a clean new replacement bearing still in its plain packaging for comparison. |
| `US1-L3-02_spindle_bearing_healthy.jpg` | No (a false alert; the copilot should advise checking before an express buy) | Close-up of a CNC spindle angular-contact ball bearing on a clean bench, in good condition: smooth, bright raceways, even light film of clean grease, no pitting, no discolouration, no debris. |
| `DE1-L1-03_hydraulic_pump_wear.jpg` | Yes (the pump scenario) | Industrial hydraulic gear pump from a press, housing opened on a bench. The gears and wear plates show scoring marks, the inside is coated with dark, cloudy hydraulic oil, and there is a small puddle of oil with fine metallic sheen underneath. |
| `DE1-L2-04_gearbox_wear.jpg` | Yes (optional) | Open gearbox of a conveyor drive with the cover removed: gear teeth show uneven wear and small pits along the contact line, and the oil in the housing is dark with fine metal particles visible. |
