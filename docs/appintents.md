---
title: App Intents updates
description: Learn about important changes in App Intents.
source: https://developer.apple.com/documentation/updates/appintents
timestamp: 2026-07-29T15:14:40.374Z
---

**Navigation:** [Updates](/documentation/updates)

**Article**

# App Intents updates

> Learn about important changes in App Intents.

## Overview

Browse notable changes in [App Intents](/documentation/AppIntents).

## June 2026

### Apple Intelligence

- Integrate your app with Apple intelligence by conforming your app intents, app entities, and app enums to an app schema in one of the [App schema domains](/documentation/AppIntents/app-schema-domains).
- Indicate that your app entities have identifiers that remain stable across devices by adopting [`SyncableEntity`](/documentation/AppIntents/SyncableEntity), so people can continue a task on another device.
- Prompt for confirmation before destructive or sensitive actions on shared or publicly accessible entities by adopting [`OwnershipProvidingEntity`](/documentation/AppIntents/OwnershipProvidingEntity) and returning an [`EntityOwnership`](/documentation/AppIntents/EntityOwnership) value.
- Enable Apple Intelligence to suggest media-related entities like songs or albums during workouts and similar contexts with [`RelevantEntities`](/documentation/AppIntents/RelevantEntities).
- Bridge your app entities to system intent value types by using [`IntentValueRepresentation`](/documentation/AppIntents/IntentValueRepresentation) in your entity’s `transferRepresentation` property.

### App intents

- Let people perform App Shortcuts, custom shortcuts, system actions, or open another app from interactive widgets with [`RunSystemShortcutIntent`](/documentation/AppIntents/RunSystemShortcutIntent).
- Extend an app intent’s background runtime by adopting [`LongRunningIntent`](/documentation/AppIntents/LongRunningIntent) and calling [`performBackgroundTask(options:operation:)`](/documentation/AppIntents/LongRunningIntent/performBackgroundTask(options:operation:)) with a [`LongRunningTaskOptions`](/documentation/AppIntents/LongRunningTaskOptions) value, reporting progress as the task runs.
- Handle cancellation cleanup gracefully by adopting [`CancellableIntent`](/documentation/AppIntents/CancellableIntent). Inspect [`IntentCancellationReason`](/documentation/AppIntents/IntentCancellationReason) to distinguish a deliberate cancellation from a timeout.
- Reverse the effect of an app intent’s action by adopting [`UndoableIntent`](/documentation/AppIntents/UndoableIntent).
- Specify whether your app intent runs in the foreground, the background, or both by setting the `supportedModes` property to an [`IntentModes`](/documentation/AppIntents/IntentModes) value, then consult [`currentMode`](/documentation/AppIntents/IntentSystemContext/currentMode) inside `perform()` to adapt your code at runtime.
- Tell the system which target may perform your app intent or entity query — the main app, the App Intents extension, or a widget extension — by setting the `allowedExecutionTargets` property to an [`IntentExecutionTargets`](/documentation/AppIntents/IntentExecutionTargets) option set.

### App entities

- Refer to a large set of entities efficiently using [`EntityCollection`](/documentation/AppIntents/EntityCollection), which stores only entity identifiers and resolves the full [`AppEntity`](/documentation/AppIntents/AppEntity) instances on demand. Use the type for an app intent parameter to avoid resolving every identifier during parameter resolution.
- Define union-type Shortcuts parameters with rich picker UI and custom metadata by adopting [`AppUnionValue`](/documentation/AppIntents/AppUnionValue) on the type the `@UnionValue` macro generates, along with the [`AppUnionValueCasesProviding`](/documentation/AppIntents/AppUnionValueCasesProviding) cases enum.
- Have the system retrieve indexed entities by identifier from the Spotlight index by adopting [`IndexedEntityQuery`](/documentation/AppIntents/IndexedEntityQuery).

### Errors

- Provide a localized description for failures by initializing an [`AppIntentError`](/documentation/AppIntents/AppIntentError) with `init(description:)`, or wrap an existing error that conforms to [`CustomLocalizedStringResourceConvertible`](/documentation/Foundation/CustomLocalizedStringResourceConvertible).

## June 2025

- Create app intents that conform to [`SnippetIntent`](/documentation/AppIntents/SnippetIntent) to display an interactive snippet.
- Make app entities available in Spotlight that conform to [`IndexedEntity`](/documentation/AppIntents/IndexedEntity) and use the `@ComputedProperty(indexingKey:)` or `@Property(indexingKey:)` Swift macros for attributes you want to add to the Spotlight index.
- Integrate your app with visual intelligence by providing app entities to the system using an [`IntentValueQuery`](/documentation/AppIntents/IntentValueQuery).
- Create an [`AppEntity`](/documentation/AppIntents/AppEntity) that conforms to the [`Transferable`](/documentation/CoreTransferable/Transferable) protocol and associate the app entity with a [`NSUserActivity`](/documentation/Foundation/NSUserActivity) using the activity’s [`appEntityIdentifier`](/documentation/Foundation/NSUserActivity/appEntityIdentifier) property to make onscreen content available to Siri without adopting an assistant schema.

## November 2024

### Siri and Apple Intelligence

- Make onscreen content available to Siri and Apple Intelligence by describing it as an [`AppEntity`](/documentation/AppIntents/AppEntity) and adopting an assistant schema. Additionally, adopt the [`Transferable`](/documentation/CoreTransferable/Transferable) protocol, and associate the app entity with a [`NSUserActivity`](/documentation/Foundation/NSUserActivity) using the activity’s [`appEntityIdentifier`](/documentation/Foundation/NSUserActivity/appEntityIdentifier) property.

## June 2024

### System integration

- Integrate your app with Siri and Apple Intelligence using [App schema domains](/documentation/AppIntents/app-schema-domains).
- Use [`ControlConfigurationIntent`](/documentation/AppIntents/ControlConfigurationIntent) and [WidgetKit](/documentation/WidgetKit) to allow users to put controls on the Lock Screen or in Control Center.
- Create a locked camera capture extension for your app and implement a [`CameraCaptureIntent`](/documentation/AppIntents/CameraCaptureIntent) to allow people to capture photos and videos from controls or the Action button.
- Create app intents that capture audio by implementing [`AudioRecordingIntent`](/documentation/AppIntents/AudioRecordingIntent).
- Allow people to find app entities in Spotlight by adopting the [`IndexedEntity`](/documentation/AppIntents/IndexedEntity) protocol.

### Content sharing

- Make it possible to share and transfer data you describe as [App entities](/documentation/AppIntents/app-entities) by conforming to [`Transferable`](/documentation/CoreTransferable/Transferable).
- Receive content other apps make available with app intents by using [`IntentFile`](/documentation/AppIntents/IntentFile) for your app intent parameters.
- Describe the file that stores your app intent data using [`FileEntity`](/documentation/AppIntents/FileEntity).

### General

- Provide additional information about errors with [`AppIntentError.PermissionRequired`](/documentation/AppIntents/AppIntentError/PermissionRequired), [`AppIntentError.Unrecoverable`](/documentation/AppIntents/AppIntentError/Unrecoverable), and [`AppIntentError.UserActionRequired`](/documentation/AppIntents/AppIntentError/UserActionRequired).
- Pass a condition to [`requestConfirmation(conditions:actionName:dialog:)`](/documentation/AppIntents/AppIntent/requestConfirmation(conditions:actionName:dialog:)) to only require user confirmation if a person’s context meets the provided condition.
- Use [`URLRepresentableIntent`](/documentation/AppIntents/URLRepresentableIntent), [`URLRepresentableEntity`](/documentation/AppIntents/URLRepresentableEntity), and [`URLRepresentableEnum`](/documentation/AppIntents/URLRepresentableEnum) to represent your app intents, app entities, and app enums as universal links that you use to provide deep links to your app’s content.
- Define a set of types for an intent parameter using the [`UnionValue()`](/documentation/AppIntents/UnionValue()) macro to create flexible app intents because a parameter can be of one of several pre-defined union types.
- Create entities that have just one singular instance with [`UniqueAppEntity`](/documentation/AppIntents/UniqueAppEntity) and the corresponding [`UniqueAppEntityQuery`](/documentation/AppIntents/UniqueAppEntityQuery). For example, to provide an app intent for app settings that appear in your app or in System Settings, create a singleton entity that encapsulates all settings as properties. Use it in the app intent that offers actions to change your app’s settings.

## Technology and frameworks

- [Accelerate updates](/documentation/updates/accelerate)
- [Accessibility updates](/documentation/updates/accessibility)
- [ActivityKit updates](/documentation/updates/activitykit)
- [AdAttributionKit Updates](/documentation/updates/adattributionkit)
- [App Clips updates](/documentation/updates/appclips)
- [AppKit updates](/documentation/updates/appkit)
- [Apple Intelligence updates](/documentation/updates/apple-intelligence)
- [AppleMapsServerAPI Updates](/documentation/updates/applemapsserverapi)
- [Apple Pencil updates](/documentation/updates/applepencil)
- [ARKit updates](/documentation/updates/arkit)
- [Audio Toolbox updates](/documentation/updates/audiotoolbox)
- [AuthenticationServices updates](/documentation/updates/authenticationservices)
- [AVFAudio updates](/documentation/updates/avfaudio)
- [AVFoundation updates](/documentation/updates/avfoundation)
- [Background Tasks updates](/documentation/updates/backgroundtasks)

---

*Extracted by [sosumi.ai](https://sosumi.ai) - Making Apple docs AI-readable.*
*This is unofficial content. All documentation belongs to Apple Inc.*
