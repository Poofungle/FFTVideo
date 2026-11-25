import json
import math
import random

import dearpygui.dearpygui as dpg
import torch
import importlib
from operator import attrgetter


def get_object_from_path(dotted_path: str):
  parts = dotted_path.split(".")
  obj = importlib.import_module(parts[0])
  if len(parts) > 1:
    obj = attrgetter(".".join(parts[1:]))(obj)
  return obj

def getDoc(path):
    func = get_object_from_path(path)
    return getattr(func, "__doc__", None)

with open('pytorch_python_api.json', 'r') as file:
    funcs = json.load(file)
classes = []
methods = []
methodsNoParam = []
allmethodswithreturn = []
other = []
for func in funcs:
    if func["kind"] == "function":
        if len(func["signature"].split("->"))>1:
            if func["signature"].split("->")[1].strip()!="None":
                allmethodswithreturn.append([func["name"],func["signature"],func["signature"].split("->")[1].strip()])
        if len(func["params"]) ==0:
            methodsNoParam.append([func["name"],func["signature"]])
        else:
            methods.append(func["signature"])
    elif func["kind"] == "class":
        classes.append(func["signature"])
    else:
        other.append(func["signature"])



dpg.create_context()
dpg.create_viewport(title= "Test")
dpg.setup_dearpygui()

def link_cb(sender, app_data):
    input_pin = app_data[1]
    links = dpg.get_item_children(sender, slot=0) or []

    for link in links:
        cfg = dpg.get_item_configuration(link)
        if cfg["attr_1"] == input_pin or cfg["attr_2"] == input_pin:
            dpg.delete_item(link)

    dpg.add_node_link(app_data[0], app_data[1], parent=sender)



def delink_cb(sender, app_data):
    dpg.delete_item(app_data)
def drop_cb(sender, app_data, user_data):
    print(app_data)

    mx, my = dpg.get_mouse_pos(local=False)
    ex, ey = dpg.get_item_rect_min("NodeEditor")
    pos = [mx - ex, my - ey]
    if app_data == "Number":
        with dpg.node(label="Number", parent="NodeEditor", pos=pos):
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_double(label="Number",width=80)
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(f"->")
        return
    if app_data == "Integer":
        with dpg.node(label="Integer", parent="NodeEditor", pos=pos):
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_int(label="Integer",width=50)
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(f"->")
        return
    body, ret = app_data.split("->")
    name,params = body.split("(",1)
    params = params.split(")")[0].split(",")
    # place node where the mouse was dropped, relative to the editor

    with dpg.node(label=name, parent="NodeEditor", pos=pos):
        for p in params:
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input, shape=dpg.mvNode_PinShape_CircleFilled):
                dpg.add_text(p)
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
            dpg.add_button(
                label="Show Optional"
            )
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text(f"-> {ret}")

def callback(sender, app_data, user_data):
    dpg.set_value(user_data, app_data)

def opentextbox(sender, app_data, user_data):
    with dpg.window(
            label="Doc String",
            width=500,
            height=400,
            on_close=lambda s: dpg.delete_item(s),  # Frees memory when closed
    ):

        dpg.add_text(getDoc("torch."+user_data), wrap=480)

with dpg.window(label="Main", tag="main"):
    with dpg.table(header_row=False,resizable=True,policy=dpg.mvTable_SizingStretchProp):
        dpg.add_table_column(init_width_or_weight=1)
        dpg.add_table_column(init_width_or_weight=1)
        dpg.add_table_column(init_width_or_weight=1)
        with dpg.table_row():
            with dpg.group():
                dpg.add_text("Nodes")
                dpg.add_input_text(label="Filter (inc, -exc)", callback=callback,user_data="NodeSearch")
                with dpg.child_window(height=400, resizable_y=True, border=True):
                    with dpg.filter_set(tag="NodeSearch"):
                        for n, s, r in allmethodswithreturn:
                            color = (255,255,255)
                            if r=="Tensor":
                                color =  (255,127,255)
                            if r=="bool":
                                color =  (127,127,255)
                            with dpg.group(filter_key=f"{n} {s} {r}",horizontal=True):
                                a=dpg.add_text(f"{n}",color=color)
                                dpg.add_button(label="V",callback=opentextbox,user_data=n)
                                with dpg.tooltip(a):
                                    dpg.add_text(s)
                                with dpg.drag_payload(parent=a, drag_data=s, payload_type="item"):
                                    dpg.add_text(n,color=color)
                dpg.add_text("Variables")
                dpg.add_input_text(label="Filter (inc, -exc)", callback=callback,user_data="VarSearch")
                with dpg.child_window(height=-1,border=True):
                    with dpg.filter_set(tag="VarSearch"):
                        with dpg.group(filter_key=f"number"):
                            a=dpg.add_text(f"Number")
                            with dpg.drag_payload(parent=a, drag_data="Number", payload_type="item"):
                                a=dpg.add_text(f"Number",color=(127,127,255))
                        with dpg.group(filter_key=f"integer"):
                            a=dpg.add_text(f"Integer")
                            with dpg.drag_payload(parent=a, drag_data="Integer", payload_type="item"):
                                a=dpg.add_text(f"Integer",color=(127,127,255))



            with dpg.child_window(tag="NodeEditorOuter",drop_callback=drop_cb,payload_type="item"):
                with dpg.node_editor(tag="NodeEditor",minimap=True,
                    callback=link_cb,
                    delink_callback=delink_cb):
                    pass
            with dpg.child_window():
                dpg.add_input_text(label="Input")
                dpg.add_text("Right")

EDITOR = "NodeEditor"
def delete_selected(sender=None, app_data=None):
    for link in dpg.get_selected_links(EDITOR):
        dpg.delete_item(link)
    for node in dpg.get_selected_nodes(EDITOR):
        attrs = set(dpg.get_item_children(node, 1))
        for link in dpg.get_item_children(EDITOR, 0):  # slot 0 = links
            cfg = dpg.get_item_configuration(link)
            if cfg["attr_1"] in attrs or cfg["attr_2"] in attrs:
                dpg.delete_item(link)
        dpg.delete_item(node)

with dpg.handler_registry():
    dpg.add_key_press_handler(dpg.mvKey_Delete, callback=delete_selected)

dpg.show_viewport()
dpg.set_primary_window("main",True)
dpg.start_dearpygui()
dpg.destroy_context()