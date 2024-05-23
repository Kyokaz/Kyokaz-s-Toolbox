# File: __init__.py
bl_info = {
    "name": "Kyokaz's Toolbox",
    "author": "Kyokaz, ChatGPT",
    "version": (2, 4, 5),
    "blender": (3, 0, 0),
    "location": "",
    "description": "Animation Toolbox",
    "category": "Animation"
}

import bpy
from .operators import (
    OBJECT_OT_toggle_default_interpolation,
    OBJECT_OT_bake_keyframes_per_steps,
    OBJECT_OT_add_keyframes_operator,
    OBJECT_OT_delete_keyframes_per_steps,
    OBJECT_OT_toggle_interpolation_selected,
    OBJECT_OT_toggle_interpolation_all,
    OBJECT_OT_apply_all_constant,
    OBJECT_OT_apply_all_bezier,
    OBJECT_OT_apply_all_linear,
    OBJECT_OT_apply_selected_constant,
    OBJECT_OT_apply_selected_bezier,
    OBJECT_OT_apply_selected_linear,
    OBJECT_OT_toggle_auto_keying,
    OBJECT_OT_ViewportRenderConfirm,
    SCENE_OT_JumpToMarker,
    SCENE_OT_RemoveMarkerAndCamera,
    SCENE_OT_RemoveAllShotCameras,
    SCENE_OT_SelectCamera,
    SCENE_OT_SetPreviewRange,
    OBJECT_OT_OpenOutputDirectory,
    SelectHiddenDisableRenderOperator,
    CreateExcludeHiddenCollectionOperator,
    CustomNameProperties,
    AddCameraButton,
    AddCameraWithMarkerButton,
    AddCameraCopyPropertiesButton,
    AddCameraShotCopyPropertiesButton,
    ShowPopupMessageOperator,
    WM_OT_capture_keymap,
    WM_OT_remove_keymap,
    VIEW3D_MT_PIE_QuickCamera
)
from .panels import (
    OBJECT_PT_toggle_interpolation_panel,
    OBJECT_PT_SelectHiddenDisableRenderPanel,
    OBJECT_PT_CameraTools_Status,
    OBJECT_PT_CameraTools
)

def draw_viewport_header(self, context):
    preferences = context.preferences.addons[__name__].preferences
    if preferences.show_viewport_button:
        self.layout.operator("object.viewport_render_confirm", text="Viewport Render", icon='RENDER_STILL')

class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    key: bpy.props.StringProperty(
        name="Key",
        default='V',
        update=lambda self, context: update_keymap(self, context)
    )
    ctrl: bpy.props.BoolProperty(
        name="Ctrl",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    alt: bpy.props.BoolProperty(
        name="Alt",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    shift: bpy.props.BoolProperty(
        name="Shift",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    capture_key: bpy.props.BoolProperty(
        name="Capture Key",
        default=False
    )
    
    show_viewport_button: bpy.props.BoolProperty(
        name="Show the Viewport Render button in the 3D Viewport header",
        description="Show the Viewport Render button in the 3D Viewport header",
        default=True
    )

    def draw(self, context):
        layout = self.layout
        addon_prefs = context.preferences.addons[__name__].preferences
        
        box = layout.box()
        row = box.row()
        row.label(text="Quick Camera")
        row = box.row()
        row.prop(self, "show_viewport_button")
        row = box.row()  
        row.label(text="Pie Menu Keybind:")
        
        if addon_prefs.capture_key:
            row.operator("wm.capture_keymap", text="Press a Key", icon="KEYINGSET")
        else:
            if addon_prefs.key == '':
                key_combination = "(None)"
            else:
                key_combination = (addon_prefs.ctrl and "Ctrl+" or "") + \
                                  (addon_prefs.alt and "Alt+" or "") + \
                                  (addon_prefs.shift and "Shift+" or "") + \
                                  addon_prefs.key
            row.operator("wm.capture_keymap", text=key_combination, icon="KEYINGSET")
        
        row.operator("wm.remove_keymap", text="", icon="X")
        
        row = box.row()
        row.prop(self, "ctrl")
        row.prop(self, "alt")
        row.prop(self, "shift")
        
        box = layout.box()
        row = box.row()
        row.label(text="This code was written with the help of ChatGPT, if you know how to improve it please let me know!")
        row = box.row()
        row.operator("wm.url_open", text="Visit GitHub", icon="URL").url = "https://github.com/Kyokaz/Kyokaz-s-Toolbox"

def draw_viewport_header(self, context):
    preferences = context.preferences.addons[__name__].preferences
    if preferences.show_viewport_button:
        self.layout.operator("object.viewport_render_confirm", text="Viewport Render", icon='RENDER_STILL')

global_addon_keymaps = []

def register_keymap():
    addon_prefs = get_addon_preferences()
    if addon_prefs is None:
        print("Addon preferences not found.")
        return

    key = addon_prefs.key
    if key == '':
        return

    ctrl = addon_prefs.ctrl
    alt = addon_prefs.alt
    shift = addon_prefs.shift

    window_manager = bpy.context.window_manager
    if window_manager.keyconfigs.addon:
        keymap = window_manager.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        keymap_item = keymap.keymap_items.new('wm.call_menu_pie', key, "PRESS", ctrl=ctrl, alt=alt, shift=shift)
        keymap_item.properties.name = "VIEW3D_MT_PIE_QuickCamera"
        global_addon_keymaps.append((keymap, keymap_item))

def update_keymap(self, context):
    unregister_keymap()
    register_keymap()

def unregister_keymap():
    window_manager = bpy.context.window_manager
    if window_manager and window_manager.keyconfigs and window_manager.keyconfigs.addon:
        for keymap, keymap_item in global_addon_keymaps:
            keymap.keymap_items.remove(keymap_item)
    global_addon_keymaps.clear()

def get_addon_preferences():
    return bpy.context.preferences.addons[__package__].preferences

classes = (
    OBJECT_OT_toggle_default_interpolation,
    OBJECT_OT_bake_keyframes_per_steps,
    OBJECT_OT_add_keyframes_operator,
    OBJECT_OT_delete_keyframes_per_steps,
    OBJECT_OT_toggle_interpolation_selected,
    OBJECT_OT_toggle_interpolation_all,
    OBJECT_OT_apply_all_constant,
    OBJECT_OT_apply_all_bezier,
    OBJECT_OT_apply_all_linear,
    OBJECT_OT_apply_selected_constant,
    OBJECT_OT_apply_selected_bezier,
    OBJECT_OT_apply_selected_linear,
    OBJECT_OT_toggle_auto_keying,
    OBJECT_PT_toggle_interpolation_panel,
    OBJECT_PT_SelectHiddenDisableRenderPanel,
    OBJECT_PT_CameraTools,
    OBJECT_PT_CameraTools_Status,
    OBJECT_OT_ViewportRenderConfirm,
    SCENE_OT_JumpToMarker,
    SCENE_OT_RemoveMarkerAndCamera,
    SCENE_OT_RemoveAllShotCameras,
    SCENE_OT_SelectCamera,
    SCENE_OT_SetPreviewRange,
    OBJECT_OT_OpenOutputDirectory,
    VIEW3D_MT_PIE_QuickCamera,
    SelectHiddenDisableRenderOperator,
    CreateExcludeHiddenCollectionOperator,
    CustomNameProperties,
    AddCameraButton,
    AddCameraWithMarkerButton,
    AddCameraCopyPropertiesButton,
    AddCameraShotCopyPropertiesButton,
    ShowPopupMessageOperator,
    WM_OT_capture_keymap,
    WM_OT_remove_keymap,
    MyAddonPreferences
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.custom_name_props = bpy.props.PointerProperty(type=CustomNameProperties)
    bpy.types.VIEW3D_HT_header.append(draw_viewport_header)
    register_keymap()

def unregister():
    unregister_keymap()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_HT_header.remove(draw_viewport_header)
    del bpy.types.Scene.custom_name_props

if __name__ == "__main__":
    register()
