# Evidence and editorial conventions

## Evidence conventions


`VERIFIED` identifies the cited source or recorded check; it does not imply every device or release was tested. `RECONSTRUCTED` marks an inferred composition or spelling. `GAP` marks an unresolved limitation and its safe default. Runtime claims retain their toolchain, destination, and observation date; community measurements retain their attribution. GitHub closure, released source, and demonstrated remediation are separate observations.

## Editorial conventions

### Version floor

Every guide states its version floor in the first 200 words, and every API is marked with the
earliest OS that has it — **26.0**, **26.2**, **26.4** and **27.0** all matter and are routinely
confused. Version confusion is the single largest source of phantom bug reports in the developer
forums.

### Measurement attribution

Every number is attributed: **Apple-published**, **community-measured**, or **measured by us** —
with hosting mode, hardware/device, OS and runtime build, Xcode build, destination, build
configuration, exceptions, and date. A community benchmark is never presented as an Apple figure.
Where community numbers complicate Apple's claims, both are given. Never carry a measured default
between tool-hosted, app-hosted, and device-hosted processes merely because the runtime build
matches; `contextSize` has already disproved that shortcut.

### Defect state and resolution

Repository state is mechanical evidence, not a resolution claim. Write “PR merged” or “issue
closed” separately from the semantic disposition: `fixed`, `fixed-with-residual`,
`merged-unreleased`, `closed-unfixed`, `closed-unmerged`, `superseded`, `consolidated`, or
`unknown`. A closure without code or maintainer evidence is never described as fixed. Use
`unknown` when the evidence does not establish what happened, and retain the workaround or hazard
until a dated target-specific verification retires it.

### Precedence when sources conflict

1. Headers and SDK sources you can read on disk
2. Apple documentation pages
3. Apple-staff answers on the Developer Forums
4. WWDC session transcripts
5. Community repositories and blog posts

Several WWDC transcript claims are already superseded — custom adapters, PCC eligibility, the
model-tier split. Where a forum answer from Apple staff conflicts with a session, the forum wins,
and the guide says so.

---
