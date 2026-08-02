# WWDC26 Session 328 — "Explore numerical computing in Swift with MLX"

**Harvested 2026-08-02** from `https://developer.apple.com/videos/play/wwdc2026/328/`
(direct WebFetch; full transcript + Apple's published code-sample block, both complete).

Speaker: **David Koski, MLX Swift.**

> 🚨 **Corpus status.** Session 328 is **listed on
> `https://developer.apple.com/wwdc26/guides/machine-learning/` as one of the 18 ML-track
> sessions**, but it is the **only one of the 18 with no transcript in `transcripts/`** and the
> only one with no reference anywhere in `guides/`. The earlier sweep
> (`notes/transcripts/missing-sessions.md`) closed seven gaps and reported "Sessions NOT obtained:
> None" — that was true of its seven *targets*, but 328 was never on the target list. This is a
> genuine miss, not a re-fetch.
>
> ⚠️ **Partial mitigation already in the repo.** The *code* from this session is already on disk:
> `repos/ml-explore__mlx-swift-examples/Numerical/` contains `Mandelbrot`, `HeatTransfer` and
> `CurveFit` (added upstream in commit `70eaaac`, 2026-06-09, message literally
> *"new files -- WWDC26 numerical computing examples"*), and Part 13 already cites
> `Numerical/*/Renderer` and `HeatTransfer/Renderer.render()`. **What was missing is the
> narration** — the algorithm rationale, the SOR derivation, the performance claims, and the
> framing of MLX Swift's place among Accelerate/BNNS/MPS/Swift Numerics. That is what this file
> adds.

---

## 1. Positioning — when to use MLX Swift (quotable, Part 13 §1 / Part 1)

Apple's own comparison of the numerical-computing options on Apple platforms:

| Framework | Apple's one-line characterisation (verbatim) |
|---|---|
| **Accelerate** | "hand-tuned vector primitives on the CPU" |
| **BNNS** | "the building block layer for neural networks" |
| **Metal Performance Shaders** | "direct access to GPU kernels" |
| **Swift Numerics** | "adds a Complex type and generic numeric protocols" |
| **MLX Swift** | "If your primary goal is writing mathematical code with an eye for performance, MLX Swift is a great solution." |

The differentiator Apple leans on is *legibility*, not raw speed:

> "The code you write looks like the math you are implementing without the programming overhead
> of some of the lower level libraries or the detailed bookkeeping required when manipulating
> arrays in plain Swift."

And the NumPy lineage is stated outright: "MLX Swift uses n-dimensional arrays as the central
abstraction, like NumPy and many others before it. In fact if you've used NumPy, the API will look
very familiar. **Most NumPy code can be translated to MLX Swift with minimal changes.**"

**Licence, stated on stage:** "mlx-swift and the entire MLX ecosystem are all open source with an
**MIT license**."

## 2. The four-front-end framing (useful for Part 14, bridges)

> "MLX isn't only Swift. It's **one framework with four front-ends: Swift, Python, C++, and C**.
> Third parties have built even more front-ends if you have needs beyond that. They share the same
> concepts, the same operations, and the same lazy-evaluation model. The concepts and patterns
> transfer across them with minimal changes. **So you can prototype in Python and ship in Swift.**"

Ecosystem packages named: `mlx-swift` (core), `mlx-swift-lm` (LM implementations),
`mlx-swift-examples` (examples — "Examples based on this session will be posted there"), and on
the Python side `mlx-lm` and `mlx-vlm`.

## 3. Code samples (verbatim, Apple's timestamps and chapter labels)

### 3:04 — Power iteration *(chapter: MLX Swift)*

```swift
import MLX
let n = 100
let steps = 10
let B = MLXRandom.normal([n, n])
var v = MLXRandom.normal([n])

// get symmetric matrix A = Bᵀ + B
let A = B.T + B

// Power iteration → top eigenvector of A.
//   v ← A v / ‖A v‖
for _ in 0 ..< steps {
    let Av = matmul(A, v)
    v = Av / norm(Av)
    eval(v)
}

// recover the eigenvalue.
//   λ = vᵀ A v
let lambda = matmul(matmul(v.T, A), v)

print(lambda)
```

> ⚠️ **The lazy-evaluation rule this sample exists to teach:** "Operations on MLX array objects
> build a compute graph, and nothing runs until you call eval or read a value. **In a loop like
> this, we call eval each step so the graph stays small.**" Omitting `eval` inside a loop is a
> silent memory/latency footgun — the program still produces the right answer, it just builds an
> unbounded graph. Part 12's `01-core-fundamentals.md` covers lazy eval from the Python docs;
> this is the same rule stated for Swift with a worked loop. **`SILENT-FAILURES.md` candidate.**
>
> Apple also notes the *converse* use of laziness: "Lazy evaluation is also what powers MLX's
> function transformations, like `grad` for automatic differentiation."

Also mentioned: "if you actually need all the eigenvalues and eigenvectors of a matrix, the MLX
Swift **linear algebra package** has functions for that too."

### 5:09 — Mandelbrot, plain Swift (the anti-pattern baseline) *(chapter: Mandelbrot)*

```swift
// Plain Swift, scalar-at-a-time
var counts = Array2D<Int>(width: w, height: h)

for y in 0 ..< h {
    for x in 0 ..< w {
        let c = Complex(xMin + Float(x) * xStep, yMin + Float(y) * yStep)
        var z = Complex<Float>.zero
        var limit = maxIterations
        for i in 0 ..< maxIterations {
            z = z * z + c
            if z.lengthSquared > radiusSquared {
                limit = i
                break
            }
        }
        counts[x, y] = limit
    }
}
```

### 5:27 — Mandelbrot, MLX Swift *(chapter: Mandelbrot)*

```swift
// Compute the Mandelbrot set on a grid of complex numbers
import MLX

let x = linspace(Float(-2.0), 0.5, count: w)
let y = linspace(Float(-1.25), 1.25, count: h).reshaped(h, 1)
let c = x + y.asImaginary()

var z = MLXArray.zeros(like: c)
var counts = MLXArray.zeros(c.shape, dtype: .int16)

for _ in 0 ..< maxIterations {
    z = z * z + c                       // iterate z ← z² + c
    counts = counts + (abs(z) .< 2)     // count bounded iterations
}
```

**Performance claim, hedged by Apple itself:** "It runs faster on the GPU, processing all points
in parallel. **How much faster depends on the exact algorithm, but 10x faster is certainly
possible.**" Note this is a *possibility* claim about an embarrassingly-parallel workload with no
measurement published — cite it as such, not as a benchmark. Part 15's honest-benchmarking guide
should treat it as an illustrative upper bound.

Note the API details worth indexing: `linspace`, `.asImaginary()`, `MLXArray.zeros(like:)`,
`.zeros(_:dtype:)`, and the **element-wise comparison operator `.<`** whose Bool result is summed
directly into an int array.

### 7:27 — Jacobi iteration via `conv2d` *(chapter: Heat distribution)*

```swift
// Jacobi iteration: average the four neighbors

// Convolution weights
let kernel = MLXArray(converting: [
    0,    0.25, 0,
    0.25, 0,    0.25,
    0,    0.25, 0,
]).reshaped(1, 3, 3, 1)

// Initial value
var temperature = heatSources

// Run this in a loop until convergence
let next = conv2d(temperature, kernel, padding: 1)
temperature = which(heatMask, heatSources, next)
```

The pedagogical point Apple makes: a neighbourhood stencil applied identically at every point
**is** a convolution — "The math said average the four neighbors and we implemented that as a
single call to `conv2d`." Boundary conditions are an element-wise ternary via `which(_:_:_:)`.

### 9:17 — Successive Over-Relaxation *(chapter: Faster convergence with SOR)*

```swift
// Successive Over-Relaxation: blend the previous and next state
let ω: Float = 2.0 / (1.0 + sin(Float.pi / Float(max(M, N))))

let redMask   = checkerboard(rows: M, cols: N, phase: 0)
let blackMask = checkerboard(rows: M, cols: N, phase: 1)

// Update red cells using black neighbors
let sorRed  = ω * conv2d(temperature, kernel, padding: 1) + (1 - ω) * temperature
temperature = which(redMask, sorRed, temperature)
temperature = which(heatMask, heatSources, temperature)

// Update black cells using (now-updated) red neighbors
let sorBlack = ω * conv2d(temperature, kernel, padding: 1) + (1 - ω) * temperature
temperature  = which(blackMask, sorBlack, temperature)
temperature  = which(heatMask, heatSources, temperature)
```

**The algorithmic content, which is the actually-valuable part of this session:**

- Jacobi converges in **O(N²)** iterations for an N-per-side grid ("Heat can move one cell at a
  time"); SOR with the optimal ω converges in **O(N)**.
- The optimal ω is closed-form: `ω = 2 / (1 + sin(π / max(M, N)))`.
- **MLX has no in-place update**, so the in-place effect SOR requires is faked with a **red/black
  checkerboard**: "MLX typically produces new arrays rather than updating in place, but a
  red/black checkerboard pattern where alternating cells are processed can be used to compute new
  values, giving the same effect."
- Measured-by-eye result: "I had to **slow SOR down by a factor of 100** just to make it visible"
  next to Jacobi. Again — a demo statement, not a benchmark.

> This red/black-checkerboard-instead-of-in-place trick is a **general MLX idiom** for any
> Gauss-Seidel-shaped algorithm, and it is not in the corpus. Good addition to Part 13 and to
> Part 12's fundamentals (the same constraint applies in Python MLX).

### 11:13 — Curve fitting with `grad` *(chapter: Curve fitting)*

```swift
// Define a loss, then optimize it with autodiff
// x, y: data points as MLXArrays
func f(_ θ: MLXArray) -> MLXArray {
    θ[0] + θ[1] * x + θ[2] * x ** 2
}

func loss(_ θ: MLXArray) -> MLXArray {
    mean((f(θ) - y) ** 2)
}

var θ = zeros([numParams])
let gradLoss = grad(loss)

for _ in 0 ..< steps {
    let g = gradLoss(θ)         // ∇L(θ)
    θ = θ - learningRate * g    // parameter update
    eval(θ)                     // force evaluation
}
```

Apple's framing: "This is the same core idea behind **training every ML model**, just on a smaller
scale." And the same `eval`-in-loop rule appears again: "call `eval` to flush the computation graph
each iteration so it doesn't grow without bound."

Escape hatches named: for this *specific* polynomial case "we could have used **QR** from the
linear algebra package to fit the curve directly"; and beyond plain gradient descent, "MLX has a
suite of optimization algorithms like **SGD, Adam, RMSprop**, and more."

## 4. The op inventory Apple enumerated

"Linear algebra, FFTs, N-dimensional convolutions, Reductions, Scans, Indexing, Random number
generation, and many more."

## 5. Suggested use in the guides

1. **Part 13 (`mlx-swift`)** — the session is the missing narrative source for the `Numerical/`
   examples Part 13 already cites. Add the citation, the SOR/red-black idiom, and the
   `eval`-in-loop rule.
2. **Part 12 §1 (core fundamentals)** — the "no in-place update → red/black checkerboard" workaround
   is language-agnostic and belongs alongside the existing indexing/in-place-update material.
3. **Part 14 (bridges)** — "one framework with four front-ends … prototype in Python and ship in
   Swift" is the cleanest first-party statement of the Python↔Swift porting story.
4. **Part 15 (honest benchmarking)** — both perf claims here ("10x possible", "100× slowdown to
   make SOR visible") are unmeasured demo statements. They are good examples of the genre the
   guide warns about, and should be cited with that caveat rather than as numbers.
5. **`transcripts/`** — a `wwdc2026-328.txt` prose-only file should be added to match the existing
   corpus convention (code lives in the notes layer, per
   `notes/transcripts/missing-sessions.md`'s provenance rule).
