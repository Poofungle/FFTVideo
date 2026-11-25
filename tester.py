import json
import torch
x = torch.tensor([[(int)(1), (int)(2), (int)(3)], [(int)(4), (int)(-5), (int)(6)], [(int)(7), (int)(8), (int)(9)]])
x=torch.ops.aten.abs(self=x)           # schema "aten::abs"
x=torch.ops.aten.fft_fft(n=8,self=x)  # schema "aten::fft_fft"

print(x)
import torch

schemas = torch._C._jit_get_all_schemas()

parsed_ops = {}
for s in schemas:
    if not s.name.startswith("aten::"):
        continue
    op_key = f"{s.name}.{s.overload_name}" if s.overload_name else s.name
    if len(s.returns)==1 and not(s.name.split("::")[1][0]=="_" and not s.name.split("::")[1][1]=="_"):
        parsed_ops[op_key] = {
          "args": [
              {
                  "name": arg.name,
                  "type": str(arg.type),
                  "required": not arg.has_default_value(),
                  "default": arg.default_value,
                  "kwarg_only": arg.kwarg_only,
                  "is_write":arg.is_write
              }
              for arg in s.arguments
          ],
          "returns": [str(ret.type) for ret in s.returns],
        }

with open("atens.json", "w") as f:
    json.dump(parsed_ops, f, indent=2)
print(len(parsed_ops))
