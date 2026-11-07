[app]

# 应用标题（显示在手机桌面/标题栏）
title = 工作笔记

# 包名（全球唯一，不要改，除非发布到应用商店）
package.name = worknotes
package.domain = com.example

# 源码目录与入口
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,json,atxt
source.include_patterns = fonts/*.ttf

# 版本号
version = 1.0

# 应用依赖（p4a 会自动拉取对应安卓 recipe）
requirements = python3,kivy==2.3.0,android

# 竖屏即可（也可改成 landscape）
orientation = portrait

# 权限：本应用全部数据本地存储，无需任何权限。
# 默认不申请权限，Android 13+ 也能正常安装。
android.permissions = 

# 只构建 arm64 + armeabi（覆盖 99% 的新手机，包体更小）
android.archs = arm64-v8a, armeabi-v7a

# 官方 release 包，可安装；debug 包签名不同，别混装
android.release_artifact = apk

# 全屏 + 沉浸式
fullscreen = 0

# 后台/退出行为
android.wakelock = False

# 若不希望标题栏被系统栏遮挡，可保留默认
android.statusbar_color = #F5F5F5

# 图标（可后续替换 assets/icon.png）
# icon.filename = %(source.dir)s/assets/icon.png
# presplash.filename = %(source.dir)s/assets/presplash.png

# 中文字体必须打进 APK，否则安卓上中文会变方块
android.add_fonts = fonts/simhei.ttf

# 不裁剪 Python（避免某些安卓版本的动态库问题）
android.no-byte-compile-python = False

# 允许外部存储（「导出备份」功能用）
android.write_external_storage = True

[buildozer]

# 日志级别
log_level = 2
warn_on_root = 1

# 打包时的输出目录
bin_dir = ./bin

# ----------------------------------------------------------------------
# p4a（python-for-android）配置
# ----------------------------------------------------------------------
[app:android]

# Android SDK 组件版本（与 p4a 1.0.7 匹配）
android.api = 34
android.minapi = 21
android.ndk = 25b
android.sdk = 24

# 使用 bootstrap=SDL2（Kivy 官方默认）
android.bootstrap = sdl2

# 编译架构（必须与上面 archs 一致）
android.arch = arm64-v8a

# 退出时不要立刻杀进程（避免闪退误判）
android.allow_backup = True

# ----------------------------------------------------------------------
# 说明：
#   - buildozer.spec 中的 [app] 段是标准配置；本文件额外保留了 [app] 顶部的
#     常用设置。若 buildozer 版本有差异，报错时优先检查
#     android.ndk / android.sdk / requirements 三行。
#   - 字体文件位于 ./fonts/simhei.ttf，已通过 android.add_fonts 打包。
# ----------------------------------------------------------------------
