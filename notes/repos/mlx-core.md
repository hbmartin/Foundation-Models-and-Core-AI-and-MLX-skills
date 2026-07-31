# MLX core (`ml-explore/mlx`) — deep-dive research notes

**Repo checked out at:** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/ml-explore__mlx`
**HEAD at time of reading:** `973e27f [CUDA] Fix grid overflow in gemm conv unfold kernels for >= 65,536 output positions (#3893)`
**Latest tag in shallow clone:** `v0.32.0`
**Declared version:** `MLX_VERSION_MAJOR 0 / MINOR 32 / PATCH 1` → **0.32.1** (dev builds append `.devYYYYMMDD+<githash>`)
**Recent commit dates observed:** July 2026 (e.g. `0c537a4` dated `Tue Jul 21 14:46:36 2026 -0700`). This is a 2026-era tree; treat everything here as post-2025.

Everything below was read from the files in this checkout in this session. Paths are repo-relative unless noted.

---

## 0. TL;DR orientation

MLX is an array framework (NumPy-like Python API + full C++ API) from Apple ML Research. Key architectural facts:

- **Unified memory**: arrays are not "on a device". You pick the device *per operation* via a `stream=` kwarg. `mx.add(a, b, stream=mx.cpu)` and `mx.add(a, b, stream=mx.gpu)` operate on the same buffers with no copies.
- **Lazy evaluation**: ops record a graph; nothing computes until `mx.eval(...)` (or an implicit eval: printing, `.item()`, numpy conversion, `memoryview`, `mx.save*`).
- **Dynamic graphs**: no shape-based recompilation stalls except where `mx.compile` caches per (shape, ndim, dtype, arity).
- **Composable transforms**: `grad`, `value_and_grad`, `vjp`, `jvp`, `vmap`, `compile`, `checkpoint`, `custom_function` — arbitrarily composable.
- **Backends**: Metal (macOS/iOS), CUDA (Linux + Windows CI), CPU (Accelerate/BLAS/LAPACK), plus `no_gpu`/`no_cpu` stubs.
- **Distributed backends**: `ring` (TCP), `jaccl` (RDMA over Thunderbolt, macOS ≥ 26.2), `mpi`, `nccl`.

---

## 1. Repository map

```
mlx/                     # C++ core library
  ops.h / ops.cpp        # 1789 / 6604 lines — the public op surface
  primitives.h/.cpp      # 2551 / 6202 lines — graph nodes, vjp/jvp/vmap rules
  transforms.h/.cpp      # eval, vjp, jvp, value_and_grad, vmap, custom_function, checkpoint
  compile.h/.cpp         # CompileMode, simplify + fuse passes
  export.h / export.cpp  # .mlxfn export/import
  fast.h / fast.cpp      # rms_norm, layer_norm, rope, SDPA, metal_kernel, cuda_kernel
  fast_primitives.h
  array.h / array.cpp    # the array class
  dtype.h / dtype.cpp    # Dtype, Dtype::Category
  device.h / stream.h    # Device{cpu,gpu}, Stream, ThreadLocalStream
  memory.h               # memory limit / cache limit / wired limit
  random.h / random.cpp  # Threefry counter-based PRNG (JAX-style splittable keys)
  linalg.h, fft.h, io.h, einsum.h, graph_utils.h, scheduler.h, utils.h (env vars)
  distributed/{mpi,nccl,ring,jaccl}/
  backend/{metal,cuda,cpu,common,gpu,no_gpu,no_cpu}/
    metal/kernels/       # .metal sources incl. steel/ (gemm, conv, attn) and *_nax variants
  types/, 3rdparty/
python/
  mlx/                   # pure-Python layer: nn, optimizers, utils, _distributed_utils
  src/                   # nanobind bindings (array.cpp, ops.cpp, fast.cpp, transforms.cpp, ...)
  tests/                 # 40 test modules — best executable documentation
docs/src/                # Sphinx .rst sources (usage/, dev/, python/, examples/, cpp/)
examples/{python,cpp,export,extensions,cmake_project}
benchmarks/{python,cpp,numpy}
cmake/, CMakeLists.txt, setup.py, pyproject.toml
```

---

## 2. Install / build / version requirements

### 2.1 PyPI (docs/src/install.rst)

```bash
pip install mlx              # macOS / Apple silicon
pip install mlx[cuda]        # Linux CUDA (alias for cuda12)
pip install mlx[cuda12]      # explicit CUDA 12
pip install mlx[cuda13]      # CUDA 13
pip install mlx[cpu]         # CPU-only Linux
```

Requirements verbatim from `docs/src/install.rst`:

- macOS wheels: **Apple silicon**, **native Python >= 3.10**, **macOS >= 14.0**.
- CUDA wheels: **Nvidia arch >= SM 7.5**, **driver >= 550.54.14**, **CUDA toolkit >= 12.0**, **glibc >= 2.35**, Python >= 3.10. CUDA 13 package needs **driver >= 580** or a CUDA compatibility package.
- CPU-only Linux: **glibc >= 2.35**, Python >= 3.10.

Troubleshooting quote: *"Probably you are using a non-native Python. The output of `python -c "import platform; print(platform.processor())"` should be `arm`."*

### 2.2 Build from source

Build requirements (install.rst lines 84–89):
- `libblas-dev`, `liblapack-dev`, `liblapacke-dev` (Linux)
- **C++ compiler with C++20 support (Clang >= 15.0)**
- **cmake >= 3.25** and `make`
- **Xcode >= 15.0 and macOS SDK >= 14.0**

`setup.py` requires `python_requires=">=3.10"`; `pyproject.toml` build-system requires `setuptools>=80`, `cmake>=3.25`, `typing_extensions`.

Dev extras (`setup.py`):
```python
extras = {
    "dev": ["ml_dtypes", "numpy>=2", "pre-commit", "torch>=2.9", "typing_extensions"],
}
```

Console scripts registered by the wheel:
```python
entry_points = {
    "console_scripts": [
        "mlx.launch = mlx._distributed_utils.launch:main",
        "mlx.distributed_config = mlx._distributed_utils.config:main",
    ]
}
```

Commands:
```bash
pip install .
pip install -e ".[dev]"
python setup.py build_ext --inplace       # faster iterative build
python -m unittest discover python/tests  # run the Python test suite

# C++
mkdir -p build && cd build
cmake .. && make -j
make test
make install

# CUDA build
CMAKE_ARGS="-DMLX_BUILD_CUDA=ON" pip install -e ".[dev]"
cmake .. -DMLX_BUILD_CUDA=ON && make -j
```

### 2.3 CMake options (verbatim from `CMakeLists.txt` lines 32–50)

| Option | Default |
|---|---|
| `MLX_BUILD_TESTS` | ON |
| `MLX_BUILD_EXAMPLES` | ON (docs table says OFF — **docs and CMakeLists disagree**) |
| `MLX_BUILD_BENCHMARKS` | OFF |
| `MLX_BUILD_PYTHON_BINDINGS` | OFF |
| `MLX_BUILD_METAL` | ON |
| `MLX_BUILD_CPU` | ON |
| `MLX_BUILD_CUDA` | OFF |
| `MLX_METAL_DEBUG` | OFF |
| `MLX_ENABLE_X64_MAC` | OFF |
| `MLX_BUILD_GGUF` | ON |
| `MLX_BUILD_SAFETENSORS` | ON |
| `MLX_BUILD_PYTHON_STUBS` | ON |
| `MLX_METAL_JIT` | OFF |
| `MLX_USE_CCACHE` | ON |
| `BUILD_SHARED_LIBS` | OFF |
| `USE_SYSTEM_FMT` | OFF |
| `USE_ASAN` / `USE_UBSAN` / `USE_TSAN` | OFF |

- `set(CMAKE_CXX_STANDARD 20)` / `CMAKE_CXX_STANDARD_REQUIRED ON`.
- Metal-cpp is fetched from `https://developer.apple.com/metal/cpp/files/metal-cpp_26.zip` (note: **metal-cpp 26**).
- CMake hard-errors if macOS SDK < 14.0 or `CMAKE_OSX_DEPLOYMENT_TARGET` < 14.0.
- On Windows/MSVC, `MLX_BUILD_GGUF` is force-set OFF ("GGUF does not build with MSVC").
- Binary-size minimization recipe (install.rst):
  ```bash
  cmake .. -DCMAKE_BUILD_TYPE=MinSizeRel -DBUILD_SHARED_LIBS=ON \
    -DMLX_BUILD_CPU=OFF -DMLX_BUILD_SAFETENSORS=OFF -DMLX_BUILD_GGUF=OFF -DMLX_METAL_JIT=ON
  ```
  Quote: *"run-time compilation incurs a cold-start cost which can be anywhere from a few hundred millisecond to a few seconds ... Once a kernel is compiled, it will be cached by the system. The Metal kernel cache persists across reboots."*

### 2.4 Two-stage PyPI wheel build (setup.py)

- `MLX_BUILD_STAGE=1` → package `mlx`, Python-ABI+platform tagged, everything **except** backend binaries; declares `mlx-metal==<ver>` on Darwin, extras `cuda`/`cuda12`/`cuda13`/`cpu`.
- `MLX_BUILD_STAGE=2` → package `mlx-metal` / `mlx-cuda-12` / `mlx-cuda-13` / `mlx-cpu`, platform-tag only (`abi = "none"`), contains `libmlx.so` / `mlx.metallib`.
- CUDA release archs baked in stage 2: `75-real`, `80-real`, `120a-real`, `120-virtual`; on Linux also `90a-real`, `100a-real`, `121a-real`.
- CUDA 12 pins: `nvidia-cublas-cu12==12.9.*`, `nvidia-cufft-cu12==11.4.*`, `nvidia-cuda-nvrtc-cu12==12.9.*`, `nvidia-cudnn-cu12==9.*`, `nvidia-nccl-cu12`.

---

## 3. Lazy evaluation & `mx.eval`

From `docs/src/usage/lazy_evaluation.rst`:

- "*When you perform operations in MLX, no computation actually happens. Instead a compute graph is recorded.*"
- Implicit evaluation triggers: `print(array)`, `np.array(x)`, `memoryview(x)`, `array.item()`, `mx.save*`.
- Warning quote: "*Using scalar arrays for control-flow will cause an evaluation.*"
- Calling `eval` twice is a no-op.
- "*anything from a few tens of operations to many thousands of operations per evaluation should be okay*".

Canonical training-loop eval point:
```python
for batch in dataset:
    loss, grad = value_and_grad_fn(model, batch)   # nothing evaluated
    optimizer.update(model, grad)                   # still nothing
    mx.eval(loss, model.parameters())               # forward + backward + update
```

Memory trick (lazy init):
```python
model = Model()                              # no memory used yet
model.load_weights("weights_fp16.safetensors")
```

Python signatures (`python/src/transforms.cpp:1186-1240`):
```python
def eval(*args) -> None
def async_eval(*args)          # experimental; "This is an experimental API and may change"
```
Both flatten trees of arrays (`tree_flatten(args, false)`) and **release the GIL** (`nb::gil_scoped_release nogil;`) before evaluating.

C++ (`mlx/transforms.h`):
```cpp
MLX_API void eval(std::vector<array> outputs);
MLX_API void async_eval(std::vector<array> outputs);
template <typename... Arrays> void eval(Arrays&&... outputs);
```

`async_eval` example from the docstring:
```python
>>> x = mx.array(1.0)
>>> y = mx.exp(x)
>>> mx.async_eval(y)
>>> print(y)
```

Graph BFS width is capped by env `MLX_BFS_MAX_WIDTH` (default **20**) — `mlx/utils.h::env::bfs_max_width()`, used in `mlx/transforms.cpp:181`.

---

## 4. Unified memory, devices, streams

`docs/src/usage/unified_memory.rst`:
```python
a = mx.random.normal((100,))
b = mx.random.normal((100,))
mx.add(a, b, stream=mx.cpu)
mx.add(a, b, stream=mx.gpu)

c = mx.add(a, b, stream=mx.cpu)
d = mx.add(a, c, stream=mx.gpu)   # MLX inserts the cross-stream dependency automatically
```
Worked example: matmul `(4096,512)@(512,4)` on GPU + 500 `exp` on a `(512,4)` on CPU → **2.8 ms all-GPU vs 1.4 ms split**, measured on an M1 Max.

### Device / Stream API

C++ (`mlx/device.h`, `mlx/stream.h`):
```cpp
struct Device { enum class DeviceType { cpu, gpu }; DeviceType type; int index; };
const Device& default_device();
void set_default_device(const Device& d);
bool is_available(const Device& d);
int device_count(Device::DeviceType type);
const std::unordered_map<std::string, std::variant<std::string, size_t>>&
    device_info(const Device& d = default_device());

struct Stream { int index; Device device; };
struct ThreadLocalStream : public Stream {};
Stream default_stream(Device d);
void set_default_stream(Stream s);
Stream new_stream(Device d);
Stream new_thread_unsafe_stream(Device d);
ThreadLocalStream new_thread_local_stream(Device d);
Stream stream_from_thread_local_stream(ThreadLocalStream tls);
std::vector<Stream> get_streams();
void synchronize();  void synchronize(Stream);  void synchronize(ThreadLocalStream);
void clear_streams();
```

Python (`python/src/stream.cpp`, `python/src/device.cpp`):
- `mx.Device(type, index=0)`, `mx.DeviceType.cpu` / `.gpu` (exported as `mx.cpu`, `mx.gpu`).
- `mx.default_device()`, `mx.set_default_device(device)`, `mx.is_available(device)`, `mx.device_count(device_type)`, `mx.device_info(d=None)`.
- `mx.default_stream(device)`, `mx.set_default_stream(stream)`, `mx.new_stream(device)`, `mx.new_thread_unsafe_stream(device)`, `mx.new_thread_local_stream(device)`, `mx.clear_streams()`, `mx.synchronize(stream=None)`.
- Context manager: `with mx.stream(mx.cpu): ...` (class `mx.StreamContext`).

**Gotchas:**
- `mx.new_stream(device)` docstring: "*The stream can only be used on the thread where it was created on, using it in any other thread would result in errors.*" Use `new_thread_unsafe_stream` for cross-thread streams — "*currently all nodes in a graph must be evaluated in sequence and it is user's responsibility to ensure there is no race condition.*"
- `mx.new_thread_local_stream` returns a `ThreadLocalStream` (distinct Python class from `Stream`).
- `device_info` keys (from `mlx/device.h` comment): `device_name` (str), `architecture` (str), `total_memory`/`memory_size` (size_t), and **CUDA only**: `free_memory`, `uuid`, `pci_bus_id`, `compute_capability_major`, `compute_capability_minor`. Metal additionally exposes `max_recommended_working_set_size` (referenced by `set_wired_limit` docs).
- `mx.metal.device_info()`, `mx.metal.get_active_memory()`, `mx.metal.set_memory_limit()` etc. are **deprecated** — they print a deprecation to stderr at first call (`python/src/metal.cpp:20-26`) and forward to the top-level `mx.*` equivalents.

---

## 5. Memory management

C++ `mlx/memory.h` / Python `python/src/memory.cpp` (all top-level `mx.*`):

| API | Notes |
|---|---|
| `mx.get_active_memory() -> int` | bytes; excludes cached buffers |
| `mx.get_peak_memory() -> int` | since program start or last reset |
| `mx.reset_peak_memory()` | |
| `mx.get_cache_memory() -> int` | free-but-not-returned memory |
| `mx.set_memory_limit(limit) -> int` | returns previous; **"When Metal is available the memory limit defaults to 1.5 times the maximum recommended working set size reported by the device."** |
| `mx.set_cache_limit(limit) -> int` | defaults to the memory limit; `0` disables the cache |
| `mx.set_wired_limit(limit) -> int` | **macOS >= 15.0 only**; default `0`; must stay strictly below total memory; larger than the system wired limit is an error |
| `mx.clear_cache()` | after this `get_cache_memory()` should be 0 |

Raising the system wired limit (from the `set_wired_limit` docstring):
```bash
sudo sysctl iogpu.wired_limit_mb=<size_in_megabytes>
```

---

## 6. Function transforms

### 6.1 Python signatures (verbatim `nb::sig` strings, `python/src/transforms.cpp`)

```python
def grad(fun: Callable[P, R],
         argnums: Optional[Union[int, Sequence[int]]] = None,
         argnames: Union[str, Sequence[str]] = []) -> Callable[P, Any]

def value_and_grad(fun: Callable[P, R],
                   argnums: Optional[Union[int, Sequence[int]]] = None,
                   argnames: Union[str, Sequence[str]] = []) -> Callable[P, Tuple[R, Any]]

def jvp(fun: Callable, primals: list[array], tangents: list[array])
        -> tuple[list[array], list[array]]

def vjp(fun: Callable, primals: list[array], cotangents: list[array])
        -> tuple[list[array], list[array]]

def vmap(fun: Callable[P, R], in_axes: object = 0, out_axes: object = 0) -> Callable[P, R]

def compile(fun: Callable[P, R],
            inputs: Optional[object] = None,
            outputs: Optional[object] = None,
            shapeless: bool = False) -> Callable[P, R]

def checkpoint(fun: Callable[P, R]) -> Callable[P, R]

def eval(*args) -> None
def async_eval(*args)
```

`mx.disable_compile()` / `mx.enable_compile()` — the latter *overrides* the `MLX_DISABLE_COMPILE` env var.

### 6.2 Autodiff notes

- `grad`/`value_and_grad` differentiate w.r.t. arg 0 by default; `argnums=1` etc.; gradients w.r.t. arbitrarily nested `list`/`tuple`/`dict` pytrees preserve the tree structure.
- "*If you are coming to MLX from PyTorch, you no longer need functions like `backward`, `zero_grad`, and `detach`, or properties like `requires_grad`.*"
- `mx.stop_gradient(x)` for blocking gradient flow.
- `mx.grad(mx.grad(f))` — arbitrary-order derivatives.
- **vmap gotcha (docs warning):** "*Some operations are not yet supported with `vmap`. If you encounter an error like: `ValueError: Primitive's vmap not implemented.` file an issue*". `in_axes`/`out_axes` accept `None` to mark non-vmapped inputs/outputs.
- vmap speed anecdote from docs: naive loop over 4096 rows `5.639 s` vs vmapped `0.024 s` (M1 Max, ~200×).

`jvp` example from the docstring:
```python
outs, jvps = mx.jvp(mx.sin, (mx.array(1.0),), (mx.array(1.0),))
```

### 6.3 `mx.custom_function`

Decorator class (`python/src/transforms.cpp:1042-1183`). Methods `.vjp(f)`, `.jvp(f)`, `.vmap(f)` are themselves decorators. All three are optional; undefined ones fall back to default behaviour.

```python
import mlx.core as mx

@mx.custom_function
def f(x, y):
    return mx.sin(x) * y

@f.vjp
def f_vjp(primals, cotangent, output):
    x, y = primals
    return cotan * mx.cos(x) * y, cotan * mx.sin(x)

@f.jvp
def f_jvp(primals, tangents):
    x, y = primals
    dx, dy = tangents
    return dx * mx.cos(x) * y + dy * mx.sin(x)

@f.vmap
def f_vmap(inputs, axes):
    x, y = inputs
    ax, ay = axes
    if ay != ax and ax is not None:
        y = y.swapaxes(ay, ax)
    return mx.sin(x) * y, (ax or ay)
```

Signature contract:
- **vjp** takes `(primals, cotangents, outputs)` — outputs are passed so you don't recompute the forward.
- **jvp** takes `(primals, tangents)`; tangents may be `None` for inputs with no gradient.
- **vmap** takes `(inputs, axes)`, returns `(outputs, out_axes)`; `None` axis for de-vectorized outputs.

**Big footgun (verbatim docstring):** "*All `custom_function` instances behave as pure functions. Namely, any variables captured will be treated as constants and no gradients will be computed with respect to the captured arrays.*" The docstring's example shows `mx.grad(g)(x, y)` raising while `mx.grad(g, argnums=1)(x, y)` prints `0.0`.

C++ equivalents (`mlx/transforms.h`): `custom_function(fun, fun_vjp?, fun_jvp?, fun_vmap?)`, `custom_vjp(fun, fun_vjp)`, `checkpoint(fun)`.

### 6.4 `mx.checkpoint` / `nn.utils.checkpoint`

- `mx.checkpoint(fun)`: gradient checkpointing w.r.t. the callable's inputs. "*Use this to reduce memory use for gradient computations at the expense of increased computation.*"
- `mlx.nn.utils.checkpoint(module, fn=None)` (python/mlx/nn/utils.py:41) additionally checkpoints w.r.t. the module's trainable parameters. If `fn is None`, it captures the *module* (not `module.__call__`) so monkey-patched `__call__` is respected.

---

## 7. `mx.compile`

### 7.1 Semantics

From `docs/src/usage/compile.rst`:
- Merges common work and **fuses element-wise ops** into a single kernel. gelu example on M1 Max: **15.5 ms → 3.1 ms (5×)** for `mx.random.uniform(shape=(32,1000,4096))`.
- Compiled functions are cached; `mx.compile(fun)(x, y)` twice does not recompile.
- **Recompilation triggers**: changing shape or ndim; changing input dtype; changing number of inputs.
- Anti-pattern: `mx.compile(lambda ...)` inside a loop recompiles each iteration.
- You cannot inspect/print arrays inside a compiled function (traced with placeholders). Disable with `mx.disable_compile()` or env `MLX_DISABLE_COMPILE`.
- Compiled functions must be **pure**. Captured mutable state is a constant unless declared.

### 7.2 `inputs=` / `outputs=` state capture

```python
from functools import partial
state = [mx.array(1.0)]

@partial(mx.compile, inputs=state)     # capture implicit inputs
def fun(x):
    return x + state[0]

state = []
@partial(mx.compile, outputs=state)    # capture implicit outputs
def fun(x, y):
    z = x + y
    state.append(z)
    return mx.exp(z)
```

Canonical compiled training step (compile.rst lines 345–392):
```python
import mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim
from functools import partial

model = nn.Linear(10, 1)
optimizer = optim.SGD(learning_rate=0.1, momentum=0.8)

def loss_fn(model, x, y):
    logits = model(x).squeeze()
    return nn.losses.binary_cross_entropy(logits, y)

state = [model.state, optimizer.state]

@partial(mx.compile, inputs=state, outputs=state)
def step(x, y):
    loss_and_grad_fn = nn.value_and_grad(model, loss_fn)
    loss, grads = loss_and_grad_fn(model, x, y)
    optimizer.update(model, grads)
    return loss

for it in range(10):
    loss = step(x, y)
    mx.eval(state)
```

> **Note (verbatim):** "*If you are using a module which performs random sampling such as `mlx.nn.Dropout`, make sure you also include `mx.random.state` in the `state` captured by `compile`, i.e. `state = [model.state, optimizer.state, mx.random.state]`.*"

Test-verified capture behaviours (`python/tests/test_compile.py:363-509`):
- `inputs=` supports dict, list, and *tuple of list* (`state = ([mx.array(2)],)`).
- Changing state inside a compiled function with both `inputs=` and `outputs=` set triggers a recompile the first time and then accumulates correctly.
- `mx.random.state` is a **single global sentinel object shared across threads** but resolves to the *calling thread's* RNG state (test `test_compile_rng_across_threads`, added by commit `ce30733 Fix captured random state in compile (#3828)`).

### 7.3 Shapeless compilation

`mx.compile(fun, shapeless=True)`. Changing **ndim or dtype still recompiles**; only shape changes are exempt.
Footgun example (compile.rst lines 482–516):
```python
def fun(x):
    return x.reshape(x.shape[0] * x.shape[1], -1)   # BAD: bakes in the first shape
def fun(x):
    return x.flatten(0, 1)                          # OK
```

### 7.4 Compile internals (`mlx/compile.cpp`, `mlx/compile.h`)

```cpp
enum class CompileMode { disabled, no_simplify, no_fuse, enabled };
MLX_API void set_compile_mode(CompileMode mode);
```
Two passes run per compiled entry (`mlx/compile.cpp:1141-1150`): `compile_simplify` (skipped under `no_simplify`) then `compile_fuse` (skipped under `no_fuse`).

**Only these primitives are fusable** (`is_fusable = is_unary || is_binary || is_ternary || is_broadcast`, mlx/compile.cpp:77):
- unary: `Abs, ArcCos, ArcCosh, ArcSin, ArcSinh, ArcTan, ArcTanh, AsType, Ceil, Cos, Conjugate, Cosh, Remainder, Erf, ErfInv, Exp, Floor, Log, Log1p, LogicalNot, Negative, Round, Sigmoid, Sign, Sin, Sinh, Square, Sqrt, Tan, Tanh, Expm1, Real, Imag, BitwiseInvert`
- binary: `Add, Divide, Equal, Greater, GreaterEqual, Less, LessEqual, LogicalNot, LogicalAnd, LogicalOr, LogAddExp, Maximum, Minimum, Multiply, NotEqual, Power, Subtract, BitwiseBinary, ArcTan2`
- ternary: `Select`
- broadcast: `Broadcast`

Fusion error you may hit: `"[compile] Compilation failed. Tried to fuse operations with different output shapes"` (mlx/compile.cpp:965).

`is_noop` = `Copy`, `StopGradient`. `is_reduction` = `Reduce`, `ArgReduce` (not fused into element-wise kernels).

---

## 8. `mx.export` / `.mlxfn`

### 8.1 Python API (`docs/src/python/export.rst`, `docs/src/usage/export.rst`)

`mx.export_function`, `mx.import_function`, `mx.exporter`, `mx.export_to_dot`.

```python
def fun(x, y): return x + y
x = mx.array(1.0); y = mx.array(1.0)
mx.export_function("add.mlxfn", fun, x, y)      # positional
mx.export_function("add.mlxfn", fun, (x, y))    # tuple form — same thing
mx.export_function("add.mlxfn", fun, x, y=y)    # mixed positional/kwargs

add_fun = mx.import_function("add.mlxfn")
out, = add_fun(mx.array(1.0), mx.array(2.0))    # ALWAYS returns a tuple
out, = add_fun((x, y))
out, = add_fun((x,), {"y": y})
```

**Gotchas:**
- Imported functions **always return a tuple** even for a single-output function.
- Calling with a different dtype or shape than the example inputs raises (unless `shapeless=True`).
- If you exported with a kwarg you must call with the same kwarg name.
- **Enclosed arrays must be `mx.eval`'d before export**, otherwise the graph that *produces* them (e.g. random init) is exported too: "*If the above example was missing `mx.eval(model.parameters())`, the exported function would include the random initialization of the `mlx.nn.Module` parameters.*"

Exporting an `nn.Module` with vs without parameters:
```python
model = nn.Linear(4, 4); mx.eval(model.parameters())

def call(x): return model(x)
mx.export_function("model.mlxfn", call, mx.zeros(4))     # params baked in

def call(x, **params):
    model.update(tree_unflatten(list(params.items())))
    return model(x)
params = tree_flatten(model.parameters(), destination={})
mx.export_function("model.mlxfn", call, (mx.zeros(4),), params)   # params as inputs
```

Multiple traces into one file (dedupes constants):
```python
with mx.exporter("fun.mlxfn", fun) as exporter:
    exporter(mx.array(1.0))
    exporter(mx.array(1.0), y=mx.array(0.0))
```

Callback export (inspect the graph instead of writing a file):
```python
def callback(args): print(args)
mx.export_function(callback, fun, mx.array([1.0, 2.0]))
```
`args["type"]` ∈ `{"inputs", "keyword_inputs", "outputs", "constants", "primitives"}`.

Imported functions are transformable: `mx.grad(lambda x: imported_fun(x)[0])`, `mx.compile(imported_fun)`.

### 8.2 C++ side (`mlx/export.h`)

```cpp
using Args   = std::vector<array>;
using Kwargs = std::unordered_map<std::string, array>;

FunctionExporter exporter(const std::string& file, fn, bool shapeless = false);
void export_function(const std::string& file, fn, const Args&, bool shapeless = false);
void export_function(const std::string& file, fn, const Args&, const Kwargs&, bool shapeless = false);
ImportedFunction import_function(const std::string& file);
// callback overloads take an ExportCallback = std::function<void(const ExportCallbackInput&)>
```
`StateT` variant enumerates everything a Primitive can serialize: `bool, int, size_t, float, double, Dtype, Shape, Strides, vector<int>, vector<size_t>, vector<tuple<bool,bool,bool>>, vector<variant<bool,int,float>>, optional<float>, string`.

C++ usage:
```cpp
auto fun = mx::import_function("fun.mlxfn");
auto inputs = {mx::array(1.0), mx::array(1.0)};
auto outputs = fun(inputs);
std::cout << outputs[0] << std::endl;
```
"*Use `std::vector<mx::array>` for positional arguments and `std::map<std::string, mx::array>` for keyword arguments when calling imported functions in C++.*"

Working example pair: `examples/export/eval_mlp.py` + `examples/export/eval_mlp.cpp`, `train_mlp.py`/`train_mlp.cpp`.

---

## 9. `mx.fast` — fused kernels & custom kernel authoring

### 9.1 API surface (`docs/src/python/fast.rst`)

`mx.fast.rms_norm`, `layer_norm`, `rope`, `scaled_dot_product_attention`, `metal_kernel`, `cuda_kernel`, `precompiled_cuda_kernel`.

Exact Python signatures (`python/src/fast.cpp`):
```python
def rms_norm(x: array, weight: Optional[array], eps: float, *, stream=None) -> array
def layer_norm(x: array, weight: Optional[array], bias: Optional[array], eps: float, *, stream=None) -> array
def rope(a: array, dims: int, *, traditional: bool, base: Optional[float], scale: float,
         offset: Union[int, array], freqs: Optional[array] = None, stream=None) -> array
def scaled_dot_product_attention(q: array, k: array, v: array, *, scale: float,
         mask: Union[None, str, array] = None, sinks: Optional[array] = None, stream=None) -> array
```

C++ (`mlx/fast.h`):
```cpp
array rms_norm(const array& x, const std::optional<array>& weight, float eps, StreamOrDevice s = {});
array layer_norm(const array& x, const std::optional<array>& weight,
                 const std::optional<array>& bias, float eps, StreamOrDevice s = {});
array rope(const array& x, int dims, bool traditional, std::optional<float> base,
           float scale, int offset, const std::optional<array>& freqs = std::nullopt, StreamOrDevice s = {});
array rope(..., const array& offset, ...);   // per-batch offsets
array scaled_dot_product_attention(const array& queries, const array& keys, const array& values,
    const float scale, const std::string& mask_mode = "", std::optional<array> mask_arr = {},
    const std::optional<array>& sinks = {}, StreamOrDevice s = {});
```

### 9.2 RoPE gotchas
- Input must be at least 3D, shape `(B, *, T, D)`.
- **"Exactly one of `base` and `freqs` must be `None`."**
- `offset` may be an `int`, or an `array` (scalar or a vector of `B` per-example offsets).
- `traditional=True` rotates *consecutive* dimensions.
- `dims` may be smaller than `D`; the remainder is left unchanged.

### 9.3 SDPA gotchas
- Shapes: `q [B, N_q, T_q, D]`, `k [B, N_kv, T_kv, D]`, `v [B, N_kv, T_kv, D]`.
- "*The softmax operation is performed in `float32` regardless of the input precision.*"
- "*For Grouped Query Attention and Multi-Query Attention, the `k` and `v` inputs should not be pre-tiled to match `q`.*"
- `mask` accepts only the string `"causal"` or an array. Invalid strings raise: `"[scaled_dot_product_attention] invalid mask option '<x>'. Must be 'causal', or an array."`
- Array masks: bool or additive, ≤4 dims, broadcast-compatible with `[B, N, T_q, T_kv]`. Additive masks must promote to `result_type(q,k,v)`.
- **`"causal"` uses lower-right alignment** — the last query aligns with the last key.
- `sinks` — optional attention-sink array (new-ish feature; validated for shape).
- `n_heads` must be a multiple of `n_kv_heads`.

**Metal fast-path conditions** (`mlx/backend/metal/scaled_dot_product_attention.cpp:593-644`, `ScaledDotProductAttention::use_fallback`) — falls back to the unfused implementation when any of:
- `is_training` (i.e. inside grad tracing) → *"It's faster for training on Metal to use the unfused SDPA for both forward and backward."* **So the fused SDPA kernel is inference-only on Metal.**
- `output_logsumexp`
- `s.device == Device::cpu`
- head dims not supported. Vector kernel (`T_q <= 8`): `D_q == D_v ∈ {64, 96, 128, 256}` **or** `(D_q=192, D_v=128)`; also requires `T_q <= T_kv` and `T_q * gqa_factor <= 32`. Full kernel (`T_q > 8`): `D_q == D_v ∈ {64, 80, 128}` and mask must be absent/array/causal-with-`T_q <= T_kv`.
- Env override: `MLX_SDPA_BLOCKS` (`mlx/backend/metal/scaled_dot_product_attention.cpp:477`); commit `8462ad9` rounds it up to a multiple of 32.
- CUDA: `MLX_CUDA_USE_CUDNN_SDPA` (default 1).

### 9.4 Custom Metal kernels

`mx.fast.metal_kernel(...)` returns a *callable*. Constructor params (python/src/fast.cpp:391-398):
```python
mx.fast.metal_kernel(
    name: str,
    input_names: List[str],
    output_names: List[str],
    source: str,
    header: str = "",
    ensure_row_contiguous: bool = True,
    atomic_outputs: bool = False,
    compile_options: Optional[dict] = None,   # {"math_mode": "safe"|"relaxed"|"fast"}
)
```
Call params:
```python
def __call__(self, *, inputs: List[Union[scalar, array]],
             output_shapes: List[Sequence[int]],
             output_dtypes: List[Dtype],
             grid: tuple[int, int, int],
             threadgroup: tuple[int, int, int],
             template: Optional[List[Tuple[str, Union[bool, int, Dtype]]]] = None,
             init_value: Optional[float] = None,
             verbose: bool = False,
             stream: Union[None, Stream, Device] = None)
```

Minimal working example (docs/src/dev/custom_metal_kernels.rst:15-43):
```python
source = """
    uint elem = thread_position_in_grid.x;
    T tmp = inp[elem];
    out[elem] = metal::exp(tmp);
"""
kernel = mx.fast.metal_kernel(
    name="myexp", input_names=["inp"], output_names=["out"], source=source,
)
def exp_elementwise(a: mx.array):
    outputs = kernel(
        inputs=[a], template=[("T", mx.float32)],
        grid=(a.size, 1, 1), threadgroup=(256, 1, 1),
        output_shapes=[a.shape], output_dtypes=[a.dtype],
    )
    return outputs[0]

a = mx.random.normal(shape=(4, 16)).astype(mx.float16)
assert mx.allclose(exp_elementwise(a), mx.exp(a))
```

Signature generation rules (verbatim from the doc):
- Only the **body** is passed in `source`; the function signature is generated.
- Each input `a` contributes `const device <T>* a [[buffer(i)]]`, plus **`a_shape`, `a_strides`, `a_ndim` if any of those identifiers appear in `source`**.
- Each output contributes `device <T>* out`.
- `template=[("T", mx.float32)]` becomes `template <typename T>` + an explicit instantiation. Template args can be `mx.core.Dtype`, `int`, or `bool`.
- Any Metal attribute used in the source (e.g. `thread_position_in_grid`, `threads_per_threadgroup`, `thread_index_in_simdgroup`, `threads_per_simdgroup`) becomes a function argument. "*All the attributes defined in Table 5.8 of the Metal Shading Language Specification are supported.*"

Generated signature shown in the docs:
```cpp
template <typename T>
[[kernel]] void custom_kernel_myexp_float_float16_t_float16_t(
  const device float16_t* inp [[buffer(0)]],
  device float16_t* out [[buffer(1)]],
  uint3 thread_position_in_grid [[thread_position_in_grid]]) { ... }

template [[host_name("custom_kernel_myexp_float_float16_t_float16_t")]] [[kernel]]
decltype(custom_kernel_myexp_float_float16_t_float16_t<float>)
custom_kernel_myexp_float_float16_t_float16_t<float>;
```

**Math mode** (new; commit `51bef6f Add math mode option for custom Metal kernels (#3728)`):
- Default is `compile_options={"math_mode": "safe"}` — IEEE semantics, e.g. `exp(-inf) == 0`. "*This is important for kernels such as masked softmax where causal or sliding-window masks depend on exponentiating `-inf`.*"
- Alternatives: `"relaxed"`, `"fast"`. Invalid values raise `"[metal_kernel] Expected math_mode to be 'safe', 'relaxed', or 'fast'."`; unknown option keys raise `"[metal_kernel] Unknown compile option \`<key>\`."` Both surface as `ValueError` in Python (test `test_custom_metal_kernel_math_mode`).
- Parsed by `parse_metal_math_mode` → `mx::MathMode::{Safe,Relaxed,Fast}` (python/src/fast.cpp:78-88).

**Strides / non-contiguous inputs:** set `ensure_row_contiguous=False` and use the auto-injected shape/strides plus `elem_to_loc` (from `mlx/backend/metal/kernels/utils.h`, "*automatically included*"):
```python
source = """
    uint elem = thread_position_in_grid.x;
    uint loc = elem_to_loc(elem, inp_shape, inp_strides, inp_ndim);
    T tmp = inp[loc];
    out[elem] = metal::exp(tmp);   // outputs are always row contiguous
"""
kernel = mx.fast.metal_kernel(..., ensure_row_contiguous=False)
```

**Atomic outputs + init_value** (for VJP kernels):
- `init_value=0` initializes every output element before the kernel runs.
- `atomic_outputs=True` makes all outputs `device atomic<T>*` so you can use `atomic_fetch_add_explicit(&x_grad[offset], v, memory_order_relaxed)`.
- Doc's `grid_sample` VJP does `simd_sum(gix)` first and only `thread_index_in_simdgroup == 0` does the atomic — "*This is much faster than relying purely on atomics.*"
- Reported speedups in the doc: forward `55.7ms -> 6.7ms (8x)`, vjp `676.4ms -> 16.7ms (40x)` on M1 Max with `x.shape=(8,1024,1024,64)`, `grid.shape=(8,256,256,2)`.

**Performance note (verbatim):** "*Every time you make a kernel, a new Metal library is created and possibly JIT compiled. To reduce the overhead from that, build the kernel once with `fast.metal_kernel` and then use it many times.*"

`grid`/`threadgroup` map to `MTLComputeCommandEncoder::dispatchThreads` — you launch `prod(grid)` **threads** (not threadgroups). "*For optimal performance, each thread group dimension should be less than or equal to the corresponding grid dimension.*"

`verbose=True` prints the full generated kernel source.

Helper functions go in `header=`:
```python
header = """
template <typename T>
T do_exp(T x) { return metal::precise::exp(x); }
"""
```

### 9.5 Custom CUDA kernels

`mx.fast.cuda_kernel(name, input_names, output_names, source, header="", ensure_row_contiguous=True, shared_memory=0)` — same call signature as `metal_kernel`. Grid is still **in threads** for API compatibility with `metal_kernel`.
```python
source = """
    auto elem = cooperative_groups::this_grid().thread_rank();
    T tmp = inp[elem];
    out[elem] = exp(tmp);
"""
```
CUDA-side strided access (from tests): `elem_to_loc(elem, inp_shape.data(), inp_strides.data(), inp_ndim)`; warp size constant is `WARP_SIZE`.

`mx.fast.precompiled_cuda_kernel(*, name, compiled_source: bytes, inputs, output_shapes, output_dtypes, scalars, grid, threadgroup, shared_memory=0, init_value=None, ensure_row_contiguous=False, stream=None)` — runs raw PTX/cubin. "*This op is still experimental and various parts of the API may change.*" `scalars` accepts only `bool`, `int`, `float`; anything else raises `"[precompiled_cuda_kernel] Invalid scalar argument type..."`.

---

## 10. Quantization

### 10.1 Modes table (verbatim from `python/src/ops.cpp:4649-4660`, the `quantize` docstring)

```
======  ======================   ==========================  =============  =====
mode    group size               bits                        scale type     bias
======  ======================   ==========================  =============  =====
affine  32, 64*, 128             2, 3, 4*, 5, 6, 8           same as input  yes
mxfp4   32*                      4*                          e8m0           no
mxfp8   32*                      8*                          e8m0           no
nvfp4   16*                      4*                          e4m3           no
======  ======================   ==========================  =============  =====
```
`*` = default when unspecified.

`mlx.nn.layers.quantized._defaults_for_mode` mirrors this:
```python
mode_defaults = {"affine": (64, 4), "mxfp4": (32, 4), "nvfp4": (16, 4), "mxfp8": (32, 8)}
```

Affine formula (verbatim from the docstring):
```
alpha = max_i w_i ;  beta = min_i w_i ;  s = (alpha - beta) / (2^b - 1)
w_hat_i = round((w_i - beta) / s)
dequantize:  w_i = s * w_hat_i + beta
```
Packing: "*`w_hat_i` fits in `b` bits and is packed in an unsigned 32-bit integer from the lower to upper bits. For instance, for 4-bit quantization we fit 8 elements in an unsigned 32 bit integer where the 1st element occupies the 4 least significant bits, the 2nd bits 4-7 etc.*"

FP modes: elements quantized to **E2M1** ("fp4") or **E4M3** ("fp8"), shared 8-bit scale per group — **E8M0** for the `mx*` modes, **E4M3** for `nvfp4`. No bias. MX spec link: OCP microscaling formats MX v1.0.

### 10.2 Python signatures (verbatim `nb::sig`)

```python
def quantize(w: array, /, group_size: Optional[int] = None, bits: Optional[int] = None,
             mode: str = 'affine', *, global_scale: Optional[array] = None,
             stream=None) -> tuple[array, array, array]

def dequantize(w: array, /, scales: array, biases: Optional[array] = None,
               group_size: Optional[int] = None, bits: Optional[int] = None,
               mode: str = 'affine', global_scale: Optional[array] = None,
               dtype: Optional[Dtype] = None, *, stream=None) -> array

def quantized_matmul(x: array, w: array, /, scales: array, biases: Optional[array] = None,
                     transpose: bool = True, group_size: Optional[int] = None,
                     bits: Optional[int] = None, mode: str = 'affine', *, stream=None) -> array

def gather_qmm(x: array, w: array, /, scales: array, biases: Optional[array] = None,
               lhs_indices: Optional[array] = None, rhs_indices: Optional[array] = None,
               transpose: bool = True, group_size: Optional[int] = None,
               bits: Optional[int] = None, mode: str = 'affine',
               *, sorted_indices: bool = False, stream=None) -> array

def qqmm(x: array, w: array, scales: Optional[array] = None, group_size: Optional[int] = None,
         bits: Optional[int] = None, mode: str = 'nvfp4',
         global_scale_x: Optional[array] = None, global_scale_w: Optional[array] = None,
         *, stream=None) -> array

def to_fp8(x: array, *, stream=None) -> array                       # -> uint8 E4M3
def from_fp8(x: array, dtype: Dtype = bfloat16, *, stream=None) -> array
```

C++ (`mlx/ops.h:1547-1611`) matches, with `mode` as `const std::string&` and `global_scale` as `std::optional<array>`.

### 10.3 `qqmm` — quantize-both-sides matmul (new)

Default mode is `"nvfp4"`; **only `nvfp4` and `mxfp8` are supported** (error `"[qqmm] Only 'nvfp4' and 'mxfp8' quantization modes are supported but '<mode>'"`). Key doc points:
- `x` is quantized **on the fly**; `w` is used as-is if already quantized (then `scales` is required and `group_size`/`bits`/`mode` must match), otherwise quantized on the fly.
- "*If `w` is expected to receive gradients, it must be provided in non-quantized form.*"
- Non-quantized dtypes must be `float32`/`float16`/`bfloat16`; quantized `w` must be packed in unsigned ints.
- Only 2D inputs (`"[qqmm] Only 2D inputs are supported"`).
- nvfp4 requires **either both or neither** of `global_scale_x` / `global_scale_w`.

Runnable example + numerical-tolerance discussion: `examples/python/qqmm.py`. Its header comment is a useful gotcha:
> "*In mxfp8 mode, the results do not match exactly: fewer than 1% of output elements differ. ... The error can exceed 1 ULP for very small values, and is always below 1 ULP for larger values. For nvfp4, the results match exactly.*"

VJP pattern verified in `examples/python/qqmm.py:80-112`: `mx.vjp(lambda x: mx.qqmm(x, w, ...), primals=(x,), cotangents=(c,))` equals `mx.qqmm(c, quantize(w.T))`.

### 10.4 Validation errors worth knowing (`mlx/ops.cpp`)

- `"[quantize] The requested group size <g> is not supported. The supported group sizes are 32, 64, and 128."` (affine)
- `"[quantize] The requested number of bits <b> is not supported. The supported bits are 2, 3, 4, 5, 6 and 8."` (note **7 is explicitly excluded**: `bits < 2 || bits > 8 || bits == 7`)
- `"[quantize] <mode> quantization requires group size <16|32> but got <g>."` / `"... requires bits to be <4|8> but got <b>."`
- `"[quantize] The matrix to be quantized must have at least 2 dimension"`
- `"[quantize] The last dimension of the matrix needs to be divisible by <group_size>"`
- **`"[quantize] Global scale is not supported on the Metal backend."`** — `global_scale` (nvfp4) is CUDA-only.
- `"[dequantize] The matrix should be given as a uint32"`
- `dequantize` return dtype: "*If `None` the return type is inferred from the scales and biases when possible and otherwise defaults to `bfloat16`.*"

Metal TF32 gating on quantized matmuls: `env::enable_tf32()` (env `MLX_ENABLE_TF32`, default **1**) is consulted in `mlx/backend/metal/quantized.cpp:788,983,1328` and `matmul.cpp`. Tests force `MLX_ENABLE_TF32=0` (`python/tests/mlx_tests.py:6`).

### 10.5 `mlx.nn` quantization layers (`python/mlx/nn/layers/quantized.py`)

```python
nn.quantize(model, group_size=None, bits=None, *, mode="affine",
            quantize_input=False, class_predicate=None)
```
- Default predicate: every leaf module that defines `to_quantized()`.
- `class_predicate(path, module)` may return `True`/`False` **or a dict of kwargs** forwarded to `to_quantized`.
- "*`quantize_input=True` is only supported for `"nvfp4"` and `"mxfp8"` modes and `Linear` layers.*"
- Modifies the model **in place** (`model.update_modules(leaves)`).

Examples from the docstring:
```python
nn.quantize(model, group_size=64, bits=4, mode="affine")

predicate = lambda p, m: isinstance(m, nn.Linear)
nn.quantize(model, mode="nvfp4", quantize_input=True, class_predicate=predicate)
```

Classes:
- `nn.QuantizedLinear(input_dims, output_dims, bias=True, group_size=None, bits=None, mode="affine")` — **parameters are frozen** (`self.freeze()` in `__init__`); classmethod `from_linear(linear_layer, group_size=None, bits=None, mode="affine")`.
- `nn.QuantizedEmbedding(num_embeddings, dims, group_size=None, bits=None, mode="affine")` — frozen; `.as_linear(x)` for tied embeddings; `from_embedding(...)`.
- `nn.QQLinear(input_dims, output_dims, group_size=None, bits=None, mode="nvfp4")` — **quantizes activations too**; **no bias support** (`from_linear` raises `NotImplementedError("QQLinear does not support bias yet.")`). Switching train/eval quantizes/dequantizes the stored weight:
  ```python
  def _set_training_mode(self, mode):
      super()._set_training_mode(mode)
      if self._training: self.dequantize()
      else:              self.quantize()
  ```
  i.e. `layer.eval()` packs weights; `layer.train()` unpacks so gradients flow.

`QuantizedLinear._extra_repr` reconstructs the logical `in_dims` as `(in_dims * 32) // self.bits` — reminder that the stored weight's last dim is packed uint32.

---

## 11. Operations catalogue

Full list from `docs/src/python/ops.rst` (211 lines) — everything is `mlx.core.*`:

```
abs add addmm all allclose any arange arccos arccosh arcsin arcsinh arctan arctan2
argmax argmin argpartition argsort array_equal asarray as_strided astype
atleast_1d atleast_2d atleast_3d bartlett bitwise_and bitwise_invert bitwise_or
bitwise_xor blackman block_masked_mm broadcast_arrays broadcast_shapes broadcast_to
can_cast ceil clip concat concatenate contiguous conj conjugate convolve conv1d conv2d
conv3d conv_transpose1d conv_transpose2d conv_transpose3d conv_general cos cosh
cummax cummin cumprod cumsum count_nonzero degrees depends dequantize diag diagonal
diff divide divmod einsum einsum_path equal erf erfinv exp expm1 expand_dims eye
flatten flip floor floor_divide full from_dlpack full_like from_fp8 gather_mm gather_qmm
greater greater_equal hadamard_transform hamming hanning identity imag inner isdtype
isfinite isclose isinf isnan isneginf isposinf issubdtype kron left_shift less
less_equal linspace load log log2 log10 log1p logaddexp logcumsumexp logical_not
logical_and logical_or logical_xor logsumexp matmul max maximum mean median meshgrid
min minimum moveaxis multiply nan_to_num negative not_equal ones ones_like outer
partition pad permute_dims positive power prod put_along_axis quantize quantized_matmul
qqmm radians real reciprocal remainder repeat reshape result_type right_shift roll
round rsqrt save savez savez_compressed save_gguf save_safetensors sigmoid sign sin
sinh slice slice_update segmented_mm softmax sort split sqrt square squeeze stack std
stop_gradient subtract sum swapaxes take take_along_axis tan tanh tensordot tile topk
to_fp8 trace transpose tri tril triu trunc unflatten unstack vecdot var view where
zeros zeros_like
```

### 11.1 Array-API standard aliases (`python/src/ops.cpp`, end of `init_ops`)

```python
mx.acos = mx.arccos           mx.acosh = mx.arccosh
mx.asin = mx.arcsin           mx.asinh = mx.arcsinh
mx.atan = mx.arctan           mx.atanh = mx.arctanh
mx.atan2 = mx.arctan2
mx.bitwise_left_shift  = mx.left_shift
mx.bitwise_right_shift = mx.right_shift
mx.cumulative_prod = mx.cumprod
mx.cumulative_sum  = mx.cumsum
mx.empty      = mx.zeros      # !!! `empty` is an alias for `zeros`
mx.empty_like = mx.zeros_like
mx.matrix_transpose = mx.transpose
mx.pow = mx.power
```
**Gotcha:** `mx.empty` allocates *zeroed* memory (it is literally `mx.zeros`), unlike NumPy.

### 11.2 Notable matmul-family ops (C++ signatures, `mlx/ops.h`)

```cpp
array addmm(array c, array a, array b, const float& alpha = 1.f, const float& beta = 1.f, StreamOrDevice s = {});   // D = beta*C + alpha*(A@B)
array block_masked_mm(array a, array b, int block_size,
    std::optional<array> mask_out = {}, std::optional<array> mask_lhs = {}, std::optional<array> mask_rhs = {}, StreamOrDevice s = {});
array gather_mm(array a, array b, std::optional<array> lhs_indices = {},
    std::optional<array> rhs_indices = {}, bool sorted_indices = false, StreamOrDevice s = {});
array segmented_mm(array a, array b, array segments, StreamOrDevice s = {});
array tensordot(const array& a, const array& b, const int axis = 2, StreamOrDevice s = {});
array tensordot(const array& a, const array& b, const std::vector<int>& axes_a, const std::vector<int>& axes_b, StreamOrDevice s = {});
array outer(const array& a, const array& b, StreamOrDevice s = {});
array inner(const array& a, const array& b, StreamOrDevice s = {});
array vecdot(const array& a, const array& b, int axis = -1, StreamOrDevice s = {});
```
`segmented_mm(a: MxK, b: KxN, segments)` → "*The offsets into the inner dimension for each segment*"; result per segment of shape `MxN`.

`gather_mm`/`gather_qmm`: "*the indices `lhs_indices` and `rhs_indices` contain flat indices along the batch dimensions (i.e. all but the last two dimensions)*". `sorted_indices=True` "*may allow a faster implementation*". For `gather_qmm`, "*`scales` and `biases` must have the same batch dimensions as `w`*".

### 11.3 Layout / view ops

```python
def contiguous(a: array, /, allow_col_major: bool = False, *, stream=None) -> array
def as_strided(a: array, /, shape=None, strides=None, offset: int = 0, *, stream=None) -> array
def view(a, dtype: Dtype, stream=None) -> array
def hadamard_transform(a: array, scale: Optional[float] = None, stream=None) -> array
```
- `contiguous`: "*Force an array to be row contiguous. Copy if necessary.*"
- `as_strided`: "*The resulting array will always be as if the provided array was row contiguous regardless of the provided array's storage order and current strides.*" ⚠ "*can lead to the resulting array pointing to invalid memory locations which can result into crashes.*" Default strides = reverse exclusive cumprod of the shape.
- `view`: "*the view op does not imply that the input and output arrays share their underlying data. The view only guarantees that the binary representation of each element (or group of elements) is the same.*" Output shape changes along the last axis when item sizes differ.
- `hadamard_transform`: supports `n = m*2^k` for `m ∈ (1, 12, 20, 28)` with `2^k <= 8192` (float32) / `2^k <= 16384` (float16/bfloat16). Default `scale = 1/sqrt(a.shape[-1])`.

### 11.4 Indexing (docs/src/usage/indexing.rst)

NumPy-like: ints, slices with stride, `...`/`Ellipsis`, `None` (new axis), integer arrays. **Two important differences:**

> "*Indexing does not perform bounds checking. Indexing out of bounds is undefined behavior.*"
> Reason: "*exceptions cannot propagate from the GPU. Performing bounds checking for array indices before launching the kernel would be extremely inefficient.*"

> "*Boolean mask based indexing is supported for assignment only.*"

Other differences:
- **Slicing copies**, it is not a view: `b = a[:]; b[2] = 0` leaves `a` unchanged. But `b = a` (aliasing) *does* share.
- Duplicate-index in-place updates are **nondeterministic**: `a[[0,0]] = mx.array([4,5])` → first element could be 4 or 5.
- No `numpy.nonzero`, no single-input `numpy.where` — "*MLX has limited support for operations for which output shapes are dependent on input data.*"

Boolean-mask assignment rules (docs lines 148–194):
- Mask must be an MLX `bool_` array or NumPy `ndarray` with `dtype=bool`.
- Mask shape must match the indexed axes exactly; scalar bool masks broadcast to the whole array.
- Uncovered trailing axes are taken in full: `a` of shape `(10,10,10)` with a `(10,10)` mask selects the 1-D slices `a[i,j,:]`.
- Shapes like `(1,10,10)` or `(10,10,1)` raise.
- Non-scalar `updates` must have at least as many elements as `True` entries.

`array.at` scatter API (`python/src/array.cpp:430`):
```python
x = x.at[idx].add(y)        # vs x[idx] += y
x = x.at[idx].subtract(y)
x = x.at[idx].multiply(y)
x = x.at[idx].divide(y)
x = x.at[idx].maximum(y)
x = x.at[idx].minimum(y)
```
> "*Regular in-place updates map to assignment. For instance `x[idx] += y` maps to `x[idx] = x[idx] + y`. As a result, assigning to the same index ignores all but one update. Using `x.at[idx].add(y)` will correctly apply all updates to all indices.*"
```python
>>> a = mx.array([0, 0]); idx = mx.array([0, 1, 0, 1])
>>> a[idx] += 1; a          # array([1, 1], dtype=int32)
>>> a = mx.array([0, 0]); a.at[idx].add(1)   # array([2, 2], dtype=int32)
```

Gradients through in-place updates work:
```python
def fun(x, idx):
    x[idx] = 2.0
    return x.sum()
mx.grad(fun)(mx.array([1.0, 2.0, 3.0]), mx.array([1]))   # array([1, 0, 1], dtype=float32)
```

---

## 12. Data types

`docs/src/python/data_types.rst` — defaults: **float32** for floats, **int32** for ints.

| Type | Bytes | Description |
|---|---|---|
| `bool_` | 1 | Boolean |
| `uint8/16/32/64` | 1/2/4/8 | unsigned int |
| `int8/16/32/64` | 1/2/4/8 | signed int |
| `bfloat16` | 2 | brain float (e8, m7) |
| `float16` | 2 | IEEE half (e5, m10) |
| `float32` | 4 | |
| `float64` | 8 | **CPU only — "Using `float64` arrays on the GPU will result in an exception."** |
| `complex64` | 8 | |

`Dtype::Category` hierarchy (`mlx/dtype.h:42-49`): `complexfloating, floating, inexact, signedinteger, unsignedinteger, integer, number, generic`. Use `mx.issubdtype(dtype_or_category, category)`. Also exposed: `mx.Dtype`, `mx.DtypeCategory`, `mx.finfo`, `mx.isdtype`, `mx.can_cast`, `mx.result_type`.

Constants (`python/src/constants.cpp`): `mx.e`, `mx.euler_gamma`, `mx.inf`, `mx.nan`, `mx.newaxis` (= `None`), `mx.pi`. `mx.__version__` comes from `mx::version()`.

---

## 13. NumPy / PyTorch / JAX / TF interop, and zero-copy

From `docs/src/usage/numpy.rst`:
- Two mechanisms: **Python buffer protocol** and **DLPack**.
- NumPy has no bfloat16: convert first (`np.array(a.astype(mx.float32))`) or you get `Item size 2 for PEP 3118 buffer format string does not match the dtype V item size 0.`
- `np.array(a, copy=False)` makes a **view** into MLX memory (`a_view.flags.owndata == False`); writes are visible in the MLX array.
- NumPy `float64` → MLX `float32` by default.
- ⚠ **Gradients don't see external memory mutations**:
  ```python
  def f(x):
      x_view = np.array(x, copy=False)
      x_view[:] *= x_view          # modify memory without telling mx
      return x.sum()
  y, df = mx.value_and_grad(f)(mx.array([3.0]))
  # y == 9.0 but df == 1.0  (wrong: 2x expected)
  ```

**PyTorch (as of this tree):**
- `torch.as_tensor(mlx_array)` = zero-copy DLPack import; `torch.tensor(...)` copies.
- `mx.asarray(torch_tensor)` / `mx.from_dlpack(...)` share when possible; `mx.array(...)` always copies.
- CPU torch tensors → MLX **always copies** ("The arrays do not share memory").
- Metal/MPS DLPack: with `copy=None`, MLX imports without a copy **if the underlying Metal buffer is not private**; private buffers are copied. `copy=False` raises if a copy would be needed; `copy=True` forces a new array. Zero-copy imports **preserve DLPack strides**.
- **"PyTorch 2.12 and later use shared storage for ordinary MPS tensors on Apple silicon, while older PyTorch versions may use private storage and require a copy on import."**
- ⚠ "*DLPack conversion does not synchronize pending Metal work; synchronize or evaluate the producing framework before reading the converted array.*" → call `torch.mps.synchronize()` / `mx.eval(...)` first.

JAX: full buffer-protocol support (`jnp.array(mx_arr)`, `mx.array(jax_arr)`).
TensorFlow: needs an explicit memoryview — `tf.constant(memoryview(a))`.

### Zero-copy CPU import (commit `0c537a4`, July 2026)

`mx.asarray(host_buffer, copy=False)` **adopts** a page-aligned CPU buffer on unified memory (Metal). Constraints extracted from `python/tests/test_zero_copy.py`:
- Requires Metal (`mx.metal.is_available()`), otherwise `copy=False` raises.
- Source buffer must be **page aligned**: the test checks `a.ctypes.data % 16384 == 0` (16 KiB pages).
- `copy=False` + dtype conversion raises (`mx.asarray(np_float64, dtype=mx.float32, copy=False)`).
- Adopted buffers are visible both ways: `a[1] = 999; mx.eval(x); x[1] == 999`.
- Regression noted in the test: "*an adopted buffer must be released (not recycled into the allocator's reuse pool) when freed. Otherwise, over many iterations the pool hands a caller-owned buffer to an unrelated array and corrupts / crashes.*"

Python signatures:
```python
def asarray(a, dtype: Optional[Dtype] = None, *, copy: Optional[bool] = None) -> array
def from_dlpack(x, /, *, copy: Optional[bool] = None) -> array
```
`copy` semantics: `True` = always copy, `False` = never copy (raises `ValueError` if needed), `None` = share when possible.

---

## 14. Saving / loading

`docs/src/usage/saving_and_loading.rst`:

| Format | Ext | Function | Notes |
|---|---|---|---|
| NumPy | `.npy` | `mx.save` | single array |
| NumPy archive | `.npz` | `mx.savez`, `mx.savez_compressed` | multiple |
| Safetensors | `.safetensors` | `mx.save_safetensors` | multiple |
| GGUF | `.gguf` | `mx.save_gguf` | multiple |

`mx.load(path)` dispatches on extension. `mx.save("array", a)` writes `array.npy` (extension auto-added). `mx.savez` takes arrays positionally (auto-named `arr_0`, ...) or as kwargs; `save_safetensors`/`save_gguf` take a `dict[str, array]`.

C++ (`mlx/io.h`) additionally exposes stream-based overloads, `load_safetensors` returning `pair<map<string,array>, map<string,string>>` (arrays + metadata), and `load_gguf` returning arrays + `GGUFMetaData` (`monostate | array | string | vector<string>`). `save_safetensors` accepts a `metadata` map.

Gotcha fixed recently: `8573c35 Fix int64 type cast error when loading GGUF metadata arrays (#3823)`.

---

## 15. `mlx.nn`

### 15.1 `Module` semantics (`python/mlx/nn/layers/base.py`)

**`class Module(dict)`** — a Module *is* a dict.

- `__setattr__`: values of type `mx.array | dict | list | tuple` are stored **in the dict** (and therefore become part of the parameter tree); everything else goes to normal `__dict__` and is popped from the dict.
- A **parameter** is "any public member of type `mx.core.array` (its name should not start with `_`)", arbitrarily nested in Modules/lists/dicts (`valid_parameter_filter`: `isinstance(value, (dict, list, mx.array)) and not key.startswith("_")`).
- `Module.state` returns `self` — "*Unlike `Module.parameters`, the `Module.state` property is a reference to the module's state. Updates to it will be reflected in the original module.*"

Method surface:
| Method | Notes |
|---|---|
| `parameters()` | recursive dict/list tree of all arrays |
| `trainable_parameters()` | excludes keys in `_no_grad` |
| `children()` | direct descendants |
| `leaf_modules()` | submodules with no submodules |
| `filter_and_map(filter_fn, map_fn=None, is_leaf_fn=None)` | the generic primitive behind the above |
| `update(parameters: dict, strict=True) -> Module` | partial trees allowed; `strict` checks it's a subset |
| `update_modules(modules: dict, strict=True) -> Module` | swap submodules programmatically |
| `apply(map_fn, filter_fn=None) -> Module` | e.g. `model.apply(lambda x: x.astype(mx.float16))` |
| `apply_to_modules(apply_fn(path, module)) -> Module` | paths like `"model.layers.0.linear"` |
| `modules()`, `named_modules()` | |
| `freeze(*, recurse=True, keys=None, strict=False)` | idempotent; `module.freeze(keys="bias")` |
| `unfreeze(*, recurse=True, keys=None, strict=False)` | |
| `train(mode=True)`, `eval()` | sets `_training` recursively |
| `set_dtype(dtype, predicate=lambda x: mx.issubdtype(x, mx.floating))` | default predicate avoids casting int params |
| `load_weights(file_or_weights, strict=True) -> Module` | `.npz` / `.safetensors` / `list[(name, array)]` |
| `save_weights(file)` | `.npz` → `mx.savez`, `.safetensors` → `mx.save_safetensors`, else `ValueError` |

`load_weights(strict=True)` raises with counts: `"Received {n} parameters not in model: \n{...}"`, `"Missing {n} parameters: \n{...}"`, `"Expected shape {v.shape} but received shape {v_new.shape} for parameter {k}"`.

Freeze idiom from the docstring:
```python
model = nn.Transformer()
model.freeze()
model.apply_to_modules(lambda k, v: v.unfreeze() if k.endswith("attention") else None)
```

`nn.value_and_grad(model, fn)` implementation (python/mlx/nn/utils.py:12-38) — worth reading since it explains the pattern:
```python
def inner_fn(params, *args, **kwargs):
    model.update(params)
    return fn(*args, **kwargs)
value_grad_fn = mx.value_and_grad(inner_fn)
# call site passes model.trainable_parameters() as arg 0
```

Repr example (docs/src/python/nn.rst):
```
MLP(
  (layers.0): Linear(input_dims=2, output_dims=128, bias=True)
  ...
)
```
Parameter counting idiom:
```python
from mlx.utils import tree_flatten
num_params = sum(v.size for _, v in tree_flatten(mlp.parameters()))
```

### 15.2 Layers exported by `mlx.nn` (from `python/mlx/nn/layers/__init__.py` + `docs/src/python/nn/layers.rst`)

`ALiBi, AllToShardedLinear, AvgPool1d/2d/3d, BatchNorm, Bilinear, CELU, Conv1d/2d/3d, ConvTranspose1d/2d/3d, Dropout, Dropout2d, Dropout3d, ELU, Embedding, FullyShardedModule, GELU, GLU, GroupNorm, GRU, HardShrink, HardTanh, Hardswish, Identity, InstanceNorm, LayerNorm, LeakyReLU, Linear, LogSigmoid, LogSoftmax, LSTM, MaxPool1d/2d/3d, Mish, Module, MultiHeadAttention, PReLU, QQLinear, QuantizedAllToShardedLinear, QuantizedEmbedding, QuantizedLinear, QuantizedShardedToAllLinear, ReLU, ReLU2, ReLU6, RMSNorm, RNN, RoPE, SELU, Sequential, ShardedToAllLinear, Sigmoid, SiLU, SinusoidalPositionalEncoding, Softmax, Softmin, Softplus, Softshrink, Softsign, Step, Tanh, Transformer, TransformerDecoder, TransformerDecoderLayer, TransformerEncoder, TransformerEncoderLayer, Upsample`

Functional forms: `celu, elu, gelu, gelu_approx, gelu_fast_approx, glu, hard_shrink, hard_tanh, hardswish, leaky_relu, log_sigmoid, log_softmax, mish, prelu, relu, relu2, relu6, selu, sigmoid, silu, softmax, softmin, softplus, softshrink, step, tanh`

Losses (`mlx.nn.losses`): `binary_cross_entropy, cosine_similarity_loss, cross_entropy, gaussian_nll_loss, hinge_loss, huber_loss, kl_div_loss, l1_loss, log_cosh_loss, margin_ranking_loss, mse_loss, nll_loss, smooth_l1_loss, triplet_loss` (+ internal `_reduce(loss, reduction="none")`).

Initializers (`mlx.nn.init`): `constant, normal, uniform, identity, glorot_normal, glorot_uniform, he_normal, he_uniform, sparse, orthogonal`. They return functions:
```python
init_fn = nn.init.uniform(low=-0.1, high=0.1)
model.apply(init_fn)
```

`nn.RoPE(dims, traditional=False, base=10000, scale=1.0)`; `__call__(x, offset: int = 0)` delegates to `mx.fast.rope`.
`nn.SinusoidalPositionalEncoding(dims, min_freq=0.0001, max_freq=1, scale=None, cos_first=False, full_turns=False)` — raises if `dims <= 0 or dims % 2 != 0`.

### 15.3 `mlx.nn` distributed helpers

`python/mlx/nn/layers/distributed.py` exports `AllToShardedLinear`, `ShardedToAllLinear`, `QuantizedAllToShardedLinear`, `QuantizedShardedToAllLinear`, `FullyShardedModule`, `fully_shard`, plus helper routines `shard_linear`, `shard_inplace`, `sum_gradients`.

- **`AllToShardedLinear`** (column-parallel): replicates the input, shards the weight along the **output** dim, returns a *sharded* output. Does **not** all-gather.
- **`ShardedToAllLinear`** (row-parallel): expects an input sharded along the feature dim, shards the weight along the **input** dim, and **does** `all_sum` so all ranks get the same result. Does **not** shard the input for you.
- Design rationale (docs): pairing all-to-sharded → sharded-to-all removes the intermediate gather.
- Quantized variants have frozen params (no gradients).
- `shard_linear(layer, "all-to-sharded"|"sharded-to-all", group=...)` returns a **new** layer; `shard_inplace(...)` mutates and adds no communication.

Llama TP recipe (docs/src/examples/tensor_parallelism.rst):
```python
def shard(self, group: mx.distributed.Group):
    self.n_heads = self.n_heads // group.size()
    self.n_kv_heads = self.n_kv_heads // group.size()
    self.wq = nn.layers.distributed.shard_linear(self.wq, "all-to-sharded", group=group)
    self.wk = nn.layers.distributed.shard_linear(self.wk, "all-to-sharded", group=group)
    self.wv = nn.layers.distributed.shard_linear(self.wv, "all-to-sharded", group=group)
    self.wo = nn.layers.distributed.shard_linear(self.wo, "sharded-to-all", group=group)
```
Then `mlx.launch -n 2 llama.py`.

**FSDP:** `nn.fully_shard(module, *, group=None, compute_dtype=None)`.
- Every parameter is sharded along **axis 0**; `a.shape[0] % group.size() must == 0` else `ValueError: Cannot shard parameter '<path>' with shape ... across N devices: axis 0 must be divisible by N.`
- Scalars can't be sharded: `ValueError: Cannot shard parameter '<path>' because it is a scalar.`
- Params are gathered for forward, reduce-scattered on backward; only the local shard is stored/updated.
- Returns `module` unchanged if `group.size() == 1`, if already wrapped, or if nothing was shardable.
- `compute_dtype` casts gathered params for the forward pass.
- Companion: `mlx.nn.utils.clip_grad_norm_sharded(gradients, max_norm, group=None) -> (clipped, grad_norm)` — sums local squared norms across the group before rescaling.
- Related in-flight work: commit `8f64abc [WIP] [CUDA] fsdp (#3768)`.

`nn.average_gradients(gradients, group=None, all_reduce_size=32*1024**2, communication_stream=None)`:
- Concatenates gradient groups until they exceed `all_reduce_size` bytes, does one `all_sum` per group, then splits back. `all_reduce_size <= 0` disables grouping.
- Falls back to ungrouped mode if the tree has mixed dtypes.

---

## 16. `mlx.optimizers`

Base `Optimizer` (`python/mlx/optimizers/optimizers.py`):
```python
class Optimizer:
    def __init__(self, schedulers=None):
        self._initialized = False
        self._state = {"step": mx.array(0, mx.uint64)}
        self._schedulers = {...}
    def update(self, model: Module, gradients: dict)      # model.update(self.apply_gradients(grads, model))
    def init(self, parameters: dict)
    def init_single(self, parameter, state)               # override
    def apply_gradients(self, gradients: dict, parameters: dict)
    def apply_single(self, gradient, parameter, state)    # override
    @property state / step / learning_rate
```
- `state` setter resets `_initialized = False`.
- `apply_gradients` first runs schedulers (`self.state[param] = scheduler(self.step)`), then increments `step`, then `tree_map(self.apply_single, gradients, parameters, self.state)`.
- `learning_rate` setter wraps in `mx.array`.
- `parameters` may be a **superset** of `gradients`; the returned tree matches the gradient tree.

`Optimizer.init` docstring example:
```python
>>> optimizer = optim.SGD(learning_rate=1e-1, momentum=0.9)
>>> model = nn.Linear(2, 2)
>>> optimizer.init(model.trainable_parameters())
>>> optimizer.state.keys()
dict_keys(['step', 'learning_rate', 'weight', 'bias'])
```

Optimizers: `SGD, RMSprop, Adagrad, AdaDelta, Adam, AdamW, Adamax, Lion, Adafactor, Muon, MultiOptimizer`. Plus `clip_grad_norm(grads, max_norm) -> (clipped_grads, total_norm)`.

Exact constructors read:
```python
SGD(learning_rate, momentum=0.0, weight_decay=0.0, dampening=0.0, nesterov=False)
  # raises ValueError if nesterov and (momentum <= 0 or dampening != 0)
Muon(learning_rate, momentum=0.95, weight_decay=0.01, nesterov=True, ns_steps=5)
MultiOptimizer(optimizers: list, filters: list = [])   # len(filters) == len(optimizers) - 1
```
`Muon` notes (verbatim): "*Muon may be sub-optimal for the embedding layer, the final fully connected layer, or any 0D/1D parameters. Those should be optimized by a different method (e.g., `AdamW`).*" and "*For 4D convolutional filters, it works by flattening their last dimensions.*" Newton-Schulz coefficients: `a, b, c = (3.4445, -4.7750, 2.0315)`; scaling `lr *= max(1, update.shape[-2]/update.shape[-1]) ** 0.5`.

`MultiOptimizer`: predicates take `(path, weight)`, the **last** optimizer is the fallback and gets no predicate; `state` is `{"states": [...]}`.

Schedulers (`python/mlx/optimizers/schedulers.py`): `exponential_decay(init, decay_rate)`, `step_decay(init, decay_rate, step_size)`, `cosine_decay(init, decay_steps, end=0.0)`, `join_schedules(schedules, boundaries)`, `linear_schedule(init, end, steps)`.

**Serialization note (docs/src/python/optimizers.rst):** "*not every optimizer configuration parameter is saved in the state. For example, for Adam the learning rate is saved but the `betas` and `eps` parameters are not. A good rule of thumb is if the parameter can be scheduled then it will be included in the optimizer state.*"
```python
state = tree_flatten(optimizer.state, destination={})
mx.save_safetensors("optimizer.safetensors", state)
# later
optimizer = optim.Adam(learning_rate=1e-2)
optimizer.state = tree_unflatten(mx.load("optimizer.safetensors"))
```

---

## 17. Tree utilities (`mlx.utils`)

```python
tree_map(fn, tree, *rest, is_leaf=None)
tree_map_with_path(fn, tree, *rest, is_leaf=None, path=None)     # fn(path, leaf, *rest)
tree_flatten(tree, prefix="", is_leaf=None, destination=None)     # -> list[(str, Any)] or dict
tree_unflatten(tree)                                              # accepts list of pairs or dict
tree_reduce(fn, tree, initializer=None, is_leaf=None)
tree_merge(tree_a, tree_b, merge_fn=None)                         # "deep dict.update"
```
- A "tree" = arbitrarily nested `dict`/`list`/`tuple` without cycles.
- "*Dictionaries should have keys that are valid Python identifiers.*"
- `tree_flatten(..., destination={})` yields a flat **dict** (`{"a.b": 1}`) instead of a list — used by `Module.save_weights` and the optimizer serialization recipe.
- `tree_flatten(prefix=".hello")` → keys prefixed `hello.` (first char always discarded).
- `tree_map` is "*closer to `itertools.starmap` than to `map`*" — `rest` trees must be supersets.
- `tree_merge` raises if leaves collide and no `merge_fn` given.
- NamedTuples are preserved (`TreeType(*subtrees) if hasattr(tree, "_fields")`).

---

## 18. Distributed

### 18.1 Backends

| Backend | Description (verbatim from docs) |
|---|---|
| MPI | "A full featured and mature distributed communications library." |
| RING | "Ring all reduce and all gather over TCP sockets. Always available and usually faster than MPI." |
| JACCL | "Low latency communication with RDMA over thunderbolt. Necessary for things like tensor parallelism." |
| NCCL | "The backend of choice for CUDA environments." |

### 18.2 API

```python
mx.distributed.init(strict: bool = False, backend: str = 'any') -> Group
mx.distributed.is_available(backend: str = 'any') -> bool
Group.rank() -> int ; Group.size() -> int ; Group.split(color: int, key: int = -1) -> Group

mx.distributed.all_sum(x, *, group=None, stream=None)
mx.distributed.all_max(x, *, group=None, stream=None)
mx.distributed.all_min(x, *, group=None, stream=None)
mx.distributed.all_gather(x, *, group=None, stream=None)
mx.distributed.sum_scatter(x, *, group=None, stream=None)
mx.distributed.send(x, dst: int, *, group=None, stream=None)
mx.distributed.recv(shape, dtype, src: int, *, group=None, stream=None)
mx.distributed.recv_like(x, src: int, *, group=None, stream=None)
```
Backend selection strings: `{'any', 'ring', 'jaccl', 'mpi', 'nccl'}`.

**Semantics:**
- All ops are **no-ops when the group size is 1** — so you never need `if world.size() > 1:` guards.
- "*After a distributed backend is successfully initialized `init` will return **the same backend** if called without arguments or with backend set to `any`.*" So `init(backend="mpi")` then `init()` returns MPI.
- Ring backend: only neighbour communication — "*`send` and `recv` with arbitrary sender and receiver are not supported in the ring backend.*"
- `Group.split(color, key=-1)`: same color → same subgroup; smaller key → smaller rank; negative key uses the current rank.

### 18.3 `mlx.launch` CLI (exact argparse from `python/mlx/_distributed_utils/launch.py:457-563`)

```
mlx.launch [--print-python] [--verbose]
           [--hosts HOSTS]                 default 127.0.0.1, comma-separated
           [--repeat-hosts N | -n N]       default 1, positive int
           [--hostfile HOSTFILE]
           [--backend BACKEND]             ring | mpi | nccl | jaccl | jaccl-ring
           [--env KEY=VAL]                 repeatable
           [--mpi-arg ARG]                 repeatable, passed to mpirun
           [--connections-per-ip N]        default 1 (ring)
           [--starting-port PORT | -p]     default 32323 (ring)
           [--cwd DIR]
           [--nccl-port PORT]              default 12345
           [--python PATH]                 default sys.executable
           -- <script or command> [args...]
```
- Default backend: `"nccl" if mx.cuda.is_available() else "ring"`; a hostfile can also declare a backend.
- Invalid backend error: `"The backend should be one of {'ring', 'mpi', 'nccl', 'jaccl', 'jaccl-ring'}"`.
- `mlx.launch` broadcasts stdin to all processes and gathers stdout/stderr → `pdb` works across ranks. It kills the rest if one fails.
- It injects `COLUMNS`/`LINES` from the terminal size.
- ⚠ `--no-verify-script` is documented in `launching_distributed.rst` but **does not appear in the argparse list I read** — likely handled elsewhere or a doc/code drift. Mark **UNVERIFIED**.

Examples:
```bash
mlx.launch -n 4 my_script.py
mlx.launch --hosts ip1,ip2,ip3,ip4 my_script.py
mlx.launch --backend mpi -n 2 test.py
mlx.launch --backend nccl --hosts linux-1,linux-2 -n 8 --no-verify-script -- ./my-job.sh
mlx.launch --backend mpi --mpi-arg '--mca btl_tcp_if_include en0' --hostfile hosts.json my_script.py
mlx.launch --verbose --backend jaccl --hostfile m3-ultra-jaccl.json \
    --env MLX_METAL_FAST_SYNCH=1 -- \
    /path/to/remote/python -m mlx_lm chat --model mlx-community/DeepSeek-R1-0528-4bit
```

### 18.4 `mlx.distributed_config` CLI (argparse from `python/mlx/_distributed_utils/config.py:568-616`)

```
mlx.distributed_config [--verbose] [--hosts HOSTS] [--ignore-unreachable]
                       [--hostfile HOSTFILE]
                       [--over {thunderbolt,ethernet}]   default thunderbolt
                       [--output-hostfile PATH]
                       [--auto-setup | --no-auto-setup]
                       [--dot]
                       [--backend {ring,jaccl,jaccl-ring}]
                       [--env KEY=VAL]
```
⚠ **Doc/code drift:** `docs/src/usage/distributed.rst` and `launching_distributed.rst` both show `--output m3-ultra-jaccl.json`, but the argparse flag is **`--output-hostfile`**. Trust the code.

What it does (steps listed in launching_distributed.rst):
1. ssh to all nodes; 2. extract thunderbolt connectivity; 3. verify a valid mesh (JACCL) or ring; 4. check RDMA enabled; 5. extract the `en0` Ethernet IP; 6. disable the thunderbolt bridge + set up per-cable P2P networks; 7. write the hostfile.

`--auto-setup` requires password-less sudo; otherwise it prints the commands.
`--dot` emits GraphViz: `mlx.distributed_config --verbose --hosts h1,h2,h3,h4 --over thunderbolt --dot | dot -Tpng | open -f -a Preview`.

### 18.5 JACCL (RDMA over Thunderbolt) — new in this era

> "*Starting from macOS 26.2, RDMA over thunderbolt is available and enables low-latency communication between Macs with thunderbolt 5. MLX provides the JACCL backend that uses this functionality to achieve communication latency an order of magnitude lower than the ring backend.*"

> "*The name JACCL (pronounced Jackal) stands for Jack and Angelos' Collective Communication Library ... tribute to Jack Beasley who led the development of RDMA over Thunderbolt at Apple.*"

Enabling RDMA (cannot be done remotely, must be done in **macOS Recovery**):
1. Start in recovery; 2. Utilities → Terminal; 3. `rdma_ctl enable`; 4. Reboot.
Verify with `ibv_devices` → lists `rdma_en2`…`rdma_en7` with node GUIDs on an M3 Ultra.

**JACCL requires a fully connected mesh** — a Thunderbolt cable between every pair of Macs.

Hostfile schema:
```json
[
  {"ssh": "m3-ultra-1", "ips": ["123.123.123.1"], "rdma": [null, "rdma_en5", "rdma_en4", "rdma_en3"]},
  {"ssh": "m3-ultra-2", "ips": [],                "rdma": ["rdma_en5", null, "rdma_en3", "rdma_en4"]},
  {"ssh": "m3-ultra-3", "ips": [],                "rdma": ["rdma_en4", "rdma_en3", null, "rdma_en5"]},
  {"ssh": "m3-ultra-4", "ips": [],                "rdma": ["rdma_en3", "rdma_en4", "rdma_en5", null]}
]
```
Even though TCP/IP isn't used for the data path, you still must disable the Thunderbolt bridge and set up isolated local networks per cable.

> Important perf note (verbatim): "*Defining the environment variable `MLX_METAL_FAST_SYNCH=1` enables a different, faster way of synchronizing between the GPU and the CPU. It is not specific to the JACCL backend and can be used in all cases where the CPU and GPU need to collaborate for some computation and is pretty critical for low-latency communication since the communication is done by the CPU.*"

### 18.6 Running without `mlx.launch` — required env vars

**Ring:** `MLX_RANK` (0-based int), `MLX_HOSTFILE` (JSON: list per rank of `["ip:port", ...]`), optional `MLX_RING_VERBOSE=1`.
```json
[
 ["123.123.1.1:5000", "123.123.1.2:5000"],
 ["123.123.2.1:5000", "123.123.2.2:5000"],
 ["123.123.3.1:5000", "123.123.3.2:5000"],
 ["123.123.4.1:5000", "123.123.4.2:5000"]
]
```
**JACCL:** `MLX_RANK`, `MLX_JACCL_COORDINATOR` (`ip:port` for rank 0), `MLX_IBV_DEVICES` (path to a JSON matrix of ibverbs device names). Code also accepts `JACCL_*`-prefixed aliases: `JACCL_IBV_DEVICES`, `JACCL_COORDINATOR`, `JACCL_RANK`, `JACCL_RING` (`mlx/distributed/jaccl/lib/jaccl/jaccl.cpp:170-174`).
**NCCL:** `MLX_RANK`, `MLX_WORLD_SIZE`, `NCCL_HOST_IP`, `NCCL_PORT`, `CUDA_VISIBLE_DEVICES` (+ any standard NCCL var).
**MPI:** launched by `mpirun`; `MLX_MPI_LIBNAME` overrides the dylib name (docs call it `MPI_LIBNAME`, code reads `MLX_MPI_LIBNAME` at `mlx/distributed/mpi/mpi.cpp:24` — **doc/code drift, trust the code**). `DYLD_LIBRARY_PATH` must point at `libmpi.dyld` for Homebrew/pip MPI.

MPI tuning: `--mca btl_tcp_links N` (multiple TCP connections), `--mca btl_tcp_if_include <iface>`.
Recommended MPI install: `conda install conda-forge::openmpi`.

### 18.7 Data-parallel recipe

```python
from mlx.utils import tree_map

def all_reduce_grads(grads):
    N = mx.distributed.init().size()
    if N == 1: return grads
    return tree_map(lambda x: mx.distributed.all_sum(x) / N, grads)

def step(model, x, y):
    loss, grads = loss_grad_fn(model, x, y)
    grads = mx.nn.average_gradients(grads)   # preferred: batches small comms
    optimizer.update(model, grads)
    return loss
```

---

## 19. Environment variables (complete list found in `mlx/`)

Runtime-read (via `std::getenv` / `env::get_var`):

| Var | Default | Where / effect |
|---|---|---|
| `MLX_DISABLE_COMPILE` | unset | `mlx/compile.cpp:219` — globally disables `mx.compile` |
| `MLX_BFS_MAX_WIDTH` | `20` | `mlx/utils.h` — graph BFS width during eval |
| `MLX_MAX_OPS_PER_BUFFER` | arch-dependent (20/40/50) | Metal & CUDA command-buffer batching |
| `MLX_MAX_MB_PER_BUFFER` | arch-dependent (40/50) | ditto |
| `MLX_METAL_FAST_SYNCH` | `0` | `mlx/backend/metal/fence.cpp:15` — faster CPU↔GPU sync |
| `MLX_ENABLE_TF32` | `1` | TF32 for float32 matmuls (Metal + CUDA cuBLAS) |
| `MLX_NCCL_TIMEOUT` | backend default | NCCL init timeout ms |
| `MLX_METAL_GPU_ARCH` | `""` | override the reported GPU architecture string |
| `MLX_SDPA_BLOCKS` | `0` (auto) | Metal SDPA block size; rounded up to a multiple of 32 |
| `MLX_CUDA_USE_CUDNN_SDPA` | `1` | use cuDNN SDPA on CUDA |
| `MLX_USE_CUDA_GRAPHS` | `true` | CUDA graph capture |
| `MLX_ENABLE_CACHE_THRASHING_CHECK` | `1` | aborts on LRU cache thrashing (tests set `0`) |
| `MLX_PTX_CACHE_DIR` | unset | CUDA JIT PTX cache dir |
| `MLX_SAVE_CUDA_GRAPHS_DOT_FILE` | unset | dump CUDA graphs to DOT |
| `MLX_MPI_LIBNAME` | platform default | MPI dylib filename |
| `MLX_HOSTFILE`, `MLX_RANK`, `MLX_RING_VERBOSE` | — | ring backend |
| `MLX_JACCL_COORDINATOR`, `MLX_IBV_DEVICES`, `MLX_JACCL_RING` | — | JACCL (aliases `JACCL_*`) |
| `MLX_WORLD_SIZE`, `NCCL_HOST_IP`, `NCCL_PORT`, `NCCL_DEBUG`, `CUDA_VISIBLE_DEVICES` | — | NCCL |
| `CUDA_HOME` / `CUDA_PATH` | — | CUDA JIT module lookup |
| `MTL_CAPTURE_ENABLED=1` | — | required for `mx.metal.start_capture` |
| `MTL_LOG_LEVEL=MTLLogLevelDebug`, `MTL_LOG_TO_STDERR=1` | — | Metal shader logging |
| `DEVELOPER_DIR` | — | select a specific Xcode |
| `ARCHFLAGS` | — | respected by setup.py for cross-compiling (`-arch <x>`) |
| `DEBUG=1` | — | `DEBUG=1 python -m pip install -e .` builds debug (enables `os_log` in kernels) |
| `PYPI_RELEASE`, `DEV_RELEASE`, `MLX_BUILD_STAGE` | — | setup.py versioning/packaging |
| `CMAKE_ARGS`, `CMAKE_BUILD_PARALLEL_LEVEL` | — | setup.py build |

CUDA LRU-cache sizing vars (also `env::get_var`): `MLX_CUDA_CONV_CACHE_SIZE`, `MLX_CUDA_FFT_CACHE_SIZE`, `MLX_CUDA_GRAPH_CACHE_SIZE`, `MLX_CUDA_SDPA_CACHE_SIZE`, `MLX_CUDA_SDPA_BACKWARD_CACHE_SIZE`.

Compile-time defines seen: `MLX_METAL_NO_NAX`, `MLX_METAL_JIT`, `MLX_METAL_DEBUG`, `MLX_METAL_VERSION`, `MLX_METAL_PATH`, `MLX_CUDA_ARCHITECTURES`, `MLX_CUDA_SM_80_ENABLED`, `MLX_LOAD_CUDA_LIBS_FROM_PYTHON`, `MLX_USE_ACCELERATE`, `MLX_STATIC`, `MLX_VERSION*`.

---

## 20. Metal backend internals worth knowing

### 20.1 NAX kernels (Metal 4 / M5-era neural accelerators)

Build gate (`mlx/backend/metal/kernels/CMakeLists.txt:157-183`):
```cmake
if(MLX_METAL_VERSION GREATER_EQUAL 400
   AND MACOS_SDK_VERSION VERSION_GREATER_EQUAL 26.2
   AND CMAKE_OSX_DEPLOYMENT_TARGET VERSION_GREATER_EQUAL 26.2)
  build_kernel(steel/gemm/kernels/steel_gemm_fused_nax     ${STEEL_NAX_HEADERS})
  build_kernel(steel/gemm/kernels/steel_gemm_gather_nax    ${STEEL_NAX_HEADERS})
  build_kernel(steel/gemm/kernels/steel_gemm_splitk_nax    ${STEEL_NAX_HEADERS})
  build_kernel(steel/gemm/kernels/steel_gemm_segmented_nax ${STEEL_NAX_HEADERS})
  build_kernel(quantized_nax quantized_nax.h ${STEEL_NAX_HEADERS})
  build_kernel(fp_quantized_nax fp4.h fp8.h fp_quantized_nax.h ${STEEL_NAX_HEADERS})
  build_kernel(steel/attn/kernels/steel_attention_nax ${STEEL_NAX_ATTN_HEADERS})
else()
  message(WARNING "NAX kernels require Metal 4, macOS SDK >= 26.2, and "
                  "MACOSX_DEPLOYMENT_TARGET >= 26.2 (...). Building without NAX kernels.")
  target_compile_definitions(mlx PRIVATE MLX_METAL_NO_NAX)
endif()
```

Runtime gate (`mlx/backend/metal/device.cpp:944-963`):
```cpp
bool is_nax_available() {
#ifdef MLX_METAL_NO_NAX
  return false;
#else
  auto _check_nax = []() {
    bool can_use_nax = false;
    if (__builtin_available(macOS 26.2, iOS 26.2, tvOS 26.2, visionOS 26.2, *)) {
      can_use_nax = true;
    }
    auto& d = metal::device(mlx::core::Device::gpu);
    auto arch = d.get_architecture().back();
    auto gen  = d.get_architecture_gen();
    can_use_nax &= gen >= (arch == 'p' ? 18 : 17);
    return can_use_nax;
  };
  static bool is_nax_available_ = _check_nax();
  return is_nax_available_;
#endif
}
```
So NAX needs **macOS/iOS/tvOS/visionOS 26.2+** at runtime *and* GPU architecture generation **≥ 17** (≥ 18 for phone-class `'p'` GPUs).

### 20.2 Architecture-class heuristics (`mlx/backend/metal/device.cpp:592-627`)

The architecture string's **last character** classifies the chip; `arch_gen_` is parsed from the two digits before it:

| suffix | class | `max_ops_per_buffer` | `max_mb_per_buffer` |
|---|---|---|---|
| `p` | phone | 20 | 40 |
| `g` | base / pro | 40 | 40 |
| `s` | max | 50 | 50 |
| `d` | ultra | 50 | 50 |
| other | default (medium) | 40 | 40 |

Both are overridable with `MLX_MAX_OPS_PER_BUFFER` / `MLX_MAX_MB_PER_BUFFER`. `MLX_METAL_GPU_ARCH` can force the architecture string.

### 20.3 Metal debugging & logging

`docs/src/dev/metal_debugger.rst`:
```bash
CMAKE_ARGS="-DMLX_METAL_DEBUG=ON" pip install -e .
MTL_CAPTURE_ENABLED=1 python my_script.py
```
```python
mx.metal.start_capture("mlx_trace.gputrace")   # path must not already exist
for _ in range(10): mx.eval(mx.add(a, b))
mx.metal.stop_capture()
```
Xcode workflow: `cmake .. -DMLX_METAL_DEBUG=ON -G Xcode && open mlx.xcodeproj`, run the `metal_capture` scheme.

`docs/src/dev/metal_logging.rst` — **requires Metal 3.2+ (macOS 15+, iOS 18+)**:
```bash
DEBUG=1 python -m pip install -e .
```
```cpp
#include "mlx/backend/metal/kernels/logging.h"
constant mlx::os_log logger("mlx", "my_kernel");
kernel void my_kernel(/* ... */) {
  logger.log_debug("unexpected state: idx=%u", idx);
}
```
```bash
MTL_LOG_LEVEL=MTLLogLevelDebug MTL_LOG_TO_STDERR=1 python script.py
```

### 20.4 Metal kernel source tree
`mlx/backend/metal/kernels/` includes `steel/` (the tiled GEMM/conv/attention library) with `gemm/`, `conv/`, `attn/`, `utils/` subtrees plus `*_nax.metal` variants, `reduction/`, `fft/`, `indexing/`. `mlx.metallib` is built with:
```
xcrun -sdk macosx metal -mmacosx-version-min=<target> <air files> -o <path>/mlx.metallib
```

---

## 21. Extending MLX (custom C++/Metal primitives)

`docs/src/dev/extensions.rst` (811 lines) + `examples/extensions/`.

**Ops vs Primitives:** "*Operations in MLX build the computation graph. Primitives provide the rules for evaluating and transforming the graph.*"

Primitive skeleton:
```cpp
class Axpby : public Primitive {
 public:
  explicit Axpby(Stream stream, float alpha, float beta)
      : Primitive(stream), alpha_(alpha), beta_(beta) {};
  void eval_cpu(const std::vector<array>& inputs, std::vector<array>& outputs) override;
  void eval_gpu(const std::vector<array>& inputs, std::vector<array>& outputs) override;
  std::vector<array> jvp(const std::vector<array>& primals,
                         const std::vector<array>& tangents,
                         const std::vector<int>& argnums) override;
  std::vector<array> vjp(const std::vector<array>& primals, ...) override;
};
```
"*To avoid unnecessary allocations, the evaluation function is responsible for allocating space for the array.*"

CMake glue:
```cmake
add_library(mlx_ext)
target_sources(mlx_ext PUBLIC ${CMAKE_CURRENT_LIST_DIR}/axpby/axpby.cpp)
target_include_directories(mlx_ext PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(mlx_ext PUBLIC mlx)

if(MLX_BUILD_METAL)
  mlx_build_metallib(
    TARGET mlx_ext_metallib
    TITLE mlx_ext
    SOURCES ${CMAKE_CURRENT_LIST_DIR}/axpby/axpby.metal
    INCLUDE_DIRS ${PROJECT_SOURCE_DIR} ${MLX_INCLUDE_DIRS}
    OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY})
  add_dependencies(mlx_ext mlx_ext_metallib)
endif()

nanobind_add_module(_ext NB_STATIC STABLE_ABI LTO NOMINSIZE NB_DOMAIN mlx
                    ${CMAKE_CURRENT_LIST_DIR}/bindings.cpp)
target_link_libraries(_ext PRIVATE mlx_ext)
if(BUILD_SHARED_LIBS)
  target_link_options(_ext PRIVATE -Wl,-rpath,@loader_path)
endif()
```
`mlx_build_metallib` lives in `cmake/extension.cmake` and is auto-imported with the MLX package.

setuptools glue:
```python
from mlx import extension
from setuptools import setup

setup(
    name="mlx_sample_extensions",
    version="0.0.0",
    ext_modules=[extension.CMakeExtension("mlx_sample_extensions._ext")],
    cmdclass={"build_ext": extension.CMakeBuild},
    packages=["mlx_sample_extensions"],
    package_data={"mlx_sample_extensions": ["*.so", "*.dylib", "*.metallib"]},
    zip_safe=False,
    python_requires=">=3.8",
)
```
Build: `pip install -r requirements.txt` then `python setup.py build_ext -j8 --inplace` (from `extensions/`).
Result layout: `mlx_sample_extensions/{__init__.py, libmlx_ext.dylib, mlx_ext.metallib, _ext.cpython-3x-darwin.so}`.
Note (verbatim): "*`mlx.core` must be imported before importing `_ext`*".

Benchmark in the doc: `Simple axpby: 1.559 ms | Custom axpby: 0.774 ms` on 4096×4096.

---

## 22. Using MLX from C++ (`docs/src/dev/mlx_in_cpp.rst`, `examples/cmake_project/`)

```cpp
#include <iostream>
#include "mlx/mlx.h"
namespace mx = mlx::core;
int main() {
  auto x = mx::array({1, 2, 3});
  auto y = mx::array({1, 2, 3});
  std::cout << x + y << std::endl;
}
```
```cmake
cmake_minimum_required(VERSION 3.27)
project(example LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python 3.9 COMPONENTS Interpreter Development.Module REQUIRED)
execute_process(COMMAND "${Python_EXECUTABLE}" -m mlx --cmake-dir
                OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE MLX_ROOT)
find_package(MLX CONFIG REQUIRED)
add_executable(example example.cpp)
target_link_libraries(example PRIVATE mlx)
```
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build && ./build/example
```
`find_package(MLX CONFIG REQUIRED)` sets `MLX_FOUND`, `MLX_INCLUDE_DIRS`, `MLX_LIBRARIES`, `MLX_CXX_FLAGS`, `MLX_BUILD_ACCELERATE`, `MLX_BUILD_METAL`.

`python -m mlx --cmake-dir` is the discovery entry point (`python/mlx/__main__.py`).

Note from install.rst: "*the built `mlx.metallib` file should be either at the same directory as the executable statically linked to `libmlx.a` or the preprocessor constant `METAL_PATH` should be defined at build time*".

C++ array semantics (from `examples/cpp/tutorial.cpp`):
```cpp
mx::array x(1.0);            // scalar, float32, ndim 0, empty shape
x = mx::array(1, mx::int32); // x.item<int>() OK, x.item<float>() UNDEFINED
x = mx::array({1.0f, 2.0f, 3.0f, 4.0f}, {2, 2});   // row-major
auto z = mx::add(x, mx::ones({2,2}));  // or x + y
mx::eval(z);                 // second eval is a no-op
z.item<float>();             // implicit evaluation
auto grad_fn  = mx::grad([](mx::array x){ return mx::square(x); });
auto d2fdx2   = mx::grad(mx::grad(fn))(x);
```
> "*Once an array is evaluated, it has data and is detached from its inputs.*"

`mlx/array.h` highlights: `array` holds a shared `ArrayDesc`; `using Shape = SmallVector<int32_t>`, `using Strides = SmallVector<int64_t>`; there's a raw-pointer constructor `array(void* data, Shape, Dtype, const std::function<void(void*)>& deleter)` which "*will attempt to use the input data without a copy*", and a buffer constructor `array(allocator::Buffer, Shape, Dtype, Deleter = allocator::free)`. Assignment to an rvalue is deleted.

---

## 23. Randomness

`docs/src/python/random.rst`: "*Following JAX's PRNG design we use a splittable version of Threefry, which is a counter-based PRNG.*"

Python module `mx.random`: `bernoulli, categorical, gumbel, key, normal, multivariate_normal, randint, seed, split, truncated_normal, uniform, laplace, permutation`. Plus the compile-capture sentinel `mx.random.state`.

```python
key = mx.random.key(0)
for _ in range(3):
    print(mx.random.uniform(key=key))     # identical every iteration
```

C++ (`mlx/random.h`): `key(uint64_t)`, `seed(uint64_t)`, `bits(shape, width=4, key=nullopt, s={})`, `split(key)` → pair, `split(key, num)`, plus the distribution functions.

**Gotcha:** the default key sequence is `static thread_local` (`KeySequence::default_()` in `mlx/random.h:22-31`) — "*Each thread has its own random key to avoid race condition.*" Seeding in one thread does not seed another.

---

## 24. Other module surfaces

**`mx.linalg`** (`docs/src/python/linalg.rst`): `inv, tri_inv, norm, cholesky, cholesky_inv, cross, det, qr, svd, eigvals, eig, eigvalsh, eigh, lu, lu_factor, pinv, slogdet, solve, solve_triangular`.

**`mx.fft`**: `fft, ifft, fft2, ifft2, fftn, ifftn, rfft, irfft, rfft2, irfft2, rfftn, irfftn, fftfreq, rfftfreq, fftshift, ifftshift`.

**`mx.metal`**: `is_available, device_info*, start_capture, stop_capture` (`*` deprecated in favour of `mx.device_info`).
**`mx.cuda`**: `is_available`.

**Print options** (`python/src/print.cpp`):
```python
mx.set_printoptions(precision=3)
with mx.printoptions(precision=3):
    print(x)
mx.get_printoptions()      # -> PrintOptions
mx.PrintOptions(precision=-1)   # -1 == default
```
Only `precision` is exposed today (`nb::class_<mx::PrintOptions>...def_rw("precision", ...)`).

**Array methods** (`docs/src/python/array.rst`): `astype, at, item, tolist, dtype, itemsize, nbytes, ndim, shape, size, real, imag, abs, all, any, argmax, argmin, conj, cos, cummax, cummin, cumprod, cumsum, diag, diagonal, exp, flatten, log, log10, log1p, log2, logcumsumexp, logsumexp, max, mean, min, moveaxis, prod, reciprocal, reshape, round, rsqrt, sin, split, sqrt, square, squeeze, std, sum, swapaxes, transpose, T, var, view`. Arrays are picklable (`__getstate__`/`__setstate__` roundtrip through NumPy, with `bfloat16` bit-cast through `uint16`).

---

## 25. Benchmarks

`benchmarks/python/` — 30+ scripts: `sdpa_bench.py`, `sdpa_vector_bench.py`, `gather_qmm_bench.py`, `segmented_mm_bench.py`, `large_gemm_bench.py`, `layer_norm_bench.py`, `rms_norm_bench.py`, `rope_bench.py`, `compile_bench.py`, `distributed_bench.py`, `hadamard_bench.py`, `einsum_bench.py`, `conv*_bench.py`, `masked_scatter.py`, `synchronize_bench.py`, plus `blas/` and `comparative/` (vs NumPy/torch). C++ benchmarks in `benchmarks/cpp/{autograd,compare_devices,irregular_strides,single_ops}.cpp`.

The canonical timing harness (`benchmarks/python/time_utils.py`) — **note the warmup and that `mx.eval` is inside the loop**:
```python
def time_fn(fn, *args, **kwargs):
    for _ in range(5):
        mx.eval(fn(*args, **kwargs))          # warmup
    num_iters = 100
    tic = time.perf_counter()
    for _ in range(num_iters):
        x = mx.eval(fn(*args, **kwargs))
    toc = time.perf_counter()
    print(f"{1e3 * (toc - tic) / num_iters:.5f} msec")

def measure_runtime(fn, **kwargs):
    for _ in range(5): fn(**kwargs)
    tic = time.perf_counter()
    for _ in range(100): fn(**kwargs)
    return (time.perf_counter() - tic) * 1000 / 100
```
Docs version with a nicer name:
```python
def timeit(fun, x):
    for _ in range(10): mx.eval(fun(x))      # warm up
    tic = time.perf_counter()
    for _ in range(100): mx.eval(fun(x))
    toc = time.perf_counter()
    print(f"Time per iteration {1e3 * (toc - tic) / 100:.3f} (ms)")
```

CONTRIBUTING.md: "*If a change is likely to impact efficiency, run some of the benchmarks before and after the change.*" Formatting via `pre-commit` (black + clang-format): `pre-commit install`, `pre-commit run --all-files`, `clang-format -i file.cpp`, `black file.py`.

---

## 26. Tests as documentation

`python/tests/` modules: `test_array, test_autograd, test_bf16, test_blas, test_compile, test_constants, test_conv, test_conv_transpose, test_device, test_double, test_einsum, test_eval, test_export_import, test_fast, test_fast_sdpa, test_fft, test_graph, test_init, test_linalg, test_load, test_losses, test_memory, test_nn, test_ops, test_optimizers, test_quantized, test_random, test_reduce, test_threads, test_tree, test_upsample, test_vmap, test_zero_copy` + distributed suites (`mpi_test_distributed.py`, `nccl_test_distributed.py`, `ring_test_distributed.py`, `mlx_distributed_tests.py`).

`python/tests/mlx_tests.py` (the harness) sets, **before importing mlx**:
```python
os.environ["MLX_ENABLE_TF32"] = "0"                      # "Use regular fp32 precision for tests"
os.environ["MLX_ENABLE_CACHE_THRASHING_CHECK"] = "0"     # "Do not abort on cache thrashing"
```
It also honours a `DEVICE` env var to pick the default device, and `MLXTestRunner` calls `mx.clear_streams()` before exiting.

Run: `python -m unittest discover python/tests`.

---

## 27. Recent commit archaeology (what is actively changing)

`git log --oneline -60` highlights:

- `973e27f` [CUDA] Fix grid overflow in gemm conv unfold kernels for ≥ 65,536 output positions (#3893)
- `9b40c9d` Fix `prod` dtype promotion when reducing a size-1 axis (#3898)
- `7c92ce1` [Metal] Avoid regex in custom kernel name generation (#3869)
- `6c0ea7f` **Fix incorrect nvfp4 quantized_matmul through the split-K path (#3854)** ← nvfp4 correctness bug recently fixed
- `0ebcee8` metal: add `gemv_wide` for fp16/bf16 matmuls of a few rows (#3888)
- `3541c66` Use `unroll_count(4)` for the NAX attention Q@K.T loop (#3843)
- `291e909` Reuse Metal WAR tracking hash tables (#3882)
- `8462ad9` Round `MLX_SDPA_BLOCKS` up to a multiple of 32 (#3875)
- `0c537a4` **Zero-copy CPU import: `mx.array(host_buffer, copy=False)` on unified memory (#3872)**
- `8f64abc` **[WIP] [CUDA] fsdp (#3768)**
- `353440c` Fix JIT preamble header filter matching project paths containing "Xcode" (#3873)
- `ce30733` **Fix captured random state in compile (#3828)**
- `b7c3dd6` [CUDA] RMSNorm forward speed up (#3850)
- `4367c73` Warn at configure time when NAX kernels are disabled (#3824)
- `8573c35` Fix int64 type cast error when loading GGUF metadata arrays (#3823)
- `57c66ca` **Patch bump to 0.32.1 (#3816)**
- `7a1d4f5` Fix conv2 gradients in grouped strided case on Metal (#3800)
- `3a73f21` Fix infinite-norm negative-axis mismatch for ≥2-D matrices (#3756)
- `b925592` Fix CPU gather transposing column-contiguous slices (#3647)
- `a8c3e9c` Fix wrong type parameter passed to `gemm_splitk_nax` (#3810)
- `b5404c9` **Fix compiled kernel correctness for negative-strided inputs (#3720)**
- `51bef6f` **Add math mode option for custom Metal kernels (#3728)**
- `a5a684d` Fix CUDA RMSNorm small-row dispatch (#3792)
- `1700b39` Fix fp quantized matvec for output dim < 8 (#3804)
- `de7b4ed` Fix `HardShrink` to accept its documented `lambd` argument (#3786)
- `3e65a0f` fix: Quote hostname in `mlx.launch` ssh commands (#3783)
- `61b5ff8` Fix multi-wire recv prefill deadlock in jaccl ring backend (#3654)
- `25616a0` Add CI for Windows CUDA build (#3775) / `eba2b50` large runner for Windows CUDA
- `1d20ba3` Fix `Upsample` `align_corners` singleton output (#3769)
- `af55406` Fix complex vjps for several unary ops (#3766)
- `eba3e4e` array API: add `cumulative_sum` and `cumulative_prod` (#3731)
- `e94b415` array API: add `positive, logical_xor, trunc, count_nonzero, diff, full_like` (#3730)
- `c9ccaba` Enable fused SDPA vector kernel for asymmetric Q/V head dims (192, 128) (#3637)
- `da38f3e` Fix `logsumexp` jvp to reduce along the axis (#3708)
- `e37e926` Add `vecdot` to array API namespace (#3748)

Themes: (1) NAX / Metal 4 GEMM+attention path is new and being tuned; (2) fp4/fp8 quantization (`nvfp4`, `mxfp4`, `mxfp8`, `qqmm`) is new and has had recent correctness fixes; (3) Array-API-standard compliance work; (4) Windows CUDA support; (5) CUDA FSDP in flight; (6) zero-copy interop.

---

## 28. Gotchas / footguns quick list

1. **No bounds checking on indexing.** Out-of-bounds is UB (exceptions can't propagate from the GPU).
2. **Slicing copies**, unlike NumPy views. `b = a[:]` then `b[2]=0` does not modify `a`.
3. **Duplicate index assignment is nondeterministic**; use `x.at[idx].add(y)`.
4. **`mx.empty` == `mx.zeros`** (Array-API alias), not uninitialized memory.
5. **`float64` is CPU-only**; using it on the GPU raises.
6. **NumPy has no bfloat16** — cast to float32/float16 first or hit a PEP-3118 error.
7. **External writes through numpy views are invisible to autodiff** (gradient silently wrong).
8. **DLPack does not synchronize** pending Metal work — synchronize the producer first.
9. **Zero-copy CPU import needs Metal + a 16 KiB page-aligned buffer + no dtype conversion.**
10. **Compiled functions must be pure**; captured state is a compile-time constant unless declared via `inputs=`/`outputs=`.
11. **Can't print/evaluate arrays inside a compiled function** — use `mx.disable_compile()` / `MLX_DISABLE_COMPILE`.
12. **`shapeless=True` still recompiles on ndim/dtype change**, and shape-dependent code (e.g. `x.reshape(x.shape[0]*x.shape[1], -1)`) silently bakes in the first shape.
13. **Dropout inside a compiled step needs `mx.random.state` in the captured state.**
14. **`mx.random`'s default key sequence is thread-local.**
15. **On Metal the fused SDPA kernel does not run during training** (`is_training` → fallback), and only specific head dims are accelerated.
16. **`quantize` requires ≥ 2 dims and last dim divisible by `group_size`**; affine bits exclude 7; `global_scale` (nvfp4) is unsupported on Metal.
17. **`QQLinear` has no bias** and flips between quantized/dequantized weights on `train()`/`eval()`.
18. **`QuantizedLinear`/`QuantizedEmbedding` parameters are frozen** (no gradients).
19. **`nn.fully_shard` shards axis 0 only** and requires `shape[0] % group_size == 0`; scalars can't be sharded.
20. **`mx.new_stream` streams are thread-bound**; cross-thread use needs `new_thread_unsafe_stream` and manual race avoidance.
21. **NAX kernels need Metal 4 + SDK/deployment target ≥ 26.2 + GPU gen ≥ 17 (≥ 18 on phone GPUs)** — otherwise silently compiled out (`MLX_METAL_NO_NAX`).
22. **`mx.metal.*` memory/device functions are deprecated** and print to stderr; use `mx.*`.
23. **Imported `.mlxfn` functions always return a tuple**, and enclosed arrays must be `mx.eval`'d before export or their producing graph is exported too.
24. **`mlx.distributed_config` flag is `--output-hostfile`**, not `--output` as the docs show.
25. **Ring backend `send`/`recv` only work between neighbours.**
26. **`MLX_ENABLE_TF32` defaults to 1** — float32 matmuls are not bit-exact by default; set `0` for reference precision (the test suite does).
27. **Custom Metal kernels default to `math_mode="safe"`**; switching to `relaxed`/`fast` can break `exp(-inf) == 0` assumptions in masked softmax.
28. **Building a new `metal_kernel` each call JIT-compiles a new library** — hoist kernel construction out of hot paths.
29. **`mx.compile` only fuses element-wise/broadcast primitives**; reductions, matmuls, gathers are not fused.
30. **`Module.__setattr__` only tracks `array | dict | list | tuple`** — assigning e.g. a NumPy array or a float stores it outside the parameter tree.

---

## 29. Source inventory (files actually read this session)

Docs (`docs/src/`):
- `index.rst`, `install.rst`
- `usage/quick_start.rst`, `usage/lazy_evaluation.rst`, `usage/unified_memory.rst`, `usage/indexing.rst`, `usage/saving_and_loading.rst`, `usage/using_streams.rst`, `usage/function_transforms.rst`, `usage/compile.rst`, `usage/export.rst`, `usage/numpy.rst`, `usage/distributed.rst`, `usage/launching_distributed.rst`
- `dev/custom_metal_kernels.rst`, `dev/extensions.rst` (head + tail), `dev/metal_debugger.rst`, `dev/metal_logging.rst`, `dev/mlx_in_cpp.rst`
- `python/ops.rst`, `python/array.rst`, `python/data_types.rst`, `python/devices_and_streams.rst`, `python/export.rst`, `python/fast.rst`, `python/fft.rst`, `python/linalg.rst`, `python/metal.rst`, `python/cuda.rst`, `python/memory_management.rst`, `python/nn.rst`, `python/nn/layers.rst`, `python/nn/functions.rst`, `python/nn/losses.rst`, `python/nn/init.rst`, `python/nn/distributed.rst`, `python/optimizers.rst`, `python/optimizers/common_optimizers.rst`, `python/distributed.rst`, `python/random.rst`, `python/transforms.rst`, `python/tree_utils.rst`, `python/printoptions.rst`
- `examples/data_parallelism.rst`, `examples/tensor_parallelism.rst`

C++ (`mlx/`):
- `version.h`, `ops.h` (quantization + matmul sections), `ops.cpp` (quantize/dequantize validation, `affine_quantize`, `fp_quantize`), `fast.h`, `fast.cpp` (SDPA validation, fallback, dispatch), `transforms.h`, `compile.h`, `compile.cpp` (`is_unary/binary/ternary/broadcast/fusable/noop/reduction`, compile mode), `export.h`, `array.h` (first 140 lines), `device.h`, `stream.h`, `memory.h`, `io.h`, `random.h`, `utils.h` (`namespace env`), `utils.cpp` (`env::get_var`), `dtype.h` (categories)
- `distributed/distributed.h`, `distributed/ops.h`
- `backend/metal/device.cpp` (`is_nax_available`, `Device::Device` arch heuristics), `backend/metal/device.h`, `backend/metal/scaled_dot_product_attention.cpp` (`use_fallback`), `backend/metal/kernels/CMakeLists.txt`

Python bindings (`python/src/`):
- `mlx.cpp`, `ops.cpp` (quantize/dequantize/quantized_matmul/gather_qmm/segmented_mm/qqmm/to_fp8/from_fp8/contiguous/view/as_strided/asarray/from_dlpack + array-API aliases), `fast.cpp` (whole file), `transforms.cpp` (custom_function, eval, async_eval, jvp, vmap, compile, checkpoint), `stream.cpp`, `device.cpp`, `memory.cpp`, `metal.cpp`, `constants.cpp`, `print.cpp` (grep), `array.cpp` (`at`, pickle), `distributed.cpp` (signatures via grep)

Python package (`python/mlx/`):
- `nn/__init__.py`, `nn/layers/__init__.py`, `nn/layers/base.py` (whole), `nn/layers/quantized.py` (whole), `nn/layers/distributed.py` (FullyShardedModule / fully_shard), `nn/layers/positional_encoding.py` (constructors), `nn/utils.py` (whole), `nn/losses.py` (function list), `optimizers/__init__.py`, `optimizers/optimizers.py` (base + SGD + Muon + clip_grad_norm), `optimizers/schedulers.py` (function list), `utils.py` (whole), `_distributed_utils/launch.py` (`main`), `_distributed_utils/config.py` (`main`)

Tests (`python/tests/`):
- `mlx_tests.py`, `test_compile.py` (capture/rng/list of tests), `test_fast.py` (custom-kernel tests, math-mode test), `test_zero_copy.py` (via `git show 0c537a4`)

Examples / benchmarks / build:
- `examples/python/qqmm.py`, `examples/export/{README.md,eval_mlp.py,eval_mlp.cpp}`, `examples/cpp/tutorial.cpp`
- `benchmarks/python/time_utils.py`
- `README.md`, `CONTRIBUTING.md`, `pyproject.toml`, `setup.py`, `CMakeLists.txt` (options + Metal section)

Git: `git log --oneline -60`, `git show --stat 0c537a4`, `git show 0c537a4 -- python/tests/test_zero_copy.py`, `git show 4367c73`.

---

## 30. Open questions / UNVERIFIED

1. **`mlx.launch --no-verify-script`** is documented in `docs/src/usage/launching_distributed.rst:164` but I did not find it in the argparse block at `python/mlx/_distributed_utils/launch.py:457-519`. Either it is parsed elsewhere (e.g. inside `launch_nccl`) or the docs are ahead of the code. **UNVERIFIED.**
2. **`mlx.distributed_config --output`** vs `--output-hostfile` — docs use `--output`, argparse defines `--output-hostfile`. Likely a docs bug; I did not run either binary. **UNVERIFIED which one works.**
3. `docs/src/install.rst` build-options table lists `MLX_BUILD_EXAMPLES` default **OFF** while `CMakeLists.txt:33` says **ON**. **Doc/code drift, unresolved.**
4. `MPI_LIBNAME` (docs) vs `MLX_MPI_LIBNAME` (code, `mlx/distributed/mpi/mpi.cpp:24`). Possibly both are honoured via `mlx.launch` setting one; not verified.
5. I did not read `mlx/primitives.h/.cpp` (2551 + 6202 lines) in full — the exhaustive Primitive list, per-primitive vmap/vjp coverage, and which primitives lack `vmap` are **not enumerated here**.
6. I did not read the `steel/` Metal kernel sources; the exact NAX tile sizes / supported dtypes for `steel_gemm_*_nax` and `steel_attention_nax` are **unknown**.
7. `mx.export_to_dot` is listed in `docs/src/python/export.rst` but I did not read its binding or signature. **UNVERIFIED.**
8. `mx.fast.metal_kernel` `compile_options` currently accepts only `math_mode`; whether more keys are planned is unknown.
9. The exact behaviour of `mx.qqmm` `global_scale_x`/`global_scale_w` on Metal (given `"[quantize] Global scale is not supported on the Metal backend."`) is unclear — presumably nvfp4-with-global-scale is CUDA-only. **UNVERIFIED.**
10. `nn.quantize(..., quantize_input=True)` routes to `QQLinear` presumably via `Linear.to_quantized(quantize_input=...)`; I did not read `python/mlx/nn/layers/linear.py` to confirm the `to_quantized` implementation. **UNVERIFIED.**
11. Whether `mlx-swift` (the Swift bindings repo) tracks 0.32.x is out of scope here; MLX's README only links to `ml-explore/mlx-swift` and `ml-explore/mlx-c`.
12. `MLX_METAL_VERSION GREATER_EQUAL 400` — I inferred "Metal 4" from the CMake warning text; the exact `__METAL_VERSION__` value ↔ Metal release mapping was not independently verified.
13. iOS/visionOS/tvOS support: `is_nax_available` checks `iOS 26.2, tvOS 26.2, visionOS 26.2` and the CMake comment says "*On iOS the caller selects the SDK*", so MLX builds for iOS — but there is no iOS install documentation in `docs/src/install.rst`. **UNVERIFIED how to build for iOS.**
