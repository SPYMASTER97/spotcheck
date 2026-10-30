# Stitch prompts: Plan feature (Compare → Plan chat → Summary)

User flow approved 2026-10-27. Generate in the **same Stitch project** as the existing SpotCheck Results screen,
so the design system (`stitch_DESIGN.md`) carries over.

**How to use**
- Paste **Prompt 0** first, once.
- Then paste prompts 1–11 one at a time, in order.
- If a screen drifts from the style, re-paste Prompt 0's style lines in front of that prompt.

Example numbers are real outputs for **T03 Roundup Cafe** (Koramangala 5th Block · Cafe · ₹800 for two),
so the mock-ups match what the app will show:
- **Planner inputs:** 150 guests/day, 12 hours, 45 menu items, 50% delivery, new fit-out, no alcohol.
- **User-stated facts:** budget ₹1 Cr (₹100 lakh), 20 staff.

---

## Prompt 0: Shared style (paste first)

```
Mobile web app called "SpotCheck" (a restaurant concept checker for Bangalore). Phone frame 390 px wide.
Keep the existing SpotCheck design system from this project: Inter font, white cards with 16 px radius
and soft shadow on a #F8F8F8 background, primary red #E23744 for buttons, selected states and key
numbers, green #2E7D32 for good news, amber #F9A825 for caution, grey #6B6B6B for secondary text.
Rounded pill chips, generous 16 px padding, emoji as small icons. Fixed bottom tab bar with 4 equal
tabs: "🔍 Predictor", "⚖️ Compare", "💬 Plan", "ℹ️ About"; the active tab in red with a red top line.
Footer text where space allows: "Not affiliated with Zomato". Do NOT use the Zomato logo or wordmark,
no login, no profile picture, no user names. Wording is plain, friendly, short.
```

## Prompt 1: Compare, no card selected (button disabled)

```
Screen "Compare" (bottom tab "⚖️ Compare" active). Title "Compare your options", subtitle
"Pick the version you'll open, then plan it." A horizontally swipeable row of concept cards with
page dots below:
Card 1 "Your concept" (tag "Base"): "₹718 for two (typical market price)", range "₹582–₹854",
green badge "In line with market", "92% chance of 4.0+ · Strong".
Card 2 "No table booking" (tag "What-if B"): "₹628", "68% · Strong".
Card 3 "₹1,200 for two" (tag "What-if C"): "₹718", "95% · Strong".
Each card has a round empty selection circle in the top-right corner and a small "All settings ⌄"
fold-out at the bottom. Below the cards: "+ Add what-if card" outline button (max 3).
Sticky above the bottom tab bar: a full-width disabled grey button "Select a card to continue".
```

## Prompt 2: Compare, card selected (button enabled)

```
Same "Compare" screen, but Card 1 "Your concept" (Base) is selected: thick red #E23744
border, filled red circle with a white ✓ in the top-right, small red badge "Selected". The other
cards are slightly faded (80% opacity). The sticky button above the bottom tab bar is now active,
full-width red with white text "Plan this concept →" and a subtle shadow. A small hint under the
title: "Tap a card to choose it. You can change it later."
```

## Prompt 3: Plan tab, empty state (no concept chosen yet)

```
Screen "Plan" (bottom tab "💬 Plan" active) before any concept is chosen. Centered empty state:
a friendly illustration of a clipboard with a small shop front, headline "Plan your opening",
text "First choose the concept you'll open in Compare. Then ask me about space, staff, money,
food cost, revenue and break-even." Primary red button "Go to Compare". Below it, a muted line:
"Estimates come from synthetic planning data."
```

## Prompt 4: Plan chat, start

```
Screen "Plan my restaurant" (bottom tab "💬 Plan" active). Top bar: back arrow "‹ Compare", title
"Plan my restaurant". Under it a compact concept strip (white card, one line plus chips):
"☕ Cafe · 📍 Koramangala 5th Block · ₹800 for two" with small chips "Online ordering",
"Table booking", "3 cuisines", and a red text link "Change" on the right.
A slim info banner (light blue, ℹ️): "Estimates from synthetic planning data, not real Bangalore
figures" with a "Why?" link.
Chat area: one assistant bubble (light grey, left, small red SpotCheck chat icon):
"Hi! Ask me anything about opening this café: size, staff, money to open, food cost, revenue or
break-even. You can also tell me details, like 'we'll be open 12 hours'."
Bottom: a chat input bar above the tab bar, placeholder "Ask about size, staff, money, food cost…",
round red send button.
```

## Prompt 5: Plan chat, objective question

```
Same "Plan my restaurant" screen, conversation in progress.
User bubble (right, red #E23744, white text): "I have an investment of 1 Cr, and a staff of 20 members"
Assistant bubble (left, grey): "Noted: budget ₹100 lakh, staff you have 20 people." then in bold
"What is your objective?" and "Tap one below or type it."
Under the bubble, a wrap of 7 large tappable objective chips (white with red outline, emoji + label):
"📐 Size of the place", "👥 Staff needed", "💰 Money to open", "🥘 Food cost", "📈 Monthly revenue",
"⏱️ Break-even", "📋 Full plan".
Small grey "facts" pills under the user bubble: "Budget ₹100 lakh", "Staff 20".
Chat input placeholder changes to "Type your objective…".
```

## Prompt 6: Plan chat, follow-up question with quick replies

```
Same chat screen. User has tapped "💰 Money to open" (shown as a small right-aligned red chip
"Objective: 💰 Money to open").
Assistant bubble: "About how many guests do you expect on a typical day (dine-in + takeaway)?"
Under it, quick-reply chips: "80", "120", "150", "200", and a grey chip "Not sure (use 120)".
A small grey progress hint inside the bubble: "Question 1 of 2".
Below, show an assistant "typing" indicator bubble with three animated dots (for while the
message is being read).
```

## Prompt 7: Plan chat, answer card

```
Same chat screen. After the follow-ups (user answered "150" and "No, new fit-out"), the assistant
replies with an ANSWER CARD instead of plain text (white card, 16 px radius, red left accent bar):
Label "💰 Initial investment", big number "≈ ₹50.3 lakh" in red, a horizontal range bar from
"₹46.3 lakh" to "₹54.2 lakh" with a dot at ₹50.3 lakh.
Green comparison row with ✓: "Your budget of ₹100 lakh covers this, ₹49.7 lakh to spare".
"Based on" row of small editable chips: "Cafe", "Koramangala 5th Block", "₹800 for two",
"150 guests/day ✎", "New fit-out ✎".
Footer in small grey italics: "Estimate from synthetic planning data (Linear Regression)".
Under the card, "Ask next" chips: "👥 Staff needed", "📈 Monthly revenue", "⏱️ Break-even",
"📋 Full plan".
```

## Prompt 8: Plan chat, break-even card (+ not-reached variant)

```
Same chat screen. Assistant ANSWER CARD for break-even:
Label "⏱️ Break-even", big number "≈ 19 months".
A compact monthly table: "Sales ₹11.4 lakh", "− Food ₹3.0 lakh", "− Staff ₹2.6 lakh",
"− Rent ₹1.4 lakh", "− Other costs ₹1.7 lakh", divider, bold "= Profit ₹2.7 lakh / month";
then "Investment ₹50.3 lakh ÷ profit = ≈ 19 months".
A small timeline bar from "Open" to "Month 19 ✓ break-even" with a red marker.
Collapsed row "Assumptions ⌄" (₹20,000 per staff a month, rent ₹90/sq ft adjusted by area,
other costs 15% of sales). Footer: "Estimate from synthetic planning data".
Second variant card below it, amber accent: "⚠️ Break-even not reached: monthly costs exceed
sales under these assumptions" with hint "Try a higher price or fewer staff in Compare".
```

## Prompt 9: Plan chat, full plan answer

```
Same chat screen. User tapped "📋 Full plan". Assistant replies with one tall "Opening plan" card
with a 2-column grid of mini stat tiles, each with emoji, label, value and small range:
"📐 Floor area ≈ 1,240 sq ft (1,160–1,320)", "👥 Staff ≈ 13 people (12–14)",
"💰 Investment ≈ ₹50.3 lakh (46.3–54.2)", "🥘 Food cost ≈ 26.2% of sales (24.6–27.8)",
"📈 Revenue ≈ ₹11.4 lakh / month (10.4–12.3)", and a wide tile "⏱️ Break-even ≈ 19 months".
Comparison rows: "✓ Budget ₹100 lakh covers the investment" (green) and
"You have 20 staff: about 7 more than needed" (grey).
Buttons at the bottom of the card: red "View in Summary", outline "Change an input".
Footer: "Estimates from synthetic planning data".
```

## Prompt 10: Change concept confirmation

```
Same chat screen dimmed behind a bottom sheet (rounded top corners, drag handle).
Sheet title "Start a new plan?", text "You picked a different concept in Compare. Your current
plan answers will be cleared." Concept change shown as two small rows:
"From: Your concept (Base)" → "To: No table booking (What-if B)".
Buttons: red full-width "Start new plan", text button "Keep current plan".
```

## Prompt 11: Summary with "My opening plan"

```
Screen "Summary" (reached from the Results/Compare flow). Keep the existing summary layout:
title "Your SpotCheck summary", the concept card, the price and rating results, and the what-if
cards each listing what changed. Add a new section at the bottom with a red section header
"📋 My opening plan · Your concept (Base)":
a list of rows with emoji, label, value and range: Floor area ≈ 1,240 sq ft; Staff ≈ 13 people;
Investment ≈ ₹50.3 lakh; Food cost ≈ 26.2% of sales; Revenue ≈ ₹11.4 lakh/month;
Break-even ≈ 19 months. Row "Your facts: budget ₹100 lakh · 20 staff".
Small note: "Plan estimates come from synthetic planning data; price and rating come from
9,244 real Zomato Bangalore restaurants."
Primary red button "⬇ Download summary (HTML)" and secondary "Back to Plan".
Footer "Not affiliated with Zomato".
```

---

### After generating

Export the screens and design files (zip) from Stitch and send them here, as for the Results screen. I'll check
them against the flow and the real outputs before building.
