bl_info = {
    "name": "Toggle Default Interpolation",
    "author": "Kyokaz",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Action Editor > Interpolation Tab",
    "description": "Toggle Default Interpolation between Constant and Bezier, ChatGPT helped me to code this lol",
    "category": "Animation"
}

bl_info = {
    "name": "Toggle Default Interpolation",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Action Editor, Graph Editor, Dope Sheet, Timeline > Interpolation Tab",
    "description": "Toggle Default Interpolation between Constant and Bezier",
    "category": "Animation"
}

import bpy

# Define a custom operator to toggle interpolation
class OBJECT_OT_toggle_interpolation(bpy.types.Operator):
    """Toggle Interpolation between Constant and Bezier"""
    bl_idname = "object.toggle_interpolation"
    bl_label = "Toggle Interpolation"

    def execute(self, context):
        # Get current interpolation type
        current_interpolation = bpy.context.preferences.edit.keyframe_new_interpolation_type
        # Toggle interpolation
        if current_interpolation == 'CONSTANT':
            bpy.context.preferences.edit.keyframe_new_interpolation_type = 'BEZIER'
        else:
            bpy.context.preferences.edit.keyframe_new_interpolation_type = 'CONSTANT'
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'
        current_interpolation = bpy.context.preferences.edit.keyframe_new_interpolation_type
        if current_interpolation == 'CONSTANT':
            layout.label(text="Interpolation: CONSTANT")
        else:
            layout.label(text="Interpolation: BEZIER")

# Define a custom panel to place the toggle button in various editors
class OBJECT_PT_toggle_interpolation_panel(bpy.types.Panel):
    """Toggle Interpolation Panel"""
    bl_label = "Interpolation"
    bl_idname = "OBJECT_PT_toggle_interpolation_panel"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Interpolation'

    @classmethod
    def poll(cls, context):
        return context.area.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR', 'TIMELINE', 'ACTION_EDITOR'}

    def draw(self, context):
        layout = self.layout
        layout.operator("object.toggle_interpolation")
        current_interpolation = bpy.context.preferences.edit.keyframe_new_interpolation_type
        if current_interpolation == 'CONSTANT':
            layout.label(text="Interpolation: CONSTANT")
        else:
            layout.label(text="Interpolation: BEZIER")


classes = (
    OBJECT_OT_toggle_interpolation,
    OBJECT_PT_toggle_interpolation_panel
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()