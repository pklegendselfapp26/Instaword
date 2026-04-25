[app]
title = Insta Word
package.name = instaword
package.domain = org.yourname
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,wav,mp3
version = 0.1

# 🟢 THE FIX: Removed plyer and pyjnius to stop the Android 16 bridge crash
requirements = python3, kivy==2.3.0, kivymd==1.1.1, pillow

orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.permissions = INTERNET, WAKE_LOCK

# 🟢 TARGETING ANDROID 16 STANDARDS
android.api = 34
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1

