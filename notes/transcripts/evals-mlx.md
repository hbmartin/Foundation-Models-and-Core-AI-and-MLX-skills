# Transcript deep-read notes — theme "evals-mlx"

**Scope:** Four WWDC26 session transcripts read IN FULL, line-by-line:

| File | Session | Title (as spoken / as cross-referenced) | Presenters |
|---|---|---|---|
| `transcripts/wwdc2026-298.txt` (290 lines) | 298 | "Meet the Evaluations framework" | **Yada** and **Rob** |
| `transcripts/wwdc2026-299.txt` (199 lines) | 299 | Self-described as advanced Evaluations; **cross-referenced elsewhere as "Create robust evaluations for agentic apps"** | **Ada** and **Kyle**, "engineers on the Evaluations team" |
| `transcripts/wwdc2026-335.txt` (263 lines) | 335 | "Improve your prompts by hill climbing with Evaluations" | **Marcus**, "a manager on the Evaluations framework team" |
| `transcripts/wwdc2026-232.txt` (150 lines) | 232 | Agentic AI workflows on Mac with MLX | **Angelos**, "an engineer on the MLX team" |

**Method / epistemic status.** These are auto-transcribed spoken-word transcripts. They contain **no literal on-screen code** — every code block below is a **RECONSTRUCTION** from the narration and is labelled as such. Type names, method names, parameter names, and enum cases that are *spoken aloud* are treated as verified-from-transcript and quoted. Anything I inferred is marked `UNVERIFIED` or `RECONSTRUCTED`. Sentence-level quotes are given verbatim with line numbers.

> ⚠️ **Naming caveat that applies to the whole file:** the transcripts were machine-transcribed. Case and pluralization of Swift identifiers as spoken cannot be fully trusted (e.g. `ModelSample` vs `ModelSamples`, `SampleGenerator` vs `SyntheticGenerator` — both pairs actually appear). Discrepancies are flagged inline.

---

# PART 1 — Session 298: "Meet the Evaluations framework"

## 1.1 Why the framework exists (the pitch, verbatim)

The framing argument is the most quotable part of the session and is worth reproducing almost in full because it is the conceptual foundation for everything else.

> "Building app features with generative AI poses new testing challenges, because the same input can produce different outputs. These models break a contract that is fundamental to software testing." — 298:7–8

> "Consider traditional software, where a particular input always produces a particular output. You can easily verify this behavior with a unit test. You're guaranteed the same input will produce the same output on any device, including your customers'." — 298:9–11

> "With intelligent software, you cannot rely on functional consistency to verify behavior. Which means that unit tests are insufficient. Unverified behavior can erode customer confidence." — 298:12–14

> "Shipping a feature with unpredictable behavior, can have adverse consequences on your app's reputation." — 298:16

The three questions the framework is designed to answer (298:19, verbatim):

> "We need to know: how often does my app produce unexpected results? How often does the agent take an unexpected path to generate answers? And under what circumstances does the feature produce unsafe results?"

Note the middle question — "unexpected path" — is the explicit motivation for `TrajectoryExpectation` / `ToolCallEvaluator` in session 299.

## 1.2 What Evaluations is, in Apple's own words

> "The Evaluations framework is a flexible system of provided types and protocols." — 298:20

> "This video will focus on evaluating intelligent features powered by language models. **But you can evaluate any stochastic system, such as classifiers and linear regression models.**" — 298:21–22

That is an important scoping claim: the framework is **not** hardwired to Foundation Models. The `Evaluation` protocol's `subject(from:)` just calls *your* code. (Cross-check: a developer forum post asks "Are evaluations just for Text-text, or is there an efficient way to evaluate image-text, like for MobileClip2, or YOLOE?" — `forums/machine-learning-and-ai-topic-evaluations.txt:8–11` — unanswered in the captured RSS, so multimodal support remains an **open question**.)

Definition of an evaluation, verbatim:

> "Every evaluation measures how well an intelligent feature performs against our expectations." — 298:52

## 1.3 The running example app

**Book Tracker** — a personal library / book-cataloging app, used as the running example across sessions 298, 299, and 335.

- Feature under test: **`BookTaggingService`** — "It automatically tags books based on a review we've written in Book Tracker." (298:33–34)
- The service runs **on-device**: "Our BookTaggingService runs on-device because it needs to be fast and local for every user interaction." (298:207)
- Session 335 reiterates the reason: "readers tend to be in all kinds of places when cataloging books, so using the on-device model ensures they can generate tags no matter where they are." (335:216)

Sample books used across the sessions (useful for guide examples): *Pride & Prejudice*, *Dracula*, *The Secret Garden*, *Treasure Island*, *Romance of the Three Kingdoms*, a Sherlock Holmes/Watson one-liner, *Alice in Wonderland*, *Little Women*, *Frankenstein*, *The Ramakien*, *Moby Dick*, *The Picture of Dorian Gray*.

## 1.4 The zeroth step: `#Playground` as a manual evaluation

Before writing any evaluation code, Rob uses the **`#Playground` macro** (Xcode inline playgrounds) as a manual, human-judgement eval:

> "Let's add a #Playground macro to BookTaggingService.swift." — 298:36–37

Observations from that manual run, which become the feature's spec:
- "9 tags is more than I was expecting." (298:42)
- "I don't want the book's name as a tag, either." (298:43)
- "Multi-word tags are gonna be a problem in the UI, so we should avoid those as well." (298:44)
- For *Dracula*: "7 tags is within our expected amount... It identified literary genres, and some categories that would help me browse a larger library." (298:46–49)

Then the key rhetorical move:

> "Okay, we've just completed our first evaluation of the service. We created a list of expectations and used our human judgement to measure how the service performed." — 298:50–51
> "Unfortunately human judgement doesn't scale. But we've created a way to automate and scale evaluations. All you have to do is add `import Evaluations`, and implement the `Evaluation` protocol." — 298:53–55

### The five expectations for BookTaggingService (the informal spec)

Derived from 298:42–49 and 298:173/183:

1. Generate the **correct number of tags** (settled on **3–8**).
2. Do **not** emit the book's title as a tag.
3. **No multi-word tags** (they break the UI).
4. Tags should **identify a literary genre**.
5. Tags should be **informative, relevant to the book, and helpful for browsing your library**.

> "We can already measure three of our original five expectations." — 298:173 (i.e. #1, #3, #4 are quantitative; #5 needs a model judge)
> "We still expect our tags to be informative, relevant to the book and helpful for browsing your library." — 298:183

## 1.5 The five steps to build & run an evaluation (verbatim)

> "There are five steps to building and running an evaluation. You define what code you're measuring. Then, define what data you're sending the code. Next, define what measurements you're making and how. Then, summarize your measurements. And then, finally, create a test to run your evaluation." — 298:58–63

Mapped to API surface:

| Step | API |
|---|---|
| 1. What code am I measuring? | `subject(from:)` |
| 2. What data am I sending? | `dataset` property, built from `ModelSample`s |
| 3. What measurements, and how? | `Metric` + `Evaluator` (closure-based) |
| 4. Summarize | `aggregateMetrics(using:)` |
| 5. Run it | Swift Testing `@Test` + `.evaluates` trait |

Session 335 gives a slightly different (but compatible) decomposition into **four components**:

> "I need to write an evaluation, which is made up of four components. First is my dataset. Then the subject of my evaluation. Then, I need to define my evaluators. And finally, I need to aggregate my results." — 335:106–110

## 1.6 Verified API surface from 298

Spoken aloud, therefore treated as real identifiers:

- `import Evaluations`  (298:55)
- **`Evaluation`** — protocol you implement (298:55)
- **`subject(from:)`** — method; "we add the call to the BookTaggingService, and return it's output inside of the `subject(from:)` method. These generated tags are the subject of our evaluation." (298:64–65)
- **`dataset`** — property; "I'm going to update my `dataset` property to include all of the book reviews from our library" (298:157)
- **`ModelSample`** — "we'll use `ModelSample` to wrap the same reviews we tested in the #Playground earlier... Notice we define expected tags as well. These are the ideal tags we'd like to see from the service." (298:67–69)
- **`Metric`** — "Now, its time to define our measurements, using the `Metric` type. We add a Metric called `"TagCount"`" (298:70–71)
- **`Evaluator`** — "`Evaluator` takes a closure, that gets passed the output from the service, for a given sample." (298:73)
- **`aggregateMetrics(using:)`** — (298:78)
- **`.evaluates`** — a new Swift Testing **`@Test` trait** (298:87–89)
- **evaluation results bundle** with **`aggregateValue`** method (298:90–93)
- **`ModelJudgeEvaluator`** (298:252, 278)
- **`ScoreDimension`** (298:242, 244, 250)
- **`ModelJudgePrompt`** with fields **`instructions`**, **`evaluationTarget`**, and passing **`expectedTags`** as reference (298:257–260)
- **`SampleGenerator`** (298:153)
- Foundation Models types referenced: **`@Generable`**, **`@Guide`** (with a `count:` parameter that takes a range) (298:119–122)

### Semantics worth memorizing

- **Evaluators are per-sample.** "Evaluators run over a single sample at a time." (298:77)
- **Aggregation is cross-sample.** "But we can measure trends and look for patterns measured over all of our samples in the `aggregateMetrics(using:)` method." (298:78)
- **Metrics can be pass/fail OR scored.** "Then, we record a measurement using a scoring value, instead of a pass/fail value." (298:165)
- **Model judges are just evaluators.** "In the Evaluations framework, a model judge is just another `Evaluator`. It conforms to the same protocol as the quantitative evaluators and produces the same `Metric` type. **So you can mix them freely within a single evaluation.**" (298:222–224) ← This is architecturally the single most important sentence in the session.

## 1.7 RECONSTRUCTED code — the first evaluation

> **RECONSTRUCTION.** Assembled from narration at 298:56–96. Member names in backticks below are spoken in the transcript; the surrounding Swift syntax (property wrappers, closure signatures, `associatedtype` bindings) is my inference and is **not verified**.

```swift
import Evaluations

struct BookTaggingEvaluation: Evaluation {

    // STEP 1: what code am I measuring?
    // "we add the call to the BookTaggingService, and return it's output
    //  inside of the subject(from:) method" (298:64)
    func subject(from sample: ModelSample) async throws -> BookTags {
        try await BookTaggingService().generateTags(for: sample.prompt)
    }

    // STEP 2: what data am I sending?
    // "Then, we'll use ModelSample to wrap the same reviews we tested in the
    //  #Playground earlier: 'Pride & Prejudice' and 'Dracula'. Notice we define
    //  expected tags as well." (298:66-69)
    var dataset: [ModelSample] {
        [
            ModelSample(
                prompt: prideAndPrejudiceReview,
                expectedOutput: ["romance", "classic", "regency", "social-satire"]
            ),
            ModelSample(
                prompt: draculaReview,
                expectedOutput: ["gothic", "horror", "epistolary", "vampires"]
            ),
        ]
    }

    // STEP 3: what measurements, and how?
    // "We add a Metric called 'TagCount', which will track the number of
    //  generated tags returned by the service." (298:71)
    let tagCount = Metric("TagCount")

    var evaluators: some Evaluator {
        Evaluator(tagCount) { output, sample in
            // "We can check the number of generated tags by using the count of
            //  the tags property. If the length of the tags array is between 3
            //  and 8, we return a passing metric from our Evaluator. If not, we
            //  return a failing metric." (298:74-76)
            (3...8).contains(output.tags.count) ? .pass : .fail
        }
    }

    // STEP 4: summarize
    // "Let's calculate the average number of times the service generates the
    //  correct number of tags. Then we'll have a ratio for how often the service
    //  behaves correctly." (298:79-80)
    func aggregateMetrics(using aggregator: MetricAggregator) {
        aggregator.average(of: tagCount)
    }
}
```

## 1.8 RECONSTRUCTED code — running it with Swift Testing

> "Evaluations integrates with **Swift Testing**, so you can run your evaluations in your app's test targets." — 298:83

> **RECONSTRUCTION** from 298:83–96.

```swift
import Testing
import Evaluations

@Suite("Book Tagging")
struct BookTaggingTests {

    // "Here we instantiate our BookTaggingEvaluation inside of a Test Suite."
    let evaluation = BookTaggingEvaluation()

    // "We add some notes to our evaluation run, so we can keep track of the
    //  configuration we're evaluating. This will be helpful later, when we
    //  compare across different evaluation runs." (298:85-86)
    let notes = [
        "model": "on-device",
        "instructions": "v3",
        "guide": "count 3...8",
    ]

    // "Next, we add a test function, using the @Test macro, and a new @Test
    //  trait .evaluates. This trait takes our evaluation and a notes
    //  dictionary" (298:87-89)
    @Test(.evaluates(evaluation, notes: notes))
    func tagCountInRange(results: EvaluationResults) async throws {
        // "Inside our @Test, we can access an evaluation results bundle. This
        //  contains all of the metrics and aggregate metrics from our evaluation
        //  run. Let's grab all of our tagCount metrics from the results, and
        //  assert against its average value. We'll use the aggregateValue method
        //  on the results bundle." (298:90-93)
        let average = results.aggregateValue(for: "TagCount")
        #expect(average >= 0.8)   // "I expect the service to produce the correct
                                  //  number of tags 80% of the time." (298:95)
    }
}
```

### Why 80%? (verbatim, and this is good guide material)

> "Why 80%? If the service performance dips below 80%, I want to know and a failing test is great signal." — 298:96

And the framing of that threshold as an **optimization target**:

> "Remember back in our test definition? This is where we defined our **optimization target**. We're saying the feature behaves as expected, if the correct number of tags were generated, 80% of the time." — 298:115–116

## 1.9 The Xcode Evaluations report (UI workflow, session 298)

Step-by-step as narrated (298:97–111):

1. Run the test (`⌘U` / test navigator — not stated explicitly).
2. "Click on the **report navigator**, and then select **Evaluations** in the test report." (298:103)
3. "Here's the evaluation report for the test suite. Let's **double click the row** to find out more." (298:105)
4. Detail view shows the metric pass rate: "my TagCount metric only passed 50% of the time." (298:106)
5. "a quick look at the **full results table** shows me that my 'Pride & Prejudice' sample produced a failure. But my 'Dracula' sample produced the correct number of tags." (298:107–108)
6. "I can **select each row in the table** to see more details, using the **assistant editor** in Xcode." (298:109)
7. "The **detail panel shows the prompt, and each measurement** for the ModelSample. **At the bottom, you see the entire response from the model.**" (298:110–111)

Session 335 adds structure to the detail view:

> "This brings up the Evaluation detail view. **On the top are our aggregate metric charts. And below is our table of results.**" — 335:56–58

Session 299 adds:

> "In Xcode 27, we introduced a new Evaluations Report to visualize your results." — 299:97
> "Now, we can compare the two evaluations using the **Compare** button" — 299:101

Session 335 adds the comparison workflow:

> "From the evaluation report I can open the **comparison button** and open my baseline evaluation. Here, I can review the scores of the two prompts side by side." — 335:178–179

## 1.10 Hill climbing, introduced (298)

The first hill-climb iteration in the whole series, narrated fully:

- Hypothesis: "I have a hunch, so I look back at the `@Generable` type, `BookTags`, that the service is generating. We already have a `@Guide` macro giving the model additional instructions for the `tags` property. **I could specify a `count` property in that `@Guide`, which can take a range.** That should instruct the model to only generate between 3 and 8 tags." (298:119–122)
- "This is an interesting theory. Let's make that change. Then re-run the evaluation to see if I'm right. **We call this process hill-climbing.**" (298:123–126)

> **RECONSTRUCTION** of the `@Generable` type (298:119–122). The `count:` label on `@Guide` is spoken ("I could specify a count property in that @Guide, which can take a range"), the exact spelling is **UNVERIFIED**.

```swift
@Generable
struct BookTags {
    @Guide(description: "Tags describing the book", count: 3...8)
    var tags: [String]
}
```

### The critical footgun revealed by hill climbing

> "All right, I made the change and I re-ran the evaluation. My test passed, and my TagCount passes a 100% of the time. **But I notice a potentially strange behavior: after my change, the service always generates eight tags.** Hmmm." — 298:127–130

And after expanding the dataset: "my TagCount average is still 100%, and **the service generated eight tags for all of them**. Now we know there's a weird behavior in the service." (298:158–159)

**Takeaway for the guide:** a pass/fail range metric can be 100% green while the underlying distribution is degenerate. The fix is to add a *scored* metric alongside the pass/fail one:

> "First, I define a new Metric, **'TagTotal'**, that will record the number of generated tags. Then I build a simple Evaluator, which records the length of the generated tags array. Then, we record a measurement using a **scoring value, instead of a pass/fail value**. Using the 'TagTotal' and 'TagCount' metrics we evaluate **range compliance and the distribution** of generated tags." — 298:163–166

> **RECONSTRUCTION** of the two-metric pattern (298:160–171):

```swift
let tagCount = Metric("TagCount")   // pass/fail: is count in 3...8?
let tagTotal = Metric("TagTotal")   // score:     what IS the count?

var evaluators: some Evaluator {
    Evaluator(tagCount) { output, _ in
        (3...8).contains(output.tags.count) ? .pass : .fail
    }
    Evaluator(tagTotal) { output, _ in
        .score(Double(output.tags.count))     // records the value, not a verdict
    }
    // "We can follow a similar pattern for checking the number of words in tags.
    //  Here, we check each tag for a space, then returning a failing metric if it
    //  does." (298:167-168)
    Evaluator(singleWordTags) { output, _ in
        output.tags.contains(where: { $0.contains(" ") }) ? .fail : .pass
    }
    // "Identifying a literary genre is equally straightforward assuming you're
    //  looking for a known set of genres. We check the BookTaggingService for
    //  knownGenres. Then compare each of the generated tags for a match."
    //  (298:169-171)
    Evaluator(containsGenre) { output, _ in
        output.tags.contains(where: { BookTaggingService.knownGenres.contains($0) })
            ? .pass : .fail
    }
}
```

Result: "We track our three expectations using **five aggregate metrics**. Here, we can see the **distribution of tags**, along with **range compliance** and **containing genre tags**." (298:175–176)

### Evaluation-driven development (the term)

> "Using our hill-climbing methodology, we've iterated on our instructions for the service. Here's where we started at the beginning. After several updates to our evaluation and multiple runs through our loop. And we can track each change to our instructions, by an expectation we added to our evaluation to verify that change." — 298:177–180
> "**When you take our hill-climbing feedback loop, and center your development process around it, we call it evaluation-driven development.**" — 298:181

## 1.11 Dataset design guidance (298:131–155)

> "We started our evaluation with only two data samples. As we saw, that only gave us two measurements to extract trends." — 298:132–133
> "**Good evaluations have thousands of samples** to extract trends, but also to exercise your feature in many different ways." — 298:134

Dimensions of variety they explicitly call out (298:135–149):

- **Genre variety** — "We want the service to recognize different genres."
- **Length variety** — "We can't assume every user will give it a verbose review, so our reviews should be different lengths."
- **Category variety** — "You browse for fiction and non-fiction using different categories, your samples should represent that variety."
- **Form variety** — "novels, short stories, and essays."
- **Adversarial content** — "Let's makes it hard on the model too. **Sprinkle in personal opinions**, so we can measure how well the service ignores those in the reviews."
- **Style transfer via expected values** — "If you want to teach the feature how to write tags like you, start by **including more of your personal style in the expected values of the samples**." (298:142)

Concrete sample personas they wrote by hand (298:144–149):
- *The Secret Garden* written "as though we were an avid gardener."
- *Treasure Island* — "a personal review from a mother reading 'Treasure Island' to her son. Lots of personal opinions in this review."
- *Romance of the Three Kingdoms* — "This board game enthusiast needed multiple paragraphs."
- Sherlock/Watson — "this casual reader described a famous British detective's sidekick in a **single sentence**."

Then the pivot to synthetic data:

> "And while it's fun to come up with these examples, **human data creation doesn't scale, either**." — 298:150
> "Consider these **sentence completion pairs**, where the output of the feature is compared directly to the expected answer. **You need thousands of examples** for this evaluation to be effective." — 298:151–152
> "Fortunately, we include a **`SampleGenerator`** as part of the Evaluations framework. **You can call it directly on an array of `ModelSample`s** and it will synthetically generate more samples **using a model of your choice**." — 298:153–154

## 1.12 Model Judges (298:185–270) — the deep dive

### Motivating failure

Tags generated for an *Alice in Wonderland* review: "Six tags, single word or hyphenated, with tags identifying genre. **Every quantitative metric we built with Rob passed.**" (298:191–192)

> "But look closer. **'Overrated' and 'pretentious' doesn't describe the book — they describe how the reader felt about it.** And **'whodunit' isn't even the right genre**. The model picked it up from 'riddles he never answers.' **It latched onto the language of the review without understanding the book.** Our metrics are passing, but they're not giving us the right signals back." — 298:193–198

### Definition

> "**A Model Judge is a language model used to score your feature's output. It gives you a subjective rating — the kind of judgment call a person would make — but applied consistently across your entire dataset.**" — 298:203–204

### The capability rule (IMPORTANT)

> "You can use a second model as a judge to evaluate your feature. **Your judge should be at least as capable as the model you're evaluating.** In our case, we can use a more capable model from **Private Cloud Compute**." — 298:208–210

### Anatomy of a model judge (four components, 298:211–216)

1. **The instruction** — "tells the model it will be given book reviews, and how it should evaluate it."
2. **The feature input** — "the prompt given to the feature being judged, in our case, its the book review."
3. **The feature output** — "the tags our service generated."
4. **The scoring guide** — "tells the model how to evaluate and score the feature."

> "**The Evaluations framework handles most of this for you, so you can focus on the scoring guide.**" — 298:216

### The 1–4 scale, and why (verbatim — strong guide material)

> "We've defined a 'TagQuality' metric on a **1 to 4 scale**, with each level describing what that score means. **An even number of options prevents the judge from defaulting to a neutral middle score. Four levels provides just enough distinction without diluting the meaning of each rating.**" — 298:218–220

> "And finally, we've specified **Private Cloud Compute as our judge model**, giving us a more capable evaluator than the on-device model we're evaluating." — 298:221

> **RECONSTRUCTION** of the "simple model judge" (298:217–221):

```swift
let tagQuality = ModelJudgeEvaluator(
    Metric("TagQuality"),
    model: PrivateCloudComputeLanguageModel(),   // "specified Private Cloud Compute as our judge model"
    scale: [
        1: "Tags are unrelated to the book or actively misleading.",
        2: "Some tags relate to the book but most are not useful for browsing.",
        3: "Most tags describe the book and are usable for browsing.",
        4: "All tags describe the book and are useful for browsing a library.",
    ]
)
```
*(The `scale:` shape is inferred; only "1 to 4 scale, with each level describing what that score means" is spoken.)*

### Rationales are the payload

> "**With model judges, rationales are essential. They give you a window into why the judge scored what it scored.**" — 298:230–231

Example: "The model judge gave this a quality score of 3. If we look at the rationale, we can identify that the model flagged 'whodunit' and 'detective-fiction' as not relevant to the book. But, we also expected it to flag all of these other tags that either reflect the reader's opinion or are not helpful for browsing." (298:227–229)

### The "the judge is right, your rubric is wrong" insight (the best paragraph in the session)

> "And here's the thing: **by the scale we wrote, the judge is actually right. Every tag connects to something that the user wrote. The judge is faithfully following the scoring guide we provided. We meant something specific by relevant and useful for browsing, and the judge interpreted those words differently than we did.**" — 298:232–235

> "By asking the model to provide judgement for my feature, in my place, I expected it to provide a similar score to how I would have scored these tags. **When there is a mismatch between the model judge and us, we can refine the model judge until it can stand in for our own judgement.**" — 298:236–237

### Diagnosis: the judge was asking two questions at once

> "Looking back, the problem with our first model judge was that **it was too broad. It was asking two different questions.**" — 298:238–239
> "**When you find yourself disagreeing with a score, you should try and see if you can split the questions.** In our case, relevance and usefulness are actually two different metrics." — 298:240–241

### `ScoreDimension`

> "Lets take a look at defining 'Relevance' as a `ScoreDimension`." — 298:242
> "When we say the tags are relevant we mean that **each tag describes a quality, theme, or tone of the book itself rather than small details or the reader's personal reactions.** And we can write that as the **description** for our `ScoreDimension`." — 298:243–244

How to author each level of the scale (298:245–249):

> "To score these tags, you'd walk through each one. Identify which tags are bad and which are good, based on whether or not they meaningfully describe the book. You'd repeat this for every tag. In this case, all of the tags are good, which earns a score of 4 on our 1 to 4 scale. **You would repeat the same process to define each scale in the scoring guide.**"

> "And that's our 'Relevance' metric with the **metric name, description, and scale** that the model judge can use." — 298:250

⇒ **`ScoreDimension` has (at least) three parts: a metric name, a description, and a scale.**

> **RECONSTRUCTION** of two score dimensions + attaching to the judge (298:242–252):

```swift
let relevance = ScoreDimension(
    name: "Relevance",
    description: """
        Each tag describes a quality, theme, or tone of the book itself rather \
        than small details or the reader's personal reactions.
        """,
    scale: [
        1: "No tag describes the book; all are details or reader reactions.",
        2: "Few tags describe the book.",
        3: "Most tags describe the book; a minority are reactions or trivia.",
        4: "Every tag meaningfully describes the book.",
    ]
)

let usefulness = ScoreDimension(
    name: "Usefulness",
    description: "Each tag works as a search term for browsing a personal library.",
    scale: [ /* 1...4, authored the same way */ ]
)

// "Now, I can add both dimensions to the ModelJudgeEvaluator." (298:252)
let judge = ModelJudgeEvaluator(
    dimensions: [relevance, usefulness],
    prompt: bookTagJudgePrompt,
    model: PrivateCloudComputeLanguageModel()
)
```

### `ModelJudgePrompt` — giving the judge app context

> "But dimensions alone aren't enough. **They tell the judge what to measure, but not how to think about your app.** Without that context, a judge evaluating tags for Book Tracker might treat a reader's criticism as a valid book descriptor. **It has no way to know that Book Tracker is a personal library, not a review platform.** And that's where the `ModelJudgePrompt` comes in." — 298:253–257

> "This is an example of a `ModelJudgePrompt`. We can tell the judge its evaluating tags for a personal library app in the **instructions**. Format the response in the **`evaluationTarget`**, and pass the **`expectedTags`** as reference for the model to compare against. For more details on `ModelJudgePrompt` please see our documentation." — 298:258–261

> **RECONSTRUCTION** (298:258–260). Field names `instructions`, `evaluationTarget` are spoken; `expectedTags` is the app-specific value being passed as reference.

```swift
let bookTagJudgePrompt = ModelJudgePrompt(
    instructions: """
        You are evaluating tags generated for Book Tracker, a personal library app.
        Book Tracker is not a review platform: tags are used to browse and search a
        reader's own collection, not to express opinions about a book's quality.
        """,
    evaluationTarget: { sample, output in
        """
        Review: \(sample.prompt)
        Generated tags: \(output.tags.joined(separator: ", "))
        Reference tags: \(sample.expectedTags.joined(separator: ", "))
        """
    }
)
```

### Result after splitting the dimensions

> "In place of Quality we now have a relevance and usefulness score... **Notice how the two rationales separate the diagnosis. Relevance tells us what kind of tag is wrong. And Usefulness tells us how the wrong tags fail at browsing.**" — 298:263–267

> "With these results, I now have a clear path forward. I can update my BookTaggingService instructions, run the evaluation again, and watch the scores change. **That's the feedback loop Rob walked us through, now powered by qualitative metrics.**" — 298:268–270

## 1.13 Best practices, verbatim (298:271–285)

This block is a near-perfect checklist; quoting in full:

> "**Start small. A focused dataset of 20 to 30 samples is a great place to get started.** Spec out your app by thinking about how you want the model to behave." — 298:272–274

> "**Use heuristics to measure quantifiable traits.** These rule-of-thumb metrics are a great way to start understanding your feature. **The rule-of-thumb is: if you can measure it in code, then it's quantitative. And if you can only describe it in words, then you need a qualitative metric, using a `ModelJudgeEvaluator`.**" — 298:275–278

> "**Start simple with your model judge. Define your scoring dimension, run it, and read the rationales. You'll learn more from a single run than from hours of careful planning.**" — 298:279–281

> "**Use rationales to drive your next change. If the scores are all the same, your question is too broad. If you can't isolate the problem, split the dimensions. And if the judge doesn't understand your app, add context.**" — 298:282–285

⚠️ Note the apparent tension: 298:134 says "Good evaluations have thousands of samples" while 298:273 says "A focused dataset of 20 to 30 samples is a great place to get started." Reconciliation (implied): start at 20–30 by hand, scale to hundreds/thousands via `SampleGenerator`.

## 1.14 Session 298 pointers

> "check out our other videos featuring the Evaluations framework: **'Improve your prompts by hill climbing with Evaluations'**, and **'Create robust evaluations for agentic apps'**." — 298:289

Also referenced: "our documentation" and "our sample code" (298:287–288). The sample code is the **Book Tracker** app (335:259: "you can review the Book Tracker app I've been using as well as the evaluations for aligning the model judge").

---

# PART 2 — Session 299: synthetic data + agentic / tool-call evaluations

## 2.1 Platform & version gates (VERIFIED, verbatim)

> "This framework is **new in Xcode 27** and supports **macOS, iOS, watchOS and visionOS**." — 299:2

⚠️ **tvOS is conspicuously absent.** Do not claim tvOS support. (Cross-check: FM framework's watchOS support is new this year and is enabled by PCC — see `transcripts/wwdc2026-241.txt:40`: "Private Cloud Compute makes it possible for us to bring the Foundation Models framework to watchOS.")

> "The Evaluations framework introduces a way to **assess intelligence-powered features in Swift apps, track improvements over time, and ensure quality in production.**" — 299:1

⚠️ Forum question, currently unanswered: "Is Evaluations only for swift or does it support other languages like python and others?" (`forums/machine-learning-and-ai-topic-evaluations.txt:16–19`). Session 334 says Python users should use the **Python SDK** + pandas + their own judge functions instead (see §5.3), which strongly implies **Evaluations is Swift-only**.

## 2.2 The data model of the sample app

> "We have a class named **`Book`** that includes the **title, author, review, tags, and rating**. We define other variables used to support the cover design. We also define **`sampleBooks`** which is an array of **13 `Book` samples**, Like this one here about Pride and Prejudice." — 299:19–21

> "These 13 samples might feel like a reasonable starting point, but **this small dataset only give us a narrow window into how our feature performs. Our evaluation results could look great and still be completely misleading.**" — 299:22–23

The variety argument (299:24–28): "There are countless books. Hundreds of genres. And a wide variety of ways a user might review what they just read. We're also talking about the real world where **summaries can be vague or incomplete.** Thirteen samples can't capture all of that."

## 2.3 Synthetic data generation — the *simple* path: `makeSamples`

> "The Evaluations framework exposes APIs that let you **define sample generation entirely in code**, so you can build your own generation pipeline, **run it from the command line**, or plug it directly into your existing workflows. **It supports text-based data and leverages the generable macro to generate structured synthetic data.**" — 299:15–16

> "**The `makeSamples` API requires three components: a prompt, a dataset, and a target count**, which is the number of samples you'd like to synthetically generate **including the dataset you provide**." — 299:31

### The `targetCount` gotcha (say this loudly in the guide)

> "And for the target count, I've set it to one hundred samples to start! **Remember, the targetCount is the size of the full resulting dataset, including the samples we started with, so the model will actually generate 87 new ones.**" — 299:36

13 initial + 87 generated = 100 total.

### `ModelSamples`

> "Here we leverage the new **`ModelSamples` API** which includes **the book's review as the prompt** and **the book's tags as the expected output**." — 299:35

⚠️ **Naming discrepancy:** 298 consistently says `ModelSample` (singular). 299:35 says `ModelSamples`. Possibly (a) a transcription artifact, (b) a plural helper/collection type, or (c) a static factory. Additionally, `transcripts/wwdc2026-246.txt:115` says "We'll start by defining a dataset that adopts the **`ModelSampleProtocol`**" — so there is very likely a **protocol** (`ModelSampleProtocol`) plus a concrete `ModelSample` type, and your own type (e.g. `TrailRequest`, `Book`) can conform. **UNVERIFIED but strongly suggested.**

> **RECONSTRUCTION** of the simple path (299:31–41):

```swift
let prompt = """
    Suggest more diverse book review samples. Cover a wide range of genres, \
    moods, and tones. Vary the length of each review. Reviews must be at least \
    100 characters. Generate between 3 and 8 lowercase tags per review.
    """

var expandedDataset = sampleBooks.map {
    ModelSample(prompt: $0.review, expectedOutput: $0.tags)
}

// "I can use the makeSamples method, which returns an async stream of newly
//  generated samples. As I iterate over it, each new sample gets appended to a
//  variable called expandedDataset that I've initialized with the starting
//  dataset." (299:40-41)
for try await sample in makeSamples(
    prompt: prompt,
    dataset: expandedDataset,
    targetCount: 100
) {
    expandedDataset.append(sample)
}
```

### Default model

> "**By default, the framework uses the on device model for generation.** The on-device model is a great option in most cases, but you might want to bring your own model, or customize the instructions the model operates under." — 299:42–43

### How much data is enough? (verbatim — excellent guide material)

> "Now you might be wondering how much data is enough? And the answer is, **it depends.**" — 299:37
> "Synthetic data generation is often an **iterative process of defining an initial dataset, generating synthetic data, validating the samples, then, analyzing whether or not the data is representative enough and continuing this cycle until you are confident!**" — 299:38
> "**What matters far more than quantity is coverage! So instead of asking how many samples do I need? Ask yourself, have I covered the meaningful variety of ways this feature will actually be used?**" — 299:40

## 2.4 `SampleGenerator` — the *full-control* path

> "For more complex configurations beyond the prompt, dataset, and target count, the framework provides the **`SampleGenerator`** Which gives you **full control over the generation process**." — 299:45

### Configuration surface (all spoken)

| Config | Type / values | Notes |
|---|---|---|
| `sessionProvider` | closure returning a `LanguageModelSession` | "This is where you control **which model drives generation and what system-level instructions frame the task**." (299:46–47) |
| `samplingStrategy` | **random** (default) \| **sliding window** | controls in-context example selection (299:59–67) |
| `validator` | closure, per-sample accept/reject | (299:72–73) |
| `dataset` / initial samples | `[ModelSample]` | (299:186) |
| `targetCount` | `Int` | same inclusive semantics as `makeSamples` (299:186) |
| validation metrics | `Metric`s | "Here I've already defined these 3 validation metrics in the SampleGenerator" (299:90) |

### `sessionProvider` — session lifecycle and the context-window footgun

> "The framework **handles batch size automatically** which is the number of samples processed during generation." — 299:52
> "**The generator calls your `sessionProvider` once at the start of a run and then reuses that session across batches** which helps the model maintain context as generation progresses." — 299:53
> "But a session has a limit for how large it can grow. The one exception is if you're making a lot of requests, giving it a large prompt, or getting large outputs, **You can exhaust the session's context window mid-run which will throw an error. In that case, the generator calls `sessionProvider` again to get a fresh one to continue generation but this won't contain context from the previous session. So make sure your instructions in your `sessionProvider` is self-contained and doesn't assume it'll only be called once.**" — 299:54–57

⇒ **FOOTGUN #1:** `sessionProvider` must be idempotent & self-contained. Do not close over run-scoped mutable state that assumes single invocation.

> "To learn more ways to mitigate against context size limits, watch the video **'Build agentic app experiences with Foundation Models'**." — 299:58

Model choice for generation:

> "For our synthetic data generation, I'll use the **`PrivateCloudComputeLanguageModel`** since **the context size is larger** and then I'll add custom instructions to focus generation on specific books, genres and moods." — 299:48

(Cross-check: `PrivateCloudComputeLanguageModel` is confirmed in `transcripts/wwdc2026-241.txt:29,46`, `wwdc2026-242.txt:20,45`, and `wwdc2026-319.txt:60` — the latter notes `contextSize` is a readable property on both `SystemLanguageModel` and `PrivateCloudComputeLanguageModel`. Session 319 also notes PCC requires an **entitlement** — `241:43`.)

### `samplingStrategy` — random vs sliding window

> "you can also use the `SampleGenerator` to customize **`samplingStrategy`**, which **controls how the generator selects examples from your initial dataset to show the model as in-context examples**." — 299:59

**Random sampling:**
> "This strategy **selects a random subset of your initial samples as examples to show the model making sure there are no duplicates**. This keeps the output varied without requiring us to think carefully about the order of our initial samples." — 299:61–62

**Sliding window:**
> "This strategy **steps through your initial samples sequentially, skipping duplicates as it goes. If your dataset has meaningful order, consider using this sliding window strategy.**" — 299:64–65

**Default:**
> "For our generator, we'll use the random strategy because our initial samples are not meaningfully ordered. **And since it's the default strategy we don't need to explicitly define it here.**" — 299:66–67

⇒ `samplingStrategy` defaults to **random**.

### `.run()`

> "we can call the `.run` function, which **returns a stream of newly synthesized samples**. As we iterate through each one, it gets added to our expandedDataset defined earlier." — 299:68–70

> **RECONSTRUCTION** of the full-control path (299:45–70, 90–94):

```swift
let generator = SampleGenerator(
    prompt: prompt,
    dataset: expandedDataset,
    targetCount: 100,

    // "The sessionProvider is a closure that returns a LanguageModelSession."
    sessionProvider: {
        LanguageModelSession(
            model: PrivateCloudComputeLanguageModel(),
            instructions: """
                Generate diverse book review samples for a personal library app.
                Focus on specific books, genres and moods.
                Rules:
                  1. Each review must be at least 100 characters long.
                  2. Cover a wide range of genres, moods, and tones.
                  3. Reviews must vary in length.
                  4. Generate between 3 and 8 book tags per review.
                  5. Tags must be lowercase.
                """
        )
    },

    // "since it's the default strategy we don't need to explicitly define it"
    samplingStrategy: .random,     // alternative: .slidingWindow

    // "The validator lets you define your own logic to accept or reject every
    //  generated sample." (299:73)
    validator: { sample in
        sample.review.count >= 100
            && (3...8).contains(sample.tags.count)
            && sample.tags.allSatisfy { $0 == $0.lowercased() }
    }
)

for try await sample in generator.run() {
    expandedDataset.append(sample)
}

// "valid samples are collected in the samples property... Any sample that fails
//  these validators gets set aside automatically as invalidSamples. Both are
//  updated in real time throughout the run" (299:91-93)
let good = generator.samples
let bad  = generator.invalidSamples
```

## 2.5 The `validator` closure — semantics and limits

> "That's where the **`validator` closure** comes in hand. The validator lets you **define your own logic to accept or reject every generated sample**. We've already defined a set of rules in the instructions in the session provider earlier, **but that doesn't guarantee the output will actually follow the rules.**" — 299:72–74

⇒ **FOOTGUN #2:** rules in the prompt are *aspirational*; the validator is the enforcement layer.

### The five rules and which are machine-checkable

Rules stated in the session-provider instructions (299:76–79):
1. "the review must be **at least 100 characters** long"
2. "Each review should also **cover a wide range of genres, moods, and tones**"
3. "the review needs to **vary in length**"
4. "The model should also generate **between 3 and 8 book tags**"
5. "**tags must be lowercase**"

> "**the validation closure validates per sample generation in isolation and doesn't have context to the other samples.**" — 299:81
> "Reviewing these rules, I can tell that **the diversity of reviews will require more judgement beyond a simple validation check** and **the length of reviews requires assessing across all samples**." — 299:82

⇒ **FOOTGUN #3:** the validator sees ONE sample. Rules #2 (diversity) and #3 (length variation) are *corpus-level* properties and **cannot** be validated there. Rules #1, #4, #5 can.

> "as generation progresses, **valid samples are collected in the `samples` property on the SyntheticGenerator**. **Any sample that fails these validators gets set aside automatically as `invalidSamples`.** **Both are updated in real time throughout the run, so you can access them at any point.** Either during iteration to check progress or after the loop completes. You can then use these results directly in your app or **save the dataset locally**." — 299:91–95

⚠️ **Naming discrepancy:** 299:91 says "**SyntheticGenerator**" while 299:45 and 299:186 say "**SampleGenerator**", and 298:153 says "**SampleGenerator**". Most likely one transcription slip; **`SampleGenerator` is the more probable real name** (3 of 4 mentions, and it's the name used in 298 and in `wwdc2026-335.txt:240` — "the **Sample Generator API**"). Mark as **needs doc confirmation**.

## 2.6 Comparing 13-sample vs 100-sample runs (the scale reality check)

> "This is the **BookTaggingEvaluation** with the 13 initial samples. As you can see we got **pretty high scores for tag quality evaluating both relevance and usefulness**." — 299:98–99
> "I've went ahead and ran the evaluation with our new dataset of 100 samples. Now, we can compare the two evaluations using the **Compare** button and **we're expecting the scores to drop!** And we were correct! The quality scores have dropped. **Our tag generation feature looked like it was performing well earlier because we weren't testing it with a comprehensive dataset.**" — 299:100–102

### Four hypotheses when scores drop on a bigger dataset (299:103–110)

> "By running our evaluation on a larger dataset, a drop in scores could signal many different things. Consider what this signal could suggest."
1. "Score changes could be due to **problems with our prompt or instructions**. You could refine one or both to better capture your needs."
2. "You could also consider **gaps in your intelligence feature**."
3. "Or you may want to **adjust your evaluation to understand what you are actually evaluating on**."
4. "your **dataset may still not be representative enough** and need to capture more variation. You can continue to increase the dataset or include more edge cases using the synthetic data APIs."

> "**These are the core ways to further improve your results.**" — 299:111

## 2.7 Tool / agentic evaluations (Kyle, 299:114–195)

### Why the final answer isn't enough

> "So far, we've been evaluating **what the model generates**... But intelligence features often take **many behind-the-scenes steps** to create their output." — 299:115–116
> "**Here's the thing. A model might give you a reasonable-sounding answer without ever calling the right tool. The final output can look correct while the path to get there isn't right.**" — 299:122–124

### What tools are (299:118–121)

> "Tools **add structure to model workflows** when they're completing a task for people using your app. You use them to **operate on real data** that people use daily. They can operate using **any custom business logic** you define. They can call **functionality a user can invoke directly** or **entirely new logic for your intelligence feature**, or a combo of both."

### Three challenges tool evals address (299:125–129)

1. **Instruction following** — "you need to tell a model how to use each tool, and **the attention you pay to the details matters. Try following the instructions word-by-word yourself to see if you miss a step.**" ← great, concrete, actionable advice.
2. **Tool complexity** — "they can accept simple instructions or require **fine-tuning parameter ranges**."
3. **Edge cases** — "A tool might seem to work well on common inputs, but **behave surprisingly on the rare ones**."

### What a tool evaluation checks (299:130–133)

> "That's why we need tool evaluations. **They let you verify the how, not just the what.**"
> "**The model should call the correct tools, with the correct arguments in the order you expect. And along the way, you'll double check that there weren't any unexpected tool calls in the middle.**"

⇒ four checks: **correct tools**, **correct arguments**, **correct order**, **no unexpected calls**.

### The Book Tracker "library assistant" tool set (299:135–139)

- **`searchBooks`** (`SearchBooksTool`) — "to find books that might have similar tags"
- **`getBookDetails`** — "to extract book metadata, like publication date from the searches"
- **`findSimilarBooks`** — "performs a **semantic search** for similar books"

> "so we're chaining together multiple steps, each one a tool call." — 299:139

### `Tool` conformance (299:140–146)

> "Here's `SearchBooksTool`. It conforms to the **`Tool` protocol**, it has a **name** the model sees and a **description** that tells it **when this tool is useful**. **The arguments are a `Generable` struct. Notice these are all optional, the model decides which filters to use based on what the user asked for.**" — 299:140–143

> "If you prompt a model with **find gothic books**, we'd expect it to populate the **tag** argument. If you prompt a model with **show me something cheerful**, we'd expect to generate a **mood** search. **These are exactly the kinds of decisions we want to evaluate.**" — 299:144–146

> **RECONSTRUCTION** of `SearchBooksTool` (299:140–146):

```swift
struct SearchBooksTool: Tool {
    let name = "searchBooks"
    let description = "Find books in the user's library that match tags, mood, or other filters."

    @Generable
    struct Arguments {
        @Guide(description: "A tag such as a genre to filter by")
        var tag: String?
        @Guide(description: "A mood or tone to search for")
        var mood: String?
        // ...all optional: "the model decides which filters to use"
    }

    func call(arguments: Arguments) async throws -> String { /* ... */ }
}
```

### `TrajectoryExpectation` — the core new type

> "**The main component of a tool evaluation is a trajectory expectation.** A session transcript has tool calls among the prompts and responses. **A `TrajectoryExpectation` checks the order and kind of each tool call in a language model session.**" — 299:149–150

The analogy (worth keeping, it's memorable):

> "You can think of a trajectory expectation check like **going over the list of decisions you made when planning a route. Cars, bikes, and buses are all tools that have their time and place in getting somewhere, but you can evaluate their utility for each segment in a specific trip.**" — 299:151–152

> "The expectation **looks for all of the tool calls. Then for each one, runs it against the expectations you write into your evaluations.**" — 299:153–154

### Case A — unordered, tool presence only

> "Our prompt is 'Find books tagged gothic'. We expect one tool call 'searchBooks'. This is a `TrajectoryExpectation`. It describes the tool calls we expect to see in the model's transcript. **The `unordered` here means we don't care when this tool call happens, just that it happens.**" — 299:156–160

> **RECONSTRUCTION:**
```swift
ModelSample(
    prompt: "Find books tagged gothic",
    expectation: TrajectoryExpectation(unordered: [
        .toolCall("searchBooks")
    ])
)
```

### Case B — argument matchers

> "We can further refine this by **adding arguments to the expectation**. Here I'm adding an argument to expect the tag 'gothic'." — 299:161–162

> "**An exact match isn't always what you want.** If the prompt is 'Find something cheerful', the model might pass **uplifting, happy, cheerful — any of those are fine**. The **`.naturalLanguage`** matcher **checks whether the value matches the intent, not the exact string**." — 299:163–166

> "And there's a whole set of matchers for different situations — **`contains`, `oneOf`, `pattern`, `range`, and more.** Check out the developer documentation for more information." — 299:167–168

⇒ **Matcher inventory (spoken):** `.naturalLanguage`, `contains`, `oneOf`, `pattern`, `range`, "and more" (exact-match is the default/implicit one).

> **RECONSTRUCTION:**
```swift
TrajectoryExpectation(unordered: [
    .toolCall("searchBooks", arguments: [
        "tag": .naturalLanguage("cheerful")   // matches uplifting / happy / cheerful
    ])
])
```

### Case C — ordered trajectories

> "**For multistep tasks, order matters.** Here the model must **first call 'searchBooks', then call 'getBookDetails'**. **If an agent tries to get details first, it doesn't have a `bookId` yet — that's a bug. Trajectory expectations catch it because we're checking the journey, not just the destination.**" — 299:169–172

> **RECONSTRUCTION:**
```swift
TrajectoryExpectation(ordered: [
    .toolCall("searchBooks"),
    .toolCall("getBookDetails"),
])
```

### Case D — `disallowed`

> "**Sometimes what an agent shouldn't do is just as important.** If a prompt includes ideas like **don't look for similar books**, the model should follow instructions. **The `disallowed` parameter specifies tools that must not appear in the transcript.** If an agent calls 'findSimilarBooks' anyway — that's a failure." — 299:173–176

> **RECONSTRUCTION:**
```swift
TrajectoryExpectation(
    unordered: [.toolCall("searchBooks")],
    disallowed: ["findSimilarBooks"]
)
```

### `ToolCallEvaluator`

> "Here's where all of the trajectory expectations come together in the full evaluation. **We define a dataset of samples, each with a prompt and a trajectory expectation and use `ToolCallEvaluator` to score them.**" — 299:177–178

> "**The `ToolCallEvaluator` combines a `LanguageModelSession` with the tools, gets a response, and captures the structured transcript.**" — 299:179

⇒ Note that `ToolCallEvaluator` **drives** the session itself (it constructs/uses a `LanguageModelSession` with your tools), rather than merely inspecting a transcript you supply. That's a meaningful design fact.

> "Tool call evaluation results **show up in the Xcode assistant alongside the rest of your results**, and you can get the whole picture of how your intelligence-based feature behaves." — 299:180

> **RECONSTRUCTION** of the full tool evaluation (299:177–179):

```swift
struct LibraryAssistantEvaluation: Evaluation {
    var dataset: [ModelSample] {
        [
            ModelSample(
                prompt: "Find books tagged gothic",
                expectation: TrajectoryExpectation(unordered: [
                    .toolCall("searchBooks", arguments: ["tag": "gothic"])
                ])
            ),
            ModelSample(
                prompt: "Tell me when the gothic books in my library were published",
                expectation: TrajectoryExpectation(ordered: [
                    .toolCall("searchBooks"),
                    .toolCall("getBookDetails"),
                ])
            ),
            ModelSample(
                prompt: "Find cheerful books, but don't look for similar books",
                expectation: TrajectoryExpectation(
                    unordered: [.toolCall("searchBooks",
                                          arguments: ["mood": .naturalLanguage("cheerful")])],
                    disallowed: ["findSimilarBooks"]
                )
            ),
        ]
    }

    var evaluators: some Evaluator {
        ToolCallEvaluator(
            session: {
                LanguageModelSession(tools: [
                    SearchBooksTool(),
                    GetBookDetailsTool(),
                    FindSimilarBooksTool(),
                ])
            }
        )
    }
}
```

## 2.8 Synthetic data FOR tool evaluations

> "**Trajectory expectations are generable too.** Expanding a dataset for your tool evaluations can be quite complex, and with the Evaluations framework we've made it a lot easier to do just that! **Since our Tool Call evaluation leverages `ModelSample` and `TrajectoryExpectation` that are generable, we can synthetically generate more samples using Sample generator like before.**" — 299:181–182

⇒ **`TrajectoryExpectation` is `@Generable`.** That's what makes trajectory synthesis possible.

### The key gotcha for tool-eval synthesis

> "**Keep in mind when creating synthetic data for tool evaluations, the model doesn't know what tools you've defined or what order the tools need to be called in. So here I've specified the available tools explaining their purpose, any order expectations, and other context the model might need.**" — 299:184–185

⇒ **FOOTGUN #4:** the generation session is *not* the same session as the one that has your tools registered. You must **describe the tools in prose in the generation instructions**.

> "Then we can define the `sampleGenerator` and use our existing dataset as our initial samples, and a **targetCount of 100**." — 299:186

### Three validation metrics for tool samples (299:187–188)

> "We can also specify validation metrics here as well! Here I've made sure **there's always an expectation** and I've also made sure the **synthetic samples include at least one tool**. And lastly **any tools called are actual tools we've already defined**."

⇒ validate: (1) non-nil `TrajectoryExpectation`, (2) ≥1 tool call in the expectation, (3) every named tool exists in your registered tool set.

> **RECONSTRUCTION:**
```swift
let toolSampleGenerator = SampleGenerator(
    prompt: "Generate diverse library-assistant requests and their expected tool trajectories.",
    dataset: toolSamples,
    targetCount: 100,
    sessionProvider: {
        LanguageModelSession(
            model: PrivateCloudComputeLanguageModel(),
            instructions: """
                The app exposes three tools:
                  - searchBooks(tag:mood:) — find books in the user's library.
                  - getBookDetails(bookId:) — fetch metadata; REQUIRES a bookId, so it
                    must always be preceded by searchBooks.
                  - findSimilarBooks(bookId:) — semantic similarity search.
                Produce a user prompt plus the trajectory of tool calls you expect.
                """
        )
    },
    validator: { sample in
        guard let expectation = sample.expectation else { return false }
        guard !expectation.toolCalls.isEmpty else { return false }
        return expectation.toolCalls.allSatisfy { knownToolNames.contains($0.name) }
    }
)
```

> "**The synthetic data APIs are a powerful way to expand your existing dataset beyond your capabilities! And the more representative your data, the more your scores reflect reality.**" — 299:189

## 2.9 The closing synthesis (299:190–195)

> "Earlier we built book tagging evaluation, **it checks what the model produces**. Tag count, genre coverage, quality scores. Now we have tool evaluations — **they check how the model gets there**. The right tools, right arguments and right order. **Run both in the same evaluation suite and you'll have built end-to-end confidence in your feature.**"

Call to action (299:196–197): "try making your own synthetic data, evaluate the custom tools in your app and check out the **sample app and other articles in the developer documentation**."

---

# PART 3 — Session 335: hill climbing, drift, and Cohen's kappa

## 3.1 The hill-climbing loop, defined

> "The Evaluations framework also allows you to **hill climb, which is a process of iteratively improving the quality of your feature using the scores of your evaluation as a guide**." — 335:8

Three phases (335:9–12):
1. **Develop** — "making some change you want to measure against your existing feature."
2. **Evaluate** — "Once all your changes are made, you then need to run the evaluation. And see if the results have passed your expectations."
3. **Analyze** — "From there, you analyze the results to understand how your feature could be further improved."

> "Leveraging the hill-climbing process is a great way to systematically improve your feature, but **effective hill-climbing takes a little bit more than just following the loop. It also takes a little bit of… Science!**" — 335:13–14

Prerequisite stated up front:

> "this video is about the process of hill-climbing an **existing** evaluation. That means **you've already written the foundations of an evaluation pipeline**, which provides a wholistic understanding of the strengths and weaknesses of your intelligence-powered feature." — 335:17–18

Session 299 also anchors the loop: "In this video, we will primarily focus on the **Develop** and **Evaluate** step." (299:9)

## 3.2 The concrete complaint that starts the loop

*Treasure Island*: "I would have expected to see tags like **'tense'** or **'morally grey'**, which speak to the themes of the story." (335:28)

*Little Women*: "Tags like **poignant** has more to do with **how the reader felt** than the contents of the book. **Emotion in book reviews is great, but it should not make it into the list of tags.** Also, a tag like **quiet-steadiness**, which is **pulled directly from the review**, isn't going to be a very useful tag when I want to search my library later." (335:30–32)

⇒ Same two failure modes as 298: **reader-reaction tags** and **over-specific extractive tags**.

## 3.3 The evaluation being hill-climbed

> "The qualitative aspects of my app are captured by the **score dimensions** type." — 335:37
> "**Relevance** tracks the how well the tags represent information about the **book's plot, theme, or other relevant information**. **Usefulness**, measures **how good the tags are as search terms**." — 335:38–39
> "The **`ModelJudgeEvaluator`** uses the **score dimensions and a prompt** to generate a score for each set of tags." — 335:40

⇒ Confirms `ModelJudgeEvaluator` composition = `[ScoreDimension]` + `ModelJudgePrompt`.

## 3.4 Expectations = Swift Testing

> "As a reminder, **your expectations can be defined using Swift Testing's `expect` macro. That way, you can tell if your expectations are met by whether or not your tests pass.**" — 335:50–51

> "In this case, **my Evaluation met all of my expectations; however, because I know the tags aren't as good as I'd like them to be, I need to investigate further.**" — 335:52

⇒ **Key lesson: a green test is not the end of the loop.** Passing tests + bad output ⇒ your metrics or your judge are wrong.

## 3.5 Human-vs-judge disagreement, on record

For *Treasure Island*:
> "I would have scored these tags a **4 for relevance and a 2 for usefulness**. My model judge also gave the tags a relevance score of 4 which is great, but it also gave usefulness a score of 4, which isn't right." — 335:65–66

For *Little Women*: "Once again, I think relevance should be a 4 and usefulness should be a 2." (335:70)

## 3.6 DRIFT — definition and mechanics (verbatim)

> "**This discrepancy between model and human is known as drift, and it is a problem faced by all developers trying to evaluate intelligent features.**" — 335:72

Mechanics (335:74–79):
> "Say I have an evaluation with 10 samples. I then ask a model judge and a person to rate each sample. The model and person then give their ratings on a scale from 1 to 4, and at the end we average those scores to build an aggregate. **If the model and the human tend to disagree in their ratings, then their average scores will diverge from one another, hence the name drift. As your data set continues to grow and grow the drift will get wider and wider. At which point, it'll be hard for you to know whether or not your feature is being properly evaluated.**"

> "To help with this, **you can align your judge to a person's expert opinion**." — 335:80

## 3.7 Why plain accuracy is insufficient (verbatim, and this is subtle)

> "One way to accomplish this would be to line up the ratings of the expert and mark where the two match. You can then use this to generate a percentage. **This percentage is called accuracy, and it is a great way to measure alignment if every value in your scoring scale is equally likely to appear.**" — 335:82–84

> "**However, it's more likely that your dataset will contain values that have an uneven distribution of scores. Think about it, datasets often contain examples of high quality output. Therefore it is often the case that a human rater is likely to rate items in the dataset with higher scores. If a model then happens to judge your smaller dataset with high scores, it may seem like the two are aligned. But then when unleashed on a larger dataset with more variations in scores, it's tendency to score high will still result in drift.**" — 335:85–89

> "So we need an alternative to accuracy, **one that accounts for the weighted nature of our dataset and the chance that the model might guess the right answer**." — 335:90

## 3.8 Cohen's kappa (the alignment metric)

> "**Cohen's kappa coefficient is a mathematical formula made popular by statistician and psychologist Jacob Cohen in 1960.**" — 335:91
> "**Cohen's kappa measures alignment, that is how often do two raters agree.**" — 335:92
> "To do that, we need to know **what percentage of the time the raters agreed, better known as accuracy**... But now we need to calculate a new value. **Coincidence, which represents the chance that one rater might get lucky and happen to align. This luck is then weighted based on the chances certain answers are more likely to appear.**" — 335:93–97

The formula, as narrated step by step (335:98–101):

> "To calculate alignment, we start with our **accuracy** score. From the accuracy score we **subtract the possibility of two raters randomly agreeing**. Finally, we **divide the difference by the inverse of random agreement, namely the chance that the two raters intentionally agreed**. The result of that gives us alignment."

```
alignment (κ) = (accuracy − p_coincidence) / (1 − p_coincidence)

where
  accuracy        = fraction of samples where the two raters gave the same score
  p_coincidence   = probability the two raters agree by chance, weighted by the
                    marginal distribution of each rater's scores
```

### The 0.6 threshold

> "For this test, I've set an expectation that **my ratings and the judges ratings should produce an alignment score of 0.6. We've chosen this number because according to statisticians, an alignment score of 0.6 represents a meaningful level of agreement.**" — 335:131–134

⚠️ **The transcript does NOT say Cohen's kappa is a built-in framework metric.** In fact 335:127 says "we need to calculate Cohen's kappa, which I can do that with a **custom aggregation method**" — i.e. **you implement it yourself in `aggregateMetrics`**. Do not claim a built-in kappa API without doc confirmation.

## 3.9 The "align your judge" evaluation (a meta-evaluation)

Four components (335:106–110): dataset, subject, evaluators, aggregation.

### Dataset — via Xcode test attachments (VERY useful, and easy to miss)

> "For this evaluation to work properly, **both my model judge and I need to evaluate the exact same dataset**. In this case the model judge reviews tags, so I need to produce a **common set of tags** for the judge and I to review." — 335:112–113

> "My evaluation from before contains a collection of reviews and tags. **Because I ran this evaluation in a test, Xcode generated an attachment containing all of the evaluation data that was generated. I can retrieve that attachment and extract summary and tag pairs.** Now, with the summary and tag pairs extracted, **I need to add my ratings**. After that, I can pass the contents of this file as the input to my evaluation." — 335:115–119

⇒ **Xcode auto-attaches the full evaluation data to the test result.** Workflow: run eval → pull attachment → hand-rate the rows → feed back as the alignment dataset.

### Subject — return the already-generated output

> "Normally, the `subject` method is for calling API related to your feature, but **since the generated model responses are part of our dataset, we can simply return the already generated tags**." — 335:121

⇒ Nice pattern: **frozen-output evaluation.** Removes feature nondeterminism so the only variable is the judge.

### Evaluators — the same judge

> "my evaluator is **the exact same model judge evaluator as in our book tags evaluation. This is where the judge provides its rating.**" — 335:123–124

### Aggregation — Cohen's kappa + mean + stddev

> "Here is where we compare my ratings against the judge's. To do that, we need to calculate Cohen's kappa, which I can do that with a **custom aggregation method**. In addition to just Cohen's kappa, I'll also calculate the **mean and standard deviation of each score dimension. This will be helpful to know if the scores of the judge are going up or down.**" — 335:126–129

> **RECONSTRUCTION** of the alignment evaluation (335:106–134):

```swift
struct JudgeAlignmentEvaluation: Evaluation {
    // Rows extracted from the Xcode test attachment of a prior BookTaggingEvaluation
    // run, then hand-annotated with the human expert's ratings.
    let ratedSamples: [RatedTagSample]   // { review, tags, humanRelevance, humanUsefulness }

    var dataset: [ModelSample] { ratedSamples.map(\.asModelSample) }

    // "we can simply return the already generated tags"
    func subject(from sample: ModelSample) async throws -> BookTags {
        BookTags(tags: sample.generatedTags)
    }

    // "the exact same model judge evaluator as in our book tags evaluation"
    var evaluators: some Evaluator { bookTagsJudge }

    func aggregateMetrics(using aggregator: MetricAggregator) {
        aggregator.custom("RelevanceAlignment") { measurements in
            cohensKappa(model: measurements.scores(for: "Relevance"),
                        human: ratedSamples.map(\.humanRelevance))
        }
        aggregator.custom("UsefulnessAlignment") { measurements in
            cohensKappa(model: measurements.scores(for: "Usefulness"),
                        human: ratedSamples.map(\.humanUsefulness))
        }
        aggregator.mean(of: "Relevance");    aggregator.standardDeviation(of: "Relevance")
        aggregator.mean(of: "Usefulness");   aggregator.standardDeviation(of: "Usefulness")
    }
}

@Test(.evaluates(JudgeAlignmentEvaluation(ratedSamples: rated)))
func judgeIsAligned(results: EvaluationResults) throws {
    #expect(results.aggregateValue(for: "RelevanceAlignment")   >= 0.6)
    #expect(results.aggregateValue(for: "UsefulnessAlignment")  >= 0.6)
}
```

## 3.10 Analysis of the failing alignment run

> "It appears that the tests failed, which means my expectations weren't met." — 335:137
> "As I expected, **the scores for both usefulness and relevance are quite low, meaning my model judge and I aren't aligned.**" — 335:141
> "To do that, **I need to open the assistant and view the results in detail.**" — 335:143

Two diagnostic examples:
- *Frankenstein*: "our judge thinks tags like **self-help** and **self-improvement** are relevant to the story. Also **psychological** is an okay search term, **but probably not a term a user is likely to search for**." (335:146–147)
- *The Ramakien*: "The judge and I agree that these collection of terms are helpful and relevant... Where we disagree is on usefulness. Terms like **visual-dimension** and **quaint-dignity** are **way too specific**." (335:148–151)

Diagnosis:
> "**I believe the model doesn't have enough knowledge on it's own to distinguish between a good tag and bad one. That's likely because the prompt of my judge doesn't provide enough context.**" — 335:152–153

## 3.11 Comparative evaluations (the scientific method framing)

> "Fortunately, **in Xcode 27, we've made so you can compare the results of two evaluations against each other.**" — 335:156

> "In a science experiment, you have two groups. **The control group, which represents the baseline** and **the experimental group which represents the change we are trying to compare against.** We can think of the two versions of our instructions in the same way, where the **control group is represented by our base prompt** and our **experimental group is represented by our newly changed prompt**." — 335:158–160

Mechanics:
> "With both prompts written, **I can add both evaluations to a test suite, which will run both evaluations.**" — 335:167

⇒ **Comparative evals = two `Evaluation` instances in the same `@Suite`.** (335:230: "So all I have to do is **define two instances of my evaluation**. One without the tool and one with it.")

Comparison UI:
> "From the evaluation report I can **open the comparison button and open my baseline evaluation**. Here, I can review the scores of the two prompts side by side." — 335:178–179

## 3.12 The three hill-climb iterations, in order (the meat of the session)

### Iteration 1 — a more thorough judge prompt

> "For our experimental prompt, I've written a **more thorough description about how to judge the set of tags. It starts by providing the judge context about the app and what it's about to be judging. Then it gives examples of good tags. As well as ways to identify bad tags.**" — 335:163–166

**Result:** "**my alignment scores for relevance improved. While my alignment score for usefulness dropped considerably.**" (335:170–171)

> "**Balancing tradeoffs like this are tricky so I need to think carefully how to proceed. But before in depth analysis comes checking if we passed. And my test confirms the obvious, we haven't.**" — 335:172–174

> "After thinking about it further, **I am going to keep this prompt change and focus the next round of iteration on improving my usefulness score.**" — 335:175

### The isolate-one-variable move (THE most important procedural detail)

> "**But before I can make changes to the experimental evaluation, I applied the new prompt from my experimental evaluation into my baseline. This ensures there's only one different variable.**" — 335:186–187

⇒ **After you accept an experimental change, promote it into the baseline before starting the next experiment.** Otherwise you're comparing two variables at once.

### Iteration 2 — sharpen the `ScoreDimension` descriptions

Diagnosis from the comparison view:
> "One thing that jumped out to me immediately is the discrepancy between usefulness scores of this review of **'Picture of Dorian Gray'**. It seems to me that **the model may be judging too harshly on usefulness.** The usefulness column of the experimental evaluation seems to corroborate my guess. **I noticed that all the scores are either a 3 or 2, which is way too harsh.**" — 335:180–183

> "I think what could help here is **being more specific about how to grade each scoring dimension.**" — 335:184

Changes:
> "For **relevance**, I've provided a slightly longer description which **emphasizes the need for a genre tag**. And here is the one for **usefulness**. Which **emphasizes being more critical of overly specific tags**." — 335:189–191

**Result:** "**the scores both improved greatly over the baseline. It looks like these specific scoring dimensions are going to be a lot more helpful.**" (335:193–194)

### Iteration 3 — few-shot examples in the judge prompt

Diagnosis: *Moby Dick* — "My relevance score is starting to align. But my usefulness score could still use some work." (335:200–201). *Frankenstein* "continues to give our judge trouble." (335:203)

> "**What I think our judge needs now is some examples of the way I judge things, which should give it a pattern for how to judge according to my scale.**" — 335:204

> "I've reworked my main judge prompt to give it **more detail about the goal of the tag generation feature to help ground the model in the problem space**. From there, I've written out a number of examples for the model to use as a guideline for reviewing." — 335:207–208

### The overfitting warning (critical)

> "**I've made sure to only give the model a few examples. By giving it a longer list I am prone to overfit the alignment score, which would make it hard to tell if my judge is actually aligned with me.**" — 335:210

**Result:** "**And now finally my scores are over my expected value! Which means I've finally passed and can exit out of the loop!**" (335:212)

> "This now means I can be confident that **when my model judge provides ratings, I can confidently say that the tags are good or bad according my standards. That means I can now put my judge to work on evaluating Book Tracker's Book Tagging Service.**" — 335:212–213

## 3.13 Hill climbing beyond prompts: adding a Tool to the feature

> "So far we've seen how to hill climb on prompts... now I'd like to show you how to improve your feature through **something other than your prompts**." — 335:214

> "What I want to do is **give the model some more context about the book it's generating tags for.** I think the additional context will help the model generate more relevant and useful tags. Better still, **Book Tracker already has the data needed for this because we store the author's name and book title when they write their review.** So, to help the tag generator, **I've created a tool to get additional information on the book, which provides the book title and author if they are available. Adding this tool is a form of hill-climbing because we are attempting to improve the quality of our feature through an incremental change.**" — 335:217–221

### The API-design trick for A/B-able features

> "**`BookTaggingService` now takes a list of tools as input. I also set the default to an empty array so my existing evaluation won't need any changes.**" — 335:224–225

> **RECONSTRUCTION** (335:224–231):
```swift
struct BookTaggingService {
    // default [] so existing evaluations compile & behave unchanged
    func generateTags(for review: String, tools: [any Tool] = []) async throws -> BookTags { ... }
}

struct BookTaggingWithToolEvaluation: Evaluation {
    let tools: [any Tool]

    func subject(from sample: ModelSample) async throws -> BookTags {
        try await BookTaggingService().generateTags(for: sample.prompt, tools: tools)
    }
    // ...identical dataset / evaluators / aggregation to BookTaggingEvaluation
}

@Suite struct TagQualityComparison {
    // "define two instances of my evaluation. One without the tool and one with it."
    let control      = BookTaggingWithToolEvaluation(tools: [])
    let experimental = BookTaggingWithToolEvaluation(tools: [BookLookupTool()])
}
```

> "Here is the new evaluation I wrote. **It's exactly the same as the other evaluation. The only difference is I now pass my new lookup tool in the tools array.**" — 335:227–229

**Result & the cliffhanger into session 299:**
> "**my service which uses tools met all my expectations**, so things are looking good. **But, my dataset for Book Tracker contains only 13 book and review pairs, that doesn't cover the wide variety of books and reviews a user might submit for tagging.**" — 335:233–234

> "I can see that **the service with the tool is performing better, however it does seem like my tool isn't being called in all the places I think it needs to. What I really need is a way to tell whether or not my tool has been called in the right situations.**" — 335:236–237

> "To learn more about our APIs for evaluating tool usage and generating comprehensive datasets, take a look at the **'Create robust evaluations for agentic apps'** video. There, you'll learn about **tool call Evaluators** and how to use the **Sample Generator API**." — 335:239–240

## 3.14 Session 335 recap (verbatim — four rules)

1. > "**Hill-climbing works best when you focus on making one change at a time. To do this, treat every iteration of the loop like a science experiment. Being able to isolate your changes will help you to understand how each part of your feature contributes to the overall quality. Knowing how each part works individually will also help you to know where you might need to make changes to resolve a bug or unwanted pattern later down the line.**" — 335:242–245

2. > "**Second, this process takes time. Not every change you make will result in positive change. However, failed experiments tell you just as much as successful ones.**" — 335:246–248

3. > "**Third, good experiments require creativity. In an intelligent feature there are so many things you can change. In your feature you can change the instructions, the tools, as well as the model or models you use to generate responses. On the evaluation side you can change the dataset, aggregation methods, and even the evaluators themselves. Everything is fair game.**" — 335:249–253

4. > "**Finally, watch out for drift. It can feel a bit meta to evaluate your evaluators but a well tuned model evaluator will save you time in the long run. Models can generate ratings much faster than humans can. So by keeping them aligned, you get useful signal as your dataset grows to cover more and more use cases.**" — 335:255–258

### The knobs you can turn, tabulated

| Side | Knob |
|---|---|
| Feature | instructions / prompt |
| Feature | tools (add/remove/change) |
| Feature | the model or models used to generate responses |
| Evaluation | dataset (size, coverage, edge cases) |
| Evaluation | aggregation methods |
| Evaluation | the evaluators themselves (incl. judge prompt & score dimensions) |

---

# PART 4 — Session 232: Agentic AI workflows on Mac with MLX

## 4.1 Framing

> "Today I'm going to show you how to **build and run agentic AI workflows entirely on your Mac using MLX. No cloud, no API keys, just your hardware doing the work.**" — 232:2–3

Chat vs. agent (232:6–17):
> "Here's the chat experience you're familiar with. You send a prompt to the language model. The model sends a response back. **If you need to act on that response, run a command, check a file, or fix an error, that's on you.** But now you're talking to an agent. **The agent talks to the model to decide what to do. Then it calls tools to actually do it: running commands, reading files, hitting APIs — It observes the results and goes back to the model to figure out the next step. User to agent. Agent to model. Agent to tools. This is the agentic loop. And it keeps cycling until your task is done.**"

> "What makes this particularly exciting on Apple silicon is that **the entire loop can run locally. Your data stays on your machine; AI is available anywhere at any time and there are no usage costs.**" — 232:18–19

## 4.2 The four-layer local agentic stack (232:33–49)

| Layer | Component | Role (verbatim) |
|---|---|---|
| 4 (top) | **The agent** | "any framework or tool that speaks the **OpenAI chat completions protocol**: **Xcode, OpenCode, Pi agent, a custom script**, or anything else." |
| 3 | **MLX-LM Server** | "an **OpenAI-compatible HTTP server** that exposes your local model through a standard API. It supports **structured tool calling** so the model can invoke functions reliably, and **reasoning models** that can analyze complex problems step-by-step before responding. **It's a drop-in replacement for any cloud LLM API.**" |
| 2 | **MLX-LM** | "provides everything you need to **load, run, quantize, and fine-tune** large language models. It supports **thousands of models from HuggingFace** and gives you both **CLI tools and a Python API**." |
| 1 (bottom) | **MLX** | "our **open-source array framework purpose-built for Apple silicon**. It handles all the **low-level computation, Metal acceleration, and memory management**." |

Ecosystem note:
> "Several popular apps and tools build on MLX and MLX-LM. **Ollama, LM Studio, and vLLM** are just a few of the most popular ones. The ecosystem is broad and growing, and **if you're using one of these tools, chances are you're already running on MLX.**" — 232:51–53

## 4.3 Three-step setup (verbatim)

> "**It only takes three steps to go from zero to a fully local agentic workflow.**" — 232:56

**Step one:** "install MLX-LM. **A single `pip install`** gets you everything you need." (232:57–58)
```bash
pip install mlx-lm
```
*(Cross-checked: `repos/ml-explore__mlx-lm/README.md:17–27` — `pip install mlx-lm` or `conda install -c conda-forge mlx-lm`.)*

**Step two:** "start the server. Run `mlx_lm.server` **with a model that supports tool calling**. **Starting with a small model to test your set-up is always a good idea.** The server starts up, loads the model, and is ready to accept requests on **local host**." (232:59–63)
```bash
mlx_lm.server --model <hf-repo-or-local-path>
```
*(Cross-checked: `repos/ml-explore__mlx-lm/mlx_lm/SERVER.md:11–21`.)*

**Step three:** "point your agent at the local server. **In most agent frameworks, you just set the base URL to your local server's address and you're done. The agent doesn't know or care that the model is running on your Mac rather than in the cloud.**" (232:64–66)

## 4.4 OpenCode configuration (232:67–73)

> "Here's the configuration for OpenCode. **We define a local provider. In particular, we set the URL to local host and set the model name the server expects. We also tell OpenCode to use this local model for everything.** That's it. Now every interaction runs through your local model."

> **RECONSTRUCTION** — the exact JSON was on screen but not read aloud. This is the standard OpenCode `opencode.json` shape and is **UNVERIFIED** against the slide:

```jsonc
{
  "provider": {
    "mlx": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "MLX (local)",
      "options": { "baseURL": "http://localhost:8080/v1" },
      "models": { "mlx-community/<model-id>": { "name": "<model-id>" } }
    }
  },
  "model": "mlx/mlx-community/<model-id>"
}
```

## 4.5 Challenge 1 — prompt processing, and the M5 Neural Accelerators

> "In an agentic workflow, **every time the model receives tool output, it has to process all that new context before it can reason about the next step. This happens over and over throughout the agentic loop, and it adds up fast.**" — 232:76–77

> "**Agentic sessions usually comprise hundreds of thousands of tokens and most of those are not generated.**" — 232:78

⇒ i.e. agentic workloads are **prefill-dominated**, not decode-dominated. That's the whole reason the M5 story matters here.

> "**The M5 chip introduces dedicated Neural Accelerators, and MLX can target them for exactly this kind of work. Specifically, Neural Accelerators make matrix multiplication four times faster on M5 compared to M4. And with the specialized multiplication and attention kernels in MLX this translates almost exactly to prompt processing speedup.**" — 232:79–81

> "Reducing prompt processing time means **your agents can read your codebase or process tool results almost four times faster.**" — 232:82

> "And the best part? **Taking advantage of Neural Accelerators requires no special arguments or code changes on your part, MLX selects the best kernel for the available hardware and it just works.**" — 232:83

## 4.6 Challenge 2 — concurrency / continuous batching

> "In practice, **agents rarely work alone. A common pattern is for an agent to spawn several subagents, each tackling a different part of the problem in parallel. One might be reading documentation, another searching code, and a third writing tests; all at the same time. That means multiple requests hitting your local model simultaneously.**" — 232:85–88

> "**MLX-LM Server handles this with continuous batching.** Instead of processing requests one at a time, **it dynamically groups incoming requests into batches and processes them together on the GPU. New requests can join a batch in progress without waiting for the current one to finish.** The result is that **your subagents don't stall waiting in a queue. They all get served concurrently**, which keeps the entire agentic workflow moving." — 232:89–93

### CROSS-CHECK against the local repo (agrees, and adds detail)

`repos/ml-explore__mlx-lm/mlx_lm/server.py` confirms continuous batching and exposes tunables not mentioned in the talk:

- `--decode-concurrency` (default **32**) — "When a request is batchable then decode that many requests in parallel" (server.py:1819–1824)
- `--prompt-concurrency` (default **8**) — "When a request is batchable then process that many prompts in parallel" (server.py:1825–1830)
- `--prefill-step-size` (default **2048**) (server.py:1831–1836)
- `--prompt-cache-size` (default **10**) — "Maximum number of distinct KV caches to hold in the prompt cache" (server.py:1837–1842)
- `--prompt-cache-bytes` — "Maximum size in bytes of the KV caches" (server.py:1843–1847)
- `--pipeline` — "Use pipelining instead of tensor parallelism" (server.py:1848–1852)
- `BatchGenerator(... completion_batch_size=decode_concurrency, prefill_batch_size=prompt_concurrency ...)` (server.py:757–761)
- `batch_generator.insert_segments(...)` — the mechanism by which a new request joins a batch in progress (server.py:712)

**Batchability gate (GOTCHA, from source, not the talk):**
```python
# mlx_lm/server.py:352-356
# Compute batchability
is_batchable = draft_model is None
is_batchable = is_batchable and all(
    hasattr(c, "merge") for c in make_prompt_cache(model)
)
```
```python
# mlx_lm/server.py:621-622
def _is_batchable(self, args):
    return self.model_provider.is_batchable and args.seed is None
```
⇒ **Speculative decoding (`--draft-model`) disables continuous batching**, and **any request that sets `seed` is un-batchable** and forces the current batch to drain (server.py:767–770: "We have a batch but this request cannot be added to the batch so drain it to process the request."). For agentic/subagent workloads: **do not set `seed`, and do not use a draft model.**

## 4.7 Challenge 3 — model size / distributed inference

> "Sometimes a single machine, **even one with 512GB of RAM**, just isn't enough because the model is too large to fit in memory. **The most recent DeepSeek model for instance has a whopping 1.6 trillion parameters and requires more than 800GB of memory just for the weights.**" — 232:94–97

> "**MLX's distributed support lets you spread a model across multiple Macs connected over Thunderbolt or Ethernet.** For agents, this is powerful in two ways. **First, it lets you run much larger, more capable models that wouldn't fit on a single machine. Second, it parallelizes prompt processing across devices, which directly speeds up the agentic loop since the model can process tool results faster.**" — 232:98–101

> "Setting up distributed inference with MLX-LM Server is fairly straightforward. **You launch the server using `mlx.launch` and a hostfile that contains information about the nodes and the type of connection. The model is automatically sharded across all available devices and everything else just works.**" — 232:102–105

> "**Starting with macOS 26.2, we have support for Thunderbolt RDMA, which provides low-latency, high-bandwidth communication over Thunderbolt. As a result, distributed inference with MLX has seen significant speed-ups: up to three times with four nodes.**" — 232:106–108

> "To learn how to set up your Macs for distributed inference with MLX, check out our session **'Explore distributed inference and training with MLX'**." — 232:109

### CROSS-CHECK against the local repos (agrees)

`repos/ml-explore__mlx/docs/src/usage/launching_distributed.rst` confirms `mlx.launch` + JSON hostfile + Thunderbolt RDMA:

- Two utilities: **`mlx.launch`** and **`mlx.distributed_config`** (rst:14–15)
- Hostfile schema (rst:141–146):
  ```json
  [
      {"ssh": "hostname1", "ips": ["123.123.1.1", "123.123.2.1"]},
      {"ssh": "hostname2", "ips": ["123.123.1.2", "123.123.2.2"]}
  ]
  ```
- RDMA over Thunderbolt uses the **JACCL** backend (rst:33, 194): "`--backend jaccl`. A hostfile is necessary to launch with this backend because it needs to contain the RDMA devices connecting each node to each other"
- Autoconfig command (rst:45–47):
  ```
  mlx.distributed_config --verbose --backend jaccl \
       --hosts m3-ultra-1,m3-ultra-2,m3-ultra-3,m3-ultra-4 --over thunderbolt \
       --auto-setup --output m3-ultra-jaccl.json
  ```
  "The `--auto-setup` argument **requires password-less sudo on each node**." (rst:66)
- Other backends: `ring` (TCP/IP over thunderbolt or ethernet), `nccl`, `mpi` (rst:33–35, 194–234)
- Debug topology: `mlx.distributed_config --verbose --hosts h1,h2,h3,h4 --over thunderbolt --dot` emits GraphViz (rst:97–103)
- `mlx.launch --print-python` to find the python path that must exist identically on all hosts (rst:160)

`repos/ml-explore__mlx-lm/mlx_lm/server.py` confirms server-side distributed:
```python
# server.py:1701-1714
def run(host, port, model_provider, server_class=ThreadingHTTPServer, handler_class=APIHandler):
    group = mx.distributed.init()
    prompt_cache = LRUPromptCache(model_provider.cli_args.prompt_cache_size)
    response_generator = ResponseGenerator(model_provider, prompt_cache)
    if group.rank() == 0:
        _run_http_server(host, port, response_generator)
    else:
        response_generator.join()
```
⇒ **Only rank 0 serves HTTP**; all other ranks join the generator loop. Point your agent at rank 0.

**GOTCHA from source (not in the talk):**
> `"Loading with adapters or draft models not supported in distributed mode"` — `mlx_lm/server.py:311`

## 4.8 Demos

### Demo 1 — PR triage (232:21–26)

> "on the left, **MLX running the model**, and on the right the **OpenCode agent** I am interacting with. I asked it to **fetch the recent pull requests from our MLX repository, summarize the changes, and identify anything that needs my attention.** The model reasons about the request, **calls the GitHub CLI** to fetch PR data, reads through the diffs, and produces a concise summary. **All of this is happening locally, the model runs on my hardware and only the git commands reach the network.**"

### Demo 2 — build a SwiftUI app from scratch (232:112–131)

> "I have started with a **blank Xcode project** and I am asking the agent to **build a drawing app for the iPad**."
> "The agent **first looks at the current directory to find out the existing project structure, makes a plan to guide its implementation, and gets on to writing the code.** Using an agent means **we don't need to copy anything or even build the project. The agent writes the file then builds the app, fixing any errors it encounters along the way.**"
> "**it only took a couple of minutes to create the first version of the app.**"
> Iteration: "I prefer **rounded end caps**... The agent will **edit the code and recompile the app until it compiles without errors.**"
> "**the model ran through MLX-LM server on this Mac and the agent used standard development tools like `xcodebuild` to verify and build its work.**"

### Demo 3 — Xcode's built-in agent pointed at MLX (232:132–146) — the concrete Xcode UI workflow

> "Let's connect Xcode to our already running MLX server. **We open the settings and navigate to the Intelligence tab. We click on Add Chat Provider... and select a Locally Hosted provider. We set the Port to 8080 or whichever port we selected when launching our MLX server and we're done. Now Xcode can talk to our local model.**" — 232:134–141

**Exact click path:** Xcode ▸ Settings ▸ **Intelligence** tab ▸ **Add Chat Provider…** ▸ **Locally Hosted** ▸ **Port: 8080**.

*(Cross-check: `mlx_lm/server.py:1735–1740` — `--port` default is **8080**, `--host` default **127.0.0.1**. `SERVER.md:23`: "This will start a text generation server on port `8080` of the `localhost`".)*

> "I have introduced a bug to our previously working app and now we can ask the model to fix it. **Within seconds, it identifies the bug and inspects the code around it. Finally, it writes a fix and we can now build and run our app.**" — 232:142–144

> "This shows how **a locally running agent can integrate with your existing development workflow in Xcode, reading project files, understanding build errors, and making targeted fixes. Local AI means your code never leaves your Mac.**" — 232:145–146

## 4.9 Closing

> "Today, we showed you the full stack for running agentic AI locally on your Mac, from MLX all the way up to the agent, and how **Neural Accelerators, continuous batching, and distributed inference** make it fast. To get started, **install MLX-LM, launch the server, and point your favorite agent at it. Everything we showed today is open-source and available right now.**" — 232:147–149

---

# PART 5 — Cross-checks against local docs / repos / forums

## 5.1 `docs/` — NO coverage of Evaluations

`/Volumes/ExtStor/FM and MLX and CoreAI/docs/` contains only 6 markdown files, all Core AI / Speech:
- `Bringing advanced speech-to-text capabilities to your app.md`
- `Compiling Core AI models ahead of time.md`
- `Integrating on-device AI models in your app with Core AI.md`
- `Managing model specialization and caching.md`
- `Recognizing speech in live audio.md`
- `Run AI models in your app on Apple silicon.md`

`grep -ril "evaluation" docs/` returns **nothing**. ⇒ **No local written documentation exists to corroborate any Evaluations API name.** Everything in Parts 1–3 rests solely on the transcripts. This is the single biggest verification gap in this note.

## 5.2 `forums/machine-learning-and-ai-topic-evaluations.txt`

Topic blurb (authoritative one-liner, useful for a guide intro):
> "**Discuss how to use Evaluations to design and run evaluation suites for LLM-based features in your apps.**" — forums:6

Three open threads, all June 2026, all with **no captured replies**:
1. **"Vision evaluations"** (thread/833822, sfrunner, 2026-06-11) — "Are evaluations just for Text-text, or is there an efficient ways to evaluate image-text, like for MobileClip2, or YOLOE?" ⇒ multimodal eval support is an **open question**. (Note the tension with 298:22's claim that "you can evaluate any stochastic system, such as classifiers and linear regression models".)
2. **"Evaluations for non-Swift languages"** (thread/833729, ardysingh) — "Is Evaluations only for swift or does it support other languages like python and others?" ⇒ **open**, but see §5.3.
3. **"Performance and customization of alternate options"** (thread/832053, progressneverstops) — "**How do I use the 'model judge evaluator' to compare the accuracy of a custom LoRA adapter against the system's private cloud compute models?**" ⇒ confirms the community reads `ModelJudgeEvaluator` as the adapter/model-comparison tool. Also asks about MLX-on-device vs AFM Core perf trade-offs.

## 5.3 Cross-references from OTHER transcripts (not in my assignment, read only for corroboration)

- **`wwdc2026-241.txt:106–109`** (platforms-state-of-the-union-ish overview): "**The Evaluations framework is a new Swift framework that measures the quality of your intelligence features. With the Evaluations framework, you can quantify accuracy as you tweak your prompts. Evaluations is built to help app developers like you, understand the statistical impact of changes, and deliver your app with confidence.**" ⇒ **"Swift framework"** confirmed a second time.
- **`wwdc2026-319.txt:63–68`** (Private Cloud Compute session): "**When deciding between the on-device and PCC model, or deciding the reasoning level to use, it's good to make that decision based on data, not just vibes. Evaluating let's you understand the quality of your specific feature. You may be surprised how well the on-device model performs at certain tasks... But the only way to know is by evaluating. That's why we created the brand new Evaluations framework. It's a new Swift framework that helps you evaluate your Foundation Models features. It's integrated right in Xcode, and it's easy to get started.**" ⇒ **model-selection is an explicit intended use case** for Evaluations.
- **`wwdc2026-319.txt:60`**: "Just access the **`contextSize`** property on either **`SystemLanguageModel`** or **`PrivateCloudComputeLanguageModel`**." ⇒ relevant to the 299 context-exhaustion footgun; you can budget generation runs against `contextSize`.
- **`wwdc2026-242.txt:185`** (context engineering): "When you start to get into nuanced transcript modifications like this, **it becomes even more important to use the Evaluations framework to create eval sets and quantify the effect of context engineering strategies.**"
- **`wwdc2026-246.txt:109–131`** (Spotlight / `SpotlightSearchTool`) — the richest external corroboration of the eval APIs:
  - "The Evaluations framework has some great APIs for building an end-to-end evaluation suite, **from large-scale dataset generation, to evaluation runs using custom metrics, and reporting**." (246:111)
  - "**We'll start by defining a dataset that adopts the `ModelSampleProtocol`.**" (246:115) ⇒ **NEW TYPE NAME not present in 298/299: `ModelSampleProtocol`.** Their custom sample type is `TrailRequest`: "Our `TrailRequest` already includes the natural language input that a person might ask about trails in our app, the output is a language model response and **an expectation of the trajectory of the request**. We'll also be adding a set of unique identifiers of searchable items that we expect the tool to return for that prompt." (246:116–117) ⇒ confirms samples carry **prompt + expected output + `TrajectoryExpectation` + arbitrary app-specific expectations**.
  - "**Samples can be serialized in any Codable format, and JSON works well for that purpose.**" (246:122) ⇒ `ModelSample`/your sample type is `Codable`.
  - "**Using the Sample Generation APIs in a command line tool**, I can expand this seed set to many more variations" (246:125) ⇒ corroborates 299:15 ("run it from the command line").
  - "For our samples, **we expect the trajectory of a response to include a call to `SpotlightSearchTool`** to perform a query, so here's how we might define that expectation." (246:127)
  - Custom metric named **`result coverage`**: "we can set the expectation for any metric we've included, like **result coverage**" (246:129–131) ⇒ example of a domain-specific quantitative metric (how many expected items appeared in the final response).
  - Eval setup can include **environment setup in the evaluation itself**: "our evaluation will load the trail items and samples from our generated datasets. Then, **we'll donate the trail items to Core Spotlight, and configure `SpotlightSearchTool` for this evaluation.**" (246:129–130)
- **`wwdc2026-334.txt:120–132`** (Python SDK / `apple-fm-sdk`): "To evaluate their prompt and iterate, **Swift developers can leverage the Evaluations framework. It's available with Xcode 27**, and it makes it easy to create evaluations, and track the accuracy of your features across multiple iterations. **But many data scientists might be more familiar with Python than with Swift. If you fall under this scenario, let me show you how I can perform this analysis in Python by using the Python SDK from a Jupyter Notebook.**" — then describes a hand-rolled Python pipeline: server-model-generated eval data → multiple prompt implementations → outputs per implementation → **Pandas DataFrame** rows → "**judge functions that rely on a server model**" scoring each output → metrics back into the DataFrame → charts.
  ⇒ **Strong implication: the Evaluations framework is Swift-only; Python users roll their own with the FM Python SDK + pandas.** Answers forum thread 833729, at least by inference.
- **`wwdc2026-243.txt:145`**: "Watch 'Meet the Evaluations framework' to see how you can **measure and improve the quality of your prompts by using structured evaluation**."

## 5.4 MLX repo cross-checks — summary table

| Talk claim (232) | Repo evidence | Verdict |
|---|---|---|
| `pip install mlx-lm` | `mlx-lm/README.md:17–21` | ✅ agrees |
| `mlx_lm.server --model <...>` | `mlx_lm/SERVER.md:11–21` | ✅ agrees |
| server on localhost, port 8080 | `SERVER.md:23`; `server.py:1735–1740` (`--host` default `127.0.0.1`, `--port` default `8080`) | ✅ agrees |
| OpenAI-compatible | `SERVER.md:3–5` "intended to be similar to the OpenAI chat API"; `/v1/chat/completions`, `/v1/models` endpoints | ✅ agrees |
| structured tool calling | `server.py:54` `ToolCallFormatter(tool_parser, tools, streaming)`; `server.py:1471` `finish_reason = "tool_calls"`; `server.py:516–521` warns if `tools` passed but `not tokenizer.has_tool_calling` | ✅ agrees, plus a gotcha |
| continuous batching | `server.py:637–770` `BatchGenerator`, `insert_segments`, drain logic; `--decode-concurrency`/`--prompt-concurrency` | ✅ agrees |
| `mlx.launch` + hostfile | `mlx/docs/src/usage/launching_distributed.rst:14, 111–146` | ✅ agrees |
| Thunderbolt RDMA | `launching_distributed.rst:33` "RDMA over thunderbolt using **JACCL**" | ✅ agrees (talk didn't name JACCL) |
| model auto-sharded across devices | `server.py:1708–1714` (`mx.distributed.init()`, rank-0 HTTP); `mlx_lm/utils.py:545–589` `pipeline_group`/`tensor_group` | ✅ agrees |
| "no special arguments" for M5 Neural Accelerators | not directly greppable in this snapshot | ⚠️ unverified in repo; take the talk's word |
| DeepSeek 1.6T / >800GB | n/a | ⚠️ talk-only |
| macOS 26.2 Thunderbolt RDMA gate | not stated in the checked-out rst | ⚠️ talk-only |

**⚠️ Repo-snapshot caveat:** the local `ml-explore__mlx-lm` checkout is a *current* clone; some of the WWDC26-era behavior (e.g. M5 Neural Accelerator kernel selection) may not be visible in the files I grepped. Absence of evidence in the repo ≠ contradiction.

---

# PART 6 — Consolidated API inventory (Evaluations framework)

Every identifier below was **spoken aloud** in one of the four transcripts. Confidence column: 🟢 = named multiple times / unambiguous; 🟡 = named once, casing or exact spelling uncertain; 🔴 = inferred, not spoken.

| Identifier | Kind | Confidence | Source |
|---|---|---|---|
| `import Evaluations` | module | 🟢 | 298:55 |
| `Evaluation` | protocol | 🟢 | 298:55, 335:106 |
| `subject(from:)` | method on `Evaluation` | 🟢 | 298:64, 335:121 |
| `dataset` | property on `Evaluation` | 🟢 | 298:157, 335:111 |
| `aggregateMetrics(using:)` | method on `Evaluation` | 🟢 | 298:78 |
| `Metric` | type | 🟢 | 298:70–71, 163, 223 |
| `Evaluator` | protocol/type, closure-taking | 🟢 | 298:73, 77, 222 |
| `ModelSample` | type | 🟢 | 298:67, 110, 154; 299:182 |
| `ModelSamples` | type / API | 🟡 | 299:35 (possible transcription of `ModelSample`) |
| `ModelSampleProtocol` | protocol | 🟡 | `wwdc2026-246.txt:115` (outside assignment) |
| `.evaluates(_:notes:)` | Swift Testing `@Test` trait | 🟢 | 298:87–89 |
| evaluation **results bundle** | type (name not spoken) | 🔴 | 298:90 |
| `aggregateValue` | method on results bundle | 🟢 | 298:93 |
| `ModelJudgeEvaluator` | type | 🟢 | 298:252, 278; 335:40 |
| `ScoreDimension` | type (name, description, scale) | 🟢 | 298:242–250; 335:37 |
| `ModelJudgePrompt` | type | 🟢 | 298:257–261 |
| `.instructions` | `ModelJudgePrompt` member | 🟢 | 298:259 |
| `.evaluationTarget` | `ModelJudgePrompt` member | 🟢 | 298:260 |
| `SampleGenerator` | type | 🟢 | 298:153; 299:45, 186; 335:240 |
| `SyntheticGenerator` | type | 🟡 | 299:91 — likely a slip for `SampleGenerator` |
| `makeSamples(prompt:dataset:targetCount:)` | function/method | 🟢 | 299:31, 40 |
| `.run()` | method on `SampleGenerator` | 🟢 | 299:68–69 |
| `sessionProvider` | `SampleGenerator` config (closure → `LanguageModelSession`) | 🟢 | 299:46, 53, 56 |
| `samplingStrategy` | `SampleGenerator` config | 🟢 | 299:59 |
| random sampling strategy (default) | enum case | 🟢 (name 🔴) | 299:60–62, 66–67 |
| sliding-window sampling strategy | enum case | 🟢 (name 🔴) | 299:63–65 |
| `validator` | `SampleGenerator` config (closure) | 🟢 | 299:72–73 |
| `samples` | property on the generator (valid samples) | 🟢 | 299:91 |
| `invalidSamples` | property on the generator | 🟢 | 299:92 |
| `targetCount` | parameter (inclusive of seed dataset) | 🟢 | 299:31, 36, 186 |
| `TrajectoryExpectation` | type, `@Generable` | 🟢 | 299:149–182; 246:127 |
| `unordered` | `TrajectoryExpectation` parameter | 🟢 | 299:160 |
| ordered trajectory | `TrajectoryExpectation` form | 🟢 (label 🔴) | 299:169–170 |
| `disallowed` | `TrajectoryExpectation` parameter | 🟢 | 299:175 |
| `.naturalLanguage` | argument matcher | 🟢 | 299:165–166 |
| `contains` | argument matcher | 🟢 | 299:167 |
| `oneOf` | argument matcher | 🟢 | 299:167 |
| `pattern` | argument matcher | 🟢 | 299:167 |
| `range` | argument matcher | 🟢 | 299:167 |
| `ToolCallEvaluator` | type | 🟢 | 299:178–179; 335:240 |
| Cohen's kappa | **user-written** custom aggregation | 🟢 (not an API) | 335:127 |

**Foundation Models types referenced from Evaluations code:** `@Generable`, `@Guide` (incl. `count:` taking a range), `LanguageModelSession`, `Tool` protocol, `SystemLanguageModel`, `PrivateCloudComputeLanguageModel`, `#Playground`.

---

# PART 7 — Gotchas, footguns, and hard-won guidance (consolidated)

## Framework / platform
1. **Xcode 27 only.** "This framework is new in Xcode 27 and supports macOS, iOS, watchOS and visionOS." (299:2) — **tvOS not listed.**
2. **Swift-only** (implied by 241:106, 319:66, 334:120–124 pushing Python users to the FM Python SDK + pandas instead). Unanswered forum thread on this.
3. **Evaluations is model-agnostic in principle** — "you can evaluate any stochastic system, such as classifiers and linear regression models" (298:22) — but image/multimodal support is unconfirmed (open forum thread).

## Metrics design
4. **A green test proves nothing about output quality.** 335:52 — "my Evaluation met all of my expectations; however, because I know the tags aren't as good as I'd like them to be, I need to investigate further."
5. **Pass/fail range metrics hide degenerate distributions.** After adding `@Guide(count: 3...8)` the service emitted **exactly 8 tags every time** while `TagCount` reported 100%. Always pair a **pass/fail** metric with a **scored** metric that records the raw value (`TagTotal`). (298:127–130, 158–166)
6. **Quantitative vs qualitative rule of thumb:** "if you can measure it in code, then it's quantitative. And if you can only describe it in words, then you need a qualitative metric, using a `ModelJudgeEvaluator`." (298:277–278)
7. **Model judges and heuristic evaluators mix freely** in one evaluation — same protocol, same `Metric` type. (298:222–224)

## Model judges
8. **Judge must be ≥ as capable as the model under test.** (298:209) In practice: on-device feature → **PCC judge**.
9. **Use an even-numbered scale (1–4).** "An even number of options prevents the judge from defaulting to a neutral middle score. Four levels provides just enough distinction without diluting the meaning of each rating." (298:219–220)
10. **A broad dimension = uniform scores = no signal.** "If the scores are all the same, your question is too broad." (298:283) The *Alice in Wonderland* case: one "TagQuality" dimension conflated **relevance** and **usefulness**; splitting them produced two separately actionable rationales. (298:238–241, 263–267)
11. **When you disagree with the judge, the judge is usually right and your rubric is wrong.** "by the scale we wrote, the judge is actually right... The judge is faithfully following the scoring guide we provided." (298:232–234)
12. **Dimensions without app context are dangerous.** "It has no way to know that Book Tracker is a personal library, not a review platform." (298:256) ⇒ that's what `ModelJudgePrompt.instructions` is for.
13. **Always read rationales.** (298:230–231, 279–282)
14. **Few-shot examples in the judge prompt help, but too many overfit the alignment score.** "By giving it a longer list I am prone to overfit the alignment score, which would make it hard to tell if my judge is actually aligned with me." (335:210)

## Drift & alignment
15. **Drift is systemic and grows with dataset size.** (335:72, 78–79)
16. **Plain accuracy is a bad alignment metric** when your score distribution is skewed high — which it usually is, because "datasets often contain examples of high quality output." (335:85–89)
17. **Use Cohen's kappa; target ≥ 0.6.** "according to statisticians, an alignment score of 0.6 represents a meaningful level of agreement." (335:133–134) You compute it yourself in a **custom aggregation method** (335:127).
18. **Freeze the feature output when aligning the judge.** Return already-generated tags from `subject(from:)` so the only variable is the judge. (335:121)
19. **Also track mean + standard deviation per score dimension** — "helpful to know if the scores of the judge are going up or down." (335:128–129)

## Hill climbing / experiment hygiene
20. **One variable at a time.** After accepting an experimental change, **promote it into the baseline** before the next experiment: "I applied the new prompt from my experimental evaluation into my baseline. This ensures there's only one different variable." (335:186–187)
21. **Comparative evaluation = two `Evaluation` instances in one `@Suite`.** (335:167, 230)
22. **Trade-offs are normal:** iteration 1 raised relevance alignment while "my alignment score for usefulness dropped considerably" — and he **kept** the change anyway and attacked usefulness next. (335:170–175)
23. **Failed experiments are informative.** (335:246–248)
24. **Make features A/B-able by defaulting new params:** `BookTaggingService` gained `tools:` with a **default of `[]`** "so my existing evaluation won't need any changes." (335:224–225)

## Synthetic data
25. **`targetCount` is the FINAL dataset size, including seeds.** 13 seeds + `targetCount: 100` ⇒ 87 generated. (299:36)
26. **`sessionProvider` may be called more than once.** Context exhaustion mid-run throws; the generator re-invokes `sessionProvider` and the new session has **no prior context**. "make sure your instructions in your `sessionProvider` is self-contained and doesn't assume it'll only be called once." (299:54–57)
27. **Prompt rules ≠ enforced rules.** "that doesn't guarantee the output will actually follow the rules" — the `validator` is the enforcement layer. (299:74)
28. **The `validator` sees one sample in isolation** — corpus-level properties (diversity, length *variation*) cannot be validated there. (299:81–82)
29. **Batch size is automatic; the session is reused across batches** to maintain context. (299:52–53)
30. **`samplingStrategy` defaults to random.** Use sliding window only "if your dataset has meaningful order." (299:65–67)
31. **`samples` / `invalidSamples` update in real time** — you can inspect them mid-run. (299:93)
32. **Bigger dataset ⇒ expect scores to DROP.** "we're expecting the scores to drop! And we were correct!" — high scores on 13 samples were an artifact. (299:100–102)
33. **For tool-eval synthesis, the generator model has no idea what your tools are.** You must describe every tool, its purpose, and ordering constraints in the generation instructions. (299:184–185)
34. **Validate synthesized tool samples for:** an expectation exists, ≥1 tool call, and every named tool actually exists. (299:187–188)

## Tool / agentic evaluations
35. **Right answer ≠ right path.** "A model might give you a reasonable-sounding answer without ever calling the right tool." (299:123–124)
36. **Ordering bugs are real bugs:** calling `getBookDetails` before `searchBooks` means no `bookId` exists. (299:171)
37. **Prefer `.naturalLanguage` over exact match for free-form arguments** (mood: "uplifting/happy/cheerful" all acceptable). (299:163–166)
38. **`disallowed` encodes negative instructions** ("don't look for similar books"). (299:173–176)
39. **Read your tool instructions literally.** "Try following the instructions word-by-word yourself to see if you miss a step." (299:126)

## MLX agentic (232)
40. **Agentic workloads are prefill-dominated:** "hundreds of thousands of tokens and most of those are not generated." (232:78) Optimize prompt processing, not decode.
41. **M5 Neural Accelerators: 4× matmul vs M4**, translating "almost exactly" to prompt-processing speedup; **zero code/flags required**. (232:79–83)
42. **macOS 26.2 gate for Thunderbolt RDMA**; up to **3× with four nodes**. (232:106–108)
43. **Choose a model that supports tool calling**, and "starting with a small model to test your set-up is always a good idea." (232:61–62)
44. *(From source, not the talk)* **`--draft-model` disables continuous batching**, and **any request with a `seed` drains the batch.** `mlx_lm/server.py:353, 622, 767–770`.
45. *(From source)* **Adapters and draft models are unsupported in distributed mode.** `mlx_lm/server.py:311`.
46. *(From source)* Server warns but does not fail when you pass `tools` to a model whose tokenizer lacks tool-calling. `mlx_lm/server.py:516–521`.
47. *(From SERVER.md)* **"The MLX LM server is not recommended for production as it only implements basic security checks."** `SERVER.md:8–9`.

---

# PART 8 — Session-to-session narrative map (for guide sequencing)

```
298  Meet the Evaluations framework
     ├─ #Playground manual eval  ->  the 5 expectations
     ├─ Evaluation protocol: subject / dataset / Metric+Evaluator / aggregateMetrics / @Test .evaluates
     ├─ Xcode report: navigator -> Evaluations -> row -> assistant editor
     ├─ First hill climb: @Guide(count: 3...8)  ->  100% pass but always 8 tags
     ├─ Fix: add a *scored* metric (TagTotal) next to the pass/fail one
     ├─ Dataset variety (genre/length/category/form/adversarial)  ->  SampleGenerator teaser
     └─ Model judges: ModelJudgeEvaluator, ScoreDimension, ModelJudgePrompt, rationales, splitting dimensions

335  Improve your prompts by hill climbing        (assumes 298)
     ├─ The loop: Develop -> Evaluate -> Analyze, as a science experiment
     ├─ DRIFT: judge vs human disagreement
     ├─ accuracy is insufficient  ->  Cohen's kappa, threshold 0.6
     ├─ Meta-evaluation: align the judge (dataset from Xcode test ATTACHMENT + human ratings)
     ├─ 3 iterations: richer judge prompt -> sharper ScoreDimension descriptions -> few-shot examples
     ├─ Comparison view; promote experimental into baseline to keep one variable
     └─ Hill climb beyond prompts: add a Tool to the feature (tools: [] default)  ->  cliffhanger

299  Create robust evaluations for agentic apps   (assumes 298; resolves 335's cliffhanger)
     ├─ Synthetic data: makeSamples(prompt:dataset:targetCount:)
     ├─ SampleGenerator: sessionProvider / samplingStrategy / validator / run() / samples / invalidSamples
     ├─ Compare 13 vs 100 samples  ->  scores drop  ->  4 hypotheses
     ├─ Tool evals: Tool protocol, TrajectoryExpectation (unordered / ordered / arguments / disallowed / matchers)
     ├─ ToolCallEvaluator drives a LanguageModelSession and captures the transcript
     └─ Synthetic data FOR tool evals (TrajectoryExpectation is @Generable)

232  Agentic AI on Mac with MLX                   (independent track)
     └─ MLX -> MLX-LM -> MLX-LM Server (OpenAI-compatible) -> Agent (Xcode / OpenCode / Pi / script)
        + Neural Accelerators (prefill), continuous batching (subagents), distributed (big models)
```

---

# PART 9 — Source inventory (everything I actually read this session)

**Read in full (assignment):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-298.txt` (290 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-299.txt` (199 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-335.txt` (263 lines)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-232.txt` (150 lines)

**Read in full (cross-check):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/forums/machine-learning-and-ai-topic-evaluations.txt` (30 lines, RSS)
- `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-lm/mlx_lm/SERVER.md` (156 lines)

**Read in part (cross-check):**
- `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-lm/mlx_lm/server.py` — lines 340–369, 505–539, 1700–1871 (+ greps over `tool`, `batch`, `distributed`)
- `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx-lm/README.md` — lines 1–80
- `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/docs/src/usage/launching_distributed.rst` — lines 1–160 (+ grep for `hostfile|RDMA|thunderbolt|backend`)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-246.txt` — lines 100–150
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-241.txt` — lines 100–115 (+ grep)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-319.txt` — lines 58–72 (+ grep)
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-334.txt` — lines 112–132
- `/Volumes/ExtStor/FM and MLX and CoreAI/transcripts/wwdc2026-242.txt`, `wwdc2026-243.txt` — grep hits only

**Directory listings performed:**
- `/Volumes/ExtStor/FM and MLX and CoreAI/docs/` (6 files, all Core AI / Speech — **zero Evaluations coverage**)
- `/Volumes/ExtStor/FM and MLX and CoreAI/repos/` (16 repos), `forums/` (4 files), `guides/` (empty)

**Nothing was fetched from the network.** All grounding is local files read in this session.

---

# PART 10 — Open questions / UNVERIFIED

### High-priority (blocks accurate guide writing)
1. **Exact Swift signatures for everything in Part 6.** No local docs exist. Every code block in Parts 1–3 is a reconstruction. Someone must diff against the real `Evaluations` module interface (e.g. `swift build` against Xcode 27 SDK, or Apple's developer documentation).
2. **`ModelSample` vs `ModelSamples` vs `ModelSampleProtocol`** — three spellings across three sessions. Most likely: a `ModelSampleProtocol` your type conforms to, plus a concrete `ModelSample`. Needs confirmation.
3. **`SampleGenerator` vs `SyntheticGenerator`** — 299:91 is the lone outlier. Confirm the real name.
4. **The results-bundle type name.** 298:90 only says "an evaluation results bundle". Is it `EvaluationResults`? `EvaluationResultsBundle`? What is the exact signature of `aggregateValue`? Does it take a `Metric` or a `String`?
5. **`Metric` construction & measurement values.** Spoken: "passing metric", "failing metric", "a scoring value". Are these `.pass`/`.fail`/`.score(_:)`? Is `Metric` a name-only handle or does it carry the value?
6. **`aggregateMetrics(using:)`** — what is the `using:` argument? An aggregator object? A builder? How do you register a **custom** aggregation (335:127 requires one for Cohen's kappa)?
7. **`.evaluates` trait signature.** Spoken as taking "our evaluation and a notes dictionary." Is it `.evaluates(_:notes:)`? How does the test function receive the results bundle — parameter injection, a global, or `@Test` return?
8. **`ScoreDimension` initializer** — name/description/scale confirmed conceptually; is `scale` a dictionary, an array of `(Int, String)`, or a dedicated `ScoringGuide` type?
9. **`ModelJudgePrompt`** — `instructions` and `evaluationTarget` are named; is `evaluationTarget` a closure, a `@PromptBuilder` block, or a string? How are expected values passed (298:260 says "pass the `expectedTags` as reference")?
10. **`TrajectoryExpectation` initializer** — `unordered:` and `disallowed:` are named; the ordered form's label is unknown (`ordered:`? positional array? a result builder?).
11. **Argument matcher spellings** — `.naturalLanguage` is spoken with a leading dot; `contains`, `oneOf`, `pattern`, `range` are spoken bare. Are they all `.`-prefixed enum cases on a `Matcher` type? What is "and more"?
12. **`ToolCallEvaluator` initializer** — how are the session and tools supplied?
13. **`makeSamples`** — free function or static method? On what type? Does it throw? Exact stream type (`AsyncThrowingStream`?).

### Medium-priority
14. **Does the framework ship a built-in Cohen's kappa / alignment aggregator?** 335 implies **no** ("custom aggregation method"), but a built-in would be a natural addition. Confirm before claiming either way.
15. **Xcode test-attachment format** (335:116). What file type/schema? Is there an API to read it, or is it JSON you parse yourself?
16. **What exactly is stored in `notes:`** and how is it surfaced in the comparison UI? (298:85–86 says it's "helpful later, when we compare across different evaluation runs.")
17. **Which model does `ModelJudgeEvaluator` use by default?** 298 explicitly specifies PCC; is on-device the default?
18. **PCC entitlement requirements when running evaluations in CI / a test target.** `wwdc2026-241.txt:43` mentions an entitlement for `PrivateCloudComputeLanguageModel`; PCC requests "are counted with your user's iCloud account" (`319:113`). **Does running a 100-sample PCC-judged evaluation burn user quota?** This is a real, unanswered practical concern.
19. **Multimodal / vision evaluations** — open forum thread 833822, no answer.
20. **Python support** — open forum thread 833729; 334 implies Swift-only.
21. **tvOS** — omitted from the platform list in 299:2. Confirm it's genuinely unsupported.
22. **Is there a CLI for running evaluations?** 299:15 says sample *generation* can "run from the command line", and 246:125 mentions "the Sample Generation APIs in a command line tool". Nothing says evaluations themselves have a CLI (they run under Swift Testing).
23. **Can `Evaluation` run outside a test target** (e.g. in a command-line tool or CI job that isn't `swift test`)? Unknown.

### MLX-side
24. **M5 Neural Accelerator kernel selection** is not visible in the local mlx snapshot — the "4× matmul, no flags needed" claim is transcript-only.
25. **The exact OpenCode config JSON** shown on screen was never read aloud.
26. **"Pi agent"** (232:48) — unidentified; possibly a transcription of a product name. Needs lookup.
27. **macOS 26.2 as the Thunderbolt-RDMA floor** — transcript-only; not stated in the checked-out `launching_distributed.rst`.
28. **Whether `mlx_lm.server` under `mlx.launch` needs any extra flags** for the agentic case (talk says "everything else just works"; source shows rank 0 alone serves HTTP).
