import dearpygui.dearpygui as dpg

def save_callback():
    print("Save Clicked")
def drag_callback(sender, app_data, user_data):
    print(sender, app_data, user_data)
def button_callbackadd(sender, app_data, user_data):
    dpg.add_text(dpg.get_value(user_data),parent=dpg.get_item_info(sender)["parent"],drag_callback=drag_callback,payload_type="text_item")
def button_callbackrem(sender, app_data, user_data):
    p = dpg.get_item_info(dpg.get_item_info(sender)["parent"])["children"][1]
    if len(p)>4:
        dpg.delete_item(dpg.get_item_info(dpg.get_item_info(sender)["parent"])["children"][1][-1])


dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()

with dpg.window(label="Main", tag="main",width=400,height=400):
    with dpg.table(header_row=False,resizable=True,policy=dpg.mvTable_SizingStretchProp):
        dpg.add_table_column(init_width_or_weight=1)
        dpg.add_table_column(init_width_or_weight=1)
        with dpg.table_row():
            with dpg.child_window():
                dpg.add_input_text(label="Input", tag="input_text1")
                dpg.add_text("Left")
                dpg.add_button(label="Add", callback=button_callbackadd,user_data="input_text1")
                dpg.add_button(label="Remove", callback=button_callbackrem)
            with dpg.child_window():
                dpg.add_input_text(label="Input", tag="input_text2")
                dpg.add_text("Right")
                dpg.add_button(label="Add", callback=button_callbackadd,user_data="input_text2")
                dpg.add_button(label="Remove", callback=button_callbackrem)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()