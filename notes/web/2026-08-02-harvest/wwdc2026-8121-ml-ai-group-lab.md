# WWDC26 Group Lab 8121 — "Coding Intelligence, Machine Learning & AI Group Lab"

**Harvested 2026-08-02** from `https://developer.apple.com/videos/play/wwdc2026/8121/`.

> ⚠️ **What this page is.** Apple publishes **no caption track** for Group Labs (the
> `pixelfolio/WWDC26-Transcripts` mirror confirms: "Nineteen Group Lab entries lack downloadable
> HLS subtitle manifests"). What Apple *does* publish is a **chaptered Q&A index with a written
> summary per answer**. Those summaries are Apple's own editorial prose, not a transcript.
> **Evidence tier: first-party, but paraphrased by Apple** — cite as
> "Apple, WWDC26 Group Lab 8121, published Q&A summary, ch. `<timestamp>`", never as a quotation
> from an engineer.

**Panel:** engineers from the ML and AI frameworks teams. Scope stated in ch. 1: Foundation
Models, Core ML, MLX, Core AI, agentic coding in Xcode, Evaluations, on-device vs PCC, and
bring-your-own LLM provider.

**Corpus status before today: 0 references to session 8121 anywhere in `guides/`, `notes/`,
`transcripts/`.** Group Labs are not listed in
`https://developer.apple.com/wwdc26/guides/machine-learning/`, which is why the earlier
transcript sweep (`notes/transcripts/missing-sessions.md`) never found it — the same blind spot
that hid Tech Talk 111432.

---

## ⭐ 1. The context-window question — this settles the documented value, not every device result

**Ch. 0:08:11 — "What is the on-device Foundation Models context window in iOS 27, and is input
plus output counted against one shared token budget?"**

Apple's published answer:

> The on-device context is **4096 tokens** and is a **shared budget** — if you feed in 4000
> tokens, the response can use the remaining ~96. The Private Cloud Compute model offers **32K**,
> also shared. For a larger context window use PCC, and for deeper reasoning use the
> reasoning-capable PCC model.

**Why this matters here.** Three places in the repo carry an unresolved 4096-vs-8192 dispute:

| Location | Current text | Effect of this finding |
|---|---|---|
| `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 7 | "The third-party 8192 claim now rests entirely on 27 *hardware*" | **The claim now also has to survive an explicit Apple statement that it is 4096 on iOS 27.** |
| `part-17/01-what-changed-checklist.md:180-183` | 🟡 "a community source reports device probing returning 8192 … Apple has not corroborated 8192 anywhere we can find" | **Apple has now documented 4096 for iOS 27.** Keep 8192 as an uncorroborated device-specific report rather than an equal platform value. |
| `part-17/01-what-changed-checklist.md:2571` | "Community source comment in a shipping third-party app. **Not corroborated by Apple**" | Retain that classification and add Apple's documented platform value. |

This also independently confirms the repo's own simulator measurement (4096 on the iOS 27.0
simulator runtime, `probes/`) and the 27.0 `swiftinterface`'s dynamic-`_contextSize`-with-4096-
fallback reading.

**What it does NOT settle:** whether a *specific* 27 device with more RAM reports something
larger at runtime. Apple's answer is a platform statement, not a per-device guarantee, and the
repo's standing advice — *read `contextSize` at runtime, never hardcode* — is unchanged and
still correct. Keep the device test in item 7; downgrade its priority.

**Also new:** the explicit statement that the budget is **shared across input and output**, with
a worked example ("feed in 4000 tokens, the response can use the remaining ~96"). Ch. 0:39:42
adds that **tool definitions and instructions consume the same budget** — "every tool definition
and instruction consumes the shared budget … only include the tools relevant to the task."

## ⭐ 2. The stack-layering answer — quotable framing for Part 1 and Part 17

**Ch. 0:04:13 — "Could you explain the roles of Core AI, Core ML, and MLX in simple terms?"**

Apple's published answer, condensed but with the load-bearing clauses intact:

- **Foundation Models** is the top of the stack. "Start there for language-model use cases, try
  the system language model, and use **Evaluations** to confirm it meets your need."
- **Core AI** is for "custom neural-network models such as diffusion or image segmentation, or
  models you train or download yourself." It "comes with **SLAs and guarantees** for building
  applications; going forward, **anything new involving neural networks should move to Core AI**."
- **Core ML** "remains but is now focused on **traditional ML like decision trees**."
- **MLX** "is the lowest level — powerful and flexible, and the place for **on-device training
  and distributed workloads across multiple machines** (for example running very large models
  across Macs, **not on the phone**)."
- Decision rule: **"Choose the highest level that meets your need."**

**Value to the guides.** Part 1's stack map and Part 17's `05-coreml-to-coreai.md` (15 🔴 GAPs)
both have to characterise the Core ML → Core AI relationship, and the corpus's evidence for
"Core ML is not deprecated, it is repositioned" has been inference from API surfaces. This is
Apple stating the repositioning in one sentence, plus a forward-looking directive
("anything new involving neural networks should move to Core AI") and the surviving Core ML
niche ("traditional ML like decision trees"). It is the cleanest citation available for that
section. Note also **"SLAs and guarantees"** attached to Core AI — an unusual, specific claim
worth quoting and worth *not* over-reading (no SLA document is named).

## 3. Background execution — a concrete, catchable failure mode

**Ch. 0:11:22 — "Can Foundation Models calls run inside `BGAppRefreshTask` or `BGProcessingTask`,
especially while the phone is locked, asleep, or long-backgrounded?"**

> Yes, calls can run in a background task, but if the OS is busy it may **rate-limit** you —
> **catch the rate-limited error** from the system language model and **retry later**. On macOS
> you're fine in the foreground, and the Private Cloud Compute model provides another path when
> on-device throttling is a concern.

**Action:** cross-check "the rate-limited error" against the captured `LanguageModelError` case
list (9 cases, `notes/web/apple-docs-fm-evals-speech.md` §5.1) and name the exact case in the
guides. This is a strong **`guides/SILENT-FAILURES.md`** candidate — background inference that
works in testing and gets throttled in the field is precisely the shape that index catalogues.
Relevant to Part 15 (shipping and operating) and Part 2.6 (availability/errors).

## 4. Guardrails — the refusal-vs-guardrail distinction, from Apple

**Ch. 0:51:39 — journal-app guardrail false positives.**

> When initializing the system language model's guardrails you can **opt into permissive content
> transformation**, so the model won't error out on emotionally intense first-person input like
> journal entries — though **it may still decline in natural language** to elaborate. For error
> handling, distinguish two separate things: a **refusal error is the model's own aligned
> response declining to answer (seen with guided generation)**, while a **guardrail error comes
> from a separate moderation model that inspects input *and* output**; you can catch each
> separately and fall back gracefully. These apply **only to Apple's models**. **Guardrails were
> substantially improved this year, so false positives should be much lower** — file feedback if
> you still hit them.

**Cross-check against the corpus, which has FOUR existing silent-failure rows on this exact
API.** `guides/SILENT-FAILURES.md` currently records that
`permissiveContentTransformations` **does not apply to `@Generable` / guided generation** —
"adopting guided output silently drops permissive mode" (rows at :436, :566, :572).

Apple's answer here is **consistent with, and explains, that finding**: the refusal path is
described as the one "seen with guided generation", i.e. a *different* mechanism from the
moderation model that `permissiveContentTransformations` relaxes. That is the missing *why*
behind the repo's four rows. **High-value addition to Part 2.6 §5.2 and Part 17.3 §10.3** — it
turns a documented contradiction into an explained mechanism.

Two further claims to fold in: the escape hatch is set **at guardrails initialization**; and the
model "**may still decline in natural language**" — a soft refusal that is *not* an error and
therefore invisible to `catch`. That is itself a silent-failure row the corpus does not have.

## 5. Model storage is not shared across apps

**Ch. 0:57:21 — "Can models used by different apps be shared across apps to save storage?"**

> **No** — sharing arbitrary models across apps isn't possible because it's genuinely complex:
> it becomes hard to manage **contention** when multiple apps want the resource simultaneously.
> That said, the system provides **model caching for the frameworks Apple ships**, so shared
> system models (like the Foundation Models system language model) don't each cost you separate
> storage.

Relevant to Part 15 `01-model-distribution-and-updates.md` and Part 7's `AIModelCache` material.
Note the stated *reason* is resource contention, not policy.

## 6. Vision vs Foundation Models — the choose-which rule

**Ch. 0:35:41.**

> Use **Vision** for well-understood, repeatable tasks like detecting a specific object, since
> it's optimized, efficient, and easy to test; step up to **Foundation Models** when the task
> **varies each time** or needs **semantic or natural-language understanding**. Foundation
> Models is also gaining Vision-powered tools this year, including a **barcode reader and an OCR
> tool**.

Confirms the `_Vision_FoundationModels` cross-import overlay story from the SDK capture, from the
product side. Good framing sentence for Part 2.4 / Part 16.

## 7. Smaller items worth a line each

- **Ch. 0:13:02 — the Apple Intelligence waitlist "applies only to Siri — it does not apply to
  the Private Cloud Compute language model or to the on-device things Siri does."** Directly
  relevant to Part 1's gating guide and Part 4's PCC guide: a developer's PCC access is *not*
  gated behind the Siri waitlist.
- **Ch. 0:13:02 — "the AFM core advanced (~20B) model … is included [in the beta] and is used for
  the voice features."** The corpus (`part-01/01-apple-ai-stack-2026-map.md:1809`) currently
  flags that "various articles assert 'about 3B' and '20B sparse with 1–4B active' *in the same
  piece*". This is a first-party ~20B figure attached to a named model ("AFM core advanced") and
  a named use ("the voice features") — it does not resolve the 3B/20B confusion but it anchors
  one side of it to Apple.
- **Ch. 0:14:24 — composing all three model sources in one agentic flow is supported**; once a
  third-party provider is involved "its own data-handling terms apply and **you're responsible
  for knowing and surfacing those boundaries**." Compliance framing for Part 4.2/4.3.
- **Ch. 0:20:05 — speech personalization for proper nouns: Apple's panel had no speech
  representative and gave no definitive answer**, only that a personalization component (e.g. a
  small model fine-tuned on a contact list) is conventional and can be built yourself. Useful
  *negative* evidence for the Speech guide's contextual-strings sections — Apple declined to
  confirm OS-level per-user personalization.
- **Ch. 0:23:02 — agentic coding: "Agents learn primarily through search and documentation
  rather than training … write down what it should know — project conventions, architecture
  notes, an `AGENTS.md`."** Out of scope for the guide series, noted for completeness.
- **Ch. 0:54:22 — evaluation philosophy: "the evaluation set is the living specification of what
  your feature is supposed to do"** and should come *before* the feature. A good epigraph for
  Part 6.

## 8. Method note for the next harvest

`8120` is the **SwiftUI** Group Lab, not a second ML lab — checked and discarded this session.
The ML/AI labs are numbered in the `80xx`/`81xx` band and are **absent from the ML track guide
page**, so they must be found from `https://developer.apple.com/videos/wwdc2026/` or from a
third-party session index. `ivan-magda/wwdc26-notes` lists 16 group labs:
`8001-8007, 8009-8011, 8013-8015, 8018, 8120-8121` — **none of the 8001-8018 band has been
checked against the AI topics yet.** That is the obvious next sweep.
