import json

import torch

with open('pytorch_python_api.json', 'r') as file:
    funcs = json.load(file)


classes = []
methods = []
methodsNoParam = []
other = []
for func in funcs:
    if func["kind"] == "function":
        if len(func["params"]) ==0:
            methodsNoParam.append(func)
        else:
            methods.append(func)
    elif func["kind"] == "class":
        classes.append(func)
    else:
        other.append(func)
print(methodsNoParam)

