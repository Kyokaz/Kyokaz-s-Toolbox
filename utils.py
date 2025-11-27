# utils.py
import os
import tempfile
from datetime import datetime
import bpy
import re

def ensure_output_directory(directory):
    """
    Ensure the output directory exists, creating it if necessary.
    Returns the absolute path to the directory.
    Raises OSError if directory cannot be created.
    """
    try:
        output_dir = bpy.path.abspath(directory) if directory else tempfile.gettempdir()
        # Normalize the path
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    except (OSError, PermissionError) as e:
        raise OSError(f"Failed to create output directory '{output_dir}': {str(e)}")

def sanitize_filename(filename):
    """
    Sanitize a filename to prevent path traversal attacks and invalid characters.
    Returns a safe filename.
    """
    # Remove path separators and dangerous characters
    # Allow alphanumeric, spaces, hyphens, underscores, and periods
    sanitized = re.sub(r'[^\w\s\-.]', '', filename)
    # Remove leading/trailing whitespace and periods
    sanitized = sanitized.strip('. ')
    # Prevent empty filenames
    if not sanitized:
        sanitized = "untitled"
    # Limit length to reasonable size
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized

def generate_output_filename(directory, suffix="output"):
    """
    Generate a safe output filename with timestamp.
    Returns the full path to the output file.
    """
    blend_name = os.path.splitext(bpy.path.basename(bpy.data.filepath))[0] or "untitled"
    # Sanitize the blend file name to prevent path traversal
    safe_blend_name = sanitize_filename(blend_name)
    safe_suffix = sanitize_filename(suffix)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, f"{safe_blend_name}_{safe_suffix}_{timestamp}.png")

def report_error(operator, message):
    operator.report({'ERROR'}, message)
    print(f"ERROR: {message}")

# rendertoolsprop

def draw_property(layout, data, property_name, label, icon=None):
    """
    Draw a property with an optional icon in a consistent style.
    """
    row = layout.row()
    if icon:
        row.prop(data, property_name, text=label, icon=icon)
    else:
        row.prop(data, property_name, text=label)

def draw_operator(layout, operator_id, label, icon=None):
    """
    Draw an operator button with an optional icon.
    """
    row = layout.row()
    if icon:
        row.operator(operator_id, text=label, icon=icon)
    else:
        row.operator(operator_id, text=label)

# get active collection

def get_active_collection(context, operator):
    """
    Retrieve the active collection from the scene. If none is found, report a warning.
    Returns the active collection or None if not found.
    """
    active_collection = context.scene.custom_name_props.get_active_collection(context)
    if not active_collection:
        operator.report({'WARNING'}, "No active collection found. Please select or create a collection.")
    return active_collection

