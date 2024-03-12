import bpy

# Define a custom operator to toggle the default interpolation
class OBJECT_OT_toggle_default_interpolation(bpy.types.Operator):
    """Toggle Default Interpolation between Constant and Bezier"""
    bl_idname = "object.toggle_default_interpolation"
    bl_label = "Toggle Default"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences = bpy.context.preferences.edit
        preferences.keyframe_new_interpolation_type = 'CONSTANT' if preferences.keyframe_new_interpolation_type != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

# Define a custom operator to toggle interpolation for selected keyframes
class OBJECT_OT_toggle_interpolation_selected(bpy.types.Operator):
    """Toggle Interpolation for Selected Keyframes between Constant and Bezier"""
    bl_idname = "object.toggle_interpolation_selected"
    bl_label = "Selected Keyframe"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.animation_data:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        if keyframe.select_control_point:
                            keyframe.interpolation = 'CONSTANT' if keyframe.interpolation != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

# Define a custom operator to toggle interpolation for all keyframes (for selected objects)
class OBJECT_OT_toggle_interpolation_all(bpy.types.Operator):
    """Toggle Interpolation for All Keyframes between Constant and Bezier (for selected objects)"""
    bl_idname = "object.toggle_interpolation_all"
    bl_label = "Selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.animation_data:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.interpolation = 'CONSTANT' if keyframe.interpolation != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to all keyframes as Constant (for selected objects)
class OBJECT_OT_apply_all_constant(bpy.types.Operator):
    """Apply Constant Interpolation to All Keyframes (for selected objects)"""
    bl_idname = "object.apply_all_constant"
    bl_label = "Constant"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.animation_data:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.interpolation = 'CONSTANT'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to all keyframes as Bezier (for selected objects)
class OBJECT_OT_apply_all_bezier(bpy.types.Operator):
    """Apply Bezier Interpolation to All Keyframes (for selected objects)"""
    bl_idname = "object.apply_all_bezier"
    bl_label = "Bezier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.animation_data:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.interpolation = 'BEZIER'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to all keyframes as Linear (for selected objects)
class OBJECT_OT_apply_all_linear(bpy.types.Operator):
    """Apply Linear Interpolation to All Keyframes (for selected objects)"""
    bl_idname = "object.apply_all_linear"
    bl_label = "Linear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.animation_data:
                for fcurve in obj.animation_data.action.fcurves:
                    for keyframe in fcurve.keyframe_points:
                        keyframe.interpolation = 'LINEAR'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to selected keyframes as Constant (for selected objects)
class OBJECT_OT_apply_selected_constant(bpy.types.Operator):
    """Apply Constant Interpolation to Selected Keyframes (for selected objects)"""
    bl_idname = "object.apply_selected_constant"
    bl_label = "Constant"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        action = context.object.animation_data.action
        if action:
            for obj in bpy.context.selected_objects:
                if obj.animation_data:
                    for fcurve in obj.animation_data.action.fcurves:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.select_control_point:
                                keyframe.interpolation = 'CONSTANT'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to selected keyframes as Bezier (for selected objects)
class OBJECT_OT_apply_selected_bezier(bpy.types.Operator):
    """Apply Bezier Interpolation to Selected Keyframes (for selected objects)"""
    bl_idname = "object.apply_selected_bezier"
    bl_label = "Bezier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        action = context.object.animation_data.action
        if action:
            for obj in bpy.context.selected_objects:
                if obj.animation_data:
                    for fcurve in obj.animation_data.action.fcurves:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.select_control_point:
                                keyframe.interpolation = 'BEZIER'
        return {'FINISHED'}

# Define a custom operator to apply interpolation to selected keyframes as Linear (for selected objects)
class OBJECT_OT_apply_selected_linear(bpy.types.Operator):
    """Apply Linear Interpolation to Selected Keyframes (for selected objects)"""
    bl_idname = "object.apply_selected_linear"
    bl_label = "Linear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        action = context.object.animation_data.action
        if action:
            for obj in bpy.context.selected_objects:
                if obj.animation_data:
                    for fcurve in obj.animation_data.action.fcurves:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.select_control_point:
                                keyframe.interpolation = 'LINEAR'
        return {'FINISHED'}


# Define a custom operator to toggle auto keying
class OBJECT_OT_toggle_auto_keying(bpy.types.Operator):
    """Toggle Auto Keying"""
    bl_idname = "object.toggle_auto_keying"
    bl_label = "Auto Keying"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if hasattr(context, 'scene'):
            bpy.context.scene.tool_settings.use_keyframe_insert_auto = not bpy.context.scene.tool_settings.use_keyframe_insert_auto
        else:
            self.report({'ERROR'}, "No active scene found")
        return {'FINISHED'}

    def draw(self, context):
        if hasattr(context, 'scene'):
            is_enabled = bpy.context.scene.tool_settings.use_keyframe_insert_auto
            self.layout.operator("object.toggle_auto_keying", text="Auto Keying: On" if is_enabled else "Auto Keying: Off", icon='AUTO')
            
# Define a custom operator to add keyframes every 2 steps
class OBJECT_OT_add_keyframes_operator(bpy.types.Operator):
    """Operator to add keyframes with custom step size between selected keyframes"""
    bl_idname = "object.add_keyframes_operator"
    bl_label = "Quick Bake"

    steps: bpy.props.IntProperty(name="Steps", default=2, min=1, description="Number of steps between keyframes")

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.animation_data is not None

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        ad = obj.animation_data
        action = ad.action

        if action is None:
            self.report({'WARNING'}, "No action found")
            return {'CANCELLED'}

        for fc in action.fcurves:
            keyframes = [kp for kp in fc.keyframe_points if kp.select_control_point]

            for i in range(len(keyframes) - 1):
                start_kp = keyframes[i]
                end_kp = keyframes[i + 1]

                start_frame = int(start_kp.co.x)
                end_frame = int(end_kp.co.x)
                start_value = start_kp.co.y
                end_value = end_kp.co.y

                for frame in range(start_frame + self.steps, end_frame, self.steps):
                    t = (frame - start_frame) / (end_frame - start_frame)
                    interpolated_value = (1 - t) * start_value + t * end_value
                    fc.keyframe_points.insert(frame, interpolated_value)

        self.report({'INFO'}, f"Keyframes added successfully with step size {self.steps}")
        return {'FINISHED'}


# Define a custom panel to place the toggle buttons in various editors
class OBJECT_PT_toggle_interpolation_panel(bpy.types.Panel):
    """Toggle Interpolation Panel"""
    bl_label = "Kyokaz's Toolbox"
    bl_idname = "OBJECT_PT_toggle_interpolation_panel"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Kyokaz Toolbox'

    @classmethod
    def poll(cls, context):
        return context.area.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR', 'TIMELINE', 'ACTION_EDITOR'}

    def draw(self, context):
        layout = self.layout

        # Draw Auto Keying button
        layout.operator("object.toggle_auto_keying", text="Auto Keying: On" if bpy.context.scene.tool_settings.use_keyframe_insert_auto else "Auto Keying: Off", icon='AUTO')
        
        layout.separator()
        layout.label(text="Bake Selected Keyframes:")
        layout.operator("object.add_keyframes_operator", icon='KEY_HLT')

        layout.separator()
        layout.label(text="Toggle Default Interpolation:")
        layout.operator("object.toggle_default_interpolation", icon='IPO_CONSTANT' if bpy.context.preferences.edit.keyframe_new_interpolation_type == 'CONSTANT' else 'IPO_BEZIER')
        layout.separator()

        # Display text status
        preferences = bpy.context.preferences.edit
        interpolation_mode = preferences.keyframe_new_interpolation_type.capitalize()
        layout.label(text=f"Current Default: {interpolation_mode}")
        
        layout.separator()
        layout.label(text="Toggle to Selected:")
        row = layout.row()
        row.operator("object.toggle_interpolation_selected", text="Keyframe", icon='KEY_HLT')
        row.operator("object.toggle_interpolation_all", text="Object", icon='CONSTRAINT')
        
        layout.separator()
        layout.label(text="Apply to Selected Object:")
        row = layout.row()
        row.operator("object.apply_all_constant", icon='IPO_CONSTANT')
        row.operator("object.apply_all_bezier", icon='IPO_BEZIER')
        row.operator("object.apply_all_linear", icon='IPO_LINEAR')
        
        layout.separator()
        layout.label(text="Apply to Selected Keyframe:")
        row = layout.row()
        row.operator("object.apply_selected_constant", icon='IPO_CONSTANT')
        row.operator("object.apply_selected_bezier", icon='IPO_BEZIER')
        row.operator("object.apply_selected_linear", icon='IPO_LINEAR')

classes = (
    OBJECT_OT_toggle_default_interpolation,
    OBJECT_OT_add_keyframes_operator,
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
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
