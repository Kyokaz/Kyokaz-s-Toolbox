# Kyokaz's Toolbox
A set of animation tools for Blender was originally made for my own animation project, and decided to share them here.

# Animation Tools
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/a5fdacc8-5380-400b-986b-53476bb34082)

### Toggle Default Interpolation
Allows users to toggle the default interpolation between Constant and Bezier without going into the preference settings.
### Bake Per Steps
Allows the user to quickly Bake selected keyframe range with custom steps using [_bpy.ops.nla.bak_](https://docs.blender.org/api/current/bpy.ops.nla.html#bpy.ops.nla.bake) operator.
### Add Per Steps
Similar to Bake Per Steps, this one only adds keyframe(s) instead of replacing it.
### Delete Per Steps
Deletes keyframe with custom steps.

# Rendering Tools

![blender_gOaPnGPe4O](https://github.com/user-attachments/assets/12a2396e-86f2-4319-831d-34de4bb2b671)

### Disable Render for Hidden Objects:
Automatically disables render for all hidden objects in the viewport in case you forgot to disable them manually for a render, Excluded Collection is added to prevent specific objects from being applied.

**Current known issue:**
- Hidden collection will not be applied if the objects inside still have their viewport render turned on (Working on fixing this).
- Hidden objects inside another collection in the excluded collection might not work properly resulting in hidden objects inside the custom collection still being applied even though they're in the excluded collection. To temporarily prevent this, disable the viewport render for the collection instead of the objects inside it.

# Quick Camera
Sets of new operators to add cameras based on your viewport with few useful features.

![image](https://github.com/user-attachments/assets/23050fdd-6200-4b63-bbdf-f47609f49353)

### Add Camera:
- Instantly add a camera based on the viewport
- An added camera will be inserted into its custom collection.
### Add Shot:
- Instantly add and bind a camera in the current frame (useful for camera switching in animation)
- Am added camera will be inserted into its custom collection with custom naming conventions.
### Copy Camera & Copy Shot
- Instantly copy current active camera attributes/properties to a new camera. (Copy Shot works the same but with the bind/marker added)
### Camera Status:
Shows useful information for each camera like frame range and total frames.

![blender_zuI8Q4WKNh](https://github.com/user-attachments/assets/74e796a3-9362-485e-8971-9dda9e7e1a40)

### Quick Pie Menu:
![blender_ZBvnQXZwms](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/5431e41d-263d-47fa-94d9-4de1251019cb)

### Set Preview Range
![blender_z9NF6xBQRT](https://github.com/user-attachments/assets/86ac2c1c-deb7-4db3-b98d-63e19bac43f7)

Set a preview range for a specific camera shot.

Quickly add a new camera using the pie menu (key bind "V" by default, customizable in the Preferences setting).
### Viewport Render Animation
![image](https://github.com/Kyokaz/Kyokaz-s-Toolbox/assets/84836314/3daecc1e-fc17-465e-92c2-c79bfcd35c5a)

Viewport Render Animation is more accessible now with the option to turn on a customizable timecode, and the ability to preview the video after render.


## Known Issues:
- Both "Remove All Shot" and "Remove All Cameras" seem to remove every camera in the current collection whether they're marked as a Shot or not.
- If you received an error when updating the addon, make sure to disable and remove the addon in the preference setting, restart Blender, and install the addon again.
  This seems to be an issue with how the addon handles class register.

# How to Install
1. Download the [latest release](https://github.com/Kyokaz/toggle_default_interpolation/releases) 
2. In Blender, go to Edit > Preferences > Add-ons > Install
3. Select the Python file and enable the add-on

# How to Use
The toggle button should appear on the side panel (N-Panel) in Timeline Editor, Action Editor, Graph Editor, Dope Sheet Editor, and Viewport Editor 'Toolbox' Panel.
Animation Tools can be found in animation related quick panels (Timeline Editor, Action Editor, Graph Editor, Dope Sheet Editor).
Quick Camera and Render Tools can be found in Toolbox Panel (Can be turned off) or in Scene Properties. 

## Disclaimer
This code was written with the help of Claude.AI, I'm not fully familiar with Python coding yet (planning to learn more once I graduate), so if you have any suggestions on how to make this better, please let me know!
