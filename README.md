# Kyokaz's Toolbox
A set of animation tools for Blender, originally made for my own personal animation project.

Quick Overview Video:
https://www.youtube.com/watch?v=Ig7vOTFnr5c

![ezgif-5-ed39fafd2b](https://github.com/user-attachments/assets/88b79a26-b34f-48ba-9d97-dbb7c3f28efe)

# Quick Camera
Sets of new operators to add cameras based on your viewport, with a few useful features.

![image](https://github.com/user-attachments/assets/23050fdd-6200-4b63-bbdf-f47609f49353)

### Add Camera:
- Instantly add a camera based on the viewport
- An added camera will be inserted into its custom collection.
### Add Shot:
- Instantly add and bind a camera in the current frame (useful for camera switching in animation)
- An added camera will be inserted into its custom collection with custom naming conventions.
### Copy Camera & Copy Shot
- Instantly copy current active camera attributes/properties to a new camera. (Copy Shot works the same, but with the bind/marker added)
### Camera Status:
Shows useful information for each camera like frame range and total frames.

![blender_zuI8Q4WKNh](https://github.com/user-attachments/assets/74e796a3-9362-485e-8971-9dda9e7e1a40)

### Quick Pie Menu:
![blender_ZBvnQXZwms](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/5431e41d-263d-47fa-94d9-4de1251019cb)

Quickly add a new camera using the pie menu (key bind "V" by default, customizable in the Preferences setting).

### Set Preview Range
![blender_z9NF6xBQRT](https://github.com/user-attachments/assets/86ac2c1c-deb7-4db3-b98d-63e19bac43f7)

Set a preview range for a specific camera shot.

### Set Favorites

![blender_QlrWHNcDdM](https://github.com/user-attachments/assets/81385212-d520-4985-83d9-8033f8948ffb)

Set a favorite up to 8 cameras that can be accessed through the pie menu.


## Notes/Annotation Overlay
![blender_qnxi0X80ac (2)](https://github.com/user-attachments/assets/a4c92a6e-69aa-4db4-9b9a-0e7216cfefda)

Added a feature to add notes or annotations on camera/shot with the option to change font & background color and size.
(Scroll to change scale, shift+scroll to change font color,  and ctrl+scroll to change background opacity)

![blender_ksESpK2tdG (2)](https://github.com/user-attachments/assets/e59c41e1-5b61-4ac9-aaff-33979574e4ca)

Added a toggleable camera Info overlay 

# Animation Tools
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/a5fdacc8-5380-400b-986b-53476bb34082)

### Toggle Default Interpolation
Allows users to toggle the default interpolation between Constant and Bezier without going into the preference settings.
### Bake Per Steps
Allows the user to quickly Bake selected keyframe range with custom steps using [_bpy.ops.nla.bak_](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake) operator.
### Add Per Steps
Similar to Bake Per Steps, this one only adds keyframe(s) instead of replacing them.
### Delete Per Steps
Deletes keyframe with custom steps.

# Rendering Tools

![blender_gOaPnGPe4O](https://github.com/user-attachments/assets/12a2396e-86f2-4319-831d-34de4bb2b671)

### Disable Render for Hidden Objects:
Automatically disables rendering for all hidden objects in the viewport in case you forgot to disable them manually for a render. Excluded Collection is added to prevent specific objects from being applied.

### Render Preset
![image](https://github.com/user-attachments/assets/49d3eaa8-5107-4a30-8f8e-76afc1154c82)
![image](https://github.com/user-attachments/assets/ccdbc89d-c8fc-4621-8d67-4754b4dce22c)

Easily create your own preset for render settings, and import and export them as a JSON file.

### Viewport Render Animation
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/3daecc1e-fc17-465e-92c2-c79bfcd35c5a)

Viewport Render Animation is more accessible now with the option to turn on a customizable timecode and the ability to preview the video after render.

# How to Install
1. Download the [latest release](https://github.com/Kyokaz/toggle_default_interpolation/releases) 
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the Python file and enable the add-on

# How to Use
Most of the toolset can be found in the side panel or in Scene Properties, anything animation related can be found in animation related panel (Timeline, Dope Sheet, Graph Editor)
Quick Camera and Render Tools can be found in the Toolbox Panel (Can be turned off) or in Scene Properties.

To change keybind or default camera settings, go to Addon Preferences.

## Disclaimer
This code was written with the assistance of Claude as I mostly handle a lot of the UI stuff. I'm not fully familiar with Python coding yet, as I'm still learning, so if you have any suggestions on how to make this better, please let me know!
