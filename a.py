"""
Collect PyTorch functions/methods and their arguments.

Outputs (in the current directory):
  pytorch_aten_schemas.json / .csv   - every native ATen op, typed args + defaults
  pytorch_python_api.json  / .csv    - Python-level API (torch, Tensor, fft, nn, ...)

Run:  python collect_pytorch_api.py
"""
import csv
import importlib
import inspect
import json

import torch

# ---------------------------------------------------------------------------
# 1. ATen operator schemas (most complete: abs, fft_fft, etc.)
# ---------------------------------------------------------------------------
def schema_args(schema):
    out = []
    for a in schema.arguments:
        try:
            default = repr(a.default_value) if a.has_default_value() else None
        except Exception:
            default = None
        out.append({
            "name": a.name,
            "type": str(a.type),
            "default": default,
            "kwarg_only": bool(getattr(a, "kwarg_only", False)),
        })
    return out


def collect_aten():
    rows = []
    for s in torch._C._jit_get_all_schemas():
        rows.append({
            "op": s.name,                      # e.g. "aten::fft_fft"
            "overload": s.overload_name,       # e.g. "out", "Tensor", ""
            "signature": str(s),               # full schema string
            "args": schema_args(s),
            "returns": [str(r.type) for r in s.returns],
        })
    rows.sort(key=lambda r: (r["op"], r["overload"]))
    return rows


# ---------------------------------------------------------------------------
# 2. Python-level API walk
# ---------------------------------------------------------------------------
NAMESPACES = [
    "torch", "torch.Tensor", "torch.fft", "torch.linalg", "torch.special",
    "torch.nn", "torch.nn.functional", "torch.nn.init", "torch.nn.utils",
    "torch.autograd", "torch.autograd.functional", "torch.optim",
    "torch.optim.lr_scheduler", "torch.utils.data", "torch.distributions",
    "torch.sparse", "torch.signal", "torch.random", "torch.cuda",
    "torch.func", "torch.jit", "torch.onnx", "torch.profiler",
    "torch.distributed", "torch.amp", "torch.backends",
]


def get_signature(obj):
    """Return (signature_string, source) where source says how we got it."""
    try:
        return str(inspect.signature(obj)), "inspect"
    except (ValueError, TypeError):
        pass
    # Builtins (e.g. torch.abs, Tensor.abs): first docstring line is usually
    # the signature, e.g. "abs(input, *, out=None) -> Tensor"
    doc = inspect.getdoc(obj) or ""
    first = doc.strip().splitlines()[0] if doc.strip() else ""
    return first, "docstring"


def params_from_object(obj):
    try:
        return [
            {
                "name": p.name,
                "default": None if p.default is p.empty else repr(p.default),
                "kind": p.kind.name,
            }
            for p in inspect.signature(obj).parameters.values()
        ]
    except (ValueError, TypeError):
        return []


def walk_namespace(modname):
    try:
        if modname == "torch.Tensor":
            mod = torch.Tensor
        else:
            mod = importlib.import_module(modname)
    except Exception as e:
        print(f"skip {modname}: {e}")
        return []

    rows = []
    for name in sorted(dir(mod)):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(mod, name)
        except Exception:
            continue
        if not callable(obj):
            continue

        if inspect.isclass(obj):
            kind = "class"
            target = obj.__init__
        else:
            kind = "function"
            target = obj

        sig, source = get_signature(target if kind == "class" else obj)
        if kind == "class" and source == "inspect":
            # drop the leading "self" for readability
            sig = sig.replace("(self, ", "(").replace("(self)", "()")

        rows.append({
            "namespace": modname,
            "name": name,
            "kind": kind,
            "signature": sig,
            "signature_source": source,
            "params": params_from_object(target),
        })
    return rows


def collect_python_api():
    rows = []
    for ns in NAMESPACES:
        rows.extend(walk_namespace(ns))
    return rows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    print(f"PyTorch {torch.__version__}")

    #aten = collect_aten()
    #write_json("pytorch_aten_schemas.json", aten)
    #write_csv("pytorch_aten_schemas.csv", aten, ["op", "overload", "signature"])
    #print(f"ATen schemas: {len(aten)}")

    api = collect_python_api()
    write_json("pytorch_python_api.json", api)
    write_csv(
        "pytorch_python_api.csv", api,
        ["namespace", "name", "kind", "signature", "signature_source"],
    )
    print(f"Python API entries: {len(api)}")

