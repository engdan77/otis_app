otis_app
==============

Background
--------------

This is a graphical App for Apple IOS, Android (but also native MacOSX and Windows) for accessing sensors registered by otis_service Server, developed in Python using Kivy-framework.
Main purpose was initially to get to know how you could use Python for Mobile application development where TCP/JSON would be used for communication between server and client.


Requirements
--------------

* Server running edoAutoHome (a RaspberryPi with sensors and software developed in Python), all details found at https://github.com/engdan77/edoautohome
* Client hardware, currently tested on iPhone5 IOS 8.1 and Mac OSX 10.9. But packages been built for Android 4.x and Windows 7 (and later) been built.


----------------------
Installation
----------------------

To save some trouble of compiling/packaging from the source properly I've done this for you. So all you have to do is to follow the below instructions.

#### Apple iPhone/iPad device

Since I've not (yet) purchased any license for this app is currently packaged into a 'ad-hoc' license mode which means you have to transfer/install it manually to a "jailbroken" device.

1. Assure your IOS-device is jailbroken (google "jailbreaka iphone") that usually comes with Cydia and the package AppSync (but if not, check in Cydia that this packag is installed)

2. On your Mac/Windows install a software that allows you to install .ipa package to your device such as the freeware iFunBox (google "iFunBox"

3. Download otis_app IOS-package from https://github.com/engdan77/otis_app/raw/master/compiled_packages/ios/autohomemobile.ipa

4. From iFunBox: Select your device, User Applications, Install App, select the downloaded package

5. Voila !!


#### Android

1. On the Android device go to Settings -> Applications -> Unknown sources to Enable

2. Transfer this apk-package to your memory card, or download directly to your phone - https://github.com/engdan77/otis_app/raw/master/compiled_packages/android/autohomemobile.apk

3. Use "My File" (if it exists) or download file explorer such as "EZ Explorer" from App store to browse to the apk-package and run it


#### Mac OS X

1. Download this dmg-image and open it - https://github.com/engdan77/otis_app/raw/master/compiled_packages/mac_os_x/autohomemobile.dmg

2. Drag-and-drop the "otis_app" icon to your Applications in Finder


#### Windows

1. Download the Windows package - https://github.com/engdan77/otis_app/raw/master/compiled_packages/windows/autohomemobile.zip

2. Unzip the archive, and run otis_app.exe


-------------------------
Run from Source
-------------------------

Download Kivy Framework from http://kivy.org, and execute main.py from Kivy.

-------------------------
Video
-------------------------
Video-clip of this application running on iPhone5/ios 8.4
[![otis_app on Youtube](https://github.com/engdan77/otis_app/blob/master/pics/youtube.png)](https://www.youtube.com/watch?v=Zn4ydA_KHYc "otis_app on Youtube - Click to Watch!")

-------------------------
Pictures
-------------------------

_*Mobile Version*_

![screen1](https://github.com/engdan77/otis_app/blob/master/pics/otis_app_sensors_01.jpg)![screen2](https://github.com/engdan77/otis_app/blob/master/pics/otis_app_sensors_02.jpg)![screen3](https://github.com/engdan77/otis_app/blob/master/pics/otis_app_sensors_03.jpg)

_*Desktop Version*_

![desktop_versions](https://github.com/engdan77/otis_app/blob/master/pics/desktop_versions.png)
