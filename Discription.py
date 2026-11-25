import importlib
import json
from operator import attrgetter

import torch


def get_object_from_path(dotted_path: str):
  parts = dotted_path.split(".")
  obj = importlib.import_module(parts[0])
  if len(parts) > 1:
    obj = attrgetter(".".join(parts[1:]))(obj)
  return obj

func = get_object_from_path("torch.scatter")
doc = getattr(func, "__doc__", None)

with open('atens.json', 'r') as file:
  funcs = json.load(file)
for func in funcs:
  print(funcs[func]["returns"][0])