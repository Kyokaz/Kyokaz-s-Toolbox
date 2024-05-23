# File: operators.py
import bpy
from bpy.types import Menu
from bpy.props import IntProperty, BoolProperty, EnumProperty, FloatVectorProperty
import os
import subprocess
import sys

class OBJECT_OT_toggle_default_interpolation(bpy.types.Operator):
    bl_idname = "object.toggle_default_interpolation"
    bl_label = "Toggle Default"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences = bpy.context.preferences.edit
        preferences.keyframe_new_interpolation_type = 'CONSTANT' if preferences.keyframe_new_interpolation_type != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

class OBJECT_OT_toggle_interpolation_selected(bpy.types.Operator):
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

class OBJECT_OT_toggle_interpolation_all(bpy.types.Operator):
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

class OBJECT_OT_apply_all_constant(bpy.types.Operator):
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

class OBJECT_OT_apply_all_bezier(bpy.types.Operator):
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

class OBJECT_OT_apply_all_linear(bpy.types.Operator):
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

class OBJECT_OT_apply_selected_constant(bpy.types.Operator):
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

class OBJECT_OT_apply_selected_bezier(bpy.types.Operator):
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

class OBJECT_OT_apply_selected_linear(bpy.types.Operator):
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

class OBJECT_OT_toggle_auto_keying(bpy.types.Operator):
    bl_idname = "object.toggle_auto_keying"
    bl_label = "Auto Keying"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if hasattr(context, 'scene'):
            bpy.context.scene.tool_settings.use_keyframe_insert_auto = not bpy.context.scene.tool_settings.use_keyframe_insert_auto
        else:
            self.report({'ERROR'}, "No active scene found")
        return {'FINISHED'}

class OBJECT_OT_add_keyframes_operator(bpy.types.Operator):
    bl_idname = "object.add_keyframes_operator"
    bl_label = "Add Per Steps"
    bl_options = {'REGISTER', 'UNDO'}

    steps: IntProperty(name="Steps", default=2, min=1, description="Number of steps between keyframes")

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

class OBJECT_OT_delete_keyframes_per_steps(bpy.types.Operator):
    bl_idname = "object.delete_keyframes_per_steps"
    bl_label = "Delete Per Steps"
    bl_options = {'REGISTER', 'UNDO'}

    steps: IntProperty(name="Steps", default=1, min=1, description="Number of steps between keyframes")

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.animation_data is not None

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        ad = obj.animation_data
        if ad is None or ad.action is None:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}

        action = ad.action

        for fc in action.fcurves:
            keyframes = [kp for kp in fc.keyframe_points if kp.select_control_point]

            for i in range(len(keyframes) - 1, -1, -self.steps):
                fc.keyframe_points.remove(keyframes[i])

        self.report({'INFO'}, f"Keyframes deleted successfully with step size {self.steps}")
        return {'FINISHED'}

class OBJECT_OT_bake_keyframes_per_steps(bpy.types.Operator):
    bl_idname = "object.bake_keyframes_per_steps"
    bl_label = "Bake Per Steps"
    bl_options = {'REGISTER', 'UNDO'}

    steps: IntProperty(name="Steps", default=1, min=1, description="Number of steps between keyframes")
    bake_type: EnumProperty(
        name="Bake Type",
        items=(
            ('POSE', "Pose", "Bake as Pose"),
            ('OBJECT', "Object", "Bake as Object")
        ),
        default='POSE'
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        ad = obj.animation_data
        if ad is not None and ad.action is not None:
            return True
        return False

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "steps")
        layout.prop(self, "bake_type")
        layout.label(text="Unselected keyframes will be deleted.", icon='INFO')

    def execute(self, context):
        obj = context.object
        ad = obj.animation_data
        if ad is None or ad.action is None:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}

        original_start_frame = bpy.context.scene.frame_start
        original_end_frame = bpy.context.scene.frame_end

        selected_keyframes = [kp.co.x for fc in ad.action.fcurves for kp in fc.keyframe_points if kp.select_control_point]
        if not selected_keyframes:
            self.report({'WARNING'}, "No keyframes selected")
            return {'CANCELLED'}

        start_frame = min(selected_keyframes)
        end_frame = max(selected_keyframes)

        bpy.context.scene.frame_start = int(start_frame)
        bpy.context.scene.frame_end = int(end_frame)

        if self.bake_type == 'POSE':
            bpy.ops.nla.bake(frame_start=bpy.context.scene.frame_start, frame_end=bpy.context.scene.frame_end, step=self.steps, bake_types={'POSE'})
        elif self.bake_type == 'OBJECT':
            bpy.ops.nla.bake(frame_start=bpy.context.scene.frame_start, frame_end=bpy.context.scene.frame_end, step=self.steps, bake_types={'OBJECT'})

        bpy.context.scene.frame_start = original_start_frame
        bpy.context.scene.frame_end = original_end_frame

        self.report({'INFO'}, f"Keyframes baked successfully with step size {self.steps}")
        return {'FINISHED'}

def is_in_exclude_hidden(obj):
    exclude_hidden_collection = bpy.data.collections.get("Exclude Hidden")
    if exclude_hidden_collection:
        return obj.hide_render or exclude_hidden_collection in obj.users_collection
    return False

class SelectHiddenDisableRenderOperator(bpy.types.Operator):
    bl_idname = "object.select_hidden_disable_render"
    bl_label = "Disable Renders for Hidden Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = []

        for obj in bpy.data.objects:
            if hasattr(obj, "hide_get") and obj.hide_get() and not is_in_exclude_hidden(obj):
                obj.hide_render = True
                selected_objects.append(obj)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_objects:
            obj.select_set(True)

        print(f"Disabled renders for {len(selected_objects)} hidden objects")
        self.report({'INFO'}, f"Successfully disabled renders for hidden objects")
        return {'FINISHED'}

class CreateExcludeHiddenCollectionOperator(bpy.types.Operator):
    bl_idname = "object.create_exclude_hidden_collection"
    bl_label = "Create 'Exclude Hidden' Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        exclude_hidden_collection = bpy.data.collections.get("Exclude Hidden")
        if not exclude_hidden_collection:
            exclude_hidden_collection = bpy.data.collections.new("Exclude Hidden")
            bpy.context.scene.collection.children.link(exclude_hidden_collection)
            print("Exclude Hidden Collection Created")
        else:
            print("Exclude Hidden Collection Already Exists")

        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            if obj.type != 'COLLECTION':
                bpy.data.collections[exclude_hidden_collection.name].objects.link(obj)
        self.report({'INFO'}, f"Successfully selected objects to excluded collection")
        return {'FINISHED'}

def get_collection_names(self, context):
    collections = bpy.data.collections
    return [(coll.name, coll.name, "") for coll in collections]

class CustomNameProperties(bpy.types.PropertyGroup):
    collection_name: bpy.props.StringProperty(name="Collection", default="Cameras")
    existing_collection: bpy.props.EnumProperty(
        name="Existing Collection",
        description="Choose an existing collection",
        items=get_collection_names,
    )
    camera_name: bpy.props.StringProperty(name="Camera", default="Camera")
    shot_name: bpy.props.StringProperty(name="Shot", default="Shot")

class AddCameraButton(bpy.types.Operator):
    bl_idname = "object.add_camera"
    bl_label = "Add Camera"
    bl_description = "Add a camera and increment its name"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        collection_name = props.collection_name or props.existing_collection or "Cameras"
        camera_base_name = props.camera_name or "Camera"

        cameras_collection = bpy.data.collections.get(collection_name)
        if not cameras_collection:
            cameras_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(cameras_collection)

        camera_count = len([obj for obj in cameras_collection.objects if obj.type == 'CAMERA'])

        new_camera = bpy.data.cameras.new(name=f"{camera_base_name} {camera_count + 1}")
        camera_object = bpy.data.objects.new(name=f"{camera_base_name} {camera_count + 1}", object_data=new_camera)

        cameras_collection.objects.link(camera_object)

        area = context.area
        view = area.spaces.active
        reg = view.region_3d
        camera_object.matrix_world = reg.view_matrix.inverted()

        scene.camera = camera_object

        camera_object.select_set(True)
        bpy.context.view_layer.objects.active = camera_object

        return {'FINISHED'}

class AddCameraWithMarkerButton(bpy.types.Operator):
    bl_idname = "object.add_camera_with_marker"
    bl_label = "Add Camera Shots"
    bl_description = "Add camera, increment its name, and add a bind marker in the timeline"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        collection_name = props.collection_name or props.existing_collection or "Camera Shots"
        shot_base_name = props.shot_name or "Shot"

        cameras_collection = bpy.data.collections.get(collection_name)
        if not cameras_collection:
            cameras_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(cameras_collection)

        camera_objs = [obj for obj in cameras_collection.objects if obj.type == 'CAMERA']
        camera_count = len(camera_objs)

        camera_name = f"{shot_base_name} {camera_count + 1}"
        marker_name = camera_name

        new_camera = bpy.data.cameras.new(name=camera_name)
        camera_object = bpy.data.objects.new(name=camera_name, object_data=new_camera)
        cameras_collection.objects.link(camera_object)

        area = context.area
        view = area.spaces.active
        reg = view.region_3d
        camera_object.matrix_world = reg.view_matrix.inverted()

        scene.camera = camera_object

        marker = scene.timeline_markers.new(name=marker_name, frame=scene.frame_current)
        marker.camera = camera_object

        context.view_layer.objects.active = camera_object
        camera_object.select_set(True)

        return {'FINISHED'}

class AddCameraCopyPropertiesButton(bpy.types.Operator):
    bl_idname = "object.add_camera_copy_properties"
    bl_label = "Add Camera Copying Properties"
    bl_description = "Create a new camera copying properties from the active camera, but not keyframes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        collection_name = props.collection_name or props.existing_collection or "Cameras"
        camera_base_name = props.camera_name or "Camera"

        cameras_collection = bpy.data.collections.get(collection_name)
        if not cameras_collection:
            cameras_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(cameras_collection)

        camera_count = len([obj for obj in cameras_collection.objects if obj.type == 'CAMERA'])

        new_camera_data = context.scene.camera.data.copy()
        new_camera_data.animation_data_clear()
        new_camera = bpy.data.objects.new(name=f"{camera_base_name} {camera_count + 1}", object_data=new_camera_data)

        cameras_collection.objects.link(new_camera)

        area = context.area
        view = area.spaces.active
        reg = view.region_3d
        new_camera.matrix_world = reg.view_matrix.inverted()

        scene.camera = new_camera

        new_camera.select_set(True)
        bpy.context.view_layer.objects.active = new_camera

        return {'FINISHED'}

class AddCameraShotCopyPropertiesButton(bpy.types.Operator):
    bl_idname = "object.add_camera_shot_copy_properties"
    bl_label = "Add Camera Shot Copying Properties"
    bl_description = "Create a new camera copying properties from the active camera, but not keyframes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        collection_name = props.collection_name or props.existing_collection or "Camera Shots"
        shot_base_name = props.shot_name or "Shot"

        cameras_collection = bpy.data.collections.get(collection_name)
        if not cameras_collection:
            cameras_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(cameras_collection)

        camera_objs = [obj for obj in cameras_collection.objects if obj.type == 'CAMERA']
        camera_count = len(camera_objs)

        camera_name = f"{shot_base_name} {camera_count + 1}"

        new_camera_data = context.scene.camera.data.copy()
        new_camera_data.animation_data_clear()
        new_camera = bpy.data.objects.new(name=camera_name, object_data=new_camera_data)

        cameras_collection.objects.link(new_camera)

        area = context.area
        view = area.spaces.active
        reg = view.region_3d
        new_camera.matrix_world = reg.view_matrix.inverted()

        scene.camera = new_camera

        context.view_layer.objects.active = new_camera
        new_camera.select_set(True)

        marker_name = camera_name
        marker = scene.timeline_markers.new(name=marker_name, frame=scene.frame_current)
        marker.camera = new_camera

        return {'FINISHED'}

class SCENE_OT_SetPreviewRange(bpy.types.Operator):
    bl_idname = "scene.set_preview_range"
    bl_label = "Set Preview Range"
    bl_options = {'REGISTER', 'UNDO'}

    start_frame: IntProperty()
    end_frame: IntProperty()
    toggle: BoolProperty(name="Toggle Preview Range", default=True)

    def execute(self, context):
        scene = context.scene
        scene.use_preview_range = self.toggle
        if self.toggle:
            scene.frame_preview_start = self.start_frame
            scene.frame_preview_end = self.end_frame
        return {'FINISHED'}

def ShowMessageBox(message="", title="Message Box", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

class ShowPopupMessageOperator(bpy.types.Operator):
    bl_idname = "wm.show_popup_message"
    bl_label = "Show Info Message"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ShowMessageBox("Empty the text field to use existing collection.", "Add Collection", 'INFO')
        return {'FINISHED'}

class OBJECT_OT_ViewportRenderConfirm(bpy.types.Operator):
    bl_idname = "object.viewport_render_confirm"
    bl_label = "Viewport Render Confirm"
    bl_options = {'REGISTER', 'UNDO'}

    preview_render: BoolProperty(
        name="Preview after render",
        description="Preview the rendered animation after rendering",
        default=True
    )

    include_timecode: BoolProperty(
        name="Include Timecode",
        description="Include a timecode in the viewport render",
        default=False
    )

    stamp_background: FloatVectorProperty(
        name="Stamp Background",
        description="Background color of the stamp",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.5)
    )

    stamp_foreground: FloatVectorProperty(
        name="Stamp Foreground",
        description="Foreground color of the stamp",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )

    stamp_font_size: IntProperty(
        name="Stamp Font Size",
        description="Font size of the stamp text",
        default=20,
        min=10,
        max=100
    )

    use_stamp_camera: BoolProperty(
        name="Stamp Camera",
        description="Include camera/shot name in the stamp",
        default=True
    )

    use_stamp_frame: BoolProperty(
        name="Stamp Frame",
        description="Include frame number in the stamp",
        default=True
    )

    use_stamp_time: BoolProperty(
        name="Stamp Time",
        description="Include timecode in the stamp",
        default=True
    )

    use_stamp_filename: BoolProperty(
        name="Stamp Filename",
        description="Include Blender file name in the stamp",
        default=True
    )

    use_stamp_date: BoolProperty(
        name="Stamp Date",
        description="Include render date in the stamp",
        default=True
    )

    use_stamp_frame_range: BoolProperty(
        name="Stamp Frame Range",
        description="Include frame range in the stamp",
        default=True
    )

    use_stamp_scene: BoolProperty(
        name="Stamp Scene",
        description="Include scene name in the stamp",
        default=False
    )

    use_stamp_note: BoolProperty(
        name="Stamp Note",
        description="Include custom note in the stamp",
        default=False
    )

    use_stamp_marker: BoolProperty(
        name="Stamp Marker",
        description="Include marker name in the stamp",
        default=False
    )

    use_stamp_sequencer_strip: BoolProperty(
        name="Stamp Sequencer Strip",
        description="Include sequencer strip name in the stamp",
        default=False
    )

    use_stamp_render_time: BoolProperty(
        name="Stamp Render Time",
        description="Include render time in the stamp",
        default=False
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Are you sure you want to render the viewport?")
        layout.prop(self, "preview_render")
        layout.prop(self, "include_timecode")
        
        if self.include_timecode:
            box = layout.box()
            box.label(text="Stamp Settings")
            box.prop(self, "stamp_background")
            box.prop(self, "stamp_foreground")
            box.prop(self, "stamp_font_size")
            box.prop(self, "use_stamp_camera")
            box.prop(self, "use_stamp_frame")
            box.prop(self, "use_stamp_time")
            box.prop(self, "use_stamp_filename")
            box.prop(self, "use_stamp_date")
            box.prop(self, "use_stamp_frame_range")
            box.prop(self, "use_stamp_scene")
            box.prop(self, "use_stamp_note")
            box.prop(self, "use_stamp_marker")
            box.prop(self, "use_stamp_sequencer_strip")
            box.prop(self, "use_stamp_render_time")

    def execute(self, context):
        scene = context.scene
        if self.include_timecode:
            scene.render.use_stamp = True
            scene.render.stamp_background = self.stamp_background
            scene.render.stamp_foreground = self.stamp_foreground
            scene.render.stamp_font_size = self.stamp_font_size
            scene.render.use_stamp_camera = self.use_stamp_camera
            scene.render.use_stamp_frame = self.use_stamp_frame
            scene.render.use_stamp_time = self.use_stamp_time
            scene.render.use_stamp_filename = self.use_stamp_filename
            scene.render.use_stamp_date = self.use_stamp_date
            scene.render.use_stamp_frame_range = self.use_stamp_frame_range
            scene.render.use_stamp_scene = self.use_stamp_scene
            scene.render.use_stamp_note = self.use_stamp_note
            scene.render.use_stamp_marker = self.use_stamp_marker
            scene.render.use_stamp_sequencer_strip = self.use_stamp_sequencer_strip
            scene.render.use_stamp_render_time = self.use_stamp_render_time

        bpy.ops.render.opengl(animation=True, write_still=True, view_context=True)

        if self.preview_render:
            bpy.ops.render.play_rendered_anim()

        if self.include_timecode:
            scene.render.use_stamp = False

        self.report({'INFO'}, "Viewport render completed.")
        return {'FINISHED'}


def draw_viewport_header(self, context):
    preferences = context.preferences.addons[__name__].preferences
    if preferences.show_viewport_button:
        self.layout.operator("object.viewport_render_confirm", text="Viewport Render", icon='RENDER_STILL')

class OBJECT_OT_OpenOutputDirectory(bpy.types.Operator):
    bl_idname = "object.open_output_directory"
    bl_label = "Open Output Directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        output_path = bpy.context.scene.render.filepath
        directory = os.path.dirname(bpy.path.abspath(output_path))
        if os.path.isdir(directory):
            if sys.platform == 'win32':
                subprocess.Popen(f'explorer "{directory}"')
            elif sys.platform == 'darwin':
                subprocess.Popen(["open", directory])
            else:  # Assume Linux or other
                subprocess.Popen(["xdg-open", directory])
            self.report({'INFO'}, f"Opened directory: {directory}")
        else:
            self.report({'ERROR'}, f"Directory does not exist: {directory}")
        return {'FINISHED'}

class SCENE_OT_JumpToMarker(bpy.types.Operator):
    bl_idname = "scene.jump_to_marker"
    bl_label = "Set as Active Camera"
    bl_options = {'REGISTER', 'UNDO'}

    marker_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        marker = scene.timeline_markers.get(self.marker_name)
        if marker:
            scene.frame_current = marker.frame
            return {'FINISHED'}
        return {'CANCELLED'}

class SCENE_OT_RemoveMarkerAndCamera(bpy.types.Operator):
    bl_idname = "scene.remove_marker_and_camera"
    bl_label = "Remove Marker and Camera"
    bl_options = {'REGISTER', 'UNDO'}

    marker_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        marker = scene.timeline_markers.get(self.marker_name)
        if marker:
            camera = bpy.data.objects.get(marker.camera.name)
            scene.timeline_markers.remove(marker)
            if camera:
                bpy.data.objects.remove(camera)
            return {'FINISHED'}
        return {'CANCELLED'}

class SCENE_OT_RemoveAllShotCameras(bpy.types.Operator):
    bl_idname = "scene.remove_all_shot_cameras"
    bl_label = "Remove All Shots?"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        collection_name = scene.collection_for_status
        selected_collection = bpy.data.collections.get(collection_name)

        if selected_collection:
            markers_to_remove = [marker for marker in scene.timeline_markers if marker.camera and marker.camera.name in selected_collection.objects]

            for marker in markers_to_remove:
                camera = marker.camera
                scene.timeline_markers.remove(marker)
                if camera:
                    bpy.data.objects.remove(camera)

        return {'FINISHED'}

class SCENE_OT_SelectCamera(bpy.types.Operator):
    bl_idname = "scene.select_camera"
    bl_label = "Select Camera"
    bl_options = {'REGISTER', 'UNDO'}

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        camera = bpy.data.objects.get(self.camera_name)
        if camera:
            context.view_layer.objects.active = camera
            camera.select_set(True)
            return {'FINISHED'}
        return {'CANCELLED'}

class VIEW3D_MT_PIE_QuickCamera(Menu):
    bl_label = "Quick Camera"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        pie.operator("object.add_camera", text="Add Camera", icon="CAMERA_DATA")
        pie.operator("object.add_camera_with_marker", text="Add Shot", icon="VIEW_CAMERA")
        pie.operator("object.add_camera_copy_properties", text="Copy Camera", icon="CAMERA_DATA")
        pie.operator("object.add_camera_shot_copy_properties", text="Copy Shot", icon="VIEW_CAMERA")

global_addon_keymaps = []

def get_addon_preferences():
    return bpy.context.preferences.addons[__package__].preferences

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

def unregister_keymap():
    window_manager = bpy.context.window_manager
    if window_manager and window_manager.keyconfigs and window_manager.keyconfigs.addon:
        for keymap, keymap_item in global_addon_keymaps:
            keymap.keymap_items.remove(keymap_item)
    global_addon_keymaps.clear()

def update_keymap(self, context):
    unregister_keymap()
    register_keymap()

def update_collection_for_status(self, context):
    bpy.context.area.tag_redraw()

bpy.types.Scene.collection_for_status = bpy.props.EnumProperty(
    items=get_collection_names,
    name="View Collection",
    update=update_collection_for_status
)



class WM_OT_capture_keymap(bpy.types.Operator):
    bl_idname = "wm.capture_keymap"
    bl_label = "Press a Key"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_prefs = get_addon_preferences()
        addon_prefs.capture_key = True
        wm = context.window_manager
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        addon_prefs = get_addon_preferences()
        if event.type == 'TIMER':
            return {'PASS_THROUGH'}

        if event.value == 'PRESS':
            addon_prefs.key = event.type
            addon_prefs.ctrl = event.ctrl
            addon_prefs.alt = event.alt
            addon_prefs.shift = event.shift
            addon_prefs.capture_key = False

            update_keymap(self, context)
            return {'FINISHED'}

        if event.type == 'ESC':
            addon_prefs.capture_key = False
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

class WM_OT_remove_keymap(bpy.types.Operator):
    bl_idname = "wm.remove_keymap"
    bl_label = "Remove Keymap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        addon_prefs = get_addon_preferences()
        addon_prefs.key = ''
        addon_prefs.ctrl = False
        addon_prefs.alt = False
        addon_prefs.shift = False

        update_keymap(self, context)
        return {'FINISHED'}
    