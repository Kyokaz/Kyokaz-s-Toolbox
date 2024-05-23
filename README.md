# Kyokaz's Toolbox 2.4.5
Set of animation tools for Blender, originally made for my own animation project, and decided to share them here.

# Animation Tools
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/e3656103-cba3-4e13-b1db-1b537c0eefcd)
### Toggle Default Interpolation
Allows user to toggle the default interpolation between Constant and Bezier without going into the preference settings.
### Bake Per Steps
Allows the user to quickly Bake selected keyframe range with custom steps using [_bpy.ops.nla.bak_](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake) operator.
### Add Per Steps
Similar to Bake Per Steps, this one only adds keyframe(s) instead of replacing it.
### Delete Per Steps
Deletes keyframe with custom steps.

# Rendering Tools
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/855e3639-b580-47ec-8f75-f79c033567da)
### Disable Render for Hidden Objects:
Automatically disables render for all hidden objects in the viewport in case you forgot to disable them manually for a render, Excluded Collection is added to prevent specific objects from being applied.

**Current known issue:**
- Hidden collection will not be applied if the objects inside still have their viewport render turned on (Working on fixing this).
- Hidden objects inside another collection in the excluded collection might not work properly resulting in hidden objects inside the custom collection still being applied even though they're in the excluded collection. To temporarily prevent this, disable the viewport render for the collection instead of the objects inside it.

# Quick Camera
Sets of new operators to add cameras based on your viewport with few useful features.

![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/8a14d063-a1dd-4146-92e1-bb3fd6d2ce93)

### Add Camera:
- Instantly add a camera based on the viewport
- An added camera will be inserted into its corresponding collection.
### Add Shot:
- Instantly add and bind a camera in the current frame (useful for camera switching in animation)
- An added camera will be inserted into its corresponding collection with different naming conventions.
### Copy Camera & Copy Shot
- Instantly copy current active camera attributes/properties to a new camera. (Copy Shot works the same but with the bind/marker added)
### Camera Status:
Shows useful information for each camera like frame range and total frames.
### Quick Pie Menu:
![blender_ZBvnQXZwms](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/5431e41d-263d-47fa-94d9-4de1251019cb)

### Set Preview Range
![CameraUpdate_preview](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/5e18ce2e-ed02-4ba8-a277-e21be84b36d3)

Set a preview range for a specific camera shot.

Quickly add a new camera using the pie menu (key bind "V" by default, customizable in the Preferences setting).
### Viewport Render Animation
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/3daecc1e-fc17-465e-92c2-c79bfcd35c5a)

Viewport Render Animation is more accessible now with the option to turn on a customizable timecode, and the ability to preview the video after render.


## Known Issues:
- There might be some issues with how the add camera button works as it might require you to view the current active camera before adding the next one. (This should be already be fixed, but something to keep in mind)
- If you receive an error when updating the addon, make sure to disable and remove the addon in the preference setting, restart Blender, and install the addon again.

# How to Install
1. Download the [latest release](https://github.com/Kyokaz/toggle_default_interpolation/releases) 
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the Python file and enable the add-on

# How to Use
The toggle button should appear on the side panel (N-Panel) in Timeline Editor, Action Editor, Graph Editor, Dope Sheet Editor, and Viewport Editor 'Tool' Panel.

## Disclaimer
This code was written with the help of ChatGPT, I'm not fully familiar with Python coding yet (planning to learn more once I graduate), so if you have any suggestions on how to make this better, please let me know!
