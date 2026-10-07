# Decisions that still affect implementation

Keep current API guidance in the owning guides. Retain these distinctions when editing them:

- A Siri-enablement availability defect is not a permanent product gate. Prefer the Apple acknowledgement in [App Intents research](web/app-intents-siri-schemas.md).
- App entities and searchable items share the Core Spotlight index; delegate behavior still needs its own evidence. See the [App Intents research](web/app-intents-siri-schemas.md).
- TensorOps version floors are per feature. Use the SDK headers and Tech Talk 111432, rather than a blanket 26.2 floor. MLX format structs are not Metal data types. See [kernel research](repos/mlx-tensorops-kernels.md).
- Structured generation requires backend capabilities, including logits access. Attribute BYO-backend limitations to the tested package, not every Core AI model. See [backend research](repos/john-rocky-models.md).
- Prefix-cache trimming returns the retained prefix; hybrid recurrent state may prevent trimming. Performance numbers remain fixture measurements, not guarantees. See [backend research](repos/john-rocky-models.md).
- Split-model ANE preferences belong to the optional loader policy, not a Core AI framework routing contract. Image orientation and inference caching remain caller responsibilities. See [non-LLM package research](repos/coreai-models-nonllm.md).
- Compiling Apple samples outrank reconstructed signatures. Older sample projects retain their own OS floors. See [sample evidence](web/apple-sample-code.md).

Use [current state](current-state.json) for environment identity and [the Instruments task](../probes/INSTRUMENTS-RECORDING.md) for the remaining manual UI capture. Closed planning and review records are recoverable from Git.
