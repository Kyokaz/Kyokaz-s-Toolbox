# pyright: reportInvalidTypeForm=false

bl_info = {
    "name": "KyokazToolbox",
    "author": "Kyokaz",
    "version": (2, 6, 5),
    "blender": (3, 0, 0),
    "location": "",
    "description": "Animation Toolbox",
    "category": "Animation"
}

import bpy
import logging
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, PointerProperty
from . import operators
from . import panels
from .utils import get_addon_preferences
from . import utils

addon_keymaps = []


def _redraw_viewports(context):
    """Helper function to redraw all 3D viewports."""
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


class MyAddonPreferences(AddonPreferences):
    bl_idname = __package__

    # Quick Camera Pie Menu
    quick_camera_key: StringProperty(
        name="Quick Camera Key",
        default='V',
        update=lambda self, context: update_keymap(self, context)
    )
    quick_camera_ctrl: BoolProperty(
        name="Ctrl",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    quick_camera_alt: BoolProperty(
        name="Alt",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    quick_camera_shift: BoolProperty(
        name="Shift",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )

    # Camera Controls
    camera_controls_key: StringProperty(
        name="Camera Controls Key",
        default='V',
        update=lambda self, context: update_keymap(self, context)
    )
    camera_controls_ctrl: BoolProperty(
        name="Ctrl",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    camera_controls_alt: BoolProperty(
        name="Alt",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    camera_controls_shift: BoolProperty(
        name="Shift",
        default=True,
        update=lambda self, context: update_keymap(self, context)
    )

    capture_key: BoolProperty(
        name="Capture Key",
        default=False
    )

    # Favorite Camera
    favorite_camera_key: StringProperty(
        name="Favorite Camera Key",
        default='V',
        update=lambda self, context: update_keymap(self, context)
    )
    favorite_camera_ctrl: BoolProperty(
        name="Ctrl",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )
    favorite_camera_alt: BoolProperty(
        name="Alt",
        default=True,
        update=lambda self, context: update_keymap(self, context)
    )
    favorite_camera_shift: BoolProperty(
        name="Shift",
        default=False,
        update=lambda self, context: update_keymap(self, context)
    )

    show_viewport_button: BoolProperty(
        name="Show the Viewport Render button in the 3D Viewport header",
        description="Show the Viewport Render button in the 3D Viewport header",
        default=True
    )

    show_pin_button: BoolProperty(
        name="Show the Pin button in the 3D Viewport header",
        description="Show the Pin button in the 3D Viewport header",
        default=True
    )

    show_render_tools_n_panel: BoolProperty(
        name="Show Render Tools in N-panel",
        description="Show the Render Tools panel in the N-panel",
        default=True
    )
    show_quick_camera_n_panel: BoolProperty(
        name="Show Quick Camera in N-panel",
        description="Show the Quick Camera panel in the N-panel",
        default=True
    )
    show_shot_list_n_panel: BoolProperty(
        name="Show Shot List in N-panel",
        description="Show the Shot List panel in the N-panel",
        default=True
    )
    show_camera_list_n_panel: BoolProperty(
        name="Show Camera List in N-panel",
        description="Show the Camera List panel in the N-panel",
        default=True
    )
    show_camera_info_overlay_n_panel: BoolProperty(
        name="Show Camera Info Overlay in N-panel",
        description="Show the Camera Info Overlay panel in the N-panel",
        default=True
    )

    show_camera_info_overlay: BoolProperty(
        name="Show Camera Info Overlay",
        description="Show camera information overlay in viewport when in camera view",
        default=True,
        update=lambda self, context: operators.toggle_camera_info_overlay(self.show_camera_info_overlay)
    )

    show_camera_notes: BoolProperty(
        name="Show Camera Notes",
        description="Show camera notes overlay in viewport when in camera view",
        default=True,
        update=lambda self, context: operators.toggle_camera_notes_overlay(self.show_camera_notes)
    )

    # Camera Info Overlay Settings
    camera_info_position_x: bpy.props.IntProperty(
        name="Position X",
        description="Horizontal position from left of the camera info overlay",
        default=30,
        soft_min=-4000,
        soft_max=4000,
        update=lambda self, context: (operators.sync_camera_info_overlay_position(self, context), _redraw_viewports(context))
    )

    camera_info_position_y: bpy.props.IntProperty(
        name="Position Y",
        description="Vertical position from bottom of the camera info overlay",
        default=100,
        soft_min=-4000,
        soft_max=4000,
        update=lambda self, context: (operators.sync_camera_info_overlay_position(self, context), _redraw_viewports(context))
    )

    camera_info_sticky_overlay: BoolProperty(
        name="Sticky Overlay",
        description="Keep the camera info overlay attached to the camera frame while keeping the current screen position",
        default=False,
        update=lambda self, context: (operators.sync_camera_info_overlay_position(self, context), _redraw_viewports(context))
    )

    camera_info_font_size: bpy.props.IntProperty(
        name="Font Size",
        description="Font size for camera info text",
        default=15,
        min=8,
        max=72,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_single_line: BoolProperty(
        name="Single Line Layout",
        description="Display all info in a single line instead of multiple lines",
        default=False,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_separator: StringProperty(
        name="Separator",
        description="Separator character for single line layout",
        default=" | ",
        maxlen=10,
        update=lambda self, context: _redraw_viewports(context)
    )

    # Info display toggles
    camera_info_show_name: BoolProperty(
        name="Show Camera/Shot Name",
        description="Display camera or shot name",
        default=True,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_show_frames: BoolProperty(
        name="Show Frame Range",
        description="Display frame range for shots",
        default=True,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_show_focal: BoolProperty(
        name="Show Focal Length",
        description="Display focal length or ortho scale",
        default=True,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_show_focus: BoolProperty(
        name="Show Focus Distance",
        description="Display focus distance when DoF is enabled",
        default=True,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_show_fstop: BoolProperty(
        name="Show F-Stop",
        description="Display F-Stop when DoF is enabled",
        default=True,
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_background_color: bpy.props.FloatVectorProperty(
        name="Background Color",
        description="Color and opacity of the background",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.6),
        update=lambda self, context: _redraw_viewports(context)
    )

    camera_info_font_color: bpy.props.FloatVectorProperty(
        name="Font Color",
        description="Color and opacity of the text",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=lambda self, context: _redraw_viewports(context)
    )

    # Default Camera Settings
    default_passepartout: bpy.props.FloatProperty(
        name="Passepartout",
        description="Default passepartout alpha for new cameras",
        default=0.5,
        min=0.0,
        max=1.0
    )

    default_type: bpy.props.EnumProperty(
        name="Camera Type",
        items=[
            ('PERSP', "Perspective", "Perspective camera"),
            ('ORTHO', "Orthographic", "Orthographic camera"),
            ('PANO', "Panoramic", "Panoramic camera")
        ],
        default='PERSP'
    )

    default_clip_start: bpy.props.FloatProperty(
        name="Clip Start",
        description="Default clip start for new cameras",
        default=0.1,
        min=0.01,
        max=1000.0
    )

    default_clip_end: bpy.props.FloatProperty(
        name="Clip End",
        description="Default clip end for new cameras",
        default=1000.0,
        min=1.0,
        max=10000.0
    )

    default_lens: bpy.props.FloatProperty(
        name="Focal Length",
        description="Default focal length for new perspective cameras",
        default=50.0,
        min=1.0,
        max=5000.0
    )

    default_ortho_scale: bpy.props.FloatProperty(
        name="Ortho Scale",
        description="Default orthographic scale for new orthographic cameras",
        default=6.0,
        min=0.01,
        max=1000.0
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="N-panel Settings:")
        box.prop(self, "show_render_tools_n_panel")
        box.prop(self, "show_quick_camera_n_panel")
        box.prop(self, "show_shot_list_n_panel")
        box.prop(self, "show_camera_list_n_panel")
        box.prop(self, "show_camera_info_overlay_n_panel")

        box = layout.box()
        row = box.row()
        row.label(text="Viewport Settings:")
        row = box.row()
        row.prop(self, "show_camera_info_overlay")
        row = box.row()
        row.prop(self, "show_camera_notes")

        # Camera info overlay settings (only show if enabled)
        if self.show_camera_info_overlay:
            sub_box = box.box()
            sub_box.label(text="Camera Info Overlay Settings:", icon='PREFERENCES')

            col = sub_box.column(align=True)
            col.label(text="Layout:")
            col.prop(self, "camera_info_single_line")
            if self.camera_info_single_line:
                col.prop(self, "camera_info_separator", text="Separator")

            col = sub_box.column(align=True)
            col.label(text="Position & Appearance:")
            row = col.row(align=True)
            row.prop(self, "camera_info_position_x")
            row.prop(self, "camera_info_position_y")
            col.prop(self, "camera_info_font_size")
            col.prop(self, "camera_info_font_color", text="Font Color")
            col.prop(self, "camera_info_background_color", text="Background")

            col = sub_box.column(align=True)
            col.label(text="Display Options:")
            col.prop(self, "camera_info_show_name")
            col.prop(self, "camera_info_show_frames")
            col.prop(self, "camera_info_show_focal")
            col.prop(self, "camera_info_show_focus")
            col.prop(self, "camera_info_show_fstop")

        box = layout.box()
        box.label(text="Default Camera Settings:")
        box.prop(self, "default_type")

        row = box.row(align=True)
        row.prop(self, "default_passepartout")

        row = box.row()
        if self.default_type == 'ORTHO':
            row.prop(self, "default_ortho_scale")
        else:
            row.prop(self, "default_lens")

        row = box.row(align=True)
        row.prop(self, "default_clip_start")
        row.prop(self, "default_clip_end")

        box = layout.box()
        row = box.row()
        row.label(text="Render Tools Settings:")
        row = box.row()
        row.prop(self, "show_viewport_button")
        row = box.row()
        row.prop(self, "show_pin_button")

        box = layout.box()
        row = box.row()
        row.label(text="Camera Tools Settings:")

        row = box.row()
        row.label(text="Quick Camera Pie Menu Keybind:")
        if self.capture_key:
            row.operator("wm.capture_keymap", text="Press a Key", icon="KEYINGSET").pie_menu = "quick_camera"
        else:
            key_combination = f"{'Ctrl+' if self.quick_camera_ctrl else ''}{'Alt+' if self.quick_camera_alt else ''}{'Shift+' if self.quick_camera_shift else ''}{self.quick_camera_key or '(None)'}"
            row.operator("wm.capture_keymap", text=key_combination, icon="KEYINGSET").pie_menu = "quick_camera"
        row.operator("wm.remove_keymap", text="", icon="X").pie_menu = "quick_camera"
        row = box.row()
        row.prop(self, "quick_camera_ctrl")
        row.prop(self, "quick_camera_alt")
        row.prop(self, "quick_camera_shift")

        row = box.row()
        row.label(text="Camera Controls Pie Menu Keybind:")
        if self.capture_key:
            row.operator("wm.capture_keymap", text="Press a Key", icon="KEYINGSET").pie_menu = "camera_controls"
        else:
            key_combination = f"{'Ctrl+' if self.camera_controls_ctrl else ''}{'Alt+' if self.camera_controls_alt else ''}{'Shift+' if self.camera_controls_shift else ''}{self.camera_controls_key or '(None)'}"
            row.operator("wm.capture_keymap", text=key_combination, icon="KEYINGSET").pie_menu = "camera_controls"
        row.operator("wm.remove_keymap", text="", icon="X").pie_menu = "camera_controls"
        row = box.row()
        row.prop(self, "camera_controls_ctrl")
        row.prop(self, "camera_controls_alt")
        row.prop(self, "camera_controls_shift")

        row = box.row()
        row.label(text="Favorite Camera Pie Menu Keybind:")
        if self.capture_key:
            row.operator("wm.capture_keymap", text="Press a Key", icon="KEYINGSET").pie_menu = "favorite_camera"
        else:
            key_combination = f"{'Ctrl+' if self.favorite_camera_ctrl else ''}{'Alt+' if self.favorite_camera_alt else ''}{'Shift+' if self.favorite_camera_shift else ''}{self.favorite_camera_key or '(None)'}"
            row.operator("wm.capture_keymap", text=key_combination, icon="KEYINGSET").pie_menu = "favorite_camera"
        row.operator("wm.remove_keymap", text="", icon="X").pie_menu = "favorite_camera"
        row = box.row()
        row.prop(self, "favorite_camera_ctrl")
        row.prop(self, "favorite_camera_alt")
        row.prop(self, "favorite_camera_shift")

        box = layout.box()
        row = box.row()
        row.label(text="This code was written with the help of Claude.AI, if you know how to improve it please let me know!")
        row = box.row()
        row.operator("wm.url_open", text="Visit GitHub", icon="URL").url = "https://github.com/Kyokaz/Kyokaz-s-Toolbox"

def draw_viewport_header(self, context):
    """Draw playblast and snapshot buttons in the 3D View header."""
    preferences = get_addon_preferences(context)
    if not preferences or not preferences.show_viewport_button:
        return

    layout = self.layout.row(align=True)
    layout.operator("object.playblast_confirm", text="Playblast", icon='RENDER_ANIMATION')
    layout.operator("object.playblast_settings", text="", icon='PREFERENCES')
    layout.operator("object.snapshot_render", text="Snapshot", icon='RENDER_RESULT')
    layout.operator("object.snapshot_render_settings", text="", icon='PREFERENCES')

def draw_local_camera_button(self, context):
    """Draw local camera pin button in the 3D View header."""
    preferences = get_addon_preferences(context)
    if not preferences or not preferences.show_pin_button:
        return

    if hasattr(context, 'space_data') and hasattr(context.space_data, 'use_local_camera'):
        icon = 'PINNED' if context.space_data.use_local_camera else 'UNPINNED'
        self.layout.operator("object.toggle_local_camera", text="", icon=icon)

def draw_set_frame_buttons(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.operator("scene.set_frame", text="Start", icon='TRIA_LEFT_BAR').frame_type = 'START'
    row.operator("scene.set_frame", text="End", icon='TRIA_RIGHT_BAR').frame_type = 'END'

def register_keymap():
    """Register keymap items for pie menus with error handling."""
    try:
        wm = bpy.context.window_manager
        if not wm or not wm.keyconfigs or not wm.keyconfigs.addon:
            logging.warning("Cannot register keymaps - window manager not available")
            return

        addon_prefs = get_addon_preferences(bpy.context)
        if addon_prefs is None:
            logging.warning("Cannot register keymaps - addon preferences not available")
            return

        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')

        # Quick Camera Pie Menu
        if addon_prefs.quick_camera_key:
            try:
                kmi = km.keymap_items.new('wm.call_menu_pie', addon_prefs.quick_camera_key, "PRESS",
                                          ctrl=addon_prefs.quick_camera_ctrl,
                                          alt=addon_prefs.quick_camera_alt,
                                          shift=addon_prefs.quick_camera_shift)
                kmi.properties.name = "VIEW3D_MT_PIE_QuickCamera"
                addon_keymaps.append((km, kmi))
            except Exception as e:
                logging.warning("Failed to register Quick Camera keymap: %s", e)

        # Camera Controls Pie Menu
        if addon_prefs.camera_controls_key:
            try:
                kmi = km.keymap_items.new('wm.call_menu_pie', addon_prefs.camera_controls_key, "PRESS",
                                          ctrl=addon_prefs.camera_controls_ctrl,
                                          alt=addon_prefs.camera_controls_alt,
                                          shift=addon_prefs.camera_controls_shift)
                kmi.properties.name = "VIEW3D_MT_PIE_camera_controls"
                addon_keymaps.append((km, kmi))
            except Exception as e:
                logging.warning("Failed to register Camera Controls keymap: %s", e)

        # Favorite Camera Pie Menu
        if addon_prefs.favorite_camera_key:
            try:
                kmi = km.keymap_items.new('wm.call_menu_pie', addon_prefs.favorite_camera_key, "PRESS",
                                          ctrl=addon_prefs.favorite_camera_ctrl,
                                          alt=addon_prefs.favorite_camera_alt,
                                          shift=addon_prefs.favorite_camera_shift)
                kmi.properties.name = "VIEW3D_MT_PIE_favorite_camera"
                addon_keymaps.append((km, kmi))
            except Exception as e:
                logging.warning("Failed to register Favorite Camera keymap: %s", e)
    except (KeyError, AttributeError) as e:
        logging.warning("Cannot register keymaps - addon preferences not available: %s", e)

def unregister_keymap():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

def update_keymap(self, context):
    unregister_keymap()
    register_keymap()

classes = (
    MyAddonPreferences,
    *operators.classes,
    *panels.classes,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.custom_name_props = bpy.props.PointerProperty(type=operators.CustomNameProperties)
    bpy.types.VIEW3D_HT_header.append(draw_viewport_header)
    bpy.types.VIEW3D_HT_header.append(draw_local_camera_button)
    
    # Add Start/End frame buttons to timeline/dopesheet header
    # TIME_MT_editor_menus was removed in Blender 5.0, use DOPESHEET_HT_header instead
    if hasattr(bpy.types, 'DOPESHEET_HT_header'):
        bpy.types.DOPESHEET_HT_header.append(draw_set_frame_buttons)
    elif hasattr(bpy.types, 'TIME_MT_editor_menus'):
        bpy.types.TIME_MT_editor_menus.append(draw_set_frame_buttons)
    
    bpy.types.Scene.camera_index = bpy.props.IntProperty()
    bpy.types.Scene.active_marker_index = bpy.props.IntProperty()
    bpy.types.Scene.snapshot_settings = bpy.props.PointerProperty(type=panels.SnapshotSettings)
    bpy.types.Scene.render_tools_settings = bpy.props.PointerProperty(type=operators.RenderToolsSettings)
    bpy.types.Scene.viewport_render_settings = bpy.props.PointerProperty(type=panels.ViewportRenderSettings)
    bpy.types.Scene.favorite_cameras = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.render_presets = PointerProperty(type=operators.RenderPresetsCollection)
    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Selected Collection Index",
        update=operators.update_collection_index  
    )
    bpy.types.Scene.camera_notes = bpy.props.CollectionProperty(type=operators.CameraNoteItem)
    bpy.types.Scene.active_note_index = bpy.props.IntProperty(name="Active Note Index", default=0)
    
    # Panel-specific scene properties
    bpy.types.Scene.shot_list_color = bpy.props.FloatVectorProperty(
        name="Shot List Color",
        subtype='COLOR',
        default=(0.2, 0.6, 1.0, 1.0),
        size=4,
        min=0.0,
        max=1.0
    )
    bpy.types.Scene.camera_list_color = bpy.props.FloatVectorProperty(
        name="Camera List Color",
        subtype='COLOR',
        default=(1.0, 0.6, 0.2, 1.0),
        size=4,
        min=0.0,
        max=1.0
    )
    bpy.types.Scene.show_camera_details = bpy.props.BoolProperty(
        name="Show Camera Details",
        default=True
    )
    
    register_keymap()
    
    # Register camera info overlay if enabled
    try:
        preferences = get_addon_preferences(bpy.context)
        if preferences is None:
            operators.register_camera_info_overlay()
            operators.register_camera_notes_overlay()
            return
        if preferences.show_camera_info_overlay:
            operators.register_camera_info_overlay()
        if preferences.show_camera_notes:
            operators.register_camera_notes_overlay()
    except AttributeError:
        operators.register_camera_info_overlay()
        operators.register_camera_notes_overlay()

def unregister():
    unregister_keymap()
    
    # Unregister camera overlays
    operators.unregister_camera_info_overlay()
    operators.unregister_camera_notes_overlay()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_HT_header.remove(draw_viewport_header)
    bpy.types.VIEW3D_HT_header.remove(draw_local_camera_button)
    
    # Remove Start/End frame buttons from timeline/dopesheet header
    if hasattr(bpy.types, 'DOPESHEET_HT_header'):
        bpy.types.DOPESHEET_HT_header.remove(draw_set_frame_buttons)
    elif hasattr(bpy.types, 'TIME_MT_editor_menus'):
        bpy.types.TIME_MT_editor_menus.remove(draw_set_frame_buttons)
    
    del bpy.types.Scene.render_presets
    del bpy.types.Scene.active_marker_index
    del bpy.types.Scene.camera_index
    del bpy.types.Scene.custom_name_props
    del bpy.types.Scene.render_tools_settings
    del bpy.types.Scene.viewport_render_settings
    del bpy.types.Scene.snapshot_settings
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.favorite_cameras
    del bpy.types.Scene.camera_notes
    del bpy.types.Scene.active_note_index
    del bpy.types.Scene.shot_list_color
    del bpy.types.Scene.camera_list_color
    del bpy.types.Scene.show_camera_details

if __name__ == "__main__":
    register()