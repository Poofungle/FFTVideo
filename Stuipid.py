import json

with open('atens.json', 'r') as file:
    funcs = json.load(file)
print(len(funcs))
l=0
poo = []
for func in funcs:
    if (len(funcs[func]["args"])) > l:
        l = len(funcs[func]["args"])
        poo =[]
        poo.append(func)
    if (len(funcs[func]["args"])) == l:
        poo.append(func)
print(l,poo)