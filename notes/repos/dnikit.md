# apple/dnikit — Data and Network Introspection Kit (DNIKit)

**Repo path (local clone, `--depth 50`):** `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__dnikit`
**Upstream:** https://github.com/apple/dnikit · **Docs:** https://apple.github.io/dnikit
**Version:** `2.0.0` (all three packages pinned together) · **License:** Apache-2.0
**Last 3 commits (`git log --format='%H %ad %an %s' --date=iso`):**

```
2f39056311d6e0fbbe4e5f73da3767a5b5070dac 2026-07-09 14:21:09 -0400 Kiwi                 Handle Keras 3 tensor metadata in TF2 models (#4)
b44b14f87507b0d305b7cc7bbcf7f091717485da 2023-09-06 17:14:56 -0400 Megan Maher Welsh    Remove frozen requirements file.
e9f4a9a8380b628a36b68b2251724a9adfab1b21 2023-07-25 14:17:53 -0700 Megan Maher Welsh    DNIKit 2.0.0 Release.
```

> **Positioning note for the 2026 Apple AI stack guides.** DNIKit is a *pure-Python*, *offline / desktop* toolkit. It is **not** Swift, not on-device, not Core ML–integrated (there is **no** CoreML backend in this repo — see "Model backends" below; `coremltools` appears nowhere). Its role in an Apple on-device ML workflow is the **pre-shipping data-quality and model-compression stage**: introspect a trained TF/Keras (or arbitrary) model's *intermediate activations* against your dataset → find duplicate/rare/mislabeled data (`DatasetReport`, `Familiarity`, `Duplicates`), find dead units (`IUA`), and get a compression *recipe* (`PFA`) telling you how many filters each layer really needs before you retrain and convert to Core ML / ship on device. From `CONTRIBUTING.md`: *"This project was released to share our work and support our publications in this area, but there are limited plans for future development of the repository."*

---

## 1. Repository layout

```
apple__dnikit/
├── CHANGELOG.md            # 2.0.0 (2023-08-03) + list of private 0.2.1 → 1.7.0 releases
├── CITATION.cff            # version 2.0.0, date-released 2023-06-19
├── CODE_OF_CONDUCT.md
├── CODEOWNERS              # *  @mmaherwelsh @davidkoski
├── CONTRIBUTING.md
├── Makefile                # install / test / doc / clean targets (see §3)
├── conftest.py             # adds --runslow flag; skips @pytest.mark.slow by default
├── mypy.ini                # strict-ish: disallow_untyped_calls/defs, check_untyped_defs
├── pytest.ini              # testpaths, --mypy --flake8 --cov src --cov-fail-under 80
├── .bumpversion.cfg        # current_version = 2.0.0, 6 files touched
├── .gitattributes          # *.gif/*.png/*.jpg/*.jpeg -> git LFS
├── docs/                   # Sphinx (sphinx-book-theme + nbsphinx)
│   ├── index.rst
│   ├── conf.py
│   ├── general/{installation,support,example_notebooks}.rst
│   ├── how_to/{dnikit_concepts,connect_model,connect_data,introspect}.rst
│   ├── introspectors/{data_introspection,model_introspection}.rst (+ subdirs)
│   ├── utils/{data_producers,pipeline_stages}.rst
│   ├── api/{index, dnikit/{index,base,processors,introspectors,exceptions,typing}, tensorflow, torch}
│   ├── dev/contributing.rst · reference/{how_to_cite,changelog}.rst
│   ├── notebooks/           # DUPLICATE of top-level notebooks/ (nbsphinx renders these)
│   └── img/, _static/custom.css
├── notebooks/
│   ├── data_introspection/{dataset_report, duplicates, dimension_reduction,
│   │                       familiarity_for_rare_data_discovery,
│   │                       familiarity_for_dataset_distribution}.ipynb
│   └── model_introspection/{principal_filter_analysis, inactive_unit_analysis}.ipynb
└── src/
    ├── dnikit/             # core package (pure python, numpy/sklearn/annoy)
    ├── dnikit_tensorflow/  # TF1 + TF2/Keras model loading, sample models & datasets
    └── dnikit_torch/       # PyTorch <-> DNIKit Producer/Dataset adaptors
```

Three **separately-installable but version-locked** distributions, each with its own `pyproject.toml` (flit build backend):
`dnikit`, `dnikit_tensorflow`, `dnikit_torch`.

---

## 2. Packaging, versions, dependency constraints

### 2.1 `src/dnikit/pyproject.toml` (verbatim, key parts)

```toml
[build-system]
requires = ["flit_core >=2,<4"]
build-backend = "flit_core.buildapi"

[tool.flit.metadata]
module = "dnikit"
home-page = "https://github.com/apple/dnikit"
license = "Apache-2.0"
author = "Apple, Inc."
author-email = "dnikit-symphony-oss@group.apple.com"

requires-python = ">=3.7"
requires = [
    "annoy",  # duplicates -- approximate nearest neighbor oh yeah
    "numpy",
    "scikit-learn",
    "typing_extensions; python_version < '3.8'",
]

[tool.flit.metadata.requires-extra]
image          = ["opencv-python-headless", "Pillow"]
dimreduction   = ["umap-learn", "pacmap"]
dataset-report = ["pandas", "umap-learn", "pacmap"]

tensorflow      = ["dnikit_tensorflow[tf2]==2.0.0"]
tensorflow1     = ["dnikit_tensorflow[tf1]==2.0.0"]
tensorflow1-gpu = ["dnikit_tensorflow[tf1-gpu]==2.0.0"]
torch           = ["dnikit_torch==2.0.0"]

test = ["flake8 < 5.0.0", "importlib-metadata < 4.3; python_version < '3.8'",
        "mypy", "pytest", "pytest-cov", "pytest-flake8", "pytest-mypy",
        "pytest-xdist[psutil]", "pytest-timeout", "flake8-copyright", "bumpversion"]
doc  = ["ipykernel","jupyter_client","nbsphinx","pandoc","sphinx","sphinx-book-theme",
        "matplotlib","pandas","jupyter-datatables","seaborn"]
notebook = ["notebook < 7.0.0", "matplotlib", "pandas", "jupyter-datatables", "plotly"]
complete = ["dnikit[image]==2.0.0","dnikit[dimreduction]==2.0.0","dnikit[duplicates]==2.0.0",
            "dnikit[dataset-report]==2.0.0","dnikit[tensorflow]==2.0.0","dnikit[notebook]==2.0.0"]
```

**Gotchas found in the metadata itself:**
- `complete` references `dnikit[duplicates]==2.0.0` but **there is no `duplicates` extra defined** in `requires-extra`. This is a latent packaging bug — `pip install "dnikit[complete]"` would attempt to resolve a non-existent extra. (`docs/dev/contributing.rst:56` also claims `make install` installs `dnikit[...,duplicates]`.) `annoy` (the duplicates dependency) is in the **base** requires, so functionally nothing is missing.
- `complete` does **not** include `torch`, even though `docs/general/installation.rst:101-103` claims it installs "`notebook`, `image`, `dimreduction`, `dataset-report`, `tensorflow`, & `torch` options."
- Classifiers list Python 3.7–3.10 only. `requires-python = ">=3.7"`.
- `scipy` is used (`scipy.stats.entropy`, `scipy.stats.multivariate_normal`, `scipy.special.logsumexp`) but is **not declared** — it arrives transitively via `scikit-learn`.

### 2.2 `src/dnikit_tensorflow/pyproject.toml`

```toml
requires = ["dnikit==2.0.0"]

[tool.flit.metadata.requires-extra]
tf2 = ["tensorflow"]                     # unpinned!
tf1 = ["numpy<1.19", "protobuf<4.0", "Keras<2.4", "h5py<3.0", "tensorflow<2.0"]
tf1-gpu = ["numpy<1.19", "protobuf<4.0", "Keras<2.4", "h5py<3.0", "tensorflow-gpu<2.0"]
```

`tf2` is an **unpinned** `tensorflow` requirement — this is exactly why the Keras 3 breakage (issue #2 / PR #4) happened; see §8.

### 2.3 `src/dnikit_torch/pyproject.toml`

```toml
requires = ["dnikit==2.0.0", "torch"]
[tool.flit.metadata.requires-extra]
test = ["torchvision"]
```

### 2.4 Version-sync assertion (runtime)

`src/dnikit_tensorflow/dnikit_tensorflow/__init__.py:34-38`:

```python
# Raise error if dnikit and dnikit_tensorflow versions are out of sync
assert __version__ == dnikit.__version__, (
    f'dnikit_tensorflow v{__version__} and '
    f'dnikit v{dnikit.__version__} should be the same versions.'
)
```

Same pattern in `src/dnikit_torch/dnikit_torch/__init__.py:32-35`. **Mixing package versions raises `AssertionError` at import time.**

`.bumpversion.cfg` bumps: the three `pyproject.toml`s + the three `__init__.py`s.

---

## 3. Install / build / test — exact commands

### Install (user)

```shell
pip install -U pip wheel
pip install dnikit                       # base
pip install "dnikit[notebook]"           # to run example notebooks
pip install "dnikit[complete]"           # base + TF2 + notebook (see extras bug above)
pip install "dnikit[tensorflow]"         # TF2
pip install "dnikit[tensorflow1]"        # TF1 CPU (needs Python <= 3.7)
pip install "dnikit[tensorflow1-gpu]"    # TF1 GPU
pip install "dnikit[torch]"
pip install "dnikit[dataset-report]"     # pandas + umap-learn + pacmap
pip install "dnikit[image]"              # opencv-python-headless + Pillow
pip install "dnikit[dimreduction]"       # umap-learn + pacmap

jupyter notebook                         # launch examples
```

Environment (docs/general/installation.rst):
- "DNIKit currently supports Python version 3.7 or greater for macOS or Linux. **Python 3.9 is recommended.** Note: to run TensorFlow 1, install Python 3.7."
- Ubuntu prerequisites: `sudo apt install -y python3.9-dev python3.9-venv python3.9-tk` and `sudo apt-get install -y libsm6 libxext6 libxrender-dev libgl1-mesa-glx`.
- **Python 3.9.7 is explicitly incompatible** (`docs/general/support.rst:91-97`): *"There is a bug in Python 3.9.7 that makes this version incompatible with DNIKit... this bug causes dataclasses that inherit from Protocols to have an incorrect `__init__` function. Dataclasses and Protocols are used throughout DNIKit, so DNIKit will fail on Python 3.9.7."* (cpython issue 89244)

### Developer install / test (`Makefile`)

```make
components := dnikit dnikit_tensorflow dnikit_torch
export PIP_INDEX_URL := https://pypi.org/simple

install: cmd = install -s --deps=develop --extras=notebook,image,dimreduction,dataset-report,tf2
install-tf1-gpu: cmd = install -s --deps=develop --extras=notebook,image,dimreduction,dataset-report,tf1-gpu
install-tf1: cmd = install -s --deps=develop --extras=notebook,image,dimreduction,dataset-report,tf1

$(components):
	@pip install -U flit$(FLIT_VER) flit_core$(FLIT_VER)
	@flit -f src/$@/pyproject.toml $(cmd)

uninstall:
	@pip uninstall --yes $(components)
```

Targets: `make all` (== `install`), `make install`, `make install-tf1`, `make install-tf1-gpu`, `make uninstall`,
`make test` (`test-pytest` + `test-notebooks`), `make test-all` (`pytest --runslow --durations=10`),
`make test-pytest`, `make test-pytest-all`, `make test-smoke` (`pytest -m "not regression"`),
`make test-notebooks`, `make doc`, `make clean`.

Notebook "test" is a **static type check**, not execution:

```make
test-notebooks:
	@jupyter nbconvert --to python --output-dir notebooks/.verify notebooks/*/*.ipynb
	@mypy notebooks/.verify
```

`pytest.ini` addopts (**every pytest run also runs mypy + flake8 + coverage**):

```ini
[pytest]
testpaths = src/dnikit/  src/dnikit_tensorflow/  src/dnikit_torch/
filterwarnings = error::dnikit.exceptions.DNIKitDeprecationWarning
addopts =
    --mypy --flake8 --junit-xml=junit.xml -s
    --cov src --cov-fail-under 80 --cov-report html:coverage
    --strict-markers -rs
markers = regression, slow
flake8-max-line-length = 100
```

`conftest.py` adds `--runslow`; without it, `@pytest.mark.slow` tests are skipped.

Docs build: `make doc` → `docs/_build/html/index.html`. Sphinx extensions (docs/conf.py): autodoc, doctest, todo, coverage, viewcode, autosectionlabel, napoleon, intersphinx, nbsphinx. `nbsphinx_execute = 'always'`, `nbsphinx_timeout = 600`, `nbsphinx_allow_errors = True`. **A clean docs build re-executes every notebook** (contributing.rst warns about this).

Targeted test invocation used in PR #4 (Windows PowerShell, from the commit message — useful because it shows how to bypass the mypy/flake8 addopts):

```powershell
$env:PYTHONPATH='src/dnikit;src/dnikit_tensorflow'; python -m pytest -o addopts= `
  src/dnikit_tensorflow/tests/test_tf2_model_loaders.py::test_get_tensor_dtype_and_shape_without_type_spec `
  src/dnikit_tensorflow/tests/test_tf2_model_loaders.py::test_convert_tf_operation_uses_layer_metadata_when_output_name_is_generic `
  src/dnikit_tensorflow/tests/test_tf2_model_loaders.py::test_tf_load_from_memory -q
```

---

## 4. Core architecture: Producer → PipelineStage → Introspector

From `docs/how_to/dnikit_concepts.rst`:

> "DNIKit begins with a `Producer` that is in charge of generating `Batches` of data... DNIKit only loads, processes and consumes data when it needs to. This is known as **lazy evaluation**... A `pipeline` is a composition of `Batch` transformations that we call `PipelineStages`... Finally, DNIKit's `Introspectors` will analyze input `Batches` (usually `Batches` of model responses)."

**Nothing computes until `<Introspector>.introspect(...)` is called.** `pipeline()` only builds the graph.

### 4.1 `Producer` protocol — `src/dnikit/dnikit/base/_producer.py:23-71`

```python
class Producer(t.Protocol):
    def __call__(self, batch_size: int) -> t.Iterable[Batch]:
        """All Producers should yield at least one Batch of size batch_size.
           The last of the batches is allowed to have a size smaller than batch_size."""
        ...
```

Two implementation styles (verbatim from the docstring, `_producer.py:34-56`):

```python
# Implement a Producer as a free function
def simple_producer(batch_size: int) -> t.Iterable[Batch]:
    for i in range(100):
        data = numpy.random.randn(batch_size, 10)
        yield Batch({"input": data})

# Implement a Producer as a class
class ClassProducer(Producer):
    def __init__(self):
        self._dims = (10, 1)
    def __call__(self, batch_size: int) -> t.Iterable[Batch]:
        for i in range(100):
            data = numpy.random.randn(batch_size, *self._dims)
            yield Batch({"input": data})
```

> **Warning (verbatim, `_producer.py:58-62`):** "Make sure to have a finite number of batches the `Producer` will generate, as some `Introspector` instances will try to consume all the batches of the producer and the program will stop responding indefinitely if there are infinite batches."

Helpers in the same file:
- `peek_first_batch(producer: Producer, batch_size: int = 1) -> Batch` (public, `_producer.py:147`) — the primary debugging tool.
- `_accumulate_batches(producer, *, batch_size: int = 1024) -> Batch` (private, `:74`) — loads **everything** into RAM; raises `DNIKitException("Producer did not produce any batches")` on `ValueError`. Used by `Familiarity.Strategy.GMM` and `Duplicates.introspect`.
- `_resize_batches(batches: t.Iterable[Batch]) -> Producer` (`:94`) — re-chunks batches; used by `CachedProducer` and `StubProducer`.
- `_produce_elements(producer, batch_size=32) -> t.Iterable[Batch.ElementType]` (`:163`).

### 4.2 `PipelineStage` + `pipeline()` — `src/dnikit/dnikit/base/_pipeline.py`

```python
class PipelineStage(_Logged, abc.ABC):
    def _pipeline(self, producer: Producer) -> Producer:      # :43  (override rarely)
        batch_processor = self._get_batch_processor()
        def new_producer(batch_size: int) -> t.Iterable[Batch]:
            for batch in producer(batch_size):
                yield batch_processor(batch)
        return new_producer

    @abc.abstractmethod
    def _get_batch_processor(self) -> t.Callable[[Batch], Batch]: ...   # :59
```

> **Warning (verbatim, `_pipeline.py:67-72`):** "The batch processor **MUST be stateless**. That is, its outputs must only depend on the input `batch`. If the `PipelineStage` has some state, the best way to ensure the batch processor is stateless is to make a local copy of all mutable variables."

Canonical stateful-stage idiom (from the same docstring, `_pipeline.py:94-110`):

```python
class Stateful(PipelineStage):
    def __init__(self, factor: float):
        self.factor = factor
    def _get_batch_processor(self) -> t.Callable[[Batch], Batch]:
        factor = self.factor          # local copy captured by closure
        def batch_operation(batch: Batch) -> Batch:
            return Batch({"result": batch["input"] * factor})
        return batch_operation
```

`pipeline()` signature (`_pipeline.py:115-116`):

```python
def pipeline(producer: Producer, *stages: OneOrMany[PipelineStage]) -> Producer
```

- Stage args may be **tuples/lists of stages and are flattened automatically** (`resolve_one_or_many_to_list`) — this is why notebooks do `*model_stages` or pass `(a, b, c)` inline.
- Raises `TypeError(f"Stage is of unsupported type: {type(stage)}")` for non-`PipelineStage`.

### 4.3 `Introspector` protocol — `src/dnikit/dnikit/base/_introspector.py:20-57`

```python
class Introspector(t.Protocol):
    introspect: t.Callable[..., t.Any]   # static factory method; args are algorithm-dependent
```

Docstring lists the full algorithm set: `PFA`, `IUA`, `DimensionReduction`, `Familiarity`, `Duplicates`, `DatasetReport`.

### 4.4 `multi_introspect()` — `src/dnikit/dnikit/base/_multi_introspect.py`

Runs N introspectors **concurrently over one pass of the producer** (memory-efficient alternative to `Cacher`).

```python
def multi_introspect(*introspectors: _Introspector[t.Any], producer: Producer) -> t.Tuple[t.Any, ...]
```

Typed overloads exist for 1..7 introspectors plus a generic `*introspectors` fallback (`:162-221`).

```python
pfa, familiarity = multi_introspect(PFA.introspect, Familiarity.introspect, producer=producer)

# with args:
results = multi_introspect(
    lambda prod: Familiarity.introspect(prod, strategy=Familiarity.Strategy.GMM()),
    producer=producer)
# or
results = multi_introspect(
    functools.partial(Familiarity.introspect, strategy=Familiarity.Strategy.GMM()),
    producer=producer)
```

Implementation: `_ProducerSplitter` (`:43-158`) uses `threading.Event` handoff — one thread per introspector via `concurrent.futures.ThreadPoolExecutor(max_workers=num_introspectors)`; only one thread runs at a time (threads used for **preemption, not parallelism**).

**Gotchas:**
- All introspectors **must request the same `batch_size`**, else `ValueError(f"Mismatched batch_size, got {batch_size}, expected {self._batch_size}")` (`:135`).
- Any exception in any introspector → `splitter.signal_failure()` → `DNIKitException("Encountered exception when processing multiple introspectors")` chained via `from e` (`:334-337`).
- **"Do not attempt to catch the `AssertionError` in any of the input introspectors, doing so may cause deadlock!"** (`:305-307`).

---

## 5. `Batch` — the universal data container

File: `src/dnikit/dnikit/base/_batch/_batch.py` (1237 lines — the largest file in the repo).

Frozen dataclass with a single member `_storage: _BatchStorage`. Three conceptual parts:

| Accessor | Type | Notes |
|---|---|---|
| `batch.fields` | `Mapping[str, np.ndarray]` | dim 0 is **always** the batch dimension |
| `batch.snapshots` | `Mapping[str, Batch]` | saved earlier pipeline state; **snapshots may not contain snapshots** |
| `batch.metadata` | `Batch.MetadataType` | keyed by `Batch.MetaKey` / `Batch.DictMetaKey` |
| `batch.batch_size` | `int` | |
| `batch.elements` | `Batch.ElementsView` | iteration / indexing / slicing |

### 5.1 Construction

```python
batch = Batch({"images": numpy.zeros((32, 3, 64, 64))})   # fields-only ctor

builder = Batch.Builder()                                  # or Batch.Builder(base=existing_batch)
builder.fields["images"] = images
builder.metadata[Batch.StdKeys.IDENTIFIER] = [...]
builder.metadata[Batch.StdKeys.LABELS] = {"fine": [...], "coarse": [...]}
builder.snapshots["origin"] = previous_batch
batch = builder.make_batch()
```

Overloads (`_batch.py:178-181`):
```python
@overload
def __init__(self, fields: t.Mapping[str, np.ndarray]): ...
@overload
def __init__(self, *, _storage: _BatchStorage): ...
```

**Errors / invariants:**
- `ValueError("Cannot initialize Batch without any fields")` if empty.
- `ValueError("Cannot provide both `fields` and `storage` arguments")`.
- `Batch.Builder(batch)` → `ValueError("Batch.Builder(batch) is not supported -- use Batch.Builder(base=batch) ...")` (`:867-870`).
- `Batch.Builder(fields=..., base=...)` together → `ValueError("Use either `fields` or `base` argument, not both")`.
- **Arrays are frozen**: `self._storage.freeze_arrays()` sets `array.flags.writeable = False` on every field array (`_storage.py:52-54`). Downstream code (e.g. `dnikit_torch.ProducerTorchDataset`) must `.copy()` before handing to `torch.Tensor`.
- `check_invariants()` (`_storage.py:56-85`) raises `DNIKitException` if field lengths mismatch, if a snapshot's batch_size differs, if a snapshot contains snapshots, or if metadata sequence lengths ≠ batch_size.
- A `_BatchStorage` with neither fields nor metadata → `DNIKitException("Must have non-empty fields or metadata.")`.

### 5.2 Metadata keys

```python
META_KEY      = Batch.MetaKey[int]("META_KEY")           # -> Sequence[int], len == batch_size
DICT_META_KEY = Batch.DictMetaKey[float]("DICT_KEY")     # -> Mapping[str, Sequence[float]]

flat = batch.metadata[META_KEY]                 # Sequence[int]
d    = batch.metadata[DICT_META_KEY]["key"]     # Sequence[float]
element_value = batch.elements[0].metadata[META_KEY]              # int
element_dict  = batch.elements[0].metadata[DICT_META_KEY]         # Mapping[str, float]
```

Generic payload types are **type-checker only, never validated at runtime**. Key `name` must be unique.
`Batch.MetadataType` supports `__getitem__`, `__contains__`, `__bool__`, `.keys()` (type-erased).
Mutable variant: `Batch.Builder.MutableMetadataType` adds `__setitem__` / `__delitem__`.

Internally `_MetaKeyTrait` metadata is stored as `storage[meta_key][None]` and `_DictMetaKeyTrait` as `storage[meta_key][field]` (`_metadata_storage.py:60-67`).

### 5.3 Standard keys — `Batch.StdKeys` (`_batch.py:1116-1237`)

```python
Batch.StdKeys.IDENTIFIER = Batch.MetaKey[t.Hashable]('dnikit.base.Batch.StdKeys.identifier')
Batch.StdKeys.PATH       = Batch.MetaKey[dt.PathOrStr]('dnikit.base.Batch.StdKeys.path')
Batch.StdKeys.LABELS     = Batch.DictMetaKey[t.Hashable]('dnikit.base.Batch.StdKeys.labels')
```

(These are assigned at module bottom, *not* in the class body — "unable to do this inline because of type visibility issues".)
`Batch.StdKeys()` raises `DNIKitException("Do not instantiate Batch.StdKeys")`.

Documented `IDENTIFIER` use cases (`_batch.py:1129-1184`): array index for CIFAR; file path for image datasets; `(path, crop_x, crop_y, crop_w, crop_h)` tuple for face-crop datasets; UUID/sequence int when nothing natural exists.

```python
builder.metadata[Batch.StdKeys.LABELS] = {
    "shape": ["square", "square", "triangle", ...],
    "color": ["blue", "red", "green", ...],
}
```

### 5.4 `Batch.elements` indexing (`_batch.py:262-342`)

```python
element = batch.elements[42]              # -> Batch.ElementType
subset  = batch.elements[-1, 1, 2, 3, 5]  # Sequence[int] -> Batch
subset  = batch.elements[10:30:2]         # slice        -> Batch
for element in batch.elements: ...        # Batch.ElementType
len(batch.elements) == batch.batch_size
```

`Batch.ElementType.fields` returns `np.ndarray` for ≥2-D fields and `np.number` for 1-D fields.
Out-of-range sequence selector → `IndexError(f"Selector {selector} out of range in batch with {n} elements")` (`_storage.py:171-177`).

Concatenation (`_storage.py:134-166`) requires identical fields, snapshots, metadata keys and metadata sub-fields, else `ValueError("Cannot concatenate batches with different fields/snapshots/metadata/metadata fields")`.

---

## 6. `Model` abstraction and framework backends

### 6.1 `dnikit.base.Model` — `src/dnikit/dnikit/base/_model.py:124-241`

Frozen dataclass wrapping a private `_ModelDetails`. **Do not instantiate directly**; use `dnikit_tensorflow` loaders.

```python
model.response_infos   # Mapping[str, ResponseInfo]  -- every layer output
model.input_layers     # Mapping[str, ResponseInfo]  -- placeholders whose name contains 'input'

stage = model(requested_responses: dt.OneManyOrNone[str] = None)  # -> PipelineStage
```

`requested_responses=None` ⇒ **all** responses are collected ("which may be expensive to compute!", `:230-231`).

Input-binding rules (`_ModelPipelineStage._get_batch_processor`, `:83-121`):
1. If the model has **exactly one** input and the batch has **exactly one** field, and the names differ but `batch.fields[f].shape[1:] == input_response.shape[1:]`, DNIKit **auto-renames** the field. This is why `mobilenet.model(...)` "auto-detects the input layer and connects up 'images' to it".
2. Otherwise, if `len(potential_inputs) == len(batch.fields)` and the name sets differ →
   ```
   DNIKitException: Model expects inputs named {names} but batch contains fields named {fields}.
   Field names must match expected input names to perform inference. (To change field names in a
   batch, try using a FieldRenamer in the pipeline. To import the FieldRenamer class, do
   'from dnikit.processors import FieldRenamer')
   ```
3. Output batch is built with `Batch.Builder(base=batch)` and `builder.fields = dict(inference_result)` — **input fields are replaced by responses**, metadata & snapshots preserved.

### 6.2 `ResponseInfo` — `src/dnikit/dnikit/base/_response_info.py`

```python
@dataclass(frozen=True)
class ResponseInfo:
    name: str
    dtype: np.dtype
    shape: t.Tuple[t.Optional[int], ...]   # first dim generally None
    layer: "ResponseInfo.Layer"            # .name, .kind (LayerKind), .typename (framework str)
```

`ResponseInfo.LayerKind` enum values (`:89-139`) — **note `LINEAR = DENSE = 1000` are aliases**:

```
UNKNOWN=0
LINEAR=1000  DENSE=1000  PLACEHOLDER=1001
CONV_1D=2000 CONV_2D=2001 CONV_3D=2002
CONV_TRANSPOSE_1D=2003 CONV_TRANSPOSE_2D=2004 CONV_TRANSPOSE_3D=2005
MAX_POOLING_1D=3000 MAX_POOLING_2D=3001 MAX_POOLING_3D=3003   # note: no 3002
AVERAGE_POOLING_1D=3004 AVERAGE_POOLING_2D=3005 AVERAGE_POOLING_3D=3006
RNN=4000 LSTM=4001 GRU=4002
BATCH_NORM=5000 BATCH_NORM_2D=5001 BATCH_NORM_3D=5002 LAYER_NORM=5003
DROPOUT=6000 DROPOUT_2D=6001 DROPOUT_3D=6002
SIGMOID=8000 TANH=8001 RELU=8002 LEAKY_RELU=8003 PRELU=8004 ELU=8005
SOFTMAX=8006 ATTENTION=8007 RELU6=8008
```

Standard idiom to select conv layers:

```python
conv2d_responses = [
    info.name
    for info in model.response_infos.values()
    if info.layer.kind is ResponseInfo.LayerKind.CONV_2D
    and 'preds' not in info.name
]
```

### 6.3 Backends actually shipped

| Framework | Support | Where |
|---|---|---|
| TensorFlow 2 / tf.keras | **Full** `Model` (load from path or memory, per-layer response extraction, inference) | `src/dnikit_tensorflow/.../_tf2_*.py` |
| TensorFlow 1 (graph/session) | **Full** `Model` (SavedModel, `.pb`, checkpoint, Keras h5, arch+weights) | `_tf1_*.py` |
| PyTorch | **Data adaptors only** — `TorchProducer`, `ProducerTorchDataset`. **No `Model`/`_ModelDetails`** — you run inference yourself and feed responses in. | `src/dnikit_torch/dnikit_torch/_torch_producer.py` |
| Core ML | **Not supported.** No `coremltools`, no `.mlmodel`/`.mlpackage` loader anywhere in the repo. | — |
| JAX / anything else | Via a custom `Producer` of responses (docs explicitly name JAX, `docs/utils/data_producers.rst:234-236`) | — |

`_ModelDetails` protocol (`_model.py:29-74`) — 3 methods: `run_inference(inputs: Mapping[str, np.ndarray], outputs: AbstractSet[str]) -> Mapping[str, np.ndarray]`, `get_response_infos() -> Iterable[ResponseInfo]`, `get_input_layer_responses() -> Sequence[ResponseInfo]`.

> **Warning (verbatim, `_model.py:36-42`):** "To wrap a deep learning framework that DNIKit does not currently support, it's recommended to create a custom `Producer` that yields the model responses, rather than creating a custom `_ModelDetails`. This class is intended for code that will eventually be integrated into DNIKit."

### 6.4 TF loading API — `dnikit_tensorflow`

Public surface (`src/dnikit_tensorflow/dnikit_tensorflow/__init__.py:26-32`):

```python
__all__ = ["load_tf_model_from_path", "load_tf_model_from_memory",
           "TFModelExamples", "TFModelWrapper", "TFDatasetExamples"]
```

```python
from dnikit_tensorflow import load_tf_model_from_path, load_tf_model_from_memory

dni_model = load_tf_model_from_path("/path/to/model")     # PathOrStr

tf2_model = ...                                            # tf.keras.models.Model
dni_model = load_tf_model_from_memory(model=tf2_model)     # TF2: pass `model=`
dni_model = load_tf_model_from_memory(session=tf1_sess)    # TF1: pass `session=`
```

`load_tf_model_from_memory(*, session=None, model=None)` (`_tensorflow_loading.py:34`) validates:
- both `None` or both set → `ValueError('For TF2 (currently installed), please pass param `model`'[ + ' only.'])`
- error text switches to "For TF1 (currently installed), please pass param `session`" when `running_tf_1()`.

`running_tf_1()` = `tf.__version__[0] == '1'` (`_tensorflow_protocols.py:27-28`). Selected at **import time** in `_tensorflow_loading.py:24-31`.

**Loading chains** (`LoadingChain.get_loader` walks in order, first `can_load()` wins; failure → `DNIKitException(f'DNIKit unable to load TF model from path: {pathname}.')`):

```python
# _tf2_loading.py:30-36
TF2LoadingChain = LoadingChain(loading_chain=[
    _TF2SavedKerasModelLoader,      # tf.saved_model.contains_saved_model(dir)
    _TF2KerasArchAndWeightsLoader,  # dir containing 1 arch file + 1 weights file
    _TF2KerasWholeModelLoader,      # pathname.suffix == '.h5'
])

# _tf1_loading.py:32-40
_TF1LoadingChain = LoadingChain(loading_chain=[
    _TF1SavedModelLoader, _TF1ProtobufLoader,        # suffix in ['.pb', '.proto']
    _TF1CheckpointLoader,                            # pathname.with_suffix('.meta').is_file()
    _TF1KerasArchAndWeightsLoader, _TF1KerasWholeModelLoader,
])
```

Arch/weights detection (`_tensorflow_file_loaders.py:53-81`): weights extensions `['.hdf', '.h5', '.hdf5', '.he5']`, architecture extensions `['.json', '.yml', '.hdf5', '.he5']`; a directory qualifies only if **exactly one** file of each kind is present.

`load_tf_2_model_from_path` calls `tf.keras.backend.clear_session()` before loading (`_tf2_loading.py:71`); the TF1 path calls `_clear_keras_session()` which clears **both** `tf.keras.backend` and `keras.backend` (`_tensorflow_file_loaders.py:26-43`).

> **Gotcha (verbatim, `_tensorflow_loading.py:92-96`):** "The keras loaders are currently using `tf.keras` instead of `keras` natively, and so issues might appear when trying to load models saved with native `keras` (not tf.keras). In this case, load the model outside of DNIKit with `keras` and pass it to load with `load_tf_model_from_memory`."

### 6.5 TF2 inference internals — `_tf2_model.py:142-181`

```python
def run_inference(self, inputs, outputs):
    self.model.trainable = False
    inference_model = tf.keras.Model(
        inputs=[self.model.input],
        outputs=[self.model.get_layer(layer_name).output for layer_name in outputs])
    ...
    results = inference_model(list(inputs.values()))
```

Special cases:
- **batch of 1**: TF collapses the batch dim, so each tensor is `np.expand_dims(tensor.numpy(), axis=0)` (`:164-171`).
- **single requested response**: `results` is a single tensor, not a list → `{list(outputs)[0]: results.numpy()}` (`:174-175`).
- Unknown input name → `TypeError(f'Invalid input "{input_name}". Valid inputs are {possible_inputs}.')`.
- **`outputs` is an `AbstractSet[str]`** and is `zip`ped with `results` — the ordering relies on the same set iteration order being used for both the `tf.keras.Model(outputs=[...])` construction and the zip. Set iteration order is stable within a process, so this works, but it is fragile.

`get_input_layer_responses()` (TF1 and TF2 alike) is a **heuristic**: `kind is PLACEHOLDER and 'input' in info.name`.

### 6.6 Sample models & datasets (`dnikit_tensorflow`)

```python
from dnikit_tensorflow import TFModelExamples, TFModelWrapper, TFDatasetExamples

mobilenet = TFModelExamples.MobileNet()     # -> TFModelWrapper
mobilenet.model                             # dnikit.base.Model
mobilenet.preprocessing                     # Processor wrapping keras preprocess_input
mobilenet.postprocessing                    # None
mobilenet.response_infos                    # Mapping[str, ResponseInfo]
stages = mobilenet(requested_responses=['conv_pw_13'])  # pre + model + post, flattened by pipeline()
```

`TFModelExamples.MobileNet` is literally (`_sample_models.py:149-151`):

```python
MobileNet: t.Callable[..., TFModelWrapper] = lambda: (
    TFModelWrapper.from_keras(tf.keras.applications.mobilenet.MobileNet(),
                              tf.keras.applications.mobilenet.preprocess_input))
```

`TFModelWrapper.load_keras_model` **round-trips the model through a temp `.h5` on disk** (`_sample_models.py:84-96`):

```python
with tempfile.TemporaryDirectory() as temp_dir:
    model_path = os.path.join(temp_dir, 'model.h5')
    model.save(model_path)
    dni_model = load_tf_model_from_path(model_path)
```
→ this breaks with Keras 3, which removed/deprecated bare `.h5` saving. (Unverified whether PR #4 addressed this; it did not touch `_sample_models.py`.)

Datasets (`_sample_datasets.py`), all subclasses of `TrainTestSplitProducer`:

```python
TFDatasetExamples.CIFAR10       # str labels: airplane automobile bird cat deer dog frog horse ship truck
TFDatasetExamples.CIFAR100      # label_mode="fine" (100 names) or "coarse" (20 names)
TFDatasetExamples.MNIST         # labels 0..9 (no str_to_label_idx)
TFDatasetExamples.FashionMNIST  # T-shirt/top Trouser Pullover Dress Coat Sandal Shirt Sneaker Bag "Ankle boot"
```

```python
cifar10 = TFDatasetExamples.CIFAR10(attach_metadata=True, max_samples=-1)
cifar10_cars = cifar10.subset(labels=["automobile"], datasets=["train"], max_samples=1000)
cifar100 = TFDatasetExamples.CIFAR100(label_mode='fine'); foxes = cifar100.subset(labels=["fox"])
mnist_fives = TFDatasetExamples.MNIST().subset(labels=[5], datasets=["test"], max_samples=100)
```

`CIFAR100.load_dataset(label_mode="fine")`; invalid mode → `ValueError("label_mode must be either 'fine' or 'coarse'")`.

---

## 7. Producers shipped in `dnikit.base`

`src/dnikit/dnikit/base/__init__.py` `__all__`:
`Batch, CachedProducer, ImageFormat, PixelFormat, ImageProducer, Introspector, Model, multi_introspect, PipelineStage, pipeline, Producer, ResponseInfo, peek_first_batch, TrainTestSplitProducer`

### 7.1 `ImageProducer` — `_image_producer.py:118-249`

```python
ImageProducer(directory: pathlib.Path, *,
              extensions: dt.OneManyOrNone[str] = None,
              recursive: bool = True,
              field: str = "images")
```

- Default extensions: `{"png", "jpeg", "jpg", "tiff", "bmp"}`; both lower- and UPPER-case globs are searched; results `sorted()`.
- Loads via `cv2.imread(path, cv2.IMREAD_UNCHANGED)`; grayscale → `expand_dims(-1)` (C=1), BGR→RGB, BGRA→RGBA. Output is **NHWC**.
- Sets both `Batch.StdKeys.IDENTIFIER` and `Batch.StdKeys.PATH` to the list of `pathlib.Path`s.
- Raises: `NotADirectoryError(f"Invalid directory: {directory}")`; `DNIKitException("No images with extensions ... found in directory ...")`; `DNIKitException("OpenCV not available, was dnikit['image'] installed?")`; `ValueError(f"Batch size has to be a greater than 0, got {batch_size}")`; and — **the big one** — `DNIKitException(f"Invalid shape for image in: {image_path}, got: {image.shape}, expected: {expected_shape}")` because **all images must be the same HWC** (docs/general/support.rst:83-88 confirms: "the images need to be the same dimensions. If some images in the dataset have different sizes, it's necessary to define a custom `Producer`").

Enums:
```python
class ImageFormat(enum.Enum):  HWC = (0, 1, 2);  CHW = (2, 1, 0)   # value = np.transpose axes to reach HWC
class PixelFormat(enum.Enum):  BGRA BGR RGBA RGB GRAY
    .to_opencv   -> cv2.cvtColor code to reach BGRA-ish write format (None for BGR/BGRA/GRAY)
    .alpha_channel -> 3 for BGRA/RGBA else None
```

### 7.2 `TrainTestSplitProducer` — `_traintest_producer.py:29-224`

```python
TrainTestSplitProducer(split_dataset: dt.TrainTestSplitType,   # ((x_train,y_train),(x_test,y_test))
                       attach_metadata: bool = True,
                       max_samples: int = -1)
TrainTestSplitProducer(tf.keras.datasets.cifar10.load_data())  # direct from keras
```

- Field name is always `"samples"`.
- Metadata: `IDENTIFIER` = list of integer indices; `LABELS` = `{"label": np.take(labels, idx), "dataset": 0 for train / 1 for test}`.
- `.shuffle()` sets `self._permutation = np.random.permutation(len(samples))` — "**this shuffling will not transfer to subsets**".
- `.subset(labels=None, datasets=None, max_samples=None) -> TrainTestSplitProducer` — `datasets` accepts only `"train"` / `"test"`.
- Errors: `TypeError` if the tuple shape is wrong; `DNIKitException` for "Only one of x_train or x_test can be empty.", "Individual items for x_train and x_test must be of the same shape.", "x_test and y_test must be of the same length.", "x_train and y_train must be of the same length."; `ValueError("'datasets' field is of length 0. Maybe it should be None?")` (same for `labels`).
- `np.squeeze` is applied to samples and labels — so a `(N,1)` label array becomes `(N,)`.

### 7.3 `Cacher` / `CachedProducer` — `_cached_producer.py`

```python
from dnikit.processors import Cacher      # exported via processors, defined in base
cacher = Cacher(storage_path: t.Optional[pathlib.Path] = None)   # default: tempfile.mkdtemp(prefix="dnikit-cacher-")
pipelined = pipeline(producer, processor, cacher)
cacher.cached          # bool: True once ".cache.done" marker exists
cacher.storage_path    # resolved absolute Path
cp = cacher.as_producer()               # -> CachedProducer  (raises if not yet cached)
cp2 = cp.copy_to(new_path, overwrite=False)
Cacher.clear(storage_path=None)         # deletes ALL dnikit caches under tempdir (or given dir)
```

On-disk format: one **pickle** per batch, `f"{index}.pkl"`, plus marker files `.dni_cache_dir` and `.cache.done`.
`Cacher` attaches a numeric `Batch.StdKeys.IDENTIFIER` if the batch has none (`_add_identifier`, `:232-244`).

**Errors / warnings:**
- Constructing a `Cacher` over a dir that already has cache files → `DNIKitException(f"Path {path} already contains caching files.")`.
- Reusing a `Cacher` in **two** pipelines → `DNIKitException("Cacher already used in a pipeline. Either create a new Cacher ... or call as_producer() ...")`.
- `as_producer()` before caching completes → `DNIKitException("Caching must be complete before converting to a CachedProducer.")`.
- `CachedProducer(path)` on a dir without `.cache.done` → `DNIKitException(f"{path} does not contain cached batches. Cannot create CachedProducer.")`.
- Reading with a different `batch_size` than was cached works but is "relatively computationally expensive since it involves concatenating and splitting batches".
- `Cacher.clear()` warning: "Make sure to only call this function once pipelines are no longer needed... Otherwise, a cache that is already in use may be destroyed!"
- `Cacher._get_batch_processor()` deliberately raises `DNIKitException('Should never call this function in CachedProducer')` — it overrides `_pipeline` instead.

### 7.4 Sample/stub producers — `dnikit.samples`

```python
from dnikit.samples import StubProducer, StubImageDataset, StubGatedAdditionDataset

StubProducer(data: Mapping[str, np.ndarray], metadata: Optional[Mapping[Any, Any]] = None)
StubImageDataset(dataset_size, image_width=640, image_height=480, channel_count=3)  # field "images", NHWC, randn
StubGatedAdditionDataset(dataset_size, minimum_sequence_length=100, maximum_sequence_length=100)
    # fields: "x" (B,T,2) float32, "target" (B,) float32, "sequence_length" (B,)
```

`StubProducer` builds one giant `Batch` up front and re-chunks it with `_resize_batches`.

---

## 8. The Keras 3 tensor-metadata commit (2f39056, 2026-07-09, PR #4, "Fixes #2")

**Files touched:** `src/dnikit_tensorflow/dnikit_tensorflow/_tensorflow/_tf2_model.py` (+45/−14) and `src/dnikit_tensorflow/tests/test_tf2_model_loaders.py` (+23/−2).

**PR summary (verbatim from the commit message):**
> - read TF2 tensor dtype and shape from `type_spec` when available, with a Keras 3 fallback to `dtype` and `shape`
> - normalize tensor metadata through TensorFlow before building `ResponseInfo`
> - use layer metadata when Keras 3 output names are generic, so Conv2D responses still classify correctly

### 8.1 Diff, annotated

**(a) New op names in `_KNOWN_OPS`** — Keras 3 reports class names, not graph op names:

```python
_KNOWN_OPS: t.Final[t.Mapping[str, ResponseInfo.LayerKind]] = {
+   "InputLayer": ResponseInfo.LayerKind.PLACEHOLDER,
    "Placeholder": ResponseInfo.LayerKind.PLACEHOLDER,
    "Softmax": ResponseInfo.LayerKind.SOFTMAX,
    "Relu": ResponseInfo.LayerKind.RELU,
    "Relu6": ResponseInfo.LayerKind.RELU6,
    "Conv2D": ResponseInfo.LayerKind.CONV_2D,
+   "BatchNormalization": ResponseInfo.LayerKind.BATCH_NORM,
    "FusedBatchNormV3": ResponseInfo.LayerKind.BATCH_NORM
}
```

**(b) Shape/dtype normalization** — previously `shape.dims` were yielded as `Dimension` objects and `dtype` was assumed to be a `tf.DType`:

```python
-def _convert_tf_shape(shape: tf.TensorShape) -> t.Tuple[t.Optional[int], ...]:
+def _convert_tf_shape(shape: t.Any) -> t.Tuple[t.Optional[int], ...]:
+    shape = tf.TensorShape(shape)
     if shape.dims is None:
         return tuple()
-    return tuple(dim for dim in shape.dims)
+    return tuple(shape.as_list())

-def _convert_tf_dtype(dtype: tf.dtypes.DType) -> np.dtype:
+def _convert_tf_dtype(dtype: t.Any) -> np.dtype:
+    dtype = tf.as_dtype(dtype)
     return dtype.as_numpy_dtype if dtype.is_numpy_compatible else np.dtype(object)
```

**(c) The core fix — `type_spec` may not exist on Keras 3 `KerasTensor`:**

```python
def _get_tensor_dtype_and_shape(tensor: t.Any) -> t.Tuple[t.Any, t.Any]:
    type_spec = getattr(tensor, "type_spec", None)
    if type_spec is not None:
        return type_spec.dtype, type_spec.shape
    return tensor.dtype, tensor.shape
```

**(d) Layer-kind classification now tries multiple names** (Keras 3 emits generic tensor names like `keras_tensor_1`):

```python
-def _convert_tf_operation(layer_name: str) -> ResponseInfo.LayerKind:
+def _convert_tf_operation(*layer_names: str) -> ResponseInfo.LayerKind:
     # First check known operations
-    operation = _extract_kind(layer_name)
-    if operation in _KNOWN_OPS:
-        return _KNOWN_OPS[operation]
+    for layer_name in layer_names:
+        operation = _extract_kind(layer_name)
+        if operation in _KNOWN_OPS:
+            return _KNOWN_OPS[operation]
     # next, check layer name prefixes
-    for layer_prefix, layer_kind in _LAYER_PREFIXES.items():
-        if layer_name.startswith(layer_prefix):
-            return layer_kind
+    for layer_name in layer_names:
+        for layer_prefix, layer_kind in _LAYER_PREFIXES.items():
+            if layer_name.startswith(layer_prefix):
+                return layer_kind
     return ResponseInfo.LayerKind.UNKNOWN
```

**(e) Call site in `_Tensorflow2ModelDetails.get_response_infos()`:**

```python
for layer in self.model.layers:
    dtype, shape = _get_tensor_dtype_and_shape(layer.output)
    yield ResponseInfo(
        name=layer.name,
        dtype=_convert_tf_dtype(dtype),
        shape=_convert_tf_shape(shape),
        layer=ResponseInfo.Layer(
            name=_remove_op_number(layer.output.name),
            kind=_convert_tf_operation(
                layer.output.name,
                layer.name,
                layer.__class__.__name__,
            ),
            typename=_extract_kind(layer.output.name)
        )
    )
```

Order of name candidates: `layer.output.name` → `layer.name` → `layer.__class__.__name__`.
Note `typename` is still derived **only** from `layer.output.name`, so under Keras 3 `typename` may be a useless `"keras_tensor_1"` even though `kind` is now correct.

**(f) The two new tests** (`test_tf2_model_loaders.py:92-106`), which double as the contract:

```python
def test_get_tensor_dtype_and_shape_without_type_spec() -> None:
    class Tensor:
        dtype = tf.float32
        shape = (None, 32, 32, 3)
    dtype, shape = _get_tensor_dtype_and_shape(Tensor())
    assert dtype == tf.float32
    assert shape == (None, 32, 32, 3)

def test_convert_tf_operation_uses_layer_metadata_when_output_name_is_generic() -> None:
    kind = _convert_tf_operation("keras_tensor_1", "conv0_conv", "Conv2D")
    assert kind is ResponseInfo.LayerKind.CONV_2D
```

Helper name-mangling used by the classifier (`_tf2_model.py:70-81`):

```python
_remove_op_number("conv_pw_13/convolution:0") -> "conv_pw_13/convolution"   # strips ":N"
_extract_kind(full_name)      -> _remove_op_number(full_name.split('/')[-1])  # last path segment
_extract_layer_prefix(name)   -> _remove_op_number(full_name.split('/')[0])   # first path segment (unused here)

_LAYER_PREFIXES = {'conv': CONV_2D, 'input': PLACEHOLDER,
                   'dropout': DROPOUT, 'global_average_pooling': AVERAGE_POOLING_2D}
```

**Practical consequence for guides:** response names differ between TF1 and TF2. `src/dnikit_tensorflow/tests/test_tf_examples.py:33-36`:

```python
if running_tf_1():
    layer_name = "conv_pw_13/Conv2D:0"
else:
    layer_name = "conv_pw_13"
```

Older docs/notebooks still show `'conv_pw_13/convolution:0'` (e.g. `docs/introspectors/data_introspection/familiarity.rst:93`, `duplicates.rst:58`) — **stale for TF2**; the notebooks use the bare `'conv_pw_13'`.

---

## 9. Processors (`dnikit.processors`)

`__all__` (`src/dnikit/dnikit/processors/__init__.py:48-68`):
`Processor, MeanStdNormalizer, Transposer, FieldRemover, FieldRenamer, Flattener, MetadataRemover, MetadataRenamer, SnapshotSaver, SnapshotRemover, PipelineDebugger, Pooler, Concatenator, Cacher, Composer, ImageGammaContrastProcessor, ImageGaussianBlurProcessor, ImageResizer, ImageRotationProcessor`

### Base `Processor` (`_base_processor.py:24-68`)

```python
Processor(func: t.Callable[[np.ndarray], np.ndarray], *, fields: dt.OneManyOrNone[str] = None)
```
`fields=None` ⇒ apply to **all** fields. Not abstract — instantiate directly with a lambda/function:

```python
def to_db_func(x: np.ndarray) -> np.ndarray:
    return 20 * np.log10(x / 1e-5)
processor = Processor(to_db_func)
```

### Full processor reference

| Class | Signature (exact) | Notes / errors |
|---|---|---|
| `MeanStdNormalizer` | `(*, mean: float, std: float, fields=None)` | `(x - mean) / std` |
| `Transposer` | `(*, dim: t.Sequence[int], fields=None)` | `ValueError("Unable to move the 0th (batch) dimension.")` if `dim[0] != 0`. NCHW↔NHWC: `dim=[0,3,1,2]` |
| `Flattener` | `(order: str = 'C', fields=None)` | `BxN1xN2x..` → `BxN`; `order ∈ {C,F,A,K}` else `ValueError` |
| `Pooler` | `(*, dim: OneOrMany[int], method: Pooler.Method, fields=None)` | `Method.MAX / SUM / AVERAGE`; `assert 0 not in dims` |
| `FieldRemover` | `(*, fields: OneOrMany[str], keep: bool = False)` | |
| `FieldRenamer` | `(mapping: Mapping[str, str])` | positional arg, **not** keyword |
| `Concatenator` | `(dim: int, output_field: str, fields: Sequence[str])` | dataclass; asserts `dim != 0` and non-empty fields |
| `SnapshotSaver` | `(save: str = "snapshot", fields=None, keep: bool = True)` | |
| `SnapshotRemover` | `(snapshots=None, keep: bool = False)` | no args ⇒ removes **all** snapshots |
| `MetadataRemover` | `(*, meta_keys=None, keys=None, keep: bool = False)` | `ValueError("`keys` contains metadata keys. Use `meta_keys` for this instead.")` |
| `MetadataRenamer` | `(mapping: Mapping[str,str], *, meta_keys: OneManyOrNone[Batch.DictMetaKey] = None)` | **DictMetaKey only** |
| `PipelineDebugger` | `(label: str = "", first_only: bool = True, dump_fields: bool = False, fields=None)` | also `PipelineDebugger.dump(batch, label, dump_fields, fields) -> str` |
| `Composer` | `(filter: Callable[[Batch], Optional[Batch]])` | plus 2 classmethods, below |
| `ImageResizer` | `(*, pixel_format: ImageFormat, size: t.Tuple[int,int], fields=None)` | `size` is **(width, height)**; OpenCV `INTER_LINEAR`; does **not** honor aspect ratio; `assert len(data.shape)==4` |
| `ImageGaussianBlurProcessor` | `(sigma: float = 0., *, fields=None)` | `ValueError` if `sigma < 0`; asserts pixels in [0,255] |
| `ImageGammaContrastProcessor` | `(gamma: float = 1., *, fields=None)` | `(I/255)^gamma*255` via `cv2.LUT` (uint8 only) |
| `ImageRotationProcessor` | `(angle: float = 0., pixel_format: ImageFormat = ImageFormat.HWC, *, cval=(0,0,0), fields=None)` | positive angle = counter-clockwise |
| `Cacher` | see §7.3 | |

All image processors raise `DNIKitException("OpenCV not available, was dnikit['image'] installed?")` at construction.

### `Composer` — batch/element filtering (`_processors.py:455-544`)

```python
Composer(filter)                                        # filter: Batch -> Optional[Batch]; None => empty batch
Composer.from_element_filter(elem_filter)               # elem_filter: Batch.ElementType -> bool
Composer.from_dict_metadata(metadata_key: Batch.DictMetaKey[str],
                            label_dimension: str, label: str)   # used by split-Familiarity
```

`Composer` returning `None` yields `batch.elements[[]]` — an **empty batch**, which is what the DatasetReport's per-label familiarity relies on.

---

## 10. Introspectors

Public API (`src/dnikit/dnikit/introspectors/__init__.py:56-77`):

```
DimensionReduction, DimensionReductionStrategyType, OneOrManyDimStrategies,
Duplicates, DuplicatesThresholdStrategyType,
IUA,
FamiliarityDistribution, FamiliarityStrategyType, FamiliarityResult, Familiarity, GMMCovarianceType,
PFA, PFAKLDiagnostics, PFAEnergyDiagnostics, PFARecipe,
PFAUnitSelectionStrategyType, PFAStrategyType, PFACovariancesResult,
DatasetReport, ReportConfig
```

### 10.1 `DimensionReduction`

```python
DimensionReduction.introspect(producer: Producer, *,
                              strategies: OneOrManyDimStrategies,
                              batch_size: t.Optional[int] = None) -> DimensionReduction
```
`OneOrManyDimStrategies = Union[DimensionReductionStrategyType, Mapping[str, DimensionReductionStrategyType]]` — a single strategy is `._clone()`-ed per field via a `defaultdict`; a mapping applies per-field (fields not in the mapping are left untouched).

Result is a `PipelineStage`: `reduced = pipeline(producer, reducer)`.

Strategies (`DimensionReduction.Strategy`, `_reducers.py`):

| Strategy | Constructor | Streaming? | Notes |
|---|---|---|---|
| `PCA` | `PCA(target_dimensions: int = 2)` | **yes** (`sklearn.decomposition.IncrementalPCA`) | `default_batch_size() = max(target_dimensions*5, 500)`; skips partial-fit for batches smaller than `target_dimensions` |
| `StandardPCA` | `StandardPCA(target_dimensions=2)` | no (accumulates) | exact `sklearn.decomposition.PCA` |
| `TSNE` | `TSNE(target_dimensions=2, *, _parameters=None, **kwargs)` | no; **one-shot** | kwargs → `sklearn.manifold.TSNE` |
| `UMAP` | `UMAP(target_dimensions=2, *, _parameters=None, **kwargs)` | no (accumulate), but **not** one-shot (has `.transform`) | `umap-learn`; import is **lazy** |
| `PaCMAP` | `PaCMAP(target_dimensions=2, *, _parameters=None, **kwargs)` | no; **one-shot** | lazy import |

Protocol `DimensionReductionStrategyType` (`_dim_reduction/_protocols.py`, `@t.runtime_checkable`):
`default_batch_size()`, `check_batch_size(batch_size)`, `target_dimensions` (property), `fit_incremental(data)`, `fit_complete()`, `is_one_shot` (property), `transform(data)`, `transform_one_shot()`, `_clone()`.

**Gotchas:**
- Input must be exactly 2-D: `DNIKitException(f'Unable to reduce response of shape {field.shape}. The shape is expected to have 2 dimensions')` — use `Flattener` or `Pooler` first.
- `PCA.check_batch_size`: `DNIKitException('DimensionReduction.Strategy.PCA (IncrementalPCA) requires that thebatch_size ({batch_size}) must be larger or equal to the target_dimensions ({target_dimensions}).')` — note the missing space, "thebatch_size", in the source string (`_reducers.py:69-72`).
- `TSNE.transform` and `PaCMAP.transform` → `DNIKitException("transform() not implemented, call transform_one_shot()")`; `PCA.transform_one_shot` → `DNIKitException("transform_one_shot() not implemented, call transform()")`.
- One-shot strategies are handled specially in `DimensionReduction._pipeline` (`_dimension_reduction.py:161-188`): the whole embedding is computed once and **sliced by running offset** as batches flow through — the pipeline must therefore be replayed in the same order, and mixing one-shot + streaming reducers in one `DimensionReduction` is supported by design.
- UMAP/PaCMAP imports are deferred inside `__init__` "so that it is not imported when dnikit is imported... **Caution due to numba SIGSEGV on task cleanup**" (`_reducers.py:243-244`, `:308-309`).
- `UMAP.transform` redirects stdout to `os.devnull` because "File umap.umap_.py has a print statement `print("inside function\n", graph)` that clutters DNIKit stdout" (`_reducers.py:334-337`).
- Missing packages: `ImportError("pacmap not available, was dnikit['dimreduction'] or pacmap installed?")` / `ImportError("UMAP not available, was dnikit['dimreduction'] or umap-learn installed?")`.
- `umap` vs `umap-learn` confusion is called out in docs/general/support.rst:72-80 — DNIKit needs **umap-learn** (imported as `umap`), *not* the unrelated PyPI `umap` package.
- Recommended recipe from docs: reduce 1024 → 40 with `PCA` first, **then** UMAP/PaCMAP/t-SNE → 2.

Runnable (from `notebooks/data_introspection/dimension_reduction.ipynb`):

```python
partial_reducer = DimensionReduction.introspect(
    producer, batch_size=BATCH_SIZE, strategies=DimensionReduction.Strategy.PCA(40))
partially_reduced = pipeline(producer, partial_reducer)

umap = DimensionReduction.introspect(
    partially_reduced, batch_size=BATCH_SIZE, strategies=DimensionReduction.Strategy.UMAP(2))
umap_reduced = pipeline(partially_reduced, umap)
```

### 10.2 `Familiarity`

```python
Familiarity.introspect(producer: Producer, *,
                       strategy: t.Optional[FamiliarityStrategyType] = None,   # default GMM()
                       batch_size: int = 1024) -> Familiarity
```

Returns a **`PipelineStage`, not a result**. Two-phase:

```python
familiarity = Familiarity.introspect(reduced_producer)          # fit
scored = pipeline(reduced_producer, familiarity)                # score
for batch in scored(batch_size=8):
    for response_name, scores in batch.metadata[familiarity.meta_key].items():
        print(response_name, [s.score for s in scores])
```

- `familiarity.meta_key` is `Batch.DictMetaKey[FamiliarityResult]`; for GMM it is the class-var `Batch.DictMetaKey[FamiliarityResult]("GMM")` (`_gmm_familiarity.py:117`).
- Score = **log-likelihood** (docstring: "Familiarity score. Note: This will actually be the log score."). Higher = more familiar. Docs describe it as the *negative* log-likelihood in the math section (`familiarity.rst:333-337`) — the code returns `logsumexp(...)`, i.e. the **positive** log-density, and the notebooks sort `reverse=True` for "most familiar", so treat "higher = more familiar" as the operational truth.

`Familiarity.Strategy.GMM` (`_gmm_familiarity.py:69-174`):

```python
Familiarity.Strategy.GMM(*, gaussian_count: int = 5,
                            convergence_threshold: float = 1e-3,
                            max_iterations: int = 200,
                            covariance_type: GMMCovarianceType = GMMCovarianceType.DIAG,
                            _random_state: t.Optional[RandomState] = None)
```
Wraps `sklearn.mixture.GaussianMixture(n_components=..., max_iter=..., tol=..., random_state=..., covariance_type=...)`.

`GMMCovarianceType.FULL = 'full'` / `GMMCovarianceType.DIAG = 'diag'`. Guidance verbatim (`_gmm_familiarity.py:51-56`):
> "If there are concerns about overfitting due to a lack of data, dimensions are high wrt. the data available, etc. Then use `DIAG`. This is typically the case when working with **DNN embeddings**. Else, use `FULL`. For example, if fitting 2D data."

Internals: `DIAG` covariances are expanded to full via `np.array([np.diag(vals) for vals in model.covariances_])`, then asserted to be `(gaussian_count, dims, dims)`. Density evaluated by `_MixtureOfMultivariateGaussianDistributions.compute_familiarity_score` = `scipy.special.logsumexp(log_pdf_i + log_weight_i)` where each `log_pdf` is `scipy.stats.multivariate_normal.logpdf`.

**Gotchas:**
- Fitting **accumulates the full producer in memory** (`_accumulate_batches`, `batch_size=1024` default).
- Input must be 2-D per field; reduce dimensions first (docs recommend 40–100 dims).
- Numerical: `src/dnikit/tests/test_familiarity.py` notes the DNIKit log-pdf differs slightly from sklearn's — the test compares `np.exp(score)` with `atol=1e-2`, and warns ranking can swap for close samples (issue #427).

Distribution-comparison heuristic (docs/.../familiarity.rst:266-283), likelihood ratio `L(f→p) = F(D_f,D_p)/F(D_f,D_f)`:
`<0.6` huge gap, re-collect; `0.6–0.8` small gap worth inspecting; `0.8–1.2` fine; `>1.2` gap worth inspecting.
(The distribution notebook actually computes the **difference** of mean log-scores, `stats['test'] - stats['train']`, i.e. the log of that ratio.)

### 10.3 `Duplicates`

```python
Duplicates.introspect(producer: Producer, *,
                      batch_size: int = 32,
                      threshold: t.Optional[DuplicatesThresholdStrategyType] = None  # default Slope()
                      ) -> Duplicates

duplicates.results   # Mapping[str, Sequence[Duplicates.DuplicateSetCandidate]]
duplicates.count     # int, number of elements in the producer
```

`DuplicateSetCandidate` fields: `std: float`, `mean: float` (distance to centroid), `projection: Optional[np.ndarray]` (2-D PCA, only when cluster size > 5), `indices: Sequence[int]`, `batch: Batch`, property `size`.

Threshold strategies (`Duplicates.ThresholdStrategy`):
- `Percentile(percentile: float)` — e.g. `98.5` means 98.5% of pairs are *not* considered close.
- `Slope(sensitivity: int = 5)` — elbow finder; `ValueError("`sensitivity` must be > 2")` in `__post_init__`. Docstring: "A lower sensitivity (down to 2) will consider more items to be close... A sensitivity of 20 ... is a reasonable large value."

Algorithm (`_duplicates.py:278-428`):
1. `_accumulate_batches(producer, batch_size=batch_size)` — **all data in RAM**.
2. Per-response **L2 normalization per column**: `l2 = np.linalg.norm(responses, axis=0); normalized = responses / l2` — "this prevents large values in a single column from dominating the distance metric".
3. `annoy.AnnoyIndex(dim, "euclidean")`, `index.set_seed(0)`, `index.build(30)` (30 trees — "the higher the number, the better the precision when querying (at the cost of time and memory)").
4. `n = 10` nearest neighbors per item ("n can be anything > 2 ... a value of 10 gives similar distance threshold results as the previous kCDTree implementation").
5. Threshold applied to `np.trim_zeros(np.sort(distances.reshape(count*n)))`.
6. Clusters = **transitive closure** of overlapping neighbor sets (`Duplicates._combine_clusters`).
7. Within a cluster: order elements by a 1-D PCA projection (if len > 2); compute a 2-D PCA `projection` (if len > 5).

Traversal idiom (docstring + docs):

```python
for response_name, clusters in duplicates.results.items():
    clusters = sorted(clusters, key=lambda x: x.mean)   # sort by mean distance to centroid
```

**Gotchas:** run-time is linear in samples **and** dimensions — reduce to ~40 dims first. `assert len(responses.shape) == 2, "Requires 1d vector per element"`. If a normalized column has L2 == 0, `responses / l2` produces NaN/inf (no guard in the code).

### 10.4 `IUA` — Inactive Unit Analysis

```python
IUA.introspect(producer: Producer, *, batch_size: int = 32,
               rtol: float = 1e-05, atol: float = 1e-08) -> IUA
iua.results  # Mapping[str, IUA.Result]
IUA.show(iua, *, vis_type: str = IUA.VisType.TABLE, response_names: Optional[Sequence[str]] = None)
IUA.VisType.TABLE == 'table';  IUA.VisType.CHART == 'chart'
```

`IUA.Result`: `mean_inactive: float`, `std_inactive: float`, `inactive: Sequence[float]` (per-probe counts), `unit_inactive_count: Sequence[float]`, `unit_inactive_proportion: Sequence[float]`.

"Inactive" == `np.isclose(responses, np.zeros_like(responses), rtol=rtol, atol=atol)`. Per-batch-item counts keep dim 0 and flatten the rest. Detects **dying ReLU** / effective-capacity loss.

`IUA.show` errors: `ValueError(f'Invalid response passed: {response}. Try one of: {result_keys}')`, `ValueError("Empty list of layers specified...")`, `ValueError('Unexpected input for parameter `vis_type`...')`; missing deps → `DNIKitException("PIL not available, was 'dnikit[notebook]' installed?")` (**message is wrong — it actually checks pandas**, `_iua.py:215-216`) and `DNIKitException("matplotlib not available, was 'dnikit[notebook]' installed?")`.
`_show_chart` builds `plt.subplots(len(responses), figsize=(7, 70))` — a hard-coded 70-inch-tall figure.

Notebook usage (`inactive_unit_analysis.ipynb`):

```python
response_producer = pipeline(
    data_producer,
    FieldRenamer({"images": "input_1:0"}),
    model(conv2d_responses),
    Transposer(dim=(0, 3, 1, 2))
)
iua = IUA.introspect(response_producer)
IUA.show(iua)                                                    # pandas table
IUA.show(iua, vis_type=IUA.VisType.CHART, response_names=['conv_pw_9'])
```

### 10.5 `PFA` — Principal Filter Analysis (network compression)

```python
PFA.introspect(producer: Producer, *, batch_size: int = 32,
               epsilon_inactive: float = 1e-8) -> PFA

pfa.get_recipe(*, strategy: t.Optional[PFAStrategyType] = None,          # default PFA.Strategy.KL()
                  unit_strategy: t.Optional[PFAUnitSelectionStrategyType] = None  # default L1Max()
              ) -> t.Mapping[str, PFARecipe]

PFA.show(recipe_result: OneOrMany[Mapping[str, PFARecipe]], *,
         vis_type: str = PFA.VisType.TABLE,
         include_columns: Optional[Sequence[str]] = None,
         exclude_columns: Optional[Sequence[str]] = None)

pfa.failed_responses    # Sequence[str] -- layers dropped for having fewer samples than features
pfa._internal_result    # Mapping[str, PFACovariancesResult]  (private, for tests/debugging)
```

`PFA.VisType.TABLE == 'table'`, `PFA.VisType.CHART == 'chart'`.

**Input requirement (verbatim, `_pfa.py:120-128`):** "The responses generated by `producer` are assumed to be **2D (Batch x C)**. Thus it might be necessary to `pipeline` together the `Producer` with a `Processor` (e.g., `Pooler`), that transforms each individual response from multi-dimensional to mono-dimensional." Violating it → `DNIKitException(f'Unable to introspect response {name}, of shape {shape},which has more than two dimensions.')` (note missing space in the message, `_covariances_calculator.py:178-180`).

If a response has fewer samples than features it is skipped and a `warnings.warn` fires:
```
Attempted to compute covariance of data matrix with less data points than features (data_point#, feature#) = (N, C)
```
The layer name lands in `pfa.failed_responses`.

`PFACovariancesResult` (`_covariances_calculator.py:39-101`): `covariances`, `eigenvalues`, `eigenvectors`, `original_output_count`, `inactive_units`. Eigen decomposition via `np.linalg.eigh`, clamped `np.maximum(0.0, eigenvalues)`, returned **descending** (`eigenvalues[::-1], eigenvectors[::-1]`). Inactive units: `var < epsilon_inactive * np.max(var)` where `var = np.abs(np.diag(covariances))`.

Covariance accumulation is **streaming** (`_CovariancesCalculator`): keeps `_count`, `_sum_x`, `_sum_xxt`; `get_centered_covariances()` = `sum_xxt/(n-1) - outer(mean, sum_x/(n-1))`.

**Compression strategies** (`PFA.Strategy`, `_pfa_algorithms.py`):

| Strategy | Signature | Behavior |
|---|---|---|
| `PFA.Strategy.KL` | `KL(interpolation_function: Optional[KLInterpolationFunction] = None)` | Parameter-free heuristic. `kl = scipy.stats.entropy(pk=sum_norm(eigenvalues)+eps, qk=uniform)`; `max_kl = log(C)`; `units_ratio = interpolation(kl, max_kl)`; `recommended = ceil(C * units_ratio)`. Default interpolation is `KL.LinearInterpolation()` = `1 - kl/max_kl`. Diagnostics: `PFAKLDiagnostics(kl_divergence, units_ratio)` |
| `PFA.Strategy.Energy` | `Energy(energy_threshold: float, min_kept_count: int = 0)` | Keep the top eigenvalues until cumulative energy ≥ threshold. `ValueError('energy_threshold should be between 0.0 and 1.0, but it is {v}')`. Logs a warning if `min_kept_count` forces the energy constraint to be violated. Diagnostics: `PFAEnergyDiagnostics(total_kept_energy)` |
| `PFA.Strategy.Size` | `Size(relative_size: float, min_kept_count: int = 0, epsilon_energy: float = 1e-8)` | **Cross-layer**: builds per-layer exclusive cumulative-energy curves, takes `np.percentile(all_values, 100*relative_size)` as a global energy threshold (clamped to `[eps, 1-eps]`), then delegates to `Energy`. `ValueError('relative_size should be between 0.0 and 1.0, ...')` |

**Unit-selection strategies** (`PFA.UnitSelectionStrategy`, `_pfa_units.py`): `AbsMax`, `AbsMin`, `L1Max`, `L1Min` — all `_DirectionalStrategy(distance ∈ {ABS, L1}, direction ∈ {np.nanmax, np.nanmin})`. `PFA.UnitSelectionStrategy.get_algos()` yields one instance of each.

They operate on `|Pearson correlation|` derived from the covariance (`corr = covar / max(sqrt(var_i*var_j), 1e-8)`), with the diagonal and all inactive rows/cols set to NaN. Returns indices of **maximally-correlated (redundant)** units; the first `covariances.inactive_units.shape[0]` entries are the inactive units.

Errors: `ValueError(f'Number of units to keep should be greater than zero but found {n}.')`;
`DNIKitException('Requested to mark all units as correlated but no units are available')`;
`DNIKitException(f'The request to keep {k} cannot be satisfied since there are only {m} active units')`;
`DNIKitException(f'All the L1 values are NaN. This is the |correlation matrix| after {it} iterations: {corr}')`.

`PFARecipe` (`_recommendation.py:58-117`): `original_output_count`, `recommended_output_count`, `maximally_correlated_units: Sequence[int]`, `number_inactive_units: int`, `diagnostics: Union[PFAKLDiagnostics, PFAEnergyDiagnostics, None]`.

`PFA.show` table columns: `["layer name", "original count", "recommended count", "units to keep", "KL divergence", "PFA strategy", "units ratio", "kept energy"]`. Default shown: the first four. `include_columns=[]` ⇒ show **all** columns. `"units to keep"` = `set(range(original)) - set(maximally_correlated_units)`.

**Errors from `PFA.show`:**
- Passing the `PFA` object instead of a recipe →
  `DNIKitException("The output of `PFA.introspect` has been passed into `PFA.show()`. Please pass the output of `pfa.get_recipe` into `PFA.show()`. The default behavior can be used by calling: `pfa = PFA.introspect(); recipe = pfa.get_recipe(); PFA.show(recipe)`")`
- `ValueError("`recipe_result` parameter input is emtpy")` (**sic**, typo in source, `_pfa.py:387`)
- Multiple recipes + `VisType.CHART` → `DNIKitException("Only one recipe's chart can be plotted at a time. ...")`
- `DNIKitException("No columns selected, are the `exclude columns` the same as the ones to `include`")`
- Missing pandas → `DNIKitException("PIL not available, was 'dnikit[notebook]' installed?")` (**message wrong again**, `_pfa.py:229-230`)
- `PFA._is_old_matplotlib_version` gates the `ax.set_xticks(range, names, rotation=...)` 3-arg form for matplotlib ≤ 3.4.

**Notebook-verified PFA workflow** (`notebooks/model_introspection/principal_filter_analysis.ipynb`):

```python
from dnikit.base import pipeline, ImageFormat, ResponseInfo
from dnikit_tensorflow import TFModelExamples, TFDatasetExamples
from dnikit.processors import ImageResizer, Pooler
from dnikit.introspectors import PFA, PFARecipe

mobilenet = TFModelExamples.MobileNet()

conv2d_responses = [
    info.name for info in mobilenet.response_infos.values()
    if info.layer.kind == ResponseInfo.LayerKind.CONV_2D and 'preds' not in info.name
]

cifar10_dataset = TFDatasetExamples.CIFAR10(max_samples=2000)
cifar10_dataset.shuffle()
dataset = pipeline(cifar10_dataset,
                   mobilenet.preprocessing,
                   ImageResizer(pixel_format=ImageFormat.HWC, size=(224, 224)))

producer = pipeline(dataset,
                    mobilenet.model(conv2d_responses),
                    Pooler(dim=(1, 2), method=Pooler.Method.MAX))

pfa = PFA.introspect(producer, batch_size=500)

energy_8_recipes  = pfa.get_recipe(strategy=PFA.Strategy.Energy(energy_threshold=0.8,  min_kept_count=3))
energy_99_recipes = pfa.get_recipe(strategy=PFA.Strategy.Energy(energy_threshold=0.99, min_kept_count=3))
results_table = PFA.show((energy_8_recipes, energy_99_recipes))
results_table['Energy'] = ['0.8']*len(energy_8_recipes) + ['0.99']*len(energy_99_recipes)

pfa_kl_recipe = pfa.get_recipe()                       # == pfa.get_recipe(strategy=PFA.Strategy.KL())
PFA.show(pfa_kl_recipe, include_columns=[])            # all columns
PFA.show(pfa_kl_recipe, vis_type=PFA.VisType.CHART)

abs_max_recipes = pfa.get_recipe(unit_strategy=PFA.UnitSelectionStrategy.AbsMax())
l1_max_recipes  = pfa.get_recipe(unit_strategy=PFA.UnitSelectionStrategy.L1Max())
```

> **Note the doc bug:** `docs/introspectors/model_introspection/network_compression.rst:150-155` shows `pfa.get_recipe(compression=PFA.Strategy.Energy(...))` — the kwarg is **`strategy=`**, not `compression=`. The same page also uses non-existent `PFA.Strategy.SOME_STRATEGY` as a placeholder, and calls `dnikit_model.response_infos()` as a method when it is a **property**.

**PFA does not modify the model.** Docs, emphasized: *"Note that PFA does not compress a network directly! It's important to instead retrain the network model with the suggested layer sizes."* Suggested workflow (`network_compression.rst:358-451`): (1) train, (2) run inference and collect responses, (3) reduce (pool) conv responses to 1 value/filter, (4) `PFA.introspect`, (5) `get_recipe` with a strategy, (6) act on the recipe. "The user is responsible for steps 1 and 6, while all the other steps can be done within DNIKit."

**Published results (docs/index.rst:80-84, network_compression.rst:310-315):** VGG-16 on CIFAR-10 / CIFAR-100 / ImageNet → compression 8× / 3× / 1.4× with accuracy **gain** 0.4% / 1.4pp / 2.4%. MNIST convnet example: Conv2D layers 32→21 and 64→45 gives **40% model-size reduction** (271 KB vs 450 KB) with no significant accuracy cost; `Energy(0.8)` gives >80% compression at ~0.5% accuracy loss (32→7 and 64→14 filters).
Reference: Suau, Zappella, Apostoloff, "Filter Distillation for Network Compression", https://arxiv.org/abs/1807.10585 (WACV 2020).

### 10.6 `DatasetReport` (+ `ReportConfig`)

```python
DatasetReport.introspect(producer: Producer, *,
                         config: t.Optional[ReportConfig] = None,
                         batch_size: int = 1024) -> DatasetReport

report.data                                 # pandas.DataFrame, one row per data sample
report.to_disk(directory='./report_save', *, overwrite=False)
DatasetReport.from_disk(directory) -> DatasetReport
DatasetReport._report_save_data_path == pathlib.Path('report_save_data.pkl')
```

Bundles **Familiarity + Duplicates + DimensionReduction (2-D projection) + a label/ID summary**, and emits a DataFrame shaped for the **Symphony** UI (https://github.com/apple/ml-symphony, https://apple.github.io/ml-symphony/).

`ReportConfig` (`_dataset_report_stages.py:65-134`):

```python
ReportConfig(
    projection: t.Optional[OneOrManyDimStrategies] = <DimensionReduction.Strategy.UMAP(2) or None>,
    duplicates: t.Optional[DuplicatesThresholdStrategyType] = Duplicates.ThresholdStrategy.Slope(),
    familiarity: t.Optional[FamiliarityStrategyType] = Familiarity.Strategy.GMM(),
    dim_reduction: t.Optional[OneOrManyDimStrategies] = None,   # None => auto PCA(40) for >40-dim fields
    split_familiarity_min: int = 50,
)
config.n_stages       # 3 if familiarity or projection; 2 if duplicates; else 1
config.use_dim_reduction  # True if any of familiarity/duplicates/projection
```

- `projection` default comes from `_projection_default()`: if `umap-learn` is missing it logs `"UMAP not available, not running projection in report.To fix, install dnikit['dimreduction']."` and returns `None` (silently disables projection).
- Set any component to `None` to skip it.
- `_DEFAULT_DIMENSIONS = 40`; `_guess_dimension_strategies` peeks the first batch and assigns `PCA(40)` only to fields with `shape[1] > 40`.

**Column naming convention** (this is the Symphony contract — `_dataframe_formatting.py`, `_string_util.remove_special_characters` strips everything outside `[a-zA-Z0-9-_]` and maps spaces to `_`):

```
id
<label_dimension>                                       # one column per LABELS key
duplicates_<response>
projection_<response>_x , projection_<response>_y
familiarity_<response>
splitFamiliarity_<response>_byAttr_<label_dimension>          # value is a dict {label: score}
splitFamiliarity_<response>_byAttr_<label_dim>_<label>        # intermediate, condensed away
```

Verified by `src/dnikit/tests/test_dataset_report.py:504-536`:

```python
overall_title.make_title('response_1')  == 'familiarity_response_1'
split_title.make_title('response_1')    == 'splitFamiliarity_response_1_byAttr_color_blue'
empty_string_title.make_title('response_1') == 'splitFamiliarity_response_1_byAttr_shape_'
partial_title.make_title('response_1')  == 'splitFamiliarity_response_1_byAttr_shape'
_DataframeFamiliarityTitle._format_split_suffix('shape') == '_byAttr_shape'
_DataframeFamiliarityTitle.get_response_name_from_title(
    title='splitFamiliarity_response_b__byAttr_color_blue') == 'response_b_'
```

Duplicates column semantics (`_report_builder_introspectors.py:120-144`): one `pd.Series` per response, `-1` = not in a cluster, otherwise the cluster number:

```
   duplicates_result
0                 -1
3                  0
5                  0
6                  0
```

**Three-stage execution model** (`_dataset_report.py:190-232` + `_dataset_report_stages.py:198-383`) — each stage is one `multi_introspect` call over one pass of data:

- Pre-stage: `pipeline(producer, Composer(convert_labels_metadata_to_str))` — **all `LABELS` values are stringified**, because `_SummaryBuilder` and the split-familiarity filter assume `str`. (Test `test_nonstr_labels` confirms ints/floats/tuples/bools all become their `str()`.)
- If `config.n_stages == 2`: attach the `Cacher` immediately.
- **Stage 1**: `_SummaryBuilder.introspect` + `DimensionReduction.introspect` (or a `_introspector_stub` no-op that just drains the producer).
- If `n_stages == 3`: `producer = pipeline(producer, stage_1_results.overall_dim_reduction, cacher)`.
- **Stage 2**: `_DuplicatesBuilder` + projection `DimensionReduction.introspect` + overall `_NamedFamiliarity.from_overall_familiarity` + **one split-familiarity introspector per (label_dimension, label)** (`_SplitFamiliarity.get_label_introspectors`).
- **Stage 3**: `_ProjectionBuilder` + `_FamiliarityBuilder` (overall) + one `_FamiliarityBuilder` per split model; then `_FamiliarityBuilder.condense_dataframes_by_labels` collapses per-label columns into one dict-valued column per (response, label_dimension).
- Finally `pd.concat([...], axis=1)`.

**Requirements & gotchas:**
- `Batch.StdKeys.IDENTIFIER` is **required** (`_SummaryBuilder` reads it unconditionally). Docs: *"For the moment, the `Batch.StdKeys.IDENTIFIER` should be a path to the image data."*
- `Batch.StdKeys.LABELS` is optional; without labels there is no split familiarity, and columns reduce to `{id, duplicates_<r>, projection_<r>_x, projection_<r>_y, familiarity_<r>}` (test `test_no_labels_report`).
- Labels with fewer than `split_familiarity_min` (default 50) samples are dropped from split familiarity (`_SummaryBuilder.filtered_labels`).
- pandas missing → `DNIKitException("pandas not available, was dnikit['dataset_report'] or dnikit['dataset_report_base'] installed?")` — **both names are wrong**: the real extras are `dataset-report` (hyphen) and there is no `dataset_report_base`.
- `to_disk` without `overwrite=True` on an existing file → `FileExistsError('Report file already exists at this path.Set "overwrite=True" ...')`; `from_disk` on a dir without the pickle → `FileNotFoundError(f"{directory} missing necessary file: report_save_data.pkl. Try saving report using report.to_disk() method.")`.
- Storage format is a **pandas pickle** — version-fragile, not a portable interchange format.
- Symphony (the viewer) "operates only on images, audio, and tabular data".

**Full runnable example** (docs/introspectors/data_introspection/dataset_report.rst:44-64):

```python
from dnikit.introspectors import DatasetReport
from dnikit_tensorflow import TFDatasetExamples, TFModelExamples
from dnikit.processors import Cacher, ImageResizer, Pooler
from dnikit.base import pipeline

cifar10 = TFDatasetExamples.CIFAR10(attach_metadata=True)
mobilenet = TFModelExamples.MobileNet()
producer = pipeline(
   cifar10,
   ImageResizer(pixel_format=ImageResizer.Format.HWC, size=(224, 224)),   # NOTE: see bug below
   mobilenet(requested_responses=['conv_pw_13']),
   Pooler(dim=(1, 2), method=Pooler.Method.MAX),
   Cacher()
)
report = DatasetReport.introspect(producer)
```

> **Doc bug:** `ImageResizer.Format.HWC` does not exist. The real symbol is `dnikit.base.ImageFormat.HWC`, passed as `ImageResizer(pixel_format=ImageFormat.HWC, size=(224, 224))` — which is what all the notebooks use. `ImageResizer.Format` appears in `dataset_report.rst`, `duplicates.rst`, `familiarity.rst`, and `docs/how_to/introspect.rst`.

Only-duplicates config:

```python
from dnikit.introspectors import DatasetReport, ReportConfig
config = ReportConfig(projection=None, familiarity=None)
report = DatasetReport.introspect(producer, config=config)
```

---

## 11. PyTorch integration (`dnikit_torch`)

`__all__` = `["ProducerTorchDataset", "TorchProducer"]`.

### 11.1 `TorchProducer` — PyTorch DataLoader → DNIKit Producer

```python
@dataclasses.dataclass(frozen=True)
class TorchProducer(Producer):
    data_loader: DataLoader
    mapping: t.Sequence[TORCH_PRODUCER_MAPPING]
    anonymous_field_name: str = "_"

TORCH_PRODUCER_MAPPING = t.Union[str, Batch.DictMetaKey, Batch.MetaKey,
                                 t.Callable[[t.Any, Batch.Builder], None]]
```

Positional mapping semantics:
- `str` → `batch.fields[name]` (Tensor → `.detach().cpu().numpy()`, list → `np.array`, ndarray passthrough, else `ValueError`)
- `Batch.MetaKey` → `batch.metadata[key] = value.tolist()` (Tensor) or the sequence directly
- `Batch.DictMetaKey` → wraps under `anonymous_field_name` (`"_"`) unless the value is a `dict`, in which case keys become metadata fields
- `None` → discard that positional value
- callable → `mapping(value, builder)` custom

```python
key1 = Batch.DictMetaKey[int]("KEY1")
key2 = Batch.DictMetaKey[t.Mapping[str, str]]("KEY2")
producer = TorchProducer(loader, ["image", None, key1, key2])
# element.metadata[key1] == {"_": 50}
# element.metadata[key2] == {"k1": "v1", "k2": "v2"}
```

**Gotchas:**
- `TorchProducer.batch_size` == `data_loader.batch_size or 100`; calling `producer(batch_size)` with a different value raises
  `ValueError('The Torch DataLoader used in this instance produces batches of size {n}, requested batch size: {m}')` — **so a `TorchProducer` cannot be fed to an introspector with a mismatched `batch_size` kwarg.**
- `assert not isinstance(self.mapping, str)` — passing a bare string instead of a list is a common mistake.
- List-of-lists metadata is **transposed**: `list(map(list, zip(*value)))` — "lists of `[a, b, c, ...]` are expected, not `[a, a, a, ...]`".

Verified behaviors (`src/dnikit_torch/tests/test_torch_producer.py`, DataLoader `batch_size=2`):

```python
_run_producer([7],            ["image", key1]).metadata[key1] == {"_": [7, 7]}
_run_producer(["a"],          ["image", key1]).metadata[key1] == {"_": ["a", "a"]}
_run_producer([[7, 8]],       ["image", key1]).metadata[key1] == {"_": [[7, 8], [7, 8]]}
_run_producer([["cat","dog"]],["image", key1]).metadata[key1] == {"_": [["cat","dog"],["cat","dog"]]}
_run_producer([{"k1":"v1","k2":"v2"}], ["image", key1]).metadata[key1] == {"k1":["v1","v1"], "k2":["v2","v2"]}
_run_producer([7, 8], ["image", None, key2]).metadata[key2] == {"_": [8, 8]}
```

### 11.2 `ProducerTorchDataset` — DNIKit Producer → PyTorch `IterableDataset`

```python
@dataclasses.dataclass(frozen=True)
class ProducerTorchDataset(IterableDataset):
    producer: Producer
    mapping: t.Sequence[PRODUCER_TORCH_MAPPING]
    batch_size: int = 100                       # size pulled from the Producer, independent of DataLoader
    transforms: t.Optional[t.Mapping[str, t.Callable[[torch.Tensor], torch.Tensor]]] = None
```

```python
def transform(element: Batch.ElementType) -> np.ndarray:
    # note: pycharm requires a writable copy of the ndarray
    return element.fields["image"].reshape((128, 32)).copy()

ds = ProducerTorchDataset(producer, ["image", "image2", key1, transform])

dataset = ProducerTorchDataset(producer, ["image", "mask", "heights"],
    transforms={"image": transforms.RandomCrop(32, 32),
                "mask": transforms.Compose([transforms.CenterCrop(10), transforms.ColorJitter()])})
```

- Field data is `.copy()`-ed because DNIKit **freezes** batch arrays (`writeable = False`) and `torch.Tensor` requires writable memory.
- Unlike typical torchvision datasets (`transform` / `target_transform`), transforms are keyed by **field name**.
- A `DictMetaKey` whose dict has a single field is unwrapped to just that field's value.

---

## 12. Typing & exceptions helpers

`dnikit.typing` (`_dnikit_types.py`):

```python
OneOrMany[_T]      = Union[_T, Collection[_T]]
OneManyOrNone[_T]  = Union[None, _T, Collection[_T]]
PathOrStr          = Union[str, pathlib.Path]
StringLike         = Any
TrainTestSplitType = Tuple[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]

resolve_one_or_many(x, cls)         -> AbstractSet[_T]
resolve_one_many_or_none(x, cls)    -> Optional[AbstractSet[_T]]
resolve_one_or_many_to_list(x, cls) -> List[_T]
resolve_path_or_str(x)              -> pathlib.Path
```

`dnikit.exceptions`:

```python
class DNIKitException(RuntimeError):        # .message; __repr__ = f"{cls}: {message}"
class DNIKitDeprecationWarning(DeprecationWarning)
def enable_deprecation_warnings(*, error: bool = False) -> None
```

Notebooks open with:

```python
from dnikit.exceptions import enable_deprecation_warnings
enable_deprecation_warnings(error=True)   # treat DNIKit deprecation warnings as errors
```

`pytest.ini` sets `filterwarnings = error::dnikit.exceptions.DNIKitDeprecationWarning`.

`dnikit._availability` — module-presence checks (all just inspect `sys.modules`, so **the caller must `try: import X except ImportError: pass` first**):
`_opencv_available()`, `_PIL_available()`, `_tensorflow_available()` (requires *both* `tensorflow` and `dnikit_tensorflow`), `_matplotlib_available()`, `_umap_available()` (actually attempts the import then checks `"umap.umap_" in sys.modules`), `_pandas_available()`.

`dnikit._logging._Logged` gives every `PipelineStage` a `.logger` named by fully-qualified class name. Module-level loggers seen: `"dnikit.introspectors.pfa"`, `"dnikit.introspectors.DatasetReport"`, `"dnikit_tensorflow.TF2"`, `"dnikit_tensorflow.TF1"`.

`dnikit._dict_utils`: `rename_keys`, `delete_keys`, `seq_of_dict_to_dict_of_seq`, `dict_of_seq_to_seq_of_dict`, `subscript_dict_of_seq`, `ordered_values_tuple`.

---

## 13. Debugging recipes (from docs/general/support.rst)

```python
from dnikit.base import peek_first_batch, pipeline

b          = peek_first_batch(producer, batch_size=1)                    # raw producer
b_processor= peek_first_batch(pipeline(producer, processor1), batch_size=2)   # after preprocessing
b_full     = peek_first_batch(response_producer, batch_size=1)           # whole pipeline
```

```python
from dnikit.processors import PipelineDebugger, SnapshotSaver
producer = pipeline(stub_dataset_metadata, SnapshotSaver(save="snap"), PipelineDebugger())
batch = peek_first_batch(producer, 5)
output = PipelineDebugger.dump(batch)
```

`PipelineDebugger.dump` output shape:

```
<label> Batch(batch_size=N) {
field: (shape)
...
Snapshots:
snap: ['field', ...]

Metadata:
Batch.MetaKey(name=...)
Batch.DictMetaKey(name=...)Batch.DictMetaKey(name=...): ['k1','k2']
}
```

Other documented issues: MacOS `SSL: CERTIFICATE_VERIFY_FAILED` → run `/Applications/Python\ 3.x/Install\ Certificates.command`.

---

## 14. Data-quality → model-quality workflow (how the pieces compose)

The canonical end-to-end shape used across every notebook:

```python
producer = pipeline(
    dataset_producer,                                            # 1. data (lazy)
    model_preprocessor,                                          # 2. framework preprocessing
    ImageResizer(pixel_format=ImageFormat.HWC, size=(224, 224)), # 3. shape fit
    model(requested_responses=['conv_pw_13']),                   # 4. inference -> responses
    Pooler(dim=(1, 2), method=Pooler.Method.MAX),                # 5. spatial reduce -> BxC
    Cacher()                                                     # 6. cache expensive inference
)
reducer  = DimensionReduction.introspect(producer, strategies=DimensionReduction.Strategy.PCA(40))
reduced  = pipeline(producer, reducer)                           # 7. 1024 -> 40 dims
```

Then, depending on the goal:

| Goal | Introspector | Consumes |
|---|---|---|
| dataset QA dashboard | `DatasetReport.introspect(producer)` | pooled responses + IDENTIFIER (+ LABELS) |
| duplicate / near-dup removal | `Duplicates.introspect(reduced)` | 40-dim responses |
| rare data / mislabeled data / bias | `Familiarity.introspect(reduced)` then `pipeline(reduced, familiarity)` | 40-dim responses |
| train/test distribution gap | fit `Familiarity` on train, score both splits, compare mean scores | 40-dim responses |
| 2-D visualization | `DimensionReduction.Strategy.UMAP(2)` / `PaCMAP(2)` / `TSNE(2)` after PCA(40) | |
| dead-unit / training health | `IUA.introspect(response_producer)` | raw conv responses (no pooling needed) |
| shrink the model before shipping | `PFA.introspect(pooled_responses)` → `pfa.get_recipe(...)` → **retrain** | pooled `BxC` responses |

Notice: `IUA` wants **un-pooled** responses (it counts inactive units per element, flattening non-batch dims itself); `PFA`, `Familiarity`, `Duplicates`, `DimensionReduction` all want **2-D `BxC`** — pool or flatten first.

---

## 15. Consolidated gotchas / footguns

1. **Nothing runs until `introspect()`** — a `pipeline()` is only a promise. `peek_first_batch` is the debugger.
2. **`Batch` field arrays are frozen** (`flags.writeable = False`). Copy before mutating or handing to torch.
3. **All fields/metadata/snapshots in a `Batch` must have the same length**; snapshots may not nest.
4. **`Model.__call__(None)` requests every layer** — potentially enormous.
5. **Field↔input auto-rename only works for 1-input/1-field models with matching non-batch shape**; otherwise use `FieldRenamer`.
6. **TF1 vs TF2 response names differ**: `"conv_pw_13/Conv2D:0"` vs `"conv_pw_13"`. Docs still show the old `':0'` names in several places.
7. **Keras 3 breaks TF2 introspection** unless you have commit `2f39056` (no `type_spec` on `KerasTensor`; generic `keras_tensor_N` names). Even after the fix, `ResponseInfo.Layer.typename` may be meaningless under Keras 3.
8. **`TFModelWrapper.load_keras_model` round-trips through a temp `.h5`** — likely to fail with Keras 3.
9. **`dnikit[complete]` references a nonexistent `duplicates` extra** and omits `torch`.
10. **`tf2` extra is an unpinned `tensorflow`** — no upper bound, hence the Keras 3 break.
11. **Python 3.9.7 is broken** (dataclass-inheriting-Protocol `__init__` bug).
12. **TF1 requires Python ≤ 3.7**, `numpy<1.19`, `protobuf<4.0`, `Keras<2.4`, `h5py<3.0`, `tensorflow<2.0`.
13. **Version lockstep**: `dnikit`, `dnikit_tensorflow`, `dnikit_torch` all assert equal `__version__` at import.
14. **Memory**: `Familiarity` (GMM) and `Duplicates` call `_accumulate_batches` — the entire response set lands in RAM. `DimensionReduction.Strategy.PCA` is the only streaming reducer; `StandardPCA`/`TSNE`/`UMAP`/`PaCMAP` accumulate.
15. **`Cacher` is single-use per pipeline** and writes **pickles** to a temp dir; `Cacher.clear()` nukes *all* dnikit caches under the temp dir.
16. **`multi_introspect` requires a uniform `batch_size` across introspectors**, and catching `AssertionError` inside an introspector can deadlock.
17. **`TorchProducer` rejects a `batch_size` different from its DataLoader's.**
18. **`DimensionReduction` requires 2-D fields**; `PFA` requires 2-D; `Duplicates` asserts 2-D.
19. **`PFA.show(pfa)` is wrong** — pass `pfa.get_recipe()`.
20. **`ImageProducer` requires all images to share HWC**; images are loaded via OpenCV (BGR→RGB conversion applied).
21. **`ImageResizer(size=...)` is `(width, height)`**, and ignores aspect ratio.
22. **`DatasetReport` stringifies all `LABELS`** and requires `Batch.StdKeys.IDENTIFIER`.
23. **`umap` (PyPI) ≠ `umap-learn`** — DNIKit needs `umap-learn`, imported as `umap`.
24. **UMAP/PaCMAP imports are deferred because of "numba SIGSEGV on task cleanup."**
25. **Several error strings are wrong**: "PIL not available" when pandas is missing (both `PFA` and `IUA`); `dnikit['dataset_report']`/`dnikit['dataset_report_base']` instead of `dnikit[dataset-report]`; typo `"emtpy"`; `"thebatch_size"`.
26. **Doc bug: `ImageResizer.Format.HWC` doesn't exist** — use `dnikit.base.ImageFormat.HWC`.
27. **Doc bug: `pfa.get_recipe(compression=...)`** — the kwarg is `strategy=`.
28. **Doc bug: `model.response_infos()`** is written as a call in `network_compression.rst` and `inactive_units.rst`; it is a **property**.
29. `LayerKind.LINEAR` and `LayerKind.DENSE` are the same enum member (`1000`); `MAX_POOLING_3D` is `3003` (there is no `3002`).
30. `PFA` silently **drops layers with fewer samples than features** (into `pfa.failed_responses`) with a `warnings.warn`.
31. Familiarity score sign: code returns log-density (higher = more familiar); the docs' math section describes it as *negative* log-likelihood. Sort `reverse=True` for "most familiar" (as the notebooks do).
32. Notebook duplication: `notebooks/` and `docs/notebooks/` are two copies of the same files; a docs build re-executes them all.

---

## 16. Citation & references

```bibtex
@online{DNIKit,
     author = {Welsh, Megan Maher; Koski, David; Sarabia, Miguel; Sivakumar, Niv; Arawjo, Ian;
               Joshi, Aparna; Doumbouya, Moussa; Suau, Xavier; Zappella, Luca; Apostoloff, Nicholas},
     title = {Data and Network Introspection Kit},
     year = 2023,
     url = {https://github.com/apple/dnikit},
}
```

Per-algorithm citations (docs/reference/how_to_cite.rst):
- **Symphony UI** (visualizing DatasetReport/Familiarity/Duplicates/Projection): Bäuerle, Cabrera, Hohman, Maher, Koski, Suau, Barik, Moritz, "Symphony: Composing Interactive Interfaces for Machine Learning", CHI 2022.
- **PFA**: Suau Cuadros, Zappella, Apostoloff, "Filter distillation for network compression", WACV 2020, https://arxiv.org/abs/1807.10585.
- **TSNE**: van der Maaten & Hinton 2008. **UMAP**: McInnes, Healy, Melville, arXiv:1802.03426. **PaCMAP**: Wang, Huang, Rudin, Shaposhnik, JMLR 22(201), 2021. **ANNOY**: Bernhardsson 2018.
- **IUA** and **Familiarity (no vis)**: no additional citation.

---

## 17. Source inventory (every file I actually read this session)

### Repo metadata / build
- `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CITATION.cff`, `CODEOWNERS`, `.bumpversion.cfg`, `.gitattributes`
- `Makefile`, `pytest.ini`, `conftest.py`, `mypy.ini`
- `src/dnikit/pyproject.toml`, `src/dnikit/README.md`
- `src/dnikit_tensorflow/pyproject.toml`, `src/dnikit_tensorflow/README.md`
- `src/dnikit_torch/pyproject.toml`, `src/dnikit_torch/README.md`
- `git log --oneline -50` (3 commits present at depth 50); `git show 2f39056` (full diff), `git show b44b14f --stat`

### `dnikit` core source
- `src/dnikit/dnikit/__init__.py`
- `src/dnikit/dnikit/_availability.py`, `_logging.py`, `_dict_utils.py` (signatures)
- `src/dnikit/dnikit/typing/_dnikit_types.py`
- `src/dnikit/dnikit/exceptions/_dnikit_exceptions.py`
- `src/dnikit/dnikit/base/__init__.py`, `_producer.py`, `_pipeline.py`, `_model.py`, `_introspector.py`,
  `_response_info.py`, `_multi_introspect.py`, `_image_producer.py`, `_cached_producer.py`, `_traintest_producer.py`
- `src/dnikit/dnikit/base/_batch/_batch.py`, `_storage.py`, `_fields.py`, `_metadata_storage.py`
- `src/dnikit/dnikit/processors/__init__.py`, `_base_processor.py`, `_processors.py`, `_image_processors.py`, `_metadata_processors.py`
- `src/dnikit/dnikit/samples/__init__.py`, `_stub_producer.py`, `_stub_datasets.py`
- `src/dnikit/dnikit/introspectors/__init__.py`
- `.../introspectors/_duplicates.py`
- `.../introspectors/_dim_reduction/_dimension_reduction.py`, `_reducers.py`, `_protocols.py`
- `.../introspectors/_familiarity/_familiarity.py`, `_protocols.py`, `_gmm_familiarity.py`, `_gaussian_familiarity.py`
- `.../introspectors/_iua/_iua.py`
- `.../introspectors/_pfa/_pfa.py`, `_pfa_algorithms.py`, `_pfa_units.py`, `_covariances_calculator.py`, `_recommendation.py`
- `.../introspectors/_report/_dataset_report.py`, `_dataset_report_stages.py`, `_report_builder_introspectors.py`,
  `_familiarity_wrappers.py`, `_dataframe_formatting.py`, `_string_util.py`

### `dnikit_tensorflow`
- `dnikit_tensorflow/__init__.py`, `_sample_models.py`, `_sample_datasets.py`
- `_tensorflow/_tensorflow_loading.py`, `_tensorflow_protocols.py`, `_tensorflow_file_loaders.py`
- `_tensorflow/_tf2_model.py`, `_tf2_loading.py`, `_tf2_file_loaders.py`
- `_tensorflow/_tf1_model.py`, `_tf1_loading.py`, `_tf1_file_loaders.py` (grep of class/can_load/load)
- `samples/__init__.py`, `samples/_simple_cnn_keras.py`

### `dnikit_torch`
- `dnikit_torch/__init__.py`, `_torch_producer.py`
- `tests/test_torch_producer.py` (first 140 lines)

### Tests
- `src/dnikit/tests/test_dataset_report.py` (full)
- `src/dnikit/tests/test_familiarity.py` (full)
- `src/dnikit/tests/test_duplicates.py` (full)
- `src/dnikit/tests/test_pfa.py` (lines 1-250 + list of all test names)
- `src/dnikit/tests/test_multi_introspect.py` (lines 1-90)
- `src/dnikit/tests/test_cached_producer.py` (lines 1-120)
- `src/dnikit_tensorflow/tests/test_tf2_model_loaders.py` (full)
- `src/dnikit_tensorflow/tests/test_tf_examples.py` (full)

### Docs (`.rst`)
- `docs/index.rst`, `docs/conf.py`
- `docs/general/installation.rst`, `docs/general/support.rst`, `docs/general/example_notebooks.rst`
- `docs/how_to/dnikit_concepts.rst`, `connect_model.rst`, `connect_data.rst`, `introspect.rst`
- `docs/introspectors/data_introspection.rst`, `model_introspection.rst`
- `docs/introspectors/data_introspection/{dataset_report,familiarity,duplicates,dimension_reduction}.rst`
- `docs/introspectors/model_introspection/{network_compression,inactive_units}.rst`
- `docs/utils/data_producers.rst`, `docs/utils/pipeline_stages.rst`
- `docs/api/index.rst`, `docs/api/dnikit/index.rst`, `docs/api/tensorflow/index.rst`, `docs/api/torch/index.rst`
- `docs/dev/contributing.rst`, `docs/reference/how_to_cite.rst`

### Notebooks (all code cells dumped verbatim via a json script)
- `notebooks/data_introspection/dataset_report.ipynb`
- `notebooks/data_introspection/duplicates.ipynb`
- `notebooks/data_introspection/dimension_reduction.ipynb`
- `notebooks/data_introspection/familiarity_for_rare_data_discovery.ipynb`
- `notebooks/data_introspection/familiarity_for_dataset_distribution.ipynb`
- `notebooks/model_introspection/principal_filter_analysis.ipynb`
- `notebooks/model_introspection/inactive_unit_analysis.ipynb`

---

## 18. Open questions / unverified

1. **Does DNIKit 2.0.0 + commit 2f39056 actually run under Keras 3 / TF 2.16+?** The commit fixes response-metadata extraction and layer classification, but `TFModelWrapper.load_keras_model` still saves to a bare `.h5`, `_TF2KerasWholeModelLoader.can_load` still keys on `.h5`, and `_Tensorflow2ModelDetails.run_inference` still builds `tf.keras.Model(inputs=[self.model.input], outputs=[...])` — all three are areas Keras 3 changed. **UNVERIFIED** — I did not execute anything (no TF installed in this session).
2. **Is `_TF2SavedKerasModelLoader` still viable?** `tf.saved_model.contains_saved_model` + `tf.keras.models.load_model(dir)` behaves differently under Keras 3 (`.keras` format). **UNVERIFIED.**
3. **Is there a `.keras` (Keras 3 native) loader?** Not in this tree — `can_load` checks only `.h5`, SavedModel dirs, and arch+weights dirs. `.keras` files would fall through to `DNIKitException('DNIKit unable to load TF model from path: ...')`. **Confirmed by reading the loaders; not executed.**
4. **What are GitHub issues #1–#3?** Only #2 ("Fixes #2") and PR #4 are referenced in the git history; the clone has no issue data.
5. **Is there a `develop` branch?** `docs/dev/contributing.rst` says the dev branch is `develop`, but this shallow clone only has `main`.
6. **Symphony integration details** (`apple/ml-symphony`) — DNIKit only emits the DataFrame; the actual widget/API contract lives in that other repo. Column naming was reverse-engineered from `_dataframe_formatting.py` + tests here.
7. **`dnikit[complete]` resolution** — whether pip errors on the undefined `duplicates` extra or just warns. **UNVERIFIED** (pip behavior is normally a warning for unknown extras, but this is a self-reference).
8. **Any relationship to Apple's 2026 Foundation Models / Core AI / MLX stack?** None found in this repo: no MLX, no Core ML, no Swift, no Speech, no Evaluations framework references anywhere. The connection is conceptual (data/model quality for on-device ML), not code-level.
9. **PFA `Size` strategy semantics vs docs**: docs describe `relative_size` as "percentage of the weights", but the implementation takes a **percentile over the pooled per-layer cumulative-energy curves**, which is a proxy for channel fraction, not weight fraction. Whether these coincide in practice is **UNVERIFIED**.
10. **`epsilon_energy` in `PFA.Strategy.Size`**: docs example passes `epsilon_energy=0.6` and describes it as "ensures that at least 0.6 of the energy is preserved", but in code it is only a clamp keeping the derived threshold within `[eps, 1-eps]` (default `1e-8`). The docs' description appears **wrong**.
11. Whether the `familiarity` score sign discrepancy (docs say negative log-likelihood; code returns `logsumexp`) is a doc bug or a deliberate re-definition. **Leaning doc bug.**
