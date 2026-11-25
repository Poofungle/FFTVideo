import json
import math
import random

import dearpygui.dearpygui as dpg
import torch
import importlib
from operator import attrgetter
from pathlib import Path

SAVE_DIR = Path("saves")
SAVE_DIR.mkdir(exist_ok=True)

EDITOR = "NodeEditor"
def get_object_from_path(dotted_path: str):
  parts = dotted_path.split(".")
  obj = importlib.import_module(parts[0])
  if len(parts) > 1:
    obj = attrgetter(".".join(parts[1:]))(obj)
  return obj

def getDoc(path):
    func = get_object_from_path(path)
    return getattr(func, "__doc__", None)

with open('atens.json', 'r') as file:
    funcs = json.load(file)



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



SIMPLE_NODES = {
    "Number":      [(dpg.mvNode_Attr_Output, lambda: dpg.add_input_double(width=80))],
    "Integer":     [(dpg.mvNode_Attr_Output, lambda: dpg.add_input_int(width=80))],
    "Video Start": [(dpg.mvNode_Attr_Output, lambda: dpg.add_text("Video"))],
    "Video End":   [(dpg.mvNode_Attr_Input,  lambda: dpg.add_text("Video"))]
}

def create_node(kind, pos):
    with dpg.node(label=kind, parent="NodeEditor", pos=pos) as node:
        if kind in SIMPLE_NODES:
            widgets = SIMPLE_NODES[kind]
            for attType, widget in widgets:
                with dpg.node_attribute(attribute_type=attType):
                    widget()
        else:
            funcn = kind
            for i, arg in enumerate(funcs[funcn]["args"]):
                if arg["required"]:
                    with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input, shape=dpg.mvNode_PinShape_CircleFilled):
                        dpg.add_text(arg["name"])
                else:
                    with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Input, shape=dpg.mvNode_PinShape_Circle):
                        dpg.add_text(arg["name"])
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(f"-> {funcs[funcn]["returns"][0]}")
    return node


def save_selected(sender, app_data, user_data):
    name = dpg.get_value("SaveName")
    nodes = dpg.get_selected_nodes(EDITOR)
    links = dpg.get_selected_links(EDITOR)
    if not name or not nodes:
        return
    attlookup = {} #att ID -> (att index, node index)
    saved_nodes=[]
    for nodeindex, node in enumerate(nodes):
        atts = dpg.get_item_children(node, 1)
        for attindex, att in enumerate(atts):
            attlookup[att] = (nodeindex, attindex)
        saved_node={"kind":dpg.get_item_label(node),"pos":dpg.get_item_pos(node)}
        saved_nodes.append(saved_node)
    saved_links = []
    for linkindex, link in enumerate(links):
        cfg = dpg.get_item_configuration(link)
        a1, a2 = cfg["attr_1"], cfg["attr_2"]
        if a1 in attlookup and a2 in attlookup:  #Don't include broken nodes
            saved_links.append([attlookup[a1], attlookup[a2]]) #(Node index, attributes index) -> other end
    with open(SAVE_DIR / f"{name}.json", "w") as f:
        json.dump({"nodes":saved_nodes,"links":saved_links}, f)
    refresh_saved()

def load_saved(file, pos):
    with open(SAVE_DIR / f"{file}.json") as f:
        data = json.load(f)
    min_x = min(n["pos"][0] for n in data["nodes"])
    min_y = min(n["pos"][1] for n in data["nodes"])
    nodes = []
    for nodeEntry in data["nodes"]:
        nodePos = (nodeEntry["pos"][0]-min_x+pos[0], nodeEntry["pos"][1]-min_y+pos[1])
        node=create_node(nodeEntry["kind"], nodePos)
        nodes.append(node)
    for linkEntry in data["links"]:
        attA = dpg.get_item_children(nodes[linkEntry[0][0]], 1)[linkEntry[0][1]]
        attB = dpg.get_item_children(nodes[linkEntry[1][0]], 1)[linkEntry[1][1]]
        dpg.add_node_link(attA,attB,parent=EDITOR)


def drop_cb(sender, app_data, user_data):
    mx, my = dpg.get_mouse_pos(local=False)
    ex, ey = dpg.get_item_rect_min("NodeEditor")  # fallback: unpanned origin
    for node in dpg.get_item_children("NodeEditor", 1) or []:
        sx, sy = dpg.get_item_rect_min(node)  # node's screen position
        gx, gy = dpg.get_item_pos(node)  # node's grid position
        if sx or sy:  # skip nodes not yet rendered
            ex, ey = sx - gx, sy - gy  # screen position of the grid origin
            break
    pos = [mx - ex, my - ey]
    if app_data.startswith("(LoadSave)"):
        load_saved(app_data.split("(LoadSave)")[1], pos)
    else:
        create_node(app_data,pos)
def delSav(sender, app_data, user_data):
    Path(user_data).unlink()
    refresh_saved()
def refresh_saved():
    dpg.delete_item("SavedList", children_only=True)
    for f in sorted(SAVE_DIR.glob("*.json")):
        with dpg.group(parent="SavedList",horizontal=True):
            t = dpg.add_text(f.stem, color=(127, 255, 127))
            dpg.add_button(label="D",callback=delSav,user_data=f)
            with dpg.drag_payload(parent=t, drag_data="(LoadSave)" + f.stem, payload_type="item"):
                dpg.add_text(f.stem, color=(127, 255, 127))

def callback(sender, app_data, user_data):
    dpg.set_value(user_data, app_data)

def opentextbox(sender, app_data, user_data):
    with dpg.window(
            label="Doc String",
            width=500,
            height=400,
            on_close=lambda s: dpg.delete_item(s),  # Frees memory when closed
    ):

        dpg.add_text(getDoc(user_data.split(".")[0].replace("fft_","fft.").replace("linalg_","linalg.").replace("special_","special.").replace("aten::","torch.")), wrap=480)

with dpg.window(label="Main", tag="main"):
    with dpg.table(header_row=False,resizable=True,policy=dpg.mvTable_SizingStretchProp):
        dpg.add_table_column(init_width_or_weight=1.5)
        dpg.add_table_column(init_width_or_weight=3)
        dpg.add_table_column(init_width_or_weight=1)
        with dpg.table_row():
            with dpg.group():
                dpg.add_text("Nodes")
                dpg.add_input_text(label="Filter (inc, -exc)", callback=callback,user_data="NodeSearch")
                with dpg.child_window(height=400, resizable_y=True, border=True):
                    with dpg.filter_set(tag="NodeSearch"):
                        for func in funcs:

                            r=funcs[func]["returns"][0]
                            s=func+"("
                            ma = len(funcs[func]["args"])-1
                            for i, arg in enumerate(funcs[func]["args"]):
                                s+=arg["name"]
                                s+=": "
                                s+=arg["type"]
                                if not arg["required"] :
                                    s+=" = " + str(arg["default"])
                                if i!=ma:
                                    s+=", "

                            s+=") -> " +r
                            color = (255,255,255)
                            if r=="Tensor":
                                color =  (255,127,255)
                            if r=="bool":
                                color =  (127,127,255)
                            with dpg.group(filter_key=f"{func} {s} {r}",horizontal=True):
                                a=dpg.add_text(f"{func}",color=color)
                                b=dpg.add_button(label="V",callback=opentextbox,user_data=func)
                                with dpg.tooltip(b):
                                    dpg.add_text("Attempt to view documentation")
                                with dpg.tooltip(a):
                                    dpg.add_text(s)
                                with dpg.drag_payload(parent=a, drag_data=func, payload_type="item"):
                                    dpg.add_text(func,color=color)
                dpg.add_text("Variables")
                dpg.add_input_text(label="Filter (inc, -exc)", callback=callback,user_data="VarSearch")
                with dpg.child_window(height=-1,border=True):
                    with dpg.filter_set(tag="VarSearch"):
                        for stri in ["Number", "Integer", "Video Start", "Video End"]:
                            with dpg.group(filter_key=stri):
                                a=dpg.add_text(stri)
                                with dpg.drag_payload(parent=a, drag_data=stri, payload_type="item"):
                                    a=dpg.add_text(stri,color=(127,127,255))


            with dpg.child_window(tag="NodeEditorOuter",drop_callback=drop_cb,payload_type="item"):
                with dpg.node_editor(tag="NodeEditor",minimap=True,
                    callback=link_cb,
                    delink_callback=delink_cb):
                    pass
            with dpg.child_window():
                with dpg.group():
                    dpg.add_text("Other")
                    with dpg.child_window(height=200, resizable_y=True, border=True):
                        dpg.add_text("Save/load")
                        dpg.add_input_text(label="Name", tag="SaveName")
                        dpg.add_button(label="Save", callback=save_selected)
                        dpg.add_separator()
                        with dpg.group(tag="SavedList"):
                            pass
                        with dpg.child_window(border=True):
                            dpg.add_button(label="Run")





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
def on_load():
    refresh_saved()

dpg.set_frame_callback(3, callback=on_load)
dpg.start_dearpygui()
dpg.destroy_context()

