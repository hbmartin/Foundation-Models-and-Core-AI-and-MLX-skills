#!/usr/bin/env python3
"""Execute named guide fences on a native Core AI host; write an honest JSON record.

Run with an isolated, explicitly pinned Python environment. This is not part of
portable unittest discovery and never installs dependencies itself.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.coreai_examples import guide_examples, removed_optimizer_errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compression", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assert not removed_optimizer_errors(root)
    examples = {e.id: e for e in guide_examples(root) if e.id}
    record = {"python": sys.version, "os": platform.platform(),
              "os_build": subprocess.check_output(["sw_vers", "-buildVersion"], text=True).strip(),
              "packages": {n: importlib.metadata.version(n) for n in
                           ("torch", "torchao", "coreai-core", "coreai-torch", "coreai-opt", "numpy")},
              "fixtures": [], "examples": {}}
    work = args.out.parent
    work.mkdir(parents=True, exist_ok=True)

    def load(name):
        example = examples[name]
        ns = {"__name__": "guide_verification"}
        exec(compile(example.code, str(example.path), "exec"), ns)
        import hashlib
        record["examples"][name] = {"path": str(example.path.relative_to(root)),
                                    "line": example.line,
                                    "sha256": hashlib.sha256(example.code.encode()).hexdigest()}
        return ns

    def check(name, fn, rejects=False):
        try:
            value = fn()
            if rejects:
                raise RuntimeError("negative fixture unexpectedly passed")
            record["fixtures"].append({"name": name, "outcome": "PASS", "details": value})
        except (AssertionError, ValueError, RuntimeError) as error:
            if rejects and str(error) != "negative fixture unexpectedly passed":
                record["fixtures"].append({"name": name, "outcome": "PASS (rejected)", "details": str(error)[:600]})
            else:
                record["fixtures"].append({"name": name, "outcome": "FAIL", "details": traceback.format_exc()})
        except Exception:
            record["fixtures"].append({"name": name, "outcome": "FAIL", "details": traceback.format_exc()})
        print(record["fixtures"][-1]["name"], record["fixtures"][-1]["outcome"], flush=True)

    try:
        import numpy as np
        import torch
        from coreai_torch import TorchConverter, get_decomp_table

        state = load("state-protocol")
        # Permit migration-only verification before all compression repairs land.
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
            check(f"export range rejects {length}", lambda length=length: run(lengths=(length,)), rejects=True)

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
        # Deliberately save again to establish b3 replaces an existing directory.
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
        check("gate loads supplied RELEASE asset/output ownership/b3 overwrite", supplied_asset)
        check("CI supplied asset", lambda: list(asyncio.run(ci["ci_asset_gate"](
            path, model, exported, sample, runtime_atol=1e-2, runtime_rtol=1e-3)).shape))
        wrong = copy.deepcopy(model)
        with torch.no_grad():
            wrong[0].weight.add_(1)
        check("wrong weights fail export parity", lambda: invoke(wrong), rejects=True)
        wrong_ep = torch.export.export(wrong, sample).run_decompositions(get_decomp_table())
        check("excessive runtime error", lambda: invoke(wrong, wrong_ep), rejects=True)
        shape_model = torch.nn.Linear(64, 32).eval()
        shape_ep = torch.export.export(shape_model, sample).run_decompositions(get_decomp_table())
        check("runtime shape mismatch", lambda: invoke(shape_model, shape_ep), rejects=True)
        for value in (float("nan"), float("inf")):
            check(f"non-finite output {value}", lambda value=value: gate["assert_parity"](
                np.zeros(2), np.full(2, value), atol=1, rtol=1, label="negative output"), rejects=True)
        if args.compression:
            compression = load("compression-native-fixtures")
            for name, fixture in compression["compression_fixtures"](work).items():
                check(name, fixture)
    except Exception:
        record["fixtures"].append({"name": "setup", "outcome": "FAIL", "details": traceback.format_exc()})
    finally:
        args.out.write_text(json.dumps(record, indent=2) + "\n")
    return int(any(x["outcome"] == "FAIL" for x in record["fixtures"]))


if __name__ == "__main__":
    raise SystemExit(main())
