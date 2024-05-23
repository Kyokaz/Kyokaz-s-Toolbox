# File: panels.py
import bpy
from bpy.types import Panel

class OBJECT_PT_toggle_interpolation_panel(Panel):
    bl_label = "Kyokaz's Toolbox"
    bl_idname = "OBJECT_PT_toggle_interpolation_panel"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Kyokaz Toolbox'

    @classmethod
    def poll(cls, context):
        return context.area.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR', 'TIMELINE', 'ACTION_EDITOR', 'FCURVES'}

    def draw(self, context):
        layout = self.layout

        layout.operator("object.toggle_auto_keying", text="Auto Keying: On" if bpy.context.scene.tool_settings.use_keyframe_insert_auto else "Auto Keying: Off", icon='AUTO')
        layout.separator()
        layout.label(text="Bake Selected Keyframes:")
        layout.operator("object.bake_keyframes_per_steps", icon='ANIM_DATA')
        layout.operator("object.add_keyframes_operator", icon='KEY_HLT')
        layout.operator("object.delete_keyframes_per_steps", icon='KEY_DEHLT')
        layout.separator()
        layout.label(text="Toggle Default Interpolation:")
        layout.operator("object.toggle_default_interpolation", icon='IPO_CONSTANT' if bpy.context.preferences.edit.keyframe_new_interpolation_type == 'CONSTANT' else 'IPO_BEZIER')
        layout.separator()
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
        layout.label(text="Disable Renders for Hidden Objects:")
        row = layout.row()
        row.operator("object.select_hidden_disable_render", text="Apply for Hidden Objects", icon='RESTRICT_RENDER_ON')
        row = layout.row()
        row.operator("object.create_exclude_hidden_collection", text="Selected to Excluded Collection")

class OBJECT_PT_SelectHiddenDisableRenderPanel(bpy.types.Panel):
    bl_label = "Render Tools"
    bl_idname = "OBJECT_PT_select_hidden_disable_render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Disable Renders for Hidden Objects:")
        row = layout.row()
        row.operator("object.select_hidden_disable_render", text="Apply for Hidden Objects", icon='RESTRICT_RENDER_ON')
        row = layout.row()
        row.operator("object.create_exclude_hidden_collection", text="Selected to Excluded Collection", icon='COLLECTION_NEW')

class OBJECT_PT_CameraTools(bpy.types.Panel):
    bl_label = "Quick Camera"
    bl_idname = "OBJECT_PT_CameraTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.custom_name_props

        box = layout.box()
        box.label(text="Add New Camera:")
        row = box.row()
        row.prop(props, "collection_name", text="", icon="COLLECTION_NEW")
        row.prop(props, "existing_collection", text="", icon="COLLECTION_NEW")
        row.operator("wm.show_popup_message", text="", icon='INFO')
        row = box.row()
        row.prop(props, "camera_name")
        row.operator("object.add_camera", text="", icon="ADD")
        row = box.row()
        row.prop(props, "shot_name")
        row.operator("object.add_camera_with_marker", text="", icon="ADD")
        box = layout.box()
        box.label(text="Copy Camera:")
        row = box.row()
        row.operator("object.add_camera_copy_properties", text="Copy Camera", icon="CAMERA_DATA")
        row.operator("object.add_camera_shot_copy_properties", text="Copy Shot", icon="VIEW_CAMERA")

class OBJECT_PT_CameraTools_Status(bpy.types.Panel):
    bl_parent_id = "OBJECT_PT_CameraTools"
    bl_label = "Camera Status"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.custom_name_props

        layout.prop(scene, "collection_for_status", text="", icon="COLLECTION_NEW")
        selected_collection = bpy.data.collections.get(scene.collection_for_status)

        if selected_collection:
            markers = [marker for marker in scene.timeline_markers if marker.camera and marker.camera.name in selected_collection.objects]
            markers.sort(key=lambda marker: int(marker.name.split(" ")[-1]))

            shots = []
            total_frames = 0
            if markers:
                for i in range(len(markers) - 1):
                    start_frame = markers[i].frame
                    end_frame = markers[i + 1].frame
                    frames_between_markers = end_frame - start_frame
                    total_frames += frames_between_markers
                    shots.append((markers[i].name, start_frame, end_frame, frames_between_markers))

                last_marker = markers[-1]
                start_frame = last_marker.frame
                end_frame = scene.frame_end
                frames_between_markers = end_frame - start_frame
                total_frames += frames_between_markers
                shots.append((last_marker.name, start_frame, end_frame, frames_between_markers))
            else:
                shots.append(("Not enough markers", 0, 0, 0))

            shots_panel = layout.box()
            shots_panel.label(text="Shots:")
            shots_subpanel = shots_panel.column()
            for shot_label, start_frame, end_frame, shot_frames in shots:
                row = shots_subpanel.row()

                camera_object = bpy.data.objects.get(shot_label)
                if camera_object:
                    op_select = row.operator("scene.select_camera", text="", icon='RESTRICT_SELECT_OFF')
                    op_select.camera_name = camera_object.name
                else:
                    row.label(text="Camera not found", icon='ERROR')

                row.label(text=f"{shot_label}: {start_frame} - {end_frame} ({shot_frames} frames)")
                op = row.operator("scene.jump_to_marker", text="", icon='VIEW_CAMERA')
                op.marker_name = shot_label
                op_remove = row.operator("scene.remove_marker_and_camera", text="", icon='TRASH')
                op_remove.marker_name = shot_label

                op_preview = row.operator("scene.set_preview_range", text="", icon='PREVIEW_RANGE')
                op_preview.start_frame = start_frame
                op_preview.end_frame = end_frame
                op_preview.toggle = not scene.use_preview_range if scene.frame_preview_start == start_frame and scene.frame_preview_end == end_frame else True

            shots_subpanel.operator("scene.remove_all_shot_cameras", text="Remove All Shots", icon='TRASH')

            current_frame = scene.frame_current
            layout.label(text=f"Current Frame: {current_frame}")
            layout.label(text=f"Total Shot Duration: {total_frames} frames")
        else:
            layout.label(text="No collection selected")

        layout.separator()
        row = layout.row()
        row.operator("object.viewport_render_confirm", text="Viewport Render", icon='RENDER_STILL')
        layout.prop(context.scene.render, "filepath", text="Output Path")
        layout.operator("object.open_output_directory", text="Open Output Directory", icon='FILE_FOLDER')
