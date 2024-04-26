# Kyokaz's Toolbox
Set of animation tools for Blender, originally made for my own animation project, and decided to share them here.
### (Some features might not be working properly for Blender 4.1 or above.)

# Animation Tools:
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/e3656103-cba3-4e13-b1db-1b537c0eefcd)
### Toggle Default Interpolation
Allows user to toggle the default interpolation between Constant and Bezier without going into the preference settings.
### Bake Per Steps
Allows the user to quickly Bake selected keyframe range with custom steps using [_bpy.ops.nla.bak_](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake) operator.
### Add Per Steps
Similar to Bake Per Steps, this one only adds keyframe(s) instead of replacing it.
### Delete Per Steps
Deletes keyframe with custom steps.

# Rendering Tools:
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/855e3639-b580-47ec-8f75-f79c033567da)
### Disable Render for Hidden Objects:
Automatically disables render for all hidden objects in the viewport in case you forgot to disable them manually for a render, Excluded Collection is added to prevent specific objects from being applied.

**Current known issue:**
- Hidden collection will not be applied if the objects inside still have their viewport render turned on (Working on fixing this).
- Hidden objects inside another collection in the excluded collection might not work properly resulting in hidden objects inside the custom collection still being applied even though they're in the excluded collection. To temporarily prevent this, disable the viewport render for the collection instead of the objects inside it.

## How to Install
1. Download the [latest release](https://github.com/Kyokaz/toggle_default_interpolation/releases) 
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the Python file and enable the add-on

## How to Use
The toggle button should appear on the side panel (N-Panel) in Timeline Editor, Action Editor, Graph Editor, Dope Sheet Editor, and Viewport Editor 'Item' (for Rendering Tools).
