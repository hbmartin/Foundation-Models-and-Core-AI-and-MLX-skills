# Device-only model assets

The generated `DeviceProbes.xcodeproj` copies this directory into the physical-device XCTest
bundle. Put a small portable `.aimodel` here before running the asset-dependent Core AI probes,
then regenerate the project. `CoreAIProbes` auto-selects the model when exactly one is bundled.
If several are present, set `PROBE_AIMODEL_URL` to the desired asset's absolute **host** path in a
scheme environment variable; the device runner resolves the same last path component here.

Model assets are ignored by Git. Do not commit weights or generated specializations.
