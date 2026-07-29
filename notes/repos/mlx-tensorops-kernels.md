# MLX + Metal TensorOps (MPP) — verified API reference

**Purpose.** WWDC26 session 330 ("Metal tensors and TensorOps") described a set of APIs *in speech only*.
Two planned guides rested on spellings reconstructed from that narration. This note replaces every one of
those guesses with a spelling quoted from a file on this machine, each with a `path:LINE` citation.

**Date of investigation:** 2026-07-27.

---

## HEADLINE CORRECTION TO THE BRIEF

The task brief asserted: *"NONE of this is verifiable in the Xcode 26.6 SDK we have."*

**That is false.** The complete, authoritative, commented Metal-side TensorOps headers ship inside
Xcode 26.6 (Build 17F113) at:

```
/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/
  System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers/
```

They were missed because a search for the *framework* under `Toolchains/` or for `MTLTensor` finds
nothing — the framework lives under `Platforms/.../SDKs/MacOSX.sdk/System/Library/Frameworks/`, and the
Metal *language* half (`metal_tensor`, `metal_cooperative_tensor`, `__exec/units.h`) lives in a
**cryptex-mounted Metal toolchain**, not in Xcode.app at all:

```
/var/run/com.apple.security.cryptexd/mnt/com.apple.MobileAsset.MetalToolchain-v17.6.109.0.iAeIa2/
  Metal.xctoolchain/usr/metal/32023/lib/clang/32023.883/include/metal/
```

So this note has **two independent sources of truth**, and they agree:

1. **Apple's shipping headers** — the normative declarations (~14,300 lines).
2. **MLX's shipping kernels** — a real, compiling, in-production call site.

Where they disagree with session 330's narration, the narration is wrong (or described an unreleased
capability). Section 12 gives the verdict table.

---

## Table of contents

- [0. Source inventory](#0-source-inventory)
- [1. Compressed verdict table](#1-compressed-verdict-table)
- [2. `matmul2d_descriptor` — the real signature](#2-matmul2d_descriptor--the-real-signature)
- [3. `matmul2d` — the operation class](#3-matmul2d--the-operation-class)
- [4. Execution scopes — `execution_simdgroup` is an alias](#4-execution-scopes--execution_simdgroup-is-an-alias)
- [5. Cooperative tensors](#5-cooperative-tensors)
- [6. Reductions: `reduce_rows`, `map_iterator`, `is_iterator_compatible`](#6-reductions-reduce_rows-map_iterator-is_iterator_compatible)
- [7. Tensor construction: `tensor_handle` / `tensor_offset` / `tensor_inline`](#7-tensor-construction-tensor_handle--tensor_offset--tensor_inline)
- [8. Data types — the enum that settles the quantization question](#8-data-types--the-enum-that-settles-the-quantization-question)
- [9. What MLX actually does (nax.h walkthrough)](#9-what-mlx-actually-does-naxh-walkthrough)
- [10. Quantization: scale planes vs hand-dequant — ANSWERED](#10-quantization-scale-planes-vs-hand-dequant--answered)
- [11. NAX / M5 gating: compile-time and runtime](#11-nax--m5-gating-compile-time-and-runtime)
- [12. Full verdict table vs session 330](#12-full-verdict-table-vs-session-330)
- [13. Dating the work + upstream PRs](#13-dating-the-work--upstream-prs)
- [14. Open questions / UNVERIFIED](#14-open-questions--unverified)
- [15. What this changes for a guide author](#15-what-this-changes-for-a-guide-author)

---

## 0. Source inventory

Everything below is quoted from one of these. Nothing is from memory.

### A. Apple SDK — MPP TensorOps (normative, Metal-side)

Root: `/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers/`

| File | Lines | Role |
|---|---:|---|
| `MetalPerformancePrimitives.h` | 12 | Umbrella; includes the two op headers |
| `MPPTensorOpsMatMul2d.h` | 642 | **Public API.** `matmul2d_descriptor`, `matmul2d`, `reduce_rows`, `reduce_columns`, `is_iterator_compatible`, `reduction_operation`. ~320 lines of doc comment with worked examples. |
| `MPPTensorOpsConvolution2d.h` | 177 | Public API for `convolution2d` |
| `__impl/MPPTensorOpsAvailability.h` | 12 | Deployment-target macro |
| `__impl/MPPTensorOpsBase.h` | 28 | `__tensor_ops_detail::op` base class |
| `__impl/MPPTensorOpsTypes.h` | 150 | **`__tensor_ops_datatype` enum**, address-space enum, descriptor-type enum, `dynamic_length` |
| `__impl/MPPTensorOpsTraits.h` | 135 | Type traits; the `#include` list that reveals the Metal-language dependencies |
| `__impl/MPPTensorOpsUtility.h` | 106 | `__type_to_tensor_ops_datatype<T>` specializations |
| `__impl/MPPTensorOpsMatMul2dImpl.h` | 8963 | Implementation; the exhaustive dtype-combination dispatch |
| `__impl/MPPTensorOpsConvolution2dImpl.h` | 4914 | Implementation |

Also present (identical framework) under `iPhoneOS.sdk`, `AppleTVSimulator.sdk`, `iPhoneSimulator.sdk`,
and `/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk`.

Module map at `.../MetalPerformancePrimitives.framework/Modules/module.modulemap`:

```
framework module MetalPerformancePrimitives {
    umbrella header "MetalPerformancePrimitives.h"

    export *
    module * { export * }
}
```

### B. Metal toolchain — the language-level tensor types (cryptex mount)

Root: `/var/run/com.apple.security.cryptexd/mnt/com.apple.MobileAsset.MetalToolchain-v17.6.109.0.iAeIa2/Metal.xctoolchain/usr/metal/32023/lib/clang/32023.883/include/metal/`

| File | Lines | Role |
|---|---:|---|
| `metal_tensor` | 2204 | `metal::tensor`, `tensor_handle`, `tensor_offset`, `tensor_inline`, the `is_*_v` traits |
| `metal_cooperative_tensor` | 584 | `metal::cooperative_tensor`, iterators, **`map_iterator`**, `get_capacity`, `get_mask`, `get_multidimensional_index` |
| `__exec/units.h` | ~190 | `execution_threads<N>`, `execution_simdgroups<N>`, and the aliases `execution_thread` / `execution_simdgroup` |

Locate the toolchain with `xcrun -sdk macosx --find metal`. It is **not** under `Xcode.app/Contents/Developer/Toolchains/` (which contains only `XcodeDefault.xctoolchain`).

### C. MLX — the real-world call site

Repo root: `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx` (shallow clone, 50 commits, HEAD `973e27f`).

Kernel headers:

| File | Lines |
|---|---:|
| `mlx/backend/metal/kernels/steel/gemm/nax.h` | 887 |
| `mlx/backend/metal/kernels/steel/attn/nax.h` | 887 — **byte-identical** to the above (verified by `diff`) |
| `mlx/backend/metal/kernels/steel/gemm/gemm_nax.h` | 131 |
| `mlx/backend/metal/kernels/quantized_nax.h` | 1680 |
| `mlx/backend/metal/kernels/quantized_nax.metal` | 106 |
| `mlx/backend/metal/kernels/fp_quantized_nax.h` | 1018 |
| `mlx/backend/metal/kernels/fp_quantized_nax.metal` | 79 |
| `mlx/backend/metal/kernels/steel/gemm/kernels/steel_gemm_{fused,gather,splitk,segmented}_nax.{h,metal}` | — |
| `mlx/backend/metal/kernels/steel/attn/kernels/steel_attention_nax.{h,metal}` | — |

Host side:

| File | Role |
|---|---|
| `mlx/backend/metal/device.cpp` | `is_nax_available()` — the runtime gate |
| `mlx/backend/metal/kernels/CMakeLists.txt` | the compile-time gate |
| `mlx/backend/metal/matmul.cpp` | GEMM dispatch |
| `mlx/backend/metal/quantized.cpp` | quantized GEMM dispatch |
| `mlx/backend/metal/jit_kernels.cpp` / `nojit_kernels.cpp` | pipeline construction |
| `mlx/utils.h` | `enable_tf32()` |

### D. Negative-result search (what is NOT there)

Run over the whole MLX tree **and** both header roots in section A and B:

```
tensor_handle tensor_inline reduce_rows map_iterator is_compatible_as
scale_plane blockFactors block_factors e8m0 E8M0 fp8 fp4 e4m3 quant aux plane
MTLTensor execution_thread execution_threadgroup dextents
```

- In **MLX**: zero hits for all of `tensor_handle`, `tensor_inline`, `reduce_rows`, `map_iterator`,
  `is_compatible_as`, `scale_plane`, `blockFactors`, `MTLTensor`, `execution_thread`,
  `execution_threadgroup`, `dextents`.
- In **the MPP + Metal tensor headers**: zero hits for `scale`, `plane`, `block_factor`, `blockFactor`,
  `fp8`, `fp4`, `e8m0`, `e4m3`, `quant`, `aux`. (Case-insensitive.)

That second result is the load-bearing one for section 10.

### E. Complete census of `mpp::` in MLX

```
$ grep -rho 'mpp::[A-Za-z0-9_:]*' mlx/ | sort | uniq -c | sort -rn
   4 mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate
   4 mpp::tensor_ops::matmul2d_descriptor
   4 mpp::tensor_ops::matmul2d
```

Twelve tokens, in four sites — two in `steel/gemm/nax.h`, two in its byte-identical twin
`steel/attn/nax.h`. **That is MLX's entire surface contact with MPP TensorOps.** Everything else
called "NAX" in MLX is MLX's own tiling code layered on top.

---

## 1. Compressed verdict table

Legend: **CONFIRMED** = exact spelling exists. **DIFFERENT** = real thing exists under another
spelling. **NOT FOUND** = no such symbol in either header root or MLX.

| Session 330 claim | Verdict | Real spelling / note |
|---|---|---|
| `matmul2d_descriptor` | **CONFIRMED** | `mpp::tensor_ops::matmul2d_descriptor` |
| `matmul2d` op | **CONFIRMED** | `mpp::tensor_ops::matmul2d<Descriptor, Scope, Args...>` |
| "parameterized by simdgroup count" | **CONFIRMED** | via `Scope = metal::execution_simdgroups<N>` |
| `execution_simdgroup` | **CONFIRMED** (as alias) | `using execution_simdgroup = execution_simdgroups<1>` |
| `execution_thread` | **CONFIRMED** (as alias) | `using execution_thread = execution_threads<1>` |
| `execution_threadgroup` | **NOT FOUND** | No such scope. Use `execution_simdgroups<N>`. |
| `tensor_handle` | **CONFIRMED** | `metal::tensor_handle` (tag type) |
| `tensor_inline` | **CONFIRMED** | `metal::tensor_inline` (tag type) |
| (unmentioned third kind) | **BONUS** | `metal::tensor_offset` also exists |
| cooperative tensors | **CONFIRMED** | `metal::cooperative_tensor<ElementType, Extents, Layout>` |
| `get_left_input_cooperative_tensor` | **CONFIRMED** | exact |
| `get_right_input_cooperative_tensor` | **CONFIRMED** | exact |
| `get_destination_cooperative_tensor` | **CONFIRMED** | exact (session 330 didn't name it; it's the primary one) |
| `is_compatible_as_left_input` | **CONFIRMED** | exact |
| `is_compatible_as_right_input` | **CONFIRMED** | exact |
| coop tensors feed a matmul directly | **CONFIRMED** | `run()`'s SFINAE accepts coop tensors in all three positions |
| `reduce_rows` | **CONFIRMED** | free function `mpp::tensor_ops::reduce_rows(...)` |
| `reduction_operation` values | **CONFIRMED** | `enum class reduction_operation { sum, max, min }` |
| `map_iterator` | **CONFIRMED** | `metal::cooperative_tensor::map_iterator(OtherIterator)` |
| quantized `MTLTensor` int2/int4/int8 | **PARTIAL** | int4/uint4/int8/uint8 yes; **int2 NOT FOUND** |
| quantized `MTLTensor` fp4/fp8 | **NOT FOUND** | no fp8/fp4 in `__tensor_ops_datatype` |
| **scale planes** | **NOT FOUND** | zero hits for `scale`/`plane` in any MPP or Metal tensor header |
| plane descriptor `dataType` + `blockFactors` | **NOT FOUND** | — |
| "auxiliary plane map" | **NOT FOUND** | — |
| `MTLTensor` (Metal-side type name) | **DIFFERENT** | Metal shading language calls it `metal::tensor<...>`. `MTLTensor` is the **host/ObjC** name only. |
| M5 "neural accelerator" per shader core | **CONFIRMED (indirectly)** | MLX gates on GPU family generation ≥ 17 (≥ 18 for `p`); Apple headers gate on OS 26.2 |
| "new in iOS/macOS 27" | **DIFFERENT** | Availability macro says **26.2**, not 27 |

Bonus APIs present in the headers that session 330 did **not** mention:

| Symbol | Where |
|---|---|
| `reduce_columns` | `MPPTensorOpsMatMul2d.h:600` |
| `is_iterator_compatible` | `MPPTensorOpsMatMul2d.h:627` |
| `get_row_reduction_destination_cooperative_tensor` | `MPPTensorOpsMatMul2d.h:561` |
| `get_column_reduction_destination_cooperative_tensor` | `MPPTensorOpsMatMul2d.h:580` |
| `reduction_operation_identity<T>` | `MPPTensorOpsMatMul2d.h:380` |
| `mpp::tensor_ops::convolution2d` | `MPPTensorOpsConvolution2d.h` |
| `mpp::tensor_ops::dynamic_length<T>` / `dynamic_length_v<T>` | `MPPTensorOpsTypes.h:138,144` |

---

## 2. `matmul2d_descriptor` — the real signature

`MPPTensorOpsMatMul2d.h:349-377`, quoted verbatim:

```cpp
struct matmul2d_descriptor
{
  enum class mode
  {
    multiply,
    multiply_accumulate,
  };

  int m, n, k;
  bool transpose_left, transpose_right;
  bool relaxed_precision;
  mode matmul_mode;

public:
  constexpr matmul2d_descriptor(int __m, int __n, int __k = static_cast<int>(metal::dynamic_extent),
                                bool __transpose_left = false,
                                bool __transpose_right = false,
                                bool __relaxed_precision = false,
                                mode __matmul_mode = mode::multiply) thread
      : m(__m),
        n(__n),
        k(__k),
        transpose_left(__transpose_left),
        transpose_right(__transpose_right),
        relaxed_precision(__relaxed_precision),
        matmul_mode(__matmul_mode)
  {
  }
};
```

**Positional argument list — memorize this order:**

| # | Name | Type | Default | Meaning |
|---:|---|---|---|---|
| 1 | `m` | `int` | *(required)* | M extent of the local tile |
| 2 | `n` | `int` | *(required)* | N extent of the local tile |
| 3 | `k` | `int` | `static_cast<int>(metal::dynamic_extent)` | K / tile-K. `dynamic_extent` ⇒ op reads K from the input tensor extents and loops internally. |
| 4 | `transpose_left` | `bool` | `false` | |
| 5 | `transpose_right` | `bool` | `false` | |
| 6 | `relaxed_precision` | `bool` | `false` | |
| 7 | `matmul_mode` | `mode` | **`mode::multiply`** | |

Two traps for a guide author:

1. **The default mode is `multiply`, not `multiply_accumulate`.** A reader who writes
   `matmul2d_descriptor(64, 32, 16)` and then loops over K will silently get *overwrite* semantics on
   every iteration. MLX passes `multiply_accumulate` explicitly (section 9).
2. **There are exactly two `mode` cases**: `multiply` and `multiply_accumulate`. No `accumulate_only`,
   no `multiply_add`, no `mode::none`.

The NN/NT/TN/TT convention, from the header's own doc comment (`MPPTensorOpsMatMul2d.h:96-97`):

```
//                             false,  // transpse_left = false for NN and NT and true for TN and TT
//                             false,  // transpse_right = false for NN and TN and true for NT and TT
```

(Apple's typo `transpse` is in the shipping header.)

`relaxed_precision`, from `MPPTensorOpsMatMul2d.h:98-99`:

```
//                             false); // relaxed_precision = false, set it to true to allow implementation
//                                     // to sacrifice accurancy for performance.
```

On the `k` argument, `MPPTensorOpsMatMul2d.h:92-95`:

```
//                             static_cast<int>(dynamic_extent), // k inner dimension. dynamic_extent means operation will read K from input tensor
//                                                               // K = A.extents().extent(0) or B.extents().extent(1) for NN
//                                                               // K = A.extents().extent(0) or B.extents().extent(0) for NT
//                                                               // and so on..
```

There is also a separate sentinel for lengths, `MPPTensorOpsTypes.h:137-144`:

```cpp
template <typename T, typename U = __tensor_ops_detail::__enable_if_t<__tensor_ops_detail::__is_integral_v<T>>>
struct dynamic_length
{
    static constexpr constant T value = metal::numeric_limits<T>::max();
};

template <typename T, typename U = __tensor_ops_detail::__enable_if_t<__tensor_ops_detail::__is_integral_v<T>>>
constexpr constant T dynamic_length_v = dynamic_length<T>::value;
```

Note `dynamic_length_v<T>` (= `numeric_limits<T>::max()`) is **not** the same as `metal::dynamic_extent`
used in the descriptor's `k` default. Don't conflate them.

---

## 3. `matmul2d` — the operation class

`MPPTensorOpsMatMul2d.h:391-402`:

```cpp
template <matmul2d_descriptor Descriptor, typename Scope, class... Args>
class matmul2d : __tensor_ops_detail::op
{
  static_assert(__tensor_ops_detail::__is_tensorops_execution_scope_v<Scope>,
                "Scope template argument should be of op_scope type");

public:

  static constexpr constant matmul2d_descriptor descriptor = Descriptor;
  using scope = Scope;

  matmul2d() thread = default;
```

Note the descriptor is a **non-type template parameter of class type** — that is why MLX declares it
`constexpr auto desc = ...` and passes `matmul2d<desc, ...>`.

### `run()`

`MPPTensorOpsMatMul2d.h:404-418`:

```cpp
  template <
      typename LeftOperandType, typename RightOperandType,
      typename DestinationOperandType,
      typename V = __tensor_ops_detail::__enable_if_t<
          ((__tensor_ops_detail::__is_tensor_type_v<LeftOperandType> || __tensor_ops_detail::__is_cooperative_tensor_type_v<LeftOperandType>) &&
           (__tensor_ops_detail::__is_tensor_type_v<RightOperandType> || __tensor_ops_detail::__is_cooperative_tensor_type_v<RightOperandType>) &&
           (__tensor_ops_detail::__is_tensor_type_v<DestinationOperandType> || __tensor_ops_detail::__is_cooperative_tensor_type_v<DestinationOperandType>))>,
      typename... RunArgs>
  INLINE void run(thread LeftOperandType &left, thread RightOperandType &right,
                  thread DestinationOperandType &destination) thread const
  {
    __mutmul2d_detail::__run<Descriptor, Scope, LeftOperandType,
                             RightOperandType, DestinationOperandType,
                             RunArgs...>(left, right, destination);
  }
```

**This SFINAE clause is the direct answer to assignment item 4's "confirm or refute".** Each of the
three operands is independently constrained to `__is_tensor_type_v<T> || __is_cooperative_tensor_type_v<T>`.
So **yes — cooperative tensors can be fed directly into a matmul, in any of the three positions**,
including all three simultaneously (which is exactly what MLX does). See section 9.

Note the internal namespace is spelled `__mutmul2d_detail` — a typo for `__matmul2d_detail`, shipping
as-is. Irrelevant to users but a good authenticity marker.

All three operands are taken by **non-const `thread` reference**. There is no `const` overload of `run`.

### Everything the class exposes

Enumerated from `MPPTensorOpsMatMul2d.h`:

| Member | Line | Kind |
|---|---:|---|
| `descriptor` | 399 | `static constexpr constant matmul2d_descriptor` |
| `scope` | 400 | type alias for `Scope` |
| `run(left, right, destination)` | 412 | method |
| `cooperative_tensor_left_input_t<...>` | 421 | type alias template |
| `get_left_input_cooperative_tensor()` | 434 | method (default-construct) |
| `get_left_input_cooperative_tensor(src)` | 451 | method (convert from another coop tensor) |
| `is_compatible_as_left_input(src)` | 466 | method → `bool` |
| `cooperative_tensor_right_input_t<...>` | 474 | type alias template |
| `get_right_input_cooperative_tensor()` | 487 | method |
| `get_right_input_cooperative_tensor(src)` | 504 | method |
| `is_compatible_as_right_input(src)` | 519 | method → `bool` |
| `cooperative_tensor_destination_t<...>` | 527 | type alias template |
| `get_destination_cooperative_tensor()` | 540 | method |
| `cooperative_tensor_row_reduction_destination_t<...>` | 550 | type alias template |
| `get_row_reduction_destination_cooperative_tensor()` | 561 | method |
| `cooperative_tensor_column_reduction_destination_t<...>` | 570 | type alias template |
| `get_column_reduction_destination_cooperative_tensor()` | 580 | method |

Note there is **no** `is_compatible_as_destination`, and **no** `get_destination_cooperative_tensor(src)`
conversion overload. The asymmetry is real.

---

## 4. Execution scopes — `execution_simdgroup` is an alias

This is the single most commonly mis-stated item, so here is the whole truth.

The primitives are two class templates, `__exec/units.h:15-18`:

```cpp
template <size_t>
struct execution_threads;
template <size_t>
struct execution_simdgroups;
```

`execution_simdgroups<Size>`, `__exec/units.h:88-104`:

```cpp
template <size_t Size>
class execution_simdgroups
{
  static_assert(Size != 0, "execution_simgroups<0> is not supported");

  using size_type = uint;

public:
  static constexpr constant size_t static_size = Size;

public:
  METAL_FUNC constexpr size_type size() thread const
  {
    return static_size;
  }
};
```

(Apple's typo `execution_simgroups` in the assert message is shipping.)

There is a dynamic specialization, `__exec/units.h:106-126`, holding a runtime `_size`.

**The aliases**, `__exec/units.h:128-129` and `:185`:

```cpp
using execution_dsimdgroups = execution_simdgroups<__execution_detail::dynamic_size>;
using execution_simdgroup = execution_simdgroups<1>;
```

```cpp
using execution_thread = execution_threads<1>;
```

And `execution_threads` only permits 1, `__exec/units.h:131-134`:

```cpp
template <size_t Size>
class execution_threads
{
  static_assert(Size == 1, "Only execution_thread<1> is supported");
```

### The complete, exhaustive scope vocabulary

| Spelling | Meaning | Real? |
|---|---|---|
| `metal::execution_thread` | 1 thread; `= execution_threads<1>` | yes |
| `metal::execution_threads<1>` | same thing | yes (only `1` compiles) |
| `metal::execution_simdgroup` | 1 SIMD group; `= execution_simdgroups<1>` | yes |
| `metal::execution_simdgroups<N>` | N SIMD groups | yes |
| `metal::execution_dsimdgroups` | runtime-sized SIMD group count | yes |
| `metal::execution_threadgroup` | — | **NO. Does not exist.** |

**How the simdgroup mapping is chosen.** It is *not* inferred and *not* a runtime argument — it is the
second template parameter of `matmul2d`, and it must match the dispatch. From
`MPPTensorOpsMatMul2d.h:305-315`:

```
//     metal::execution_thread: The operation will be run on a single thread.
//                              Fragment shaders only support this execution scope.
//     metal::execution_simdgroup: The operation will be run cooperatively by all
//                                 threads in the SIMD group. May be used for finer
//                                 control over tiling by slicing tensors with SIMD IDs.
//     metal::execution_simdgroups<N>: The operation will be executed cooperatively by N
//                                     SIMD groups. Must be used when all threads in a
//                                     threadgroup are cooperatively performing the operation.
//
// It is undefined behavior if the number of SIMD groups dispatched does not
// match the number of SIMD groups that the operation was configured with.
```

And the uniformity requirement, `MPPTensorOpsMatMul2d.h:300-303`:

```
// an execution scope provided as template argument. All the threads in this
// execution scope must enter the run method i.e. call to run methods must be
// "execution scope" uniform.
```

The scope is validated at compile time by `MPPTensorOpsTraits.h:120-122`:

```cpp
template <typename T>
constexpr constant bool __is_tensorops_execution_scope_v = metal::is_execution_thread_v<__remove_cv_t<__remove_ref_ptr_t<T>>> ||
                                                           metal::is_execution_simdgroups_v<__remove_cv_t<__remove_ref_ptr_t<T>>>;
```

Which means: only `execution_threads<1>` and any `execution_simdgroups<N>` are legal `Scope` arguments.

Host-side, the header's example shows how the two must agree, `MPPTensorOpsMatMul2d.h:75-79`:

```
//    id<MTLComputePipelineState> state = [device newComputePipelineState:...];
//    NSUInteger simdgroupWidth = [state threadExecutionWidth];
//    ...
//    [encoder dispatchThreadgroups:threadgroups
//    threadPerThreadgroups:MTLSizeMake(simdgroupWidth*4, 1, 1)];
```

i.e. `execution_simdgroups<4>` ⟺ `threadExecutionWidth * 4` threads per threadgroup.

**MLX picks the other strategy**: it uses `execution_simdgroup` (=`<1>`) everywhere and does its own
multi-simdgroup tiling above the op. See section 9.

---

## 5. Cooperative tensors

### The type

`MPPTensorOpsTraits.h:100-106` pins the shape of the type:

```cpp
template <class ElementType, class Extents, class Layout>
struct __is_cooperative_tensor_type<metal::cooperative_tensor<ElementType, Extents, Layout>> : __true_type
{
};

template <class T>
constant auto __is_cooperative_tensor_type_v = __is_cooperative_tensor_type<__remove_cv_t<__remove_ref_ptr_t<T>>>::value;
```

So the real spelling is **`metal::cooperative_tensor<ElementType, Extents, Layout>`** — three
parameters, in `namespace metal` (not `mpp`), declared in `<metal_cooperative_tensor>`.

The semantics, from the doc comment `MPPTensorOpsMatMul2d.h:212-225`:

```
// output is computed using cooperative_tensor. Unlike tensor_handle,
// tensor_offset and tensor_inline which are non-owning meaning these are
// wrappers around resource in device, threadgroup or thread address space,
// cooperative_tensor owns thread private data and divides the data for entire
// tensor among threads (participating in the scope of operation) in implementation
// defined manner. This thread private memory is allocated at construction of
// cooperative_tensor and deallocated when this cooperative_tensor goes out of
// scope. The layout of cooperative_tensor depends on operation, data type,
// number of threads in opscope with which op was created. Note that
// cooperative_tensor created from an op is only valid for threads that are part
// of execution scope on which op was created.
```

Three consequences worth stating plainly in a guide:

1. A cooperative tensor is **owning, thread-private register storage** — it is not a view.
2. Its element-to-lane mapping is **implementation defined**. You may not assume `ct[i]` is any
   particular matrix element. Use `get_multidimensional_index(i)` if you need coordinates.
3. It is **bound to the op and scope that produced it**. You cannot construct one standalone and hand
   it to a differently-configured op.

### Construction — the three getters

Default construction (no source), `MPPTensorOpsMatMul2d.h:425-438`:

```cpp
  template <typename LeftElementType, typename RightElementType,
            typename ElementType, typename CoordType = int,
            typename U = __tensor_ops_detail::__enable_if_t<
                __tensor_ops_detail::__is_thread_addrspace_v<LeftElementType> &&
                __tensor_ops_detail::__is_thread_addrspace_v<RightElementType> &&
                __tensor_ops_detail::__is_thread_addrspace_v<ElementType> &&
                __tensor_ops_detail::__is_integral_v<CoordType>>,
            typename... CoopArgs>
  INLINE cooperative_tensor_left_input_t<LeftElementType, RightElementType, ElementType, CoordType, CoopArgs...>
  get_left_input_cooperative_tensor() thread const
  {
    return __mutmul2d_detail::__get_left_input_cooperative_tensor<
        Descriptor, Scope, LeftElementType, RightElementType, ElementType, CoordType, CoopArgs...>();
  }
```

`get_right_input_cooperative_tensor()` is the exact mirror at `:478-491`.

The destination getter differs — its first two template parameters are **operand types, not element
types**, `MPPTensorOpsMatMul2d.h:531-546`:

```cpp
  template <typename LeftOperandType, typename RightOperandType,
            typename ElementType, typename CoordType = int,
            typename U = __tensor_ops_detail::__enable_if_t<
                (__tensor_ops_detail::__is_tensor_type_v<LeftOperandType> || __tensor_ops_detail::__is_cooperative_tensor_type_v<LeftOperandType>) &&
                (__tensor_ops_detail::__is_tensor_type_v<RightOperandType> || __tensor_ops_detail::__is_cooperative_tensor_type_v<RightOperandType>) &&
                __tensor_ops_detail::__is_thread_addrspace_v<ElementType> &&
                __tensor_ops_detail::__is_integral_v<CoordType>>,
            typename... CoopArgs>
  INLINE cooperative_tensor_destination_t<LeftOperandType, RightOperandType, ElementType, CoordType, CoopArgs...>
  get_destination_cooperative_tensor() thread const
  {

    return __mutmul2d_detail::__get_destination_cooperative_tensor<
        Descriptor, Scope, LeftOperandType, RightOperandType, ElementType,
        CoordType, CoopArgs...>();
  }
```

**Template parameter summary — get this right or nothing compiles:**

| Getter | TP1 | TP2 | TP3 | TP4 |
|---|---|---|---|---|
| `get_left_input_cooperative_tensor` | `LeftElementType` | `RightElementType` | `ElementType` | `CoordType = int` |
| `get_right_input_cooperative_tensor` | `LeftElementType` | `RightElementType` | `ElementType` | `CoordType = int` |
| `get_destination_cooperative_tensor` | `LeftOperandType` | `RightOperandType` | `ElementType` | `CoordType = int` |

The input getters want the **element** types of both operands plus the accumulator element type; the
destination getter wants the **operand (tensor) types** of both inputs plus the destination element type.
That is why MLX writes `decltype(ct_a), decltype(ct_b), CType` for the destination but
`AType, BType, CType` for the inputs — see section 9.

Each has a corresponding public type alias (`cooperative_tensor_left_input_t`,
`cooperative_tensor_right_input_t`, `cooperative_tensor_destination_t`) at `:421`, `:474`, `:527`, so
you can name the type without `decltype`.

### The conversion overloads

`MPPTensorOpsMatMul2d.h:440-456` — build a left-input coop tensor *from an existing coop tensor*:

```cpp
  template <typename LeftElementType, typename RightElementType,
            typename ElementType, typename CoordType = int,
            typename SrcElemType, typename SrcExtents, typename SrcLayout,
            ...>
  INLINE cooperative_tensor_left_input_t<LeftElementType, RightElementType, ElementType, CoordType, CoopArgs...>
  get_left_input_cooperative_tensor(const thread metal::cooperative_tensor<SrcElemType, SrcExtents, SrcLayout> & src) thread const
```

This is the **fusion primitive**: it lets the destination coop tensor of one matmul become the left
input of the next without a round trip through memory. Right-input mirror at `:493-509`.

### `is_compatible_as_left_input` / `is_compatible_as_right_input`

`MPPTensorOpsMatMul2d.h:458-471`:

```cpp
  template <typename LeftElementType, typename RightElementType, typename ElementType,
            typename SrcElemType, typename SrcExtents, typename SrcLayout,
            typename U = __tensor_ops_detail::__enable_if_t<
                __tensor_ops_detail::__is_thread_addrspace_v<LeftElementType> &&
                __tensor_ops_detail::__is_thread_addrspace_v<RightElementType> &&
                __tensor_ops_detail::__is_thread_addrspace_v<ElementType> &&
                __tensor_ops_detail::__is_thread_addrspace_v<SrcElemType>>>
  INLINE bool
  is_compatible_as_left_input(const thread metal::cooperative_tensor<SrcElemType, SrcExtents, SrcLayout> & src) thread const
  {
      return __mutmul2d_detail::__is_compatible_as_left_input<
          LeftElementType, RightElementType, ElementType, Descriptor, Scope,
          SrcElemType, SrcExtents, SrcLayout>(src);
  }
```

Right mirror at `:511-524`. Both spellings **CONFIRMED exactly** as session 330 described. Note:

- They return **`bool`** (a runtime value), not a `constexpr bool`.
- They take **exactly one runtime argument**: a `const thread` reference to a `cooperative_tensor`.
- They have **no `CoordType`** template parameter (unlike the getters).
- They are the guard you call before the conversion overload above.

### The `cooperative_tensor` public surface (from `<metal_cooperative_tensor>`)

| Member | Line in `metal_cooperative_tensor` |
|---|---:|
| `get_capacity()` | 413 |
| `get_multidimensional_index(thread_index_type)` | 433 |
| `get_multidimensional_index(const_iterator)` | 438 |
| `get_multidimensional_index(const thread element_type*)` | 443 |
| `get_iterator(...)` | ~525-536 |
| `map_iterator(OtherIterator)` (mutable) | 543 |
| `map_iterator(OtherIterator)` (const) | 553 |
| `begin()` / `end()` | 559-577 |

`get_mask(i)` appears in the official usage example (`MPPTensorOpsMatMul2d.h:261,280`) as the validity
predicate. The idiomatic loop, from the header's own example at `:259-263`:

```cpp
//    #pragma unroll full
//    for (uint16_t i = 0, i < cT.get_capacity(); ++i) {
//      if(cT.get_mask(i))
//        cT[i] = 0;
//    }
```

(Apple's example has a syntax error — `i = 0,` should be `i = 0;`. Do not copy it verbatim into a guide.)

Also from the example: `.load(tensor)` and `.store(tensor)` move between a coop tensor and a
tensor handle (`:275`, `:293`), and `get_multidimensional_index(i)` returns the 2-D local coordinate
(`:287`).

The doc comment is explicit that **not every slot is live** (`:247-250`):

```
//    // cooperative tensor will divide data among the threads in these
//    // 4 SIMD-Groups. The layout of data among lanes is implementation defined
//    // and not all threads and even all elements within a thread need
//    // be valid. Use the valid element check shown below to guard
```

---

## 6. Reductions: `reduce_rows`, `map_iterator`, `is_iterator_compatible`

### `reduce_rows` — CONFIRMED, and it is a free function

Session 330 described `reduce_rows` as if it were a member. It is not. `MPPTensorOpsMatMul2d.h:587-597`:

```cpp
template <class ElementType, class SrcExtents, class DstExtents, class SrcLayout, class DstLayout>
inline void reduce_rows(
    thread metal::cooperative_tensor<ElementType, SrcExtents, SrcLayout> &source,
    thread metal::cooperative_tensor<ElementType, DstExtents, DstLayout> &destination,
    reduction_operation op = reduction_operation::sum,
    ElementType identity =
        reduction_operation_identity<ElementType>::sum_identity)
{
  __mutmul2d_detail::__reduce_rows<ElementType, SrcExtents, DstExtents, SrcLayout, DstLayout>(
      source, destination, identity, op);
}
```

And its unmentioned twin, `MPPTensorOpsMatMul2d.h:599-609`:

```cpp
template <class ElementType, class SrcExtents, class DstExtents, class SrcLayout, class DstLayout>
inline void reduce_columns(
    thread metal::cooperative_tensor<ElementType, SrcExtents, SrcLayout> &source,
    thread metal::cooperative_tensor<ElementType, DstExtents, DstLayout> &destination,
    reduction_operation op = reduction_operation::sum,
    ElementType identity =
        reduction_operation_identity<ElementType>::sum_identity)
```

Facts a guide must get right:

- Both live in **`mpp::tensor_ops`**, at namespace scope — call them unqualified inside that namespace
  or as `mpp::tensor_ops::reduce_rows(...)`.
- **Source and destination must share `ElementType`.** There is a single `ElementType` parameter used
  for both. You cannot reduce a `half` tile into a `float` accumulator with this call.
- Both operands are **cooperative tensors** — you cannot reduce into a plain `tensor`.
- Argument order is `(source, destination, op, identity)`. The **identity is last**, but note the
  internal `__reduce_rows` call **swaps them** to `(source, destination, identity, op)`. Only the
  public order matters to you.

### `reduction_operation` values — CONFIRMED, exactly three

`MPPTensorOpsMatMul2d.h:342-347`:

```cpp
enum class reduction_operation
{
  sum,
  max,
  min,
};
```

No `prod`, no `mean`, no `any`/`all`. Three cases.

### Init-value convention

`MPPTensorOpsMatMul2d.h:379-387`:

```cpp
template <typename ElementType>
struct reduction_operation_identity
{
  static const constant ElementType sum_identity = (ElementType)0;
  static const constant ElementType max_identity =
      metal::numeric_limits<ElementType>::lowest();
  static const constant ElementType min_identity =
      metal::numeric_limits<ElementType>::max();
};
```

| Operation | Identity to pass |
|---|---|
| `sum` | `reduction_operation_identity<T>::sum_identity` = `T(0)` |
| `max` | `reduction_operation_identity<T>::max_identity` = `numeric_limits<T>::lowest()` |
| `min` | `reduction_operation_identity<T>::min_identity` = `numeric_limits<T>::max()` |

**THE FOOTGUN, and it is a bad one.** The default `identity` argument is
`reduction_operation_identity<ElementType>::sum_identity` — i.e. **zero** — *regardless of `op`*. So:

```cpp
reduce_rows(src, dst, reduction_operation::max);   // identity defaults to 0  ->  WRONG
```

silently computes `max(0, row)`, clamping every negative row-max to zero. The signature makes the wrong
thing the short thing. Any guide covering `reduce_rows` **must** flag this. The correct call:

```cpp
reduce_rows(src, dst, reduction_operation::max,
            reduction_operation_identity<float>::max_identity);
```

Note also `max_identity` uses `lowest()`, not `-numeric_limits<T>::max()` and not `-infinity`. For
floats those coincide in value with `-FLT_MAX`; for integer element types `lowest()` is the correct
choice and `-max()` would be off by one.

### Pre-shaped reduction destinations

Rather than constructing a destination coop tensor by hand, ask the op for one —
`MPPTensorOpsMatMul2d.h:554-565`:

```cpp
  template <typename LeftOperandType, typename RightOperandType, typename ElementType,
            typename CoordType = int,
            typename U = __tensor_ops_detail::__enable_if_t<
                __tensor_ops_detail::__is_integral_v<CoordType>>,
            typename... CoopArgs>
  INLINE cooperative_tensor_row_reduction_destination_t<LeftOperandType, RightOperandType,
                                                        ElementType, CoordType, CoopArgs...>
  get_row_reduction_destination_cooperative_tensor() thread const
```

Column mirror at `:574-584`. These are the intended inputs to `reduce_rows` / `reduce_columns`.

### `map_iterator` — CONFIRMED, and it is on `cooperative_tensor`

`metal_cooperative_tensor:538-557`:

```cpp
  template <class OtherIterator>
  METAL_FUNC enable_if_t<__cooperative_tensor_detail::is_detected<
                             __cooperative_tensor_detail::has_interface_map_index,
                             layout, OtherIterator, iterator>::value,
                         iterator>
  map_iterator(OtherIterator it) thread
  {
    return iterator(*this, layout::template map_index<OtherIterator, iterator>(
        static_cast<const thread void *>(&it._ct), it._idx, static_cast<const thread void *>(this)));
  }
  template <class OtherIterator>
  METAL_FUNC enable_if_t<__cooperative_tensor_detail::is_detected<
                             __cooperative_tensor_detail::has_interface_map_index,
                             layout, OtherIterator, iterator>::value,
                         const_iterator>
  map_iterator(OtherIterator it) thread const
```

**Answering assignment item 5 precisely:**

- **Argument type:** `OtherIterator` — an iterator obtained from a *different* cooperative tensor.
  Not an index, not a coordinate.
- **Return type:** `iterator` on the non-const overload, `const_iterator` on the const overload —
  i.e. an iterator into **`*this`**, positioned at the element corresponding to `it`.
- It is **SFINAE-gated** on the layout implementing a `map_index` interface. If the two layouts are
  incompatible, the overload does not exist and you get a hard compile error rather than a wrong answer.
- It is a member of `metal::cooperative_tensor`, in `<metal_cooperative_tensor>`, **not** of
  `mpp::tensor_ops`.

So `map_iterator` translates a position in tensor A's lane-private layout into the equivalent position
in tensor B's — the mechanism for elementwise-combining two coop tensors with different layouts.

### `is_iterator_compatible` — the runtime guard for `map_iterator`

`MPPTensorOpsMatMul2d.h:611-633`, including Apple's own usage comment:

```cpp
// Returns whether the iterators are compatible between a source and destination cooperative tensor.
//
// Use this to check whether map_iterator will be return a valid iterator. For example:
//
//     if (is_iterator_compatible(sourceCT, destCT)) {
//         for (auto it = sourceCT.begin(); it != sourceCT.end(); it++) {
//             auto dst_it = destCT.map_iterator(sourceCT)
//
//             *it += *dst_it;
//         }
//     }
//     else {
//          // Fall back to storing sourceCT to threadgroup memory and access via
//          // destCT's multidimensional indices
//     }
template <class SrcElementType, class DstElementType, class SrcExtents, class DstExtents, class SrcLayout, class DstLayout>
inline bool is_iterator_compatible(
    const thread metal::cooperative_tensor<SrcElementType, SrcExtents, SrcLayout> &source,
    const thread metal::cooperative_tensor<DstElementType, DstExtents, DstLayout> &destination)
```

Note this one **does** allow differing element types (`SrcElementType`, `DstElementType`), unlike
`reduce_rows`. Apple's example snippet is itself buggy (`destCT.map_iterator(sourceCT)` should take
`it`, and there's a missing semicolon) — again, do not copy verbatim.

The documented fallback when layouts are incompatible — "storing sourceCT to threadgroup memory and
access via destCT's multidimensional indices" — is worth reproducing in a guide, since it's the only
portable path.

### What MLX does instead

MLX uses **none** of `reduce_rows`, `reduce_columns`, `map_iterator`, or `is_iterator_compatible`.
Its attention kernel rolls its own row reduction over its own fragment layout, using
`simd_shuffle_xor` — `steel/gemm/nax.h:353-371`:

```cpp
  template <typename Op, typename T>
  METAL_FUNC static constexpr void row_reduce(
      thread const dtype_frag_t<T>& inp_vals,
      thread T* reduced_vals) {
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < kElemRows; i++) {
      T thr_reduce = Op::apply(
          Op::apply(inp_vals[i * kElemCols + 0], inp_vals[i * kElemCols + 1]),
          Op::apply(inp_vals[i * kElemCols + 2], inp_vals[i * kElemCols + 3]));

      T qgr_reduce = simd_shuffle_xor(thr_reduce, ushort(1));
      qgr_reduce = Op::apply(thr_reduce, qgr_reduce);

      T sgr_reduce = simd_shuffle_xor(qgr_reduce, ushort(8));
      sgr_reduce = Op::apply(qgr_reduce, sgr_reduce);

      reduced_vals[i] = Op::apply(reduced_vals[i], sgr_reduce);
    }
  }
```

and calls it from the flash-attention softmax,
`steel/attn/kernels/steel_attention_nax.h:395,413,398,416`:

```cpp
    Stile.template row_reduce<MaxOp>(new_max);
    ...
    Stile.template row_bin_op<ExpSubOp>(new_max);
    ...
    Stile.template row_reduce<SumOp>(sum_score);
    ...
    Otile.template row_bin_op<MulOp>(factor);
```

This is only possible because MLX knows its own fragment layout exactly (`get_coord()`,
`steel/gemm/nax.h:45-51`) rather than treating it as implementation-defined. It is a deliberate
trade: MLX gives up MPP's layout abstraction to get an in-register online-softmax it fully controls.
A guide should present `reduce_rows` as the portable API and the MLX approach as the expert escape hatch.

---

## 7. Tensor construction: `tensor_handle` / `tensor_offset` / `tensor_inline`

Session 330 named two. There are **three**.

`metal_tensor:224-235`:

```cpp
struct tensor_inline
...
struct tensor_handle
...
struct tensor_offset
...
struct tensor;
```

with the primary template at `metal_tensor:326` and a `tensor_handle` specialization at
`metal_tensor:1397`:

```cpp
struct tensor<ElementType, Extents, tensor_handle, Tags...>
```

So the shape of the type is **`metal::tensor<ElementType, Extents, Descriptor, Tags...>`**, where the
third parameter is one of the three tag structs above. The detection traits, `metal_tensor:472-486`:

```cpp
constexpr constant bool is_tensor_handle_v = is_tensor_handle<T>::value;
...
constexpr constant bool is_tensor_inline_v = is_tensor_inline<T>::value;
...
constexpr constant bool has_tensor_offset_v = has_tensor_offset<T>::value;
```

Note the **naming asymmetry**: `is_tensor_handle_v`, `is_tensor_inline_v`, but `has_tensor_offset_v`
(not `is_`). MPP wraps all three, `MPPTensorOpsTraits.h:108-118`:

```cpp
template <typename T>
constant bool __is_tensor_handle_v = metal::is_tensor_handle_v<__remove_cv_t<__remove_ref_ptr_t<T>>>;

template <typename T>
constant bool __is_tensor_offset_v = metal::has_tensor_offset_v<__remove_cv_t<__remove_ref_ptr_t<T>>>;

template <typename T>
constant bool __is_tensor_inline_v = metal::is_tensor_inline_v<__remove_cv_t<__remove_ref_ptr_t<T>>>;

template <typename T>
constant bool __is_tensor_type_v = __is_tensor_handle_v<T> || __is_tensor_offset_v<T> || __is_tensor_inline_v<T>;
```

That last line is what `run()`'s SFINAE means by "is a tensor type": any of the three descriptors.

### What each one is

From the ABI-level enum, `MPPTensorOpsTypes.h:67-73`:

```cpp
enum __tensor_ops_tensor_descriptor_type
{
  __tensor_ops_tensor_descriptor_type_handle,
  __tensor_ops_tensor_descriptor_type_offset,
  __tensor_ops_tensor_descriptor_type_inline,
  __tensor_ops_tensor_descriptor_type_none,   // raw data pointer (thread*)
};
```

and the mapping, `MPPTensorOpsTypes.h:88-99`:

```cpp
template <typename TensorType>
constexpr __tensor_ops_tensor_descriptor_type __tensor_type_to_tensor_descriptor_type()
{
  if constexpr (__is_tensor_offset_v<TensorType>)
    return __tensor_ops_tensor_descriptor_type_offset;
  else if constexpr (__is_tensor_handle_v<TensorType>)
    return __tensor_ops_tensor_descriptor_type_handle;
  else if constexpr (__is_tensor_inline_v<TensorType>)
    return __tensor_ops_tensor_descriptor_type_inline;
  else
    static_assert(__assert_false_v<TensorType>, "unsupported tensor descriptor");
}
```

Note the **`offset` check comes first** — `has_tensor_offset_v` is a `has_`, so a handle-with-offset
classifies as `offset`, not `handle`. Order matters.

| Descriptor | What it is | How you get one |
|---|---|---|
| `tensor_handle` | Host-allocated tensor bound as a kernel argument | Declare a kernel param: `tensor<device half, dextents<int32_t, 2>> A` |
| `tensor_offset` | A handle with a shifted origin, same extents | `A.slice(x, y)` |
| `tensor_inline` | Stack/inline-constructed tensor over a pointer you already have | Construct in the kernel body |
| *(none)* | Raw `thread*`, no descriptor | internal |

The `slice` → `tensor_offset` relationship is stated outright in the doc comment,
`MPPTensorOpsMatMul2d.h:106-110`:

```
//    // Following three lines of code create appropriate slice for this thread
//    // group to work on. E.g. A.slice below creates a
//    // tensor<device half, dextents<int32_t, 2>, tensor_offset>
//    // which has same extents as original tensor A but origin shifted to
//    // (0,tgid.y*64) i.e. mA[x,y] == A[x,tgid.y*64+y]
```

### Host-allocated vs stack: the declaration forms

**Host-allocated (`tensor_handle`)** — a kernel parameter, `MPPTensorOpsMatMul2d.h:81-85`:

```cpp
// kernel void simpleMatMul(tensor<device half,  dextents<int32_t, 2>> A,
//                          tensor<device half,  dextents<int32_t, 2>> B,
//                          tensor<device float, dextents<int32_t, 2>> C,
//                          constant uint& M, constant uint& N, constant uint& K,
//                          uint2 tgid [[threadgroup_position_in_grid]])
```

The third template argument is **omitted** — `tensor_handle` is the default descriptor.
`dextents<int32_t, 2>` = rank-2, all extents dynamic, `int32_t` index type.

**Sliced (`tensor_offset`)**, `:112-114`:

```cpp
//    auto mA = A.slice(0, tgid.y*64);
//    auto mB = B.slice(tgid.x*32, 0);
//    auto mC = C.slice(tgid.x*32, tgid.y*64);
```

**Statically-sliced** — extents become compile-time constants, enabling the no-bounds-check fast path,
`:143-145`:

```cpp
//      auto tA = A.static_slice<dynamic_extent, 64>(0,tgid.y*64);
//      auto tB = B.static_slice<32, dynamic_extent>(tgid.x*32, 0);
//      auto tC = C.static_slice<32, 64>(tgid.x*32, tgid.y*64);
```

Note the **coordinate order is (x, y) = (column, row)** in `slice`/`static_slice`, but the descriptor's
`(m, n)` is (rows, cols). In the example a 64×32 output tile is `matmul2d_descriptor(64, 32, ...)` yet
sliced as `static_slice<32, 64>`. This transposition is a genuine trap and belongs in any guide.

Address spaces are tracked by the tensor type — `device`, `threadgroup`, `thread` —
`MPPTensorOpsTypes.h:59-65`:

```cpp
enum __tensor_ops_address_space
{
  __tensor_ops_address_space_invalid,
  __tensor_ops_address_space_device,
  __tensor_ops_address_space_threadgroup,
  __tensor_ops_address_space_thread_private,
};
```

`constant` is a recognized address space in the traits (`MPPTensorOpsTraits.h:81-82` defines
`__is_constant_addrspace_v`) but has **no corresponding `__tensor_ops_address_space` enumerator** —
so `constant`-space tensors are not supported as operands.

### MLX uses none of this

MLX never constructs a `metal::tensor` of any descriptor kind. Its kernels take raw
`const device T*` / `threadgroup T*` pointers and feed the matmul exclusively through cooperative
tensors. Verified: zero occurrences of `tensor_handle`, `tensor_inline`, `tensor_offset`, `dextents`,
or `.slice(` in the MLX tree.

---

## 8. Data types — the enum that settles the quantization question

This is the crux. `MPPTensorOpsTypes.h:36-57`, complete and unabridged:

```cpp
enum __tensor_ops_datatype
{
  __tensor_ops_datatype_invalid = 0,

  __tensor_ops_datatype_float_bit = 0x10000000,
  __tensor_ops_datatype_float32 = __tensor_ops_datatype_float_bit | 32,
  __tensor_ops_datatype_float16 = __tensor_ops_datatype_float_bit | 16,

  __tensor_ops_datatype_signed_bit = 0x20000000,
  __tensor_ops_datatype_int4 = __tensor_ops_datatype_signed_bit | 4,
  __tensor_ops_datatype_int8 = __tensor_ops_datatype_signed_bit | 8,
  __tensor_ops_datatype_int16 = __tensor_ops_datatype_signed_bit | 16,
  __tensor_ops_datatype_int32 = __tensor_ops_datatype_signed_bit | 32,

  __tensor_ops_datatype_uint4 = 4,
  __tensor_ops_datatype_uint8 = 8,
  __tensor_ops_datatype_uint16 = 16,
  __tensor_ops_datatype_uint32 = 32,

  __tensor_ops_datatype_alternate_encoding_bit = 0x80000000,
  __tensor_ops_datatype_bfloat16 = __tensor_ops_datatype_alternate_encoding_bit | __tensor_ops_datatype_float16,
};
```

**That is the entire set.** Thirteen types plus `invalid`.

| Session 330 said | In the enum? |
|---|---|
| int2 | **NO** |
| int4 | **YES** — `__tensor_ops_datatype_int4` (and `uint4`) |
| int8 | **YES** — `__tensor_ops_datatype_int8` (and `uint8`) |
| fp4 | **NO** |
| fp8 | **NO** |
| `E8M0` scale factors | **NO** |

The encoding is a low-16-bits-are-bit-width scheme, confirmed by `MPPTensorOpsTypes.h:130-133`:

```cpp
inline uint16_t __sizeof_tensorops_datatype(__tensor_ops_datatype dataType)
{
  return (dataType & 0xFFFF) >> 3;
}
```

Note this returns **bytes** — so 4-bit types report `0`. Sub-byte handling is special-cased elsewhere.

### The Metal-language types that map onto them

`MPPTensorOpsTypes.h:101-128`:

```cpp
template <typename ElementType>
constexpr __tensor_ops_datatype __element_type_to_tensor_ops_datatype()
{
  if constexpr (__is_same_v<ElementType, float>)
    return __tensor_ops_datatype_float32;
#if __HAVE_BFLOAT__
  else if constexpr (__is_same_v<ElementType, bfloat>)
    return __tensor_ops_datatype_bfloat16;
#endif
  else if constexpr (__is_same_v<ElementType, half>)
    return __tensor_ops_datatype_float16;
#if __HAVE_INT4B_FORMAT_TYPE__
  else if constexpr (__is_same_v<ElementType, metal::int4b_format>)
    return __tensor_ops_datatype_int4;
  else if constexpr (__is_same_v<ElementType, metal::uint4b_format>)
    return __tensor_ops_datatype_uint4;
#endif
  else if constexpr (__is_same_v<ElementType, int8_t>)
    return __tensor_ops_datatype_int8;
  else if constexpr (__is_same_v<ElementType, uint8_t>)
    return __tensor_ops_datatype_uint8;
  else if constexpr (__is_same_v<ElementType, int32_t>)
    return __tensor_ops_datatype_int32;
  else if constexpr (__is_same_v<ElementType, uint32_t>)
    return __tensor_ops_datatype_uint32;
  else
    static_assert(__assert_false_v<ElementType>, "unsupported data type");
}
```

**The 4-bit element types are named `metal::int4b_format` and `metal::uint4b_format`**, gated on the
feature macro `__HAVE_INT4B_FORMAT_TYPE__`. This is the real spelling of session 330's "int4 tensors".
`MPPTensorOpsUtility.h:66-77` carries the parallel trait specializations.

### The supported operand triples

The public header enumerates every legal (left, right, destination) combination in its opening comment,
`MPPTensorOpsMatMul2d.h:13-61`. The 4-bit rows, verbatim (`:52-61`):

```
//  half     int4b_format   half
//  half     int4b_format   float
//  half     uint4b_format  half
//  half     uint4b_format  float
//  int8_t   int4b_format   int32_t
//  uint8_t  uint4b_format  int32_t
//  bfloat   int4b_format   bfloat
//  bfloat   uint4b_format  bfloat
//  bfloat   int4b_format   float
//  bfloat   uint4b_format  float
```

Corroborated by the implementation's dispatch chain, e.g. `MPPTensorOpsMatMul2dImpl.h:5801`:

```cpp
        else if constexpr (__tensor_ops_detail::__is_same_v<leftValueType, half> && __tensor_ops_detail::__is_same_v<rightValueType, metal::int4b_format> && __tensor_ops_detail::__is_same_v<destinationValueType, half>) {
```

and by the operand validity assert, `MPPTensorOpsMatMul2dImpl.h:2505-2528`:

```cpp
                  __tensor_ops_detail::__is_same_v<left_element_type, metal::uint4b_format> ||
                  __tensor_ops_detail::__is_same_v<left_element_type, metal::int4b_format> ||
                  ...
                  "uint8_t/int8_t/uint4b_format/int4b_format/float/half/bfloat");
```

Two structural observations for a guide:

1. **4-bit is right-operand-only in the mixed-precision rows.** Every `int4b_format`/`uint4b_format`
   entry has it in the *right* (weights) position. There is no `int4b_format × half` row. This matches
   the weights-quantized inference use case and constrains kernel design: your weights must be operand B.
2. **There is no scale operand anywhere in the signature.** The op takes exactly three operands. A
   4-bit matmul produces the raw integer/float dot product of the *stored* 4-bit values. Any scale or
   zero-point must be applied by you, outside the op.

Point 2 is the mechanical reason section 10's answer comes out the way it does.

### Verdict on "quantized tensors with scale planes"

- `int4b_format` / `uint4b_format` / `int8_t` / `uint8_t` as **tensor element types**: real, shipping.
- **fp8 / fp4 / E8M0 as TensorOps element types: absent.**
- **Scale planes, plane descriptors, `blockFactors`, auxiliary plane maps: absent.** Case-insensitive
  searches for `scale`, `plane`, `block_factor`, `blockFactor`, `fp8`, `fp4`, `e8m0`, `e4m3`, `quant`,
  and `aux` across all ~14,300 lines of MPP headers and all 2,788 lines of `metal_tensor` +
  `metal_cooperative_tensor` return **zero hits**.

Either session 330 described a capability that did not ship in the 26.x SDK, or it described a
*host-side* `MTLTensor` layout feature that has no shading-language TensorOps counterpart. On this
machine, with these headers, it is not reachable from a Metal kernel.

---

## 9. What MLX actually does (nax.h walkthrough)

MLX's entire MPP contact surface is one function, `mma`, written twice with mirrored operand shapes.
Here is the first, `steel/gemm/nax.h:387-456`, complete:

```cpp
  template <
      typename CType,
      typename AType,
      typename BType,
      bool transpose_a = false,
      bool transpose_b = false>
  METAL_FUNC static constexpr void mma(
      thread dtype_frag_t<CType>& Cn0,
      thread dtype_frag_t<CType>& Cn1,
      const thread dtype_frag_t<AType>& A,
      metal::bool_constant<transpose_a>,
      const thread dtype_frag_t<BType>& Bn0,
      const thread dtype_frag_t<BType>& Bn1,
      metal::bool_constant<transpose_b>) {
    constexpr auto desc = mpp::tensor_ops::matmul2d_descriptor(
        16,
        32,
        16,
        transpose_a,
        transpose_b,
        true,
        mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate);

    // Create matmul op
    mpp::tensor_ops::matmul2d<desc, metal::execution_simdgroup> gemm_op;

    // Create matmul operands in registers
    auto ct_a =
        gemm_op
            .template get_left_input_cooperative_tensor<AType, BType, CType>();
    auto ct_b =
        gemm_op
            .template get_right_input_cooperative_tensor<AType, BType, CType>();

    // Create matmul output in register
    auto ct_c = gemm_op.template get_destination_cooperative_tensor<
        decltype(ct_a),
        decltype(ct_b),
        CType>();

    // Load A in to left operand registers
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < kElemsPerFrag; i++) {
      ct_a[i] = A[i];
    }

    // Load B into right operand registers
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < kElemsPerFrag; i++) {
      ct_b[i] = Bn0[i];
      ct_b[kElemsPerFrag + i] = Bn1[i];
    }

    // Load C into output registers (op handles accumulation)
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < kElemsPerFrag; i++) {
      ct_c[i] = Cn0[i];
      ct_c[kElemsPerFrag + i] = Cn1[i];
    }

    // Do matmul
    gemm_op.run(ct_a, ct_b, ct_c);

    // Copy out results
    STEEL_PRAGMA_UNROLL
    for (short i = 0; i < kElemsPerFrag; i++) {
      Cn0[i] = ct_c[i];
      Cn1[i] = ct_c[kElemsPerFrag + i];
    }
  }
```

The second overload, `steel/gemm/nax.h:458-528`, is identical except it takes two A fragments and one B
fragment (`Am0`/`Am1` + `B`) instead of one A and two B — the 2×1 vs 1×2 micro-tile shapes.
Both use the same descriptor.

### Decoding MLX's descriptor call

```cpp
mpp::tensor_ops::matmul2d_descriptor(
    16,                     // m
    32,                     // n
    16,                     // k
    transpose_a,            // transpose_left
    transpose_b,            // transpose_right
    true,                   // relaxed_precision   <-- NOTE
    mpp::tensor_ops::matmul2d_descriptor::mode::multiply_accumulate)
```

Five things a guide author should take from this:

1. **All seven arguments are passed positionally.** No designated initializers, no builder.
2. **`m=16, n=32, k=16`.** A tiny per-simdgroup micro-tile — MLX is not letting MPP tile for it.
   The `16×16` fragment is MLX's `BaseNAXFrag::kFragRows/kFragCols` (`nax.h:28-29`); `n=32` because the
   op consumes two adjacent 16-wide B fragments at once.
3. **`relaxed_precision = true`, unconditionally.** MLX always takes the fast path. This is the
   mechanism behind MLX's TF32-style behavior for `float32` inputs, and it is why the host gates the
   whole NAX path on `env::enable_tf32()` when the dtype is `float32` (section 11). A guide
   **must** connect these two facts — the kernel-side `true` and the host-side opt-out are one feature.
4. **`mode::multiply_accumulate` is passed explicitly**, because the default is `multiply`. MLX
   pre-loads C into `ct_c` and relies on the op to accumulate — see the `// Load C into output
   registers (op handles accumulation)` comment.
5. **`metal::execution_simdgroup`**, i.e. `execution_simdgroups<1>`. One simdgroup per op. MLX runs
   `WM * WN` simdgroups per threadgroup (typically 2×2 = 4, see `quantized_nax.metal:74`) and tiles
   across them **itself**, rather than using `execution_simdgroups<4>`.

### The cooperative-tensor pattern, and what it proves

All three operands are cooperative tensors, constructed from the op, filled elementwise by index, and
passed to `run`. **This is a live, compiling, shipping proof that `run()` accepts coop tensors in all
three positions** — the refutation-or-confirmation asked for in assignment item 4. Confirmed.

Observe the template arguments, which match section 5's table exactly:

- inputs: `<AType, BType, CType>` — element types of left, right, destination.
- destination: `<decltype(ct_a), decltype(ct_b), CType>` — **operand** types of left and right, then
  destination element type.

MLX indexes the coop tensors directly (`ct_a[i] = A[i]`) and **never calls `get_mask(i)`** — despite
Apple's doc comment insisting not all elements are valid. MLX gets away with this because its
descriptor exactly matches its own fragment size, so every slot is live. Copying that pattern into a
kernel with a different tile shape is a latent correctness bug. A guide should show `get_mask` as the
default and MLX's omission as a shape-specific optimization.

Also note `kElemsPerFrag`, `steel/gemm/nax.h:31`:

```cpp
  STEEL_CONST short kElemsPerFrag = (kFragRows * kFragCols) / 32;
```

= `(16*16)/32` = 8 elements per lane per fragment, with the two-fragment operands occupying indices
`[0,8)` and `[8,16)` of the coop tensor. MLX is relying on a specific, undocumented linearization of
the coop tensor's lane-private storage. It works, but it is **not** contractual per Apple's own text.

### The layers MLX builds on top

| Layer | Where | Role |
|---|---|---|
| `BaseNAXFrag` | `steel/gemm/nax.h:27-529` | 16×16 fragment; `get_coord()`, load/store variants, `row_reduce`, `row_bin_op`, and the two `mma` overloads |
| `NAXTile<T, R, C>` | `steel/gemm/nax.h:531-817` | grid of fragments in registers; `load`/`store`/`load_safe`/`store_safe`/`load_rows`/`store_rows`/`store_slice`, plus tile-level `row_reduce`/`row_bin_op` |
| `tile_matmad_nax(...)` | `steel/gemm/nax.h:825-884` | drives `mma` across the tile; static-asserts M/N/K agreement |
| `gemm_loop(...)` | `steel/gemm/gemm_nax.h:26-129` | the K loop, with aligned/unaligned specializations |

`tile_matmad_nax` picks between the two `mma` overloads by tile shape, `steel/gemm/nax.h:847,865`:

```cpp
  if constexpr (TN == 1 && TM % 2 == 0) {
```
```cpp
  } else if constexpr (TN % 2 == 0) {
```

**Note there is no `else`.** If `TN` is odd and not 1 (or `TN==1` with odd `TM`), `tile_matmad_nax`
silently compiles to nothing and the GEMM produces garbage. Upstream PR #3924 ("Add a tile-shape
static_assert to tile_matmad_nax", open as of 2026-07-26) exists to fix exactly this. Worth knowing
before recommending arbitrary tile shapes.

The three static asserts that *are* present, `steel/gemm/nax.h:834,838,842`:

```cpp
  static_assert(TMa == TM, "MXU tile matmul: M dimensions do not match");
  static_assert(TNb == TN, "MXU tile matmul: N dimensions do not match");
  static_assert(TKa == TK, "MXU tile matmul: K dimensions do not match");
```

("MXU" — Apple's internal name for the matrix unit — leaking into MLX's assert strings.)

---

## 10. Quantization: scale planes vs hand-dequant — ANSWERED

**MLX hand-dequantizes into threadgroup memory before the tensor op ever sees the data.
It does not use scale planes. It does not pass 4-bit tensors to `matmul2d`. It does not
dequantize into cooperative tensors either.**

The pipeline is:

```
device uint8_t (packed 4/8-bit weights)  +  device uint8_t/T (scales, biases)
        |
        |   QuantizedBlockLoader::load_unsafe()   <-- dequantization happens HERE
        v
threadgroup T (or threadgroup Wtype = bfloat)     <-- full-precision tile in shared memory
        |
        |   NAXTile::load()
        v
thread registers (NAXTile fragments)
        |
        |   tile_matmad_nax -> BaseNAXFrag::mma
        v
cooperative_tensor  ->  mpp::tensor_ops::matmul2d::run()
```

By the time MPP is involved, the weights are plain `half`/`bfloat`/`float`. The op is a **dense
matmul**; it has no idea quantization ever happened.

### The code that decides — affine path

`quantized_nax.h:962-970` chooses the loader:

```cpp
  using loader_w_t = QuantizedBlockLoader<
      T,
      BN,
      BK,
      BK_padded,
      1,
      WM * WN * SIMD_SIZE,
      group_size,
      bits>;
```

`quantized_nax.h:1022-1026` runs it into threadgroup memory:

```cpp
        if constexpr (kAlignedN.value) {
          loader_w.load_unsafe();
        } else {
          loader_w.load_safe(short2(BK, tgp_bn));
        }
```

then `quantized_nax.h:1043` reads that threadgroup tile straight into a NAX register tile:

```cpp
          Btile.template load<T, BK_padded, 1>(Ws + tn * BK_padded + kk1);
```

with `Ws` declared as **full-precision threadgroup memory**, `quantized_nax.h:1230`:

```cpp
  threadgroup T Ws[BN * BK_padded];
```

The actual bit-unpacking + scale-and-bias is the classic affine kernel, `quantized_nax.h:486-530`
(4-bit case shown):

```cpp
template <typename U, int N, int bits>
inline void
dequantize(const device uint8_t* w, U scale, U bias, threadgroup U* w_local) {
...
  else if (bits == 4) {
    U s[2] = {scale, scale / static_cast<U>(16.0f)};
    for (int i = 0; i < (N / 2); i++) {
      w_local[2 * i] = s[0] * (w[i] & 0x0f) + bias;
      w_local[2 * i + 1] = s[1] * (w[i] & 0xf0) + bias;
    }
  }
```

Destination is `threadgroup U*`. Not a cooperative tensor, not a register file.

### The code that decides — MX/NV floating-point path

`fp_quantized_nax.h` is the more interesting one, because this is where `fp8_e8m0` appears — and it is
**MLX's own software type**, not a Metal or MPP type.

`fp_quantized_nax.h:31-38`:

```cpp
template <typename T, int group_size>
static inline T dequantize_scale(uint8_t s) {
  if constexpr (group_size == 16) {
    // Use nv scale
    return T(*(thread fp8_e4m3*)(&s));
  } else {
    return T(*(thread fp8_e8m0*)(&s));
  }
}
```

`fp8_e8m0` and `fp8_e4m3` are defined in `mlx/backend/metal/kernels/fp8.h` (`fp8_e8m0` at
`fp8.h:51-52`), and `fp4_e2m1` in `fp4.h`. They are **plain structs with hand-written bit
manipulation**, loaded from a `uint8_t` by reinterpret-cast. There is no hardware fp8 type and no
Metal `fp8` at all.

Element dequant, `fp_quantized_nax.h:50-67`:

```cpp
template <int bits, typename U = float>
struct Dequantize {
  U operator()(uint8_t x) {
    if constexpr (bits == 8) {
      return U(*(thread fp8_e4m3*)(&x));
    } else {
      return U(*(thread fp4_e2m1*)(&x));
    }
  }
};

template <typename U, int bits>
inline void dequantize(uint8_t w, U scale, threadgroup U* w_local) {
  if constexpr (bits == 4) {
    w_local[0] = scale * Dequantize<4, U>{}(w);
    w_local[1] = scale * Dequantize<4, U>{}(w >> 4);
  } else {
    w_local[0] = scale * Dequantize<8, U>{}(w);
  }
}
```

Again: destination `threadgroup U*`.

And the loader that applies block scales, `fp_quantized_nax.h:130-145`:

```cpp
  void load_unsafe() const {
    if (BCOLS_PACKED * BROWS < tgp_size && bi >= BROWS) {
      return;
    }

    int k = 0;
    for (int i = 0; i < n_steps_per_read; i++) {
      T scale = dequantize_scale<T, group_size>(scales[i]);
      for (int j = 0; j < n_reads_per_scale; j++) {
        dequantize<T, bits>(
            src[k * bytes_per_pack], scale, dst + k * pack_factor);
        k++;
      }
    }
  }
```

**This is a hand-written software emulation of exactly what session 330's "scale planes" would have
done in hardware.** `scales[i]` is a separate `const device uint8_t*` buffer (declared
`fp_quantized_nax.h:107`), decoded as E8M0 or E4M3 in software, multiplied in software.
If MPP supported scale planes, this loop would not exist.

Note the accumulation type for the FP path defaults to **bfloat**, `fp_quantized_nax.h:198-204`:

```cpp
    typename Wtype = bfloat>
METAL_FUNC void fp_qmm_t_impl(
    ...
    threadgroup Wtype* Ws,
```

so MX/NV weights are dequantized to `bfloat` in threadgroup memory, then matmul'd.

### Dtypes and block sizes actually instantiated

**Affine path** — `quantized_nax.metal:88-104`:

```cpp
#define instantiate_quantized_types(group_size, bits)       \
  instantiate_quantized_funcs(float, group_size, bits)      \
  instantiate_quantized_funcs(float16_t, group_size, bits)  \
  instantiate_quantized_funcs(bfloat16_t, group_size, bits)

#define instantiate_quantized_groups(bits) \
  instantiate_quantized_types(128, bits)   \
  instantiate_quantized_types(64, bits)    \
  instantiate_quantized_types(32, bits)

#define instantiate_quantized_all() \
  instantiate_quantized_groups(2) \
  instantiate_quantized_groups(3) \
  instantiate_quantized_groups(4) \
  instantiate_quantized_groups(5) \
  instantiate_quantized_groups(6) \
  instantiate_quantized_groups(8)
```

- bits ∈ {2, 3, 4, 5, 6, 8} — **including the non-power-of-two 3, 5, 6**, which no hardware tensor
  type could represent. Packing helpers at `quantized_nax.h:20-29`:
  ```cpp
  template <int bits, int wsize = 8>
  inline constexpr short get_pack_factor() {
    return (bits == 3 || bits == 5) ? 8 : (bits == 6 ? 4 : wsize / bits);
  }
  ```
- group_size (block size) ∈ {32, 64, 128}
- activation dtype ∈ {float, float16_t, bfloat16_t}

**MX/NV floating-point path** — `fp_quantized_nax.metal:71-78`:

```cpp
#define instantiate_quantized_types(type) \
  instantiate_quantized_modes(type, nvfp4, 16, 4) \
  instantiate_quantized_modes(type, mxfp8, 32, 8) \
  instantiate_quantized_modes(type, mxfp4, 32, 4)

instantiate_quantized_types(float)
instantiate_quantized_types(bfloat16_t)
instantiate_quantized_types(float16_t)
```

| Mode | Block size | Bits | Scale encoding |
|---|---:|---:|---|
| `nvfp4` | 16 | 4 | `fp8_e4m3` (the `group_size == 16` branch) |
| `mxfp8` | 32 | 8 | `fp8_e8m0` |
| `mxfp4` | 32 | 4 | `fp8_e8m0` |

So: **`fp8_e8m0`, `fp8_e4m3`, `fp4_e2m1`, mxfp4, mxfp8, nvfp4 all appear — entirely in MLX's own
software layer.** None of them reaches the tensor op.

### Alignment requirements visible in the code

| Requirement | Where | Note |
|---|---|---|
| `K % 64 == 0` | `quantized.cpp:787`, `:982` | hard gate; otherwise fall back to non-NAX |
| `transpose == true` | `quantized.cpp:787`, `:982`, `:1327` | NAX quantized path is **transposed-B only** |
| `BK >= SIMD_SIZE` | `quantized_nax.h:952` | `static_assert` |
| `BK % SIMD_SIZE == 0` | `quantized_nax.h:953` | `static_assert` |
| BK = 64 only for gather | `quantized.cpp:689` | comment: *"The gather qmm NAX kernels are instantiated with BK = 64 only"* |
| `BK_padded = BK + 16/sizeof(T)` | `quantized_nax.h:960` | bank-conflict padding |
| tiles fixed at 64/64/64, WM=WN=2 | `quantized_nax.metal:61-81` | every instantiation |
| `SK = 32`, `TK = SK/16 = 2` | `quantized_nax.h:991-995` | K micro-step |
| `bk == 64` changes grid | `matmul.cpp:2964` | segmented path |

### Bottom line for the guide

The honest framing is: **as of the 26.x SDK, TensorOps has no quantized-input story beyond
`int4b_format`/`uint4b_format`/`int8_t`/`uint8_t` raw integer operands with no scale mechanism.**
MLX — written by Apple, against the same headers, for the same hardware — declined even to use those,
and hand-dequantizes to `bfloat`/`half` in threadgroup memory instead.

That choice is defensible on the code's own terms: MLX supports 2/3/4/5/6/8-bit affine plus
mxfp4/mxfp8/nvfp4 with three block sizes. `int4b_format` covers exactly one of those eleven
configurations, and even then would still need scales applied outside the op. The generality
isn't there, so MLX skipped the feature entirely.

A guide that tells readers to feed quantized weights to `matmul2d` via scale planes would be
describing something that cannot be written against this SDK.

---

## 11. NAX / M5 gating: compile-time and runtime

MLX gates in **three** independent places. All three must pass.

### 11.1 Apple's own availability macro

`MPPTensorOpsAvailability.h:10`:

```cpp
#define __TENSOR_OPS_SUPPORT_DEPLOYMENT_TARGET_26_2 ((__ENVIRONMENT_OS_VERSION_MIN_REQUIRED__) >= 260200)
```

**26.2 — not 27.** Session 330's "new in iOS/macOS 27" is wrong for this API, or refers to a later
addition. Everything in section 2-8 is a 26.2 feature.

Both public headers are additionally hard-gated on two compiler feature macros —
`MPPTensorOpsMatMul2d.h:328`:

```cpp
#if defined(__METAL_VERSION__) && defined(__HAVE_TENSOR__)
```

If `__HAVE_TENSOR__` is undefined the entire header expands to nothing — no error, just an empty
namespace and a confusing "no member named matmul2d" later. Related feature macros seen in the
headers: `__HAVE_BFLOAT__`, `__HAVE_INT4B_FORMAT_TYPE__` (`MPPTensorOpsTypes.h:106,112`),
`__HAVE_EXECUTION_UNIT__` (`__exec/units.h:9`).

### 11.2 MLX compile-time gate (CMake)

`mlx/backend/metal/kernels/CMakeLists.txt:158-182`:

```cmake
  if(MLX_METAL_VERSION GREATER_EQUAL 400
     AND MACOS_SDK_VERSION VERSION_GREATER_EQUAL 26.2
     AND CMAKE_OSX_DEPLOYMENT_TARGET VERSION_GREATER_EQUAL 26.2)

    build_kernel(steel/gemm/kernels/steel_gemm_fused_nax ${STEEL_NAX_HEADERS})
    build_kernel(steel/gemm/kernels/steel_gemm_gather_nax ${STEEL_NAX_HEADERS})
    build_kernel(steel/gemm/kernels/steel_gemm_splitk_nax ${STEEL_NAX_HEADERS})
    build_kernel(steel/gemm/kernels/steel_gemm_segmented_nax
                 ${STEEL_NAX_HEADERS})

    build_kernel(quantized_nax quantized_nax.h ${STEEL_NAX_HEADERS})
    build_kernel(fp_quantized_nax fp4.h fp8.h fp_quantized_nax.h
                 ${STEEL_NAX_HEADERS})

    build_kernel(steel/attn/kernels/steel_attention_nax
                 ${STEEL_NAX_ATTN_HEADERS})

  else()
    message(
      WARNING "NAX kernels require Metal 4, macOS SDK >= 26.2, and "
              "MACOSX_DEPLOYMENT_TARGET >= 26.2 (SDK ${MACOS_SDK_VERSION}, "
              "CMAKE_OSX_DEPLOYMENT_TARGET=${CMAKE_OSX_DEPLOYMENT_TARGET}). "
              "Building without NAX kernels.")
    target_compile_definitions(mlx PRIVATE MLX_METAL_NO_NAX)
  endif()
```

Three conditions: **Metal 4** (`MLX_METAL_VERSION >= 400`), **SDK ≥ 26.2**, **deployment target ≥ 26.2**.
The deployment-target one is the practical gotcha — a default macOS build often targets something
older and silently loses every NAX kernel with only a CMake warning. Upstream PR #3622 ("NAX requires
setting MACOSX_DEPLOYMENT_TARGET=26.2", MERGED) and #3824 ("Warn at configure time when NAX kernels
are disabled", MERGED) both exist because people hit this.

Failure sets `MLX_METAL_NO_NAX`, which shortcircuits the runtime check.

### 11.3 MLX runtime gate — the M5 detection

`mlx/backend/metal/device.cpp:944-963`, complete:

```cpp
bool is_nax_available() {
#ifdef MLX_METAL_NO_NAX
  return false;
#else
  auto _check_nax = []() {
    bool can_use_nax = false;
    if (__builtin_available(
            macOS 26.2, iOS 26.2, tvOS 26.2, visionOS 26.2, *)) {
      can_use_nax = true;
    }
    auto& d = metal::device(mlx::core::Device::gpu);
    auto arch = d.get_architecture().back();
    auto gen = d.get_architecture_gen();
    can_use_nax &= gen >= (arch == 'p' ? 18 : 17);
    return can_use_nax;
  };
  static bool is_nax_available_ = _check_nax();
  return is_nax_available_;
#endif
}
```

Two runtime conditions:

1. **OS ≥ 26.2** via `__builtin_available` (matching Apple's macro, section 11.1).
2. **GPU family generation** parsed from the architecture string:
   `gen >= 18` if the arch suffix is `'p'`, else `gen >= 17`.

That last line is MLX's M5-class detection. The architecture string's **last character** is a
class suffix; elsewhere MLX branches on `'s'`/`'d'` (`matmul.cpp:919-920`):

```cpp
  char devc = d.get_architecture().back();
  int min_tmn_threshold = (devc == 's' || devc == 'd') ? 2048 : 1024;
```

and PR #3791 is titled "Raise qmv batch limit for large matrices on **M5-class GPUs**", confirming
gen 17 ≈ M5 generation. There is **no** query for "neural accelerator present" — no
`supportsFamily`, no feature flag. MLX infers it from generation number alone. `get_architecture_gen()`
is declared inline at `mlx/backend/metal/device.h:159`.

**Session 330's "neural accelerator per shader core" has no API.** You cannot ask Metal whether it
exists. You infer it from GPU family generation, exactly as MLX does. That is worth saying plainly in
a guide, because readers will look for a capability query and there isn't one.

### 11.4 The dtype/TF32 gate

Independent of NAX availability, `mlx/utils.h:195-197`:

```cpp
inline bool enable_tf32() {
  static bool enable_tf32_ = get_var("MLX_ENABLE_TF32", 1);
  return enable_tf32_;
}
```

Default **on**. Used to gate NAX for float32, `matmul.cpp:916-918`:

```cpp
  bool use_nax = metal::is_nax_available() &&
      !issubdtype(a.dtype(), complexfloating) &&
      (env::enable_tf32() || a.dtype() != float32);
```

and identically at `matmul.cpp:2858-2859`, `quantized.cpp:787-788`, `:982-983`, `:1327-1328`, e.g.:

```cpp
  if (metal::is_nax_available() && transpose && (K % 64 == 0) &&
      (env::enable_tf32() || x.dtype() != float32)) {
```

Read this as: *"use NAX unless the input is float32 and the user has disabled TF32."* It exists
because `nax.h` hardcodes `relaxed_precision = true` (section 9). Setting `MLX_ENABLE_TF32=0` opts
float32 matmuls out of the whole NAX path — the only precision control available, and it is
all-or-nothing. Upstream PR #3883 ("Warn once when float32 ops silently run at TF32 precision", open)
suggests users are being surprised by this.

Complex dtypes are excluded outright (`!issubdtype(a.dtype(), complexfloating)`).

### 11.5 Fallback behavior

There is always a non-NAX twin. `matmul.cpp:984-985`:

```cpp
  if (use_nax) {
    return steel_matmul_regular_axpby_nax<CHECK_AB>(
```

vs the ordinary `steel_matmul_regular_axpby`. Same for `steel_gemm_splitk_axpby_nax`,
`gather_mm_rhs_nax`, `qmm_nax`, `gather_qmm_nax`, `gather_qmm_rhs_nax`, and the segmented path which
merely appends to the kernel name, `matmul.cpp:2883`:

```cpp
    base_name += "nax_";
```

The non-NAX kernels use `simdgroup_matrix` (`<metal_simdgroup_matrix>`) — note `steel/gemm/nax.h:5-7`
still includes both, since `NAXTile` reuses surrounding STEEL machinery.

Interesting inversion at `matmul.cpp:924`: the **old** split-K path is taken only when NAX is *absent*:

```cpp
  if (!use_nax && batch_size_out == 1 && (_tm * _tn) <= min_tmn_threshold &&
```

while NAX has its own split-K at `:947`. So NAX is not a drop-in accelerator — it changes which
algorithm is selected, not just which kernel implements it.

### 11.6 A portability wrinkle worth knowing

MLX includes the MPP umbrella header unconditionally, `steel/gemm/nax.h:12`:

```cpp
#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>
```

Upstream PR #3853 ("Guard NAX MetalPerformancePrimitives include behind `__has_include`", open as of
2026-07-16) exists to make this defensive. If you write a guide showing this include, mention that a
bare include is a hard build break on toolchains without the framework, and `__has_include` is the
recommended guard.

---

## 12. Full verdict table vs session 330

Each row cites the file that decides it. Paths are relative to:
- **SDK** = `…/MacOSX.sdk/System/Library/Frameworks/MetalPerformancePrimitives.framework/Headers/`
- **TC** = `…/Metal.xctoolchain/usr/metal/32023/lib/clang/32023.883/include/metal/`
- **MLX** = `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx/mlx/`

| # | Session 330 API | Verdict | Real spelling | Citation |
|---:|---|---|---|---|
| 1 | `matmul2d_descriptor` | **CONFIRMED** | `mpp::tensor_ops::matmul2d_descriptor` | SDK `MPPTensorOpsMatMul2d.h:349`; MLX `backend/metal/kernels/steel/gemm/nax.h:401` |
| 2 | `matmul2d` op | **CONFIRMED** | `mpp::tensor_ops::matmul2d<Descriptor, Scope, Args...>` | SDK `MPPTensorOpsMatMul2d.h:391-392`; MLX `…/steel/gemm/nax.h:411` |
| 3 | "parameterized by simdgroup count" | **CONFIRMED** | second template arg `Scope`, e.g. `execution_simdgroups<4>` | SDK `MPPTensorOpsMatMul2d.h:104,310-312` |
| 4 | `mode::` enum | **CONFIRMED** | `matmul2d_descriptor::mode::{multiply, multiply_accumulate}` | SDK `MPPTensorOpsMatMul2d.h:351-355`; MLX `…/steel/gemm/nax.h:408` |
| 5 | `execution_simdgroup` | **CONFIRMED** (alias) | `using execution_simdgroup = execution_simdgroups<1>` | TC `__exec/units.h:129`; MLX `…/steel/gemm/nax.h:411` |
| 6 | `execution_thread` | **CONFIRMED** (alias) | `using execution_thread = execution_threads<1>` | TC `__exec/units.h:185` |
| 7 | `execution_threadgroup` | **NOT FOUND** | no such type; use `execution_simdgroups<N>` | TC `__exec/units.h` (absent); MPP scope trait SDK `MPPTensorOpsTraits.h:120-122` |
| 8 | `tensor_handle` | **CONFIRMED** | `metal::tensor_handle` tag; `tensor<E, Ext, tensor_handle, Tags...>` | TC `metal_tensor:227,1397` |
| 9 | `tensor_inline` | **CONFIRMED** | `metal::tensor_inline` | TC `metal_tensor:224` |
| 10 | *(not mentioned)* | **BONUS** | `metal::tensor_offset` — result of `.slice()` | TC `metal_tensor:230`; SDK `MPPTensorOpsMatMul2d.h:108` |
| 11 | cooperative tensors | **CONFIRMED** | `metal::cooperative_tensor<ElementType, Extents, Layout>` | SDK `MPPTensorOpsTraits.h:100-101` |
| 12 | `get_left_input_cooperative_tensor` | **CONFIRMED** | exact; `<LeftElemT, RightElemT, ElemT, CoordT=int>` | SDK `MPPTensorOpsMatMul2d.h:434`; MLX `…/steel/gemm/nax.h:416` |
| 13 | `get_right_input_cooperative_tensor` | **CONFIRMED** | exact | SDK `MPPTensorOpsMatMul2d.h:487`; MLX `…/steel/gemm/nax.h:419` |
| 14 | `get_destination_cooperative_tensor` | **CONFIRMED** | `<LeftOperandT, RightOperandT, ElemT, CoordT=int>` — **operand** types | SDK `MPPTensorOpsMatMul2d.h:540`; MLX `…/steel/gemm/nax.h:422-425` |
| 15 | `is_compatible_as_left_input` | **CONFIRMED** | returns `bool`; takes `const thread cooperative_tensor&` | SDK `MPPTensorOpsMatMul2d.h:466` |
| 16 | `is_compatible_as_right_input` | **CONFIRMED** | ditto | SDK `MPPTensorOpsMatMul2d.h:519` |
| 17 | coop tensor → matmul directly? | **CONFIRMED (yes)** | `run()` SFINAE: `__is_tensor_type_v \|\| __is_cooperative_tensor_type_v` per operand | SDK `MPPTensorOpsMatMul2d.h:407-410`; MLX `…/steel/gemm/nax.h:448` |
| 18 | `reduce_rows` | **CONFIRMED** | free fn `mpp::tensor_ops::reduce_rows(src, dst, op, identity)` | SDK `MPPTensorOpsMatMul2d.h:588` |
| 19 | `reduction_operation` values | **CONFIRMED** | `{ sum, max, min }` — exactly three | SDK `MPPTensorOpsMatMul2d.h:342-347` |
| 20 | reduction init value | **CONFIRMED** | `reduction_operation_identity<T>::{sum,max,min}_identity` | SDK `MPPTensorOpsMatMul2d.h:379-387` |
| 21 | `map_iterator` | **CONFIRMED** | `cooperative_tensor::map_iterator(OtherIterator) -> iterator` | TC `metal_cooperative_tensor:543,553` |
| 22 | quantized int8 tensors | **CONFIRMED** | `int8_t` / `uint8_t` element types | SDK `MPPTensorOpsTypes.h:46,51` |
| 23 | quantized int4 tensors | **DIFFERENT** | `metal::int4b_format` / `metal::uint4b_format` (not "int4") | SDK `MPPTensorOpsTypes.h:113-116`, `MPPTensorOpsMatMul2d.h:52-61` |
| 24 | quantized int2 tensors | **NOT FOUND** | no 2-bit enumerator | SDK `MPPTensorOpsTypes.h:36-57` |
| 25 | fp8 tensor dtype | **NOT FOUND** | absent from `__tensor_ops_datatype` | SDK `MPPTensorOpsTypes.h:36-57` |
| 26 | fp4 tensor dtype | **NOT FOUND** | absent | SDK `MPPTensorOpsTypes.h:36-57` |
| 27 | **scale planes** | **NOT FOUND** | zero hits for `scale`/`plane` in ~14.3k lines MPP + 2.8k lines Metal tensor headers | §0.D |
| 28 | plane descriptor `dataType`+`blockFactors` | **NOT FOUND** | — | §0.D |
| 29 | "auxiliary plane map" | **NOT FOUND** | — | §0.D |
| 30 | E8M0 block scales in hardware | **NOT FOUND** (software only) | MLX's own `fp8_e8m0` struct | MLX `backend/metal/kernels/fp8.h:51-52`; used `…/fp_quantized_nax.h:36` |
| 31 | `MTLTensor` in shaders | **DIFFERENT** | Metal SL type is `metal::tensor<...>`; `MTLTensor` is host-side only | TC `metal_tensor:326`; SDK `MPPTensorOpsMatMul2d.h:81` |
| 32 | M5 neural accelerator per core | **CONFIRMED indirectly, NO API** | inferred from `get_architecture_gen() >= 17` (18 for `'p'`) | MLX `backend/metal/device.cpp:955-957` |
| 33 | "new in iOS/macOS 27" | **DIFFERENT** | availability is **26.2** | SDK `__impl/MPPTensorOpsAvailability.h:10`; MLX `device.cpp:950-951`, `kernels/CMakeLists.txt:159-160` |

### Scorecard

- **CONFIRMED exactly as narrated:** 15 of 33
- **CONFIRMED but with a materially different spelling or shape:** 5
- **NOT FOUND (still unverified, likely not shipping):** 8 — all of them clustered in the
  scale-plane / fp8 / fp4 / int2 group
- **Bonus APIs discovered that session 330 didn't mention:** 7 (§1)

The narration was accurate about the **matmul + cooperative tensor + execution scope** core and
inaccurate about the **quantization** story.

---

## 13. Dating the work + upstream PRs

### Repository caveat

The local MLX clone is **shallow** (`git rev-parse --is-shallow-repository` → `true`, 50 commits).
The requested `git log` over the NAX files returns a single, misleading result:

```
$ git log --oneline --date=short --format='%h %ad %s' -- \
    mlx/backend/metal/kernels/steel/gemm/nax.h mlx/backend/metal/kernels/quantized_nax.h
ca60290 2026-06-27 Fix docstring nits (#3758)
```

`ca60290` is the **graft boundary**, not the introducing commit — `git show --stat ca60290` lists the
entire tree (`.clang-format`, `.github/**`, …) because it's the artificial root of the shallow clone.
`git log --diff-filter=A` returns the same commit for every NAX file, for the same reason.

**Therefore: the true introduction dates are UNVERIFIED from this clone.** To get them, re-clone
with full history (`git fetch --unshallow`).

HEAD is `973e27f` — "[CUDA] Fix grid overflow in gemm conv unfold kernels for >= 65,536 output
positions (#3893)".

### What the PR record does establish

`gh pr list -R ml-explore/mlx --search nax --state all` (2026-07-27):

| PR | Date | State | Title |
|---:|---|---|---|
| 3470 | 2026-05-01 | CLOSED | nax-g16 perf baseline: MLX_DISABLE_NAX gate + bench harness + report |
| 3593 | 2026-05-27 | CLOSED | Add MLX_DISABLE_NAX option to skip Metal-4 nax kernels at build time |
| 3622 | 2026-06-04 | **MERGED** | NAX requires setting MACOSX_DEPLOYMENT_TARGET=26.2 |
| 3631 | 2026-06-05 | **MERGED** | Fix int16 overflow in NAX qmm edge-tile bounds |
| 3632 | 2026-06-05 | **MERGED** | Fix gather_qmm NAX kernel name mismatch |
| 3810 | 2026-07-07 | **MERGED** | Fix wrong type parameter passed to gemm_splitk_nax |
| 3824 | 2026-07-09 | **MERGED** | Warn at configure time when NAX kernels are disabled |
| 3843 | 2026-07-13 | **MERGED** | Use unroll_count(4) for the NAX attention Q@K.T loop |
| 3842 | 2026-07-13 | OPEN | Add a fused full-attention path for head_dim 256 on NAX devices |
| 3853 | 2026-07-16 | OPEN | Guard NAX MetalPerformancePrimitives include behind `__has_include` |
| 3791 | 2026-07-02 | OPEN | Raise qmv batch limit for large matrices on M5-class GPUs |
| 3883 | 2026-07-21 | OPEN | Warn once when float32 ops silently run at TF32 precision |
| 3912 | 2026-07-24 | OPEN | Fix fp quantized matmul corruption when the quantized dim is not a multiple of 32 |
| 3922 | 2026-07-26 | OPEN | Fix sorted gather_qmm NAX boundary handling |
| 3924 | 2026-07-26 | OPEN | Add a tile-shape static_assert to tile_matmad_nax |

Inferences that are safe:

- NAX work was **already underway by 2026-05-01** (PR 3470 benchmarks it), so the kernels predate that.
- The **build-gating story churned through May-July 2026** (3470 → 3593 → 3622 → 3824 → 3853), which is
  consistent with §11.2's three-condition CMake block being hard to get right.
- There is an **active stream of correctness fixes** as of the last week before this investigation
  (3912, 3922, 3924, all within 72 hours). The NAX path is **new and still settling**. A guide should
  not present it as mature.
- 3924 confirms §9's missing-`else` observation is a real, acknowledged defect.
- 3883 confirms §11.4's TF32 surprise is a real, acknowledged UX problem.

Copyright headers give a corroborating floor: `steel/gemm/nax.h:1`, `gemm_nax.h:1`, and
`fp_quantized_nax.h:1` all read `// Copyright © 2025 Apple Inc.`, while `quantized_nax.h:1` reads
`// Copyright © 2023-2024 Apple Inc.` — the latter because it was **derived from the pre-existing
`quantized.h`** (it still contains the full legacy `qdot`/`qouter`/`dequantize` family at lines
20-926, most of which the NAX kernels below never call). The Apple SDK headers are uniformly
`Copyright (c) 2025 Apple Inc.`.

---

## 14. Open questions / UNVERIFIED

Things this investigation could **not** settle. Do not write around these — flag them.

1. **Introduction dates of the NAX kernels.** Blocked by the shallow clone (§13). Fix:
   `git -C <repo> fetch --unshallow`, then re-run the `git log --diff-filter=A` command.

2. **Whether scale planes exist at all.** Established: they are absent from the Metal shading-language
   TensorOps surface in this SDK. **Not** established: whether a host-side `MTLTensor` API exposes
   plane descriptors with `dataType`/`blockFactors` that some *other* consumer (MPSGraph, CoreML,
   ANE) uses. The ObjC/Swift `Metal.framework` headers were not searched — only the Metal-side MPP
   framework and the Metal toolchain. **Next step:** grep
   `…/MacOSX.sdk/System/Library/Frameworks/Metal.framework/Headers/` for `MTLTensor`, `blockFactors`,
   `scale`, `plane`.

3. **Whether session 330 described an unreleased or NDA-tier feature.** Cannot be determined from
   local artifacts. Two hypotheses fit the evidence equally: (a) the feature slipped past 26.x;
   (b) the narration conflated a host-side layout facility with the shader-side op API. The
   availability macro saying **26.2** while the brief says "iOS/macOS 27" is weak evidence for (a).

4. **`get_mask` exact signature.** Seen only in Apple's doc-comment example
   (`MPPTensorOpsMatMul2d.h:261,280`), not located in the `metal_cooperative_tensor` grep output.
   Its return type and parameter type are **UNVERIFIED**; the usage `if (cT.get_mask(i))` implies
   `bool get_mask(index)` but this was not confirmed against a declaration.

5. **`cooperative_tensor::load()` / `store()` signatures.** Same situation — used in the doc example
   (`:275`, `:293`) but the declarations were not read. Whether they accept all three tensor
   descriptor kinds is **UNVERIFIED**.

6. **The `Layout` template parameter of `cooperative_tensor`.** Its concrete instantiations are
   produced inside `__mutmul2d_detail` (8963 lines of `MPPTensorOpsMatMul2dImpl.h`), which was
   grepped but not read in full. The layout concept requires `get_capacity`,
   `get_multidimensional_index`, `get_element_index`, `get_element_pointer`, `map_index`
   (`metal_cooperative_tensor:213-347`), but whether user-defined layouts are supported is
   **UNVERIFIED**.

7. **`convolution2d`.** `MPPTensorOpsConvolution2d.h` (177 lines) + `…Convolution2dImpl.h`
   (4914 lines) exist and were **not read**. MLX does not use them. If a guide covers TensorOps
   broadly, this is a real gap.

8. **Actual M5 hardware behavior.** No M5 device was available. Whether `is_nax_available()` returns
   true on any machine here is **untested**; every conclusion about NAX is static-analysis only.
   Nothing was compiled or run.

9. **What "NAX" stands for.** Used ~60 times across MLX with no expansion anywhere in the tree.
   Apple's assert strings say "MXU" (`steel/gemm/nax.h:834`). Presumably *Neural Accelerator*
   something. **UNVERIFIED** — don't guess in prose.

10. **Whether `int4b_format` matmuls are actually faster than MLX's dequantize-then-dense approach.**
    MLX's choice (§10) may be about generality, or about performance, or both. No benchmark was run.
    Do not assert a performance rationale.

11. **`__HAVE_TENSOR__` / `__HAVE_INT4B_FORMAT_TYPE__` activation conditions.** These gate whether any
    of this compiles (§11.1), but which `-std=metal` version and target defines them was not
    determined. Practically: MLX requires `MLX_METAL_VERSION >= 400` (Metal 4).

12. **Metal toolchain version stability.** The cryptex path contains a build-specific token
    (`MetalToolchain-v17.6.109.0.iAeIa2`). It **will differ on other machines**. Any guide must
    tell readers to resolve it via `xcrun -sdk macosx --find metal`, never to hardcode it.

---

## 15. What this changes for a guide author

### Do this first

**Read the headers.** They are on the machine, they are ~14,300 lines, they contain ~320 lines of
Apple-authored prose with four complete worked examples, and they are the normative source. Any guide
written from the session video when these files were sitting in the SDK is doing it the hard way and
getting it wrong. Paths in §0.

### Corrections that must land in the drafts

1. **Kill the scale-plane material entirely.** It is the largest single block of unverifiable content
   and there is no way to write a compiling example. Replace with §8's real story:
   `int4b_format`/`uint4b_format`/`int8_t`/`uint8_t` operands, no scale mechanism in the op, scales
   applied by you. Say plainly that block-scaled formats (mxfp4/mxfp8/nvfp4) are **software**
   constructs today, and point at MLX's `fp_quantized_nax.h` as the reference implementation.

2. **Change "iOS/macOS 27" to "26.2" everywhere.** Cited: `MPPTensorOpsAvailability.h:10`.

3. **`execution_simdgroup` is `execution_simdgroups<1>`, and `execution_threadgroup` does not exist.**
   The general form is `execution_simdgroups<N>`, and it must match your dispatch or you get UB
   (`MPPTensorOpsMatMul2d.h:314-315`). Present the full four-name vocabulary (§4).

4. **`matmul2d_descriptor`'s default mode is `multiply`.** Any K-loop example that omits the 7th
   argument is wrong. Show the full positional list (§2) — there are no named parameters.

5. **`reduce_rows` is a free function in `mpp::tensor_ops`, not a member**, its source and destination
   must share `ElementType`, and **its default identity is `sum_identity` regardless of `op`**.
   The `max`/`min` footgun (§6) deserves a callout box; it silently produces wrong numbers.

6. **`map_iterator` takes an iterator and returns an iterator**, is a member of
   `metal::cooperative_tensor`, and is SFINAE-gated. Pair it with `is_iterator_compatible` and show
   the documented threadgroup-memory fallback (§6).

7. **There are three tensor descriptors, not two** — `tensor_handle`, `tensor_offset`, `tensor_inline`.
   `.slice()` produces the offset kind; that relationship is the useful thing to teach (§7). Also warn
   about the `(x,y)` vs `(m,n)` transposition in `static_slice` — Apple's own example has
   `matmul2d_descriptor(64, 32, …)` alongside `static_slice<32, 64>`.

8. **In Metal shader code the type is `metal::tensor<...>`, not `MTLTensor`.** `MTLTensor` is the
   host-side name. Mixing them will confuse every reader who tries to compile.

### Things you can now assert with confidence

- Cooperative tensors **can** be the left, right, and destination operand of a matmul simultaneously.
  Both the SFINAE clause (`MPPTensorOpsMatMul2d.h:407-410`) and MLX's shipping kernel
  (`steel/gemm/nax.h:414-448`) prove it.
- The three getters' template parameters differ in kind — element types for inputs, **operand** types
  for the destination (§5 table). This is the #1 thing that won't compile if you guess.
- MPP supports exactly 13 datatypes and ~50 (left, right, dest) triples, all enumerated in the header
  comment at `MPPTensorOpsMatMul2d.h:13-61`. Reproduce that table; it's the single most useful
  reference artifact in the whole framework.
- 4-bit operands are **right-side only** in every mixed-precision row. Weights go in operand B.

### Framing advice

- **Lead with the two-tier structure.** `mpp::tensor_ops::*` (the framework: `matmul2d`,
  `convolution2d`, reductions) sits on top of `metal::*` (the language: `tensor`,
  `cooperative_tensor`, execution scopes). Readers who don't grasp that they're in different
  namespaces from different headers will flounder.
- **Use MLX as the worked example, but annotate its deviations.** It is real and it compiles, but it
  (a) never calls `get_mask`, (b) hardcodes `relaxed_precision = true`, (c) uses
  `execution_simdgroup` and hand-tiles across simdgroups, (d) bypasses `metal::tensor` entirely,
  and (e) implements its own `row_reduce` instead of `reduce_rows`. Each is a defensible expert
  choice and a bad default.
- **Be honest about maturity.** Four correctness PRs against NAX in the last three weeks (§13),
  including a missing-`else` in `tile_matmad_nax` that silently produces garbage for odd tile shapes.
  Present NAX as new and sharp-edged.
- **The M5 capability query does not exist.** Readers will look for `supportsFamily`-style detection.
  Show MLX's generation-number heuristic (`device.cpp:955-957`) and say outright that it is the only
  approach available.
- **Never hardcode the Metal toolchain path.** `xcrun -sdk macosx --find metal`.

### Suggested guide restructure

Given the findings, the two planned guides probably want to become:

1. **"Metal TensorOps: matmul2d and cooperative tensors"** — sections 2-7 here, essentially complete
   and fully citable. This guide can ship.
2. **"Quantized matmul on Apple GPUs"** — must be rewritten around §8 + §10. The honest thesis is
   *"TensorOps gives you 4/8-bit integer operands and nothing else; here is how MLX builds
   mxfp4/mxfp8/nvfp4/affine-2..8-bit on top by dequantizing into threadgroup memory."* That is a
   better guide than the scale-plane one would have been, and it has a working reference
   implementation to point at.
