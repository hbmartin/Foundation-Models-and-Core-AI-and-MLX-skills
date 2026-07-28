# What to run on a macOS 27 / Xcode 27 machine

This machine is **macOS 26.5.2 / Xcode 26.6 / SDK 26.5**. The gaps below are unresolvable here.
Each closes one or more 🔴 GAP boxes currently shipping in the guides.

Run what you can, paste the raw output back. Partial is fine — every item is independent.

---

## 1. The `fm` CLI — closes the largest gap in the series

Guide `part-05/references/02-fm-cli-and-python-sdk.md` currently says, honestly, that nobody has run
this. Only semantic option names were spoken aloud in WWDC26 session 334.

```bash
fm --help
fm respond --help
fm chat --help
fm schema --help
fm schema object --help
# and any other subcommands `fm --help` reveals:
fm <subcommand> --help
```

Inside an interactive session, the slash-command list:
```bash
fm chat
# then type: /help      (and /?  if /help does nothing)
```

---

## 2. `coreai-build` — closes gaps in guides 7.2, 10.3 and Part 15

Four flags are attested from an Apple doc article. The architecture codes come from a community
source and are unverified. Unknown whether subcommands beyond `compile` and `inspect` exist.

```bash
xcrun coreai-build --help
xcrun coreai-build compile --help
xcrun coreai-build inspect --help
```

Specifically needed: the full `--preferred-compute` value list, and the enumeration of device
architecture codes (we have only `h18p`, from a blog, unconfirmed).

---

## 3. Xcode 27 Instruments lane names — closes gaps in guides 5.1 and 10.2

WWDC26 session 243 says the Foundation Models template has **6 lanes**. Only two are named anywhere
in the entire corpus: *Instructions* and *Model Inference*. The agents refused to invent the other
four, which is correct but leaves the guide thin.

1. Open Instruments 27 → template chooser.
2. Screenshot or list the lane names for the **Foundation Models** template (all 6).
3. Same for the **Core AI** template — its lane and metric names come only from prose.

---

## 4. Core AI error types — closes a gap in guides 7.1 and 7.2

No inference, specialization or cache error type appears among the 312 indexed Core AI symbols.
`AssetError` covers asset operations only. So what `AIModel.init`, `loadFunction`, `run` and cache
deletion actually throw is unknown — which means readers cannot write correct `catch` blocks.

```bash
# Dump the shipped interface:
xcrun --sdk macosx swift-api-digester --dump-sdk -module CoreAI -o /tmp/coreai.json 2>/dev/null
# Or simply locate and open the generated interface:
find "$(xcrun --sdk macosx --show-sdk-path)" -name 'CoreAI.swiftinterface' -o -name 'CoreAI.swiftmodule' | head
```

---

## 5. The FoundationModels interface — closes ~8 gaps across Parts 2, 3 and 4

Several signature questions would collapse at once: which `LanguageModelSession.init(model:...)`
overloads are real; the `tokenCount(for:)` overload set; whether a `Profile(model:)` initialiser
exists at all (only the `.model(_:)` modifier appears in compiling code); the full `QuotaUsage.Status`
and `UnavailableReason` case lists; and the `Tool.includesSchemaInInstructions` default.

```bash
find "$(xcrun --sdk macosx --show-sdk-path)" -path '*FoundationModels*' -name '*.swiftinterface' | head
# then just cat the arm64 one
```

Same for Vision, which would close the `BarcodeReaderTool` / `OCRTool` `Arguments`/`Output`
associated-type gap:
```bash
find "$(xcrun --sdk macosx --show-sdk-path)" -path '*Vision*' -name '*.swiftinterface' | head
```

---

## 6. MetalPerformancePrimitives on the 27 SDK — confirms the Part 11 version story

We verified against the **26.6** headers that scale planes do not exist and that the dtype set is
int4/int8 only. Worth confirming nothing changed in 27, and resolving the availability discrepancy:
Tech Talk 111432's ladder is 26.0 / 26.1 / 26.3 / 26.4 and never mentions 26.2, while the 26.6
headers annotate the symbol as 26.2.

```bash
grep -rn "available" "$(xcrun --sdk macosx --show-sdk-path)"/System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers/ | grep -i tensor | head -40
grep -rniE "scale|plane|e8m0|fp8|fp4|int2" "$(xcrun --sdk macosx --show-sdk-path)"/System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers/ | head
```

---

## 7. Two device tests (only if you have a 27 device handy)

- **`AIModelCache` deletion semantics.** Apple's own docs contradict themselves: the reference page
  says deleting a referenced entry throws; the caching article says deletion is deferred until the
  `AIModel` deallocates. One test settles it.
- **On-device `contextSize`.** TN3193 says 4096. A third-party app's source comment claims device
  probing returns 8192. Print `SystemLanguageModel().contextSize` on a real 27 device.

---

## Not needed from you

Everything else is either resolved or resolvable from material already on disk. The research corpus
is ~85,000 lines and the guides are written against it; these seven items are the residue that
genuinely requires the newer toolchain.
