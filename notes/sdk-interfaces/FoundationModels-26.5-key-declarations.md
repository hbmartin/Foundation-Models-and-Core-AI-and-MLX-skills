# FoundationModels 26.5 SDK interface — extracted declarations
# Primary source: MacOSX26.5.sdk .../FoundationModels.swiftinterface (module version 1.5.2, swift 6.3.2)
# Copied verbatim to FoundationModels-26.5-macos.swiftinterface in this dir. This is the 26.x surface —
# the BEFORE side of the 26->27 migration. 27-only symbols (LanguageModelError, PrivateCloudComputeLanguageModel,
# DynamicProfile, LanguageModelExecutor, ContextOptions, QuotaUsage, BarcodeReaderTool) are ABSENT here (grep-verified 0).

## Tool protocol
796:    public var name: Swift.String
797:    public var description: Swift.String
821:    public var name: Swift.String {
943:  public var description: Swift.String {
951:  public var description: Swift.String {
959:  public var description: Swift.String {
967:  public var description: Swift.String {
975:  public var description: Swift.String {
983:  public var description: Swift.String {
991:  public var description: Swift.String {
999:  public var description: Swift.String {
1007:  public var description: Swift.String {
1015:  public var description: Swift.String {
1023:  public var description: Swift.String {
1184:public protocol Tool<Arguments, Output> : Swift.Sendable {
1185:  associatedtype Output : FoundationModels.PromptRepresentable
1186:  associatedtype Arguments : FoundationModels.ConvertibleFromGeneratedContent
1187:  var name: Swift.String { get }
1188:  var description: Swift.String { get }
1190:  var includesSchemaInInstructions: Swift.Bool { get }

## tokenCount overloads
599:  nonisolated(nonsending) final public func tokenCount(for prompt: some PromptRepresentable) async throws -> Swift.Int
605:  nonisolated(nonsending) final public func tokenCount(for instructions: FoundationModels.Instructions) async throws -> Swift.Int
611:  nonisolated(nonsending) final public func tokenCount(for tools: [any FoundationModels.Tool]) async throws -> Swift.Int
617:  nonisolated(nonsending) final public func tokenCount(for schema: FoundationModels.GenerationSchema) async throws -> Swift.Int
623:  nonisolated(nonsending) final public func tokenCount(for transcriptEntries: some Collection<Transcript.Entry>) async throws -> Swift.Int

## respond / streamResponse (count + first few)
respond/streamResponse decl count: 18
353:  nonisolated(nonsending) final public func respond(to prompt: FoundationModels.Prompt, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<Swift.String>
357:  @_disfavoredOverload nonisolated(nonsending) final public func respond(to prompt: Swift.String, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<Swift.String>
361:  nonisolated(nonsending) final public func respond(options: FoundationModels.GenerationOptions = GenerationOptions(), @FoundationModels.PromptBuilder prompt: () throws -> FoundationModels.Prompt) async throws -> FoundationModels.LanguageModelSession.Response<Swift.String>
365:  nonisolated(nonsending) final public func respond(to prompt: FoundationModels.Prompt, schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<FoundationModels.GeneratedContent>
369:  @_disfavoredOverload nonisolated(nonsending) final public func respond(to prompt: Swift.String, schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<FoundationModels.GeneratedContent>
373:  nonisolated(nonsending) final public func respond(schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions(), @FoundationModels.PromptBuilder prompt: () throws -> FoundationModels.Prompt) async throws -> FoundationModels.LanguageModelSession.Response<FoundationModels.GeneratedContent>
377:  nonisolated(nonsending) final public func respond<Content>(to prompt: FoundationModels.Prompt, generating type: Content.Type = Content.self, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<Content> where Content : FoundationModels.Generable
381:  @_disfavoredOverload nonisolated(nonsending) final public func respond<Content>(to prompt: Swift.String, generating type: Content.Type = Content.self, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) async throws -> FoundationModels.LanguageModelSession.Response<Content> where Content : FoundationModels.Generable
385:  nonisolated(nonsending) final public func respond<Content>(generating type: Content.Type = Content.self, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions(), @FoundationModels.PromptBuilder prompt: () throws -> FoundationModels.Prompt) async throws -> FoundationModels.LanguageModelSession.Response<Content> where Content : FoundationModels.Generable
390:  final public func streamResponse(to prompt: FoundationModels.Prompt, schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) -> sending FoundationModels.LanguageModelSession.ResponseStream<FoundationModels.GeneratedContent>
501:  @_disfavoredOverload final public func streamResponse(to prompt: Swift.String, schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions()) -> sending FoundationModels.LanguageModelSession.ResponseStream<FoundationModels.GeneratedContent>
502:  final public func streamResponse(schema: FoundationModels.GenerationSchema, includeSchemaInPrompt: Swift.Bool = true, options: FoundationModels.GenerationOptions = GenerationOptions(), @FoundationModels.PromptBuilder prompt: () throws -> FoundationModels.Prompt) rethrows -> sending FoundationModels.LanguageModelSession.ResponseStream<FoundationModels.GeneratedContent>

## SamplingMode + GenerationOptions
1309:public struct GenerationOptions : Swift.Sendable, Swift.Equatable {
1313:  public struct SamplingMode : Swift.Sendable, Swift.Equatable {
1317:    public static func random(top k: Swift.Int, seed: Swift.UInt64? = nil) -> FoundationModels.GenerationOptions.SamplingMode
1318:    public static func random(probabilityThreshold: Swift.Double, seed: Swift.UInt64? = nil) -> FoundationModels.GenerationOptions.SamplingMode
1321:  public var sampling: FoundationModels.GenerationOptions.SamplingMode?
1322:  public var temperature: Swift.Double?
1323:  public var maximumResponseTokens: Swift.Int?

## Transcript.Entry + Segment cases
    case instructions(FoundationModels.Transcript.Instructions)
    case prompt(FoundationModels.Transcript.Prompt)
    case toolCalls(FoundationModels.Transcript.ToolCalls)
    case toolOutput(FoundationModels.Transcript.ToolOutput)
    case response(FoundationModels.Transcript.Response)
    case text(FoundationModels.Transcript.TextSegment)
    case structure(FoundationModels.Transcript.StructuredSegment)

## Guardrails
542:  public struct Guardrails : Swift.Sendable {
544:    public static let permissiveContentTransformations: FoundationModels.SystemLanguageModel.Guardrails
