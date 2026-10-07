#!/usr/bin/env python3
"""Execute named guide fences on a native Core AI host; write an honest JSON record.

Run using python -I in a trusted pinned environment, from a separate reviewed
runner checkout. --reviewed-revision explicitly authorizes the immutable source
commit; this is a trust policy, not a sandbox. This is not part of
portable unittest discovery and never installs dependencies itself.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import stat
import traceback
import tempfile

# Everything before load_trusted_reader() is standard-library-only. Candidate
# Git configuration, helper modules, bytecode and working-tree fences are untrusted.
import hashlib
import os
import re
import types


def git_read(root, *arguments):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    command = ["/usr/bin/git", "-C", str(root), "--no-replace-objects",
               "--work-tree=" + str(root), "-c", "core.fsmonitor=false",
               "-c", "core.hooksPath=" + os.devnull, *arguments]
    try:
        return subprocess.run(command, env=env, check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", b"").decode(errors="replace").strip()
        raise ValueError(f"cannot read reviewed Git snapshot: {detail or error}") from error


def object_id(payload, kind="blob"):
    return hashlib.sha1(kind.encode() + b" " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def reviewed_tree(root, revision):
    """Verify the full commit/tree chain; recursive ls-tree alone trusts inner trees."""
    commit = git_read(root, "cat-file", "commit", revision)
    if object_id(commit, "commit") != revision:
        raise ValueError("Git commit digest mismatch")
    match = re.match(rb"tree ([0-9a-f]{40})\n", commit)
    if match is None:
        raise ValueError("reviewed commit has no valid tree")

    def walk(oid, prefix="", ancestors=()):
        if oid in ancestors:
            raise ValueError("cyclic Git tree")
        payload = git_read(root, "cat-file", "tree", oid)
        if object_id(payload, "tree") != oid:
            raise ValueError(f"Git tree digest mismatch: {prefix or '.'}")
        offset, seen = 0, set()
        while offset < len(payload):
            space, end = payload.find(b" ", offset), payload.find(b"\0", offset)
            if space < offset or end < space or end + 21 > len(payload):
                raise ValueError("malformed Git tree entry")
            mode = payload[offset:space].decode("ascii")
            name = payload[space + 1:end].decode("utf-8")
            child = payload[end + 1:end + 21].hex()
            offset = end + 21
            if name in seen or name in ("", ".", "..") or "/" in name:
                raise ValueError(f"unsafe/duplicate Git tree entry: {name}")
            seen.add(name)
            relative = prefix + name
            if mode == "40000":
                yield from walk(child, relative + "/", (*ancestors, oid))
            else:
                yield mode, child, relative

    yield from walk(match.group(1).decode())


def clean_snapshot(root, revision):
    """Read raw approved blobs and check bytes/index; never run status or filters."""
    root = Path(root).resolve()
    if git_read(root, "rev-parse", "HEAD").decode().strip() != revision:
        raise ValueError(f"{root}: HEAD differs from reviewed revision {revision}")
    if git_read(root, "cat-file", "-t", revision).strip() != b"commit":
        raise ValueError("reviewed revision must identify a commit")
    expected, documents = {}, {}
    for mode, oid, relative in reviewed_tree(root, revision):
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"unsafe tracked path: {relative}")
        if mode not in ("100644", "100755"):
            raise ValueError(f"unsupported tracked mode {mode}: {relative}")
        expected[relative] = (mode, oid)
        payload = git_read(root, "cat-file", "blob", oid)
        if object_id(payload) != oid:
            raise ValueError(f"Git object digest mismatch: {relative}")
        target = root / relative
        if any(parent.is_symlink() for parent in (target, *target.parents) if parent != root):
            raise ValueError(f"symlink in tracked path: {relative}")
        try:
            actual = target.read_bytes()
            actual_mode = "100755" if target.stat().st_mode & 0o111 else "100644"
        except OSError as error:
            raise ValueError(f"missing tracked file: {relative}") from error
        if actual_mode != mode or object_id(actual) != oid:
            raise ValueError(f"non-reviewed tracked edit: {relative}")
        documents[relative] = payload
    indexed = {}
    for entry in git_read(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        name = raw_path.decode()
        if stage != "0" or name in indexed:
            raise ValueError(f"unmerged index entry: {name}")
        indexed[name] = (mode, oid)
    if indexed != expected:
        raise ValueError(f"{root}: staged files differ from the reviewed tree")
    extra = git_read(root, "ls-files", "--others", "--exclude-standard", "-z")
    if extra:
        raise ValueError(f"{root}: non-ignored untracked files: " + extra.decode().replace("\0", ", "))
    return documents


def approved_snapshots(runner_root, source_root, revision, *, isolated, optimize):
    if not isolated:
        raise ValueError("native verification requires python -I from a trusted runner checkout")
    if optimize:
        raise ValueError("optimized Python (-O/-OO) disables parity assertions and is unsupported")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("--reviewed-revision requires a full lowercase 40-hex commit SHA")
    runner_root, source_root = Path(runner_root).resolve(), Path(source_root).resolve()
    if runner_root == source_root:
        raise ValueError("runner and source must be separate checkouts; review the runner independently")
    runner_revision = git_read(runner_root, "rev-parse", "HEAD").decode().strip()
    runner = clean_snapshot(runner_root, runner_revision)
    source = clean_snapshot(source_root, revision)
    return runner_revision, runner, source


def load_trusted_reader(runner_documents):
    """Load verified source bytes, without filesystem imports or ignored .pyc files."""
    package = types.ModuleType("scripts")
    package.__path__ = []
    sys.modules["scripts"] = package
    for name in ("mdlinks", "coreai_examples"):
        relative = f"scripts/{name}.py"
        module = types.ModuleType("scripts." + name)
        module.__file__ = relative
        module.__package__ = "scripts"
        sys.modules[module.__name__] = module
        exec(compile(runner_documents[relative], relative, "exec"), module.__dict__)
    return sys.modules["scripts.coreai_examples"]


def snapshot_examples(reader, documents):
    examples, seen = [], set()
    for relative, payload in sorted(documents.items()):
        path = Path(relative)
        if (len(path.parts) < 2 or path.parts[0] != "guides" or path.suffix != ".md"
                or not any(path.parts[1].startswith(f"part-{part:02d}-") for part in reader.PARTS)):
            continue
        for example in reader.python_fences(payload.decode("utf-8"), path):
            if example.id:
                if example.id in seen:
                    raise ValueError(f"{path}:{example.line}: duplicate corpus example ID {example.id}")
                seen.add(example.id)
            examples.append(example)
    errors = [f"{e.path}:{line}: removed .optimize() call" for e in examples
              if e.historical is None for line in reader.optimizer_calls(e)]
    if errors:
        raise ValueError("\n".join(errors))
    return {e.id: e for e in examples if e.id}


def json_details(value):
    """Normalize supported measurements without hiding invalid data as strings."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite fixture detail")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("fixture detail keys must be strings")
        return {key: json_details(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_details(item) for item in value]
    # NumPy is imported only after the immutable trust preflight. Do not import
    # it just to serialize a setup failure or a portable fixture.
    numpy = sys.modules.get("numpy")
    if numpy is not None:
        if isinstance(value, getattr(numpy, "ndarray", ())):
            return json_details(value.tolist())
        if isinstance(value, getattr(numpy, "generic", ())):
            item = value.item()
            if type(item) is type(value):
                raise TypeError(f"unsupported NumPy detail: {type(value).__name__}")
            return json_details(item)
    raise TypeError(f"unsupported fixture detail: {type(value).__name__}")


class RecordWriteError(OSError):
    """Publication failed; the previous complete checkpoint remains authoritative."""


def publish_record(path, record):
    temporary = None
    try:
        payload = json.dumps(record, indent=2, allow_nan=False) + "\n"
        try:
            publish_mode = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError:
            current_umask = os.umask(0)
            os.umask(current_umask)
            publish_mode = 0o666 & ~current_umask
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), publish_mode)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as error:
        raise RecordWriteError(f"cannot publish verification record {path}: {error}") from error
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


class RunRecorder:
    def __init__(self, path, record):
        self.path, self.record = path, record
        self.record["run_status"] = "running"
        publish_record(self.path, self.record)

    def check(self, name, fn, expected_error=None):
        result = fixture_result(name, fn, expected_error)
        self.record["fixtures"].append(result)
        publish_record(self.path, self.record)
        print(result["name"], result["outcome"], flush=True)
        return result

    def finish(self, *, interrupted=False):
        failed = any(result["outcome"] == "FAIL" for result in self.record["fixtures"])
        self.record["run_status"] = "interrupted" if interrupted else "failed" if failed else "passed"
        publish_record(self.path, self.record)
        return 130 if interrupted else int(failed)


def standalone_composite_check(work, load, composite):
    """Require fresh entrypoint output and independently execute the saved asset."""
    with tempfile.TemporaryDirectory(prefix="standalone-composite-", dir=work) as directory:
        previous = Path.cwd()
        try:
            os.chdir(directory)
            load("composite-quantization", module_name="__main__")
        finally:
            os.chdir(previous)
        path = Path(directory) / "composite-demo" / "composite-quantized.aimodel"
        if not path.is_dir() or not any(path.iterdir()):
            raise AssertionError("standalone composite entrypoint did not create an asset")
        details = composite["compare_composite_asset"](path)
        return {"entrypoint": "__main__", "asset_created": True, **details}


def fixture_result(name, fn, expected_error=None):
    """Only the specified exception and diagnostic establish a negative control."""
    try:
        value = fn()
    except SystemExit:
        return {"name": name, "outcome": "FAIL", "details": traceback.format_exc()}
    except Exception as error:
        if (expected_error is not None and isinstance(error, expected_error[0])
                and expected_error[1] in str(error)):
            return {"name": name, "outcome": "PASS (rejected)", "details": str(error)[:600]}
        return {"name": name, "outcome": "FAIL", "details": traceback.format_exc()}
    if expected_error is not None:
        return {"name": name, "outcome": "FAIL", "details": "negative fixture unexpectedly passed"}
    try:
        details = json_details(value)
    except (TypeError, ValueError, RecursionError) as error:
        return {"name": name, "outcome": "FAIL", "details": f"fixture detail serialization failed: {error}"}
    return {"name": name, "outcome": "PASS", "details": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--reviewed-revision", required=True)
    parser.add_argument("--preflight-only", action="store_true", help="validate trust and examples without native execution")
    parser.add_argument("--compression", action="store_true")
    args = parser.parse_args()
    runner_root = Path(__file__).resolve().parents[1]
    try:
        runner_revision, runner_documents, source_documents = approved_snapshots(
            runner_root, args.source_repo, args.reviewed_revision,
            isolated=sys.flags.isolated, optimize=sys.flags.optimize)
        reader = load_trusted_reader(runner_documents)
        examples = snapshot_examples(reader, source_documents)
        required = {"state-protocol", "shipped-asset-gate", "ci-asset-gate"}
        if args.compression:
            required.update({"compression-native-fixtures", "composite-quantization"})
        missing = required - examples.keys()
        if missing:
            raise ValueError("missing required example IDs: " + ", ".join(sorted(missing)))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    provenance = {"runner_revision": runner_revision, "source_revision": args.reviewed_revision,
                  "runner_helpers": {p: hashlib.sha256(runner_documents[p]).hexdigest()
                     for p in ("scripts/verify_coreai_examples.py", "scripts/coreai_examples.py", "scripts/mdlinks.py")},
                  "isolated": True, "optimized": False}
    if args.preflight_only:
        print(json.dumps({**provenance, "example_ids": sorted(examples)}, indent=2))
        return 0
    record = {**provenance, "python": sys.version, "compression": args.compression,
              "packages": {}, "toolchain": {}, "fixtures": [], "examples": {}}
    work = args.out.parent.resolve()
    try:
        work.mkdir(parents=True, exist_ok=True)
        recorder = RunRecorder(args.out, record)
    except OSError as error:
        print(error, file=sys.stderr)
        return 1

    def load(name, module_name="guide_verification"):
        example = examples[name]
        ns = {"__name__": module_name}
        record["examples"][name] = {"path": str(example.path),
                                    "line": example.line,
                                    "sha256": hashlib.sha256(example.code.encode()).hexdigest()}
        exec(compile("\n" * (example.line - 1) + example.code, str(example.path), "exec"), ns)
        return ns

    def check(name, fn, expected_error=None):
        return recorder.check(name, fn, expected_error)

    interrupted = False
    publication_failed = False
    finish_status = 1
    try:
        record["os"] = platform.platform()
        record["os_build"] = subprocess.check_output(["sw_vers", "-buildVersion"], text=True).strip()
        packages = ["torch", "coreai-core", "coreai-torch", "numpy"]
        if args.compression:
            packages.extend(["torchao", "coreai-opt", "scikit-learn"])
        for name in packages:
            record["packages"][name] = importlib.metadata.version(name)
        record["toolchain"]["developer_dir"] = os.environ.get("DEVELOPER_DIR") or subprocess.check_output(
            ["xcode-select", "-p"], text=True).strip()
        record["toolchain"]["xcode"] = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
        record["toolchain"]["macos_sdk"] = subprocess.check_output(
            ["xcrun", "--sdk", "macosx", "--show-sdk-build-version"], text=True).strip()
        import numpy as np
        import torch
        from coreai_torch import TorchConverter, get_decomp_table

        check("NumPy scalar/array fixture details", lambda: {
            "integer": np.int64(7), "float": np.float32(0.25), "boolean": np.bool_(True),
            "array": np.array([[1, 2], [3, 4]]), "tuple": (Path("asset.aimodel"), np.int32(3))})
        state = load("state-protocol")
        # Migration-only verification does not require compression-package metadata.
        state_path = work / "state-release.aimodel"
        reference, ep = state["convert_state_model"](state_path)
        run = lambda **kw: asyncio.run(state["verify_state_asset"](state_path, reference, **kw))
        def state_checks():
            first, second = run(), run()
            for a, b in zip(first, second):
                np.testing.assert_array_equal(a, b)
            assert all(np.isfinite(x).all() for x in first)  # context already exited
            return {"lengths": [2, 8, 32], "shapes": [list(x.shape) for x in first]}
        check("state consecutive/reset/copied outputs", state_checks)
        check("state asymmetric initial buffers", lambda: [list(x.shape) for x in run(initial=(0.25, -0.5))])
        for length in (1, 33):
            check(f"application range rejects {length}", lambda length=length: run(lengths=(length,)),
                  expected_error=(ValueError, "sequence outside declared range 2–32"))

        gate = load("shipped-asset-gate")
        ci = load("ci-asset-gate")
        torch.manual_seed(17)
        model = torch.nn.Sequential(torch.nn.Linear(64, 64), torch.nn.ReLU()).eval()
        sample = (torch.randn(1, 64),)
        exported = torch.export.export(model, sample).run_decompositions(get_decomp_table())
        program = (TorchConverter(mode=TorchConverter.Mode.RELEASE)
                   .add_exported_program(exported, input_names=["x"], output_names=["y"]).to_coreai())
        path = work / "shipping-release.aimodel"
        program.save_asset(path)
        before = {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}
        def invoke(m=model, e=exported, atol=1e-2, rtol=1e-3):
            return asyncio.run(gate["shipped_asset_gate"](path, m, e, sample,
                input_names=["x"], output_names=["y"], runtime_atol=atol, runtime_rtol=rtol))
        def supplied_asset():
            result = invoke()["y"]
            assert np.isfinite(result).all()
            assert before == {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}
            return {"path": str(path), "shape": list(result.shape), "unchanged": True}
        check("gate loads supplied RELEASE asset/output ownership/non-mutation", supplied_asset)
        def replacement():
            destination = work / "overwrite.aimodel"
            program.save_asset(destination)
            sentinel = destination / "obsolete-sentinel.txt"
            sentinel.write_text("old asset")
            different = copy.deepcopy(model)
            with torch.no_grad():
                different[0].weight.zero_()
                different[0].bias.fill_(3)
            second_ep = torch.export.export(different, sample).run_decompositions(get_decomp_table())
            second_program = (TorchConverter(mode=TorchConverter.Mode.RELEASE)
                .add_exported_program(second_ep, input_names=["x"], output_names=["y"]).to_coreai())
            second_program.save_asset(destination)
            assert not sentinel.exists(), "save merged instead of replacing the destination"
            actual = asyncio.run(gate["shipped_asset_gate"](destination, different, second_ep, sample,
                input_names=["x"], output_names=["y"], runtime_atol=1e-2, runtime_rtol=1e-3))["y"]
            assert not np.allclose(actual, model(*sample).detach().numpy(), atol=1e-2, rtol=1e-3)
            return {"old_file_removed": True, "new_program_max_abs": float(np.max(np.abs(actual - 3)))}
        check("b3 replaces existing asset with different program", replacement)
        check("CI supplied asset", lambda: list(asyncio.run(ci["ci_asset_gate"](
            path, model, exported, sample, runtime_atol=1e-2, runtime_rtol=1e-3,
            required_composites=())).shape))
        check("CI rejects missing required composite", lambda: asyncio.run(ci["ci_asset_gate"](
            path, model, exported, sample, runtime_atol=1e-2, runtime_rtol=1e-3,
            required_composites=("rms_norm",))),
            expected_error=(AssertionError, "missing composite: rms_norm"))
        wrong = copy.deepcopy(model)
        with torch.no_grad():
            wrong[0].weight.add_(1)
        check("wrong weights fail export parity", lambda: invoke(wrong),
              expected_error=(AssertionError, "export y"))
        wrong_ep = torch.export.export(wrong, sample).run_decompositions(get_decomp_table())
        check("excessive runtime error", lambda: invoke(wrong, wrong_ep),
              expected_error=(AssertionError, "Core AI y"))
        shape_model = torch.nn.Linear(64, 32).eval()
        shape_ep = torch.export.export(shape_model, sample).run_decompositions(get_decomp_table())
        check("runtime shape mismatch", lambda: invoke(shape_model, shape_ep),
              expected_error=(AssertionError, "Core AI y"))
        for value in (float("nan"), float("inf")):
            check(f"non-finite output {value}", lambda value=value: gate["assert_parity"](
                np.zeros(2), np.full(2, value), atol=1, rtol=1, label="negative output"),
                expected_error=(AssertionError, "negative output: non-finite result"))
        if args.compression:
            compression = load("compression-native-fixtures")
            for name, fixture in compression["compression_fixtures"](work).items():
                check(name, fixture)
            original_cast = compression["cast_fp32_to_fp16"]
            def substituted_cast(transform):
                compression["cast_fp32_to_fp16"] = transform
                try:
                    return compression["compression_fixtures"](work)["casting exclusions"]()
                finally:
                    compression["cast_fp32_to_fp16"] = original_cast
            check("casting no-op rejected", lambda: substituted_cast(lambda ep, **kw: ep),
                  expected_error=(AssertionError, "standard cast did not lower exp"))
            check("casting ignored exclusions rejected", lambda: substituted_cast(
                lambda ep, **kw: original_cast(ep)), expected_error=(AssertionError, "ignored exp was cast"))
            def skip_overflow_cast(ep, **kwargs):
                if any(n.target == torch.ops.aten.log1p.default for n in ep.graph.nodes):
                    return ep
                return original_cast(ep, **kwargs)
            check("casting overflow graph no-op rejected", lambda: substituted_cast(skip_overflow_cast),
                  expected_error=(AssertionError, "overflow graph computation was not lowered"))
            def corrupt_overflow_cast(ep, defect, **kwargs):
                overflow = any(n.target == torch.ops.aten.log1p.default for n in ep.graph.nodes)
                if overflow and kwargs.get("ignored_ops") and defect == "exclusions":
                    return original_cast(ep)
                result = original_cast(ep, **kwargs)
                if not overflow or not kwargs.get("ignored_ops"):
                    return result
                exp = next(n for n in ep.graph.nodes if n.target == torch.ops.aten.exp.default)
                log = next(n for n in ep.graph.nodes if n.target == torch.ops.aten.log1p.default)
                if defect == "entry":
                    exp.args[0].kwargs = {**exp.args[0].kwargs, "dtype": torch.float16}
                elif defect == "exit":
                    exit_cast = next(iter(log.users))
                    exit_cast.kwargs = {**exit_cast.kwargs, "dtype": torch.float32}
                elif defect == "extra-user":
                    with ep.graph.inserting_after(log):
                        ep.graph.call_function(torch.ops.aten._to_copy.default,
                                               args=(log,), kwargs={"dtype": torch.float16})
                return result
            for defect, diagnostic in (
                ("exclusions", "overflow graph exclusion was ignored"),
                ("entry", "overflow entry cast incorrect"),
                ("exit", "overflow exit cast incorrect"),
                ("extra-user", "overflow log1p must have exactly one user"),
            ):
                check(f"casting overflow {defect} rejected", lambda defect=defect: substituted_cast(
                    lambda ep, **kwargs: corrupt_overflow_cast(ep, defect, **kwargs)),
                    expected_error=(AssertionError, diagnostic))
            composite = load("composite-quantization")
            check("graph composite quantization", lambda: composite["composite_fixture"](work))
            check("inert standalone composite rejected", lambda: standalone_composite_check(
                work, lambda *args, **kwargs: {}, composite),
                expected_error=(AssertionError, "standalone composite entrypoint did not create an asset"))
            check("standalone composite invocation", lambda: standalone_composite_check(work, load, composite))
    except RecordWriteError as error:
        publication_failed = True
        print(error, file=sys.stderr)
    except KeyboardInterrupt:
        interrupted = True
    except (Exception, SystemExit):
        record["fixtures"].append({"name": "setup", "outcome": "FAIL", "details": traceback.format_exc()})
    except BaseException:
        interrupted = True
        raise
    finally:
        if not publication_failed:
            try:
                finish_status = recorder.finish(interrupted=interrupted)
            except RecordWriteError as error:
                print(error, file=sys.stderr)
    return finish_status


if __name__ == "__main__":
    raise SystemExit(main())
