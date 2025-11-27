import bpy
from bpy.types import Panel, UIList, PropertyGroup, Operator
from bpy.props import BoolProperty, StringProperty, IntProperty, FloatVectorProperty, EnumProperty
from .utils import draw_property, draw_operator
from . import operators

class OBJECT_PT_BasePanel(Panel):
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Kyokaz Toolbox'

    @classmethod
    def poll(cls, context):
        return context.area.type in {'GRAPH_EDITOR', 'DOPESHEET_EDITOR', 'TIMELINE', 'ACTION_EDITOR', 'FCURVES'}

class OBJECT_UL_CollectionList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon='OUTLINER_COLLECTION')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OUTLINER_COLLECTION')

class OBJECT_PT_toggle_interpolation_panel(OBJECT_PT_BasePanel):
    bl_label = "Animation Tools"
    bl_idname = "OBJECT_PT_toggle_interpolation_panel"

    def draw_header(self, context):
        self.layout.label(icon='RENDER_ANIMATION')

    def draw(self, context):
        layout = self.layout
        layout.operator("object.toggle_auto_keying", 
                        text="Auto Keying: " + ("On" if context.scene.tool_settings.use_keyframe_insert_auto else "Off"), 
                        icon='AUTO')
        layout.separator()

class OBJECT_PT_interpolation_tools_panel(OBJECT_PT_BasePanel):
    bl_label = "Interpolation Tools"
    bl_parent_id = "OBJECT_PT_toggle_interpolation_panel"

    def draw(self, context):
        layout = self.layout
        interpolation_type = context.preferences.edit.keyframe_new_interpolation_type
        interpolation_icon = {'CONSTANT': 'IPO_CONSTANT', 'LINEAR': 'IPO_LINEAR'}.get(interpolation_type, 'IPO_BEZIER')
        interpolation_text = interpolation_type.capitalize()

        layout.label(text="Toggle Default Interpolation:")
        layout.operator("object.toggle_default_interpolation", text=interpolation_text, icon=interpolation_icon)
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

class OBJECT_PT_bake_tools_panel(OBJECT_PT_BasePanel):
    bl_label = "Bake Tools"
    bl_parent_id = "OBJECT_PT_toggle_interpolation_panel"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Bake Selected Keyframes:")
        layout.operator("object.bake_keyframes_per_steps", icon='ANIM_DATA')
        layout.operator("object.add_keyframes_operator", icon='KEY_HLT')
        layout.operator("object.delete_keyframes_per_steps", icon='KEY_DEHLT')
        layout.separator()


class OBJECT_PT_RenderToolsPanel(bpy.types.Panel):
    bl_label = "Render Tools"
    bl_idname = "OBJECT_PT_render_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        try:
            preferences = context.preferences.addons[__package__].preferences
            return preferences.show_render_tools_n_panel
        except (KeyError, AttributeError):
            return True  # Default to showing if preferences not found

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='RENDER_STILL')

    def draw(self, context):
        layout = self.layout
        settings = context.scene.render_tools_settings

        draw_property(layout, settings, "output_directory", "Output Directory", icon='FILE_FOLDER')

        box = layout.box()
        box.label(text="Render Settings:", icon="RENDER_STILL")
        # Main operator and Affect Children option
        row = box.row(align=True)
        row.operator("object.disable_render_for_hidden", text="Disable Render for Hidden", icon='HIDE_ON')
        row.prop(settings, "affect_children", text="", icon='OUTLINER_OB_ARMATURE')

        # Exception Collection
        row = box.row(align=True)
        row.prop(settings, "exception_collection", text="")
        row.operator("object.create_exception_collection", text="", icon='COLLECTION_NEW')
        row.operator("object.add_selected_to_exceptions", text="Add Selected", icon='HAND')

        # Tooltip for the Exception Collection
        row = box.row(align=True)
        row.label(text="Exception: Objects in this collection will be ignored", icon='INFO')

        # Viewport Render
        box = layout.box()
        box.label(text="Viewport Render:", icon="RENDER_STILL")
        row = box.row(align=True)
        row.operator("object.viewport_render_confirm", text="Viewport Render", icon='RENDER_STILL')
        row.operator("object.viewport_render_settings", text="", icon='PREFERENCES')
        
        row = box.row(align=True)
        row.operator("object.snapshot_render", text="Snapshot", icon='RENDER_RESULT')
        row.operator("object.snapshot_render_settings", text="", icon='PREFERENCES')

        # Add render presets UI
        operators.draw_render_presets(self, context, layout)


class OBJECT_PT_CameraTools(Panel):
    bl_label = "Quick Camera"
    bl_idname = "OBJECT_PT_CameraTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'

    @classmethod
    def poll(cls, context):
        try:
            preferences = context.preferences.addons[__package__].preferences
            return preferences.show_quick_camera_n_panel
        except (KeyError, AttributeError):
            return True  # Default to showing if preferences not found

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='CAMERA_DATA')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.custom_name_props

        # Camera Collection Selection
        box = layout.box()
        box.label(text="Camera Collection:", icon="OUTLINER_COLLECTION")
        row = box.row(align=True)
        row.prop(props, "camera_collection", text="")

        # New Collection Creation
        row = box.row(align=True)
        row.prop(props, "collection_name", text="")
        row.operator("object.create_camera_collection", text="", icon="PLUS")

        # Camera Creation
        box = layout.box()
        box.label(text="Add New Camera:", icon="ADD")
        
        row = box.row()
        row.prop(props, "camera_name")
        row.operator("object.add_camera", text="", icon="ADD")
        row = box.row()
        row.prop(props, "shot_name")
        row.operator("object.add_camera_with_marker", text="", icon="ADD")

        row = box.row(align=True)
        row.operator("object.add_camera_copy_properties", text="Copy Camera", icon="CAMERA_DATA")
        row.operator("object.add_camera_shot_copy_properties", text="Copy Shot", icon="VIEW_CAMERA")

class OBJECT_PT_DefaultCameraSettings(Panel):
    bl_label = "Default Camera Settings"
    bl_parent_id = "OBJECT_PT_CameraTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.custom_name_props
        
        layout.prop(props, "default_type")
        
        row = layout.row(align=True)
        row.prop(props, "default_passepartout")
        row.operator("object.apply_passepartout_to_all_cameras", text="", icon='CHECKMARK')
        
        row = layout.row()
        if props.default_type == 'ORTHO':
            row.prop(props, "default_ortho_scale")
        else:
            row.prop(props, "default_lens")
        
        row = layout.row()
        row.prop(props, "default_clip_start")
        row.prop(props, "default_clip_end")

class OBJECT_PT_ActiveCameraSettings(Panel):
    bl_label = "Active Camera Settings"
    bl_parent_id = "OBJECT_PT_CameraTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'CAMERA'

    def draw(self, context):
        layout = self.layout
        active_object = context.active_object
        
        row = layout.row(align=True)
        if active_object.data.type == 'ORTHO':
            row.prop(active_object.data, "ortho_scale", text="Ortho Scale")
        else:
            row.prop(active_object.data, "lens", text="Focal Length")
        
        row = layout.row()
        row.prop(active_object.data, "type")
        
        row = layout.row()
        row.prop(active_object.data, "passepartout_alpha", text="Passepartout")
        
        row = layout.row()
        row.prop(active_object.data, "clip_start")
        row.prop(active_object.data, "clip_end")
        
        layout.prop(active_object.data.dof, "use_dof", text="Depth of Field")
        if active_object.data.dof.use_dof:
            row = layout.row(align=True)
            row.prop(active_object.data.dof, "focus_distance", text="Focus Distance")
            row.prop(active_object.data.dof, "aperture_fstop", text="F-Stop")


class OBJECT_PT_CameraInfoOverlay(Panel):
    bl_label = "Camera Info Overlay"
    bl_parent_id = "OBJECT_PT_CameraTools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        try:
            preferences = context.preferences.addons[__package__].preferences
            row = layout.row(align=True)
            row.prop(preferences, "show_camera_info_overlay", text="")
            row.label(text="", icon='CAMERA_DATA')
            row.prop(preferences, "show_camera_notes", text="", icon='TEXT')
        except (KeyError, AttributeError):
            pass

    def draw(self, context):
        layout = self.layout
        
        try:
            preferences = context.preferences.addons[__package__].preferences
            
            # Enable/disable layout based on overlay state
            layout.enabled = preferences.show_camera_info_overlay
            
            # Layout options
            box = layout.box()
            box.label(text="Layout:", icon='ALIGN_JUSTIFY')
            box.prop(preferences, "camera_info_single_line")
            if preferences.camera_info_single_line:
                box.prop(preferences, "camera_info_separator", text="Separator")
            
            # Position and appearance
            box = layout.box()
            box.label(text="Position & Appearance:", icon='ORIENTATION_VIEW')
            col = box.column(align=True)
            col.prop(preferences, "camera_info_position_x", text="X Position")
            col.prop(preferences, "camera_info_position_y", text="Y Position")
            col.prop(preferences, "camera_info_font_size", text="Font Size")
            col.prop(preferences, "camera_info_font_color", text="Font Color")
            col.prop(preferences, "camera_info_background_color", text="Background")
            
            # Info display options
            box = layout.box()
            box.label(text="Display Options:", icon='PREFERENCES')
            col = box.column(align=True)
            col.prop(preferences, "camera_info_show_name")
            col.prop(preferences, "camera_info_show_frames")
            col.prop(preferences, "camera_info_show_focal")
            col.prop(preferences, "camera_info_show_focus")
            col.prop(preferences, "camera_info_show_fstop")
            
        except (KeyError, AttributeError):
            layout.label(text="Preferences not available", icon='ERROR')


class OBJECT_UL_ShotList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        scene = context.scene
        props = scene.custom_name_props
        selected_collection = props.get_shot_list_collection(context)

        if selected_collection and item.camera and item.camera.name in selected_collection.objects:
            row = layout.row(align=True)

            is_current_camera = scene.camera and scene.camera.name == item.camera.name
            is_preview_range = scene.use_preview_range and scene.frame_preview_start == item.frame

            # Jump to marker
            op = row.operator("scene.jump_to_marker", text="", icon='MARKER')
            op.marker_name = item.name

            # Select camera
            op_select = row.operator("scene.select_camera", text="", icon='RESTRICT_SELECT_OFF')
            op_select.camera_name = item.camera.name

            # Shot/Marker name with note indicator
            name_row = row.row(align=True)
            name_row.prop(item, "name", text="", emboss=False)
            
            # Check if shot's camera has notes
            has_notes = any(note.camera_name == item.camera.name for note in scene.camera_notes)
            if has_notes:
                name_row.label(text="", icon='TEXT')

            # Preview range
            preview_row = row.row()
            preview_row.alert = is_preview_range
            op_preview = preview_row.operator("scene.set_preview_range", text="", icon='PREVIEW_RANGE')
            op_preview.start_frame = item.frame

            # Calculate end frame safely
            marker_index = scene.timeline_markers.find(item.name)
            if marker_index >= 0 and marker_index < len(scene.timeline_markers) - 1:
                end_frame = scene.timeline_markers[marker_index + 1].frame
            else:
                end_frame = scene.frame_end

            op_preview.end_frame = end_frame
            op_preview.toggle = not is_preview_range

            # Frame range and duration
            shot_frames = end_frame - item.frame
            
            frame_row = row.row()
            frame_row.label(text=f"{item.frame} - {end_frame} ({shot_frames} frames)")

            # Remove marker and camera
            op_remove = row.operator("scene.remove_marker_and_camera", text="", icon='X')
            op_remove.marker_name = item.name

    def filter_items(self, context, data, propname):
        helpers = bpy.types.UI_UL_list
        markers = getattr(data, propname)
        props = context.scene.custom_name_props
        selected_collection = props.get_shot_list_collection(context)
        
        # Initialize filter flags and order
        flt_flags = [self.bitflag_filter_item] * len(markers)
        flt_neworder = []

        # Filter by name
        if self.filter_name:
            flt_flags = helpers.filter_items_by_name(self.filter_name, self.bitflag_filter_item, markers, "name")

        # Filter by selected collection
        if selected_collection:
            for idx, marker in enumerate(markers):
                if not marker.camera or marker.camera.name not in selected_collection.objects:
                    flt_flags[idx] &= ~self.bitflag_filter_item

        # Sort
        if self.use_filter_sort_alpha:
            flt_neworder = helpers.sort_items_by_name(markers, "name")

        return flt_flags, flt_neworder

class OBJECT_PT_ShotList(Panel):
    bl_label = "Shot List"
    bl_idname = "OBJECT_PT_ShotList"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'

    @classmethod
    def poll(cls, context):
        try:
            preferences = context.preferences.addons[__package__].preferences
            return preferences.show_shot_list_n_panel
        except (KeyError, AttributeError):
            return True  # Default to showing if preferences not found

    def draw_header(self, context):
        self.layout.label(icon='VIEW_CAMERA')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.custom_name_props

        # Camera Collection Selection
        box = layout.box()
        box.label(text="Camera Collection:", icon="OUTLINER_COLLECTION")
        row = box.row(align=True)
        row.prop(props, "shot_list_collection", text="")

        selected_collection = props.get_shot_list_collection(context)

        if selected_collection:
            layout.template_list("OBJECT_UL_ShotList", "", scene, "timeline_markers", scene, "active_marker_index", rows=5)

            valid_markers = [marker for marker in scene.timeline_markers
                             if marker.camera and marker.camera.name in selected_collection.objects]

            if valid_markers:
                # Calculate total frames safely
                if len(valid_markers) > 1:
                    total_frames = sum(valid_markers[i+1].frame - valid_markers[i].frame for i in range(len(valid_markers)-1))
                    total_frames += scene.frame_end - valid_markers[-1].frame
                else:
                    # Only one marker
                    total_frames = scene.frame_end - valid_markers[0].frame
                layout.label(text=f"Total Shot Duration: {total_frames} frames")
            else:
                layout.label(text="No shots in the selected collection")
            
            col = layout.column(align=True)
            col.operator("scene.remove_all_shot_cameras", text="Remove All Shots and Markers", icon='TRASH')
            col.operator("scene.remove_all_markers", text="Remove All Markers", icon='MARKER')
            col.operator("scene.clean_up_markers", text="Clean Up Markers", icon='BRUSH_DATA')
        else:
            layout.label(text="No collection selected")


class OBJECT_UL_CameraList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item.type == 'CAMERA':
            row = layout.row(align=True)
            
            # Select camera
            op_select = row.operator("scene.select_camera", text="", icon='RESTRICT_SELECT_OFF')
            op_select.camera_name = item.name

            # Set active camera
            op_set_active = row.operator("scene.set_active_camera", text="", icon='OUTLINER_OB_CAMERA')
            op_set_active.camera_name = item.name

            # Favorite toggle
            props = context.scene.custom_name_props
            is_favorite = item in [fc.camera for fc in props.favorite_cameras if fc.camera]
            icon = 'SOLO_ON' if is_favorite else 'SOLO_OFF'
            op = row.operator("object.toggle_favorite_camera", text="", icon=icon, emboss=False)
            op.camera_name = item.name

            # Camera name with note indicator
            name_row = row.row(align=True)
            name_row.prop(item, "name", text="", emboss=False)
            
            # Check if camera has notes
            scene = context.scene
            has_notes = any(note.camera_name == item.name for note in scene.camera_notes)
            if has_notes:
                name_row.label(text="", icon='TEXT')

            # Camera settings
            if item.data.type == 'ORTHO':
                row.prop(item.data, "ortho_scale", text="Ortho Scale", emboss=True)
            else:
                row.prop(item.data, "lens", text="Lens", emboss=True)
            
            # DOF toggle
            dof_row = row.row(align=True)
            
            if item.data.dof.use_dof:
                dof_row.prop(item.data.dof, "focus_distance", text="Focus", emboss=True)
                dof_row.prop(item.data.dof, "focus_object", text="", emboss=True)
            
            row.prop(item.data.dof, "use_dof", text="", icon='PROP_ON', toggle=True)

            # Remove camera
            op_remove = row.operator("object.delete_camera", text="", icon='X')
            op_remove.camera_name = item.name

    def filter_items(self, context, data, propname):
        helpers = bpy.types.UI_UL_list
        objects = context.scene.objects
        props = context.scene.custom_name_props
        selected_collection = props.get_camera_list_collection(context)
        
        # Initialize filter flags and order
        flt_flags = [self.bitflag_filter_item] * len(objects)
        flt_neworder = []

        # Filter by name
        if self.filter_name:
            flt_flags = helpers.filter_items_by_name(self.filter_name, self.bitflag_filter_item, objects, "name")

        # Filter by camera type and selected collection
        for idx, obj in enumerate(objects):
            if obj.type != 'CAMERA' or (selected_collection and obj.name not in selected_collection.objects):
                flt_flags[idx] &= ~self.bitflag_filter_item

        # Sort
        if self.use_filter_sort_alpha:
            flt_neworder = helpers.sort_items_by_name(objects, "name")

        return flt_flags, flt_neworder

class OBJECT_PT_CameraList(Panel):
    bl_label = "Camera List"
    bl_idname = "OBJECT_PT_CameraList"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'

    @classmethod
    def poll(cls, context):
        try:
            preferences = context.preferences.addons[__package__].preferences
            return preferences.show_camera_list_n_panel
        except (KeyError, AttributeError):
            return True  # Default to showing if preferences not found

    def draw_header(self, context):
        self.layout.label(icon='OUTLINER_OB_CAMERA')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.custom_name_props

        # Camera Collection Selection
        box = layout.box()
        box.label(text="Camera Collection:", icon="OUTLINER_COLLECTION")
        row = box.row(align=True)
        row.prop(props, "camera_list_collection", text="")

        selected_collection = props.get_camera_list_collection(context)

        if selected_collection:
            layout.template_list("OBJECT_UL_CameraList", "", selected_collection, "objects", scene, "camera_index", rows=5)

            col = layout.column(align=True)
            col.operator("scene.remove_all_cameras", text="Remove All Cameras", icon='TRASH')
            col.operator("object.add_camera", text="Add New Camera", icon='ADD')
            
            # Add information about favorite cameras
            favorite_count = len([fc for fc in props.favorite_cameras if fc.camera])
            layout.label(text=f"Favorite Cameras: {favorite_count}/8")
        else:
            layout.label(text="No collection selected")

class OBJECT_UL_camera_notes(UIList):
    """UIList for camera notes"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="", icon='HIDE_OFF' if item.enabled else 'HIDE_ON', emboss=False)
            row.prop(item, "text", text="", emboss=False, icon='TEXT')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(item, "enabled", text="", icon='HIDE_OFF' if item.enabled else 'HIDE_ON')
    
    def filter_items(self, context, data, propname):
        """Filter items to show only notes for the active camera"""
        notes = getattr(data, propname)
        flt_flags = []
        flt_neworder = []
        
        scene = context.scene
        camera_name = None
        
        # Use the active scene camera
        if scene.camera and scene.camera.type == 'CAMERA':
            camera_name = scene.camera.name
        
        if camera_name:
            # Filter: show only notes matching the active camera
            flt_flags = [self.bitflag_filter_item if note.camera_name == camera_name else 0 
                         for note in notes]
        else:
            # Show all notes if no active camera
            flt_flags = [self.bitflag_filter_item for _ in notes]
        
        return flt_flags, flt_neworder

class OBJECT_OT_move_note(bpy.types.Operator):
    """Move note up or down in the list"""
    bl_idname = "object.move_note"
    bl_label = "Move Note"
    bl_options = {'REGISTER', 'UNDO'}
    
    direction: bpy.props.EnumProperty(
        items=[
            ('UP', 'Up', 'Move note up'),
            ('DOWN', 'Down', 'Move note down'),
        ]
    )
    note_index: bpy.props.IntProperty()
    
    def execute(self, context):
        scene = context.scene
        notes = scene.camera_notes
        
        if self.direction == 'UP' and self.note_index > 0:
            notes.move(self.note_index, self.note_index - 1)
            scene.active_note_index -= 1
        elif self.direction == 'DOWN' and self.note_index < len(notes) - 1:
            notes.move(self.note_index, self.note_index + 1)
            scene.active_note_index += 1
        
        # Force viewport redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
            
        return {'FINISHED'}

class OBJECT_PT_Notes(Panel):
    """Unified notes panel that works in both Camera List and Shot List contexts"""
    bl_label = "Notes"
    bl_idname = "OBJECT_PT_Notes"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Toolbox'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        # Show panel if there's an active camera in the scene
        return context.scene.camera and context.scene.camera.type == 'CAMERA'

    def draw_header(self, context):
        layout = self.layout
        try:
            preferences = context.preferences.addons[__package__].preferences
            layout.prop(preferences, "show_camera_notes", text="")
        except (KeyError, AttributeError):
            layout.label(icon='TEXT')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Use the active scene camera
        camera = scene.camera
        
        if camera and camera.type == 'CAMERA':
            box = layout.box()
            box.label(text=f"Active Camera: {camera.name}", icon='CAMERA_DATA')
            
            # Use template_list for scrollable list (filter is handled in the UIList)
            row = box.row()
            row.template_list("OBJECT_UL_camera_notes", "", scene, "camera_notes", scene, "active_note_index", rows=5)
            
            # Add/Remove/Move buttons
            col = row.column(align=True)
            op = col.operator("object.add_camera_note", text="", icon='ADD')
            op.camera_name = camera.name
            
            # Check if active note belongs to this camera
            active_note_valid = False
            if 0 <= scene.active_note_index < len(scene.camera_notes):
                active_note = scene.camera_notes[scene.active_note_index]
                if active_note.camera_name == camera.name:
                    active_note_valid = True
                    op = col.operator("object.remove_camera_note", text="", icon='REMOVE')
                    op.note_index = scene.active_note_index
            
            col.separator()
            
            if active_note_valid:
                op = col.operator("object.move_note", text="", icon='TRIA_UP')
                op.direction = 'UP'
                op.note_index = scene.active_note_index
                
                op = col.operator("object.move_note", text="", icon='TRIA_DOWN')
                op.direction = 'DOWN'
                op.note_index = scene.active_note_index
            
            # Settings for selected note
            if active_note_valid:
                active_note = scene.camera_notes[scene.active_note_index]
                settings_box = layout.box()
                settings_box.label(text="Note Settings:", icon='PREFERENCES')
                
                col = settings_box.column(align=True)
                col.prop(active_note, "text", text="Text")
                
                row = col.row(align=True)
                row.prop(active_note, "position_x", text="X")
                row.prop(active_note, "position_y", text="Y")
                
                col.prop(active_note, "font_size", text="Size")
                col.prop(active_note, "font_color", text="Color")
                
                col.separator()
                col.prop(active_note, "show_background", text="Show Background")
                if active_note.show_background:
                    col.prop(active_note, "background_color", text="BG Color")
            
            # Count notes for this camera
            camera_notes_count = sum(1 for note in scene.camera_notes if note.camera_name == camera.name)
            layout.label(text=f"Total: {camera_notes_count} notes")

# Create parent panel instances for Camera List and Shot List
class OBJECT_PT_CameraNotes(OBJECT_PT_Notes):
    bl_idname = "OBJECT_PT_CameraNotes"
    bl_parent_id = "OBJECT_PT_CameraList"

class OBJECT_PT_ShotNotes(OBJECT_PT_Notes):
    bl_idname = "OBJECT_PT_ShotNotes"
    bl_parent_id = "OBJECT_PT_ShotList"

class ViewportRenderSettings(PropertyGroup):
    output_directory: StringProperty(
        name="Output Directory",
        description="Directory to save the viewport render",
        subtype='DIR_PATH',
        default=""
    )
    preview_render: BoolProperty(
        name="Preview",
        description="Preview the rendered animation after rendering",
        default=True
    )
    save_file: BoolProperty(
        name="Save File",
        description="Save the rendered animation to file",
        default=True
    )
    filename_suffix: StringProperty(
        name="Name Suffix",
        description="Suffix to add to the viewport render filename",
        default="viewport_render"
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
    use_stamp_camera: BoolProperty(name="Stamp Camera", default=True)
    use_stamp_frame: BoolProperty(name="Stamp Frame", default=True)
    use_stamp_time: BoolProperty(name="Stamp Time", default=True)
    use_stamp_filename: BoolProperty(name="Stamp Filename", default=True)
    use_stamp_date: BoolProperty(name="Stamp Date", default=True)
    use_stamp_frame_range: BoolProperty(name="Stamp Frame Range", default=True)
    use_stamp_scene: BoolProperty(name="Stamp Scene", default=False)
    use_stamp_note: BoolProperty(name="Stamp Note", default=False)
    use_stamp_marker: BoolProperty(name="Stamp Marker", default=False)
    use_stamp_sequencer_strip: BoolProperty(name="Stamp Sequencer Strip", default=False)
    use_stamp_render_time: BoolProperty(name="Stamp Render Time", default=False)

class SnapshotSettings(PropertyGroup):
    output_directory: StringProperty(
        name="Output Directory",
        description="Directory to save the snapshot",
        subtype='DIR_PATH',
        default=""
    )
    preview_render: BoolProperty(
        name="Preview",
        description="Preview the rendered image after snapshot",
        default=True
    )
    save_file: BoolProperty(
        name="Save File",
        description="Save the rendered snapshot to file",
        default=True
    )
    filename_suffix: StringProperty(
        name="Name Suffix",
        description="Suffix to add to the snapshot filename",
        default="snapshot"
    )

class KYOKAZ_PT_ToolboxScenePanel(bpy.types.Panel):
    bl_label = "Kyokaz's Toolbox"
    bl_idname = "KYOKAZ_PT_ToolboxScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        self.layout.label(icon='EVENT_K')

    def draw(self, context):
        layout = self.layout
        layout.label(text="Kyokaz's Toolbox version 2.6", icon="INFO")

class KYOKAZ_PT_RenderToolsScenePanel(bpy.types.Panel):
    bl_label = "Render Tools"
    bl_parent_id = "KYOKAZ_PT_ToolboxScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='RENDER_STILL')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_RenderToolsPanel
        OBJECT_PT_RenderToolsPanel.draw(self, context)

class KYOKAZ_PT_QuickCameraScenePanel(bpy.types.Panel):
    bl_label = "Quick Camera"
    bl_parent_id = "KYOKAZ_PT_ToolboxScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='CAMERA_DATA')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_CameraTools
        OBJECT_PT_CameraTools.draw(self, context)

class KYOKAZ_PT_CameraListScenePanel(bpy.types.Panel):
    bl_label = "Camera List"
    bl_parent_id = "KYOKAZ_PT_QuickCameraScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        self.layout.label(icon='OUTLINER_OB_CAMERA')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_CameraList
        OBJECT_PT_CameraList.draw(self, context)

class KYOKAZ_PT_ShotListScenePanel(bpy.types.Panel):
    bl_label = "Shot List"
    bl_parent_id = "KYOKAZ_PT_QuickCameraScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        self.layout.label(icon='VIEW_CAMERA')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_ShotList
        OBJECT_PT_ShotList.draw(self, context)

class KYOKAZ_PT_CameraInfoOverlayScenePanel(bpy.types.Panel):
    bl_label = "Camera Info Overlay"
    bl_parent_id = "KYOKAZ_PT_QuickCameraScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        try:
            preferences = context.preferences.addons[__package__].preferences
            row = layout.row(align=True)
            row.prop(preferences, "show_camera_info_overlay", text="")
            row.label(text="", icon='CAMERA_DATA')
            row.prop(preferences, "show_camera_notes", text="", icon='TEXT')
        except (KeyError, AttributeError):
            pass

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_CameraInfoOverlay
        OBJECT_PT_CameraInfoOverlay.draw(self, context)

class KYOKAZ_PT_CameraNotesScenePanel(bpy.types.Panel):
    bl_label = "Camera Notes"
    bl_parent_id = "KYOKAZ_PT_CameraListScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        try:
            preferences = context.preferences.addons[__package__].preferences
            layout.prop(preferences, "show_camera_notes", text="")
        except (KeyError, AttributeError):
            layout.label(icon='TEXT')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_CameraNotes
        OBJECT_PT_CameraNotes.draw(self, context)

class KYOKAZ_PT_ShotNotesScenePanel(bpy.types.Panel):
    bl_label = "Shot Notes"
    bl_parent_id = "KYOKAZ_PT_ShotListScenePanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        try:
            preferences = context.preferences.addons[__package__].preferences
            layout.prop(preferences, "show_camera_notes", text="")
        except (KeyError, AttributeError):
            layout.label(icon='TEXT')

    def draw(self, context):
        layout = self.layout
        # Copy the content from OBJECT_PT_ShotNotes
        OBJECT_PT_ShotNotes.draw(self, context)

classes = (
    KYOKAZ_PT_ToolboxScenePanel,
    KYOKAZ_PT_RenderToolsScenePanel,
    KYOKAZ_PT_QuickCameraScenePanel,
    KYOKAZ_PT_CameraListScenePanel,
    KYOKAZ_PT_ShotListScenePanel,
    KYOKAZ_PT_CameraInfoOverlayScenePanel,
    KYOKAZ_PT_CameraNotesScenePanel,
    KYOKAZ_PT_ShotNotesScenePanel,
    OBJECT_UL_CollectionList,
    OBJECT_PT_toggle_interpolation_panel,
    OBJECT_PT_interpolation_tools_panel,
    OBJECT_PT_bake_tools_panel,
    OBJECT_PT_RenderToolsPanel,
    OBJECT_PT_ShotList,
    OBJECT_PT_CameraList,
    OBJECT_PT_CameraTools,
    OBJECT_PT_DefaultCameraSettings,
    OBJECT_PT_ActiveCameraSettings,
    OBJECT_PT_CameraInfoOverlay,
    OBJECT_PT_Notes,
    OBJECT_PT_CameraNotes,
    OBJECT_PT_ShotNotes,
    OBJECT_OT_move_note,
    OBJECT_UL_camera_notes,
    OBJECT_UL_CameraList,
    OBJECT_UL_ShotList,
    ViewportRenderSettings,
    SnapshotSettings,
)

# Scene properties are registered in __init__.py along with the classes
# to avoid double registration issues
