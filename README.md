# Kyokaz's Toolbox
Set of animation tools for Blender, originally made for my own animation project, decided to share them here.
### (Some features might not be working properly for Blender 4.1 or above.)

## Current Main Features:
### Toggle Default Interpolation
Allows user to toggle the default interpolation between Constant and Bezier without going into the preference settings.
### Bake Per Steps
Allows user to quickly Bake selected keyframe range with custom steps using [_bpy.ops.nla.bak_](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake) operator.
### Add Per Steps
Similar to Bake Per Steps, this one only adds keyframe(s) instead of replacing it.
### Delete Per Steps
Deletes keyframe with custom steps.

## How to Install
1. Download the [latest release](https://github.com/Kyokaz/toggle_default_interpolation/releases) 
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the Python file and enable the add-on

## How to Use
The toggle button should appear on the side panel (N-Panel) in Timeline Editor, Action Editor, Graph Editor, and Dope Sheet Editor.
