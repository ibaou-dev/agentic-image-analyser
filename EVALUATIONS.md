# Model Evaluation — screenshots/untitled.jpg
**Date:** 2026-03-31
**Judge:** Claude Sonnet 4.6 (claude-sonnet-4-6)
**Provider:** gemini-oauth (Gemini CLI OAuth / Code Assist endpoint)

---

## 1. Image — Ground Truth

The image (`screenshots/untitled.jpg`, 2544×1270, 240 KB) is a screenshot of a **Redmine** instance running the **Git Mirror plugin**, showing its administrative dashboard.

### Expected "gold standard" output

**Application:** Redmine · Git Mirror Dashboard plugin
**Footer:** "Powered by Redmine © 2006-2026 Jean-Philippe Lang"

**Summary bar (5 counters with badge colours):**
- 3 total (grey) · 3 ok (light green) · 0 failed (light pink) · 0 syncing (light blue) · 0 stale (grey)

**Table (3 rows × 7 columns):**

| Project | Repository | Remote URL | Auth Type | Poll (cron) | Last synced | Sync Status |
|---|---|---|---|---|---|---|
| makis | redmine_git_mirror | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 03/31/2026 07:35 PM | SUCCESS |
| makis | redmine-git-mirror-test | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 03/31/2026 07:30 PM | SUCCESS |
| zzz | agentic-dummy-project | https://github.com/ibaou-dev/agenti… | None (public repo) | `*/15 * * * *` | 03/31/2026 07:30 PM | SUCCESS |

> Row 1 last synced at 07:35 PM; rows 2–3 at 07:30 PM — a subtle differentiator.

**Global navigation bar (top, 5 links):** Home · My page · Projects · Administration · Help

**Project navigation tabs (7):** Projects · Activity · Issues · Spent time · Gantt · Calendar · News

**Administration sidebar (15 items, in order):**
Projects · Users · Groups · Roles and permissions · Trackers · Issue statuses · Workflow · Custom fields · Enumerations · Settings · LDAP authentication · CI/CD Registry · Plugins · Information · **Git Mirror** _(active/selected — bold, no icon)_

**Header right:** "Logged in as **admin**" · My account · Sign out · Search field · "Jump to a project…" dropdown

**Footer:** "Powered by Redmine © 2006-2026 Jean-Philippe Lang"

---

## 2. Evaluation Prompt (identical for all models)

```
Analyze this screenshot of a web application dashboard. Provide:

1. APPLICATION IDENTIFICATION: What application is this, what plugin or module is shown,
   and any version information visible.
2. PAGE SUMMARY: The page title and any summary statistics or counters shown.
3. TABLE DATA: Extract the complete table — all column headers and every row's values
   verbatim, including URLs as fully as visible.
4. NAVIGATION: All top-level navigation tabs/links visible.
5. SIDEBAR/PANEL: Every item listed in any sidebar or admin panel, in order.
6. VISUAL OBSERVATIONS: Layout, colour scheme, status indicators (icons, badges, colours),
   and any notable UI patterns.
7. COMPLETENESS CHECK: Anything else visible in the screenshot not covered above
   (e.g. header links, footer, logged-in user info).
```

---

## 3. Models Run

| Model | Provider | Duration | Status |
|---|---|---|---|
| `gemini-2.5-flash` | gemini-oauth | 14.82s | ✅ Success |
| `gemini-2.5-pro` | gemini-oauth | 19.43s | ✅ Success |
| `gemini-3-flash-preview` | gemini-oauth | 14.52s | ✅ Success |
| `gemini-3.1-pro-preview` | gemini-oauth | 23.37s | ✅ Success |

---

## 4. Full Model Responses

### Model 1 — gemini-2.5-flash · 14.82s
**Analysis file:** `./image-analyses/eval-flash/2026-03-31/untitled_6d5edc55.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer "© 2006-2026 Jean-Philippe Lang"

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅

**3. Table:**
| Project | Repository | Remote URL | Auth Type | Poll (cron) | Last synced | Sync |
|---|---|---|---|---|---|---|
| makis | redmine_git_mirror | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 07:35 PM | SUCCESS |
| makis | redmine-git-mirror-test | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 07:30 PM | SUCCESS |
| zzz | agentic-dummy-project | https://github.com/ibaou-dev/agenti… | None (public repo) | `*/15 * * * *` | 07:30 PM | SUCCESS |

**4. Navigation:**
- Global: Home · My page · Projects · Administration · Help ✅
- Project tabs: Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅

**5. Sidebar:** All 15 items in order ✅ _(no selection state noted)_

**6. Visual:** Three-column layout; dark blue header; green SUCCESS badge; "ok" badge light green; stats row acts as filter tabs; sidebar icons; URLs truncated; ">>" collapse icon.

**7. Completeness:** "Logged in as admin" · My account · Sign out · Search · "Jump to a project…" · footer ✅

---

### Model 2 — gemini-2.5-pro · 19.43s
**Analysis file:** `./image-analyses/2026-03-31/untitled_6d5edc55.md`

**1. App ID:** Redmine · Git Mirror Dashboard · "© 2006-2026" ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅

**3. Table:** All 3 rows × 7 columns, identical data ✅. Added note on SUCCESS green badge.

**4. Navigation:**
- Project tabs only: Projects · Activity · Issues · Spent time · Gantt · Calendar · News
- ⚠️ Global nav bar (Home, My page…) listed in Section 7 (Completeness), not Section 4

**5. Sidebar:** All 15 items ✅ _(no selection state noted)_

**6. Visual:** Two-column layout; zebra striping; ">>" collapse; global search bar.

**7. Completeness:** Recovered global nav links here · "Logged in as admin" · footer ✅

---

### Model 3 — gemini-3-flash-preview · 14.52s
**Analysis file:** `./image-analyses/eval-gemini3-flash/2026-03-31/untitled_6d5edc55.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer "© 2006-2026" ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅

**3. Table:** All 3 rows × 7 columns ✅

**4. Navigation:**
- "Top Header (Black Bar)": Home · My page · Projects · Administration · Help ✅
- "Primary Navigation (Blue Bar)": Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅

**5. Sidebar:** All 15 items ✅. Notable: **"Git Mirror (Selected item)"** — correctly identified the active page state.

**6. Visual:** Three-tier header; "lozenge/pill" badge terminology; green SUCCESS and "3 ok" badges; subtle table row hover styling; "Jump to a project…" dropdown; sidebar icons.

**7. Completeness:** "Logged in as admin" · My account · Sign out · Search · "Jump to a project…" · sidebar ">>" toggle · footer ✅

---

### Model 4 — gemini-3.1-pro-preview · 23.37s
**Analysis file:** `./image-analyses/eval-gemini31-pro/2026-03-31/untitled_6d5edc55.md`

**1. App ID:** Redmine · Git Mirror Dashboard (within Administration area) · footer "© 2006-2026" — added observation: "either a future-dated configuration or a modified date range" ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅ — **uniquely noted individual badge colours**: grey / light green / **light pink** / **light blue** / grey

**3. Table:** All 3 rows × 7 columns ✅. Added inline note: "SUCCESS values displayed inside light green visual badges".

**4. Navigation:**
- "Top-most global navigation bar (dark grey)": Home · My page · Projects · Administration · Help ✅
- "Secondary application navigation bar (blue gradient)": Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅

**5. Sidebar:** All 15 items ✅. **"Git Mirror — styled differently: bold text, no icon — indicating it is the currently active page"** — most precise observation of all four models.

**6. Visual:** Enterprise aesthetic palette; coloured pill badges for all 5 counters (pink for failed, blue for syncing); light green rectangular SUCCESS badge; URL truncation noted; ">>" collapse noted.

**7. Completeness:** "Logged in as admin" · My account · Sign out · Search field · "Jump to a project…" dropdown · footer ✅ — noted "Search:" label before the input.

---

## 5. Judge Scores (Claude Sonnet 4.6)

### Scoring Rubric

| Criterion | Weight | Full marks require |
|---|---|---|
| App identification | 10 | Names Redmine + Git Mirror plugin; footer noted |
| Summary stats | 15 | All 5 counters; bonus for badge colour differentiation |
| Table completeness | 30 | All 3 rows × 7 columns; no wrong values; timing diff noted |
| Navigation | 15 | Both nav levels: global bar (5 links) + project tabs (7) |
| Sidebar | 20 | All 15 items, correct order; bonus for noting active state |
| Format & clarity | 10 | Structured, scannable, descriptive labels, no hallucinations |

### Scores

| Criterion | Wt | gemini-2.5-flash | gemini-2.5-pro | gemini-3-flash-preview | gemini-3.1-pro-preview |
|---|---|---|---|---|---|
| App identification | 10 | 10 | 10 | 10 | 10 |
| Summary stats | 15 | 14 | 14 | 14 | **15** |
| Table completeness | 30 | 29 | 29 | 29 | **30** |
| Navigation | 15 | **15** | 9 | **15** | **15** |
| Sidebar | 20 | 19 | 19 | **20** | **20** |
| Format & clarity | 10 | 8 | 9 | 9 | **10** |
| **Total** | **100** | **95** | **90** | **97** | **100** |

### Justifications

**Summary stats (2.5 models 14/15, 3.1-pro 15/15):**
gemini-3.1-pro-preview uniquely reported distinct badge colours for all 5 counters (grey/green/pink/blue/grey), which matches the actual UI. The 2.5 models and gemini-3-flash-preview only noted that "ok" was green, missing the pink (failed) and blue (syncing) differentiation.

**Table (29/30 except 3.1-pro 30/30):**
All models extracted all 3 rows × 7 columns correctly, including the subtle 07:35 PM vs 07:30 PM sync time difference on row 1. gemini-3.1-pro-preview gets full marks for additionally annotating the SUCCESS badge styling inline. The -1 for the others reflects no annotation and URLs being legitimately truncated.

**Navigation (2.5-pro 9/15, rest 15/15):**
gemini-2.5-pro put the global nav links in Section 7 (Completeness) rather than Section 4 (Navigation), missing the structural intent of the prompt. All other three models correctly identified and separately listed both nav levels in Section 4.

**Sidebar (2.5 models 19/20, Gemini-3 models 20/20):**
Both Gemini-3 models noted that "Git Mirror" is the currently selected/active item (bold styling, no icon). Neither 2.5 model noted this. Full marks awarded to both Gemini-3 models for capturing the selection state.

**Format (2.5-flash 8, 2.5-pro 9, 3-flash-preview 9, 3.1-pro-preview 10):**
gemini-3.1-pro-preview used descriptive labels for both nav bars (named the colour of each bar), used code formatting for cron and URLs, used a numbered sidebar list, and added contextual annotations throughout. It is the clearest and most informative response with zero hallucinations.

---

## 6. Timing Comparison

| Model | Duration | vs. fastest |
|---|---|---|
| **gemini-3-flash-preview** | **14.52s** | 1.0× (fastest) |
| gemini-2.5-flash | 14.82s | 1.02× |
| gemini-2.5-pro | 19.43s | 1.34× |
| gemini-3.1-pro-preview | 23.37s | 1.61× |

---

## 7. Ranking & Qualitative Analysis

### Final Ranking

| Rank | Model | Score | Duration |
|---|---|---|---|
| 🥇 | **gemini-3.1-pro-preview** | **100/100** | 23.37s |
| 🥈 | **gemini-3-flash-preview** | **97/100** | 14.52s |
| 🥉 | gemini-2.5-flash | 95/100 | 14.82s |
| 4th | gemini-2.5-pro | 90/100 | 19.43s |

### Key Observations

**gemini-3.1-pro-preview is the only model to achieve a perfect score.** It surpassed the others on three independent axes: badge colour differentiation (pink for failed, blue for syncing — the others missed these), table annotation, and navigation label quality. Its description of "Git Mirror" as bold with no icon indicating the active page is the most precise visual observation across all four responses.

**gemini-3-flash-preview is the best bang-for-buck model.** It is the fastest (14.52s, marginally ahead of 2.5-flash), scores 97/100, correctly handles both navigation levels, and notices the sidebar active state. For production UI pipelines where latency matters, it dominates.

**The generation-3 models are a clear step up from 2.5 on this task.** Both Gemini 3 models noticed the active sidebar item (a detail requiring cross-element visual reasoning). The 3.1-pro model additionally noticed per-badge colour differences — which requires fine-grained colour discrimination across small UI elements.

**gemini-2.5-pro underperforms relative to its latency.** At 19.4s it is slower than gemini-3-flash-preview and scores 7 points lower. The structural error (global nav in wrong section) is a reasoning failure, not a perception failure — it saw the links but mis-categorised them.

**No hallucinations in any model.** All four responses are fully grounded in visible image content.

### Speed vs. Quality

```
Score
100 │                              ● gemini-3.1-pro-preview (23.4s)
 97 │          ● gemini-3-flash-preview (14.5s)
 95 │            ● gemini-2.5-flash (14.8s)
 90 │                        ● gemini-2.5-pro (19.4s)
    └──────────────────────────────────────────────
      14s       17s       20s       23s
```

The ideal operating point for quality/speed is **gemini-3-flash-preview**: near-perfect score at the lowest latency.

---

## 8. Reproduction Commands

```bash
# gemini-2.5-flash
uv run agentic-vision analyze --image /home/ibaou/workspace/agentic-image-analyser/screenshots/untitled.jpg \
  --model gemini-2.5-flash --provider gemini-oauth --output-dir ./image-analyses/eval-flash

# gemini-2.5-pro
uv run agentic-vision analyze --image /home/ibaou/workspace/agentic-image-analyser/screenshots/untitled.jpg \
  --model gemini-2.5-pro --provider gemini-oauth

# gemini-3-flash-preview
uv run agentic-vision analyze --image /home/ibaou/workspace/agentic-image-analyser/screenshots/untitled.jpg \
  --model gemini-3-flash-preview --provider gemini-oauth --output-dir ./image-analyses/eval-gemini3-flash

# gemini-3.1-pro-preview
uv run agentic-vision analyze --image /home/ibaou/workspace/agentic-image-analyser/screenshots/untitled.jpg \
  --model gemini-3.1-pro-preview --provider gemini-oauth --output-dir ./image-analyses/eval-gemini31-pro
```

---

---

# Round 2 — Compressed Image (`screenshots/untitled_small.jpg`)

**Date:** 2026-04-01
**Image:** 1272×635 · 34 KB (50% scale, JPEG quality 70 — compressed from 2544×1270 · 240 KB, **7× smaller**)

---

## R2.1 Models Run

| Model | Provider | Duration | Status |
|---|---|---|---|
| `gemini-2.5-flash` | gemini-oauth | 15.15s | ✅ Success |
| `gemini-2.5-pro` | gemini-oauth | 51.18s | ✅ Success |
| `gemini-3-flash-preview` | gemini-oauth | 13.70s | ✅ Success |
| `gemini-3.1-pro-preview` | gemini-oauth | 17.89s | ✅ Success |

---

## R2.2 Full Model Responses

### Model 1 — gemini-2.5-flash · 15.15s
**Analysis file:** `./image-analyses/eval2-flash/2026-04-01/untitled_small_c1c2f634.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer "© 2006-2026 Jean-Philippe Lang" ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅. Noted "ok" badge green background; other counters grey.

**3. Table:**
| Project | Repository | Remote URL | Auth Type | Poll (cron) | Last synced | Sync |
|---|---|---|---|---|---|---|
| makis | redmine_git_mirror | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 07:35 PM | SUCCESS |
| makis | redmine-git-mirror-test | https://github.com/ibaou-dev/redmin… | None (public repo) | `*/15 * * * *` | 07:30 PM | SUCCESS |
| zzz | agentic-dummy-project | https://github.com/ibaou-dev/agenti… | None (public repo) | `*/15 * * * *` | 07:30 PM | SUCCESS |

**4. Navigation (§4):**
- Top Header: Home · My page · Projects · Administration · Help ✅
- Main Tabs: Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅

**5. Sidebar:** All 15 items ✅. Describes icon for each item. "Git Mirror (with a Git branch icon)" — **no active state noted**.

**6. Visual:** Green background for "ok" badge; SUCCESS green badge; standard layout. Sidebar icons described per item.

**7. Completeness:** "Logged in as admin" · My account · Sign out · Search · "Jump to a project…" · footer ✅

---

### Model 2 — gemini-2.5-pro · 51.18s
**Analysis file:** `./image-analyses/eval2-pro/2026-04-01/untitled_small_c1c2f634.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅. Described as "grey badges" with no colour differentiation.

**3. Table:** All 3 rows × 7 columns ✅. Timing diff noted. URLs and cron in backtick formatting.

**4. Navigation (§4):** ⚠️ Lists only project tabs (Projects · Activity … News). Global nav (Home, My page…) placed in **§7 again** — same structural error as Round 1.

**5. Sidebar:** All 15 items ✅. No active state noted.

**6. Visual:** "Zebra-striped" table rows noted; collapsible sidebar `»` symbol; icons in sidebar.

**7. Completeness:** Global nav recovered here · "Logged in as admin" · footer ✅

---

### Model 3 — gemini-3-flash-preview · 13.70s
**Analysis file:** `./image-analyses/eval2-gemini3-flash/2026-04-01/untitled_small_c1c2f634.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅. "grey borders and black text" for counters; green SUCCESS badge.

**3. Table:** All 3 rows × 7 columns ✅. Timing diff noted.

**4. Navigation (§4):**
- "Top-Left Utilities": Home · My page · Projects · Administration · Help ✅
- "Primary Application Tabs": Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅
- Also listed Top-Right utilities and Search in §4 (captured in wrong section but still caught)

**5. Sidebar:** All 15 items in numbered list ✅. **`Git Mirror` — "currently active"** ✅ Active state preserved at lower resolution.

**6. Visual:** Dark blue header; lighter blue navigation bar; grey sidebar; cron-style syntax note; `>>` toggle icon.

**7. Completeness:** Footer ✅. Note: "Logged in as admin" captured in §4 (Top-Right Utilities) rather than §7 — minor structural issue.

---

### Model 4 — gemini-3.1-pro-preview · 17.89s
**Analysis file:** `./image-analyses/eval2-gemini31-pro/2026-04-01/untitled_small_c1c2f634.md`

**1. App ID:** Redmine · Git Mirror Dashboard · footer ✅

**2. Summary:** 3 total · 3 ok · 0 failed · 0 syncing · 0 stale ✅. "light grey pill-shaped badges" and "light green rectangular badge … SUCCESS". ⚠️ **No longer mentions individual badge colours** (pink/failed, blue/syncing) — this detail was unique to R1 and is gone.

**3. Table:** All 3 rows × 7 columns ✅. Timing diff noted. URLs and cron in backtick formatting.

**4. Navigation (§4):**
- "Top Header Bar (Dark Grey)": Home · My page · Projects · Administration · Help ✅
- "Secondary Header Bar (Blue)": Projects · Activity · Issues · Spent time · Gantt · Calendar · News ✅

**5. Sidebar:** All 15 items ✅. ⚠️ **"Git Mirror" listed as a plain item** — active state no longer noted. In R1 it described "bold text, no icon — indicating it is the currently active page". This observation is lost.

**6. Visual:** "Dark grey top bar, gradient blue main header." URL truncation and cron noted. No per-badge colour breakdown.

**7. Completeness:** "Logged in as admin" · My account · Sign out · Search · footer ✅

---

## R2.3 Judge Scores — Round 2

| Criterion | Wt | gemini-2.5-flash | gemini-2.5-pro | gemini-3-flash-preview | gemini-3.1-pro-preview |
|---|---|---|---|---|---|
| App identification | 10 | 10 | 10 | 10 | 10 |
| Summary stats | 15 | 14 | 14 | 14 | 14 |
| Table completeness | 30 | 29 | 29 | 29 | 29 |
| Navigation | 15 | **15** | 9 | **15** | **15** |
| Sidebar | 20 | 19 | 19 | **20** | 19 |
| Format & clarity | 10 | 8 | 9 | 9 | 9 |
| **Total** | **100** | **95** | **90** | **97** | **96** |

**Score changes vs Round 1:**
- gemini-2.5-flash: **95 → 95** (unchanged)
- gemini-2.5-pro: **90 → 90** (unchanged)
- gemini-3-flash-preview: **97 → 97** (unchanged)
- gemini-3.1-pro-preview: **100 → 96** ⬇️ (−4 pts)

---

## R2.4 Round 1 vs Round 2 Comparison

| Model | R1 Score | R1 Time | R2 Score | R2 Time | Score Δ | Time Δ |
|---|---|---|---|---|---|---|
| gemini-2.5-flash | 95 | 14.82s | 95 | 15.15s | — | +0.33s |
| gemini-2.5-pro | 90 | 19.43s | 90 | 51.18s | — | **+31.75s** ⚠️ |
| gemini-3-flash-preview | 97 | 14.52s | 97 | 13.70s | — | −0.82s |
| gemini-3.1-pro-preview | **100** | 23.37s | **96** | 17.89s | **−4** | −5.48s |

---

## R2.5 Observations on Image Compression

### Quality impact

**Compression revealed a fine-detail ceiling for gemini-3.1-pro-preview.** Its R1 perfect score rested on two observations that required pixel-level detail: (1) differentiating the individual badge background colours (grey / light green / **light pink** / **light blue** / grey), and (2) noticing that the Git Mirror sidebar item is bold with no icon, indicating the active page. Both of these details are below the threshold of visibility at 1272×635, JPEG quality 70. At the compressed resolution, gemini-3.1-pro-preview becomes indistinguishable from gemini-3-flash-preview in the sidebar criterion, and all four models tie on summary stats.

**The other three models are unaffected.** Their scores were already limited by structural reasoning (gemini-2.5-pro's nav categorisation error) or by not noticing the active state and badge colours — observations that were absent even from the full-resolution image. Compression cannot degrade what was never captured.

**gemini-3-flash-preview is now the outright winner** at the compressed resolution: tied on score with the compressed 3.1-pro-preview (97 vs 96), 4s faster, and still the only model that correctly identifies the active sidebar item.

### Speed impact

The flash-tier models (2.5-flash, 3-flash-preview) show effectively no speed change — the smaller upload size barely registers at these latencies. The 3.1-pro-preview was actually faster in R2 (18s vs 23s), which is consistent with normal server-side variance. The 2.5-pro spike to 51s is a clear outlier and almost certainly reflects server-side load rather than image size.

**Conclusion: for this class of UI screenshot task, image compression to 50% / JPEG 70 does not meaningfully affect response time for any model, but does reduce fine-detail extraction for the best model. The sweet spot — quality, speed, and compression robustness — is gemini-3-flash-preview.**
