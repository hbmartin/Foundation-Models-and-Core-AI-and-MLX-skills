# Device-only model assets

The generated `DeviceProbes.xcodeproj` copies this directory into the physical-device XCTest
bundle. Put a small portable `.aimodel` here before running the asset-dependent Core AI probes,
then regenerate the project. `CoreAIProbes` auto-selects the model when exactly one is bundled.
If several are present, use `PROBE_AIMODEL_URL` — the desired asset's absolute **host** path;
the device runner resolves the same last path component here. The variable is already declared
(disabled) on the `DeviceProbes` scheme by `device-project.yml`, so regeneration preserves the
declaration: fill in its value and tick its checkbox in the scheme editor for a one-off run (the
tick does not survive `xcodegen generate`), or set the value and `isEnabled: true` in
`device-project.yml` before regenerating. Do not hand-add scheme variables — regeneration wipes
those.

Model assets are ignored by Git. Do not commit weights or generated specializations.
