// swift-tools-version: 6.2
// Runtime-probe package for the Apple on-device AI guide series.
//
// Platform floors are deliberately 26: the package must BUILD AND TEST on any
// 26.x-or-later host (it was authored on macOS 26.5.2; the authoring host moved
// to macOS 27 beta 5 on 2026-08-17). Every probe that needs
// an OS 27 runtime guards its body with `if #available(macOS 27.0, iOS 27.0, *)`
// and records "SKIPPED: needs OS 27" (XCTSkip) otherwise. Frameworks that do not
// exist on 26 (CoreAI, Evaluations) are compile-guarded with `#if canImport(...)`
// so the package still builds against an SDK that lacks them.
import PackageDescription

let package = Package(
    name: "Probes",
    platforms: [
        .macOS(.v26),
        .iOS(.v26),
    ],
    targets: [
        .target(name: "ProbeSupport"),
        .testTarget(
            name: "ProbesTests",
            dependencies: ["ProbeSupport"]
        ),
    ]
)
