# API & symbol index — Metal TensorOps and Performance Primitives for ML kernels

**33 symbols, of 1200 across the series, that the guide parts in this skill cover — with whether each appears in the captured 26.x / 27.x SDK interfaces.**

> `26.x` / `27.x` aggregate all captured minor versions of each SDK family, including 27.2. A `✓` means the leading type name appears in at least one corresponding captured `.swiftinterface`; it does not establish a minimum SDK or OS version, or imply presence in 27.0. Check the guide's availability notes and the versioned capture before choosing a deployment target. Dotted uppercase type paths must be one contiguous subpath of a qualified or declared type chain. A longer chain may prove any contiguous type subpath, but `::` module qualifiers never become nested types. Lowercase members are not signature-matched — the guides carry the signature-level citations. **Blank in both columns means the spelling is not SDK-confirmed**: package types and C/ObjC-only API legitimately show neither, but so does a reconstruction. A symbol absent from this page may still be covered elsewhere in the series — the full index is at https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills/blob/main/guides/API-INDEX.md. Sliced on 2026-10-30; regenerate with `./scripts/build-skills.sh` rather than editing by hand.

## CoreAI  <sub>1 symbol</sub>

| Symbol | 26.x | 27.x | Covered in |
|---|:-:|:-:|---|
| `AIModel` |  | ✓ | [11.README](part-11-metal-and-tensorops/README.md) |

## Metal/MPP  <sub>13 symbols</sub>

| Symbol | 26.x | 27.x | Covered in |
|---|:-:|:-:|---|
| `Metal.framework` |  | ✓ | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `MetalParameter` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MetalPerformancePrimitives` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MetalPerformancePrimitives.framework` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `MTL4MachineLearningCommandEncoder` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLSize` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensor` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.README](part-11-metal-and-tensorops/README.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensor.auxiliaryPlanes` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensorAuxiliaryPlaneDescriptor` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensorDataType` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.README](part-11-metal-and-tensorops/README.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensorDescriptor` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `MTLTensorDescriptor.auxiliaryPlanes` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.README](part-11-metal-and-tensorops/README.md) |
| `MTLTensorUsageMachineLearning` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |

## other  <sub>19 symbols</sub>

| Symbol | 26.x | 27.x | Covered in |
|---|:-:|:-:|---|
| `CoordType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `DstElementType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `E8M0` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `ElementType` | ✓ | ✓ | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `LeftElementType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `LeftOperandType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `NaN` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `OtherIterator` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `QuantizationSpec` |  |  | [11.README](part-11-metal-and-tensorops/README.md) |
| `QuantizedLinear` |  |  | [11.README](part-11-metal-and-tensorops/README.md) |
| `RightElementType` |  |  | [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `RightOperandType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `SrcElementType` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md) |
| `TM` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `TN` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `TorchMetalKernel` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md), [11.README](part-11-metal-and-tensorops/README.md) |
| `TypeError` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `ValueError` |  |  | [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
| `Xcode.app` |  |  | [11.README](part-11-metal-and-tensorops/README.md), [11.1](part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md), [11.2](part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md) |
