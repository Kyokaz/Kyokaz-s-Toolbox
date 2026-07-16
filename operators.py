import bpy
import blf
import gpu
import logging
from gpu_extras.batch import batch_for_shader
from bpy.types import Operator, PropertyGroup, Menu, UIList
from bpy.props import IntProperty, BoolProperty, EnumProperty, FloatVectorProperty, StringProperty, PointerProperty, FloatProperty, CollectionProperty
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d
from .utils import ensure_output_directory, generate_output_filename, report_error, get_active_collection, get_addon_preferences
from mathutils import Vector
import os
import subprocess
import sys
import platform
import tempfile
import mathutils
import json
from datetime import datetime
import re

# Global variable to store the draw handler
_camera_info_draw_handler = None
_camera_notes_draw_handler = None
_camera_info_syncing_position = False
_camera_info_sticky_anchor_x = 0.5
_camera_info_sticky_anchor_y = 0.5
_camera_info_normal_position_x = 30.0
_camera_info_normal_position_y = 100.0


def _safe_redraw_viewports(context):
    """Safely redraw all 3D viewports without raising on invalid context state."""
    try:
        if context is None:
            return
        wm = getattr(context, "window_manager", None)
        if wm is None:
            return
        for window in wm.windows:
            screen = getattr(window, "screen", None)
            if screen is None:
                continue
            for area in screen.areas:
                if getattr(area, "type", None) == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass


def get_action_fcurves(action):
    """Get fcurves/channels from action, compatible with Blender 4.x and 5.0+."""
    if action is None:
        return None
    # Blender 5.0+ uses 'channels', older versions use 'fcurves'
    return getattr(action, 'channels', None) or getattr(action, 'fcurves', None)

def get_view_matrix_from_context(context):
    """Retrieve the 3D view matrix from the current context."""
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D' and space.region_3d:
                    return space.region_3d.view_matrix
    return mathutils.Matrix.Identity(4)  # Default to identity if no VIEW_3D found


def project_camera_frame_point(region, rv3d, camera, norm_x, norm_y):
    """Project a point on the camera frame into 2D region coordinates."""
    try:
        frame_local = camera.data.view_frame()
        frame_world = [camera.matrix_world @ v for v in frame_local]
    except Exception:
        return None

    def lerp(v1, v2, t):
        return v1 * (1.0 - t) + v2 * t

    top = lerp(frame_world[0], frame_world[1], norm_x)
    bottom = lerp(frame_world[3], frame_world[2], norm_x)
    point_world = lerp(bottom, top, norm_y)

    return location_3d_to_region_2d(region, rv3d, point_world)


def get_camera_view_region_and_rv3d(context):
    """Return the active camera-view 3D region and rv3d from the current window."""
    if not context or not getattr(context, "window_manager", None):
        return None, None

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                for space in area.spaces:
                    if space.type != 'VIEW_3D':
                        continue
                    rv3d = getattr(space, "region_3d", None)
                    if rv3d and rv3d.view_perspective == 'CAMERA':
                        return region, rv3d
    return None, None


def screen_to_camera_frame_normalized(region, rv3d, camera, screen_x, screen_y):
    """Convert a 2D screen position to normalized camera-frame coordinates."""
    try:
        mouse_region = Vector((screen_x, screen_y))
        ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_region)
        ray_dir = region_2d_to_vector_3d(region, rv3d, mouse_region)

        frame_local = camera.data.view_frame()
        frame_world = [camera.matrix_world @ v for v in frame_local]

        bl_world = frame_world[3]
        br_world = frame_world[2]
        tl_world = frame_world[0]
        plane_normal = (br_world - bl_world).cross(tl_world - bl_world).normalized()

        denom = ray_dir.dot(plane_normal)
        if abs(denom) <= 1e-6:
            return None

        t = (bl_world - ray_origin).dot(plane_normal) / denom
        point_world = ray_origin + ray_dir * t
        point_local = camera.matrix_world.inverted() @ point_world

        bl_local = frame_local[3]
        r = frame_local[2] - frame_local[3]
        u = frame_local[0] - frame_local[3]

        mat = mathutils.Matrix(((r.x, u.x), (r.y, u.y)))
        vec = mathutils.Vector((point_local.x - bl_local.x, point_local.y - bl_local.y))
        if mat.determinant() == 0:
            return None

        sol = mat.inverted() @ vec
        return sol[0], sol[1]
    except Exception:
        return None


def sync_camera_info_overlay_position(preferences, context):
    """Update the sticky anchor separately from the normal screen-space position."""
    global _camera_info_sticky_anchor_x, _camera_info_sticky_anchor_y
    global _camera_info_normal_position_x, _camera_info_normal_position_y

    if preferences is None or context is None:
        return

    scene = getattr(context, "scene", None)
    camera = getattr(scene, "camera", None)
    if camera is None or camera.type != 'CAMERA':
        return

    region, rv3d = get_camera_view_region_and_rv3d(context)
    if not region or not rv3d:
        return

    screen_x = float(preferences.camera_info_position_x)
    screen_y = float(preferences.camera_info_position_y)

    if preferences.camera_info_sticky_overlay:
        normalized = screen_to_camera_frame_normalized(region, rv3d, camera, screen_x, screen_y)
        if normalized is not None:
            _camera_info_sticky_anchor_x, _camera_info_sticky_anchor_y = normalized

    _camera_info_normal_position_x = screen_x
    _camera_info_normal_position_y = screen_y


def sanitize_filename(filename):
    """Sanitize a filename to prevent path traversal attacks and invalid characters."""
    # Remove path separators and dangerous characters
    # Allow alphanumeric, spaces, hyphens, underscores, and periods
    sanitized = re.sub(r'[^\w\s\-.]', '', filename)
    # Remove leading/trailing whitespace and periods
    sanitized = sanitized.strip('. ')
    # Prevent empty filenames
    if not sanitized:
        sanitized = "untitled"
    # Limit length to reasonable size (255 is typical max filename length)
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized

def safe_open_directory(directory_path):
    """Safely open a directory in the system file explorer with path validation."""
    # Normalize and validate the path
    abs_path = os.path.abspath(directory_path)

    # Verify it's actually a directory and exists
    if not os.path.isdir(abs_path):
        return False, f"Directory does not exist: {abs_path}"

    # Security check: ensure the path is real and not a symlink to somewhere dangerous
    try:
        real_path = os.path.realpath(abs_path)
        if not os.path.isdir(real_path):
            return False, f"Invalid directory path: {abs_path}"
    except (OSError, ValueError) as e:
        return False, f"Path validation failed: {str(e)}"

    # Open the directory using platform-specific commands
    try:
        if platform.system() == "Windows":
            os.startfile(real_path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", real_path])
        else:  # Linux and other Unix-like systems
            subprocess.Popen(["xdg-open", real_path])
        return True, f"Opened directory: {real_path}"
    except Exception as e:
        return False, f"Failed to open directory: {str(e)}"

def draw_camera_info_overlay():
    """Draw camera information overlay in the viewport when in camera view."""
    try:
        context = bpy.context

        # Check if we're in camera view
        if not context or not getattr(context, "space_data", None) or context.space_data.type != 'VIEW_3D':
            return

        region_3d = getattr(context.space_data, "region_3d", None)
        if not region_3d or region_3d.view_perspective != 'CAMERA':
            return

        region = getattr(context, "region", None)
        if region is None:
            return

        scene = getattr(context, "scene", None)
        if scene is None:
            return

        camera = getattr(scene, "camera", None)
        if not camera or camera.type != 'CAMERA':
            return

        # Get preferences
        preferences = get_addon_preferences(context)
        if preferences is None:
            return

        # Get camera info
        camera_data = camera.data
        camera_name = camera.name

        # Get frame range info for shots
        props = getattr(scene, "custom_name_props", None)
        shot_info = None

        # Check if camera is in a shot (timeline marker)
        for marker in scene.timeline_markers:
            if marker.camera and marker.camera == camera:
                marker_index = list(scene.timeline_markers).index(marker)
                if marker_index < len(scene.timeline_markers) - 1:
                    next_marker = list(scene.timeline_markers)[marker_index + 1]
                    end_frame = next_marker.frame
                else:
                    end_frame = scene.frame_end

                shot_frames = end_frame - marker.frame
                shot_info = {
                    'name': marker.name,
                    'start': marker.frame,
                    'end': end_frame,
                    'frames': shot_frames
                }
                break

        # Prepare text information based on user preferences
        info_parts = []

        # Camera/Shot name
        if preferences.camera_info_show_name:
            if shot_info:
                info_parts.append(f"Shot: {shot_info['name']}")
            else:
                info_parts.append(f"Camera: {camera_name}")

        # Frame range (only for shots)
        if preferences.camera_info_show_frames and shot_info:
            info_parts.append(f"Frames: {shot_info['start']}-{shot_info['end']} ({shot_info['frames']}f)")

        # Focal Length
        if preferences.camera_info_show_focal:
            if camera_data.type == 'ORTHO':
                info_parts.append(f"Ortho Scale: {camera_data.ortho_scale:.2f}")
            else:
                info_parts.append(f"Focal Length: {camera_data.lens:.1f}mm")

        # Focus Distance (if DoF is enabled)
        if camera_data.dof.use_dof:
            if preferences.camera_info_show_focus:
                info_parts.append(f"Focus: {camera_data.dof.focus_distance:.2f}m")
            if preferences.camera_info_show_fstop:
                info_parts.append(f"F-Stop: f/{camera_data.dof.aperture_fstop:.1f}")

        # Don't draw if no info to display
        if not info_parts:
            return

        # Combine info based on layout preference
        if preferences.camera_info_single_line:
            info_lines = [preferences.camera_info_separator.join(info_parts)]
        else:
            info_lines = info_parts

        # Draw the text
        font_id = 0
        font_color = preferences.camera_info_font_color
        blf.color(font_id, font_color[0], font_color[1], font_color[2], font_color[3])
        blf.size(font_id, preferences.camera_info_font_size)

        rv3d = context.space_data.region_3d

        # Use the sticky camera-frame anchor when sticky mode is enabled, and use the
        # last visible screen-space position when it is disabled.
        if preferences.camera_info_sticky_overlay:
            try:
                coord_2d = project_camera_frame_point(region, rv3d, camera, _camera_info_sticky_anchor_x, _camera_info_sticky_anchor_y)
                if coord_2d is not None:
                    x_offset = coord_2d.x
                    y_start = coord_2d.y
                    _camera_info_normal_position_x = x_offset
                    _camera_info_normal_position_y = y_start
                else:
                    x_offset = float(preferences.camera_info_position_x)
                    y_start = float(preferences.camera_info_position_y)
            except Exception:
                x_offset = float(preferences.camera_info_position_x)
                y_start = float(preferences.camera_info_position_y)
        else:
            x_offset = float(preferences.camera_info_position_x)
            y_start = float(preferences.camera_info_position_y)
            _camera_info_normal_position_x = x_offset
            _camera_info_normal_position_y = y_start

        line_height = preferences.camera_info_font_size + 6

        # Draw background rectangle
        try:
            import gpu
            from gpu_extras.batch import batch_for_shader
        except Exception:
            return

        # Calculate max text width for background
        max_width = 0
        for line in info_lines:
            text_width, text_height = blf.dimensions(font_id, line)
            if text_width > max_width:
                max_width = text_width

        # Draw semi-transparent background
        padding = 10
        bg_x = x_offset - padding
        bg_y = y_start - padding
        bg_width = max_width + padding * 2
        bg_height = len(info_lines) * line_height + padding * 2

        # Enable proper alpha blending
        gpu.state.blend_set('ALPHA')
        try:
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {"pos": [
                    (bg_x, bg_y),
                    (bg_x + bg_width, bg_y),
                    (bg_x + bg_width, bg_y + bg_height),
                    (bg_x, bg_y + bg_height)
                ]},
            )

            shader.bind()
            bg_color = preferences.camera_info_background_color
            shader.uniform_float("color", (bg_color[0], bg_color[1], bg_color[2], bg_color[3]))
            batch.draw(shader)
        finally:
            gpu.state.blend_set('NONE')

        # Draw text lines
        for i, line in enumerate(info_lines):
            y_pos = y_start + (len(info_lines) - 1 - i) * line_height
            blf.position(font_id, x_offset, y_pos, 0)
            blf.draw(font_id, line)
    except Exception:
        return

def register_camera_info_overlay():
    """Register the camera info overlay draw handler."""
    global _camera_info_draw_handler

    if _camera_info_draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_camera_info_draw_handler, 'WINDOW')
        except Exception:
            pass
        _camera_info_draw_handler = None

    _camera_info_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        draw_camera_info_overlay, (), 'WINDOW', 'POST_PIXEL'
    )


def unregister_camera_info_overlay():
    """Unregister the camera info overlay draw handler."""
    global _camera_info_draw_handler

    if _camera_info_draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_camera_info_draw_handler, 'WINDOW')
        except Exception:
            pass
        _camera_info_draw_handler = None


def toggle_camera_info_overlay(enable):
    """Toggle the camera info overlay on or off."""
    try:
        if enable:
            register_camera_info_overlay()
        else:
            unregister_camera_info_overlay()
    except Exception:
        pass

    _safe_redraw_viewports(bpy.context)


def toggle_camera_notes_overlay(enable):
    """Toggle the camera notes overlay on or off."""
    try:
        if enable:
            register_camera_notes_overlay()
        else:
            unregister_camera_notes_overlay()
    except Exception:
        pass

    _safe_redraw_viewports(bpy.context)

def draw_camera_notes_overlay():
    """Draw camera notes overlay in the viewport when in camera view."""
    try:
        context = bpy.context

        # Check if we're in camera view
        if not context or not getattr(context, "space_data", None) or context.space_data.type != 'VIEW_3D':
            return

        region_3d = getattr(context.space_data, "region_3d", None)
        if not region_3d or region_3d.view_perspective != 'CAMERA':
            return

        region = getattr(context, "region", None)
        if region is None:
            return

        scene = getattr(context, "scene", None)
        if scene is None:
            return

        camera = getattr(scene, "camera", None)
        if not camera or camera.type != 'CAMERA':
            return

        # Get notes for this camera
        camera_notes = [note for note in scene.camera_notes if note.camera_name == camera.name and note.enabled]

        if not camera_notes:
            return

        rv3d = context.space_data.region_3d
        font_id = 0

        try:
            import gpu
            from gpu_extras.batch import batch_for_shader
        except Exception:
            return

        # Set up proper GPU state for 2D overlay rendering
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('NONE')

        try:
            # Draw each note (background + text)
            for note in camera_notes:
                coord_2d = project_camera_frame_point(region, rv3d, camera, note.position_x / 1000.0, note.position_y / 1000.0)
                if coord_2d is not None:
                    x_pos, y_pos = coord_2d.x, coord_2d.y
                else:
                    x_pos = note.position_x
                    y_pos = note.position_y

                blf.size(font_id, note.font_size)

                if note.show_background:
                    text_width, text_height = blf.dimensions(font_id, note.text)

                    padding = 8
                    bg_x = x_pos - padding
                    bg_y = y_pos - padding
                    bg_width = text_width + padding * 2
                    bg_height = text_height + padding * 2

                    bg_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                    batch = batch_for_shader(
                        bg_shader, 'TRI_FAN',
                        {"pos": [
                            (bg_x, bg_y),
                            (bg_x + bg_width, bg_y),
                            (bg_x + bg_width, bg_y + bg_height),
                            (bg_x, bg_y + bg_height)
                        ]},
                    )

                    gpu.state.blend_set('ALPHA')
                    bg_shader.bind()
                    bg_color = note.background_color
                    bg_shader.uniform_float("color", (bg_color[0], bg_color[1], bg_color[2], bg_color[3]))
                    batch.draw(bg_shader)
                    gpu.shader.unbind()

                blf.color(font_id, note.font_color[0], note.font_color[1], note.font_color[2], note.font_color[3])
                blf.position(font_id, x_pos, y_pos, 0)
                blf.draw(font_id, note.text)
        finally:
            gpu.state.blend_set('NONE')
            gpu.state.depth_test_set('LESS_EQUAL')
    except Exception:
        return

def register_camera_notes_overlay():
    """Register the camera notes overlay draw handler."""
    global _camera_notes_draw_handler

    if _camera_notes_draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_camera_notes_draw_handler, 'WINDOW')
        except Exception:
            pass
        _camera_notes_draw_handler = None

    _camera_notes_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        draw_camera_notes_overlay, (), 'WINDOW', 'POST_PIXEL'
    )


def unregister_camera_notes_overlay():
    """Unregister the camera notes overlay draw handler."""
    global _camera_notes_draw_handler

    if _camera_notes_draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_camera_notes_draw_handler, 'WINDOW')
        except Exception:
            pass
        _camera_notes_draw_handler = None

class FavoriteCameraItem(PropertyGroup):
    camera: PointerProperty(type=bpy.types.Object)

class CameraNoteItem(PropertyGroup):
    """Property group for individual camera/shot notes"""
    text: StringProperty(
        name="Note Text",
        description="Text content of the note",
        default="Note"
    )
    camera_name: StringProperty(
        name="Camera Name",
        description="Name of the camera this note belongs to",
        default=""
    )
    position_x: IntProperty(
        name="Position X",
        description="Horizontal position in pixels from left edge of camera view",
        default=100,
        soft_min=-4000,
        soft_max=4000
    )
    position_y: IntProperty(
        name="Position Y",
        description="Vertical position in pixels from bottom edge of camera view",
        default=100,
        soft_min=-4000,
        soft_max=4000
    )
    font_size: IntProperty(
        name="Font Size",
        description="Font size for the note",
        default=20,
        min=8,
        max=100
    )
    font_color: FloatVectorProperty(
        name="Font Color",
        description="Color and opacity of the text",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 0.0, 1.0)  # Yellow by default
    )
    background_color: FloatVectorProperty(
        name="Background Color",
        description="Color and opacity of the background",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.7)
    )
    show_background: BoolProperty(
        name="Show Background",
        description="Show background behind the note",
        default=True
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Show this note in viewport",
        default=True
    )

class OBJECT_OT_BaseOperator(Operator):
    bl_options = {'REGISTER', 'UNDO'}
    bl_label = "Base Operator"

    def apply_interpolation(self, context, interpolation_type, selected_only=False):
        changed_count = 0
        for obj in context.selected_objects:
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_action_fcurves(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        for keyframe in fcurve.keyframe_points:
                            if not selected_only or keyframe.select_control_point:
                                if keyframe.interpolation != interpolation_type:
                                    keyframe.interpolation = interpolation_type
                                    changed_count += 1
        
        self.report({'INFO'}, f"Applied {interpolation_type} interpolation to {changed_count} keyframes")
        context.area.tag_redraw()
        return {'FINISHED'}

class OBJECT_OT_toggle_default_interpolation(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_default_interpolation"
    bl_label = "Toggle Default"

    def execute(self, context):
        preferences = context.preferences.edit
        current_type = preferences.keyframe_new_interpolation_type
        new_type = {'CONSTANT': 'LINEAR', 'LINEAR': 'BEZIER'}.get(current_type, 'CONSTANT')
        preferences.keyframe_new_interpolation_type = new_type
        self.report({'INFO'}, f"Default interpolation set to {new_type.capitalize()}")
        return {'FINISHED'}

class OBJECT_OT_toggle_interpolation_selected(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_interpolation_selected"
    bl_label = "Selected Keyframe"

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_action_fcurves(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        for keyframe in fcurve.keyframe_points:
                            if keyframe.select_control_point:
                                keyframe.interpolation = 'CONSTANT' if keyframe.interpolation != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

class OBJECT_OT_toggle_interpolation_all(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_interpolation_all"
    bl_label = "Selected Objects"

    @classmethod
    def poll(cls, context):
        return any(obj.animation_data and obj.animation_data.action for obj in context.selected_objects)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.animation_data and obj.animation_data.action:
                fcurves = get_action_fcurves(obj.animation_data.action)
                if fcurves:
                    for fcurve in fcurves:
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'CONSTANT' if keyframe.interpolation != 'CONSTANT' else 'BEZIER'
        return {'FINISHED'}

class OBJECT_OT_apply_all_constant(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_all_constant"
    bl_label = "Constant"

    @classmethod
    def poll(cls, context):
        return any(obj.animation_data and obj.animation_data.action for obj in context.selected_objects)

    def execute(self, context):
        return self.apply_interpolation(context, 'CONSTANT')

class OBJECT_OT_apply_all_bezier(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_all_bezier"
    bl_label = "Bezier"

    @classmethod
    def poll(cls, context):
        return any(obj.animation_data and obj.animation_data.action for obj in context.selected_objects)

    def execute(self, context):
        return self.apply_interpolation(context, 'BEZIER')

class OBJECT_OT_apply_all_linear(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_all_linear"
    bl_label = "Linear"

    @classmethod
    def poll(cls, context):
        return any(obj.animation_data and obj.animation_data.action for obj in context.selected_objects)

    def execute(self, context):
        return self.apply_interpolation(context, 'LINEAR')

class OBJECT_OT_apply_selected_constant(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_selected_constant"
    bl_label = "Constant"

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def execute(self, context):
        return self.apply_interpolation(context, 'CONSTANT', selected_only=True)

class OBJECT_OT_apply_selected_bezier(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_selected_bezier"
    bl_label = "Bezier"

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def execute(self, context):
        return self.apply_interpolation(context, 'BEZIER', selected_only=True)

class OBJECT_OT_apply_selected_linear(OBJECT_OT_BaseOperator):
    bl_idname = "object.apply_selected_linear"
    bl_label = "Linear"

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def execute(self, context):
        return self.apply_interpolation(context, 'LINEAR', selected_only=True)

class OBJECT_OT_toggle_auto_keying(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_auto_keying"
    bl_label = "Auto Keying"

    def execute(self, context):
        context.scene.tool_settings.use_keyframe_insert_auto = not context.scene.tool_settings.use_keyframe_insert_auto
        return {'FINISHED'}

class OBJECT_OT_add_keyframes_operator(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_keyframes_operator"
    bl_label = "Add Per Steps"

    steps: IntProperty(name="Steps", default=2, min=1, description="Number of steps between keyframes")

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action

        if not action:
            self.report({'WARNING'}, "No action found")
            return {'CANCELLED'}

        fcurves = get_action_fcurves(action)
        if not fcurves:
            self.report({'WARNING'}, "No animation channels found")
            return {'CANCELLED'}

        for fc in fcurves:
            keyframes = [kp for kp in fc.keyframe_points if kp.select_control_point]
            for i in range(len(keyframes) - 1):
                start_kp, end_kp = keyframes[i], keyframes[i + 1]
                start_frame, end_frame = int(start_kp.co.x), int(end_kp.co.x)
                start_value, end_value = start_kp.co.y, end_kp.co.y

                for frame in range(start_frame + self.steps, end_frame, self.steps):
                    t = (frame - start_frame) / (end_frame - start_frame)
                    interpolated_value = (1 - t) * start_value + t * end_value
                    fc.keyframe_points.insert(frame, interpolated_value)

        self.report({'INFO'}, f"Keyframes added successfully with step size {self.steps}")
        return {'FINISHED'}

class OBJECT_OT_delete_keyframes_per_steps(OBJECT_OT_BaseOperator):
    bl_idname = "object.delete_keyframes_per_steps"
    bl_label = "Delete Per Steps"

    steps: IntProperty(name="Steps", default=1, min=1, description="Number of steps between keyframes")

    @classmethod
    def poll(cls, context):
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        if not action:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}

        # Blender 5.0 changed fcurves to channels
        fcurves = get_action_fcurves(action)
        if not fcurves:
            self.report({'WARNING'}, "No animation channels found")
            return {'CANCELLED'}

        for fc in fcurves:
            keyframes = [kp for kp in fc.keyframe_points if kp.select_control_point]
            to_remove = [keyframes[i] for i in range(0, len(keyframes), self.steps)]
            for kp in reversed(to_remove):
                fc.keyframe_points.remove(kp)

        self.report({'INFO'}, f"Keyframes deleted successfully with step size {self.steps}")
        return {'FINISHED'}

class OBJECT_OT_bake_keyframes_per_steps(OBJECT_OT_BaseOperator):
    bl_idname = "object.bake_keyframes_per_steps"
    bl_label = "Bake Per Steps"

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
        if not (context.active_object and context.active_object.animation_data and context.active_object.animation_data.action):
            return False
        fcurves = get_action_fcurves(context.active_object.animation_data.action)
        return fcurves and any(any(kp.select_control_point for kp in fc.keyframe_points) for fc in fcurves)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "steps")
        layout.prop(self, "bake_type")
        layout.label(text="Unselected keyframes will be deleted.", icon='INFO')

    def execute(self, context):
        obj = context.object
        action = obj.animation_data.action
        if not action:
            self.report({'WARNING'}, "No animation data found")
            return {'CANCELLED'}

        original_start_frame = context.scene.frame_start
        original_end_frame = context.scene.frame_end

        fcurves = get_action_fcurves(action)
        if not fcurves:
            self.report({'WARNING'}, "No animation channels found")
            return {'CANCELLED'}

        selected_keyframes = [kp.co.x for fc in fcurves for kp in fc.keyframe_points if kp.select_control_point]
        if not selected_keyframes:
            self.report({'WARNING'}, "No keyframes selected")
            return {'CANCELLED'}

        start_frame = int(min(selected_keyframes))
        end_frame = int(max(selected_keyframes))

        context.scene.frame_start = start_frame
        context.scene.frame_end = end_frame

        bpy.ops.nla.bake(frame_start=start_frame, frame_end=end_frame, step=self.steps, bake_types={self.bake_type})

        context.scene.frame_start = original_start_frame
        context.scene.frame_end = original_end_frame

        self.report({'INFO'}, f"Keyframes baked successfully with step size {self.steps}")
        return {'FINISHED'}

class SCENE_OT_set_frame(bpy.types.Operator):
    bl_idname = "scene.set_frame"
    bl_label = "Set Frame"
    bl_description = "Set the current frame as start or end frame"

    frame_type: bpy.props.EnumProperty(
        items=[
            ('START', "Start", "Set as start frame"),
            ('END', "End", "Set as end frame"),
        ],
        name="Frame Type",
        description="Whether to set the start or end frame",
    )

    def execute(self, context):
        if self.frame_type == 'START':
            context.scene.frame_start = context.scene.frame_current
            self.report({'INFO'}, f"Start frame set to {context.scene.frame_start}")
        else:
            context.scene.frame_end = context.scene.frame_current
            self.report({'INFO'}, f"End frame set to {context.scene.frame_end}")
        return {'FINISHED'}

def is_in_exclude_hidden(obj):
    exclude_hidden_collection = bpy.data.collections.get("Exclude Hidden")
    return obj.hide_render or (exclude_hidden_collection and exclude_hidden_collection in obj.users_collection)

class RenderToolsSettings(PropertyGroup):
    output_directory: StringProperty(
        name="Output Directory",
        description="Directory used for playblast and snapshot output",
        subtype='DIR_PATH',
        default=""
    )

    affect_children: BoolProperty(
        name="Affect Children",
        default=False,
        description="Apply the action to child objects of hidden objects"
    )
    
    exception_collection: StringProperty(
        name="Exception Collection",
        default="Render_Exceptions",
        description="Objects in this collection will not be affected by the disable render operation"
    )

class SelectHiddenDisableRenderOperator(Operator):
    bl_idname = "object.select_hidden_disable_render"
    bl_label = "Disable Renders for Hidden Objects"

    def execute(self, context):
        exception_collection = bpy.data.collections.get("Exclude Hidden")
        selected_objects = [obj for obj in context.view_layer.objects if obj.hide_get() and 
                            (not exception_collection or obj.name not in exception_collection.objects)]
        
        for obj in selected_objects:
            obj.hide_render = True

        bpy.ops.object.select_all(action='DESELECT')

        for obj in selected_objects:
            obj.select_set(True)

        self.report({'INFO'}, f"Successfully disabled renders for {len(selected_objects)} hidden objects")
        return {'FINISHED'}

class OBJECT_OT_DisableRenderForHidden(Operator):
    bl_idname = "object.disable_render_for_hidden"
    bl_label = "Disable Render for Hidden Objects"
    bl_description = "Disable render for all hidden objects, recursively checking collections"

    def process_collection(self, collection, exception_collection, settings, stats):
        """Recursively process a collection and its objects"""
        # Process all objects in this collection
        for obj in collection.objects:
            if obj.hide_get() and (not exception_collection or obj.name not in exception_collection.objects):
                obj.hide_render = True
                stats['affected_count'] += 1
                
                # Process children if enabled
                if settings.affect_children:
                    for child in obj.children_recursive:
                        if not exception_collection or child.name not in exception_collection.objects:
                            child.hide_render = True
                            stats['affected_count'] += 1

        # Recursively process child collections
        for child_collection in collection.children:
            self.process_collection(child_collection, exception_collection, settings, stats)

    def execute(self, context):
        settings = context.scene.render_tools_settings
        exception_collection = bpy.data.collections.get(settings.exception_collection)
        
        stats = {'affected_count': 0}
        
        # Start with the master collection and process recursively
        self.process_collection(context.scene.collection, exception_collection, settings, stats)

        self.report({'INFO'}, f"Disabled render for {stats['affected_count']} hidden objects")
        return {'FINISHED'}

class OBJECT_OT_CreateExceptionCollection(Operator):
    bl_idname = "object.create_exception_collection"
    bl_label = "Create Exception Collection"
    bl_description = "Create a new collection for render exceptions"

    def execute(self, context):
        settings = context.scene.render_tools_settings
        
        if not settings.exception_collection:
            self.report({'ERROR'}, "Exception collection name cannot be empty")
            return {'CANCELLED'}
            
        if not bpy.data.collections.get(settings.exception_collection):
            new_collection = bpy.data.collections.new(settings.exception_collection)
            context.scene.collection.children.link(new_collection)
            self.report({'INFO'}, f"Created exception collection: {settings.exception_collection}")
        else:
            self.report({'INFO'}, f"Exception collection already exists: {settings.exception_collection}")
        return {'FINISHED'}

class OBJECT_OT_AddSelectedToExceptions(Operator):
    bl_idname = "object.add_selected_to_exceptions"
    bl_label = "Add Selected to Exceptions"
    bl_description = "Add selected objects and their children to the exception collection"

    def process_object_hierarchy(self, obj, exception_collection, stats):
        """Process an object and optionally its child hierarchy"""
        if obj.name not in exception_collection.objects:
            try:
                exception_collection.objects.link(obj)
                stats['added_count'] += 1
            except RuntimeError:
                # Object might already be in the collection
                pass

        # Process child objects
        for child in obj.children_recursive:
            if child.name not in exception_collection.objects:
                try:
                    exception_collection.objects.link(child)
                    stats['added_count'] += 1
                except RuntimeError:
                    pass

    def execute(self, context):
        settings = context.scene.render_tools_settings
        exception_collection = bpy.data.collections.get(settings.exception_collection)
        
        if not exception_collection:
            exception_collection = bpy.data.collections.new(settings.exception_collection)
            context.scene.collection.children.link(exception_collection)

        stats = {'added_count': 0}

        # Process selected objects and their hierarchies
        for obj in context.selected_objects:
            # If the selected object is a collection
            if obj.instance_type == 'COLLECTION' and obj.instance_collection:
                for collection_obj in obj.instance_collection.all_objects:
                    self.process_object_hierarchy(collection_obj, exception_collection, stats)
            else:
                self.process_object_hierarchy(obj, exception_collection, stats)

        self.report({'INFO'}, f"Added {stats['added_count']} objects to the exception collection")
        return {'FINISHED'}

class CreateExcludeHiddenCollectionOperator(OBJECT_OT_BaseOperator):
    bl_idname = "object.create_exclude_hidden_collection"
    bl_label = "Create 'Exclude Hidden' Collection"

    def execute(self, context):
        exclude_hidden_collection = bpy.data.collections.get("Exclude Hidden")
        if not exclude_hidden_collection:
            exclude_hidden_collection = bpy.data.collections.new("Exclude Hidden")
            context.scene.collection.children.link(exclude_hidden_collection)

        for obj in context.selected_objects:
            if obj.type != 'COLLECTION':
                exclude_hidden_collection.objects.link(obj)
        
        self.report({'INFO'}, f"Successfully added selected objects to excluded collection")
        return {'FINISHED'}

#def get_collection_names(self, context):
#    return [(coll.name, coll.name, "") for coll in bpy.data.collections]

def update_collection_index(self, context):
    context.area.tag_redraw()

class CustomNameProperties(PropertyGroup):
    collection_name: StringProperty(name="New Collection", default="Cameras")
    camera_name: StringProperty(name="Camera", default="Camera")
    shot_name: StringProperty(name="Shot", default="Shot")
    
    favorite_cameras: CollectionProperty(
        type=FavoriteCameraItem,
        name="Favorite Cameras",
        description="List of favorite cameras"
    )
    
    camera_collection: PointerProperty(
        name="Camera Collection",
        type=bpy.types.Collection,
        description="Select a collection for cameras"
    )

    shot_list_collection: PointerProperty(
        name="Shot List Collection",
        type=bpy.types.Collection,
        description="Select a collection for the shot list"
    )

    camera_list_collection: PointerProperty(
        name="Camera List Collection",
        type=bpy.types.Collection,
        description="Select a collection for the camera list"
    )

    def get_active_collection(self, context):
        return self.camera_collection

    def get_shot_list_collection(self, context):
        return self.shot_list_collection

    def get_camera_list_collection(self, context):
        return self.camera_list_collection

    def set_active_collections(self, collection):
        self.camera_collection = collection
        self.shot_list_collection = collection
        self.camera_list_collection = collection


class OBJECT_OT_ApplyPassepartoutToAllCameras(Operator):
    bl_idname = "object.apply_passepartout_to_all_cameras"
    bl_label = "Apply to All Cameras"
    bl_description = "Apply the default passepartout value to all cameras in the scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'ERROR'}, "Addon preferences are not available")
            return {'CANCELLED'}

        passepartout_value = preferences.default_passepartout
        
        # Count cameras that will be affected
        camera_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                obj.data.passepartout_alpha = passepartout_value
                camera_count += 1
        
        if camera_count > 0:
            self.report({'INFO'}, f"Applied passepartout value {passepartout_value:.2f} to {camera_count} camera(s)")
        else:
            self.report({'WARNING'}, "No cameras found in the scene")
        
        return {'FINISHED'}


class OBJECT_OT_ApplyClippingToAllCameras(Operator):
    bl_idname = "object.apply_clipping_to_all_cameras"
    bl_label = "Apply to All Cameras"
    bl_description = "Apply the default clipping values to all cameras in the scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'ERROR'}, "Addon preferences are not available")
            return {'CANCELLED'}

        clip_start = preferences.default_clip_start
        clip_end = preferences.default_clip_end
        
        # Count cameras that will be affected
        camera_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA':
                obj.data.clip_start = clip_start
                obj.data.clip_end = clip_end
                camera_count += 1
        
        if camera_count > 0:
            self.report({'INFO'}, f"Applied clipping (Start: {clip_start}, End: {clip_end}) to {camera_count} camera(s)")
        else:
            self.report({'WARNING'}, "No cameras found in the scene")
        
        return {'FINISHED'}


class OBJECT_OT_TogglePanelVisibility(Operator):
    bl_idname = "object.toggle_panel_visibility"
    bl_label = "Toggle Panel Visibility"
    bl_description = "Toggle visibility of a specific panel"
    bl_options = {'REGISTER', 'UNDO'}
    
    panel_name: StringProperty()
    
    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'ERROR'}, "Failed to toggle panel: addon preferences not available")
            return {'CANCELLED'}

        if self.panel_name == "render_tools":
            preferences.show_render_tools_n_panel = not preferences.show_render_tools_n_panel
        elif self.panel_name == "shot_list":
            preferences.show_shot_list_n_panel = not preferences.show_shot_list_n_panel
        elif self.panel_name == "camera_list":
            preferences.show_camera_list_n_panel = not preferences.show_camera_list_n_panel
        elif self.panel_name == "camera_info_overlay":
            preferences.show_camera_info_overlay_n_panel = not preferences.show_camera_info_overlay_n_panel

        # Force UI refresh
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'PROPERTIES'}:
                area.tag_redraw()
        
        return {'FINISHED'}


class OBJECT_OT_CreateCameraCollection(Operator):
    bl_idname = "object.create_camera_collection"
    bl_label = "Create Camera Collection"
    bl_description = "Create a new collection for cameras"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.custom_name_props
        new_collection = bpy.data.collections.new(props.collection_name)
        context.scene.collection.children.link(new_collection)
        
        # Set the new collection as the active one
        props.camera_collection = new_collection
        props.shot_list_collection = new_collection
        props.camera_list_collection = new_collection
        
        # Force UI update
        for area in context.screen.areas:
            area.tag_redraw()
        
        self.report({'INFO'}, f"Created new camera collection: {new_collection.name}")
        return {'FINISHED'}
    
class AddCameraButton(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_camera"
    bl_label = "Add Camera"
    bl_description = "Add a camera and increment its name"

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        active_collection = get_active_collection(context, self)
        if not active_collection:
            active_collection = bpy.data.collections.new("Cameras")
            context.scene.collection.children.link(active_collection)
            self.report({'INFO'}, "Created new 'Cameras' collection")

        camera_base_name = props.camera_name or "Camera"
        camera_count = sum(1 for obj in active_collection.objects if obj.type == 'CAMERA')

        preferences = get_addon_preferences(context)

        new_camera_data = bpy.data.cameras.new(name=f"{camera_base_name} {camera_count + 1}")
        new_camera = bpy.data.objects.new(name=f"{camera_base_name} {camera_count + 1}", object_data=new_camera_data)

        if preferences is not None:
            new_camera_data.type = preferences.default_type
            new_camera_data.passepartout_alpha = preferences.default_passepartout
            new_camera_data.clip_start = preferences.default_clip_start
            new_camera_data.clip_end = preferences.default_clip_end
            if new_camera_data.type == 'ORTHO':
                new_camera_data.ortho_scale = preferences.default_ortho_scale
            else:
                new_camera_data.lens = preferences.default_lens

        # Get the view matrix and apply it to the camera
        view_matrix = get_view_matrix_from_context(context)
        new_camera.matrix_world = view_matrix.inverted()

        active_collection.objects.link(new_camera)
        scene.camera = new_camera
        new_camera.select_set(True)
        context.view_layer.objects.active = new_camera
        props.set_active_collections(active_collection)

        return {'FINISHED'}

class AddCameraWithMarkerButton(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_camera_with_marker"
    bl_label = "Add Camera Shots"
    bl_description = "Add camera, increment its name, and add a bind marker in the timeline"

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props
        active_collection = get_active_collection(context, self)
        if not active_collection:
            active_collection = bpy.data.collections.new("Cameras")
            context.scene.collection.children.link(active_collection)
            self.report({'INFO'}, "Created new 'Cameras' collection")

        shot_base_name = props.shot_name or "Shot"
        # Count only cameras that have associated markers (shots), not all cameras
        camera_objs = [obj for obj in active_collection.objects if obj.type == 'CAMERA']
        shot_count = sum(1 for obj in camera_objs
                        if any(marker.camera == obj for marker in scene.timeline_markers))

        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'ERROR'}, "Addon preferences are not available")
            return {'CANCELLED'}

        camera_name = f"{shot_base_name} {shot_count + 1}"
        marker_name = camera_name
        new_camera = bpy.data.cameras.new(name=camera_name)
        camera_object = bpy.data.objects.new(name=camera_name, object_data=new_camera)

        new_camera.type = preferences.default_type
        new_camera.passepartout_alpha = preferences.default_passepartout
        new_camera.clip_start = preferences.default_clip_start
        new_camera.clip_end = preferences.default_clip_end
        if new_camera.type == 'ORTHO':
            new_camera.ortho_scale = preferences.default_ortho_scale
        else:
            new_camera.lens = preferences.default_lens

        # Get the view matrix and apply it to the camera
        view_matrix = get_view_matrix_from_context(context)
        camera_object.matrix_world = view_matrix.inverted()

        active_collection.objects.link(camera_object)
        marker = scene.timeline_markers.new(name=marker_name, frame=scene.frame_current)
        marker.camera = camera_object

        scene.camera = camera_object
        camera_object.select_set(True)
        context.view_layer.objects.active = camera_object
        props.set_active_collections(active_collection)

        return {'FINISHED'}

class AddCameraCopyPropertiesButton(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_camera_copy_properties"
    bl_label = "Add Camera Copying Properties"
    bl_description = "Create a new camera copying properties from the active camera, but not keyframes"

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props

        active_collection = get_active_collection(context, self)
        if not active_collection:
            active_collection = bpy.data.collections.new("Cameras")
            context.scene.collection.children.link(active_collection)
            self.report({'INFO'}, "Created new 'Cameras' collection")

        # Validate that there's an active camera
        if not context.scene.camera or context.scene.camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera in scene")
            return {'CANCELLED'}

        camera_base_name = props.camera_name or "Camera"
        camera_count = sum(1 for obj in active_collection.objects if obj.type == 'CAMERA')

        new_camera_data = context.scene.camera.data.copy()
        new_camera_data.animation_data_clear()

        new_camera = bpy.data.objects.new(name=f"{camera_base_name} {camera_count + 1}", object_data=new_camera_data)

        # Get the view matrix and apply it to the camera
        view_matrix = get_view_matrix_from_context(context)
        new_camera.matrix_world = view_matrix.inverted()

        active_collection.objects.link(new_camera)
        scene.camera = new_camera
        new_camera.select_set(True)
        context.view_layer.objects.active = new_camera
        props.set_active_collections(active_collection)

        return {'FINISHED'}

class AddCameraShotCopyPropertiesButton(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_camera_shot_copy_properties"
    bl_label = "Add Camera Shot Copying Properties"
    bl_description = "Create a new camera copying properties from the active camera, but not keyframes"

    def execute(self, context):
        scene = context.scene
        props = scene.custom_name_props

        active_collection = get_active_collection(context, self)
        if not active_collection:
            active_collection = bpy.data.collections.new("Cameras")
            context.scene.collection.children.link(active_collection)
            self.report({'INFO'}, "Created new 'Cameras' collection")

        # Validate that there's an active camera
        if not context.scene.camera or context.scene.camera.type != 'CAMERA':
            self.report({'ERROR'}, "No active camera in scene")
            return {'CANCELLED'}

        shot_base_name = props.shot_name or "Shot"
        # Count only cameras that have associated markers (shots), not all cameras
        camera_objs = [obj for obj in active_collection.objects if obj.type == 'CAMERA']
        shot_count = sum(1 for obj in camera_objs
                        if any(marker.camera == obj for marker in scene.timeline_markers))

        camera_name = f"{shot_base_name} {shot_count + 1}"
        new_camera_data = context.scene.camera.data.copy()
        new_camera_data.animation_data_clear()

        new_camera = bpy.data.objects.new(name=camera_name, object_data=new_camera_data)

        # Get the view matrix and apply it to the camera
        view_matrix = get_view_matrix_from_context(context)
        new_camera.matrix_world = view_matrix.inverted()

        active_collection.objects.link(new_camera)
        scene.camera = new_camera
        new_camera.select_set(True)
        context.view_layer.objects.active = new_camera
        props.set_active_collections(active_collection)

        marker = scene.timeline_markers.new(name=camera_name, frame=scene.frame_current)
        marker.camera = new_camera

        return {'FINISHED'}

class SCENE_OT_SetPreviewRange(OBJECT_OT_BaseOperator):
    bl_idname = "scene.set_preview_range"
    bl_label = "Set Preview Range"

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

def show_message_box(message="", title="Message Box", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

class ShowPopupMessageOperator(OBJECT_OT_BaseOperator):
    bl_idname = "wm.show_popup_message"
    bl_label = "Show Info Message"

    def execute(self, context):
        show_message_box("Empty the text field to use existing collection.", "Add Collection", 'INFO')
        return {'FINISHED'}

class OBJECT_OT_PlayblastConfirm(OBJECT_OT_BaseOperator):
    bl_idname = "object.playblast_confirm"
    bl_label = "Playblast"
    bl_description = "Create a playblast (viewport animation render) of the current timeline"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        settings = scene.viewport_render_settings

        # Ensure output directory exists
        try:
            output_dir = ensure_output_directory(settings.output_directory)
        except Exception as e:
            report_error(self, f"Failed to create output directory: {e}")
            return {'CANCELLED'}

        # Backup original render settings
        original_filepath = scene.render.filepath
        original_use_stamp = scene.render.use_stamp
        original_stamp_settings = {}
        
        if settings.include_timecode:
            # Backup stamp settings
            for prop in ['stamp_background', 'stamp_foreground', 'stamp_font_size']:
                if hasattr(scene.render, prop):
                    original_stamp_settings[prop] = getattr(scene.render, prop)
            
            # Apply stamp settings
            scene.render.use_stamp = True
            scene.render.stamp_background = settings.stamp_background
            scene.render.stamp_foreground = settings.stamp_foreground
            scene.render.stamp_font_size = settings.stamp_font_size
            
            # Apply stamp options
            for prop in dir(settings):
                if prop.startswith('use_stamp_'):
                    if hasattr(scene.render, prop):
                        setattr(scene.render, prop, getattr(settings, prop))

        # Generate filename
        playblast_filepath = generate_output_filename(output_dir, settings.filename_suffix)
        scene.render.filepath = playblast_filepath

        try:
            # Perform the playblast (viewport render)
            bpy.ops.render.opengl(animation=True, write_still=True, view_context=True)

            # Optionally preview the render (before restoring settings)
            if settings.preview_render:
                bpy.ops.render.play_rendered_anim()
        finally:
            # Always restore original settings
            scene.render.filepath = original_filepath
            scene.render.use_stamp = original_use_stamp
            for prop, value in original_stamp_settings.items():
                if hasattr(scene.render, prop):
                    setattr(scene.render, prop, value)

        self.report({'INFO'}, f"Playblast saved to: {playblast_filepath}")
        return {'FINISHED'}

class OBJECT_OT_PlayblastSettings(OBJECT_OT_BaseOperator):
    bl_idname = "object.playblast_settings"
    bl_label = "Playblast Settings"
    bl_description = "Configure playblast output settings"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.viewport_render_settings

        layout.prop(settings, "output_directory")
        layout.operator("object.open_playblast_directory", text="Open Output Directory", icon='FILE_FOLDER')
        layout.separator()
        layout.prop(settings, "preview_render")
        layout.prop(settings, "filename_suffix")
        layout.separator()
        layout.prop(settings, "include_timecode")
        
        if settings.include_timecode:
            box = layout.box()
            box.label(text="Timecode Settings", icon='TIME')
            box.prop(settings, "stamp_background", text="Background")
            box.prop(settings, "stamp_foreground", text="Foreground")
            box.prop(settings, "stamp_font_size", text="Font Size")
            
            box.separator()
            col = box.column(align=True)
            col.label(text="Display Options:")
            col.prop(settings, "use_stamp_camera")
            col.prop(settings, "use_stamp_frame")
            col.prop(settings, "use_stamp_time")
            col.prop(settings, "use_stamp_filename")
            col.prop(settings, "use_stamp_date")
            col.prop(settings, "use_stamp_frame_range")
            col.prop(settings, "use_stamp_scene")
            col.prop(settings, "use_stamp_note")
            col.prop(settings, "use_stamp_marker")
            col.prop(settings, "use_stamp_render_time")

    def execute(self, context):
        self.report({'INFO'}, "Playblast settings updated.")
        return {'FINISHED'}

class OBJECT_OT_SnapshotRender(OBJECT_OT_BaseOperator):
    bl_idname = "object.snapshot_render"
    bl_label = "Snapshot"
    bl_description = "Capture a single frame viewport snapshot"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        settings = scene.snapshot_settings

        # Ensure output directory exists
        try:
            output_dir = ensure_output_directory(settings.output_directory) if settings.output_directory else tempfile.gettempdir()
        except Exception as e:
            report_error(self, f"Failed to create output directory: {e}")
            return {'CANCELLED'}

        # Backup original render settings
        original_file_format = scene.render.image_settings.file_format
        original_filepath = scene.render.filepath

        # Generate the output filename with sanitization
        blend_name = bpy.path.basename(bpy.data.filepath)
        blend_name = os.path.splitext(blend_name)[0] if blend_name else "untitled"
        blend_name = sanitize_filename(blend_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = sanitize_filename(settings.filename_suffix)
        filename = f"{blend_name}_{suffix}_{timestamp}.png"
        file_path = os.path.join(output_dir, filename)

        try:
            # Update render settings
            scene.render.image_settings.file_format = 'PNG'
            scene.render.filepath = file_path

            # Perform the snapshot render
            bpy.ops.render.opengl(write_still=True, view_context=True)

            # Verify file was created
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Snapshot file was not created: {file_path}")

        except Exception as e:
            self.report({'ERROR'}, f"Failed to create snapshot: {e}")
            return {'CANCELLED'}
        finally:
            # Always restore original settings
            scene.render.image_settings.file_format = original_file_format
            scene.render.filepath = original_filepath

        # Optionally preview the rendered snapshot
        if settings.preview_render:
            try:
                bpy.ops.render.view_show('INVOKE_DEFAULT')
            except Exception:
                pass  # Preview may fail if no image editor available

        self.report({'INFO'}, f"Snapshot saved to: {file_path}")
        return {'FINISHED'}
    
class OBJECT_OT_SnapshotRenderSettings(OBJECT_OT_BaseOperator):
    bl_idname = "object.snapshot_render_settings"
    bl_label = "Snapshot Settings"
    bl_description = "Configure snapshot output settings"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        settings = context.scene.snapshot_settings

        layout.prop(settings, "output_directory")
        layout.operator("object.open_snapshot_directory", text="Open Output Directory", icon='FILE_FOLDER')
        layout.separator()
        layout.prop(settings, "preview_render")
        layout.prop(settings, "filename_suffix")

    def execute(self, context):
        self.report({'INFO'}, "Snapshot settings updated.")
        return {'FINISHED'}
    
class OBJECT_OT_OpenSnapshotDirectory(OBJECT_OT_BaseOperator):
    bl_idname = "object.open_snapshot_directory"
    bl_label = "Open Snapshot Directory"

    def execute(self, context):
        output_dir = bpy.path.abspath(context.scene.snapshot_settings.output_directory)
        
        if not output_dir:
            self.report({'WARNING'}, "No output directory set")
            return {'CANCELLED'}
            
        success, message = safe_open_directory(output_dir)

        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

class OBJECT_OT_OpenPlayblastDirectory(OBJECT_OT_BaseOperator):
    bl_idname = "object.open_playblast_directory"
    bl_label = "Open Playblast Directory"

    def execute(self, context):
        settings = context.scene.viewport_render_settings
        output_dir = bpy.path.abspath(settings.output_directory)
        
        if not output_dir:
            self.report({'WARNING'}, "No output directory set")
            return {'CANCELLED'}
            
        success, message = safe_open_directory(output_dir)

        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

class SCENE_OT_JumpToMarker(OBJECT_OT_BaseOperator):
    bl_idname = "scene.jump_to_marker"
    bl_label = "Set as Active Camera"

    marker_name: StringProperty()

    def execute(self, context):
        marker = context.scene.timeline_markers.get(self.marker_name)
        if marker:
            context.scene.frame_current = marker.frame
            return {'FINISHED'}
        return {'CANCELLED'}

class SCENE_OT_RemoveAllMarkers(OBJECT_OT_BaseOperator):
    bl_idname = "scene.remove_all_markers"
    bl_label = "Remove All Markers"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        # Create a list copy to avoid modifying collection during iteration
        markers_to_remove = list(context.scene.timeline_markers)
        for marker in markers_to_remove:
            context.scene.timeline_markers.remove(marker)
        self.report({'INFO'}, "All markers have been removed")
        return {'FINISHED'}

class SCENE_OT_RemoveMarkerAndCamera(OBJECT_OT_BaseOperator):
    bl_idname = "scene.remove_marker_and_camera"
    bl_label = "Remove Marker and Camera"

    marker_name: StringProperty()

    def execute(self, context):
        marker = context.scene.timeline_markers.get(self.marker_name)
        if marker:
            if marker.camera and bpy.data.objects.get(marker.camera.name):
                bpy.data.objects.remove(bpy.data.objects[marker.camera.name])
            context.scene.timeline_markers.remove(marker)
            self.report({'INFO'}, f"Marker '{self.marker_name}' removed")
            return {'FINISHED'}
        self.report({'WARNING'}, f"Marker '{self.marker_name}' not found")
        return {'CANCELLED'}

class SCENE_OT_CleanUpMarkers(OBJECT_OT_BaseOperator):
    bl_idname = "scene.clean_up_markers"
    bl_label = "Clean Up Markers"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        selected_collection = scene.custom_name_props.get_shot_list_collection(context)

        if selected_collection:
            invalid_markers = [marker for marker in scene.timeline_markers
                               if not marker.camera or
                               marker.camera.name not in selected_collection.objects or
                               not bpy.data.objects.get(marker.camera.name)]

            for marker in invalid_markers:
                scene.timeline_markers.remove(marker)

            self.report({'INFO'}, f"Removed {len(invalid_markers)} invalid markers")
        else:
            self.report({'WARNING'}, "No collection selected")

        return {'FINISHED'}

class SCENE_OT_RemoveAllShotCameras(OBJECT_OT_BaseOperator):
    bl_idname = "scene.remove_all_shot_cameras"
    bl_label = "Remove All Shots?"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        selected_collection = scene.custom_name_props.get_shot_list_collection(context)

        if selected_collection:
            markers_to_remove = [marker for marker in scene.timeline_markers if marker.camera and marker.camera.name in selected_collection.objects]

            for marker in markers_to_remove:
                camera = marker.camera
                scene.timeline_markers.remove(marker)
                if camera:
                    bpy.data.objects.remove(camera)

        return {'FINISHED'}

class SCENE_OT_RemoveAllCameras(OBJECT_OT_BaseOperator):
    bl_idname = "scene.remove_all_cameras"
    bl_label = "Remove All Cameras"

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        scene = context.scene
        selected_collection = scene.custom_name_props.get_camera_list_collection(context)

        if selected_collection:
            cameras_to_remove = [obj for obj in selected_collection.objects if obj.type == 'CAMERA']

            for camera in cameras_to_remove:
                bpy.data.objects.remove(camera)

        return {'FINISHED'}

class SCENE_OT_SelectCamera(OBJECT_OT_BaseOperator):
    bl_idname = "scene.select_camera"
    bl_label = "Select Camera"

    camera_name: StringProperty()

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        camera = bpy.data.objects.get(self.camera_name)
        if camera:
            context.view_layer.objects.active = camera
            camera.select_set(True)
            return {'FINISHED'}
        return {'CANCELLED'}

class OBJECT_OT_toggle_local_camera(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_local_camera"
    bl_label = "Toggle Local Camera"

    def execute(self, context):
        context.space_data.use_local_camera = not context.space_data.use_local_camera
        return {'FINISHED'}

class OBJECT_OT_toggle_camera_info_overlay(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_camera_info_overlay"
    bl_label = "Toggle Camera Info Overlay"
    bl_description = "Toggle camera information overlay in viewport"

    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'WARNING'}, "Could not access addon preferences")
            return {'CANCELLED'}

        preferences.show_camera_info_overlay = not preferences.show_camera_info_overlay
        status = "enabled" if preferences.show_camera_info_overlay else "disabled"
        self.report({'INFO'}, f"Camera info overlay {status}")
        return {'FINISHED'}

class OBJECT_OT_toggle_camera_notes_overlay(OBJECT_OT_BaseOperator):
    bl_idname = "object.toggle_camera_notes_overlay"
    bl_label = "Toggle Camera Notes"
    bl_description = "Toggle camera notes overlay in viewport"

    def execute(self, context):
        preferences = get_addon_preferences(context)
        if preferences is None:
            self.report({'WARNING'}, "Could not access addon preferences")
            return {'CANCELLED'}

        preferences.show_camera_notes = not preferences.show_camera_notes
        status = "shown" if preferences.show_camera_notes else "hidden"
        self.report({'INFO'}, f"Camera notes {status}")
        return {'FINISHED'}

# Global variables for interactive note placement
_note_placement_handler = None
_note_placement_data = {}

def draw_note_placement_preview():
    """Draw preview of note being placed"""
    global _note_placement_data
    
    if not _note_placement_data:
        return
    
    context = bpy.context
    
    # Only draw in camera view
    if not context.space_data or context.space_data.type != 'VIEW_3D':
        return
    
    region_3d = context.space_data.region_3d
    if not region_3d or region_3d.view_perspective != 'CAMERA':
        return
    
    # Get mouse position and settings
    mouse_x = _note_placement_data.get('mouse_x', 0)
    mouse_y = _note_placement_data.get('mouse_y', 0)
    text = _note_placement_data.get('text', 'Note')
    font_size = _note_placement_data.get('font_size', 20)
    font_color = _note_placement_data.get('font_color', (1.0, 1.0, 0.0, 1.0))
    bg_color = _note_placement_data.get('bg_color', (0.0, 0.0, 0.0, 0.5))
    
    # Draw preview
    font_id = 0
    blf.size(font_id, font_size)
    
    # Calculate text dimensions for background
    text_width, text_height = blf.dimensions(font_id, text)
    
    # Draw background
    padding = 8
    bg_x = mouse_x - padding
    bg_y = mouse_y - padding
    bg_width = text_width + padding * 2
    bg_height = text_height + padding * 2
    
    # Set up proper GPU state for 2D overlay rendering
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    try:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        
        # Draw background
        batch_bg = batch_for_shader(
            shader, 'TRI_FAN',
            {"pos": [
                (bg_x, bg_y),
                (bg_x + bg_width, bg_y),
                (bg_x + bg_width, bg_y + bg_height),
                (bg_x, bg_y + bg_height)
            ]},
        )
        shader.bind()
        shader.uniform_float("color", bg_color)
        batch_bg.draw(shader)

        # Draw text
        blf.color(font_id, font_color[0], font_color[1], font_color[2], font_color[3])
        blf.position(font_id, mouse_x, mouse_y, 0)
        blf.draw(font_id, text)

        # Draw crosshair at cursor (reuse shader)
        cross_size = 10
        batch_cross = batch_for_shader(
            shader, 'LINES',
            {"pos": [
                (mouse_x - cross_size, mouse_y),
                (mouse_x + cross_size, mouse_y),
                (mouse_x, mouse_y - cross_size),
                (mouse_x, mouse_y + cross_size)
            ]},
        )
        shader.bind()
        shader.uniform_float("color", (1.0, 1.0, 1.0, 0.8))
        batch_cross.draw(shader)
    finally:
        # Restore default GPU state
        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('LESS_EQUAL')

class OBJECT_OT_add_note_interactive(Operator):
    bl_idname = "object.add_note_interactive"
    bl_label = "Add Note (Interactive)"
    bl_description = "Place a note at cursor position. Type to edit text, scroll to scale, Shift+scroll for font color, Ctrl+scroll for bg color"
    bl_options = {'REGISTER', 'UNDO'}
    
    camera_name: StringProperty()
    
    # Instance variables initialized in invoke
    mouse_x: IntProperty(default=0)
    mouse_y: IntProperty(default=0)
    text_input: StringProperty(default="")
    font_size: IntProperty(default=20)
    font_color: FloatVectorProperty(size=4, default=(1.0, 1.0, 0.0, 1.0))
    bg_color: FloatVectorProperty(size=4, default=(0.0, 0.0, 0.0, 0.5))
    hue_index: IntProperty(default=2)  # Start at yellow (0=Red, 1=Green, 2=Yellow, 3=Cyan, 4=Blue, 5=Magenta)
    
    def modal(self, context, event):
        global _note_placement_data, _note_placement_handler
        
        context.area.tag_redraw()
        
        # Update mouse position
        if event.type == 'MOUSEMOVE':
            self.mouse_x = event.mouse_region_x
            self.mouse_y = event.mouse_region_y
            _note_placement_data['mouse_x'] = self.mouse_x
            _note_placement_data['mouse_y'] = self.mouse_y
        
        # Shift + Scroll to change font color
        elif event.type == 'WHEELUPMOUSE' and event.shift:
            self.hue_index = (self.hue_index + 1) % 7
            self.font_color = self.get_color_from_index(self.hue_index)
            _note_placement_data['font_color'] = tuple(self.font_color)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE' and event.shift:
            self.hue_index = (self.hue_index - 1) % 7
            self.font_color = self.get_color_from_index(self.hue_index)
            _note_placement_data['font_color'] = tuple(self.font_color)
            return {'RUNNING_MODAL'}
        
        # Ctrl + Scroll to change background opacity
        elif event.type == 'WHEELUPMOUSE' and event.ctrl:
            self.bg_color[3] = min(1.0, self.bg_color[3] + 0.1)
            _note_placement_data['bg_color'] = tuple(self.bg_color)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE' and event.ctrl:
            self.bg_color[3] = max(0.0, self.bg_color[3] - 0.1)
            _note_placement_data['bg_color'] = tuple(self.bg_color)
            return {'RUNNING_MODAL'}
        
        # Scroll to change font size (no modifiers)
        elif event.type == 'WHEELUPMOUSE' and not event.shift and not event.ctrl:
            self.font_size = min(100, self.font_size + 2)
            _note_placement_data['font_size'] = self.font_size
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE' and not event.shift and not event.ctrl:
            self.font_size = max(8, self.font_size - 2)
            _note_placement_data['font_size'] = self.font_size
            return {'RUNNING_MODAL'}
        
        # Text input - handle all printable characters
        elif event.type in {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                            'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
                            'SPACE', 'PERIOD', 'COMMA', 'MINUS', 'PLUS', 'SLASH', 'SEMI_COLON', 'QUOTE',
                            'LEFT_BRACKET', 'RIGHT_BRACKET', 'BACK_SLASH', 'EQUAL', 'ACCENT_GRAVE'} and event.value == 'PRESS':
            
            # Convert event type to character (with shift support)
            if event.shift:
                shift_char_map = {
                    'ZERO': ')', 'ONE': '!', 'TWO': '@', 'THREE': '#', 'FOUR': '$',
                    'FIVE': '%', 'SIX': '^', 'SEVEN': '&', 'EIGHT': '*', 'NINE': '(',
                    'PERIOD': '>', 'COMMA': '<', 'MINUS': '_', 'PLUS': '+', 'SLASH': '?',
                    'SEMI_COLON': ':', 'QUOTE': '"', 'LEFT_BRACKET': '{', 'RIGHT_BRACKET': '}',
                    'BACK_SLASH': '|', 'EQUAL': '+', 'ACCENT_GRAVE': '~'
                }
                if event.type in shift_char_map:
                    char = shift_char_map[event.type]
                else:
                    # Letters to uppercase
                    char = event.type.upper() if len(event.type) == 1 else event.type.lower()
            else:
                char_map = {
                    'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
                    'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9',
                    'SPACE': ' ', 'PERIOD': '.', 'COMMA': ',', 'MINUS': '-', 'PLUS': '=', 
                    'SLASH': '/', 'SEMI_COLON': ';', 'QUOTE': "'", 'LEFT_BRACKET': '[',
                    'RIGHT_BRACKET': ']', 'BACK_SLASH': '\\', 'EQUAL': '=', 'ACCENT_GRAVE': '`'
                }
                
                if event.type in char_map:
                    char = char_map[event.type]
                else:
                    char = event.type.lower()
            
            self.text_input += char
            _note_placement_data['text'] = self.text_input if self.text_input else "Note"
            return {'RUNNING_MODAL'}
        
        # Backspace to delete characters
        elif event.type == 'BACK_SPACE' and event.value == 'PRESS':
            if self.text_input:
                self.text_input = self.text_input[:-1]
                _note_placement_data['text'] = self.text_input if self.text_input else "Note"
            return {'RUNNING_MODAL'}
        
        # Left click to confirm placement
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Calculate normalized camera-plane coordinates
            scene = context.scene
            region = context.region
            rv3d = context.space_data.region_3d
            cam = bpy.data.objects.get(self.camera_name)
            
            norm_x = 0.5
            norm_y = 0.5
            
            # Try to get normalized position on camera image plane
            try:
                frame_local = cam.data.view_frame()
                fw = [cam.matrix_world @ v for v in frame_local]
                
                # Ray from view through mouse
                mouse_region = Vector((self.mouse_x, self.mouse_y))
                ray_origin = region_2d_to_origin_3d(region, rv3d, mouse_region)
                ray_dir = region_2d_to_vector_3d(region, rv3d, mouse_region)
                
                # Define plane using camera frame
                bl_world = fw[3]
                br_world = fw[2]
                tl_world = fw[0]
                plane_normal = (br_world - bl_world).cross(tl_world - bl_world).normalized()
                
                # Intersect ray with plane
                denom = ray_dir.dot(plane_normal)
                if abs(denom) > 1e-6:
                    t = (bl_world - ray_origin).dot(plane_normal) / denom
                    point_world = ray_origin + ray_dir * t
                    point_local = cam.matrix_world.inverted() @ point_world
                    
                    # Solve for normalized coordinates
                    bl_local = frame_local[3]
                    r = frame_local[2] - frame_local[3]
                    u = frame_local[0] - frame_local[3]
                    
                    mat = mathutils.Matrix(((r.x, u.x), (r.y, u.y)))
                    vec = mathutils.Vector((point_local.x - bl_local.x, point_local.y - bl_local.y))
                    if mat.determinant() != 0:
                        sol = mat.inverted() @ vec
                        norm_x = sol[0]
                        norm_y = sol[1]
            except Exception:
                pass
            
            # Convert normalized to pixel values (multiply by reference)
            pixel_x = int(round(norm_x * 1000.0))
            pixel_y = int(round(norm_y * 1000.0))

            note = scene.camera_notes.add()
            note.camera_name = self.camera_name
            note.text = self.text_input if self.text_input else "Note"
            note.position_x = pixel_x
            note.position_y = pixel_y
            note.font_size = self.font_size
            note.font_color = self.font_color
            note.background_color = self.bg_color
            note.show_background = True  # Enable background by default
            scene.active_note_index = len(scene.camera_notes) - 1
            
            # Force viewport redraw
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            # Cleanup
            self.cleanup(context)
            self.report({'INFO'}, f"Note added at ({self.mouse_x}, {self.mouse_y})")
            return {'FINISHED'}
        
        # Right click or ESC to cancel
        elif event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            self.cleanup(context)
            self.report({'INFO'}, "Note placement cancelled")
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}
    
    def get_color_from_index(self, index):
        """Get a color from a predefined palette"""
        colors = [
            (1.0, 0.0, 0.0, 1.0),  # Red
            (0.0, 1.0, 0.0, 1.0),  # Green
            (1.0, 1.0, 0.0, 1.0),  # Yellow
            (0.0, 1.0, 1.0, 1.0),  # Cyan
            (0.0, 0.0, 1.0, 1.0),  # Blue
            (1.0, 0.0, 1.0, 1.0),  # Magenta
            (1.0, 1.0, 1.0, 1.0),  # White
        ]
        return colors[index % len(colors)]
    
    def invoke(self, context, event):
        global _note_placement_data, _note_placement_handler
        
        # Check if in camera view
        if not context.space_data or context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Must be in 3D View")
            return {'CANCELLED'}
        
        region_3d = context.space_data.region_3d
        if not region_3d or region_3d.view_perspective != 'CAMERA':
            self.report({'WARNING'}, "Must be in camera view to place notes")
            return {'CANCELLED'}
        
        # Check if camera exists
        scene = context.scene
        camera = bpy.data.objects.get(self.camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'WARNING'}, f"Camera '{self.camera_name}' not found")
            return {'CANCELLED'}
        
        # Reset instance variables for fresh start
        self.text_input = ""
        self.font_size = 20
        self.hue_index = 2  # Yellow
        self.font_color = self.get_color_from_index(self.hue_index)
        self.bg_color = [0.0, 0.0, 0.0, 0.5]
        self.mouse_x = event.mouse_region_x
        self.mouse_y = event.mouse_region_y
        
        # Initialize placement data
        _note_placement_data = {
            'mouse_x': self.mouse_x,
            'mouse_y': self.mouse_y,
            'text': 'Note',
            'font_size': 20,
            'font_color': tuple(self.font_color),
            'bg_color': tuple(self.bg_color)
        }
        
        # Register draw handler
        if _note_placement_handler is None:
            _note_placement_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_note_placement_preview, (), 'WINDOW', 'POST_PIXEL'
            )
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        
        self.report({'INFO'}, "Click to place note. Type to edit text. Scroll to scale. ESC to cancel.")
        return {'RUNNING_MODAL'}
    
    def cleanup(self, context):
        global _note_placement_data, _note_placement_handler
        
        # Remove draw handler
        if _note_placement_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_note_placement_handler, 'WINDOW')
            _note_placement_handler = None
        
        _note_placement_data = {}
        context.area.tag_redraw()

class OBJECT_OT_add_camera_note(OBJECT_OT_BaseOperator):
    bl_idname = "object.add_camera_note"
    bl_label = "Add Note"
    bl_description = "Add a new note to the selected camera"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        scene = context.scene
        note = scene.camera_notes.add()
        note.camera_name = self.camera_name
        note.text = f"Note {len(scene.camera_notes)}"
        note.position_x = 500
        note.position_y = 500
        scene.active_note_index = len(scene.camera_notes) - 1
        
        # Force viewport redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        self.report({'INFO'}, f"Added note to camera '{self.camera_name}'")
        return {'FINISHED'}

class OBJECT_OT_remove_camera_note(OBJECT_OT_BaseOperator):
    bl_idname = "object.remove_camera_note"
    bl_label = "Remove Note"
    bl_description = "Remove the selected note"
    
    note_index: IntProperty()
    
    def execute(self, context):
        scene = context.scene
        if 0 <= self.note_index < len(scene.camera_notes):
            scene.camera_notes.remove(self.note_index)
            if scene.active_note_index >= len(scene.camera_notes):
                scene.active_note_index = len(scene.camera_notes) - 1
            
            # Force viewport redraw
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, "Note removed")
            return {'FINISHED'}
        return {'CANCELLED'}

class OBJECT_OT_clear_camera_notes(OBJECT_OT_BaseOperator):
    bl_idname = "object.clear_camera_notes"
    bl_label = "Clear All Notes"
    bl_description = "Remove all notes for the selected camera"
    
    camera_name: StringProperty()
    
    def execute(self, context):
        scene = context.scene
        indices_to_remove = []
        
        for i, note in enumerate(scene.camera_notes):
            if note.camera_name == self.camera_name:
                indices_to_remove.append(i)
        
        # Remove in reverse order to maintain indices
        for i in reversed(indices_to_remove):
            scene.camera_notes.remove(i)
        
        scene.active_note_index = 0
        self.report({'INFO'}, f"Cleared {len(indices_to_remove)} notes")
        return {'FINISHED'}

class VIEW3D_MT_PIE_QuickCamera(Menu):
    bl_label = "Quick Camera"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        
        # Get active camera and check if in camera view
        scene = context.scene
        active_camera = scene.camera
        
        # Check if in camera view
        in_camera_view = False
        if context.space_data and context.space_data.type == 'VIEW_3D':
            region_3d = context.space_data.region_3d
            if region_3d and region_3d.view_perspective == 'CAMERA':
                in_camera_view = True
        
        # Main pie items
        pie.operator("object.add_camera", text="Add Camera", icon="CAMERA_DATA")
        pie.operator("object.add_camera_with_marker", text="Add Shot", icon="VIEW_CAMERA")
        pie.operator("object.add_camera_copy_properties", text="Copy Camera", icon="CAMERA_DATA")
        pie.operator("object.add_camera_shot_copy_properties", text="Copy Shot", icon="VIEW_CAMERA")
        
        # Add Note option (only if there's an active camera AND in camera view)
        if active_camera and active_camera.type == 'CAMERA' and in_camera_view:
            op = pie.operator("object.add_note_interactive", text="Add Note", icon="FILE_TEXT")
            op.camera_name = active_camera.name
        else:
            pie.separator()
        
        # Toggle Notes overlay (only show when in camera view)
        if in_camera_view:
            preferences = get_addon_preferences(context)
            if preferences is None:
                pie.separator()
            else:
                icon = 'HIDE_OFF' if preferences.show_camera_notes else 'HIDE_ON'
                text = "Hide Notes" if preferences.show_camera_notes else "Show Notes"
                pie.operator("object.toggle_camera_notes_overlay", text=text, icon=icon)
        else:
            pie.separator()

        # Adjust passepartout of the active camera (drag to change)
        if active_camera and active_camera.type == 'CAMERA':
            pie.operator("object.adjust_passepartout", text="Passepartout", icon='CAMERA_DATA')
        else:
            pie.separator()

        # Toggle Camera Info Overlay
        preferences = get_addon_preferences(context)
        if preferences is None:
            pie.separator()
        else:
            icon = 'HIDE_OFF' if preferences.show_camera_info_overlay else 'HIDE_ON'
            text = "Hide Camera Info" if preferences.show_camera_info_overlay else "Show Camera Info"
            pie.operator("object.toggle_camera_info_overlay", text=text, icon=icon)

class SCENE_OT_SetActiveCamera(OBJECT_OT_BaseOperator):
    bl_idname = "scene.set_active_camera"
    bl_label = "Set Active Camera"

    camera_name: StringProperty()

    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera:
            context.scene.camera = camera
            self.report({'INFO'}, f"Camera '{self.camera_name}' set as active.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Camera '{self.camera_name}' not found.")
            return {'CANCELLED'}

class OBJECT_OT_delete_camera(OBJECT_OT_BaseOperator):
    bl_idname = "object.delete_camera"
    bl_label = "Delete Camera"

    camera_name: StringProperty()

    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera:
            bpy.data.objects.remove(camera)
            self.report({'INFO'}, f"Camera '{self.camera_name}' removed.")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"Camera '{self.camera_name}' not found.")
            return {'CANCELLED'}

class SCENE_OT_set_and_view_camera(Operator):
    bl_idname = "scene.set_and_view_camera"
    bl_label = "Set and View Camera"
    bl_description = "Set the camera as active and view through it"

    camera_name: StringProperty()

    def execute(self, context):
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            context.scene.camera = camera
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces[0].region_3d.view_perspective = 'CAMERA'
                    break
            return {'FINISHED'}
        return {'CANCELLED'}

class OBJECT_OT_toggle_favorite_camera(Operator):
    bl_idname = "object.toggle_favorite_camera"
    bl_label = "Toggle Favorite Camera"
    bl_description = "Toggle this camera as a favorite"

    camera_name: StringProperty()

    def execute(self, context):
        props = context.scene.custom_name_props
        camera = bpy.data.objects.get(self.camera_name)
        if camera and camera.type == 'CAMERA':
            favorite_cameras = [fc.camera for fc in props.favorite_cameras if fc.camera]
            
            if camera in favorite_cameras:
                for i, fc in enumerate(props.favorite_cameras):
                    if fc.camera == camera:
                        props.favorite_cameras.remove(i)
                        break
            elif len(props.favorite_cameras) < 8:
                new_favorite = props.favorite_cameras.add()
                new_favorite.camera = camera
            else:
                self.report({'WARNING'}, "You can only have up to 8 favorite cameras")
            
            return {'FINISHED'}

class VIEW3D_MT_PIE_favorite_camera(Menu):
    bl_label = "Favorite Cameras"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        
        props = context.scene.custom_name_props
        favorite_cameras = [fc for fc in props.favorite_cameras if fc.camera]
        
        for i, fc in enumerate(favorite_cameras):
            if i < 8:  # Limit to 8 cameras in the pie menu
                op = pie.operator("scene.set_and_view_camera", text=fc.camera.name)
                op.camera_name = fc.camera.name
        
        # Fill remaining slots with empty operators to complete the pie menu
        for _ in range(8 - len(favorite_cameras)):
            pie.separator()

class WM_OT_capture_keymap(bpy.types.Operator):
    bl_idname = "wm.capture_keymap"
    bl_label = "Press a Key"

    pie_menu: bpy.props.StringProperty()

    def execute(self, context):
        addon_prefs = get_addon_preferences(context)
        if addon_prefs is None:
            self.report({'ERROR'}, "Addon preferences not available")
            return {'CANCELLED'}
        addon_prefs.capture_key = True
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        addon_prefs = get_addon_preferences(context)
        if addon_prefs is None:
            self.report({'ERROR'}, "Addon preferences not available")
            return {'CANCELLED'}
        if event.type == 'TIMER':
            return {'PASS_THROUGH'}

        if event.value == 'PRESS':
            if self.pie_menu == "quick_camera":
                addon_prefs.quick_camera_key = event.type
                addon_prefs.quick_camera_ctrl = event.ctrl
                addon_prefs.quick_camera_alt = event.alt
                addon_prefs.quick_camera_shift = event.shift
            elif self.pie_menu == "camera_controls":
                addon_prefs.camera_controls_key = event.type
                addon_prefs.camera_controls_ctrl = event.ctrl
                addon_prefs.camera_controls_alt = event.alt
                addon_prefs.camera_controls_shift = event.shift
            elif self.pie_menu == "favorite_camera":
                addon_prefs.favorite_camera_key = event.type
                addon_prefs.favorite_camera_ctrl = event.ctrl
                addon_prefs.favorite_camera_alt = event.alt
                addon_prefs.favorite_camera_shift = event.shift
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

    pie_menu: bpy.props.StringProperty()

    def execute(self, context):
        addon_prefs = get_addon_preferences(context)
        if addon_prefs is None:
            self.report({'ERROR'}, "Addon preferences not available")
            return {'CANCELLED'}
        if self.pie_menu == "quick_camera":
            addon_prefs.quick_camera_key = ''
            addon_prefs.quick_camera_ctrl = False
            addon_prefs.quick_camera_alt = False
            addon_prefs.quick_camera_shift = False
        elif self.pie_menu == "camera_controls":
            addon_prefs.camera_controls_key = ''
            addon_prefs.camera_controls_ctrl = False
            addon_prefs.camera_controls_alt = False
            addon_prefs.camera_controls_shift = False
        elif self.pie_menu == "favorite_camera":
            addon_prefs.favorite_camera_key = ''
            addon_prefs.favorite_camera_ctrl = False
            addon_prefs.favorite_camera_alt = False
            addon_prefs.favorite_camera_shift = False

        update_keymap(self, context)
        return {'FINISHED'}

def update_keymap(self, context):
    pass

class OBJECT_OT_adjust_focal_length(Operator):
    bl_idname = "object.adjust_focal_length"
    bl_label = "Adjust Focal Length/Ortho Scale"

    initial_value: FloatProperty()

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'MOUSEMOVE':
                sensitivity = 0.1 if event.shift else 1.0
                delta = (event.mouse_x - event.mouse_prev_x) * sensitivity

                if self.camera.data.type == 'ORTHO':
                    self.camera.data.ortho_scale = max(0.1, self.camera.data.ortho_scale + delta * 0.05)
                    self.display_text = f"Orthographic Scale: {self.camera.data.ortho_scale:.2f}"
                else:
                    self.camera.data.lens = max(1, self.camera.data.lens + delta)
                    self.display_text = f"Focal Length: {self.camera.data.lens:.1f}mm"

            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}

            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                if self.camera.data.type == 'ORTHO':
                    self.camera.data.ortho_scale = self.initial_value
                else:
                    self.camera.data.lens = self.initial_value
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.camera = context.scene.camera or context.view_layer.objects.active
        if self.camera and self.camera.type == 'CAMERA':
            if self.camera.data.type == 'ORTHO':
                self.initial_value = self.camera.data.ortho_scale
                self.display_text = f"Orthographic Scale: {self.initial_value:.2f}"
            else:
                self.initial_value = self.camera.data.lens
                self.display_text = f"Focal Length: {self.initial_value:.1f}mm"
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

    def draw_callback_px(self, op, context):
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        
        # Get the dimensions of the region
        region = context.region
        width = region.width
        height = region.height
        
        # Calculate text dimensions
        blf.size(font_id, 20)
        text_width, text_height = blf.dimensions(font_id, self.display_text)
        
        # Position text at the bottom center
        x = (width - text_width) / 2
        y = 70  # Adjust this value to move the text up or down
        
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, self.display_text)

class OBJECT_OT_adjust_fstop(Operator):
    bl_idname = "object.adjust_fstop"
    bl_label = "Adjust F-Stop"

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'MOUSEMOVE':
                sensitivity = 0.01 if event.shift else 0.1
                delta = (event.mouse_x - event.mouse_prev_x) * sensitivity
                self.camera.data.dof.aperture_fstop = max(0.1, self.camera.data.dof.aperture_fstop + delta)
                self.display_text = f"F-Stop: f/{self.camera.data.dof.aperture_fstop:.1f}"
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                self.camera.data.dof.aperture_fstop = self.initial_fstop
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.camera.data.dof.use_dof = self.initial_use_dof
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.camera = context.scene.camera or context.view_layer.objects.active
        if self.camera and self.camera.type == 'CAMERA':
            self.initial_fstop = self.camera.data.dof.aperture_fstop
            self.initial_use_dof = self.camera.data.dof.use_dof
            self.camera.data.dof.use_dof = True  # Enable DoF
            self.display_text = f"F-Stop: f/{self.initial_fstop:.1f}"
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

    def draw_callback_px(self, op, context):
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        
        # Get the dimensions of the region
        region = context.region
        width = region.width
        height = region.height
        
        # Calculate text dimensions
        blf.size(font_id, 20)
        text_width, text_height = blf.dimensions(font_id, self.display_text)
        
        # Position text at the bottom center
        x = (width - text_width) / 2
        y = 70  # Adjust this value to move the text up or down
        
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, self.display_text)

class OBJECT_OT_adjust_passepartout(Operator):
    bl_idname = "object.adjust_passepartout"
    bl_label = "Adjust Passepartout"
    bl_description = "Drag to adjust the active camera's passepartout alpha"

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'MOUSEMOVE':
                sensitivity = 0.001 if event.shift else 0.005
                delta = (event.mouse_x - event.mouse_prev_x) * sensitivity
                self.camera.data.passepartout_alpha = min(1.0, max(0.0, self.camera.data.passepartout_alpha + delta))
                self.display_text = f"Passepartout: {self.camera.data.passepartout_alpha:.2f}"
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                self.camera.data.passepartout_alpha = self.initial_value
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        self.camera = context.scene.camera or context.view_layer.objects.active
        if self.camera and self.camera.type == 'CAMERA':
            self.initial_value = self.camera.data.passepartout_alpha
            self.display_text = f"Passepartout: {self.initial_value:.2f}"
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

    def draw_callback_px(self, op, context):
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        
        # Get the dimensions of the region
        region = context.region
        width = region.width
        height = region.height
        
        # Calculate text dimensions
        blf.size(font_id, 20)
        text_width, text_height = blf.dimensions(font_id, self.display_text)
        
        # Position text at the bottom center
        x = (width - text_width) / 2
        y = 70  # Adjust this value to move the text up or down
        
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, self.display_text)

class OBJECT_OT_dof_picker(Operator):
    bl_idname = "object.dof_picker"
    bl_label = "DoF Picker"

    def _restore_dof_state(self):
        self.camera.data.dof.focus_distance = self.initial_focus
        self.camera.data.dof.use_dof = self.initial_use_dof
        self.camera.data.dof.focus_object = self.initial_focus_object

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'MOUSEMOVE':
                self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                self.update_focus(context, event)
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                context.window.cursor_modal_restore()
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                context.window.cursor_modal_restore()
                self._restore_dof_state()
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            context.window.cursor_modal_restore()
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._restore_dof_state()
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a 3D view")
            return {'CANCELLED'}

        self.camera = context.scene.camera or context.view_layer.objects.active
        if self.camera and self.camera.type == 'CAMERA':
            self.initial_focus = self.camera.data.dof.focus_distance
            self.initial_use_dof = self.camera.data.dof.use_dof
            self.initial_focus_object = self.camera.data.dof.focus_object
            self.camera.data.dof.use_dof = True  # Enable DoF
            if self.initial_focus_object is not None:
                self.camera.data.dof.focus_object = None
            context.window.cursor_modal_set('EYEDROPPER')
            self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.display_text = f"DoF Distance: {self.initial_focus:.2f}m"
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

    def update_focus(self, context, event):
        coord = event.mouse_region_x, event.mouse_region_y
        region = context.region
        rv3d = context.region_data
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
        ray_target = ray_origin + view_vector

        hit, location, _, _, _, _ = context.scene.ray_cast(context.view_layer.depsgraph, ray_origin, view_vector)

        if hit:
            focus_distance = (self.camera.matrix_world.inverted() @ location).length
            self.camera.data.dof.focus_distance = focus_distance
            self.display_text = f"DoF Distance: {focus_distance:.2f}m"

    def draw_callback_px(self, op, context):
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        blf.position(font_id, self.mouse_pos.x + 15, self.mouse_pos.y - 15, 0)
        blf.size(font_id, 16)
        blf.draw(font_id, self.display_text)

class OBJECT_OT_dof_focus_object_picker(Operator):
    bl_idname = "object.dof_focus_object_picker"
    bl_label = "Pick DoF Focus Object"

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'MOUSEMOVE':
                self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
                self.update_focus_object(context, event)
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                context.window.cursor_modal_restore()
                context.area.header_text_set(None)
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                context.window.cursor_modal_restore()
                context.area.header_text_set(None)
                self.camera.data.dof.focus_object = self.initial_focus_object
                self.camera.data.dof.use_dof = self.initial_use_dof
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            context.window.cursor_modal_restore()
            context.area.header_text_set(None)
            self.restore_selection(context)
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.camera.data.dof.use_dof = self.initial_use_dof
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a 3D view")
            return {'CANCELLED'}

        self.camera = context.scene.camera or context.view_layer.objects.active
        if self.camera and self.camera.type == 'CAMERA':
            self.initial_focus_object = self.camera.data.dof.focus_object
            self.initial_use_dof = self.camera.data.dof.use_dof
            self.camera.data.dof.use_dof = True  # Enable DoF
            context.window.cursor_modal_set('EYEDROPPER')
            self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
            self.current_object = None
            args = (self, context)
            self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

    def update_focus_object(self, context, event):
        coord = event.mouse_region_x, event.mouse_region_y
        region = context.region
        rv3d = context.region_data
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)

        result, location, normal, index, object, matrix = context.scene.ray_cast(context.view_layer.depsgraph, ray_origin, view_vector)
        if result and object is not None:
            self.camera.data.dof.focus_object = object
            self.current_object = object
            context.area.header_text_set(f"Focus Object: {object.name}")
            return

        self.current_object = None
        context.area.header_text_set("No object under cursor")

    def draw_callback_px(self, op, context):
        if self.current_object:
            font_id = 0
            blf.color(font_id, 1, 1, 1, 1)
            blf.position(font_id, self.mouse_pos.x + 15, self.mouse_pos.y - 15, 0)
            blf.size(font_id, 16)
            blf.draw(font_id, self.current_object.name)

class OBJECT_OT_set_dof_object(Operator):
    bl_idname = "object.set_dof_object"
    bl_label = "Set DoF Object"

    def execute(self, context):
        camera = context.scene.camera or context.view_layer.objects.active
        if camera and camera.type == 'CAMERA':
            return bpy.ops.object.dof_focus_object_picker('INVOKE_DEFAULT')

        self.report({'WARNING'}, "No active camera")
        return {'CANCELLED'}

class OBJECT_OT_remove_dof_object(Operator):
    bl_idname = "object.remove_dof_object"
    bl_label = "Remove DoF Object"
    bl_description = "Remove the current focus object from the camera"

    def execute(self, context):
        camera = context.scene.camera or context.view_layer.objects.active
        if camera and camera.type == 'CAMERA':
            camera.data.dof.focus_object = None
            camera.data.dof.use_dof = False
            self.report({'INFO'}, "Removed DoF focus object and disabled DoF")
        else:
            self.report({'WARNING'}, "No active camera")
        return {'FINISHED'}

class OBJECT_OT_create_empty_focus(Operator):
    bl_idname = "object.create_empty_focus"
    bl_label = "Create Empty Focus"
    bl_description = "Create an empty object and set it as the camera's focus object"

    def modal(self, context, event):
        try:
            context.area.tag_redraw()

            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self.create_empty_and_set_focus(context, event)
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                self.camera.data.dof.use_dof = self.initial_use_dof
                if hasattr(self, '_handle'):
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'CANCELLED'}

            return {'RUNNING_MODAL'}
        except Exception as e:
            # Ensure handler is removed on error
            if hasattr(self, '_handle'):
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self.camera.data.dof.use_dof = self.initial_use_dof
            self.report({'ERROR'}, f"Error in modal operator: {str(e)}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if context.space_data.type != 'VIEW_3D':
            self.report({'WARNING'}, "Active space must be a 3D view")
            return {'CANCELLED'}

        self.camera = context.scene.camera or context.view_layer.objects.active
        if not self.camera or self.camera.type != 'CAMERA':
            self.report({'WARNING'}, "No active camera")
            return {'CANCELLED'}

        self.initial_use_dof = self.camera.data.dof.use_dof
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

        context.window.cursor_modal_set('CROSSHAIR')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def create_empty_and_set_focus(self, context, event):
        # Get the ray from the viewport and mouse
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y
        view_vector = region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = region_2d_to_origin_3d(region, rv3d, coord)

        result, location, normal, index, object, matrix = context.scene.ray_cast(context.view_layer.depsgraph, ray_origin, view_vector)

        if result:
            # Create empty
            empty = bpy.data.objects.new("CameraFocus", None)
            empty.empty_display_type = 'PLAIN_AXES'
            empty.location = location
            context.scene.collection.objects.link(empty)

            # Set empty as camera's focus object
            self.camera.data.dof.focus_object = empty
            self.camera.data.dof.use_dof = True

            self.report({'INFO'}, "Created empty focus object and set it as camera's focus")
        else:
            self.report({'WARNING'}, "No object found under mouse cursor")

        context.window.cursor_modal_restore()
    
    def draw_callback_px(self, op, context):
        font_id = 0
        blf.color(font_id, 1, 1, 1, 1)
        
        # Get the dimensions of the region
        region = context.region
        width = region.width
        height = region.height
        
        # Calculate text dimensions
        text = "Click to Place Empty Focus"
        blf.size(font_id, 20)
        text_width, text_height = blf.dimensions(font_id, text)
        
        # Position text at the bottom center
        x = (width - text_width) / 2
        y = 70  # Adjust this value to move the text up or down
        
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, text)

class OBJECT_OT_toggle_lock_camera_to_view(Operator):
    bl_idname = "object.toggle_lock_camera_to_view"
    bl_label = "Toggle Lock Camera to View"
    bl_description = "Toggle the 'Lock Camera to View' option"

    def execute(self, context):
        context.space_data.lock_camera = not context.space_data.lock_camera
        status = "enabled" if context.space_data.lock_camera else "disabled"
        self.report({'INFO'}, f"Lock Camera to View {status}")
        return {'FINISHED'}

class OBJECT_OT_select_active_camera(Operator):
    bl_idname = "object.select_active_camera"
    bl_label = "Select Active Camera"
    bl_description = "Select the active camera in the scene"

    def execute(self, context):
        active_camera = context.scene.camera
        if active_camera:
            bpy.ops.object.select_all(action='DESELECT')
            active_camera.select_set(True)
            context.view_layer.objects.active = active_camera
            self.report({'INFO'}, f"Selected active camera: {active_camera.name}")
        else:
            self.report({'WARNING'}, "No active camera in the scene")
        return {'FINISHED'}

class OBJECT_OT_toggle_favorite_active_camera(Operator):
    bl_idname = "object.toggle_favorite_active_camera"
    bl_label = "Toggle Favorite Active Camera"
    bl_description = "Add or remove the active camera from favorites"

    def execute(self, context):
        active_camera = context.scene.camera
        if active_camera and active_camera.type == 'CAMERA':
            props = context.scene.custom_name_props
            favorite_cameras = [fc.camera for fc in props.favorite_cameras if fc.camera]
            
            if active_camera in favorite_cameras:
                for i, fc in enumerate(props.favorite_cameras):
                    if fc.camera == active_camera:
                        props.favorite_cameras.remove(i)
                        self.report({'INFO'}, f"Removed {active_camera.name} from favorites")
                        break
            else:
                if len(props.favorite_cameras) < 8:
                    new_favorite = props.favorite_cameras.add()
                    new_favorite.camera = active_camera
                    self.report({'INFO'}, f"Added {active_camera.name} to favorites")
                else:
                    self.report({'WARNING'}, "Favorite list is full. Remove a camera to add a new one.")
        else:
            self.report({'WARNING'}, "No active camera to favorite/unfavorite")
        return {'FINISHED'}

class VIEW3D_MT_PIE_camera_controls(Menu):
    bl_label = "Camera Controls"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        camera = context.scene.camera or context.view_layer.objects.active
        
        pie.operator("object.dof_picker", text="DoF Distance", icon='DRIVER_DISTANCE')
        
        if camera and camera.type == 'CAMERA' and camera.data.dof.focus_object:
            pie.operator("object.remove_dof_object", text="Remove DoF Object", icon='X')
        else:
            pie.operator("object.set_dof_object", text="Set DoF Object", icon='OBJECT_DATA')
        
        pie.operator("object.adjust_focal_length", text="Focal Length", icon='CAMERA_DATA')
        pie.operator("object.adjust_fstop", text="F-Stop", icon='CAMERA_DATA')
        pie.operator("object.create_empty_focus", text="Create Empty Focus", icon='EMPTY_AXIS')
        pie.operator("object.toggle_lock_camera_to_view", text="Lock Camera to View", icon='LOCKVIEW_ON')
        pie.operator("object.select_active_camera", text="Select Active Camera", icon='OUTLINER_OB_CAMERA')

        props = context.scene.custom_name_props
        favorite_cameras = [fc.camera for fc in props.favorite_cameras if fc.camera]
        is_favorite = camera in favorite_cameras if camera and camera.type == 'CAMERA' else False

        if is_favorite:
            pie.operator("object.toggle_favorite_active_camera", text="Remove from Favorite", icon='X')
        else:
            pie.operator("object.toggle_favorite_active_camera", text="Favorite Active Camera", icon='SOLO_ON')

def collect_all_attributes(obj):
    """Recursively collects all attributes of an object."""
    if obj is None:
        return None
        
    attributes = {}
    for attr in dir(obj):
        if not attr.startswith('_') and not callable(getattr(obj, attr)):
            try:
                value = getattr(obj, attr)
                if isinstance(value, (bool, int, float, str)):
                    attributes[attr] = value
                elif hasattr(value, '__iter__') and not isinstance(value, str):
                    if len(value) > 0 and all(isinstance(x, (bool, int, float, str)) for x in value):
                        attributes[attr] = list(value)
            except (AttributeError, TypeError, RuntimeError):
                # Skip attributes that can't be accessed or serialized
                continue
    return attributes

def apply_settings(obj, settings):
    """Recursively applies settings to an object."""
    if not settings or not obj:
        return
        
    for key, value in settings.items():
        try:
            if isinstance(value, dict):
                apply_settings(getattr(obj, key), value)
            elif hasattr(obj, key):
                setattr(obj, key, value)
        except Exception as e:
            logging.getLogger(__name__).warning("Failed to set %s: %s", key, e)



class OBJECT_OT_ExportAllSettings(Operator):
    bl_idname = "render.export_all_settings"
    bl_label = "Export All Settings"
    bl_description = "Export all render settings, including nested attributes, as a JSON file"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            # Get current active preset name if it exists
            preset_name = "New Preset"
            if hasattr(context.scene, "render_presets"):
                index = context.scene.render_presets.active_preset_index
                if index >= 0 and index < len(context.scene.render_presets.presets):
                    preset_name = context.scene.render_presets.presets[index].name

            # Collect settings
            settings = {
                "preset_name": preset_name,  # Include preset name in export
                "render_settings": collect_all_attributes(bpy.context.scene.render),
                "cycles_settings": collect_all_attributes(bpy.context.scene.cycles) if hasattr(bpy.context.scene, "cycles") else None,
                "eevee_settings": collect_all_attributes(bpy.context.scene.eevee) if hasattr(bpy.context.scene, "eevee") else None,
                "world_settings": collect_all_attributes(bpy.context.scene.world) if bpy.context.scene.world else None,
                "view_settings": collect_all_attributes(bpy.context.scene.view_settings),
            }

            with open(self.filepath, "w") as file:
                json.dump(settings, file, indent=4)
            self.report({"INFO"}, f"Settings exported to {self.filepath}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to export settings: {e}")
            return {"CANCELLED"}

    def invoke(self, context, event):
        if not self.filepath:
            # Use active preset name for filename if available
            if hasattr(context.scene, "render_presets"):
                index = context.scene.render_presets.active_preset_index
                if index >= 0 and index < len(context.scene.render_presets.presets):
                    preset_name = context.scene.render_presets.presets[index].name
                    # Sanitize the preset name to prevent path traversal
                    safe_name = sanitize_filename(preset_name)
                    self.filepath = os.path.join(
                        os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser("~"),
                        f"{safe_name}.json"
                    )

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

class OBJECT_OT_ImportAllSettings(Operator):
    bl_idname = "render.import_all_settings"
    bl_label = "Import All Settings"
    bl_description = "Import render settings from a JSON file as a new preset"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            # Load settings from JSON
            with open(self.filepath, "r") as file:
                settings = json.load(file)

            # Extract preset name if it exists in the file, otherwise use filename
            if isinstance(settings, dict):
                preset_name = settings.pop("preset_name", None)
                if not preset_name:
                    preset_name = os.path.splitext(os.path.basename(self.filepath))[0]

            # Create new preset if render_presets exists
            if hasattr(context.scene, "render_presets"):
                presets = context.scene.render_presets.presets
                new_preset = presets.add()
                new_preset.name = preset_name
                # Store settings as a JSON string in the preset
                new_preset.settings = json.dumps(settings)
                # Set as active preset
                context.scene.render_presets.active_preset_index = len(presets) - 1

            self.report({"INFO"}, f"Settings imported as preset: {preset_name}")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to import settings: {e}")
            return {"CANCELLED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

class RenderPreset(PropertyGroup):
    name: StringProperty(default="New Preset")
    settings: StringProperty()  # Store settings as JSON string
    render_engine: StringProperty(default="BLENDER_EEVEE")  # Store render engine type

# Property group to store all presets and active index
class RenderPresetsCollection(PropertyGroup):
    presets: CollectionProperty(type=RenderPreset)
    active_preset_index: IntProperty()

# UI List for render presets
class RENDER_UL_presets_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Get render engine type from preset settings
            settings = json.loads(item.settings) if item.settings else {}
            render_settings = settings.get("render_settings", {})
            engine = render_settings.get("engine", item.render_engine)
            
            # Display appropriate icon based on render engine
            engine_icon = 'EVENT_E'
            if engine == 'CYCLES':
                engine_icon = 'EVENT_C'
            elif engine == 'BLENDER_EEVEE':
                engine_icon = 'EVENT_UNKNOWN'
                
            row.label(text="", icon=engine_icon)
            row.prop(item, "name", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PRESET')

# Operator to add new preset
class RENDER_OT_add_preset(Operator):
    bl_idname = "render.add_preset"
    bl_label = "Add Preset"
    bl_description = "Add a new render preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        presets = context.scene.render_presets.presets
        new_preset = presets.add()
        new_preset.name = f"Preset {len(presets)}"
        context.scene.render_presets.active_preset_index = len(presets) - 1
        return {'FINISHED'}

# Operator to remove preset
class RENDER_OT_remove_preset(Operator):
    bl_idname = "render.remove_preset"
    bl_label = "Remove Preset"
    bl_description = "Remove selected render preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        presets = context.scene.render_presets.presets
        index = context.scene.render_presets.active_preset_index
        
        if index >= 0 and index < len(presets):
            presets.remove(index)
            context.scene.render_presets.active_preset_index = min(index, len(presets) - 1)
        
        return {'FINISHED'}

# Operator to save current render settings to preset
class RENDER_OT_save_to_preset(Operator):
    bl_idname = "render.save_to_preset"
    bl_label = "Save Current Settings"
    bl_description = "Save current render settings to selected preset"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        index = context.scene.render_presets.active_preset_index
        if index < 0:
            self.report({'ERROR'}, "No preset selected")
            return {'CANCELLED'}
            
        try:
            # Collect all settings
            settings = {
                "render_settings": collect_all_attributes(context.scene.render),
                "cycles_settings": collect_all_attributes(context.scene.cycles) if hasattr(context.scene, "cycles") else None,
                "eevee_settings": collect_all_attributes(context.scene.eevee) if hasattr(context.scene, "eevee") else None,
                "world_settings": collect_all_attributes(context.scene.world) if context.scene.world else None,
                "view_settings": collect_all_attributes(context.scene.view_settings),
            }
            
            # Save settings to preset
            preset = context.scene.render_presets.presets[index]
            preset.settings = json.dumps(settings)
            
            # Store current render engine
            preset.render_engine = context.scene.render.engine
            
            self.report({'INFO'}, f"Settings saved to preset {preset.name}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save settings: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

# Operator to apply preset settings
# Update the RENDER_OT_apply_preset operator
class RENDER_OT_apply_preset(Operator):
    bl_idname = "render.apply_preset"
    bl_label = "Apply Preset"
    bl_description = "Apply selected preset settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Add properties for selective application
    apply_render: BoolProperty(
        name="Render Settings",
        description="Apply render settings (resolution, samples, etc.)",
        default=True
    )
    
    apply_cycles: BoolProperty(
        name="Cycles Settings",
        description="Apply Cycles render engine settings",
        default=True
    )
    
    apply_eevee: BoolProperty(
        name="EEVEE Settings",
        description="Apply EEVEE render engine settings",
        default=True
    )
    
    apply_world: BoolProperty(
        name="World Settings",
        description="Apply world settings (background, environment, etc.)",
        default=True
    )
    
    apply_view: BoolProperty(
        name="View Settings",
        description="Apply view settings (color management, etc.)",
        default=True
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Settings to Apply:")
        
        col = layout.column(align=True)
        col.prop(self, "apply_render")
        col.prop(self, "apply_cycles")
        col.prop(self, "apply_eevee")
        col.prop(self, "apply_world")
        col.prop(self, "apply_view")
    
    def execute(self, context):
        index = context.scene.render_presets.active_preset_index
        if index < 0:
            self.report({'ERROR'}, "No preset selected")
            return {'CANCELLED'}
            
        preset = context.scene.render_presets.presets[index]
        if not preset.settings:
            self.report({'ERROR'}, "No settings saved for this preset")
            return {'CANCELLED'}
            
        try:
            # Load settings from preset
            settings = json.loads(preset.settings)
            
            # Apply settings based on user selection
            if self.apply_render and "render_settings" in settings:
                apply_settings(context.scene.render, settings["render_settings"])
                
            if self.apply_cycles and "cycles_settings" in settings and hasattr(context.scene, "cycles"):
                apply_settings(context.scene.cycles, settings["cycles_settings"])
                
            if self.apply_eevee and "eevee_settings" in settings and hasattr(context.scene, "eevee"):
                apply_settings(context.scene.eevee, settings["eevee_settings"])
                
            if self.apply_world and "world_settings" in settings and context.scene.world:
                apply_settings(context.scene.world, settings["world_settings"])
                
            if self.apply_view and "view_settings" in settings:
                apply_settings(context.scene.view_settings, settings["view_settings"])
            
            self.report({'INFO'}, f"Applied selected settings from preset {preset.name}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to apply settings: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class RENDER_OT_backup_all_presets(Operator):
    bl_idname = "render.backup_all_presets"
    bl_label = "Backup All Presets"
    bl_description = "Save all render presets to a single file"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        try:
            presets = context.scene.render_presets.presets
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "presets": []
            }
            
            # Collect all presets
            for preset in presets:
                preset_data = {
                    "name": preset.name,
                    "settings": json.loads(preset.settings) if preset.settings else {}
                }
                backup_data["presets"].append(preset_data)
            
            # Save to file
            with open(self.filepath, 'w') as f:
                json.dump(backup_data, f, indent=4)
                
            self.report({'INFO'}, f"Successfully backed up {len(presets)} presets")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to backup presets: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if not self.filepath:
            blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0] if bpy.data.filepath else "untitled"
            # Sanitize blend name to prevent path traversal
            safe_blend_name = sanitize_filename(blend_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.filepath = os.path.join(
                os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser("~"),
                f"{safe_blend_name}_render_presets_{timestamp}.json"
            )

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class RENDER_OT_restore_all_presets(Operator):
    bl_idname = "render.restore_all_presets"
    bl_label = "Restore All Presets"
    bl_description = "Restore render presets from a backup file"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(subtype="FILE_PATH")
    replace_existing: BoolProperty(
        name="Replace Existing",
        description="Replace existing presets with the same names",
        default=True
    )
    
    def execute(self, context):
        try:
            with open(self.filepath, 'r') as f:
                backup_data = json.load(f)
            
            # Validate backup data structure
            if not isinstance(backup_data, dict) or "presets" not in backup_data:
                self.report({'ERROR'}, "Invalid backup file format")
                return {'CANCELLED'}
            
            presets = context.scene.render_presets.presets
            restored_count = 0
            skipped_count = 0
            
            # Process each preset in the backup
            for preset_data in backup_data["presets"]:
                name = preset_data["name"]
                settings = preset_data["settings"]
                
                # Check if preset with this name already exists
                existing_preset = None
                for p in presets:
                    if p.name == name:
                        existing_preset = p
                        break
                
                if existing_preset:
                    if self.replace_existing:
                        # Update existing preset
                        existing_preset.settings = json.dumps(settings)
                        restored_count += 1
                    else:
                        skipped_count += 1
                        continue
                else:
                    # Create new preset
                    new_preset = presets.add()
                    new_preset.name = name
                    new_preset.settings = json.dumps(settings)
                    restored_count += 1
            
            msg = f"Restored {restored_count} presets"
            if skipped_count > 0:
                msg += f" (skipped {skipped_count} existing)"
            self.report({'INFO'}, msg)
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to restore presets: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "replace_existing")

class RENDER_OT_duplicate_preset(Operator):
    bl_idname = "render.duplicate_preset"
    bl_label = "Duplicate Preset"
    bl_description = "Create a copy of the selected preset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        presets = context.scene.render_presets.presets
        active_index = context.scene.render_presets.active_preset_index

        if active_index < 0 or active_index >= len(presets):
            self.report({'WARNING'}, "No preset selected")
            return {'CANCELLED'}

        # Get the source preset
        source_preset = presets[active_index]
        
        # Create new preset
        new_preset = presets.add()
        
        # Copy settings
        new_preset.name = source_preset.name + " Copy"
        new_preset.settings = source_preset.settings  # Copy the settings JSON string
        
        # Set the new preset as active
        context.scene.render_presets.active_preset_index = len(presets) - 1
        
        self.report({'INFO'}, f"Duplicated preset: {source_preset.name}")
        return {'FINISHED'}

# Update the draw_render_presets function
def draw_render_presets(self, context, layout):
    box = layout.box()
    box.label(text="Render Presets:", icon="PRESET")
    
    row = box.row()
    # Main list on the left
    row.template_list("RENDER_UL_presets_list", "", context.scene.render_presets,
                     "presets", context.scene.render_presets, "active_preset_index")
    
    # Side buttons column
    col = row.column(align=True)
    col.operator("render.add_preset", icon='ADD', text="")
    col.operator("render.remove_preset", icon='REMOVE', text="")
    col.separator()
    col.operator("render.duplicate_preset", icon='DUPLICATE', text="")
    col.operator("render.save_to_preset", icon='FILE_TICK', text="")
    col.operator("render.apply_preset", icon='CHECKMARK', text="")
    
    # Backup/restore and export/import buttons below
    row = box.row(align=True)
    row.operator("render.backup_all_presets", icon='EXPORT', text="Batch Export")
    row.operator("render.restore_all_presets", icon='IMPORT', text="Batch Import")
    
    row = box.row(align=True)
    row.operator("render.export_all_settings", icon='FILE_BACKUP', text="Export Settings")
    row.operator("render.import_all_settings", icon='FILE_REFRESH', text="Import Settings")

classes = (
    FavoriteCameraItem,
    CameraNoteItem,
    OBJECT_OT_toggle_default_interpolation,
    OBJECT_OT_toggle_interpolation_selected,
    OBJECT_OT_toggle_interpolation_all,
    OBJECT_OT_apply_all_constant,
    OBJECT_OT_apply_all_bezier,
    OBJECT_OT_apply_all_linear,
    OBJECT_OT_apply_selected_constant,
    OBJECT_OT_apply_selected_bezier,
    OBJECT_OT_apply_selected_linear,
    OBJECT_OT_toggle_auto_keying,
    OBJECT_OT_add_keyframes_operator,
    OBJECT_OT_delete_keyframes_per_steps,
    OBJECT_OT_bake_keyframes_per_steps,
    SCENE_OT_set_frame,
    RenderToolsSettings,
    SelectHiddenDisableRenderOperator,
    OBJECT_OT_DisableRenderForHidden,
    OBJECT_OT_CreateExceptionCollection,
    OBJECT_OT_AddSelectedToExceptions,
    CreateExcludeHiddenCollectionOperator,
    CustomNameProperties,
    OBJECT_OT_ApplyPassepartoutToAllCameras,
    OBJECT_OT_ApplyClippingToAllCameras,
    OBJECT_OT_TogglePanelVisibility,
    OBJECT_OT_CreateCameraCollection,
    AddCameraButton,
    AddCameraWithMarkerButton,
    AddCameraCopyPropertiesButton,
    AddCameraShotCopyPropertiesButton,
    SCENE_OT_SetPreviewRange,
    ShowPopupMessageOperator,
    OBJECT_OT_PlayblastConfirm,
    OBJECT_OT_PlayblastSettings,
    OBJECT_OT_SnapshotRender,
    OBJECT_OT_SnapshotRenderSettings,
    OBJECT_OT_OpenSnapshotDirectory,
    OBJECT_OT_OpenPlayblastDirectory,
    SCENE_OT_JumpToMarker,
    SCENE_OT_RemoveAllMarkers,
    SCENE_OT_RemoveMarkerAndCamera,
    SCENE_OT_CleanUpMarkers,
    SCENE_OT_RemoveAllShotCameras,
    SCENE_OT_RemoveAllCameras,
    SCENE_OT_SelectCamera,
    OBJECT_OT_toggle_local_camera,
    VIEW3D_MT_PIE_QuickCamera,
    SCENE_OT_SetActiveCamera,
    OBJECT_OT_delete_camera,
    WM_OT_capture_keymap,
    WM_OT_remove_keymap,
    OBJECT_OT_dof_picker,
    OBJECT_OT_remove_dof_object,
    OBJECT_OT_dof_focus_object_picker,
    OBJECT_OT_adjust_focal_length,
    OBJECT_OT_adjust_fstop,
    OBJECT_OT_adjust_passepartout,
    OBJECT_OT_set_dof_object,
    OBJECT_OT_toggle_lock_camera_to_view,
    OBJECT_OT_select_active_camera,
    OBJECT_OT_toggle_camera_info_overlay,
    OBJECT_OT_toggle_camera_notes_overlay,
    OBJECT_OT_add_note_interactive,
    OBJECT_OT_add_camera_note,
    OBJECT_OT_remove_camera_note,
    OBJECT_OT_clear_camera_notes,
    VIEW3D_MT_PIE_camera_controls,
    SCENE_OT_set_and_view_camera,
    OBJECT_OT_create_empty_focus,
    OBJECT_OT_toggle_favorite_camera,
    VIEW3D_MT_PIE_favorite_camera,
    OBJECT_OT_toggle_favorite_active_camera,
    OBJECT_OT_ExportAllSettings,
    OBJECT_OT_ImportAllSettings,
    RenderPreset,
    RenderPresetsCollection,
    RENDER_UL_presets_list,
    RENDER_OT_add_preset,
    RENDER_OT_remove_preset,
    RENDER_OT_save_to_preset,
    RENDER_OT_apply_preset,
    RENDER_OT_backup_all_presets,
    RENDER_OT_restore_all_presets,
    RENDER_OT_duplicate_preset,


)


# Classes are registered in __init__.py to avoid double registration issues

if __name__ == "__main__":
    import bpy
    # Can't register from here when running as a module
    pass