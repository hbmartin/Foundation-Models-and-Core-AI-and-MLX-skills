# MLX Official Documentation Site — Exhaustive Research Notes

**Research date:** 2026-07-27
**Site crawled:** `https://ml-explore.github.io/mlx/build/html/`
**Documented version (verbatim from `<title>` on every page):** `MLX 0.32.0 documentation`
**Copyright footer on every page:** `By MLX Contributors — © Copyright 2023, Apple.`

**Method note:** WebFetch returns LLM-summarized content, which loses exact signatures. To get verbatim
text I downloaded raw HTML with `curl` into a scratch dir and ran a custom Python `html.parser`
extractor that preserves `<pre>` blocks and `<dt>` signature lines. **All code and signatures below
are verbatim from the rendered HTML**, not from memory. Where I paraphrase, it is marked.

Scratch copies of the raw HTML live at:
`/private/tmp/claude-501/-Volumes-ExtStor-FM-and-MLX-and-CoreAI/064ca93f-3a95-445f-9fa4-7cd79f77f3b0/scratchpad/mlxdocs/`
(session-scoped; will be garbage collected).

---

## 0. Site map / toctree (verbatim structure from `index.html`)

Top-level intro text, verbatim:

> MLX is a NumPy-like array framework designed for efficient and flexible machine learning on Apple
> silicon, brought to you by Apple machine learning research.
>
> The Python API closely follows NumPy with a few exceptions. MLX also has a fully featured C++ API
> which closely follows the Python API.
>
> The main differences between MLX and NumPy are:
>
> - **Composable function transformations**: MLX has composable function transformations for automatic
>   differentiation, automatic vectorization, and computation graph optimization.
> - **Lazy computation**: Computations in MLX are lazy. Arrays are only materialized when needed.
> - **Multi-device**: Operations can run on any of the supported devices (CPU, GPU, …)
>
> The design of MLX is inspired by frameworks like PyTorch, Jax, and ArrayFire. A notable difference
> from these frameworks and MLX is the *unified memory model*. Arrays in MLX live in shared memory.
> Operations on MLX arrays can be performed on any of the supported device types without performing
> data copies. Currently supported device types are the CPU and GPU.

### Toctree

```
Install
  └ Build and Install                          install.html
Usage
  ├ Quick Start Guide                          usage/quick_start.html
  ├ Lazy Evaluation                            usage/lazy_evaluation.html
  ├ Unified Memory                             usage/unified_memory.html
  ├ Indexing Arrays                            usage/indexing.html
  ├ Saving and Loading Arrays                  usage/saving_and_loading.html
  ├ Function Transforms                        usage/function_transforms.html
  ├ Compilation                                usage/compile.html
  ├ Conversion to NumPy and Other Frameworks   usage/numpy.html
  ├ Distributed Communication                  usage/distributed.html
  ├ Using Streams                              usage/using_streams.html
  └ Exporting Functions                        usage/export.html
  (+ NOT in the index toctree but linked from usage/distributed.html:)
  └ Launching Distributed Programs             usage/launching_distributed.html
Examples
  ├ Linear Regression                          examples/linear_regression.html
  ├ Multi-Layer Perceptron                     examples/mlp.html
  ├ LLM inference                              examples/llama-inference.html
  ├ Data Parallelism                           examples/data_parallelism.html
  └ Tensor Parallelism                         examples/tensor_parallelism.html
Python API Reference
  ├ Array                    python/array.html
  ├ Data Types               python/data_types.html
  ├ Devices and Streams      python/devices_and_streams.html
  ├ Export Functions         python/export.html
  ├ Operations               python/ops.html
  ├ Random                   python/random.html
  ├ Transforms               python/transforms.html
  ├ Fast                     python/fast.html
  ├ FFT                      python/fft.html
  ├ Linear Algebra           python/linalg.html
  ├ Metal                    python/metal.html
  ├ CUDA                     python/cuda.html
  ├ Memory Management        python/memory_management.html
  ├ Neural Networks          python/nn.html
  │   ├ Module               python/nn/module.html
  │   ├ Layers               python/nn/layers.html
  │   ├ Functions            python/nn/functions.html
  │   ├ Loss Functions       python/nn/losses.html
  │   ├ Initializers         python/nn/init.html
  │   └ Distributed          python/nn/distributed.html
  ├ Optimizers               python/optimizers.html
  │   ├ Optimizer            python/optimizers/optimizer.html
  │   ├ Common Optimizers    python/optimizers/common_optimizers.html
  │   └ Schedulers           python/optimizers/schedulers.html
  ├ Distributed Communication python/distributed.html
  ├ Tree Utils               python/tree_utils.html
  └ Print Options            python/printoptions.html
C++ API Reference
  └ Operations               cpp/ops.html
Further Reading
  ├ Custom Extensions in MLX dev/extensions.html
  ├ Metal Debugger           dev/metal_debugger.html
  ├ Metal Logging            dev/metal_logging.html
  ├ Custom Metal Kernels     dev/custom_metal_kernels.html
  └ Using MLX in C++         dev/mlx_in_cpp.html
```

**GOTCHA (crawler-relevant):** autosummary pages are relative to the *containing index page's*
directory. Top-level pages use `python/_autosummary/<name>.html`, but nested ones use
`python/nn/_autosummary/<name>.html` and `python/optimizers/_autosummary/<name>.html`.
Requesting `python/_autosummary/mlx.optimizers.Muon.html` returns a **GitHub Pages 404**, not the doc.

---

## 1. Build and Install (`install.html`) — verbatim

### 1.1 Python install from PyPI

```bash
pip install mlx
```

> To install from PyPI your system must meet the following requirements:
> - Using Apple silicon
> - Using a native Python >= 3.10
> - macOS >= 14.0

> **Note**: MLX is only available on devices running macOS >= 14.0 and higher.

### 1.2 CUDA backend (Linux/NVIDIA)

```bash
pip install mlx[cuda12]
```

> To install the CUDA package from PyPi your system must meet the following requirements:
> - Nvidia architecture >= SM 7.5
> - Nvidia driver >= 550.54.14
> - CUDA toolkit >= 12.0
> - Linux distribution with glibc >= 2.35
> - Python >= 3.10
>
> For CUDA 13 use `pip install mlx[cuda13]`. The CUDA 13 package requires an Nvidia driver >= 580 or
> an appropriate CUDA compatibility package.

### 1.3 CPU-only (Linux)

```bash
pip install mlx[cpu]
```

> - Linux distribution with glibc >= 2.35
> - Python >= 3.10

### 1.4 PyPI troubleshooting (verbatim)

> *My OS and Python versions are in the required range but pip still does not find a matching
> distribution.*
>
> Probably you are using a non-native Python. The output of
> ```
> python -c "import platform; print(platform.processor())"
> ```
> should be `arm`. If it is `i386` (and you have M series machine) then you are using a non-native
> Python. Switch your Python to a native Python. A good way to do this is with Conda.

### 1.5 Build requirements (verbatim)

> - `libblas-dev`, `liblapack-dev`, and `liblapacke-dev` (Linux)
> - A C++ compiler with C++20 support (e.g. Clang >= 15.0)
> - cmake – version 3.25 or later, and `make`
> - Xcode >= 15.0 and macOS SDK >= 14.0
>
> **Note**: Ensure your shell environment is native `arm`, not `x86` via Rosetta. If the output of
> `uname -p` is `x86`, see the troubleshooting section below.

### 1.6 Build Python API from source

```bash
git clone git@github.com:ml-explore/mlx.git mlx && cd mlx
pip install .
```

Development install:

```bash
pip install -e ".[dev]"
```

Faster incremental builds once dev deps installed:

```bash
python setup.py build_ext --inplace
```

Run tests:

```bash
python -m unittest discover python/tests
```

### 1.7 Build C++ API from source

```bash
git clone git@github.com:ml-explore/mlx.git mlx && cd mlx
mkdir -p build && cd build
cmake .. && make -j
make test
make install
```

> Note that the built `mlx.metallib` file should be either at the same directory as the executable
> statically linked to `libmlx.a` or the preprocessor constant `METAL_PATH` should be defined at
> build time and it should point to the path to the built metal library.

### 1.8 CMake Build Options — exact table

| Option | Default |
|---|---|
| `MLX_BUILD_TESTS` | ON |
| `MLX_BUILD_EXAMPLES` | OFF |
| `MLX_BUILD_BENCHMARKS` | OFF |
| `MLX_BUILD_METAL` | ON |
| `MLX_BUILD_CPU` | ON |
| `MLX_BUILD_PYTHON_BINDINGS` | OFF |
| `MLX_METAL_DEBUG` | OFF |
| `MLX_BUILD_SAFETENSORS` | ON |
| `MLX_BUILD_GGUF` | ON |
| `MLX_METAL_JIT` | OFF |

(`MLX_BUILD_CUDA` is documented separately in the CUDA build section but is **not** in this table.)

### 1.9 Choosing an Xcode / SDK

> If you have multiple Xcode installations and wish to use a specific one while building, you can do
> so by adding the following environment variable before building
> ```
> export DEVELOPER_DIR="/path/to/Xcode.app/Contents/Developer/"
> ```
> Further, you can use the following command to find out which macOS SDK will be used
> ```
> xcrun -sdk macosx --show-sdk-version
> ```

### 1.10 Binary Size Minimization (verbatim, incl. the typo "THE")

> To produce a smaller binary use the CMake flags `CMAKE_BUILD_TYPE=MinSizeRel` and
> `BUILD_SHARED_LIBS=ON`.

```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=MinSizeRel \
  -DBUILD_SHARED_LIBS=ON \
  -DMLX_BUILD_CPU=OFF \
  -DMLX_BUILD_SAFETENSORS=OFF \
  -DMLX_BUILD_GGUF=OFF \
  -DMLX_METAL_JIT=ON
```

> THE `MLX_METAL_JIT` flag minimizes the size of the MLX Metal library which contains pre-built GPU
> kernels. This substantially reduces the size of the Metal library by run-time compiling kernels the
> first time they are used in MLX on a given machine. Note run-time compilation incurs a cold-start
> cost which can be anwywhere from a few hundred millisecond to a few seconds depending on the
> application. Once a kernel is compiled, it will be cached by the system. **The Metal kernel cache
> persists across reboots.**

### 1.11 Linux (CPU-only) from source

```bash
apt-get update -y
apt-get install libblas-dev liblapack-dev liblapacke-dev -y
```

### 1.12 CUDA from source

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
dpkg -i cuda-keyring_1.1-1_all.deb
apt-get update -y
apt-get -y install cuda-toolkit-12-9
apt-get install libblas-dev liblapack-dev liblapacke-dev libcudnn9-dev-cuda-12 -y
```

Python build:

```bash
CMAKE_ARGS="-DMLX_BUILD_CUDA=ON" pip install -e ".[dev]"
```

C++ build:

```bash
mkdir -p build && cd build
cmake .. -DMLX_BUILD_CUDA=ON && make -j
```

### 1.13 Build troubleshooting (verbatim)

**Metal not found**

```
error: unable to find utility "metal", not a developer tool or in PATH
```

```bash
xcode-select --install
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
```

**x86 Shell**

> If the output of `uname -p` is `x86` then your shell is running as x86 via Rosetta instead of
> natively.
>
> To fix this, find the application in Finder (`/Applications` for iTerm, `/Applications/Utilities`
> for Terminal), right-click, and click "Get Info". Uncheck "Open using Rosetta", close the "Get Info"
> window, and restart your terminal.

```bash
$ uname -p
arm
```

Also check cmake's architecture:

```bash
$ cmake --system-information | grep CMAKE_HOST_SYSTEM_PROCESSOR
CMAKE_HOST_SYSTEM_PROCESSOR "arm64"
```

> If you see `"x86_64"`, try re-installing `cmake`. If you see `"arm64"` but the build errors out with
> "Building for x86_64 on macOS is not supported." wipe your build cache with `rm -rf build/` and try
> again.

---

## 2. Quick Start (`usage/quick_start.html`) — verbatim

```python
>> import mlx.core as mx
>> a = mx.array([1, 2, 3, 4])
>> a.shape
[4]
>> a.dtype
int32
>> b = mx.array([1.0, 2.0, 3.0, 4.0])
>> b.dtype
float32
```

> Operations in MLX are lazy. The outputs of MLX operations are not computed until they are needed. To
> force an array to be evaluated use `eval()`. Arrays will automatically be evaluated in a few cases.
> For example, inspecting a scalar with `array.item()`, printing an array, or converting an array from
> `array` to `numpy.ndarray` all automatically evaluate the array.

```python
>> c = a + b   # c not yet evaluated
>> mx.eval(c)  # evaluates c
>> c = a + b
>> print(c)    # Also evaluates c
array([2, 4, 6, 8], dtype=float32)
>> c = a + b
>> import numpy as np
>> np.array(c) # Also evaluates c
array([2., 4., 6., 8.], dtype=float32)
```

Function/graph transformations:

> MLX has standard function transformations like `grad()` and `vmap()`. Transformations can be
> composed arbitrarily. For example `grad(vmap(grad(fn)))` (or any other composition) is allowed.

```python
>> x = mx.array(0.0)
>> mx.sin(x)
array(0, dtype=float32)
>> mx.grad(mx.sin)(x)
array(1, dtype=float32)
>> mx.grad(mx.grad(mx.sin))(x)
array(-0, dtype=float32)
```

Note `.shape` returns a **list** `[4]`, not a tuple. (Confirmed verbatim above.)

---

## 3. Lazy Evaluation (`usage/lazy_evaluation.html`) — verbatim

### Why Lazy Evaluation

> When you perform operations in MLX, no computation actually happens. Instead a compute graph is
> recorded. The actual computation only happens if an `eval()` is performed.

**Transforming Compute Graphs:**

> Lazy evaluation lets us record a compute graph without actually doing any computations. This is
> useful for function transformations like `grad()` and `vmap()` and graph optimizations.
>
> Currently, MLX does not compile and rerun compute graphs. They are all generated dynamically.
> However, lazy evaluation makes it much easier to integrate compilation for future performance
> enhancements.

**Only Compute What You Use:**

```python
def fun(x):
    a = fun1(x)
    b = expensive_fun(a)
    return a, b

y, _ = fun(x)
```

> Here, we never actually compute the output of `expensive_fun`. Use this pattern with care though, as
> the graph of `expensive_fun` is still built, and that has some cost associated to it.

> Say you have a very large model `Model` derived from `mlx.nn.Module`. You can instantiate this model
> with `model = Model()`. Typically, this will initialize all of the weights as `float32`, but the
> initialization does not actually compute anything until you perform an `eval()`. If you update the
> model with `float16` weights, your maximum consumed memory will be half that required if eager
> computation was used instead.

```python
model = Model() # no memory used yet
model.load_weights("weights_fp16.safetensors")
```

### When to Evaluate

Bad pattern (verbatim):

```python
for _ in range(100):
     a = a + b
     mx.eval(a)
     b = b * 2
     mx.eval(b)
```

> This is a bad idea because there is some fixed overhead with each graph evaluation. On the other
> hand, there is some slight overhead which grows with the compute graph size, so extremely large
> graphs (while computationally correct) can be costly.
>
> Luckily, a wide range of compute graph sizes work pretty well with MLX: **anything from a few tens of
> operations to many thousands of operations per evaluation should be okay.**

Recommended pattern (verbatim):

```python
for batch in dataset:

    # Nothing has been evaluated yet
    loss, grad = value_and_grad_fn(model, batch)

    # Still nothing has been evaluated
    optimizer.update(model, grad)

    # Evaluate the loss and the new parameters which will
    # run the full gradient computation and optimizer update
    mx.eval(loss, model.parameters())
```

### Implicit evaluation triggers (verbatim)

> An important behavior to be aware of is when the graph will be implicitly evaluated. Anytime you
> `print` an array, convert it to an `numpy.ndarray`, or otherwise access its memory via `memoryview`,
> the graph will be evaluated. Saving arrays via `save()` (or any other MLX saving functions) will
> also evaluate the array.
>
> Calling `array.item()` on a scalar array will also evaluate it. In the example above, printing the
> loss (`print(loss)`) or adding the loss scalar to a list (`losses.append(loss.item())`) would cause
> a graph evaluation. If these lines are before `mx.eval(loss, model.parameters())` then this will be
> a **partial evaluation, computing only the forward pass.**
>
> Also, calling `eval()` on an array or set of arrays multiple times is perfectly fine. This is
> effectively a no-op.

### Control-flow warning (verbatim)

> **Warning**: Using scalar arrays for control-flow will cause an evaluation.

```python
def fun(x):
    h, y = first_layer(x)
    if y > 0:  # An evaluation is done here!
        z = second_layer_a(h)
    else:
        z = second_layer_b(h)
    return z
```

> Using arrays for control flow should be done with care. The above example works and can even be used
> with gradient transformations. However, this can be very inefficient if evaluations are done too
> frequently.

### API

```
eval(*args) -> None
```
> Evaluate an `array` or tree of `array`.
> `*args` (arrays or trees of arrays) – Each argument can be a single array or a tree of arrays. If a
> tree is given the nodes can be a Python `list`, `tuple` or `dict`. Leaves which are not arrays are
> ignored.

```
async_eval(*args)
```
> Asynchronously evaluate an `array` or tree of `array`.
> **Note**: This is an experimental API and may change in future versions.

```python
>>> x = mx.array(1.0)
>>> y = mx.exp(x)
>>> mx.async_eval(y)
>>> print(y)
>>>
>>> y = mx.exp(x)
>>> mx.async_eval(y)
>>> z = y + 3
>>> mx.async_eval(z)
>>> print(z)
```

---

## 4. Unified Memory (`usage/unified_memory.html`) — verbatim (full page, it is short)

> Apple silicon has a unified memory architecture. The CPU and GPU have direct access to the same
> memory pool. MLX is designed to take advantage of that.
>
> Concretely, when you make an array in MLX you don't have to specify its location:

```python
a = mx.random.normal((100,))
b = mx.random.normal((100,))
```

> Both `a` and `b` live in unified memory.
>
> In MLX, rather than moving arrays to devices, you specify the device when you run the operation. Any
> device can perform any operation on `a` and `b` without needing to move them from one memory
> location to another. For example:

```python
mx.add(a, b, stream=mx.cpu)
mx.add(a, b, stream=mx.gpu)
```

> In the above, both the CPU and the GPU will perform the same add operation. The operations can (and
> likely will) be run in parallel since there are no dependencies between them. See Using Streams for
> more information the semantics of streams in MLX.
>
> In the above `add` example, there are no dependencies between operations, so there is no possibility
> for race conditions. If there are dependencies, the MLX scheduler will automatically manage them.
> For example:

```python
c = mx.add(a, b, stream=mx.cpu)
d = mx.add(a, c, stream=mx.gpu)
```

> In the above case, the second `add` runs on the GPU but it depends on the output of the first `add`
> which is running on the CPU. MLX will automatically insert a dependency between the two streams so
> that the second `add` only starts executing after the first is complete and `c` is available.

### A Simple Example (verbatim)

```python
def fun(a, b, d1, d2):
  x = mx.matmul(a, b, stream=d1)
  for _ in range(500):
      b = mx.exp(b, stream=d2)
  return x, b
```

```python
a = mx.random.uniform(shape=(4096, 512))
b = mx.random.uniform(shape=(512, 4))
```

> The first `matmul` operation is a good fit for the GPU since it's more compute dense. The second
> sequence of operations are a better fit for the CPU, since they are very small and would probably be
> overhead bound on the GPU.
>
> If we time the computation fully on the GPU, we get **2.8 milliseconds**. But if we run the
> computation with `d1=mx.gpu` and `d2=mx.cpu`, then the time is only about **1.4 milliseconds**,
> about twice as fast. These times were measured on an **M1 Max**.

---

## 5. Using Streams (`usage/using_streams.html`) — verbatim (this page is TINY; the whole body follows)

> ## Specifying the `Stream`
>
> All operations (including random number generation) take an optional keyword argument `stream`. The
> `stream` kwarg specifies which `Stream` the operation should run on. If the stream is unspecified
> then the operation is run on the default stream of the default device:
> `mx.default_stream(mx.default_device())`. The `stream` kwarg can also be a `Device` (e.g.
> `stream=my_device`) in which case the operation is run on the default stream of the provided device
> `mx.default_stream(my_device)`.

That is the **entire** page. Everything else about streams is in the API reference (§13).

---

## 6. Indexing Arrays (`usage/indexing.html`) — verbatim highlights

Basic indexing works like NumPy: integers, negative indices, slices, `...`/`Ellipsis`, `None` for new
axis, and array indices.

```python
>>> arr = mx.arange(10)
>>> arr[3]
array(3, dtype=int32)
>>> arr[-2] # negative indexing works
array(8, dtype=int32)
>>> arr[2:8:2] # start, stop, stride
array([2, 4, 6], dtype=int32)
```

### Differences from NumPy (verbatim — IMPORTANT FOOTGUNS)

> **Note**: MLX indexing is different from NumPy indexing in two important ways:
>
> - **Indexing does not perform bounds checking. Indexing out of bounds is undefined behavior.**
> - Boolean mask based indexing is supported **for assignment only** (see Boolean Mask Assignment).
>
> The reason for the lack of bounds checking is that exceptions cannot propagate from the GPU.
> Performing bounds checking for array indices before launching the kernel would be extremely
> inefficient.
>
> Indexing with boolean masks is something that MLX may support in the future. In general, MLX has
> limited support for operations for which output *shapes* are dependent on input *data*. Other
> examples of these types of operations which MLX does not yet support include `numpy.nonzero()` and
> the single input version of `numpy.where()`.

### In-place updates

> Note that unlike NumPy, **slicing an array creates a copy, not a view**. So mutating it does not
> mutate the original array:

```python
>>> a = mx.array([1, 2, 3])
>>> b = a[:]
>>> b[2] = 0
>>> b
array([1, 2, 0], dtype=int32)
>>> a
array([1, 2, 3], dtype=int32)
```

> Also unlike NumPy, **updates to the same location are nondeterministic**:

```python
>>> a = mx.array([1, 2, 3])
>>> a[[0, 0]] = mx.array([4, 5])
```

> The first element of `a` could be `4` or `5`.

Gradients through in-place updates work:

```python
def fun(x, idx):
    x[idx] = 2.0
    return x.sum()

dfdx = mx.grad(fun)(mx.array([1.0, 2.0, 3.0]), mx.array([1]))
print(dfdx)  # Prints: array([1, 0, 1], dtype=float32)
```

### Boolean Mask Assignment (verbatim)

> MLX supports boolean indices using NumPy syntax. A mask must already be a `bool_` MLX `array` or a
> NumPy `ndarray` with `dtype=bool`. Other index types are routed through the standard scatter code.

```python
>>> a = mx.array([1.0, 2.0, 3.0])
>>> mask = mx.array([True, False, True])
>>> updates = mx.array([5.0, 6.0])
>>> a[mask] = updates
>>> a
array([5.0, 2.0, 6.0], dtype=float32)
```

> Scalar assignments broadcast to every `True` entry in `mask`. For non-scalar assignments, `updates`
> must provide at least as many elements as there are `True` entries in `mask`.

> Boolean masks follow NumPy semantics:
> - The mask shape must match the shape of the axes it indexes **exactly**. The only exception is a
>   scalar boolean mask, which broadcasts to the full array.
> - Any axes not covered by the mask are taken in full.

```python
>>> a = mx.arange(1000).reshape(10, 10, 10)
>>> a[mx.random.normal((10, 10)) > 0.0] = 0  # valid: mask covers axes 0 and 1
```

> The mask of shape `(10, 10)` applies to the first two axes, so `a[mask]` selects the 1-D slices
> `a[i, j, :]` where `mask[i, j]` is `True`. Shapes such as `(1, 10, 10)` or `(10, 10, 1)` do not match
> the indexed axes and therefore raise errors.

### `array.at` (from `python/_autosummary/mlx.core.array.at.html`)

> **property `array.at`** — Used to apply updates at the given indices.
>
> **Note**: Regular in-place updates map to assignment. For instance `x[idx] += y` maps to
> `x[idx] = x[idx] + y`. As a result, assigning to the same index ignores all but one update. Using
> `x.at[idx].add(y)` will correctly apply all updates to all indices.

| `array.at` syntax | In-place syntax |
|---|---|
| `x = x.at[idx].add(y)` | `x[idx] += y` |
| `x = x.at[idx].subtract(y)` | `x[idx] -= y` |
| `x = x.at[idx].multiply(y)` | `x[idx] *= y` |
| `x = x.at[idx].divide(y)` | `x[idx] /= y` |
| `x = x.at[idx].maximum(y)` | `x[idx] = mx.maximum(x[idx], y)` |
| `x = x.at[idx].minimum(y)` | `x[idx] = mx.minimum(x[idx], y)` |

```python
>>> a = mx.array([0, 0])
>>> idx = mx.array([0, 1, 0, 1])
>>> a[idx] += 1
>>> a
array([1, 1], dtype=int32)
>>>
>>> a = mx.array([0, 0])
>>> a.at[idx].add(1)
array([2, 2], dtype=int32)
```

---

## 7. Saving and Loading Arrays (`usage/saving_and_loading.html`) — verbatim

### Serialization Formats table (exact)

| Format | Extension | Function | Notes |
|---|---|---|---|
| NumPy | `.npy` | `save()` | Single arrays only |
| NumPy archive | `.npz` | `savez()` and `savez_compressed()` | Multiple arrays |
| Safetensors | `.safetensors` | `save_safetensors()` | Multiple arrays |
| GGUF | `.gguf` | `save_gguf()` | Multiple arrays |

> The `load()` function will load any of the supported serialization formats. It determines the format
> from the extensions. The output of `load()` depends on the format.

```python
>>> a = mx.array([1.0])
>>> mx.save("array", a)
```

> The array `a` will be saved in the file `array.npy` (notice the extension is automatically added).
> Including the extension is optional; if it is missing it will be added.

```python
>>> mx.load("array.npy")
array([1], dtype=float32)
```

```python
>>> a = mx.array([1.0])
>>> b = mx.array([2.0])
>>> mx.savez("arrays", a, b=b)
```

> For compatibility with `numpy.savez()` the MLX `savez()` takes arrays as arguments. **If the keywords
> are missing, then default names will be provided.**

```python
>>> mx.load("arrays.npz")
{'b': array([2], dtype=float32), 'arr_0': array([1], dtype=float32)}
```

```python
>>> a = mx.array([1.0])
>>> b = mx.array([2.0])
>>> mx.save_safetensors("arrays", {"a": a, "b": b})
```

### API signatures

```
load(file: file | str | Path, /, format: str | None = None, return_metadata: bool = False, *,
     stream: None | Stream | Device = None)
     -> array | dict[str, array] | Tuple[dict[str, array], dict[str, Any]]
```
> The supported formats are `.npy`, `.npz`, `.safetensors`, and `.gguf`.
> `format` – If `None`, the format is inferred from the file extension. Supported formats: `npy`,
> `npz`, and `safetensors`. Default: `None`.
> `return_metadata` – Load the metadata for formats which support matadata [sic]. Default: `False`.
>
> **Warning**: When loading unsupported quantization formats from GGUF, tensors will automatically cast
> to `mx.float16`

```
save_safetensors(file: file | str | Path, arrays: dict[str, array],
                 metadata: dict[str, str] | None = None)
```

---

## 8. Function Transforms (`usage/function_transforms.html`) — verbatim

> MLX uses composable function transformations for automatic differentiation, vectorization, and
> compute graph optimizations. […] The key idea behind composable function transformations is that
> **every transformation returns a function which can be further transformed.**

```python
>>> dfdx = mx.grad(mx.sin)
>>> dfdx(mx.array(mx.pi))
array(-1, dtype=float32)
>>> mx.cos(mx.array(mx.pi))
array(-1, dtype=float32)
```

```python
>>> d2fdx2 = mx.grad(mx.grad(mx.sin))
>>> d2fdx2(mx.array(mx.pi / 2))
array(-1, dtype=float32)
>>> mx.sin(mx.array(mx.pi / 2))
array(1, dtype=float32)
```

> Using `grad()` on the output of `grad()` is always ok. You keep getting higher order derivatives.

### Automatic Differentiation

> **Note**: If you are coming to MLX from PyTorch, you no longer need functions like `backward`,
> `zero_grad`, and `detach`, or properties like `requires_grad`.

```python
def loss_fn(w, x, y):
    return mx.mean(mx.square(w * x - y))

w = mx.array(1.0)
x = mx.array([0.5, -0.5])
y = mx.array([1.5, -1.5])

# Computes the gradient of loss_fn with respect to w:
grad_fn = mx.grad(loss_fn)
dloss_dw = grad_fn(w, x, y)
# Prints array(-1, dtype=float32)
print(dloss_dw)

# To get the gradient with respect to x we can do:
grad_fn = mx.grad(loss_fn, argnums=1)
dloss_dx = grad_fn(w, x, y)
# Prints array([-1, 1], dtype=float32)
print(dloss_dx)
```

```python
# Computes the gradient of loss_fn with respect to w:
loss_and_grad_fn = mx.value_and_grad(loss_fn)
loss, dloss_dw = loss_and_grad_fn(w, x, y)

# Prints array(1, dtype=float32)
print(loss)

# Prints array(-1, dtype=float32)
print(dloss_dw)
```

Nested containers (`list`, `tuple`, `dict`):

```python
def loss_fn(params, x, y):
    w, b = params["weight"], params["bias"]
    h = w * x + b
    return mx.mean(mx.square(h - y))

params = {"weight": mx.array(1.0), "bias": mx.array(0.0)}
x = mx.array([0.5, -0.5])
y = mx.array([1.5, -1.5])

# Computes the gradient of loss_fn with respect to both the
# weight and bias:
grad_fn = mx.grad(loss_fn)
grads = grad_fn(params, x, y)

# Prints
# {'weight': array(-1, dtype=float32), 'bias': array(0, dtype=float32)}
print(grads)
```

> In some cases you may want to stop gradients from propagating through a part of the function. You
> can use the `stop_gradient()` for that.

### Automatic Vectorization

> **Warning**: Some operations are not yet supported with `vmap()`. If you encounter an error like:
> `ValueError: Primitive's vmap not implemented.` file an issue and include your function. We will
> prioritize including it.

```python
xs = mx.random.uniform(shape=(4096, 100))
ys = mx.random.uniform(shape=(100, 4096))

def naive_add(xs, ys):
    return [xs[i] + ys[:, i] for i in range(xs.shape[0])]
```

```python
# Vectorize over the second dimension of x and the
# first dimension of y
vmap_add = mx.vmap(lambda x, y: x + y, in_axes=(0, 1))
```

```python
import timeit

print(timeit.timeit(lambda: mx.eval(naive_add(xs, ys)), number=100))
print(timeit.timeit(lambda: mx.eval(vmap_add(xs, ys)), number=100))
```

> On an M1 Max the naive version takes in total `5.639` seconds whereas the vectorized version takes
> only `0.024` seconds, **more than 200 times faster.**
>
> Of course, this operation is quite contrived. A better approach is to simply do `xs + ys.T`, but for
> more complex functions `vmap()` can be quite handy.

### Exact transform signatures (from `python/_autosummary/`)

```
grad(fun: Callable[P, R],
     argnums: int | Sequence[int] | None = None,
     argnames: str | Sequence[str] = []) -> Callable[P, Any]
```
> `argnums` – Specify the index (or indices) of the positional arguments of `fun` to compute the
> gradient with respect to. **If neither `argnums` nor `argnames` are provided `argnums` defaults to
> `0`** indicating `fun`'s first argument.
> `argnames` – Specify keyword arguments of `fun` to compute gradients with respect to. It defaults to
> `[]` so no gradients for keyword arguments by default.

```
value_and_grad(fun: Callable[P, R],
               argnums: int | Sequence[int] | None = None,
               argnames: str | Sequence[str] = []) -> Callable[P, Tuple[R, Any]]
```
> The function passed to `value_and_grad()` should return **either a scalar loss or a tuple in which
> the first element is a scalar loss and the remaining elements can be anything.**

```python
import mlx.core as mx

def mse(params, inputs, targets):
    outputs = forward(params, inputs)
    lvalue = (outputs - targets).square().mean()
    return lvalue

# Returns lvalue, dlvalue/dparams
lvalue, grads = mx.value_and_grad(mse)(params, inputs, targets)

def lasso(params, inputs, targets, a=1.0, b=1.0):
    outputs = forward(params, inputs)
    mse = (outputs - targets).square().mean()
    l1 = mx.abs(outputs - targets).mean()

    loss = a*mse + b*l1

    return loss, mse, l1

(loss, mse, l1), grads = mx.value_and_grad(lasso)(params, inputs, targets)
```

```
vmap(fun: Callable[P, R], in_axes: object = 0, out_axes: object = 0) -> Callable[P, R]
```
> `in_axes` – An integer or a valid **prefix tree** of the inputs to `fun` where each node specifies
> the vmapped axis. **If the value is `None` then the corresponding input(s) are not vmapped.**
> Defaults to `0`.
> `out_axes` – same idea for outputs. Defaults to `0`.

```
vjp(fun: Callable, primals: list[array], cotangents: list[array])
    -> tuple[list[array], list[array]]
```
> Computes the product of the `cotangents` with the Jacobian of a function `fun` evaluated at
> `primals`. The `cotangents` should be the same in number, shape, and type as the outputs of `fun`.
> Returns a tuple with the outputs of `fun` in the first position and the vector-Jacobian products in
> the second position.

```python
import mlx.core as mx

outs, vjps = mx.vjp(mx.sin, (mx.array(1.0),), (mx.array(1.0),))
```

```
jvp(fun: Callable, primals: list[array], tangents: list[array])
    -> tuple[list[array], list[array]]
```

```
checkpoint(fun: Callable[P, R]) -> Callable[P, R]
```
> Transform the passed callable to one that performs gradient checkpointing with respect to the inputs
> of the callable. **Use this to reduce memory use for gradient computations at the expense of
> increased computation.**

### `mx.custom_function` (verbatim from autosummary)

```
class custom_function(*args, **kwargs)
__init__(self, f: Callable)
```
Methods: `jvp(self, f)`, `vjp(self, f)`, `vmap(self, f)`.

> This class is meant to be used as a function decorator. Instances are callables that behave
> identically to the wrapped function. However, when a function transformation is used (e.g. computing
> gradients using `value_and_grad()`) then the functions defined via `custom_function.vjp()`,
> `custom_function.jvp()` and `custom_function.vmap()` are used instead of the default transformation.
>
> Note, all custom transformations are **optional**. Undefined transformations fall back to the default
> behaviour.

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

**FOOTGUN (verbatim):**

> All `custom_function` instances behave as pure functions. Namely, any variables captured will be
> treated as constants and no gradients will be computed with respect to the captured arrays.

```python
import mlx.core as mx

def g(x, y):
    @mx.custom_function
    def f(x):
        return x * y

    @f.vjp
    def f_vjp(x, dx, fx):
        # Note that we have only x, dx and fx and nothing with respect to y
        raise ValueError("Abort!")

    return f(x)

x = mx.array(2.0)
y = mx.array(3.0)
print(g(x, y))                      # prints 6.0
print(mx.grad(g)(x, y))             # Raises exception
print(mx.grad(g, argnums=1)(x, y))  # prints 0.0
```

Note the doc's own inconsistency: the `f.vjp` signature is documented once as
`f_vjp(primals, cotangent, output)` and once as `f_vjp(x, dx, fx)`. In the Metal-kernel page it is
`grid_sample_vjp(primals, cotangent, _)`. So the real arity is **3: (primals, cotangent, output)**.

---

## 9. Compilation (`usage/compile.html`) — verbatim, FULL

Opening:

> MLX has a `compile()` function transformation which compiles computation graphs. Function compilation
> results in smaller graphs by merging common work and fusing certain operations. In many cases this
> can lead to big improvements in run-time and memory use.
>
> Getting started with `compile()` is simple, but there are some edge cases that are good to be aware
> of for more complex graphs and advanced usage.

### 9.1 Basics of Compile

```python
def fun(x, y):
    return mx.exp(-x) + y

x = mx.array(1.0)
y = mx.array(2.0)

# Regular call, no compilation
# Prints: array(2.36788, dtype=float32)
print(fun(x, y))

# Compile the function
compiled_fun = mx.compile(fun)

# Prints: array(2.36788, dtype=float32)
print(compiled_fun(x, y))
```

> The output of both the regular function and the compiled function is the same up to numerical
> precision.
>
> The first time you call a compiled function, MLX will build the compute graph, optimize it, and
> generate and compile code. This can be relatively slow. However, MLX will cache compiled functions,
> so calling a compiled function multiple times will not initiate a new compilation. This means you
> should typically compile functions that you plan to use more than once.

```python
def fun(x, y):
    return mx.exp(-x) + y

x = mx.array(1.0)
y = mx.array(2.0)

compiled_fun = mx.compile(fun)

# Compiled here
compiled_fun(x, y)

# Not compiled again
compiled_fun(x, y)

# Not compiled again
mx.compile(fun)(x, y)
```

Note the third line: **`mx.compile(fun)` on the same underlying function object hits the cache.**

Recompilation triggers (verbatim list):

> There are some important cases to be aware of that can cause a function to be recompiled:
> - Changing the shape or number of dimensions
> - Changing the type of any of the inputs
> - Changing the number of inputs to the function
>
> In certain cases only some of the compilation stack will be rerun (for example when changing the
> shapes) and in other cases the full compilation stack will be rerun (for example when changing the
> types). In general you should avoid compiling functions too frequently.

Anti-pattern:

```python
a = mx.array(1.0)
# Don't do this, compiles lambda at each iteration
for _ in range(5):
    mx.compile(lambda x: mx.exp(mx.abs(x)))(a)
```

### 9.2 Example Speedup

```python
def gelu(x):
    return x * (1 + mx.erf(x / math.sqrt(2))) / 2
```

> If you use this function with small arrays, it will be overhead bound. If you use it with large
> arrays it will be memory bandwidth bound. However, all of the operations in the `gelu` are fusible
> into a single kernel with `compile()`. This can speedup both cases considerably.

```python
import time

def timeit(fun, x):
    # warm up
    for _ in range(10):
        mx.eval(fun(x))

    tic = time.perf_counter()
    for _ in range(100):
        mx.eval(fun(x))
    toc = time.perf_counter()
    tpi = 1e3 * (toc - tic) / 100
    print(f"Time per iteration {tpi:.3f} (ms)")
```

```python
x = mx.random.uniform(shape=(32, 1000, 4096))
timeit(gelu, x)
timeit(mx.compile(gelu), x)
```

> On an M1 Max the times are **15.5 and 3.1 milliseconds**. The compiled `gelu` is **five times faster**.

### 9.3 Debugging

> When a compiled function is first called, it is traced with placeholder inputs. This means you can't
> evaluate arrays (for example to print their contents) inside compiled functions.

```python
@mx.compile
def fun(x):
    z = -x
    print(z)  # Crash
    return mx.exp(z)

fun(mx.array(5.0))
```

> For debugging, inspecting arrays can be helpful. One way to do that is to globally disable
> compilation using the `disable_compile()` function or `MLX_DISABLE_COMPILE` flag.

```python
@mx.compile
def fun(x):
    z = -x
    print(z)  # Okay
    return mx.exp(z)

mx.disable_compile()
fun(mx.array(5.0))
```

APIs: `mx.disable_compile()` — "Globally disable compilation."; `mx.enable_compile()` — "Globally
enable compilation." Environment variable: **`MLX_DISABLE_COMPILE`**.

### 9.4 Pure Functions

> Compiled functions are intended to be *pure*; that is they should not have side effects.

```python
state = []

@mx.compile
def fun(x, y):
    z = x + y
    state.append(z)
    return mx.exp(z)

fun(mx.array(1.0), mx.array(2.0))
# Crash!
print(state)
```

> After the first call of `fun`, the `state` list will hold a **placeholder array**. The placeholder
> does not have any data; it is only used to build the computation graph. Printing such an array
> results in a crash.

Option 1 — return state as an output:

```python
state = []

@mx.compile
def fun(x, y):
    z = x + y
    state.append(z)
    return mx.exp(z), state

_, state = fun(mx.array(1.0), mx.array(2.0))
# Prints [array(3, dtype=float32)]
print(state)
```

Option 2 — `outputs=` capture:

```python
from functools import partial

state = []

# Tell compile to capture state as an output
@partial(mx.compile, outputs=state)
def fun(x, y):
    z = x + y
    state.append(z)
    return mx.exp(z)

fun(mx.array(1.0), mx.array(2.0))
# Prints [array(3, dtype=float32)]
print(state)
```

> This is particularly useful for compiling a function which includes an update to a container of
> arrays, as is commonly done when training the parameters of a `mlx.nn.Module`.

**Captured non-argument arrays become CONSTANTS:**

```python
state = [mx.array(1.0)]

@mx.compile
def fun(x):
    return x + state[0]

# Prints array(2, dtype=float32)
print(fun(mx.array(1.0)))

# Update state
state[0] = mx.array(5.0)

# Still prints array(2, dtype=float32)
print(fun(mx.array(1.0)))
```

Fix 1 — pass state as an argument:

```python
state = [mx.array(1.0)]

@mx.compile
def fun(x, state):
    return x + state[0]

# Prints array(2, dtype=float32)
print(fun(mx.array(1.0), state))
...
# Prints array(6, dtype=float32)
print(fun(mx.array(1.0), state))
```

Fix 2 — `inputs=` capture:

```python
from functools import partial

state = [mx.array(1.0)]

# Tell compile to capture state as an input
@partial(mx.compile, inputs=state)
def fun(x):
    return x + state[0]

# Prints array(2, dtype=float32)
print(fun(mx.array(1.0)))

# Update state
state[0] = mx.array(5.0)

# Prints array(6, dtype=float32)
print(fun(mx.array(1.0)))
```

### 9.5 Compiling Training Graphs (verbatim, both versions)

Uncompiled baseline:

```python
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim

# 4 examples with 10 features each
x = mx.random.uniform(shape=(4, 10))

# 0, 1 targets
y = mx.array([0, 1, 0, 1])

# Simple linear model
model = nn.Linear(10, 1)

# SGD with momentum
optimizer = optim.SGD(learning_rate=0.1, momentum=0.8)

def loss_fn(model, x, y):
    logits = model(x).squeeze()
    return nn.losses.binary_cross_entropy(logits, y)

loss_and_grad_fn = nn.value_and_grad(model, loss_fn)

# Perform 10 steps of gradient descent
for it in range(10):
    loss, grads = loss_and_grad_fn(model, x, y)
    optimizer.update(model, grads)
    mx.eval(model.parameters(), optimizer.state)
```

Compiled version:

```python
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from functools import partial

# 4 examples with 10 features each
x = mx.random.uniform(shape=(4, 10))

# 0, 1 targets
y = mx.array([0, 1, 0, 1])

# Simple linear model
model = nn.Linear(10, 1)

# SGD with momentum
optimizer = optim.SGD(learning_rate=0.1, momentum=0.8)

def loss_fn(model, x, y):
    logits = model(x).squeeze()
    return nn.losses.binary_cross_entropy(logits, y)

# The state that will be captured as input and output
state = [model.state, optimizer.state]

@partial(mx.compile, inputs=state, outputs=state)
def step(x, y):
    loss_and_grad_fn = nn.value_and_grad(model, loss_fn)
    loss, grads = loss_and_grad_fn(model, x, y)
    optimizer.update(model, grads)
    return loss

# Perform 10 steps of gradient descent
for it in range(10):
    loss = step(x, y)
    # Evaluate the model and optimizer state
    mx.eval(state)
    print(loss)
```

> **Note**: If you are using a module which performs random sampling such as `mlx.nn.Dropout()`, make
> sure you also include `mx.random.state` in the `state` captured by `compile()`, i.e.
> `state = [model.state, optimizer.state, mx.random.state]`.

### 9.6 Transformations with Compile

```python
grad_fn = mx.grad(mx.exp)

compiled_grad_fn = mx.compile(grad_fn)

# Prints: array(2.71828, dtype=float32)
print(grad_fn(mx.array(1.0)))

# Also prints: array(2.71828, dtype=float32)
print(compiled_grad_fn(mx.array(1.0)))
```

> **Note**: In order to compile as much as possible, **a transformation of a compiled function will not
> by default be compiled**. To compile the transformed function simply pass it through `compile()`.

```python
@mx.compile
def inner(x):
    return mx.exp(-mx.abs(x))

def outer(x):
    inner(inner(x))

# Compiling the outer function is good to do as it will likely
# be faster even though the inner functions are compiled
fun = mx.compile(outer)
```

### 9.7 Shapeless Compilation (verbatim)

> When the shape of an input to a compiled function changes, the function is recompiled. You can
> compile a function once and run it on inputs with variable shapes by specifying `shapeless=True` to
> `compile()`. In this case changes to the shapes of the inputs do not cause the function to be
> recompiled.

```python
def fun(x, y):
    return mx.abs(x + y)

compiled_fun = mx.compile(fun, shapeless=True)

x = mx.array(1.0)
y = mx.array(-2.0)

# Firt call compiles the function
print(compiled_fun(x, y))

# Second call with different shapes
# does not recompile the function
x = mx.array([1.0, -6.0])
y = mx.array([-2.0, 3.0])
print(compiled_fun(x, y))
```

> Use shapeless compilations carefully. Since compilation is not triggered when shapes change, **any
> graphs which are conditional on the input shapes will not work as expected.** Shape-dependent
> computations are common and sometimes subtle to detect. For example:

```python
def fun(x):
    return x.reshape(x.shape[0] * x.shape[1], -1)

compiled_fun = mx.compile(fun, shapeless=True)

x = mx.random.uniform(shape=(2, 3, 4))

out = compiled_fun(x)

x = mx.random.uniform(shape=(5, 5, 3))

# Error, can't reshape (5, 5, 3) to (6, -1)
out = compiled_fun(x)
```

> The second call to the `compiled_fun` fails because of the call to `reshape()` which uses the static
> shape of `x` in the first call. We can fix this by using `flatten()` to avoid hardcoding the shape
> of `x`:

```python
def fun(x):
    return x.flatten(0, 1)

compiled_fun = mx.compile(fun, shapeless=True)

x = mx.random.uniform(shape=(2, 3, 4))

out = compiled_fun(x)

x = mx.random.uniform(shape=(5, 5, 3))

# Ok
out = compiled_fun(x)
```

### 9.8 `mx.compile` exact signature

```
compile(fun: Callable[P, R],
        inputs: object | None = None,
        outputs: object | None = None,
        shapeless: bool = False) -> Callable[P, R]
```

> `inputs` (*list or dict, optional*) – These inputs will be captured during the function compilation
> along with the inputs to `fun`. The `inputs` can be a `list` or a `dict` containing arbitrarily
> nested lists, dictionaries, or arrays. **Leaf nodes that are not `array` are ignored.** Default:
> `None`
>
> `outputs` (*list or dict, optional*) – These outputs will be captured and updated in a compiled
> function. […] Leaf nodes that are not `array` are ignored. Default: `None`
>
> `shapeless` (*bool, optional*) – A function compiled with the `shapeless` option enabled will not be
> recompiled when the input shape changes. **Not all functions can be compiled with `shapeless`
> enabled. Attempting to compile such functions with shapeless enabled will throw.** Note, **changing
> the number of dimensions or type of any input will result in a recompilation even with `shapeless`
> set to `True`.** Default: `False`

**KEY NUANCE:** shapeless still recompiles on *ndim* change and on *dtype* change. It only avoids
recompilation for same-ndim shape changes.

---

## 10. Conversion to NumPy and Other Frameworks (`usage/numpy.html`) — verbatim

> MLX array supports conversion between other frameworks with either:
> - The Python Buffer Protocol.
> - DLPack.

```python
import mlx.core as mx
import numpy as np

a = mx.arange(3)
b = np.array(a) # copy of a
c = mx.array(b) # copy of b
```

> **Note**: Since NumPy does not support `bfloat16` arrays, you will need to convert to `float16` or
> `float32` first: `np.array(a.astype(mx.float32))`. Otherwise, you will receive an error like:
> `Item size 2 for PEP 3118 buffer format string does not match the dtype V item size 0.`

```python
a = mx.arange(3)
a_view = np.array(a, copy=False)
print(a_view.flags.owndata)  # False
a_view[0] = 1
print(a[0].item())  # 1
```

> **Note**: NumPy arrays with type `float64` will be default converted to MLX arrays with type
> `float32`.

> A NumPy array view is a normal NumPy array, except that it does not own its memory. This means
> writing to the view is reflected in the original array.
>
> While this is quite powerful to prevent copying arrays, it should be noted that **external changes to
> the memory of arrays cannot be reflected in gradients.**

```python
def f(x):
    x_view = np.array(x, copy=False)
    x_view[:] *= x_view # modify memory without telling mx
    return x.sum()

x = mx.array([3.0])
y, df = mx.value_and_grad(f)(x)
print("f(x) = x² =", y.item())    # 9.0
print("f'(x) = 2x !=", df.item()) # 1.0
```

> The function `f` indirectly modifies the array `x` through a memory view. However, this modification
> is not reflected in the gradient, as seen in the last line outputting `1.0`, representing the
> gradient of the sum operation alone. The squaring of `x` occurs externally to MLX, meaning that no
> gradient is incorporated. It's important to note that a similar issue arises during array conversion
> and copying. For instance, a function defined as `mx.array(np.array(x)**2).sum()` would also result
> in an incorrect gradient, even though no in-place operations on MLX memory are executed.

### PyTorch (verbatim — this section is NEW/detailed and full of gotchas)

> PyTorch supports DLPack inputs and can import MLX arrays directly. MLX can also import PyTorch
> tensors through DLPack with `mx.asarray` or `mx.from_dlpack`. Use `torch.as_tensor` to import an MLX
> array with DLPack; `torch.tensor` copies the data instead. Similarly, `mx.asarray` can share DLPack
> inputs when possible, while `mx.array` copies:

```python
import mlx.core as mx
import torch

a = mx.arange(3, dtype=mx.float32)
mx.eval(a)

shared = torch.as_tensor(a)
copied = torch.tensor(a)
```

> Creating an MLX array from a CPU tensor copies the data into MLX-owned storage. The arrays do not
> share memory:

```python
b = torch.arange(3)
c = mx.array(b)

b += 10
print(c.tolist())  # [0, 1, 2]
```

> **Metal DLPack inputs are different.** If a PyTorch MPS tensor is passed to `mx.asarray` or to
> `mx.from_dlpack` with `copy=None`, MLX imports it without a copy when the underlying Metal buffer is
> not private. **Private Metal buffers are copied into MLX-managed storage instead.** Passing
> `copy=False` requires zero-copy import and **raises an error if a copy would be needed**. Passing
> `copy=True` asks MLX to create a new array instead of reusing the Metal buffer. Zero-copy imports
> preserve the DLPack strides. `mx.array` also creates a new array instead of reusing the Metal
> buffer. MLX arrays exported to PyTorch with DLPack are exported without a copy on Metal.
>
> In particular, **PyTorch 2.12 and later use shared storage for ordinary MPS tensors on Apple silicon,
> while older PyTorch versions may use private storage and require a copy on import.** DLPack
> conversion **does not synchronize pending Metal work**; synchronize or evaluate the producing
> framework before reading the converted array.

```python
b = torch.arange(3, device="mps", dtype=torch.float32)
torch.mps.synchronize()
c = mx.asarray(b)                # zero-copy if the Metal buffer can be reused
d = mx.from_dlpack(b, copy=True) # explicit copy


a = mx.arange(3, dtype=mx.float32)
mx.eval(a)
b = torch.as_tensor(a)           # zero-copy DLPack import on Metal
```

### JAX

> JAX fully supports the buffer protocol.

```python
import mlx.core as mx
import jax.numpy as jnp

a = mx.arange(3)
b = jnp.array(a)
c = mx.array(b)
```

### TensorFlow

> TensorFlow supports the buffer protocol, but it requires an explicit `memoryview`.

```python
import mlx.core as mx
import tensorflow as tf

a = mx.arange(3)
b = tf.constant(memoryview(a))
c = mx.array(b)
```

`from_dlpack` signature (from ops index): `from_dlpack(x, /, *[, copy])`.

---

## 11. Exporting Functions (`usage/export.html`) — verbatim, FULL

> MLX has an API to export and import functions to and from a file. This lets you run computations
> written in one MLX front-end (e.g. Python) in another MLX front-end (e.g. C++).

### 11.1 Basics

```python
def fun(x, y):
    return x + y

x = mx.array(1.0)
y = mx.array(1.0)
mx.export_function("add.mlxfn", fun, x, y)
```

> To export a function, provide sample input arrays that the function can be called with. **The data
> doesn't matter, but the shapes and types of the arrays do.**

```python
add_fun = mx.import_function("add.mlxfn")

out, = add_fun(mx.array(1.0), mx.array(2.0))
# Prints: array(3, dtype=float32)
print(out)

out, = add_fun(mx.array(1.0), mx.array(3.0))
# Prints: array(4, dtype=float32)
print(out)

# Raises an exception
add_fun(mx.array(1), mx.array(3.0))

# Raises an exception
add_fun(mx.array([1.0, 2.0]), mx.array(3.0))
```

> Notice the third and fourth calls to `add_fun` raise exceptions because the shapes and types of the
> inputs are different than the shapes and types of the example inputs we exported the function with.
>
> Also notice that even though the original `fun` returns a single output array, **the imported
> function always returns a tuple of one or more arrays.**

Positional-vs-tuple form:

```python
def fun(x, y):
    return x + y

x = mx.array(1.0)
y = mx.array(1.0)

# Both arguments to fun are positional
mx.export_function("add.mlxfn", fun, x, y)

# Same as above
mx.export_function("add.mlxfn", fun, (x, y))

imported_fun = mx.import_function("add.mlxfn")

# Ok
out, = imported_fun(x, y)

# Also ok
out, = imported_fun((x, y))
```

Keyword arguments:

> You can pass example inputs to functions as positional or keyword arguments. **If you use keyword
> arguments to export the function, then you have to use the same keyword arguments when calling the
> imported function.**

```python
def fun(x, y):
    return x + y

# One argument to fun is positional, the other is a kwarg
mx.export_function("add.mlxfn", fun, x, y=y)

imported_fun = mx.import_function("add.mlxfn")

# Ok
out, = imported_fun(x, y=y)

# Also ok
out, = imported_fun((x,), {"y": y})

# Raises since the keyword argument is missing
out, = imported_fun(x, y)

# Raises since the keyword argument has the wrong key
out, = imported_fun(x, z=y)
```

### 11.2 Exporting Modules

```python
model = nn.Linear(4, 4)
mx.eval(model.parameters())

def call(x):
    return model(x)

mx.export_function("model.mlxfn", call, mx.zeros(4))
```

> In the above example, the `mlx.nn.Linear` module is exported. **Its parameters are also saved to the
> `model.mlxfn` file.**
>
> **Note**: For enclosed arrays inside an exported function, be extra careful to ensure they are
> evaluated. **The computation graph that gets exported will include the computation that produces
> enclosed inputs.**
>
> If the above example was missing `mx.eval(model.parameters()`, the exported function would include
> the random initialization of the `mlx.nn.Module` parameters.

Export without parameters baked in:

```python
model = nn.Linear(4, 4)
mx.eval(model.parameters())

def call(x, **params):
    # Set the model's parameters to the input parameters
    model.update(tree_unflatten(list(params.items())))
    return model(x)

params = tree_flatten(model.parameters(), destination={})
mx.export_function("model.mlxfn", call, (mx.zeros(4),), params)
```

### 11.3 Exporting with a Callback

```python
def fun(x):
    return x.astype(mx.int32)

def callback(args):
    print(args)

mx.export_function(callback, fun, mx.array([1.0, 2.0]))
```

> The argument to the callback (`args`) is a dictionary which includes a `type` field. The possible
> types are:
> - `"inputs"`: The ordered positional inputs to the exported function
> - `"keyword_inputs"`: The keyword specified inputs to the exported function
> - `"outputs"`: The ordered outputs of the exported function
> - `"constants"`: Any graph constants
> - `"primitives"`: Inner graph nodes representating the operations
>
> Each type has additional fields in the `args` dictionary.

### 11.4 Shapeless Exports

```python
mx.export_function("fun.mlxfn", mx.abs, mx.array([0.0]), shapeless=True)
imported_abs = mx.import_function("fun.mlxfn")

# Ok
out, = imported_abs(mx.array([-1.0]))

# Also ok
out, = imported_abs(mx.array([-1.0, -2.0]))
```

> With `shapeless=False` (which is the default), the second call to `imported_abs` would raise an
> exception with a shape mismatch.
>
> Shapeless exporting works the same as shapeless compilation and should be used carefully.

### 11.5 Exporting Multiple Traces

> In some cases, functions build different computation graphs for different input arguments. A simple
> way to manage this is to export to a new file with each set of inputs. This is a fine option in many
> cases. But it can be suboptimal if the exported functions have a large amount of duplicate constant
> data (for example the parameters of a `mlx.nn.Module`).

```python
def fun(x, y=None):
    constant = mx.array(3.0)
    if y is not None:
        x += y
    return x + constant

with mx.exporter("fun.mlxfn", fun) as exporter:
    exporter(mx.array(1.0))
    exporter(mx.array(1.0), y=mx.array(0.0))

imported_function = mx.import_function("fun.mlxfn")

# Call the function with y=None
out, = imported_function(mx.array(1.0))
print(out)

# Call the function with y specified
out, = imported_function(mx.array(1.0), y=mx.array(1.0))
print(out)
```

> In the above example the function constant data, (i.e. `constant`), is only saved once.

### 11.6 Transformations with Imported Functions

```python
def fun(x):
    return mx.sin(x)

x = mx.array(0.0)
mx.export_function("sine.mlxfn", fun, x)

imported_fun = mx.import_function("sine.mlxfn")

# Take the derivative of the imported function
dfdx = mx.grad(lambda x: imported_fun(x)[0])
# Prints: array(1, dtype=float32)
print(dfdx(x))

# Compile the imported function
mx.compile(imported_fun)
# Prints: array(0, dtype=float32)
print(compiled_fun(x)[0])
```

(The doc's own snippet has a bug: it assigns nothing to `compiled_fun`. Recorded verbatim.)

### 11.7 Importing Functions in C++

```python
def fun(x, y):
    return mx.exp(x + y)

x = mx.array(1.0)
y = mx.array(1.0)
mx.export_function("fun.mlxfn", fun, x, y)
```

```cpp
auto fun = mx::import_function("fun.mlxfn");

auto inputs = {mx::array(1.0), mx::array(1.0)};
auto outputs = fun(inputs);

// Prints: array(2, dtype=float32)
std::cout << outputs[0] << std::endl;
```

> Imported functions can be transformed in C++ just like in Python. Use `std::vector<mx::array>` for
> positional arguments and `std::map<std::string, mx::array>` for keyword arguments when calling
> imported functions in C++.

### 11.8 Export API signatures (verbatim)

```
export_function(file_or_callback: str | Callable, fun: Callable, *args,
                shapeless: bool = False, **kwargs) -> None
```
> **Warning**: This is part of an experimental API which is likely to change in future versions of MLX.
> **Functions exported with older versions of MLX may not be compatible with future versions.**
>
> `file_or_callback` (*str or Callable*) – Either a file path to export the function to or a callback.
> `fun` (*Callable*) – A function which takes as input zero or more `array` and returns one or more
> `array`.
> `*args` (*array*) – Example array inputs to the function.
> `shapeless` (*bool, optional*) – Whether or not the function allows inputs with variable shapes.
> Default: `False`.

```
import_function(file: str) -> Callable
```
> The imported function can be called either with `*args` and `**kwargs` or with a tuple of arrays
> and/or dictionary of string keys with array values. **Imported functions always return a tuple of
> arrays.**

```python
>>> fn = mx.import_function("function.mlxfn")
>>> out = fn(a, b, x=x, y=y)[0]
>>>
>>> out = fn((a, b), {"x": x, "y": y}[0]
```

```
exporter(file: str, fun: Callable, *, shapeless: bool = False) -> mlx.core.FunctionExporter
```

```python
def fun(*args):
    return sum(args)

with mx.exporter("fun.mlxfn", fun) as exporter:
    exporter(mx.array(1))
    exporter(mx.array(1), mx.array(2))
    exporter(mx.array(1), mx.array(2), mx.array(3))
```

```
export_to_dot(file: object, *args, **kwargs) -> None
```
> Export a graph to DOT format for visualization.
> A variable number of output arrays can be provided for exporting. The graph exported will
> recursively include all unevaluated inputs of the provided outputs.
> `**kwargs` (*dict[str, array]*) – Provide some names for arrays in the graph to make the result
> easier to parse.

```python
>>> a = mx.array(1) + mx.array(2)
>>> mx.export_to_dot("graph.dot", a)
>>> x = mx.array(1)
>>> y = mx.array(2)
>>> mx.export_to_dot("graph.dot", x + y, x=x, y=y)
```

**File extension convention: `.mlxfn`.**

---

## 12. Distributed Communication (`usage/distributed.html`) — verbatim, FULL

### 12.1 Backends table (exact)

| Backend | Description |
|---|---|
| MPI | A full featured and mature distributed communications library. |
| RING | Ring all reduce and all gather over TCP sockets. Always available and usually faster than MPI. |
| JACCL | Low latency communication with RDMA over thunderbolt. Necessary for things like tensor parallelism. |
| NCCL | The backend of choice for CUDA environments. |

### 12.2 Getting Started

```python
import mlx.core as mx

world = mx.distributed.init()
x = mx.distributed.all_sum(mx.ones(10))
print(world.rank(), x)
```

> However, when this script is run with `python` only one process is launched and no distributed
> communication takes place. Namely, **all operations in `mx.distributed` are noops when the
> distributed group has a size of one.** This property allows us to avoid code that checks if we are
> in a distributed setting similar to the one below:

```python
import mlx.core as mx

x = ...
world = mx.distributed.init()
# No need for the check we can simply do x = mx.distributed.all_sum(x)
if world.size() > 1:
    x = mx.distributed.all_sum(x)
```

### 12.3 Running distributed programs

```
$ mlx.launch -n 4 my_script.py
3 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
2 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
1 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
0 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
```

```
$ mlx.launch --hosts ip1,ip2,ip3,ip4 my_script.py
3 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
2 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
1 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
0 array([4, 4, 4, ..., 4, 4, 4], dtype=float32)
```

### 12.4 Selecting Backend (verbatim — subtle sticky-backend semantics)

> You can select the backend you want to use when calling `init()` by passing one of
> `{'any', 'ring', 'jaccl', 'mpi', 'nccl'}`. When passing `any`, MLX will try all available backends.
> If they all fail then a singleton group is created.
>
> **Note**: After a distributed backend is successfully initialized `init()` will return **the same
> backend** if called without arguments or with backend set to `any`.

```python
# Case 1: Initialize MPI regardless if it was possible to initialize the ring backend
world = mx.distributed.init(backend="mpi")
world2 = mx.distributed.init()  # subsequent calls return the MPI backend!

# Case 2: Initialize any backend
world = mx.distributed.init(backend="any")  # equivalent to no arguments
world2 = mx.distributed.init()  # same as above

# Case 3: Initialize both backends at the same time
world_mpi = mx.distributed.init(backend="mpi")
world_ring = mx.distributed.init(backend="ring")
world_any = mx.distributed.init()  # same as MPI because it was initialized first!
```

### 12.5 Ring backend

> The ring backend does not depend on any third party library so it is **always available**. It uses
> TCP sockets so the nodes need to be reachable via a network. As the name suggests the nodes are
> connected in a ring which means that rank 1 can only communicate with rank 0 and rank 2, rank 2 only
> with rank 1 and rank 3 and so on and so forth. As a result **`send()` and `recv()` with arbitrary
> sender and receiver are not supported in the ring backend.**

Hostfile schema (4-node ring):

```json
[
    {"ssh": "hostname1", "ips": ["123.123.123.1"]},
    {"ssh": "hostname2", "ips": ["123.123.123.2"]},
    {"ssh": "hostname3", "ips": ["123.123.123.3"]},
    {"ssh": "hostname4", "ips": ["123.123.123.4"]}
]
```

> Running `mlx.launch --hostfile ring-4.json my_script.py` will ssh into each node, run the script
> which will listen for connections in each of the provided IPs. Specifically, `hostname1` will connect
> to `123.123.123.2` and accept a connection from `123.123.123.4` and so on and so forth.

**Thunderbolt Ring:**

```bash
mlx.distributed_config --verbose --hosts host1,host2,host3,host4 --backend ring
```

> By default the script will attempt to discover the thunderbolt ring and provide you with the commands
> to configure each node as well as the `hostfile.json` to use with `mlx.launch`. If password-less
> `sudo` is available on the nodes then `--auto-setup` can be used to configure them automatically.

Manual steps (verbatim):

> - Disable the thunderbolt bridge interface
> - For the cable connecting rank `i` to rank `i + 1` find the interfaces corresponding to that cable
>   in nodes `i` and `i + 1`.
> - Set up a unique subnetwork connecting the two nodes for the corresponding interfaces. For instance
>   if the cable corresponds to `en2` on node `i` and `en2` also on node `i + 1` then we may assign IPs
>   `192.168.0.1` and `192.168.0.2` respectively to the two nodes.

### 12.6 JACCL backend — NEW, macOS 26.2+ (verbatim; this is the most 2026-specific content on the site)

> Starting from **macOS 26.2**, RDMA over thunderbolt is available and enables low-latency
> communication between Macs with **thunderbolt 5**. MLX provides the JACCL backend that uses this
> functionality to achieve communication latency **an order of magnitude lower than the ring backend.**
>
> **Note**: The name JACCL (pronounced Jackal) stands for *Jack and Angelos' Collective Communication
> Library* and it is an obvious pun to Nvidia's NCCL but also tribute to *Jack Beasley* who led the
> development of RDMA over Thunderbolt at Apple.

**Enabling RDMA (verbatim):**

> Until the feature matures, enabling RDMA over thunderbolt is slightly more involved and **cannot be
> done remotely even with sudo**. In fact, it has to be done in **macOS recovery**:
>
> - Start your computer in recovery.
> - Open the Terminal by going to Utilities -> Terminal.
> - Run `rdma_ctl enable`.
> - Reboot.

Verification:

```
~ % ibv_devices
    device                 node GUID
    ------              ----------------
    rdma_en2            8096a9d9edbaac05
    rdma_en3            8196a9d9edbaac05
    rdma_en5            8396a9d9edbaac05
    rdma_en4            8296a9d9edbaac05
    rdma_en6            8496a9d9edbaac05
    rdma_en7            8596a9d9edbaac05
```

(the doc says this output is "for an M3 Ultra")

**Mesh requirement (verbatim):**

> The JACCL backend supports **only fully connected topologies**. Namely, there needs to be a
> thunderbolt cable connecting **all pairs** of Macs directly.

Hostfile schema for JACCL (verbatim):

> The hostfile needs to contain
> - Hostnames to use for launching scripts via ssh
> - An IP for rank 0 that is reachable by all nodes
> - A list of rdma devices that connect each node to each other node

```json
[
    {
        "ssh": "m3-ultra-1",
        "ips": ["123.123.123.1"],
        "rdma": [null, "rdma_en5", "rdma_en4", "rdma_en3"]
    },
    {
        "ssh": "m3-ultra-2",
        "ips": [],
        "rdma": ["rdma_en5", null, "rdma_en3", "rdma_en4"]
    },
    {
        "ssh": "m3-ultra-3",
        "ips": [],
        "rdma": ["rdma_en4", "rdma_en3", null, "rdma_en5"]
    },
    {
        "ssh": "m3-ultra-4",
        "ips": [],
        "rdma": ["rdma_en3", "rdma_en4", "rdma_en5", null]
    }
]
```

> **Even though TCP/IP is not used when communicating with Thunderbolt RDMA, disabling the thunderbolt
> bridge is still required as well as setting up isolated local networks for each thunderbolt
> connection.**

Visualize / auto-configure:

```bash
mlx.distributed_config --verbose \
    --hosts m3-ultra-1,m3-ultra-2,m3-ultra-3,m3-ultra-4 \
    --over thunderbolt --dot | dot -Tpng | open -f -a Preview
```

```bash
mlx.distributed_config --verbose \
    --hosts m3-ultra-1,m3-ultra-2,m3-ultra-3,m3-ultra-4 \
    --over thunderbolt --backend jaccl \
    --auto-setup --output m3-ultra-jaccl.json
```

Launch (verbatim, including the inline comment):

```bash
mlx.launch --verbose --backend jaccl --hostfile m3-ultra-jaccl.json \
    --env MLX_METAL_FAST_SYNCH=1 -- \  # <--- important
    /path/to/remote/python -m mlx_lm chat --model mlx-community/DeepSeek-R1-0528-4bit
```

> **Note**: Defining the environment variable **`MLX_METAL_FAST_SYNCH=1`** enables a different, faster
> way of synchronizing between the GPU and the CPU. It is not specific to the JACCL backend and can be
> used in all cases where the CPU and GPU need to collaborate for some computation and is pretty
> critical for low-latency communication since the communication is done by the CPU.

### 12.7 NCCL backend

> MLX on CUDA environments ships with the ability to talk to NCCL which is a high-performance
> collective communication library that supports both multi-gpu and multi-node setups.
>
> **For CUDA environments, NCCL is the default backend for `mlx.launch`**

```bash
mlx.launch -n 8 test.py

# perfect for interactive scripts
mlx.launch -n 8 python -m mlx_lm chat --model my-model
```

```bash
mlx.launch --hosts my-cuda-node -n 8 test.py
```

### 12.8 MPI backend

> MLX already comes with the ability to "talk" to MPI if it is installed on the machine. Launching
> distributed MLX programs that use MPI can be done with `mpirun` as expected. However, in the
> following examples we will be using `mlx.launch --backend mpi` which takes care of some nuisances
> such as setting absolute paths for the `mpirun` executable and the `libmpi.dyld` shared library.

```
$ mlx.launch --backend mpi -n 2 test.py
1 array([2, 2, 2, ..., 2, 2, 2], dtype=float32)
0 array([2, 2, 2, ..., 2, 2, 2], dtype=float32)
```

Installing MPI:

```
$ conda install conda-forge::openmpi
```

> Installing with Homebrew or pip requires specifying the location of `libmpi.dyld` so that MLX can
> find it and load it at runtime. This can simply be achieved by passing the `DYLD_LIBRARY_PATH`
> environment variable to `mpirun` and it is done automatically by `mlx.launch`. **Some environments
> use a non-standard library filename that can be specified using the `MPI_LIBNAME` environment
> variable.** This is automatically taken care of by `mlx.launch` as well.

```
$ mpirun -np 2 -x DYLD_LIBRARY_PATH=/opt/homebrew/lib/ -x MPI_LIBNAME=libmpi.40.dylib python test.py
$ # or simply
$ mlx.launch -n 2 test.py
```

Remote hosts checklist (verbatim):

> - `ssh hostname` works from all machines to all machines without asking for password or host
>   confirmation
> - `mpirun` is accessible on all machines.
> - Ensure that the `hostname` used by MPI is the one that you have configured in the `.ssh/config`
>   files on all machines.

Tuning MPI all-reduce:

> **Note**: For faster all reduce consider using the ring backend either with Thunderbolt connections
> or over Ethernet.
>
> Configure MPI to use N tcp connections between each host to improve bandwidth by passing
> `--mca btl_tcp_links N`.
>
> Force MPI to use the most performant network interface by setting
> `--mca btl_tcp_if_include <iface>` where `<iface>` should be the interface you want to use.

### 12.9 Distributed without `mlx.launch` — environment variables (verbatim, per backend)

**Ring:**
> `MLX_RANK` should contain a single 0-based integer that defines the rank of the process.
> `MLX_HOSTFILE` should contain the path to a json file that contains IPs and ports for each rank to
> listen to, something like the following:

```json
[
    ["123.123.1.1:5000", "123.123.1.2:5000"],
    ["123.123.2.1:5000", "123.123.2.2:5000"],
    ["123.123.3.1:5000", "123.123.3.2:5000"],
    ["123.123.4.1:5000", "123.123.4.2:5000"]
]
```

> `MLX_RING_VERBOSE` is optional and if set to `1` it enables some more logging from the distributed
> backend.

**JACCL:**
> `MLX_RANK` should contain a single 0-based integer that defines the rank of the process.
> `MLX_JACCL_COORDINATOR` should contain the IP and port that rank 0 can listen to all the other ranks
> connect to in order to establish the RDMA connections.
> `MLX_IBV_DEVICES` should contain the path to a json file that contains the ibverbs device names that
> connect each node to each other node, something like the following:

```json
[
    [null, "rdma_en5", "rdma_en4", "rdma_en3"],
    ["rdma_en5", null, "rdma_en3", "rdma_en4"],
    ["rdma_en4", "rdma_en3", null, "rdma_en5"],
    ["rdma_en3", "rdma_en4", "rdma_en5", null]
]
```

**NCCL:**
> `MLX_RANK` should contain a single 0-based integer that defines the rank of the process.
> `MLX_WORLD_SIZE` should contain the total number of processes that will be launched.
> `NCCL_HOST_IP` and `NCCL_PORT` should contain the IP and port that all hosts can connect to to
> establish the NCCL communication.
> `CUDA_VISIBLE_DEVICES` should contain the local index of the gpu that corresponds to this process.
>
> Of course any other environment variable that is used by NCCL can be set.

### 12.10 Tips and Tricks (verbatim)

> - *Test locally first.* You can use the pattern `mlx.launch -n2 -- my_script.py` to run a small scale
>   test on a single node first.
> - *Batch your communication.* As described in the training example, performing a lot of small
>   communications can hurt performance. Copy the approach of `mlx.nn.average_gradients()` to gather
>   many small communications in a single large one.
> - *Visualize the connectivity.* Use `mlx.distributed_config --hosts h1,h2,h3 --over thunderbolt --dot`
>   to visualize the connnections and make sure that the cables are connected correctly.
> - *Use the debugger.* `mlx.launch` is meant for interactive use. **It broadcasts stdin to all
>   processes and gathers stdout from all processes. This makes using `pdb` a breeze.**

---

## 13. Launching Distributed Programs (`usage/launching_distributed.html`) — the `mlx.launch` / `mlx.distributed_config` CLI reference

> The MLX python package provides two utilities to help you configure your Macs for distributed
> computation and also launch distributed programs on multiple nodes or with many processes in a single
> node. These utilities are aptly named
> - `mlx.launch`
> - `mlx.distributed_config`

### 13.1 `mlx.distributed_config`

What the script does for JACCL (verbatim step list):

> - ssh to all nodes to verify that they are reachable
> - Extract the thunderbolt connectivity. Namely run commands on each node to calculate which node is
>   connected to which other node.
> - Verify that we have a valid fully connected mesh
> - Check that RDMA is enabled
> - Extract the ethernet IP from interface **`en0`**
> - Disable the thunderbolt bridge and set up peer to peer networks for each thunderbolt cable
> - Write the hostfile

> The `--auto-setup` argument requires password-less sudo on each node. If it isn't available then the
> configuration script will print commands to be run on each node.

Ring over thunderbolt:
> Setting up a ring backend over thunderbolt only requires changing the `--backend` from `jaccl` to
> `ring`. The steps are very similar with the main difference being that **instead of verifying that
> the nodes are fully connected, the script attempts to identify a ring topology (or multiple rings).**

Ring over Ethernet:
> Configuring the ring backend over ethernet doesn't require setting up network interface and as such
> it simply extracts the `en0` IP from each node and writes the hostfile.

`mlx.distributed_config` flags seen in the docs:
- `--verbose`
- `--hosts h1,h2,h3,h4`
- `--backend {jaccl,ring}`
- `--over {thunderbolt,ethernet}`
- `--auto-setup`
- `--output <hostfile.json>`
- `--dot` (emits GraphViz)

### 13.2 `mlx.launch`

```bash
mlx.launch --hosts ip1,ip2 my_script.py
```

```bash
mlx.launch -n 2 my_script.py
```

> The `mlx.launch` command connects to the provided host and launches the input script on each host. It
> **monitors each of the launched processes and terminates the rest if one of them fails unexpectedly
> or if `mlx.launch` is terminated.** It also takes care of forwarding the output of each remote
> process to stdout and stderr respectively.
>
> Importantly, it also **broadcasts stdin to each process** which enables interactive programs to work
> in distributed mode as well as debugging using the interactive debugger.

Hostfile schema:

```json
[
    {"ssh": "hostname1", "ips": ["123.123.1.1", "123.123.2.1"]},
    {"ssh": "hostname2", "ips": ["123.123.1.2", "123.123.2.2"]}
]
```

> You can use `mlx.distributed_config --over ethernet` to create a hostfile with IPs corresponding to
> the `en0` interface.

Remote host checklist (verbatim):

> - `ssh hostname` works without asking for password or host confirmation
> - the python binary is available on all hosts at the same path. **You can use
>   `mlx.launch --print-python` to see what that path is.**
> - the script you want to run is available on all hosts at the same path
>
> If you are launching from a node with a completely different setup than the nodes that the program
> will run on, you can specify **`--no-verify-script`** so that `mlx.launch` does not attempt to verify
> that the executable and script exist locally before launching the distributed job.

**Ring Specifics (verbatim):**

> The ring backend, which is also **the default backend**, can be explicitly selected with the argument
> `--backend ring`. The ring backend has some specific requirements and arguments that are different to
> other backends:
> - The argument `--hosts` **only accepts IPs and not hostnames**. If we need to ssh to a hostname that
>   does not correspond to the IP we want to bind to we have to provide a hostfile.
> - **`--starting-port`** defines the port to bind to on the remote hosts. Specifically rank 0 for the
>   first IP will use this port and each subsequent IP or rank will add 1 to this port.
> - **`--connections-per-ip`** allows us to increase the number of connections between neighboring
>   nodes. This corresponds to `--mca btl_tcp_links 2` for `mpirun`.

**JACCL Specifics:**
> The JACCL backend can be selected with the argument `--backend jaccl`. **A hostfile is necessary** to
> launch with this backend because it needs to contain the RDMA devices connecting each node to each
> other node.

**NCCL Specifics:**
> The NCCL backend is the default backend for CUDA environments. When launching from a Mac to a Linux
> machine with CUDA then the backend should be selected using `--backend nccl`.
>
> The **`--repeat-hosts, -n`** argument should be used to launch multi-node and multi-gpu jobs.

```bash
mlx.launch --backend nccl --hosts linux-1,linux-2 -n 8 --no-verify-script -- ./my-job.sh
```

> will attempt to launch **16 processes, 8 on each node** that will all run `my-job.sh`.

**MPI Specifics:**
> One can use MPI by passing `--backend mpi` to `mlx.launch`. In that case, `mlx.launch` is a thin
> wrapper over `mpirun`. Moreover,
> - The IPs in the hostfile are ignored
> - The ssh connectivity requirement is stronger as every node needs to be able to connect to every
>   other node
> - `mpirun` needs to be available on every node at the same path
>
> Finally, one can pass arguments to `mpirun` using **`--mpi-arg`**.

```bash
mlx.launch --backend mpi --mpi-arg '--mca btl_tcp_if_include en0' --hostfile hosts.json my_script.py
```

### 13.3 Complete `mlx.launch` flag list gathered from the docs

| Flag | Meaning |
|---|---|
| `-n`, `--repeat-hosts N` | number of processes per host (localhost if no `--hosts`) |
| `--hosts h1,h2,...` | comma-separated hosts/IPs |
| `--hostfile <file.json>` | JSON hostfile (required for JACCL) |
| `--backend {ring,jaccl,mpi,nccl}` | ring is default (nccl default on CUDA) |
| `--starting-port P` | ring only; base TCP port |
| `--connections-per-ip N` | ring only; parallel TCP links |
| `--mpi-arg '<args>'` | mpi only; forwarded to `mpirun` |
| `--env VAR=VAL` | set env var in remote processes |
| `--print-python` | print the python path it would use |
| `--no-verify-script` | skip local existence check of script/executable |
| `--verbose` | verbose logging |
| `--` | separator before the command to run |

### 13.4 `mx.distributed` API signatures (verbatim from autosummary)

```
init(strict: bool = False, backend: str = 'any') -> Group
```
> `strict` – If set to False it returns a singleton group in case `mx.distributed.is_available()`
> returns False otherwise it throws a runtime error. Default: `False`
> `backend` – Which distributed backend to initialize. Possible values `mpi`, `ring`, `nccl`, `jaccl`,
> `any`. If set to `any` all available backends are tried and the first one that succeeds becomes the
> global group which will be returned in subsequent calls. Default: `any`

```python
import mlx.core as mx

group = mx.distributed.init(backend="ring")
```

```
is_available(backend: str = 'any') -> bool
```
> **Note**, this function returns whether MLX has the *capability* of instantiating that distributed
> backend **not** whether it is possible to create a communication group. For that purpose one should
> use `init(strict=True)`.

```
class Group
  rank(self)              # Get the rank of this process
  size(self)              # Get the size of the group
  split(self, color[, key])  # Split the group to subgroups based on the provided color.
```

```
all_sum(x: array, *, group: Group | None = None, stream: None | Stream | Device = None) -> array
all_max(x: array, *, group=None, stream=None) -> array
all_min(x: array, *, group=None, stream=None) -> array
all_gather(x: array, *, group=None, stream=None) -> array
send(x: array, dst: int, *, group=None, stream=None) -> array
recv(shape: Sequence[int], dtype: Dtype, src: int, *, group=None, stream=None) -> array
recv_like(x, src, *, group=None, stream=None) -> array
sum_scatter(x: array, *, group=None, stream=None) -> array
```

- `all_gather`: "Gather the `x` arrays from all processes in the group and **concatenate them along the
  first axis**. The arrays should all have the same shape."
- `send`: "Returns an array identical to `x` which **when evaluated the send is performed**."
- `sum_scatter` (verbatim): "Sum `x` across all processes in the group and shard the result along the
  first axis across ranks. `x.shape[0]` must be divisible by the group size. The result is equivalent
  to `all_sum(x)[rank*chunk_size:(rank+1)*chunk_size]`, where `chunk_size = x.shape[0] // group.size()`
  and `rank` is the rank of this process in the group. Note: `all_sum` is mentioned only for
  illustration; the actual implementation does not perform `all_sum` and uses a single reduce-scatter
  collective instead. **Currently supported only for the NCCL backend.**" Output shape:
  `[x.shape[0] // group.size(), *x.shape[1:]]`.

---

## 14. Custom Metal Kernels (`dev/custom_metal_kernels.html`) — verbatim, FULL

> MLX supports writing custom Metal kernels through the Python and C++ APIs.

### 14.1 Simple example

```python
source = """
    uint elem = thread_position_in_grid.x;
    T tmp = inp[elem];
    out[elem] = metal::exp(tmp);
"""

kernel = mx.fast.metal_kernel(
    name="myexp",
    input_names=["inp"],
    output_names=["out"],
    source=source,
)

def exp_elementwise(a: mx.array):
    outputs = kernel(
        inputs=[a],
        template=[("T", mx.float32)],
        grid=(a.size, 1, 1),
        threadgroup=(256, 1, 1),
        output_shapes=[a.shape],
        output_dtypes=[a.dtype],
    )
    return outputs[0]

a = mx.random.normal(shape=(4, 16)).astype(mx.float16)
b = exp_elementwise(a)
assert mx.allclose(b, mx.exp(a))
```

> **Every time you make a kernel, a new Metal library is created and possibly JIT compiled. To reduce
> the overhead from that, build the kernel once with `fast.metal_kernel()` and then use it many times.**
>
> **Note**: Only pass the **body** of the Metal kernel in `source`. The function signature is generated
> automatically.

### 14.2 How the signature is generated (verbatim, 4 sources)

> The full function signature will be generated using:
>
> - **The shapes/dtypes of `inputs`** — In the above, `a` is an `mx.array` of type `mx.float16` and we
>   pass it with the key `inp` so we will add `const device float16_t* inp` to the signature.
>   **`inp_shape`, `inp_strides` and `inp_ndim` are also added for convenience if they are present in
>   `source`.**
> - **The list of `output_dtypes`** — In the above, `out` is an `mx.array` of type `mx.float16` so we
>   add `device float16_t* out`.
> - **Template parameters passed using `template`** — In the above, `template=[("T", mx.float32)]` adds
>   a template of `template <typename T>` to the function and instantiates the template with
>   `custom_kernel_myexp_float_float16_t_float16_t<float>`. **Template parameters can be
>   `mx.core.Dtype`, `int` or `bool`.**
> - **Metal attributes used in `source` such as `[[thread_position_in_grid]]`** — These will be added
>   as function arguments. **All the attributes defined in Table 5.8 of the Metal Shading Language
>   Specification are supported.**

Generated signature (verbatim):

```cpp
template <typename T>
[[kernel]] void custom_kernel_myexp_float_float16_t_float16_t(
        const device float16_t* inp [[buffer(0)]],
        device float16_t* out [[buffer(1)]],
        uint3 thread_position_in_grid [[thread_position_in_grid]]) {

        uint elem = thread_position_in_grid.x;
        T tmp = inp[elem];
        out[elem] = metal::exp(tmp);

}

template [[host_name("custom_kernel_myexp_float_float16_t_float16_t")]] [[kernel]] decltype(custom_kernel_myexp_float_float16_t_float16_t<float>) custom_kernel_myexp_float_float16_t_float16_t<float>;
```

> **Note**: `grid` and `threadgroup` are parameters to the Metal **`dispatchThreads`** function. This
> means we will launch **`mx.prod(grid)` threads**, subdivided into `threadgroup` size threadgroups.
> For optimal performance, each thread group dimension should be less than or equal to the
> corresponding grid dimension.
>
> Passing **`verbose=True`** to `ast.metal_kernel.__call__()` will print the generated code for
> debugging purposes.

(Note: "`ast.metal_kernel`" is a typo in the docs for `mx.fast.metal_kernel`.)

### 14.3 Math Mode (verbatim — NEW section, easy to get wrong)

> By default `fast.metal_kernel()` compiles kernels with `compile_options={"math_mode": "safe"}` so
> special values follow IEEE behavior, for example `exp(-inf) == 0`. **This is important for kernels
> such as masked softmax where causal or sliding-window masks depend on exponentiating `-inf`.**
>
> If your kernel does not rely on these edge cases, you can opt in to less strict math with
> `compile_options={"math_mode": "relaxed"}` or `compile_options={"math_mode": "fast"}`:

```python
kernel = mx.fast.metal_kernel(
    name="my_kernel",
    input_names=["x"],
    output_names=["y"],
    source=source,
    compile_options={"math_mode": "relaxed"},
)
```

### 14.4 Using Shape/Strides (verbatim)

> `fast.metal_kernel()` supports an argument `ensure_row_contiguous` which is **`True` by default**.
> This will **copy the array inputs if needed** before the kernel is launched to ensure that the memory
> layout is row contiguous. Generally this makes writing the kernel easier, since we don't have to
> worry about gaps or the ordering of the dims when indexing.
>
> If we want to avoid this copy, `fast.metal_kernel()` automatically passes `a_shape`, `a_strides` and
> `a_ndim` for each input array `a` if any are present in `source`. We can then use MLX's built in
> indexing utils to fetch the right elements for each thread.

```python
source = """
    uint elem = thread_position_in_grid.x;
    // Utils from `mlx/backend/metal/kernels/utils.h` are automatically included
    uint loc = elem_to_loc(elem, inp_shape, inp_strides, inp_ndim);
    T tmp = inp[loc];
    // Output arrays are always row contiguous
    out[elem] = metal::exp(tmp);
"""

kernel = mx.fast.metal_kernel(
    name="myexp_strided",
    input_names=["inp"],
    output_names=["out"],
    source=source,
    ensure_row_contiguous=False,
)

def exp_elementwise(a: mx.array):
    outputs = kernel(
        inputs=[a],
        template=[("T", mx.float32)],
        grid=(a.size, 1, 1),
        threadgroup=(256, 1, 1),
        output_shapes=[a.shape],
        output_dtypes=[a.dtype],
    )
    return outputs[0]

a = mx.random.normal(shape=(4, 16)).astype(mx.float16)
# make non-contiguous
a = a[::2]
b = exp_elementwise(a)
assert mx.allclose(b, mx.exp(a))
```

Two facts worth memorizing:
1. `mlx/backend/metal/kernels/utils.h` is **automatically included** — `elem_to_loc` and `ceildiv` are
   available for free.
2. **"Output arrays are always row contiguous"** — so you index outputs with the raw linear `elem`.

### 14.5 Complex example — `grid_sample` bilinear (verbatim)

Reference implementation with standard ops:

```python
def grid_sample_ref(x, grid):
    N, H_in, W_in, _ = x.shape
    ix = ((grid[..., 0] + 1) * W_in - 1) / 2
    iy = ((grid[..., 1] + 1) * H_in - 1) / 2

    ix_nw = mx.floor(ix).astype(mx.int32)
    iy_nw = mx.floor(iy).astype(mx.int32)

    ix_ne = ix_nw + 1
    iy_ne = iy_nw

    ix_sw = ix_nw
    iy_sw = iy_nw + 1

    ix_se = ix_nw + 1
    iy_se = iy_nw + 1

    nw = (ix_se - ix)    * (iy_se - iy)
    ne = (ix    - ix_sw) * (iy_sw - iy)
    sw = (ix_ne - ix)    * (iy    - iy_ne)
    se = (ix    - ix_nw) * (iy    - iy_nw)

    I_nw = x[mx.arange(N)[:, None, None], iy_nw, ix_nw, :]
    I_ne = x[mx.arange(N)[:, None, None], iy_ne, ix_ne, :]
    I_sw = x[mx.arange(N)[:, None, None], iy_sw, ix_sw, :]
    I_se = x[mx.arange(N)[:, None, None], iy_se, ix_se, :]

    mask_nw = (iy_nw >= 0) & (iy_nw <= H_in - 1) & (ix_nw >= 0) & (ix_nw <= W_in - 1)
    mask_ne = (iy_ne >= 0) & (iy_ne <= H_in - 1) & (ix_ne >= 0) & (ix_ne <= W_in - 1)
    mask_sw = (iy_sw >= 0) & (iy_sw <= H_in - 1) & (ix_sw >= 0) & (ix_sw <= W_in - 1)
    mask_se = (iy_se >= 0) & (iy_se <= H_in - 1) & (ix_se >= 0) & (ix_se <= W_in - 1)

    I_nw *= mask_nw[..., None]
    I_ne *= mask_ne[..., None]
    I_sw *= mask_sw[..., None]
    I_se *= mask_se[..., None]

    output = nw[..., None] * I_nw + ne[..., None] * I_ne + sw[..., None] * I_sw + se[..., None] * I_se

    return output
```

Fused forward kernel (verbatim):

```python
source = """
    uint elem = thread_position_in_grid.x;
    int H = x_shape[1];
    int W = x_shape[2];
    int C = x_shape[3];
    int gH = grid_shape[1];
    int gW = grid_shape[2];

    int w_stride = C;
    int h_stride = W * w_stride;
    int b_stride = H * h_stride;

    uint grid_idx = elem / C * 2;
    float ix = ((grid[grid_idx] + 1) * W - 1) / 2;
    float iy = ((grid[grid_idx + 1] + 1) * H - 1) / 2;

    int ix_nw = floor(ix);
    int iy_nw = floor(iy);

    int ix_ne = ix_nw + 1;
    int iy_ne = iy_nw;

    int ix_sw = ix_nw;
    int iy_sw = iy_nw + 1;

    int ix_se = ix_nw + 1;
    int iy_se = iy_nw + 1;

    T nw = (ix_se - ix)    * (iy_se - iy);
    T ne = (ix    - ix_sw) * (iy_sw - iy);
    T sw = (ix_ne - ix)    * (iy    - iy_ne);
    T se = (ix    - ix_nw) * (iy    - iy_nw);

    int batch_idx = elem / C / gH / gW * b_stride;
    int channel_idx = elem % C;
    int base_idx = batch_idx + channel_idx;

    T I_nw = x[base_idx + iy_nw * h_stride + ix_nw * w_stride];
    T I_ne = x[base_idx + iy_ne * h_stride + ix_ne * w_stride];
    T I_sw = x[base_idx + iy_sw * h_stride + ix_sw * w_stride];
    T I_se = x[base_idx + iy_se * h_stride + ix_se * w_stride];

    I_nw = iy_nw >= 0 && iy_nw <= H - 1 && ix_nw >= 0 && ix_nw <= W - 1 ? I_nw : 0;
    I_ne = iy_ne >= 0 && iy_ne <= H - 1 && ix_ne >= 0 && ix_ne <= W - 1 ? I_ne : 0;
    I_sw = iy_sw >= 0 && iy_sw <= H - 1 && ix_sw >= 0 && ix_sw <= W - 1 ? I_sw : 0;
    I_se = iy_se >= 0 && iy_se <= H - 1 && ix_se >= 0 && ix_se <= W - 1 ? I_se : 0;

    out[elem] = nw * I_nw + ne * I_ne + sw * I_sw + se * I_se;
"""

kernel = mx.fast.metal_kernel(
    name="grid_sample",
    input_names=["x", "grid"],
    output_names=["out"],
    source=source,
)

@mx.custom_function
def grid_sample(x, grid):

    assert x.ndim == 4, "`x` must be 4D."
    assert grid.ndim == 4, "`grid` must be 4D."

    B, _, _, C = x.shape
    _, gN, gM, D = grid.shape
    out_shape = (B, gN, gM, C)

    assert D == 2, "Last dim of `grid` must be size 2."

    outputs = kernel(
        inputs=[x, grid],
        template=[("T", x.dtype)],
        output_shapes=[out_shape],
        output_dtypes=[x.dtype],
        grid=(np.prod(out_shape), 1, 1),
        threadgroup=(256, 1, 1),
    )
    return outputs[0]
```

> For a reasonably sized input such as:
> ```
> x.shape = (8, 1024, 1024, 64)
> grid.shape = (8, 256, 256, 2)
> ```
> On an M1 Max, we see a big performance improvement:
> **`55.7ms -> 6.7ms => 8x speed up`**

### 14.6 Grid Sample VJP — `init_value` and `atomic_outputs` (verbatim)

> The backwards pass requires atomically updating `x_grad`/`grid_grad` and so requires a few extra
> `fast.metal_kernel()` features:
>
> - **`init_value=0`** — Initialize all of the kernel's outputs to this value before it runs. This
>   allows us to update only part of the output arrays with the kernel.
> - **`atomic_outputs=True`** — Designate all of the kernel outputs as `atomic` in the function
>   signature. This means we can use Metal's `atomic` features to simultaneously update the `x_grad`
>   and `grid_grad` arrays from multiple threadgroups. **See section 6.15 of the Metal Shading Language
>   Specification for more details.**

Backward kernel (verbatim; note `C_padded`, `simd_sum`, `thread_index_in_simdgroup`,
`threads_per_simdgroup`, `ceildiv`, `atomic_fetch_add_explicit`, `memory_order_relaxed`):

```python
source = """
    uint elem = thread_position_in_grid.x;
    int H = x_shape[1];
    int W = x_shape[2];
    int C = x_shape[3];
    // Pad C to the nearest larger simdgroup size multiple
    int C_padded = ceildiv(C, threads_per_simdgroup) * threads_per_simdgroup;

    int gH = grid_shape[1];
    int gW = grid_shape[2];

    int w_stride = C;
    int h_stride = W * w_stride;
    int b_stride = H * h_stride;

    uint grid_idx = elem / C_padded * 2;
    float ix = ((grid[grid_idx] + 1) * W - 1) / 2;
    float iy = ((grid[grid_idx + 1] + 1) * H - 1) / 2;

    int ix_nw = floor(ix);
    int iy_nw = floor(iy);

    int ix_ne = ix_nw + 1;
    int iy_ne = iy_nw;

    int ix_sw = ix_nw;
    int iy_sw = iy_nw + 1;

    int ix_se = ix_nw + 1;
    int iy_se = iy_nw + 1;

    T nw = (ix_se - ix)    * (iy_se - iy);
    T ne = (ix    - ix_sw) * (iy_sw - iy);
    T sw = (ix_ne - ix)    * (iy    - iy_ne);
    T se = (ix    - ix_nw) * (iy    - iy_nw);

    int batch_idx = elem / C_padded / gH / gW * b_stride;
    int channel_idx = elem % C_padded;
    int base_idx = batch_idx + channel_idx;

    T gix = T(0);
    T giy = T(0);
    if (channel_idx < C) {
        int cot_index = elem / C_padded * C + channel_idx;
        T cot = cotangent[cot_index];
        if (iy_nw >= 0 && iy_nw <= H - 1 && ix_nw >= 0 && ix_nw <= W - 1) {
            int offset = base_idx + iy_nw * h_stride + ix_nw * w_stride;
            atomic_fetch_add_explicit(&x_grad[offset], nw * cot, memory_order_relaxed);

            T I_nw = x[offset];
            gix -= I_nw * (iy_se - iy) * cot;
            giy -= I_nw * (ix_se - ix) * cot;
        }
        if (iy_ne >= 0 && iy_ne <= H - 1 && ix_ne >= 0 && ix_ne <= W - 1) {
            int offset = base_idx + iy_ne * h_stride + ix_ne * w_stride;
            atomic_fetch_add_explicit(&x_grad[offset], ne * cot, memory_order_relaxed);

            T I_ne = x[offset];
            gix += I_ne * (iy_sw - iy) * cot;
            giy -= I_ne * (ix - ix_sw) * cot;
        }
        if (iy_sw >= 0 && iy_sw <= H - 1 && ix_sw >= 0 && ix_sw <= W - 1) {
            int offset = base_idx + iy_sw * h_stride + ix_sw * w_stride;
            atomic_fetch_add_explicit(&x_grad[offset], sw * cot, memory_order_relaxed);

            T I_sw = x[offset];
            gix -= I_sw * (iy - iy_ne) * cot;
            giy += I_sw * (ix_ne - ix) * cot;
        }
        if (iy_se >= 0 && iy_se <= H - 1 && ix_se >= 0 && ix_se <= W - 1) {
            int offset = base_idx + iy_se * h_stride + ix_se * w_stride;
            atomic_fetch_add_explicit(&x_grad[offset], se * cot, memory_order_relaxed);

            T I_se = x[offset];
            gix += I_se * (iy - iy_nw) * cot;
            giy += I_se * (ix - ix_nw) * cot;
        }
    }

    T gix_mult = W / 2;
    T giy_mult = H / 2;

    // Reduce across each simdgroup first.
    // This is much faster than relying purely on atomics.
    gix = simd_sum(gix);
    giy = simd_sum(giy);

    if (thread_index_in_simdgroup == 0) {
        atomic_fetch_add_explicit(&grid_grad[grid_idx], gix * gix_mult, memory_order_relaxed);
        atomic_fetch_add_explicit(&grid_grad[grid_idx + 1], giy * giy_mult, memory_order_relaxed);
    }
"""
kernel = mx.fast.metal_kernel(
    name="grid_sample_grad",
    input_names=["x", "grid", "cotangent"],
    output_names=["x_grad", "grid_grad"],
    source=source,
    atomic_outputs=True,
)

@grid_sample.vjp
def grid_sample_vjp(primals, cotangent, _):
    x, grid = primals
    B, _, _, C = x.shape
    _, gN, gM, D = grid.shape

    assert D == 2, "Last dim of `grid` must be size 2."

    # pad the output channels to simd group size
    # so that our `simd_sum`s don't overlap.
    simdgroup_size = 32
    C_padded = (C + simdgroup_size - 1) // simdgroup_size * simdgroup_size
    grid_size = B * gN * gM * C_padded
    outputs = kernel(
        inputs=[x, grid, cotangent],
        template=[("T", x.dtype)],
        output_shapes=[x.shape, grid.shape],
        output_dtypes=[x.dtype, x.dtype],
        grid=(grid_size, 1, 1),
        threadgroup=(256, 1, 1),
        init_value=0,
    )
    return outputs[0], outputs[1]
```

> There's an even larger speed up for the vjp:
> **`676.4ms -> 16.7ms => 40x speed up`**

### 14.7 `mx.fast.metal_kernel` — exact signature (from autosummary)

```
metal_kernel(name: str,
             input_names: Sequence[str],
             output_names: Sequence[str],
             source: str,
             header: str = '',
             ensure_row_contiguous: bool = True,
             atomic_outputs: bool = False,
             compile_options: object | None = None) -> object
```

> `name` (*str*) – Name for the kernel.
> `input_names` (*List[str]*) – The parameter names of the inputs in the function signature.
> `output_names` (*List[str]*) – The parameter names of the outputs in the function signature.
> `source` (*str*) – Source code. This is the **body** of a function in Metal, the function signature
> will be automatically generated.
> `header` (*str*) – Header source code to include **before** the main function. Useful for helper
> functions or includes that should live outside of the main function body.
> `ensure_row_contiguous` (*bool*) – Whether to ensure the inputs are row contiguous before the kernel
> runs. Default: `True`.
> `atomic_outputs` (*bool*) – Whether to use atomic outputs in the function signature e.g.
> `device atomic<float>`. Default: `False`.
> `compile_options` (*dict, optional*) – Options to compile the Metal kernel with. Supported options:
>   - `"math_mode"`: The Metal math mode: `"safe"`, `"relaxed"`, or `"fast"`. `"safe"` preserves IEEE
>     behavior for special values such as `exp(-inf) == 0`. Default: `"safe"`.
>
> **Returns:** Callable `metal_kernel`.

**The returned callable's kwargs** (documented only by usage, never as a formal signature — collected
from every example on the site):

```
kernel(inputs=[...],                # list[array]
       template=[(name, value), …],  # values may be mx.core.Dtype, int, or bool
       grid=(x, y, z),               # in THREADS (dispatchThreads)
       threadgroup=(x, y, z),
       output_shapes=[shape, …],
       output_dtypes=[dtype, …],
       init_value=<float>,           # optional; pre-fill outputs
       verbose=False)                # print generated Metal source
-> list[array]
```

### 14.8 CUDA equivalents

```
cuda_kernel(name: str, input_names: Sequence[str], output_names: Sequence[str], source: str,
            header: str = '', ensure_row_contiguous: bool = True, shared_memory: int = 0) -> object
```
> A jit-compiled custom CUDA kernel defined from a source string. This is the CUDA equivalent of Custom
> Metal Kernels.
> `shared_memory` (*int*) – The dynamic shared memory to request for the kernel. A value of 0 means no
> dynamic shared memory. Default: `0`.

```python
def exp_elementwise(a: mx.array):
    source = '''
        auto elem = cooperative_groups::this_grid().thread_rank();
        T tmp = inp[elem];
        out[elem] = exp(tmp);
    '''

    kernel = mx.fast.cuda_kernel(
        name="myexp",
        input_names=["inp"],
        output_names=["out"],
        source=source
    )
    outputs = kernel(
        inputs=[a],
        template=[("T", mx.float32)],
        grid=(a.size, 1, 1),
        threadgroup=(256, 1, 1),
        output_shapes=[a.shape],
        output_dtypes=[a.dtype],
        verbose=True,
    )
    return outputs[0]

a = mx.random.normal(shape=(16, 16)).astype(mx.float16)
b = exp_elementwise(a)
assert mx.allclose(b, mx.exp(a))
```

Note the CUDA kernel body uses `cooperative_groups::this_grid().thread_rank()` instead of
`thread_position_in_grid.x`.

```
precompiled_cuda_kernel(*, name: str,
                        compiled_source: bytes,
                        inputs: Sequence[bool | int | float | mlx.core.array | ndarray[writable=False] | complex | mlx.core.ArrayLike],
                        output_shapes: Sequence[tuple[int, ...]],
                        output_dtypes: Sequence[mlx.core.Dtype],
                        scalars: Sequence[object],
                        grid: tuple[int, int, int],
                        threadgroup: tuple[int, int, int],
                        shared_memory: int = 0,
                        init_value: float | None = None,
                        ensure_row_contiguous: bool = False,
                        stream: mlx.core.Stream | mlx.core.ThreadLocalStream | mlx.core.Device | None = None)
                        -> list[array]
```
> Run a precompiled CUDA kernel defined from PTX or cubin.
> **This op is still experimental and various parts of the API may change.**
> `grid` – 3-tuple specifying the grid to launch the kernel with. **For compatibility with
> `metal_kernel()` the grid is in threads and not in threadblocks.**
> `init_value` – Optional value to use to initialize all of the output arrays. **By default, output
> arrays are uninitialized.** Default: `None`.
> `ensure_row_contiguous` – Default here is **`False`** (unlike `metal_kernel`/`cuda_kernel` where it
> is `True`).

---

## 15. Metal Debugger (`dev/metal_debugger.html`) — verbatim, FULL

> Profiling is a key step for performance optimization. You can build MLX with the `MLX_METAL_DEBUG`
> option to improve the Metal debugging and optimization workflow. The `MLX_METAL_DEBUG` debug option:
>
> - Records source during Metal compilation, for later inspection while debugging.
> - Labels Metal objects such as command queues, improving capture readability.
>
> To build with debugging enabled in Python prepend `CMAKE_ARGS="-DMLX_METAL_DEBUG=ON"` to the build
> call.
>
> The `metal.start_capture()` function initiates a capture of all MLX GPU work.
>
> **Note**: To capture a GPU trace you must run the application with **`MTL_CAPTURE_ENABLED=1`**.

```python
import mlx.core as mx

a = mx.random.uniform(shape=(512, 512))
b = mx.random.uniform(shape=(512, 512))
mx.eval(a, b)

trace_file = "mlx_trace.gputrace"

# Make sure to run with MTL_CAPTURE_ENABLED=1 and
# that the path trace_file does not already exist.
mx.metal.start_capture(trace_file)

for _ in range(10):
    mx.eval(mx.add(a, b))

mx.metal.stop_capture()
```

> You can open and replay the GPU trace in Xcode. The `Dependencies` view has a great overview of all
> operations.

### Xcode Workflow

```bash
mkdir build && cd  build
cmake .. -DMLX_METAL_DEBUG=ON -G Xcode
open mlx.xcodeproj
```

> Select the `metal_capture` example schema and run.

### API

```
start_capture(path: str) -> None    # path should have the extension `.gputrace`
stop_capture() -> None
metal.is_available() -> bool        # "Check if the Metal back-end is available."
metal.device_info() -> dict[str, str | int]
```

**Gotchas:** (a) `MTL_CAPTURE_ENABLED=1` must be set in the *environment*, not in code; (b) the trace
path **must not already exist**.

---

## 16. Metal Logging (`dev/metal_logging.html`) — verbatim, FULL (short page)

> In debug builds, MLX compiles Metal kernels with `os_log` enabled so shader warnings and debug
> messages are visible during development.
>
> **Note**: Metal logging is only available with **Metal 3.2 or higher (macOS 15 and up, iOS 18 and
> up).**

```bash
DEBUG=1 python -m pip install -e .
```

```cpp
#include "mlx/backend/metal/kernels/logging.h"

constant mlx::os_log logger("mlx", "my_kernel");

kernel void my_kernel(/* ... */) {
  // ...
  logger.log_debug("unexpected state: idx=%u", idx);
}
```

```bash
MTL_LOG_LEVEL=MTLLogLevelDebug MTL_LOG_TO_STDERR=1 python script.py
```

Env vars to remember: **`DEBUG=1`** (build), **`MTL_LOG_LEVEL=MTLLogLevelDebug`**,
**`MTL_LOG_TO_STDERR=1`** (run).

---

## 17. Python API Reference — `mlx.core`

### 17.1 Transforms (`python/transforms.html`) — complete list with brief signatures

```
eval(*args)
async_eval(*args)
compile(fun[, inputs, outputs, shapeless])
checkpoint(fun)
custom_function(*args, **kwargs)
disable_compile()
enable_compile()
grad(fun[, argnums, argnames])
value_and_grad(fun[, argnums, argnames])
jvp(fun, primals, tangents)
vjp(fun, primals, cotangents)
vmap(fun[, in_axes, out_axes])
```

Full signatures for all of these are in §8 and §9 above.

### 17.2 Devices and Streams (`python/devices_and_streams.html`)

```
Device(*args, **kwargs)                 A device to run operations on.
Stream                                  A stream for running operations on a given device.
default_device()                        Get the default device.
set_default_device(device)              Set the default device.
default_stream(device)                  Get the device's default stream.
new_stream(device)                      Make a new stream on the given device.
new_thread_local_stream(device)         Make a new stream that will be unique per thread.
set_default_stream(stream)              Set the default stream.
stream(s)                               Create a context manager to set the default device and stream.
synchronize([stream])                   Synchronize with the given stream.
clear_streams()                         Destroy all streams created in current thread.
device_count(device_type)               Get the number of available devices for the given device type.
device_info([d])                        Get information about a device.
```

Exact signatures:

```
class Device(*args, **kwargs)
    __init__(self, type: mlx.core.DeviceType, index: int = 0) -> None
    Attributes: type  -> mlx.core.DeviceType
```

```
new_stream(device: Device) -> Stream
```
> Make a new stream on the given device. **The stream can only be used on the thread where it was
> created on, using it in any other thread would result in errors.**

```
new_thread_local_stream(device: Device) -> mlx.core.ThreadLocalStream
```
> Make a new stream that will be unique per thread.

```
stream(s: Stream | mlx.core.ThreadLocalStream | Device) -> mlx.core.StreamContext
```
> Create a context manager to set the default device and stream.

```
synchronize(stream: Stream | mlx.core.ThreadLocalStream | Device | None = None) -> None
```
> Synchronize with the given stream. If device is provided the default stream for that device is used.
> If `None` then the default stream of the default device is used. Default: `None`.

```
clear_streams() -> None
```
> Destroy all streams created in current thread.

```
device_info(d: Device | None = None) -> dict[str, str | int]
```
> Get information about a device. Returns a dictionary with device properties. Available keys depend on
> the backend and device type. **Common keys include `device_name`, `architecture`, and `total_memory`
> (or `memory_size`).**

**NOTE:** there are now three distinct stream-ish types: `Stream`, `ThreadLocalStream`, and `Device`
(implicitly convertible via default stream). `mx.cpu` / `mx.gpu` are `Device` values used throughout
the docs as `stream=` arguments.

### 17.3 Memory Management (`python/memory_management.html`)

```
get_active_memory() -> int
get_peak_memory() -> int
reset_peak_memory()
get_cache_memory() -> int
set_memory_limit(limit: int) -> int
set_cache_limit(limit: int) -> int
set_wired_limit(limit: int) -> int
clear_cache() -> None
```

Verbatim details:

- `get_active_memory()` — "Get the actively used memory in bytes. **Note, this will not always match
  memory use reported by the system because it does not include cached memory buffers.**"
- `get_peak_memory()` — "The maximum memory used recorded from the beginning of the program execution
  or since the last call to `reset_peak_memory()`."
- `get_cache_memory()` — "The cache includes memory not currently used that has not been returned to
  the system allocator."
- `set_memory_limit(limit)` — "The memory limit is a **guideline** for the maximum amount of memory to
  use during graph evaluation. If the memory limit is exceeded and there is no more RAM (including swap
  when available) allocations will result in an exception. **When metal is available the memory limit
  defaults to 1.5 times the maximum recommended working set size reported by the device.**" Returns the
  previous memory limit in bytes.
- `set_cache_limit(limit)` — "If using more than the given limit, free memory will be reclaimed from
  the cache on the next allocation. **To disable the cache, set the limit to `0`.** The cache limit
  defaults to the memory limit." Returns previous cache limit.
- `set_wired_limit(limit)` — verbatim Note:
  > - This function is only useful on **macOS 15.0 or higher**.
  > - The wired limit should remain **strictly less** than the total memory size.
  >
  > The wired limit is the total size in bytes of memory that will be kept resident. **The default
  > value is `0`.**
  >
  > Setting a wired limit larger than system wired limit is an error. You can increase the system wired
  > limit with:
  > ```
  > sudo sysctl iogpu.wired_limit_mb=<size_in_megabytes>
  > ```
  > Use `device_info()` to query the system wired limit (`"max_recommended_working_set_size"`) and the
  > total memory size (`"memory_size"`).
- `clear_cache()` — "Clear the memory cache. After calling this, `get_cache_memory()` should return
  `0`."

### 17.4 Metal / CUDA namespaces

```
mlx.core.metal.is_available()   -> bool     "Check if the Metal back-end is available."
mlx.core.metal.device_info()    -> dict[str, str | int]
mlx.core.metal.start_capture(path: str) -> None
mlx.core.metal.stop_capture()   -> None
mlx.core.cuda.is_available()    -> bool     "Check if the CUDA back-end is available."
```

### 17.5 Random (`python/random.html`) — verbatim preamble + list

> Random sampling functions in MLX use an **implicit global PRNG state by default**. However, all
> function take an optional `key` keyword argument for when more fine-grained control or explicit state
> management is needed.

```python
for _ in range(3):
  print(mx.random.uniform())
```

```python
key = mx.random.key(0)
for _ in range(3):
  print(mx.random.uniform(key=key))
```

> which will yield the **same** pseudo random number at each iteration.
>
> Following **JAX's PRNG design we use a splittable version of Threefry, which is a counter-based
> PRNG.**

```
bernoulli([p, shape, key, stream])          Generate Bernoulli random values.
categorical(logits[, axis, shape, ...])     Sample from a categorical distribution.
gumbel([shape, dtype, key, stream])         Sample from the standard Gumbel distribution.
key(seed)                                   Get a PRNG key from a seed.
normal([shape, dtype, loc, scale, key, stream])
multivariate_normal(mean, cov[, shape, ...])
randint(low, high[, shape, dtype, key, stream])
seed(seed)                                  Seed the global PRNG.
split(key[, num, stream])                   Split a PRNG key into sub keys.
truncated_normal(lower, upper[, shape, ...])
uniform([low, high, shape, dtype, key, stream])
laplace([shape, dtype, loc, scale, key, stream])
permutation(x[, axis, key, stream])         Generate a random permutation or permute the entries.
```

Exact signatures:

```
key(seed: int) -> array
split(key: array, num: int = 2, stream: None | Stream | Device = None) -> array
```
> Returns "The array of sub keys with `num` as its first dimension."

```
normal(shape: Sequence[int] = [],
       dtype: Dtype | None = float32,
       loc: scalar | array | None = None,
       scale: scalar | array | None = None,
       key: array | None = None,
       stream: None | Stream | Device = None) -> array
```
> If `loc` and `scale` are not provided the "standard" normal distribution is used. That means
> x ~ N(0, 1) for real numbers and Re(x), Im(x) ~ N(0, 1/2) **for complex numbers**.

```
categorical(logits: array, axis: int = -1, shape: Sequence[int] | None = None,
            num_samples: int | None = None, key: array | None = None,
            stream: None | Stream | Device = None) -> array
```
> The values are sampled from the categorical distribution specified by the **unnormalized** values in
> `logits`. Note, **at most one of `shape` or `num_samples` can be specified.** If both are `None`, the
> output has the same shape as `logits` with the `axis` dimension removed.
> Returns the `shape`-sized output array with type **`uint32`**.

Also referenced elsewhere in the docs but not on this index page: **`mx.random.state`** — the global
PRNG state object you must add to `mx.compile(inputs=..., outputs=...)` when the graph samples.

### 17.6 FFT (`python/fft.html`)

```
fft(a[, n, axis, norm, stream])          One dimensional discrete Fourier Transform.
ifft(a[, n, axis, norm, stream])
fft2(a[, s, axes, norm, stream])
ifft2(a[, s, axes, norm, stream])
fftn(a[, s, axes, norm, stream])
ifftn(a[, s, axes, norm, stream])
rfft(a[, n, axis, norm, stream])         One dimensional DFT on a real input.
irfft(a[, n, axis, norm, stream])        The inverse of rfft().
rfft2(a[, s, axes, norm, stream])
irfft2(a[, s, axes, norm, stream])
rfftn(a[, s, axes, norm, stream])
irfftn(a[, s, axes, norm, stream])
fftfreq(n[, d, stream])                  Return the DFT sample frequencies.
rfftfreq(n[, d, stream])                 …for use with rfft() and irfft().
fftshift(a[, axes, stream])              Shift the zero-frequency component to the center.
ifftshift(a[, axes, stream])             The inverse of fftshift().
```

Note the presence of a `norm` parameter on all transform functions (NumPy-compatible).

### 17.7 Linear Algebra (`python/linalg.html`)

```
inv(a, *[, stream])                     Compute the inverse of a square matrix.
tri_inv(a[, upper, stream])             Inverse of a triangular square matrix.
norm(a, /[, ord, axis, keepdims, stream])   Matrix or vector norm.
cholesky(a[, upper, stream])            Cholesky decomposition of a real symmetric PSD matrix.
cholesky_inv(L[, upper, stream])        Inverse via its Cholesky decomposition.
cross(a, b[, axis, stream])             Cross product along a specified axis.
det(a, *[, stream])                     Determinant of a square matrix.
qr(a, *[, stream])                      QR factorization.
svd(a[, compute_uv, stream])            Singular Value Decomposition.
eigvals(a, *[, stream])                 Eigenvalues of a square matrix.
eig(a, *[, stream])                     Eigenvalues and eigenvectors of a square matrix.
eigvalsh(a[, UPLO, stream])             Eigenvalues of complex Hermitian / real symmetric.
eigh(a[, UPLO, stream])                 Eigenvalues and eigenvectors of Hermitian/symmetric.
lu(a, *[, stream])                      LU factorization of the given matrix A.
lu_factor(a, *[, stream])               Compact representation of the LU factorization.
pinv(a, *[, stream])                    Moore-Penrose pseudo-inverse.
slogdet(a, *[, stream])                 Sign and natural log of |det|.
solve(a, b, *[, stream])                Solve AX = B.
solve_triangular(a, b, *[, upper, stream])  Triangular AX = B.
```

Note `eig`/`eigvals` (non-symmetric) are present, which is newer than many MLX releases.

### 17.8 Fast (`python/fast.html`)

```
rms_norm(x, weight, eps, *[, stream])
layer_norm(x, weight, bias, eps, *[, stream])
rope(a, dims, *, traditional, base, scale, ...)
scaled_dot_product_attention(q, k, v, *, scale)
metal_kernel(name, input_names, ...[, ...])
cuda_kernel(name, input_names, output_names, ...)
precompiled_cuda_kernel(*, name, ...)
```

Exact signatures:

```
rms_norm(x: array, weight: array | None, eps: float, *, stream=None) -> array
```
> The normalization is with respect to the **last axis** of the input `x`. `weight` should be
> one-dimensional with the same size as the last axis of `x`. **If set to `None` then no scaling
> happens.**

```
layer_norm(x, weight, bias, eps, *, stream=None) -> array
```

```
rope(a: array, dims: int, *, traditional: bool, base: float | None, scale: float,
     offset: int | array, freqs: array | None = None, stream=None) -> array
```
> The input is expected to be at least 3D with shape `(B, *, T, D)`.
> `dims` – The feature dimensions to be rotated. **If the input feature is larger than dims then the
> rest is left unchanged.**
> `traditional` – If set to `True` choose the traditional implementation which rotates **consecutive**
> dimensions.
> `base` – **Exactly one of `base` and `freqs` must be `None`.**
> `offset` – The position offset to start at. **If an `array` is given it can be a scalar or vector of
> `B` offsets for each example in the batch.**
> `freqs` – Optional frequencies to use with RoPE. If set, the `base` parameter must be `None`.

```
scaled_dot_product_attention(q: array, k: array, v: array, *, scale: float,
                             mask: None | str | array = None,
                             sinks: array | None = None,
                             stream=None) -> array
```
> A fast implementation of multi-head attention: `O = softmax(Q @ K.T, dim=-1) @ V`.
> Supports: Multi-Head Attention, Grouped Query Attention, Multi-Query Attention.
>
> **Note:**
> - The **softmax operation is performed in `float32` regardless of the input precision.**
> - For Grouped Query Attention and Multi-Query Attention, **the `k` and `v` inputs should not be
>   pre-tiled to match `q`.**
>
> Dimensions: `B` batch, `N_q` query heads, `N_kv` key/value heads, `T_q` queries per example, `T_kv`
> keys/values per example, `D` per-head dimension.
> `q` shape `[B, N_q, T_q, D]`; `k` shape `[B, N_kv, T_kv, D]`; `v` shape `[B, N_kv, T_kv, D]`.
> `scale` – typically `1.0 / sqrt(q.shape(-1))`.
> `mask` – "The mask can be an array or a string indicating the mask type. **The only supported string
> type is `"causal"`.** If the mask is an array it can be a boolean or additive mask. The mask can have
> at most 4 dimensions and must be broadcast-compatible with the shape `[B, N, T_q, T_kv]`. If an
> additive mask is given its type must promote to the promoted type of `q`, `k`, and `v`. **The
> `"causal"` mask uses lower-right alignment where the last query aligns with the last key.**"
> `sinks` – "An optional array of **attention sinks**. Default: `None`."

```python
B = 2
N_q = N_kv = 32
T_q = T_kv = 1000
D = 128

q = mx.random.normal(shape=(B, N_q, T_q, D))
k = mx.random.normal(shape=(B, N_kv, T_kv, D))
v = mx.random.normal(shape=(B, N_kv, T_kv, D))
scale = D ** -0.5

out = mx.fast.scaled_dot_product_attention(q, k, v, scale=scale, mask="causal")
```

### 17.9 Quantization — `quantize` / `dequantize` / `quantized_matmul` / `qqmm` / fp8

```
quantize(w: array, /, group_size: int | None = None, bits: int | None = None,
         mode: str = 'affine', *, global_scale: array | None = None,
         stream: None | Stream | Device = None) -> tuple[array, array, array]
```

> Note, every `group_size` elements in a row of `w` are quantized together. Hence, the last dimension
> of `w` should be divisible by `group_size`.
>
> **Warning**: `quantize` only supports inputs with **two or more dimensions** with the last dimension
> divisible by `group_size`.
>
> The supported quantization modes are `"affine"`, `"mxfp4"`, `"mxfp8"`, and `"nvfp4"`.

**Quantization modes table (exact; `*` = default when unspecified):**

| mode | group size | bits | scale type | bias |
|---|---|---|---|---|
| affine | 32, 64\*, 128 | 2, 3, 4\*, 5, 6, 8 | same as input | yes |
| mxfp4 | 32\* | 4\* | e8m0 | no |
| mxfp8 | 32\* | 8\* | e8m0 | no |
| nvfp4 | 16\* | 4\* | e4m3 | no |

> The `"affine"` mode quantizes groups of *g* consecutive elements in a row of `w`. For each group the
> quantized representation of each element is computed as:
> α = max_i w_i ; β = min_i w_i ; s = (α − β)/(2^b − 1) ; ŵ_i = round((w_i − β)/s).
>
> After the above computation, ŵ_i fits in *b* bits and is packed in an **unsigned 32-bit integer from
> the lower to upper bits**. For instance, for 4-bit quantization we fit 8 elements in an unsigned 32
> bit integer where the 1st element occupies the 4 least significant bits, the 2nd bits 4-7 etc.
>
> The `"mxfp4"`, `"mxfp8"`, and `"nvfp4"` modes similarly quantize groups of *g* elements of `w`. For
> the `"mx"` modes, the group size must be `32`. For `"nvfp4"` the group size must be `16`. The
> elements are quantized to 4-bit or 8-bit precision floating-point values: **E2M1 for `"fp4"` and
> E4M3 for `"fp8"`. There is a shared 8-bit scale per group. The `"mx"` modes use an E8M0 scale and the
> `"nv"` mode uses an E4M3 scale.** Unlike `affine` quantization, these modes does not have a bias
> value.

Returns: `w_q`, `scales`, and `biases` — **biases only returned for `mode=="affine"`** (so the return
tuple has "either two or three elements").

```
dequantize(w: array, /, scales: array, biases: array | None = None,
           group_size: int | None = None, bits: int | None = None,
           mode: str = 'affine', global_scale: array | None = None,
           dtype: Dtype | None = None, *, stream=None) -> array
```
> `dtype` – The data type of the dequantized output. **If `None` the return type is inferred from the
> scales and biases when possible and otherwise defaults to `bfloat16`.** Default: `None`.
> For `affine`: w_i = s·ŵ_i + β.

```
quantized_matmul(x: array, w: array, /, scales: array, biases: array | None = None,
                 transpose: bool = True, group_size: int | None = None,
                 bits: int | None = None, mode: str = 'affine', *, stream=None) -> array
```
> `transpose` – Defines whether to multiply with the transposed `w` or not, namely whether we are
> performing `x @ w.T` or `x @ w`. Default: `True`.

```
qqmm(x: array, w: array, scales: array | None = None, group_size: int | None = None,
     bits: int | None = None, mode: str = 'nvfp4',
     global_scale_x: array | None = None, global_scale_w: array | None = None,
     *, stream=None) -> array
```
> Perform a matrix multiplication using a possibly quantized weight matrix `w` and a non-quantized
> input `x`. **The input `x` is quantized on the fly.** The weight matrix `w` is used as-is if it is
> already quantized; otherwise, it is quantized on the fly.
>
> If `w` is quantized, `scales` must be provided, and `group_size`, `bits`, and `mode` must match the
> parameters that were used to quantize `w`.
>
> **Notes**: **If `w` is expected to receive gradients, it must be provided in non-quantized form.**
> If `x` and `w` are not quantized, their data types must be `float32`, `float16`, or `bfloat16`. If
> `w` is quantized, it must be packed in unsigned integers. `global_scale_x` and `global_scale_w` are
> only used for `nvfp4` quantization.
>
> `mode` – Default: `"nvfp4"`. **Supported modes are `nvfp4` and `mxfp8`.**

```
to_fp8(x: array, *, stream=None) -> array
```
> Convert the array to fp8 (**e4m3**) from another floating-point type.
> Returns: The array converted to fp8 with type **`uint8`**.

```
from_fp8(x[, dtype, stream])
```

```
segmented_mm(a: array, b: array, /, segments: array, *, stream=None) -> array
```
> Perform a matrix multiplication but segment the inner dimension and save the result for each segment
> separately. `a` shape `MxK`, `b` shape `KxN`, `segments` = "The offsets into the inner dimension for
> each segment." Returns "The result per segment of shape `MxN`."

```
hadamard_transform(a: array, scale: float | None = None, stream=None) -> array
```
> Perform the Walsh-Hadamard transform along the final axis. Equivalent to:
> ```python
> from scipy.linalg import hadamard
> y = (hadamard(len(x)) @ x) * scale
> ```
> **Supports sizes `n = m*2^k` for `m` in `(1, 12, 20, 28)` and `2^k <= 8192` for float32 and
> `2^k <= 16384` for float16/bfloat16.**
> `scale` defaults to `1/sqrt(a.shape[-1])` so that the Hadamard matrix is orthonormal.

```
einsum(subscripts: str, *operands, stream=None) -> array
einsum_path(subscripts, *operands)
```

### 17.10 Notable / less-obvious operations in `python/ops.html`

```
as_strided(a, /[, shape, strides, offset, ...])
bartlett(M, *[, stream])          blackman(M, *[, stream])
hamming(M, *[, stream])           hanning(M, *[, stream])
block_masked_mm(a, b, /[, block_size, ...])
contiguous(a, /[, allow_col_major, stream])
conv_general(input, weight, /[, stride, ...])
depends(inputs, dependencies)
diff(a, /[, n, axis, stream])
from_dlpack(x, /, *[, copy])
isdtype(dtype, kind)
kron(a, b, *[, stream])
logcumsumexp(a, /[, axis, reverse, ...])
median(a, /[, axis, keepdims, stream])
nan_to_num(a[, nan, posinf, neginf, stream])
permute_dims(a, /[, axes, stream])
put_along_axis(a, /, indices, values[, ...])
slice_update(a, update, start_indices, axes, *)
topk(a, /, k[, axis, stream])
unflatten(a, /, axis, shape, *[, stream])
unstack(x, /, *[, axis, stream])
vecdot(a, b, /, *[, axis, stream])
```

Note `permute_dims`, `isdtype`, `vecdot`, `unstack` are Array-API-standard aliases. `contiguous` takes
`allow_col_major`. `depends(inputs, dependencies)` lets you manually add graph edges.

### 17.11 Print Options (`python/printoptions.html`)

```
PrintOptions(*args, **kwargs)
set_printoptions([precision])   Set global printing precision for array formatting.
printoptions([precision])       Context manager for setting print options temporarily.
get_printoptions()              Get global printing precision for array formatting.
```

### 17.12 Tree Utils (`python/tree_utils.html`)

> In MLX we consider a python tree to be an arbitrarily nested collection of dictionaries, lists and
> tuples **without cycles**. Functions in this module that return python trees will be using the
> default python `dict`, `list` and `tuple` but they can usually process objects that inherit from any
> of these.
>
> **Note**: Dictionaries should have keys that are valid python identifiers.

```
tree_flatten(tree[, prefix, is_leaf, destination])
tree_unflatten(tree)
tree_map(fn, tree, *rest[, is_leaf])
tree_map_with_path(fn, tree, *rest[, ...])
tree_reduce(fn, tree[, initializer, is_leaf])
tree_merge(tree_a, tree_b[, merge_fn])
```

```
tree_flatten(tree: Any, prefix: str = '', is_leaf: Callable | None = None,
             destination: List[Tuple[str, Any]] | Dict[str, Any] | None = None)
             -> List[Tuple[str, Any]] | Dict[str, Any]
```
> The keys are using the **dot notation** to define trees of arbitrary depth and complexity.

```python
from mlx.utils import tree_flatten

print(tree_flatten([[[0]]]))
# [("0.0.0", 0)]

print(tree_flatten([[[0]]], prefix=".hello"))
# [("hello.0.0.0", 0)]

tree_flatten({"a": {"b": 1}}, destination={})
{"a.b": 1}
```

> `prefix` – A prefix to use for the keys. **The first character is always discarded.**
> `destination` – A list or dictionary to store the flattened tree. If None an empty list will be used.

```
tree_map(fn: Callable, tree: Any, *rest: Any, is_leaf: Callable | None = None) -> Any
```
> If `rest` is provided, every item is assumed to be a **superset** of `tree` and the corresponding
> leaves are provided as extra positional arguments to `fn`. In that respect, `tree_map()` is closer to
> `itertools.starmap()` than to `map()`.

```python
import mlx.nn as nn
from mlx.utils import tree_map

model = nn.Linear(10, 10)
print(model.parameters().keys())
# dict_keys(['weight', 'bias'])

# square the parameters
model.update(tree_map(lambda x: x*x, model.parameters()))
```

---

## 18. Python API Reference — `mlx.nn`

### 18.1 Quick Start (verbatim from `python/nn.html`)

```python
import mlx.core as mx
import mlx.nn as nn

class MLP(nn.Module):
    def __init__(self, in_dims: int, out_dims: int):
        super().__init__()

        self.layers = [
            nn.Linear(in_dims, 128),
            nn.Linear(128, 128),
            nn.Linear(128, out_dims),
        ]

    def __call__(self, x):
        for i, l in enumerate(self.layers):
            x = mx.maximum(x, 0) if i > 0 else x
            x = l(x)
        return x

# The model is created with all its parameters but nothing is initialized
# yet because MLX is lazily evaluated
mlp = MLP(2, 10)

# We can access its parameters by calling mlp.parameters()
params = mlp.parameters()
print(params["layers"][0]["weight"].shape)

# Printing a parameter will cause it to be evaluated and thus initialized
print(params["layers"][0])

# We can also force evaluate all parameters to initialize the model
mx.eval(mlp.parameters())

# A simple loss function.
# NOTE: It doesn't matter how it uses the mlp model. It currently captures
#       it from the local scope. It could be a positional argument or a
#       keyword argument.
def l2_loss(x, y):
    y_hat = mlp(x)
    return (y_hat - y).square().mean()

# Calling `nn.value_and_grad` instead of `mx.value_and_grad` returns the
# gradient with respect to `mlp.trainable_parameters()`
loss_and_grad = nn.value_and_grad(mlp, l2_loss)
```

### 18.2 The Module Class (verbatim)

> **A parameter of a module is any public member of type `mlx.core.array` (its name should not start
> with `_`).** It can be arbitrarily nested in other `Module` instances or lists and dictionaries.
>
> `Module.parameters()` can be used to extract a nested dictionary with all the parameters of a module
> and its submodules.
>
> A `Module` can also keep track of "frozen" parameters. See the `Module.freeze()` method for more
> details. `mlx.nn.value_and_grad()` the gradients returned will be with respect to these trainable
> parameters.

Inspecting:

```python
print(mlp)
```

```
MLP(
  (layers.0): Linear(input_dims=2, output_dims=128, bias=True)
  (layers.1): Linear(input_dims=128, output_dims=128, bias=True)
  (layers.2): Linear(input_dims=128, output_dims=10, bias=True)
)
```

```python
from mlx.utils import tree_map
shapes = tree_map(lambda p: p.shape, mlp.parameters())
```

```python
from mlx.utils import tree_flatten
num_params = sum(v.size for _, v in tree_flatten(mlp.parameters()))
```

### 18.3 `nn.value_and_grad` semantics (verbatim)

Manual pattern:

```python
model = ...

def f(params, other_inputs):
    model.update(params)  # <---- Necessary to make the model use the passed parameters
    return model(other_inputs)

f(model.trainable_parameters(), mx.zeros((10,)))
```

> However, `mlx.nn.value_and_grad()` provides precisely this pattern and **only computes the gradients
> with respect to the trainable parameters of the model.**
>
> In detail:
> - it wraps the passed function with a function that calls `Module.update()` to make sure the model is
>   using the provided parameters.
> - it calls `mlx.core.value_and_grad()` to transform the function into a function that also computes
>   the gradients with respect to the passed parameters.
> - it wraps the returned function with a function that passes the trainable parameters as the first
>   argument to the function returned by `mlx.core.value_and_grad()`

### 18.4 Module methods (complete list from `python/nn/module.html` toctree)

```
Module.training (attr)      Module.state (attr)
Module.apply()              Module.apply_to_modules()
Module.children()           Module.eval()
Module.filter_and_map()     Module.freeze()
Module.leaf_modules()       Module.load_weights()
Module.modules()            Module.named_modules()
Module.parameters()         Module.save_weights()
Module.set_dtype()          Module.train()
Module.trainable_parameters()  Module.unfreeze()
Module.update()             Module.update_modules()
```

```
Module.load_weights(file_or_weights: str | List[Tuple[str, array]], strict: bool = True) -> Module
```
> Update the model's weights from a `.npz`, a `.safetensors` file, or a list.
> `strict` – **If `True` then checks that the provided weights exactly match the parameters of the
> model. Otherwise, only the weights actually contained in the model are loaded and shapes are not
> checked.** Default: `True`.

```python
import mlx.core as mx
import mlx.nn as nn

model = nn.Linear(10, 10)

# Load from file
model.load_weights("weights.npz")

# Load from .safetensors file
model.load_weights("weights.safetensors")

# Load from list
weights = [
    ("weight", mx.random.uniform(shape=(10, 10))),
    ("bias",  mx.zeros((10,))),
]
model.load_weights(weights)

# Missing weight
weights = [
    ("weight", mx.random.uniform(shape=(10, 10))),
]

# Raises a ValueError exception
model.load_weights(weights)

# Ok, only updates the weight but not the bias
model.load_weights(weights, strict=False)
```

```
Module.set_dtype(dtype: Dtype, predicate: Callable[[Dtype], bool] | None = <function Module.<lambda>>)
```
> `predicate` – A predicate to select parameters to cast. **By default, only parameters of type
> `floating` will be updated to avoid casting integer parameters to the new dtype.**

### 18.5 Module-level `nn` functions

```
value_and_grad(model, fn)
quantize(model[, group_size, bits, mode, ...])
average_gradients(gradients[, group, ...])
fsdp_apply_gradients(gradients, parameters, ...)
```

```
nn.quantize(model: Module, group_size: int = None, bits: int = None, *,
            mode: str = 'affine', quantize_input: bool = False,
            class_predicate: Callable[[str, Module], bool | dict] | None = None)
```
> By default **all layers that define a `to_quantized()` method will be quantized. Both `Linear` and
> `Embedding` layers will be quantized. The module is updated in-place.**
>
> **Note**: `quantize_input=True` is only supported for `"nvfp4"` and `"mxfp8"` modes and `Linear`
> layers.
>
> `class_predicate` – A callable which receives the `Module` path and `Module` itself and returns
> `True` **or a dict of params for `to_quantized`** if it should be quantized and `False` otherwise.

```python
>>> import mlx.nn as nn
>>> nn.quantize(model, group_size=64, bits=4, mode="affine")
```

```python
>>> predicate = lambda p, m: isinstance(m, nn.Linear)
>>> nn.quantize(model, mode="nvfp4", quantize_input=True, class_predicate=predicate)
```

```
nn.average_gradients(gradients: Any, group: Group | None = None,
                     all_reduce_size: int = 33554432,
                     communication_stream: Stream | None = None)
```
> This helper enables **concatenating several gradients of small arrays to one big all reduce call for
> better networking performance.**
> `all_reduce_size` – Group arrays until their size in bytes exceeds this number. Perform one
> communication step per group of arrays. **If less or equal to 0 array grouping is disabled.** Default:
> `32MiB`.
> `communication_stream` – The stream to use for the communication. If unspecified the default
> communication stream is used **which can vary by back-end**. Default: `None`.

```
nn.fsdp_apply_gradients(gradients, parameters, optimizer, fsdp_group=None, dp_group=None,
                        communication_size=33554432, communication_stream=None, max_norm=None)
```
> Perform a distributed optimizer step by sharding gradients and optimizer states across ranks.
>
> This helper function performs the following steps:
> 1. Reduce-scatter the gradients across ranks so each rank gets a shard of the averaged gradients.
> 2. Optionally clip the sharded gradients by global norm.
> 3. Apply the optimizer update on the local parameter slice using the sharded gradients.
> 4. All-gather the updated parameter slices from all ranks to reconstruct the full parameters tree.
>
> **This is similar to PyTorch's FSDP with `reshard_after_forward=False`.**
>
> `gradients` – Each gradient's **first dimension must be divisible by `fsdp_group.size()`**.
> `parameters` – Each parameter's first dimension must be divisible by `fsdp_group.size()`.
> `optimizer` – Optimizer with an `apply_gradients` method.
> `fsdp_group` – If `None`, the global group is used.
> `dp_group` – **Required when `fsdp_group` is smaller than the world (e.g. FSDP intra-node, DDP
> inter-node).** Default: `None`.
> `max_norm` – If provided, clip gradients to this maximum global norm before applying the optimizer
> update. Default: `None`.
>
> **Returns**: If `max_norm` is `None`, returns the updated full-parameter tree. Otherwise returns
> `(parameters, grad_norm)`, where `grad_norm` is the global gradient norm **before** clipping.

```python
>>> optimizer = optim.SGD(learning_rate=0.01)
>>> # Without gradient clipping
>>> updated_params = fsdp_apply_gradients(grads, params, optimizer)
>>> model.update(updated_params)
>>>
>>> # With gradient clipping
>>> updated_params, grad_norm = fsdp_apply_gradients(
...     grads, params, optimizer, max_norm=1.0
... )
>>> model.update(updated_params)
```

### 18.6 Layers (`python/nn/layers.html`) — complete list with constructor argument hints

```
ALiBi()
AllToShardedLinear(input_dims, output_dims)
AvgPool1d(kernel_size[, stride, padding])
AvgPool2d(kernel_size[, stride, padding])
AvgPool3d(kernel_size[, stride, padding])
BatchNorm(num_features[, eps, momentum, ...])
Bilinear(input1_dims, input2_dims, output_dims)
CELU([alpha])
Conv1d(in_channels, out_channels, kernel_size)
Conv2d(in_channels, out_channels, kernel_size)
Conv3d(in_channels, out_channels, kernel_size)
ConvTranspose1d(in_channels, out_channels, ...)
ConvTranspose2d(in_channels, out_channels, ...)
ConvTranspose3d(in_channels, out_channels, ...)
Dropout([p])
Dropout2d([p])              Apply 2D channel-wise dropout during training.
Dropout3d([p])              Apply 3D channel-wise dropout during training.
Embedding(num_embeddings, dims)
ELU([alpha])
GELU([approx])
GLU([axis])
GroupNorm(num_groups, dims[, eps, affine, ...])
GRU(input_size, hidden_size[, bias])
HardShrink([lambd])
HardTanh()
Hardswish()
Identity(*args, **kwargs)
InstanceNorm(dims[, eps, affine])
LayerNorm(dims[, eps, affine, bias])
LeakyReLU([negative_slope])
Linear(input_dims, output_dims[, bias])
LogSigmoid()
LogSoftmax()
LSTM(input_size, hidden_size[, bias])
MaxPool1d(kernel_size[, stride, padding])
MaxPool2d(kernel_size[, stride, padding])
MaxPool3d(kernel_size[, stride, padding])
Mish()
MultiHeadAttention(dims, num_heads[, ...])
PReLU([num_parameters, init])
QQLinear(input_dims, output_dims[, ...])          Quantizes the INPUT and applies an affine
                                                  transformation using quantized weights.
QuantizedAllToShardedLinear(input_dims, ...)
QuantizedEmbedding(num_embeddings, dims[, ...])
QuantizedLinear(input_dims, output_dims[, ...])
QuantizedShardedToAllLinear(input_dims, ...)
RMSNorm(dims[, eps])
ReLU()
ReLU2()                     Applies the ReLU² activation function.
ReLU6()
RNN(input_size, hidden_size[, bias, ...])         An Elman recurrent layer.
RoPE(dims[, traditional, base, scale])
SELU()
Sequential(*modules)
ShardedToAllLinear(input_dims, output_dims)
Sigmoid()
SiLU()
SinusoidalPositionalEncoding(dims[, ...])
Softmin()   Softshrink([lambd])   Softsign()   Softmax()   Softplus()
Step([threshold])
Tanh()
Transformer(dims, num_heads, ...)
TransformerDecoder(num_layers, dims, ...[, ...])
TransformerDecoderLayer(dims, num_heads, ...)
TransformerEncoder(num_layers, dims, ...[, ...])
TransformerEncoderLayer(dims, num_heads, ...)
Upsample(scale_factor[, mode, align_corners])
```

**New / notable:** `QQLinear` (quantized activations × quantized weights), `ReLU2`,
`AllToShardedLinear` / `ShardedToAllLinear` + quantized variants (tensor parallel),
`AvgPool3d`/`MaxPool3d`, `Conv3d`/`ConvTranspose3d`.

### 18.7 Functions (`python/nn/functions.html`)

```
elu, celu, gelu, gelu_approx, gelu_fast_approx, glu, hard_shrink, hard_tanh, hardswish,
leaky_relu, log_sigmoid, log_softmax, mish, prelu, relu, relu2, relu6, selu, sigmoid, silu,
softmax, softmin, softplus, softshrink, step, tanh
```

### 18.8 Loss Functions (`python/nn/losses.html`)

```
binary_cross_entropy(inputs, targets[, ...])
cosine_similarity_loss(x1, x2[, axis, eps, ...])
cross_entropy(logits, targets[, weights, ...])
gaussian_nll_loss(inputs, targets, vars[, ...])
hinge_loss(inputs, targets[, reduction])
huber_loss(inputs, targets[, delta, reduction])
kl_div_loss(inputs, targets[, axis, reduction])
l1_loss(predictions, targets[, reduction])
log_cosh_loss(inputs, targets[, reduction])
margin_ranking_loss(inputs1, inputs2, targets)
mse_loss(predictions, targets[, reduction])
nll_loss(inputs, targets[, axis, reduction])
smooth_l1_loss(predictions, targets[, beta, ...])
triplet_loss(anchors, positives, negatives)
```

All are in the `mlx.nn.losses` namespace (`nn.losses.binary_cross_entropy`, etc.). Note argument name
inconsistency across losses: some use `inputs, targets`, others `predictions, targets`, and
`cross_entropy` uses `logits, targets`.

### 18.9 Initializers (`python/nn/init.html`) — verbatim

> The `mlx.nn.init` package contains commonly used initializers for neural network parameters.
> **Initializers return a function which can be applied to any input `mlx.core.array` to produce an
> initialized output.**

```python
import mlx.core as mx
import mlx.nn as nn

init_fn = nn.init.uniform()

# Produces a [2, 2] uniform matrix
param = init_fn(mx.zeros((2, 2)))
```

```python
import mlx.nn as nn

model = nn.Sequential(nn.Linear(5, 10), nn.ReLU(), nn.Linear(10, 5))
init_fn = nn.init.uniform(low=-0.1, high=0.1)
model.apply(init_fn)
```

```
constant(value[, dtype])
normal([mean, std, dtype])
uniform([low, high, dtype])
identity([dtype])
glorot_normal([dtype])
glorot_uniform([dtype])
he_normal([dtype])
he_uniform([dtype])           A He uniform (Kaiming uniform) initializer.
sparse(sparsity[, mean, std, dtype])
orthogonal([gain, dtype])
```

### 18.10 nn Distributed (`python/nn/distributed.html`)

> The `mlx.nn.layers.distributed` package contains helpful routines to create sharded layers from
> existing `Modules`.

```
shard_linear(module, sharding, *[, segments, group])
shard_inplace(module, sharding, *[, ...])
AllToShardedLinear(input_dims, output_dims)
ShardedToAllLinear(input_dims, output_dims)
QuantizedAllToShardedLinear(input_dims, ...)
QuantizedShardedToAllLinear(input_dims, ...)
```

```
shard_linear(module: Module, sharding: str, *, segments: int | list = 1, group: Group | None = None)
```
> Create a new linear layer that has its parameters sharded and also performs distributed communication
> either in the forward or backward pass.
> **Note**: Contrary to `shard_inplace`, **the original layer is not changed but a new layer is
> returned.**
> `sharding` – One of **"all-to-sharded"** and **"sharded-to-all"** that defines the type of sharding to
> perform.
> `segments` – The segments to use. Default: `1`.
> `group` – The distributed group to shard across. If not set, the global group will be used.

---

## 19. Python API Reference — `mlx.optimizers`

### 19.1 Usage pattern (verbatim)

```python
# Create a model
model = MLP(num_layers, train_images.shape[-1], hidden_dim, num_classes)
mx.eval(model.parameters())

# Create the gradient function and the optimizer
loss_and_grad_fn = nn.value_and_grad(model, loss_fn)
optimizer = optim.SGD(learning_rate=learning_rate)

for e in range(num_epochs):
    for X, y in batch_iterate(batch_size, train_images, train_labels):
        loss, grads = loss_and_grad_fn(model, X, y)

        # Update the model with the gradients. So far no computation has happened.
        optimizer.update(model, grads)

        # Compute the new parameters but also the optimizer state.
        mx.eval(model.parameters(), optimizer.state)
```

### 19.2 Saving and Loading optimizers (verbatim)

```python
import mlx.core as mx
from mlx.utils import tree_flatten, tree_unflatten
import mlx.optimizers as optim

optimizer = optim.Adam(learning_rate=1e-2)

# Perform some updates with the optimizer
model = {"w" : mx.zeros((5, 5))}
grads = {"w" : mx.ones((5, 5))}
optimizer.update(model, grads)

# Save the state
state = tree_flatten(optimizer.state, destination={})
mx.save_safetensors("optimizer.safetensors", state)

# Later on, for example when loading from a checkpoint,
# recreate the optimizer and load the state
optimizer = optim.Adam(learning_rate=1e-2)

state = tree_unflatten(mx.load("optimizer.safetensors"))
optimizer.state = state
```

> **Note, not every optimizer configuation parameter is saved in the state. For example, for Adam the
> learning rate is saved but the `betas` and `eps` parameters are not. A good rule of thumb is if the
> parameter can be scheduled then it will be included in the optimizer state.**

### 19.3 Base class

```
class Optimizer(schedulers=None)
```
> The base class for all optimizers. It allows us to implement an optimizer on a per-parameter basis
> and apply it to a parameter tree.

```
Optimizer.state                                    The optimizer's state dictionary.
Optimizer.apply_gradients(gradients, parameters)   Apply the gradients to the parameters and
                                                   return the updated parameters.
Optimizer.init(parameters)                         Initialize the optimizer's state
Optimizer.update(model: Module, gradients: dict)   Apply the gradients to the parameters of the model
                                                   and update the model with the new parameters.
```

Subclasses implement `apply_single(gradient, parameter, state)` and `init_single(parameter, state)`.

### 19.4 Common Optimizers (complete list + brief signatures)

```
SGD(learning_rate[, momentum, weight_decay, ...])
RMSprop(learning_rate[, alpha, eps])
Adagrad(learning_rate[, eps])
Adafactor([learning_rate, eps, ...])
AdaDelta(learning_rate[, rho, eps])
Adam(learning_rate[, betas, eps, ...])
AdamW(learning_rate[, betas, eps, ...])
Adamax(learning_rate[, betas, eps])
Lion(learning_rate[, betas, weight_decay])
MultiOptimizer(optimizers[, filters])
Muon(learning_rate[, momentum, ...])
```

Exact signatures for the two most notable:

```
class SGD(learning_rate: float | Callable[[array], array],
          momentum: float = 0.0,
          weight_decay: float = 0.0,
          dampening: float = 0.0,
          nesterov: bool = False)
```
> v_{t+1} = μ·v_t + (1 − τ)·g_t ;  w_{t+1} = w_t − λ·v_{t+1}

```
class AdamW(learning_rate: float | Callable[[array], array],
            betas: List[float] = [0.9, 0.999],
            eps: float = 1e-08,
            weight_decay: float = 0.01,
            bias_correction: bool = False)
```
> m_{t+1} = β₁m_t + (1−β₁)g_t ; v_{t+1} = β₂v_t + (1−β₂)g_t² ;
> w_{t+1} = w_t − α( m_{t+1}/(√v_{t+1} + ε) + λ·w_t )
> `bias_correction` – If set to `True`, bias correction is applied. **Default: `False`**

```
class Muon(learning_rate: float | Callable[[array], array],
           momentum: float = 0.95,
           weight_decay: float = 0.01,
           nesterov: bool = True,
           ns_steps: int = 5)
```
> Our Muon (MomentUm Orthogonalized by Newton-schulz) optimizer follows the original implementation:
> "Muon: An optimizer for hidden layers in neural networks"
>
> **Note:**
> - **Muon may be sub-optimal for the embedding layer, the final fully connected layer, or any 0D/1D
>   parameters. Those should be optimized by a different method (e.g., `AdamW`).**
> - **For 4D convolutional filters, it works by flattening their last dimensions.**
>
> `ns_steps` – Number of Newton-Schulz iteration steps for orthogonalization. Default: `5`
> `nesterov` – Enables Nesterov momentum. **Recommended for better performance.** Default: `True`

```
class MultiOptimizer(optimizers, filters: list = [])
```
> Wraps a list of optimizers with corresponding weight predicates/filters to make it easy to use
> different optimizers for different weights.
>
> **The predicates take the full "path" of the weight and the weight itself and return True if it
> should be considered for this optimizer. The last optimizer in the list is a fallback optimizer and
> no predicate should be given for it.**
>
> `filters` – A list of predicates that **should be one less than the provided optimizers**.

(`MultiOptimizer` + `Muon` together are the canonical "Muon for hidden layers, AdamW for
embeddings/head" recipe.)

### 19.5 Schedulers

```
cosine_decay(init, decay_steps[, end])
exponential_decay(init, decay_rate)
join_schedules(schedules, boundaries)
linear_schedule(init, end, steps)
step_decay(init, decay_rate, step_size)
```

### 19.6 `clip_grad_norm`

```
clip_grad_norm(grads, max_norm)
```
> This function ensures that the global norm of the gradients does not exceed `max_norm`. It scales
> down the gradients proportionally if their norm is greater than `max_norm`.
> Returns: **The possibly rescaled gradients AND the original gradient norm** — return type
> `(dict, float)`.

```python
>>> grads = {"w1": mx.array([2, 3]), "w2": mx.array([1])}
>>> clipped_grads, total_norm = clip_grad_norm(grads, max_norm=2.0)
>>> print(clipped_grads)
{"w1": mx.array([...]), "w2": mx.array([...])}
```

---

## 20. Examples — Data Parallelism (`examples/data_parallelism.html`) — verbatim

Baseline loop:

```python
model = ...
optimizer = ...
dataset = ...

def step(model, x, y):
    loss, grads = loss_grad_fn(model, x, y)
    optimizer.update(model, grads)
    return loss

for x, y in dataset:
    loss = step(model, x, y)
    mx.eval(loss, model.parameters())
```

> All we have to do to average the gradients across machines is perform an `all_sum()` and divide by
> the size of the `Group`.

```python
def all_avg(x):
    return mx.distributed.all_sum(x) / mx.distributed.init().size()
```

```python
from mlx.utils import tree_map

def all_reduce_grads(grads):
    N = mx.distributed.init().size()
    if N == 1:
        return grads
    return tree_map(
        lambda x: mx.distributed.all_sum(x) / N,
        grads
    )

def step(model, x, y):
    loss, grads = loss_grad_fn(model, x, y)
    grads = all_reduce_grads(grads)  # <--- This line was added
    optimizer.update(model, grads)
    return loss
```

> Although the code example above works correctly; **it performs one communication per gradient. It is
> significantly more efficient to aggregate several gradients together and perform fewer communication
> steps.** This is the purpose of `mlx.nn.average_gradients()`.

```python
model = ...
optimizer = ...
dataset = ...

def step(model, x, y):
    loss, grads = loss_grad_fn(model, x, y)
    grads = mx.nn.average_gradients(grads)  # <---- This line was added
    optimizer.update(model, grads)
    return loss

for x, y in dataset:
    loss = step(model, x, y)
    mx.eval(loss, model.parameters())
```

(Note: the doc writes `mx.nn.average_gradients` here but elsewhere `mlx.nn.average_gradients` /
`nn.average_gradients`. The importable path is `mlx.nn.average_gradients`.)

---

## 21. Examples — Tensor Parallelism (`examples/tensor_parallelism.html`) — verbatim

### 21.1 `AllToShardedLinear`

> This layer **replicates a common input and shards the weight matrix along the output dimension**
> across all devices in the `mlx.core.distributed.Group`. The layer produces a sharded output.
>
> For example, consider an `mlx.nn.AllToShardedLinear` layer with `input_dims=2` and `output_dims=2`, a
> batched input of shape `(4, 2)`, and a device group with 2 devices. The layer shards the weight matrix
> along the output dimension across the two devices, where each device receives the full input and
> computes a partial output.
>
> **This layer does not automatically gather all outputs from each device. This is an intended and
> useful design choice.**
>
> `QuantizedAllToShardedLinear` is the quantized equivalent […] Similar to `mlx.nn.QuantizedLinear`,
> **its parameters are frozen and will not be included in any gradient computation.**

### 21.2 `ShardedToAllLinear`

> This layer **expects inputs that are sharded along the feature dimension and shards the weight matrix
> along the input dimension** across all devices in the `mlx.core.distributed.Group`. **The layer
> automatically aggregates the results using `mlx.core.distributed.all_sum`**, so all devices in the
> group will have the same result.
>
> **This layer does not automatically shard the inputs along the feature dimension for you.** It is
> necessary to create a "partial" input structure to feed into the layer.

### 21.3 Why the asymmetry (verbatim)

> All-to-sharded and sharded-to-all layers naturally go together because **the output of the former
> layer is exactly the input needed for the latter. This removes the need for an intermediate gather
> step between the layers, reducing communication overhead.**

```python
x = ... # some (4, 2) model input: batch size 4, feature size 2
l1 = nn.AllToShardedLinear(2, 2, bias=False) # initialize the layer
l1_out = l1(x) # (4, 1) output

l2 = nn.ShardedToAllLinear(2, 2, bias=False)
l2_out = l2(l1_out) # (4, 2) output
```

### 21.4 `shard_linear` vs `shard_inplace` (verbatim)

> **`shard_linear`** — Converts a regular linear layer into a tensor parallel layer that distributes
> computation across multiple devices. Takes an existing `mlx.nn.Linear` or `mlx.nn.QuantizedLinear`
> layer and returns a new distributed layer (either `mlx.nn.AllToShardedLinear` or
> `mlx.nn.ShardedToAllLinear`, depending on the sharding type). **The original layer is not modified.**
>
> **`shard_inplace`** — Splits the parameters of an existing layer across multiple devices by modifying
> the layer in-place. Unlike `shard_linear`, **this function does not create a new layer or add
> distributed communication. The layer itself must handle distributed communication if needed.**

### 21.5 Llama TP recipe (verbatim)

```python
world = mx.distributed.init()
rank = world.rank()
```

> This architecture has two natural places where tensor parallelism can be applied: the attention block
> and the FFN block. Both follow the same pattern: multiple parallel linear layers operating on the
> same input, followed by a single output linear layer. In the attention block, the **Q, K, and V
> projections are sharded along the output dimension (all-to-sharded), and the output projection is
> sharded along the input dimension (sharded-to-all).** Similarly in the FFN block, the **gate and up
> projections become all-to-sharded layers, and the down projection becomes a sharded-to-all layer.**
>
> The intermediate operations between the linear layers (RoPE, softmax, scaled dot-product attention in
> the attention block, and element-wise multiplication in the FFN block) do not impede the use of our
> TP paradigm. These operations are either:
> - **Element-wise operations** (RoPE, element-wise multiplication): These operate independently on each
>   element or position, preserving the sharding pattern without requiring cross-device communication.
> - **Operations on non-sharded dimensions** (softmax, scaled dot-product attention): These operate along
>   dimensions that are not sharded (such as the sequence length or head dimensions), so they can be
>   computed independently on each device. The attention computation `Q @ K^T` and `scores @ V` work
>   correctly with sharded Q, K, V tensors because the matrix multiplications are performed along the
>   sharded feature dimension, and the results remain properly sharded for the subsequent sharded-to-all
>   layer.

```python
# ... in Attention class
def shard(self, group: mx.distributed.Group):
    self.n_heads = self.n_heads // group.size()
    self.n_kv_heads = self.n_kv_heads // group.size()
    self.wq = nn.layers.distributed.shard_linear(self.wq, "all-to-sharded", group=group)
    self.wk = nn.layers.distributed.shard_linear(self.wk, "all-to-sharded", group=group)
    self.wv = nn.layers.distributed.shard_linear(self.wv, "all-to-sharded", group=group)
    self.wo = nn.layers.distributed.shard_linear(self.wo, "sharded-to-all", group=group)
```

```python
# ... in FeedForward class
def shard(self, group: mx.distributed.Group):
    self.w1 = nn.layers.distributed.shard_linear(self.w1, "all-to-sharded", group=group)
    self.w2 = nn.layers.distributed.shard_linear(self.w2, "sharded-to-all", group=group)
    self.w3 = nn.layers.distributed.shard_linear(self.w3, "all-to-sharded", group=group)
```

```python
# ... in load_model function
if world.size() > 1:
    # convert Linear layers in Transformer/FFN to appropriate Sharded Layers
    for layer in model.layers:
        layer.attention.shard(group=world)
        layer.feed_forward.shard(group=world)
```

> This allows us to use the llama inference file as normal when running `python llama.py`, but now we
> can also run it across two (or more) devices via `mlx.launch -n 2 llama.py`.

---

## 22. C++ API Reference (`cpp/ops.html`)

The C++ reference on this site consists of **exactly one page**: `cpp/ops.html`, titled "Operations".
It documents **366 `<dt>` signatures** (counted). There is no C++ page for `array`, `Primitive`,
`Stream`, `nn`, or `optimizers` — those are only in the source.

### 22.1 Conventions

- Namespace in examples: `namespace mx = mlx::core;`
- Every op takes a trailing `StreamOrDevice s = {}` argument.
- Shapes are `Shape` (a `std::vector<int>`-like), strides are `Strides` / `std::vector<int64_t>`.
- Overload sets are large (e.g. `arange` has 9 overloads, `roll` has 6, `logsumexp` has 4).

### 22.2 Representative verbatim signatures

```cpp
array arange(double start, double stop, double step, Dtype dtype, StreamOrDevice s = {})
array arange(double start, double stop, double step, StreamOrDevice s = {})
array arange(double start, double stop, Dtype dtype, StreamOrDevice s = {})
array arange(double start, double stop, StreamOrDevice s = {})
array arange(double stop, Dtype dtype, StreamOrDevice s = {})
array arange(double stop, StreamOrDevice s = {})
array arange(int start, int stop, int step, StreamOrDevice s = {})
array arange(int start, int stop, StreamOrDevice s = {})
array arange(int stop, StreamOrDevice s = {})

array linspace(double start, double stop, int num = 50, Dtype dtype = float32, StreamOrDevice s = {})

array astype(array a, Dtype dtype, std::optional<bool> copy, StreamOrDevice s = {})
inline array astype(array a, Dtype dtype, StreamOrDevice s = {})

array as_strided(array a, Shape shape, Strides strides, size_t offset, StreamOrDevice s = {})
array copy(array a, StreamOrDevice s = {})

array full(Shape shape, array vals, Dtype dtype, StreamOrDevice s = {})
array full(Shape shape, array vals, StreamOrDevice s = {})
template<typename T> array full(Shape shape, T val, Dtype dtype, StreamOrDevice s = {})
template<typename T> array full(Shape shape, T val, StreamOrDevice s = {})
array full_like(const array &a, array vals, Dtype dtype, StreamOrDevice s = {})
array full_like(const array &a, array vals, StreamOrDevice s = {})
```

Slicing & scatter family (note the many `slice_update_*` reduction variants that have **no direct
Python equivalent name**):

```cpp
array slice(const array &a, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
inline array slice(const array &a, std::initializer_list<int> start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice(const array &a, Shape start, Shape stop, StreamOrDevice s = {})
array slice(const array &a, const array &start, std::vector<int> axes, Shape slice_size, StreamOrDevice s = {})

array slice_update(const array &src, const array &update, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice_update(const array &src, const array &update, Shape start, Shape stop, StreamOrDevice s = {})
array slice_update(const array &src, const array &update, const array &start, std::vector<int> axes, StreamOrDevice s = {})
array slice_update_add(const array &src, const array &update, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice_update_add(const array &src, const array &update, Shape start, Shape stop, StreamOrDevice s = {})
array slice_update_prod(const array &src, const array &update, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice_update_prod(const array &src, const array &update, Shape start, Shape stop, StreamOrDevice s = {})
array slice_update_max(const array &src, const array &update, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice_update_max(const array &src, const array &update, Shape start, Shape stop, StreamOrDevice s = {})
array slice_update_min(const array &src, const array &update, Shape start, Shape stop, Shape strides, StreamOrDevice s = {})
array slice_update_min(const array &src, const array &update, Shape start, Shape stop, StreamOrDevice s = {})

array gather(const array &a, const std::vector<array> &indices, const std::vector<int> &axes, const Shape &slice_sizes, StreamOrDevice s = {})
inline array gather(const array &a, const array &indices, int axis, const Shape &slice_sizes, StreamOrDevice s = {})

array scatter(const array &a, const std::vector<array> &indices, const array &updates, const std::vector<int> &axes, StreamOrDevice s = {})
inline array scatter(const array &a, const array &indices, const array &updates, int axis, StreamOrDevice s = {})
array scatter_add(const array &a, const std::vector<array> &indices, const array &updates, const std::vector<int> &axes, StreamOrDevice s = {})
array scatter_add_axis(const array &a, const array &indices, const array &values, int axis, StreamOrDevice s = {})
array scatter_prod(...)   array scatter_max(...)   array scatter_min(...)
array masked_scatter(const array &a, const array &mask, const array &src, StreamOrDevice s = {})
```

Other notable C++-only details:

```cpp
array softmax(const array &a, const std::vector<int> &axes, bool precise = false, StreamOrDevice s = {})
```
— the C++ `softmax` exposes a **`bool precise`** flag not surfaced under that name in the Python docs.

```cpp
array contiguous(const array &a, bool allow_col_major = false, StreamOrDevice s = {})
array view(const array &a, const Dtype &dtype, StreamOrDevice s = {})
array number_of_elements(const array &a, std::vector<int> axes, bool inverted, Dtype dtype = int32, StreamOrDevice s = {})
array hadamard_transform(const array &a, std::optional<float> scale = std::nullopt, StreamOrDevice s = {})

array logsumexp(const array &a, bool keepdims, StreamOrDevice s = {})
inline array logsumexp(const array &a, StreamOrDevice s = {})
array logsumexp(const array &a, const std::vector<int> &axes, bool keepdims = false, StreamOrDevice s = {})
array logsumexp(const array &a, int axis, bool keepdims = false, StreamOrDevice s = {})

std::vector<array> split(const array &a, int num_splits, int axis, StreamOrDevice s = {})
std::vector<array> split(const array &a, int num_splits, StreamOrDevice s = {})
std::vector<array> split(const array &a, const Shape &indices, int axis, StreamOrDevice s = {})
std::vector<array> split(const array &a, const Shape &indices, StreamOrDevice s = {})

array roll(const array &a, int shift, StreamOrDevice s = {})
array roll(const array &a, const Shape &shift, StreamOrDevice s = {})
array roll(const array &a, int shift, int axis, StreamOrDevice s = {})
array roll(const array &a, int shift, const std::vector<int> &axes, StreamOrDevice s = {})
array roll(const array &a, const Shape &shift, int axis, StreamOrDevice s = {})
array roll(const array &a, const Shape &shift, const std::vector<int> &axes, StreamOrDevice s = {})

array bitwise_and(const array &a, const array &b, StreamOrDevice s = {})   array operator&(const array&, const array&)
array bitwise_or (const array &a, const array &b, StreamOrDevice s = {})   array operator|(const array&, const array&)
array bitwise_xor(const array &a, const array &b, StreamOrDevice s = {})   array operator^(const array&, const array&)
array left_shift (const array &a, const array &b, StreamOrDevice s = {})   array operator<<(const array&, const array&)
array right_shift(const array &a, const array &b, StreamOrDevice s = {})   array operator>>(const array&, const array&)
array bitwise_invert(const array &a, StreamOrDevice s = {})                array operator~(const array&)

array real(const array &a, StreamOrDevice s = {})
array imag(const array &a, StreamOrDevice s = {})
array conjugate(const array &a, StreamOrDevice s = {})

std::vector<array> atleast_1d/atleast_2d/atleast_3d(const std::vector<array> &a, StreamOrDevice s = {})
```

---

## 23. Using MLX in C++ (`dev/mlx_in_cpp.html`) — verbatim, FULL

```bash
pip install -U mlx
```

`example.cpp`:

```cpp
#include <iostream>

#include "mlx/mlx.h"

namespace mx = mlx::core;

int main() {
  auto x = mx::array({1, 2, 3});
  auto y = mx::array({1, 2, 3});
  std::cout << x + y << std::endl;
  return 0;
}
```

`CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.27)

project(example LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

> If you installed MLX with Python, then add the following to the CMake file:

```cmake
find_package(
  Python 3.9
  COMPONENTS Interpreter Development.Module
  REQUIRED)
execute_process(
  COMMAND "${Python_EXECUTABLE}" -m mlx --cmake-dir
  OUTPUT_STRIP_TRAILING_WHITESPACE
  OUTPUT_VARIABLE MLX_ROOT)
```

> If you installed the MLX C++ package to a system path, then CMake should be able to find it. If you
> installed it to a non-standard location or CMake can't find MLX then set `MLX_ROOT`:

```cmake
set(MLX_ROOT "/path/to/mlx/")
```

```cmake
find_package(MLX CONFIG REQUIRED)
```

```cmake
add_executable(example example.cpp)
target_link_libraries(example PRIVATE mlx)
```

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

```bash
./build/example
```

### Package Variables set by `find_package(MLX CONFIG REQUIRED)` (exact table)

| Variable | Description |
|---|---|
| `MLX_FOUND` | `True` if MLX is found |
| `MLX_INCLUDE_DIRS` | Include directory |
| `MLX_LIBRARIES` | Libraries to link against |
| `MLX_CXX_FLAGS` | Additional compiler flags |
| `MLX_BUILD_ACCELERATE` | `True` if MLX was built with Accelerate |
| `MLX_BUILD_METAL` | `True` if MLX was built with Metal |

**Key CLI fact:** `python -m mlx --cmake-dir` prints the CMake package dir of a pip-installed MLX.
Note the CMake minimum here (3.27) is higher than the MLX build requirement (3.25).

---

## 24. Custom Extensions in MLX (`dev/extensions.html`) — verbatim highlights

Page outline: Introducing the Example → Operations and Primitives (Operations / Primitives / Using the
Primitive) → Implementing the Primitive (CPU Back-end / GPU Back-end / Primitive Transforms) →
Building and Binding (Binding to Python / Building with CMake / Building with `setuptools`) → Usage →
Results → Scripts.

### 24.1 Operations vs Primitives (verbatim)

> **Operations in MLX build the computation graph. Primitives provide the rules for evaluating and
> transforming the graph.**

```cpp
/**
 *  Scale and sum two vectors element-wise
 *  z = alpha * x + beta * y
 *
 *  Use NumPy-style broadcasting between x and y
 *  Inputs are upcasted to floats if needed
 **/
array axpby(
    const array& x, // Input array x
    const array& y, // Input array y
    const float alpha, // Scaling factor for x
    const float beta, // Scaling factor for y
    StreamOrDevice s = {} // Stream on which to schedule the operation
);
```

> A `Primitive` is part of the computation graph of an `array`. It defines how to create output arrays
> given input arrays. Further, a `Primitive` has methods to run on the CPU or GPU and for function
> transformations such as `vjp` and `jvp`.

```cpp
class Axpby : public Primitive {
 public:
  explicit Axpby(Stream stream, float alpha, float beta)
      : Primitive(stream), alpha_(alpha), beta_(beta){};

  /**
   * A primitive must know how to evaluate itself on the CPU/GPU
   * for the given inputs and populate the output array.
   *
   * To avoid unnecessary allocations, the evaluation function
   * is responsible for allocating space for the array.
   */
  void eval_cpu(
      const std::vector<array>& inputs,
      std::vector<array>& outputs) override;
  void eval_gpu(
      const std::vector<array>& inputs,
      std::vector<array>& outputs) override;

  /** The Jacobian-vector product. */
  std::vector<array> jvp(
      const std::vector<array>& primals,
      const std::vector<array>& tangents,
      const std::vector<int>& argnums) override;

  /** The vector-Jacobian product. */
  std::vector<array> vjp(
      const std::vector<array>& primals,
      const std::vector<array>& cotangents,
      const std::vector<int>& argnums,
      const std::vector<array>& outputs) override;

  /**
   * The primitive must know how to vectorize itself across
   * the given axes. The output is a pair containing the array
   * representing the vectorized computation and the axis which
   * corresponds to the output vectorized dimension.
   */
  std::pair<std::vector<array>, std::vector<int>> vmap(
      const std::vector<array>& inputs,
      const std::vector<int>& axes) override;

  /** The name of primitive. */
  const char* name() const override {
    return "Axpby";
  }

  /** Equivalence check **/
  bool is_equivalent(const Primitive& other) const override;

 private:
  float alpha_;
  float beta_;
};
```

### 24.2 Using the Primitive from an operation (verbatim)

```cpp
array axpby(
    const array& x, // Input array x
    const array& y, // Input array y
    const float alpha, // Scaling factor for x
    const float beta, // Scaling factor for y
    StreamOrDevice s /* = {} */ // Stream on which to schedule the operation
) {
  // Promote dtypes between x and y as needed
  auto promoted_dtype = promote_types(x.dtype(), y.dtype());

  // Upcast to float32 for non-floating point inputs x and y
  auto out_dtype = issubdtype(promoted_dtype, float32)
      ? promoted_dtype
      : promote_types(promoted_dtype, float32);

  // Cast x and y up to the determined dtype (on the same stream s)
  auto x_casted = astype(x, out_dtype, s);
  auto y_casted = astype(y, out_dtype, s);

  // Broadcast the shapes of x and y (on the same stream s)
  auto broadcasted_inputs = broadcast_arrays({x_casted, y_casted}, s);
  auto out_shape = broadcasted_inputs[0].shape();

  // Construct the array as the output of the Axpby primitive
  // with the broadcasted and upcasted arrays as inputs
  return array(
      /* const std::vector<int>& shape = */ out_shape,
      /* Dtype dtype = */ out_dtype,
      /* std::unique_ptr<Primitive> primitive = */
      std::make_shared<Axpby>(to_stream(s), alpha, beta),
      /* const std::vector<array>& inputs = */ broadcasted_inputs);
}
```

### 24.3 GPU back-end (verbatim — canonical Metal encoder API surface)

```cpp
template <typename T>
[[kernel]] void axpby_general(
    device const T* x [[buffer(0)]],
    device const T* y [[buffer(1)]],
    device T* out [[buffer(2)]],
    constant const float& alpha [[buffer(3)]],
    constant const float& beta [[buffer(4)]],
    constant const int* shape [[buffer(5)]],
    constant const int64_t* x_strides [[buffer(6)]],
    constant const int64_t* y_strides [[buffer(7)]],
    constant const int& ndim [[buffer(8)]],
    uint index [[thread_position_in_grid]]) {
  // Convert linear indices to offsets in array
  auto x_offset = elem_to_loc(index, shape, x_strides, ndim);
  auto y_offset = elem_to_loc(index, shape, y_strides, ndim);

  // Do the operation and update the output
  out[index] =
      static_cast<T>(alpha) * x[x_offset] + static_cast<T>(beta) * y[y_offset];
}
```

```cpp
instantiate_kernel("axpby_general_float32", axpby_general, float)
instantiate_kernel("axpby_general_float16", axpby_general, float16_t)
instantiate_kernel("axpby_general_bfloat16", axpby_general, bfloat16_t)
instantiate_kernel("axpby_general_complex64", axpby_general, complex64_t)
```

```cpp
/** Evaluate primitive on GPU */
void Axpby::eval_gpu(
    const std::vector<array>& inputs,
    std::vector<array>& outputs) {
  // Prepare inputs
  assert(inputs.size() == 2);
  auto& x = inputs[0];
  auto& y = inputs[1];
  auto& out = outputs[0];

  // Each primitive carries the stream it should execute on
  // and each stream carries its device identifiers
  auto& s = stream();
  // We get the needed metal device using the stream
  auto& d = metal::device(s.device);

  // Allocate output memory
  out.set_data(allocator::malloc(out.nbytes()));

  // Resolve name of kernel
  std::stream kname;
  kname = "axpby_general_" + type_to_name(out);

  // Load the metal library
  auto lib = d.get_library("mlx_ext", current_binary_dir());

  // Make a kernel from this metal library
  auto kernel = d.get_kernel(kname, lib);

  // Prepare to encode kernel
  auto& compute_encoder = mx::metal::get_command_encoder(s);
  compute_encoder.set_compute_pipeline_state(kernel);

  // Kernel parameters are registered with buffer indices corresponding to
  // those in the kernel declaration at axpby.metal
  int ndim = out.ndim();
  size_t nelem = out.size();

  // Encode input arrays to kernel
  compute_encoder.set_input_array(x, 0);
  compute_encoder.set_input_array(y, 1);

  // Encode output arrays to kernel
  compute_encoder.set_output_array(out, 2);

  // Encode alpha and beta
  compute_encoder.set_bytes(alpha_, 3);
  compute_encoder.set_bytes(beta_, 4);

  // Encode shape, strides and ndim
  compute_encoder.set_vector_bytes(x.shape(), 5);
  compute_encoder.set_vector_bytes(x.strides(), 6);
  compute_encoder.set_bytes(y.strides(), 7);
  compute_encoder.set_bytes(ndim, 8);

  // We launch 1 thread for each input and make sure that the number of
  // threads in any given threadgroup is not higher than the max allowed
  size_t tgp_size = std::min(nelem, kernel->maxTotalThreadsPerThreadgroup());

  // Fix the 3D size of each threadgroup (in terms of threads)
  MTL::Size group_dims = MTL::Size(tgp_size, 1, 1);

  // Fix the 3D size of the launch grid (in terms of threads)
  MTL::Size grid_dims = MTL::Size(nelem, 1, 1);

  // Launch the grid with the given number of threads divided among
  // the given threadgroups
  compute_encoder.dispatch_threads(grid_dims, group_dims);
}
```

> A few things to note about MLX and Metal before moving on. **MLX keeps track of the active
> `command_buffer` and the `MTLCommandBuffer` to which it is associated. We rely on
> `metal::get_command_encoder()` to give us the active metal compute command encoder instead of
> building a new one and calling `compute_encoder->end_encoding()` at the end. MLX adds kernels
> (compute pipelines) to the active command buffer until some specified limit is hit or the command
> buffer needs to be flushed for synchronization.**

### 24.4 Primitive transforms (verbatim)

```cpp
/** The Jacobian-vector product. */
std::vector<array> Axpby::jvp(
    const std::vector<array>& primals,
    const std::vector<array>& tangents,
    const std::vector<int>& argnums) {
  // Forward mode diff that pushes along the tangents
  // The jvp transform on the primitive can be built with ops
  // that are scheduled on the same stream as the primitive

  // If argnums = {0}, we only push along x in which case the
  // jvp is just the tangent scaled by alpha
  // Similarly, if argnums = {1}, the jvp is just the tangent
  // scaled by beta
  if (argnums.size() > 1) {
    auto scale = argnums[0] == 0 ? alpha_ : beta_;
    auto scale_arr = array(scale, tangents[0].dtype());
    return {multiply(scale_arr, tangents[0], stream())};
  }
  // If argnums = {0, 1}, we take contributions from both
  // which gives us jvp = tangent_x * alpha + tangent_y * beta
  else {
    return {axpby(tangents[0], tangents[1], alpha_, beta_, stream())};
  }
}
```

```cpp
/** The vector-Jacobian product. */
std::vector<array> Axpby::vjp(
    const std::vector<array>& primals,
    const std::vector<array>& cotangents,
    const std::vector<int>& argnums,
    const std::vector<int>& /* unused */) {
  // Reverse mode diff
  std::vector<array> vjps;
  for (auto arg : argnums) {
    auto scale = arg == 0 ? alpha_ : beta_;
    auto scale_arr = array(scale, cotangents[0].dtype());
    vjps.push_back(multiply(scale_arr, cotangents[0], stream()));
  }
  return vjps;
}
```

> Note, **a transformation does not need to be fully defined to start using the `Primitive`.**

```cpp
/** Vectorize primitive along given axis */
std::pair<std::vector<array>, std::vector<int>> Axpby::vmap(
    const std::vector<array>& inputs,
    const std::vector<int>& axes) {
  throw std::runtime_error("[Axpby] vmap not implemented.");
}
```

### 24.5 Extension directory layout (verbatim)

```
extensions
├── axpby
│   ├── axpby.cpp
│   ├── axpby.h
│   └── axpby.metal
├── mlx_sample_extensions
│   └── __init__.py
├── bindings.cpp
├── CMakeLists.txt
└── setup.py
```

### 24.6 Python bindings (nanobind)

```cpp
NB_MODULE(_ext, m) {
  m.doc() = "Sample extension for MLX";

  m.def(
      "axpby",
      &axpby,
      "x"_a,
      "y"_a,
      "alpha"_a,
      "beta"_a,
      nb::kw_only(),
      "stream"_a = nb::none(),
      R"(
        Scale and sum two vectors element-wise
        ``z = alpha * x + beta * y``
        ...
```

### 24.7 CMake for extensions (verbatim)

```cmake
# Add library
add_library(mlx_ext)

# Add sources
target_sources(
    mlx_ext
    PUBLIC
    ${CMAKE_CURRENT_LIST_DIR}/axpby/axpby.cpp
)

# Add include headers
target_include_directories(
    mlx_ext PUBLIC ${CMAKE_CURRENT_LIST_DIR}
)

# Link to mlx
target_link_libraries(mlx_ext PUBLIC mlx)
```

> We also need to build the attached Metal library. For convenience, we provide a
> **`mlx_build_metallib()`** function that builds a `.metallib` target given sources, headers,
> destinations, etc. (**defined in `cmake/extension.cmake` and automatically imported with MLX
> package**).

```cmake
# Build metallib
if(MLX_BUILD_METAL)

  mlx_build_metallib(
      TARGET mlx_ext_metallib
      TITLE mlx_ext
      SOURCES ${CMAKE_CURRENT_LIST_DIR}/axpby/axpby.metal
      INCLUDE_DIRS ${PROJECT_SOURCE_DIR} ${MLX_INCLUDE_DIRS}
      OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
  )

  add_dependencies(
      mlx_ext
      mlx_ext_metallib
  )

endif()
```

```cmake
nanobind_add_module(
  _ext
  NB_STATIC STABLE_ABI LTO NOMINSIZE
  NB_DOMAIN mlx
  ${CMAKE_CURRENT_LIST_DIR}/bindings.cpp
)
target_link_libraries(_ext PRIVATE mlx_ext)

if(BUILD_SHARED_LIBS)
  target_link_options(_ext PRIVATE -Wl,-rpath,@loader_path)
endif()
```

### 24.8 setuptools (verbatim)

```python
from mlx import extension
from setuptools import setup

if __name__ == "__main__":
    setup(
        name="mlx_sample_extensions",
        version="0.0.0",
        description="Sample C++ and Metal extensions for MLX primitives.",
        ext_modules=[extension.CMakeExtension("mlx_sample_extensions._ext")],
        cmdclass={"build_ext": extension.CMakeBuild},
        packages=["mlx_sample_extensions"],
        package_data={"mlx_sample_extensions": ["*.so", "*.dylib", "*.metallib"]},
        extras_require={"dev":[]},
        zip_safe=False,
        python_requires=">=3.8",
    )
```

> **Note**: We treat `extensions/mlx_sample_extensions` as the package directory even though it only
> contains a `__init__.py` to ensure the following:
> - **`mlx.core` must be imported before importing `_ext`**
> - The C++ extension library and the metal library are co-located with the python bindings and copied
>   together if the package is installed

Build commands:

```bash
pip install -r requirements.txt
python setup.py build_ext -j8 --inplace   # run inside extensions/
python -m pip install .                    # run inside extensions/
```

Resulting layout:

```
extensions
├── mlx_sample_extensions
│   ├── __init__.py
│   ├── libmlx_ext.dylib # C++ extension library
│   ├── mlx_ext.metallib # Metal library
│   └── _ext.cpython-3x-darwin.so # Python Binding
…
```

Usage:

```python
import mlx.core as mx
from mlx_sample_extensions import axpby

a = mx.ones((3, 4))
b = mx.ones((3, 4))
c = axpby(a, b, 4.0, 2.0, stream=mx.cpu)

print(f"c shape: {c.shape}")
print(f"c dtype: {c.dtype}")
print(f"c is correct: {mx.all(c == 6.0).item()}")
```

---

## 25. Cross-cutting gotchas / footguns catalogue

Everything below is grounded in a quote already recorded above.

**Lazy eval / eval**
- Printing, `np.array(...)`, `memoryview`, `.item()`, and `mx.save*` all force evaluation. Placing
  `print(loss)` before `mx.eval(loss, params)` causes a **partial evaluation of only the forward pass**.
- Scalar arrays in `if` cause evaluation.
- Repeated `mx.eval` on already-evaluated arrays is a no-op.
- `mx.async_eval` is explicitly labelled **experimental**.

**Compile**
- Cannot `print` inside a compiled function — placeholder arrays crash.
- Captured (non-argument) arrays are **frozen constants**; use `inputs=` / `outputs=`.
- Recompiles on: shape change, ndim change, dtype change, arity change.
- `shapeless=True` still recompiles on **ndim** or **dtype** change; can throw at compile time for
  un-shapeless-able functions; silently mis-specializes shape-derived Python arithmetic
  (`x.shape[0]*x.shape[1]`) — use `flatten(0, 1)`.
- Compiling an anonymous lambda inside a loop recompiles every iteration.
- Transform-of-compiled-function is not compiled by default.
- With `nn.Dropout` etc., `mx.random.state` must be in the captured state.

**Indexing**
- **No bounds checking. OOB indexing is undefined behavior** (because GPU exceptions can't propagate).
- Boolean mask indexing is **assignment-only**.
- Slicing copies (unlike NumPy views).
- Duplicate-index assignment is **nondeterministic**; use `x.at[idx].add(y)`.
- `numpy.nonzero()` and single-arg `numpy.where()` are unsupported (data-dependent output shapes).

**NumPy / framework interop**
- `bfloat16` → must `.astype(mx.float32)` before `np.array`; else
  `Item size 2 for PEP 3118 buffer format string does not match the dtype V item size 0.`
- NumPy `float64` silently becomes MLX `float32`.
- `np.array(x, copy=False)` views bypass autodiff — gradients silently wrong.
- PyTorch MPS: private Metal buffers force a copy; `copy=False` raises if a copy would be needed;
  **PyTorch ≥ 2.12 uses shared storage** for MPS tensors, older versions may not.
- DLPack conversion **does not synchronize pending Metal work** — call `torch.mps.synchronize()` /
  `mx.eval()` first.

**Custom Metal kernels**
- Each `mx.fast.metal_kernel(...)` construction builds a **new Metal library** (possibly JIT) — hoist it
  out of hot paths.
- `source` is the **body only**.
- `grid` is in **threads**, not threadgroups (`dispatchThreads` semantics).
- `ensure_row_contiguous=True` (default) may **silently copy** inputs.
- Output arrays are always row contiguous.
- Default `math_mode` is `"safe"` — switching to `relaxed`/`fast` breaks `exp(-inf) == 0`, which breaks
  masked softmax.
- `atomic_outputs=True` + `init_value=0` are required together for scatter-style backward kernels.
- `precompiled_cuda_kernel` defaults `ensure_row_contiguous=False` (opposite of the other two) and
  leaves outputs **uninitialized** unless `init_value` is given.

**Distributed**
- `mx.distributed` ops are **no-ops** at group size 1 — silently non-distributed.
- `init()` is **sticky**: the first successfully-initialized backend is returned by later bare `init()`
  calls, even if you asked for `any`.
- Ring backend does **not** support arbitrary `send`/`recv`.
- JACCL requires **macOS 26.2+**, Thunderbolt 5, a **fully connected mesh**, and `rdma_ctl enable` run
  **from macOS Recovery** (cannot be done remotely).
- JACCL/ring still need the Thunderbolt bridge disabled and per-cable isolated subnets.
- `MLX_METAL_FAST_SYNCH=1` is described as "pretty critical" for low-latency (JACCL) communication.
- `sum_scatter` is **NCCL-only** today.
- `mlx.launch --hosts` with the ring backend accepts **IPs only**, not hostnames.
- Homebrew/pip MPI needs `DYLD_LIBRARY_PATH` and possibly `MPI_LIBNAME`.

**Export**
- `.mlxfn` format is **experimental**; "Functions exported with older versions of MLX may not be
  compatible with future versions."
- Imported functions **always return a tuple**.
- Shapes/dtypes/kwarg names must match exactly (unless `shapeless=True`).
- Un-evaluated enclosed arrays bake their **producing computation** (e.g. random init) into the file —
  always `mx.eval(model.parameters())` first.

**Memory**
- `set_wired_limit` needs macOS 15+ and a raised system limit via
  `sudo sysctl iogpu.wired_limit_mb=<MB>`.
- `set_cache_limit(0)` disables the cache entirely.
- `get_active_memory()` excludes cached buffers, so it won't match Activity Monitor.

**Build**
- `MLX_METAL_JIT=ON` shrinks the binary but adds a cold-start of "a few hundred millisecond to a few
  seconds"; the kernel cache **persists across reboots**.
- x86-via-Rosetta shells break the build; `cmake --system-information | grep CMAKE_HOST_SYSTEM_PROCESSOR`
  must say `arm64`.
- `MLX_METAL_DEBUG=ON` for captures; `MTL_CAPTURE_ENABLED=1` at runtime; the trace path must not exist.
- Metal logging needs Metal 3.2 (macOS 15+/iOS 18+) and a `DEBUG=1` build.

---

## 26. Environment variables — complete list found on the site

| Variable | Where documented | Effect |
|---|---|---|
| `MLX_DISABLE_COMPILE` | `usage/compile.html` | globally disable `mx.compile` |
| `MLX_METAL_FAST_SYNCH=1` | `usage/distributed.html` | faster CPU↔GPU synchronization; "pretty critical" for JACCL |
| `MLX_RANK` | `usage/distributed.html` | 0-based rank (ring, jaccl, nccl) |
| `MLX_WORLD_SIZE` | `usage/distributed.html` | total processes (nccl) |
| `MLX_HOSTFILE` | `usage/distributed.html` | ring: JSON of `["ip:port", …]` lists |
| `MLX_RING_VERBOSE=1` | `usage/distributed.html` | extra ring logging |
| `MLX_JACCL_COORDINATOR` | `usage/distributed.html` | IP:port for rank-0 RDMA rendezvous |
| `MLX_IBV_DEVICES` | `usage/distributed.html` | JSON matrix of ibverbs device names |
| `NCCL_HOST_IP`, `NCCL_PORT` | `usage/distributed.html` | NCCL rendezvous |
| `CUDA_VISIBLE_DEVICES` | `usage/distributed.html` | local GPU index per process |
| `DYLD_LIBRARY_PATH` | `usage/distributed.html` | needed for brew/pip MPI |
| `MPI_LIBNAME` | `usage/distributed.html` | non-standard MPI dylib filename |
| `MTL_CAPTURE_ENABLED=1` | `dev/metal_debugger.html` | required for `mx.metal.start_capture` |
| `MTL_LOG_LEVEL=MTLLogLevelDebug` | `dev/metal_logging.html` | Metal shader log level |
| `MTL_LOG_TO_STDERR=1` | `dev/metal_logging.html` | forward Metal logs to stderr |
| `DEBUG=1` | `dev/metal_logging.html` | debug build (`DEBUG=1 python -m pip install -e .`) |
| `DEVELOPER_DIR` | `install.html` | pick a specific Xcode |
| `CMAKE_ARGS` | `install.html`, `dev/metal_debugger.html` | pass CMake flags to `pip install` |
| `METAL_PATH` (preprocessor constant, not env) | `install.html` | path to `mlx.metallib` for static links |

---

## 27. Source inventory — every URL I actually fetched and read this session

All under base `https://ml-explore.github.io/mlx/build/html/`.

**Top level**
- `index.html`
- `install.html`

**Usage**
- `usage/quick_start.html`
- `usage/lazy_evaluation.html`
- `usage/unified_memory.html`
- `usage/indexing.html`
- `usage/saving_and_loading.html`
- `usage/function_transforms.html`
- `usage/compile.html`
- `usage/numpy.html`
- `usage/distributed.html`
- `usage/launching_distributed.html`
- `usage/using_streams.html`
- `usage/export.html`

**Examples**
- `examples/linear_regression.html` (downloaded, skimmed)
- `examples/mlp.html` (downloaded, skimmed)
- `examples/llama-inference.html` (downloaded, skimmed)
- `examples/data_parallelism.html` (read in full)
- `examples/tensor_parallelism.html` (read in full)

**Dev / Further Reading**
- `dev/extensions.html`
- `dev/metal_debugger.html`
- `dev/metal_logging.html`
- `dev/custom_metal_kernels.html`
- `dev/mlx_in_cpp.html`

**C++**
- `cpp/ops.html`

**Python API index pages**
- `python/array.html`, `python/data_types.html`, `python/devices_and_streams.html`,
  `python/export.html`, `python/ops.html`, `python/random.html`, `python/transforms.html`,
  `python/fast.html`, `python/fft.html`, `python/linalg.html`, `python/metal.html`,
  `python/cuda.html`, `python/memory_management.html`, `python/nn.html`, `python/nn/layers.html`,
  `python/nn/functions.html`, `python/nn/losses.html`, `python/nn/init.html`,
  `python/nn/module.html`, `python/nn/distributed.html`, `python/optimizers.html`,
  `python/optimizers/optimizer.html`, `python/optimizers/common_optimizers.html`,
  `python/optimizers/schedulers.html`, `python/distributed.html`, `python/tree_utils.html`,
  `python/printoptions.html`

**Python `_autosummary` detail pages (read for exact signatures)**

`python/_autosummary/`:
`mlx.core.compile`, `mlx.core.grad`, `mlx.core.value_and_grad`, `mlx.core.vmap`, `mlx.core.vjp`,
`mlx.core.jvp`, `mlx.core.custom_function`, `mlx.core.checkpoint`, `mlx.core.eval`,
`mlx.core.async_eval`, `mlx.core.disable_compile`, `mlx.core.enable_compile`,
`mlx.core.export_function`, `mlx.core.import_function`, `mlx.core.exporter`,
`mlx.core.export_to_dot`, `mlx.core.fast.metal_kernel`, `mlx.core.fast.cuda_kernel`,
`mlx.core.fast.precompiled_cuda_kernel`, `mlx.core.fast.scaled_dot_product_attention`,
`mlx.core.fast.rope`, `mlx.core.fast.rms_norm`, `mlx.core.fast.layer_norm`,
`mlx.core.distributed.init`, `mlx.core.distributed.Group`, `mlx.core.distributed.is_available`,
`mlx.core.distributed.all_sum`, `mlx.core.distributed.all_gather`, `mlx.core.distributed.all_max`,
`mlx.core.distributed.all_min`, `mlx.core.distributed.send`, `mlx.core.distributed.recv`,
`mlx.core.distributed.recv_like`, `mlx.core.distributed.sum_scatter`,
`mlx.core.metal.start_capture`, `mlx.core.metal.stop_capture`, `mlx.core.metal.device_info`,
`mlx.core.metal.is_available`, `mlx.core.cuda.is_available`, `mlx.core.set_memory_limit`,
`mlx.core.set_cache_limit`, `mlx.core.set_wired_limit`, `mlx.core.clear_cache`,
`mlx.core.get_active_memory`, `mlx.core.get_peak_memory`, `mlx.core.reset_peak_memory`,
`mlx.core.get_cache_memory`, `mlx.core.new_stream`, `mlx.core.new_thread_local_stream`,
`mlx.core.set_default_stream`, `mlx.core.default_stream`, `mlx.core.stream`,
`mlx.core.synchronize`, `mlx.core.device_info`, `mlx.core.device_count`, `mlx.core.clear_streams`,
`mlx.core.Stream`, `mlx.core.Device`, `mlx.core.quantize`, `mlx.core.dequantize`,
`mlx.core.quantized_matmul`, `mlx.core.qqmm`, `mlx.core.to_fp8`, `mlx.core.segmented_mm`,
`mlx.core.hadamard_transform`, `mlx.core.einsum`, `mlx.core.load`, `mlx.core.save_safetensors`,
`mlx.core.random.key`, `mlx.core.random.split`, `mlx.core.random.normal`,
`mlx.core.random.categorical`, `mlx.core.array.at`, `mlx.nn.quantize`, `mlx.nn.value_and_grad`,
`mlx.nn.average_gradients`, `mlx.nn.fsdp_apply_gradients`, `mlx.utils.tree_flatten`,
`mlx.utils.tree_map`, `mlx.optimizers.clip_grad_norm`

`python/optimizers/_autosummary/`:
`mlx.optimizers.Muon`, `mlx.optimizers.MultiOptimizer`, `mlx.optimizers.AdamW`,
`mlx.optimizers.SGD`, `mlx.optimizers.Adam`, `mlx.optimizers.Adafactor`,
`mlx.optimizers.Optimizer.update`, `mlx.optimizers.Optimizer.state`,
`mlx.optimizers.cosine_decay`, `mlx.optimizers.join_schedules`

`python/nn/_autosummary/`:
`mlx.nn.Module.load_weights`, `mlx.nn.Module.set_dtype`, `mlx.nn.Module.freeze`,
`mlx.nn.Module.state`, `mlx.nn.Module.update`, `mlx.nn.Linear`, `mlx.nn.QuantizedLinear`,
`mlx.nn.RoPE`, `mlx.nn.MultiHeadAttention`, `mlx.nn.Upsample`,
`mlx.nn.layers.distributed.shard_linear`, `mlx.nn.layers.distributed.shard_inplace`

### Pages I could NOT get / did not fully read

- **Nothing was blocked.** No page returned thin or blocked content; `curl` + a local HTML→text
  extractor got the full rendered body of every page attempted. No need for `r.jina.ai`, sosumi.ai, or
  a real browser.
- I *downloaded but only skimmed* (not exhaustively transcribed): `examples/linear_regression.html`,
  `examples/mlp.html`, `examples/llama-inference.html`, `python/array.html`,
  `python/data_types.html`, `python/nn/module.html` (individual method pages beyond
  `load_weights`/`set_dtype`), `python/nn/functions.html` detail pages, and the ~350 remaining
  per-op `_autosummary` pages under `python/_autosummary/`. Their **index-level one-line signatures**
  are transcribed above; the per-op prose is not.
- The **404s I hit** were my own path error, not missing docs: `python/_autosummary/mlx.optimizers.*`
  and `python/_autosummary/mlx.nn.*` return GitHub Pages 404s; the real paths are
  `python/optimizers/_autosummary/…` and `python/nn/_autosummary/…`.

---

## 28. Open questions / UNVERIFIED

1. **Version currency.** The site serves **MLX 0.32.0** at the `build/html/` path. I found no version
   switcher and did not verify whether a newer MLX exists on PyPI/GitHub as of 2026-07-27. Anything
   here should be re-checked against the installed wheel before being written into a guide as
   "current".
2. **`mx.fast.metal_kernel` returned-callable signature is UNVERIFIED as a formal signature.** The docs
   never publish it. The kwargs I list (`inputs`, `template`, `grid`, `threadgroup`, `output_shapes`,
   `output_dtypes`, `init_value`, `verbose`) are *inferred from every example on the site*. Defaults and
   whether they are keyword-only are unknown. Also unknown: whether `stream=` is accepted.
3. **`custom_function.vjp` arity.** Docs show both `f_vjp(primals, cotangent, output)` and
   `f_vjp(x, dx, fx)`. Three positional args is consistent across the Metal-kernel page
   (`grid_sample_vjp(primals, cotangent, _)`), but I did not verify against source.
4. **`mlx.launch` full flag set is INCOMPLETE.** The docs mention flags in prose; there is no `--help`
   dump on the site. Flags like `--env` are shown only in one example. Actual argparse surface
   unverified.
5. **`mlx.distributed_config` full flag set** likewise unverified beyond
   `--verbose --hosts --backend --over --auto-setup --output --dot`.
6. **JACCL specifics.** macOS 26.2 / Thunderbolt 5 / `rdma_ctl enable` / `ibv_devices` are quoted
   verbatim, but I could not verify any of it against a machine or an Apple doc. Whether `rdma_ctl` is
   Apple-shipped or MLX-shipped is not stated.
7. **`MLX_BUILD_CUDA`** is documented in prose but is absent from the Build Options table — its default
   is UNVERIFIED (presumably OFF).
8. **`mx.random.state`** is referenced by the compile page but has no autosummary entry I found; its
   type and API are unverified.
9. **`nn.Module.state`** — referenced heavily in compile examples (`state = [model.state,
   optimizer.state]`) but I did not read its detail page. Its exact semantics (does it include
   buffers? frozen params?) are unverified.
10. **`segments` parameter of `shard_linear`** ("The segments to use. Default: `1`") is not explained
    anywhere on the site. Meaning unverified.
11. **`QQLinear`** has only a one-line description; its constructor kwargs are unverified.
12. **`softmax(..., bool precise)`** exists in C++ but I did not confirm how/whether it is exposed in
    Python (`mx.softmax` signature not read in detail).
13. **`Stream` class detail page** (`python/_autosummary/mlx.core.Stream.html`) actually redirects/renders
    the content of `mlx.core.stream` (the context manager). The `Stream` class's own attributes
    (`.device`, `.index`?) are unverified.
14. **Per-op autosummary prose for ~350 ops** was not read. Argument names in §17.10 come from the index
    page's abbreviated signatures only.
15. **`mlx.core.exporter` returns `mlx.core.FunctionExporter`** — that class's own API (beyond being a
    context manager and callable) is undocumented on the site.
16. Whether **`mx.compile`'s cache is keyed on the Python function object** (the doc's
    `mx.compile(fun)(x, y)` "Not compiled again" example implies yes) is inferred, not stated.
