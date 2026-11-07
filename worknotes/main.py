# -*- coding: utf-8 -*-
"""
Kivy 笔记应用（Android 版）—— 多板块 + 自定义板块 + 全局搜索
================================================================
给日常维修/操作笔记用的小工具：

  1. 左侧是「板块」列表，默认三个板块：
        医院 HIS 系统操作 / 打印机维修 / 总结笔记
     用户可以随时 新建板块、重命名、删除板块。
  2. 右侧是笔记列表 + 编辑区，一段一条笔记（问题提示词 → 操作步骤）。
  3. 顶部是全局搜索框，可按关键词跨板块搜索，也可限定某个板块内搜索。
  4. 全部数据用 JsonStore 存在 JSON 文件中，重启不丢，可备份迁移。
  5. 内置中文字体处理：安卓上若系统无可用中文字体，则回退到打包的思源宋体。

运行（桌面调试）:  python main.py
打包安卓 APK  :  见 buildozer.spec / .github/workflows/build-apk.yml
"""

# ----------------------------------------------------------------------
# 标准库
# ----------------------------------------------------------------------
import os
import sys
import traceback
from datetime import datetime

# ----------------------------------------------------------------------
# Kivy 导入（与上一版保持风格）
# ----------------------------------------------------------------------
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform

# ----------------------------------------------------------------------
# 常量
# ----------------------------------------------------------------------
APP_NAME = "worknotes"
PKG = "com.example.worknotes"
APP_VERSION = "1.0"

DEFAULT_BOARDS = [
    {"id": "b_his", "name": "医院HIS系统操作"},
    {"id": "b_printer", "name": "打印机维修"},
    {"id": "b_summary", "name": "总结笔记"},
]

# 安卓上想确保中文显示，就把 .ttf 放进项目 fonts 目录并在 buildozer.spec 里 include
FONT_CANDIDATES = [
    "fonts/simhei.ttf",       # 打包进 APK 的思源/黑体（推荐）
    "simhei.ttf",
    "Deng.ttf",
    "NotoSansCJKsc-Regular.otf",
    "NotoSerifCJKsc-Regular.otf",
    "SourceHanSansSC-Regular.otf",
]
FALLBACK_FONT = "Roboto"   # 实在找不到字体时用它（安卓系统通常自带中文字体）

# ----------------------------------------------------------------------
# 中文字体处理（安卓不内置中文字体，必须打包）
# ----------------------------------------------------------------------
def _find_cjk_font():
    """在应用目录里找一个可用的中文字体；找不到返回 None。"""
    search_dirs = []
    if getattr(sys, "frozen", False):
        search_dirs.append(os.path.dirname(sys.executable))
    try:
        search_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    search_dirs.append(os.getcwd())
    search_dirs.append("/sdcard")

    for d in search_dirs:
        for name in FONT_CANDIDATES:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    # 也找项目里的 fonts 子目录
    for d in search_dirs:
        fd = os.path.join(d, "fonts")
        if os.path.isdir(fd):
            for name in FONT_CANDIDATES:
                p = os.path.join(fd, name)
                if os.path.isfile(p):
                    return p
    return None


def setup_fonts():
    """注册应用级字体名，返回 (font_name, font_path)。"""
    try:
        p = _find_cjk_font()
        if p:
            from kivy.core.text import LabelBase
            LabelBase.register("CJK", p)
            try:
                LabelBase.register("CJK_BOLD", p)
            except Exception:
                pass
            return "CJK", p
        # 尝试系统里常见的安卓中文字体
        for sp in FONT_CANDIDATES:
            try:
                from kivy.core.text import LabelBase
                LabelBase.register("CJK", sp)
                return "CJK", sp
            except Exception:
                continue
    except Exception:
        traceback.print_exc()
    return FALLBACK_FONT, None


FONT_NAME, FONT_PATH = setup_fonts()

# ----------------------------------------------------------------------
# 数据文件路径（安卓 / 桌面通用）
# ----------------------------------------------------------------------
def _data_file_path():
    if platform == "android":
        from android.storage import app_storage_path  # noqa
        base = app_storage_path()
    else:
        try:
            base = App.get_running_app().user_data_dir
        except Exception:
            base = os.path.join(os.path.expanduser("~"), "." + APP_NAME)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "notes_data.json")


# ----------------------------------------------------------------------
# 界面（KV 字符串）
# ----------------------------------------------------------------------
Builder.load_string('''
#:import utils kivy.utils

<BoardTab@AccordionItem>

<MainScreen>:
    orientation: 'horizontal'
    padding: dp(4)
    spacing: dp(4)
    canvas.before:
        Color:
            rgba: 0.97, 0.97, 0.98, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # ================= 左栏：板块 =================
    BoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.28
        padding: dp(6)
        spacing: dp(6)

        Label:
            text: '笔记板块'
            size_hint_y: None
            height: dp(34)
            font_name: app.font_name
            font_size: dp(16)
            bold: True
            color: 0.15, 0.15, 0.18, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.size

        ScrollView:
            size_hint_y: 1
            bar_width: dp(4)
            BoxLayout:
                id: board_box
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(4)

        Button:
            text: '＋ 新建板块'
            size_hint_y: None
            height: dp(44)
            font_name: app.font_name
            font_size: dp(14)
            background_normal: ''
            background_color: 0.16, 0.55, 0.36, 1
            color: 1, 1, 1, 1
            on_release: root.ask_new_board()

    # ================= 右栏：笔记 =================
    BoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.72
        padding: dp(6)
        spacing: dp(6)

        # ---- 标题 ----
        Label:
            id: board_title
            text: '请选择一个板块'
            size_hint_y: None
            height: dp(36)
            font_name: app.font_name
            font_size: dp(17)
            bold: True
            color: 0.12, 0.12, 0.15, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.size

        # ---- 工具栏：搜索 + 添加 ----
        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(6)

            TextInput:
                id: search_box
                hint_text: '🔍 搜索提示词 / 解决办法 / 全部板块…'
                size_hint_x: 0.62
                multiline: False
                font_name: app.font_name
                font_size: dp(14)
                write_tab: False
                background_color: 1, 1, 1, 1
                foreground_color: 0.1, 0.1, 0.12, 1
                cursor_color: 0.2, 0.4, 0.7, 1
                hint_text_color: 0.55, 0.55, 0.6, 1
                padding_y: dp(9)
                on_text_validate: root.focus_next()
                on_text: root.apply_filter()

            Button:
                text: '全局'
                size_hint_x: 0.18
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: (0.20, 0.45, 0.75, 1) if root.search_scope == 'all' else (0.72, 0.74, 0.78, 1)
                color: 1, 1, 1, 1 if root.search_scope == 'all' else (0.25, 0.27, 0.3, 1)
                on_release: root.scope_all()

            Button:
                text: '本板块'
                size_hint_x: 0.20
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: (0.20, 0.45, 0.75, 1) if root.search_scope == 'board' else (0.72, 0.74, 0.78, 1)
                color: 1, 1, 1, 1 if root.search_scope == 'board' else (0.25, 0.27, 0.3, 1)
                on_release: root.scope_board()

        # ---- 笔记列表 ----
        RecycleView:
            id: rv
            viewclass: 'NoteRow'
            effect_cls: 'ScrollEffect'
            bar_width: dp(4)
            bar_color: 0.3, 0.45, 0.7, 0.5
            RecycleBoxLayout:
                default_size: None, dp(92)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(4)

        Label:
            id: stats_label
            text: root.stats_text
            size_hint_y: None
            height: dp(24)
            font_name: app.font_name
            font_size: dp(12)
            color: 0.45, 0.48, 0.52, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.size

        # ---- 操作按钮 ----
        BoxLayout:
            size_hint_y: None
            height: dp(44)
            spacing: dp(6)

            Button:
                text: '＋ 新建笔记'
                size_hint_x: 0.34
                font_name: app.font_name
                font_size: dp(14)
                background_normal: ''
                background_color: 0.16, 0.55, 0.36, 1
                color: 1, 1, 1, 1
                bold: True
                on_release: root.open_editor(None)

            Button:
                text: '删除板块'
                size_hint_x: 0.33
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: 0.78, 0.32, 0.30, 1
                color: 1, 1, 1, 1
                on_release: root.ask_delete_board()

            Button:
                text: '导出备份'
                size_hint_x: 0.33
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: 0.35, 0.40, 0.50, 1
                color: 1, 1, 1, 1
                on_release: root.export_data()

''')


# ----------------------------------------------------------------------
# 列表行
# ----------------------------------------------------------------------
class NoteRow(RecycleDataViewBehavior, BoxLayout):
    root = ObjectProperty()
    index = None

    selected = BooleanProperty(False)
    title_text = StringProperty("")
    preview_text = StringProperty("")
    meta_text = StringProperty("")
    note_id = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.note_id = data.get("note_id", "")
        self.title_text = data.get("title_text", "")
        self.preview_text = data.get("preview_text", "")
        self.meta_text = data.get("meta_text", "")
        self.selected = data.get("selected", False)
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if self.root and self.collide_point(*touch.pos):
            self.root.select_row(self.index)
        return super().on_touch_down(touch)

    def edit_note(self):
        if self.root and self.note_id:
            self.root.open_editor(self.note_id)

    def delete_note(self):
        if self.root and self.note_id:
            self.root.confirm_delete_note(self.note_id)


Builder.load_string('''
<NoteRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(92)
    padding: dp(8)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: (0.88, 0.93, 1.0, 1) if self.selected else (1, 1, 1, 1)
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: 0.82, 0.85, 0.88, 1
        Line:
            rectangle: self.x, self.y, self.width, self.height

    BoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.66
        spacing: dp(2)

        Label:
            text: root.title_text
            size_hint_y: 0.46
            font_name: app.font_name
            font_size: dp(15)
            bold: True
            color: 0.12, 0.12, 0.16, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None
            shorten: True
            shorten_from: 'right'

        Label:
            text: root.preview_text
            size_hint_y: 0.54
            font_name: app.font_name
            font_size: dp(13)
            color: 0.40, 0.42, 0.46, 1
            halign: 'left'
            valign: 'top'
            text_size: self.width, None
            shorten: True
            shorten_from: 'right'

    BoxLayout:
        orientation: 'vertical'
        size_hint_x: 0.30
        spacing: dp(4)
        padding: dp(2)

        Label:
            text: root.meta_text
            size_hint_y: None
            height: dp(20)
            font_name: app.font_name
            font_size: dp(11)
            color: 0.52, 0.55, 0.60, 1
            halign: 'right'
            valign: 'middle'
            text_size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(32)
            spacing: dp(4)

            Button:
                text: '打开'
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: 0.20, 0.45, 0.75, 1
                color: 1, 1, 1, 1
                on_release: root.edit_note()

            Button:
                text: '删'
                size_hint_x: None
                width: dp(40)
                font_name: app.font_name
                font_size: dp(13)
                background_normal: ''
                background_color: 0.78, 0.32, 0.30, 1
                color: 1, 1, 1, 1
                on_release: root.delete_note()
''')


# ----------------------------------------------------------------------
# 主界面
# ----------------------------------------------------------------------
class MainScreen(BoxLayout):
    boards = ListProperty([])
    notes = ListProperty([])
    raw_notes = ListProperty([])
    visible_rows = ListProperty([])

    search_scope = StringProperty("all")     # all | board
    current_board = StringProperty("")
    stats_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.path = _data_file_path()
        self.store = JsonStore(self.path)
        self.load_all()
        # 默认选中第一个板块
        if self.boards:
            self.set_current_board(self.boards[0]["id"], from_init=True)
        self.bind(boards=self._rebuild_board_buttons)
        self._rebuild_board_buttons()

    # ---------------- 持久化 ----------------
    def load_all(self):
        # 板块
        if self.store.exists("boards"):
            self.boards = list(self.store.get("boards")["items"])
        else:
            self.boards = [dict(b) for b in DEFAULT_BOARDS]
        # 笔记
        self.notes = []
        try:
            keys = self.store.keys()
        except Exception:
            keys = []
        for k in keys:
            if not k.startswith("n_"):
                continue
            try:
                item = dict(self.store.get(k))
            except Exception:
                continue
            item.setdefault("id", k)
            self.notes.append(item)
        self._sort_notes()

    def save_boards(self):
        self.store.put("boards", items=list(self.boards))

    def save_note(self, note):
        """单条保存/覆盖（高效，避免全量重写）"""
        self.store.put(note["id"], **note)

    def delete_note_store(self, note_id):
        if self.store.exists(note_id):
            self.store.delete(note_id)

    def _sort_notes(self):
        self.notes.sort(key=lambda n: (not n.get("pinned", False), n.get("created", "")),
                        reverse=True)

    # ---------------- 板块按钮 ----------------
    def _rebuild_board_buttons(self, *a):
        box = self.ids.board_box
        box.clear_widgets()

        all_btn = Button(
            text="📚 全部笔记",
            size_hint_y=None, height=dp(44),
            font_name=App.get_running_app().font_name,
            font_size=dp(14),
            background_normal="",
            background_color=(0.30, 0.42, 0.62, 1) if self.current_board == "__all__"
                             else (0.42, 0.46, 0.54, 1),
            color=(1, 1, 1, 1),
        )
        all_btn.bind(on_release=lambda *x: self.set_current_board("__all__"))
        box.add_widget(all_btn)

        for b in self.boards:
            bid = b["id"]
            name = b["name"]
            active = (self.current_board == bid)
            btn = Button(
                text="%s%s（%d）" % ("📌 " if active else "", name,
                                    sum(1 for n in self.notes if n.get("board") == bid)),
                size_hint_y=None, height=dp(44),
                font_name=App.get_running_app().font_name,
                font_size=dp(14),
                halign="left", valign="middle",
                padding_x=dp(10),
                shorten=True, shorten_from="right",
                background_normal="",
                background_color=(0.20, 0.45, 0.75, 1) if active
                                 else (0.92, 0.93, 0.95, 1),
                color=(1, 1, 1, 1) if active else (0.18, 0.20, 0.24, 1),
            )
            btn.bind(on_release=lambda inst, bid=bid: self.set_current_board(bid))
            # 长按重命名
            btn.bind(on_long_press=lambda inst, bid=bid: self.ask_rename_board(bid))
            box.add_widget(btn)

    def set_current_board(self, board_id, from_init=False):
        self.current_board = board_id
        if board_id == "__all__":
            self.ids.board_title.text = "📚 全部笔记（跨板块）"
            self.search_scope = "all"
        else:
            name = next((b["name"] for b in self.boards if b["id"] == board_id), "?")
            self.ids.board_title.text = "📂 " + name
            self.search_scope = "board"
        self._rebuild_board_buttons()
        self.apply_filter()

    # ---------------- 搜索 / 过滤 ----------------
    def scope_all(self):
        self.search_scope = "all"
        self.apply_filter()

    def scope_board(self):
        self.search_scope = "board"
        self.apply_filter()

    def apply_filter(self):
        kw = self.ids.search_box.text.strip().lower()
        pool = self.notes

        if self.search_scope == "board" and self.current_board not in ("", "__all__"):
            pool = [n for n in self.notes if n.get("board") == self.current_board]

        if kw:
            # 按关键词匹配，标题权重更高（前缀匹配优先）
            exact, partial = [], []
            for n in pool:
                title = (n.get("title", "") or "").lower()
                text = (n.get("text", "") or "").lower()
                tags = (n.get("tags", "") or "").lower()
                hay = title + "\n" + text + "\n" + tags
                if kw in title:
                    exact.append(n)
                elif kw in hay:
                    partial.append(n)
            result = exact + partial
        else:
            result = list(pool)

        self._sort_notes()
        rows = []
        for n in result:
            content = (n.get("text", "") or "").replace("\n", " ")
            preview = (content[:46] + "…") if len(content) > 46 else (content or "（空）")
            bname = next((b["name"] for b in self.boards
                          if b["id"] == n.get("board")), "未分类")
            rows.append({
                "note_id": n["id"],
                "title_text": n.get("title", "") or "（无标题）",
                "preview_text": preview,
                "meta_text": "%s · %s" % (bname, n.get("updated", n.get("created", ""))[:16]),
                "selected": False,
            })
        self.ids.rv.data = rows
        self.raw_notes = result
        self.visible_rows = rows

        if kw:
            self.stats_text = "找到 %d 条（关键词：%s，范围：%s）" % (
                len(result), kw, "全部板块" if self.search_scope == "all" else "当前板块")
        else:
            self.stats_text = "当前范围共 %d 条笔记" % len(result)

    def select_row(self, index):
        data = self.ids.rv.data
        for i, row in enumerate(data):
            row["selected"] = (i == index)
        self.ids.rv.refresh_from_data()

    def focus_next(self):
        self.ids.rv.focus = True

    # ---------------- 笔记增删改 ----------------
    def open_editor(self, note_id=None):
        editing = note_id is not None
        note = next((n for n in self.notes if n["id"] == note_id), None) if editing else None

        target_board = note.get("board") if note else (
            self.current_board if self.current_board != "__all__"
            else (self.boards[0]["id"] if self.boards else ""))

        popup = Popup(
            title="编辑笔记" if editing else "新建笔记",
            size_hint=(0.94, 0.92),
            auto_dismiss=False,
            title_size=dp(17),
            title_font=App.get_running_app().font_name,
            separator_color=(0.20, 0.45, 0.75, 1),
        )
        popup.background = ""
        popup.background_color = (0.96, 0.96, 0.97, 1)

        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        # 板块选择
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        top.add_widget(Label(text="板块：", size_hint_x=None, width=dp(48),
                             font_name=App.get_running_app().font_name,
                             font_size=dp(14), color=(0.15, 0.15, 0.18, 1),
                             halign="left", valign="middle", text_size=self.size))
        board_values = [b["name"] for b in self.boards]
        board_ids = [b["id"] for b in self.boards]
        sp = Spinner(
            text=next((b["name"] for b in self.boards if b["id"] == target_board),
                      board_values[0] if board_values else ""),
            values=board_values,
            size_hint_x=0.55,
            font_name=App.get_running_app().font_name,
            font_size=dp(14),
            background_color=(0.90, 0.91, 0.94, 1),
            color=(0.12, 0.12, 0.15, 1),
        )
        top.add_widget(sp)
        top.add_widget(Label(text="置顶" if note and note.get("pinned") else "",
                             size_hint_x=None, width=dp(50),
                             font_name=App.get_running_app().font_name,
                             font_size=dp(12), color=(0.6, 0.6, 0.6, 1)))
        root.add_widget(top)

        # 提示词（标题）
        title_input = TextInput(
            text=note.get("title", "") if note else "",
            hint_text="提示词 / 问题现象（如：HIS登录提示密码错误）",
            size_hint_y=None, height=dp(50),
            multiline=False,
            font_name=App.get_running_app().font_name, font_size=dp(15),
            background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.12, 1),
            cursor_color=(0.2, 0.4, 0.7, 1), hint_text_color=(0.6, 0.6, 0.65, 1),
            padding_y=dp(12),
        )
        root.add_widget(title_input)

        # 标签
        tag_input = TextInput(
            text=note.get("tags", "") if note else "",
            hint_text="标签（可选，用空格分隔，如：his 登录 报错）",
            size_hint_y=None, height=dp(44),
            multiline=False,
            font_name=App.get_running_app().font_name, font_size=dp(14),
            background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.12, 1),
            cursor_color=(0.2, 0.4, 0.7, 1), hint_text_color=(0.6, 0.6, 0.65, 1),
            padding_y=dp(10),
        )
        root.add_widget(tag_input)

        # 正文
        body_input = TextInput(
            text=note.get("text", "") if note else "",
            hint_text="操作步骤 / 维修办法（可多行）…",
            size_hint_y=1,
            font_name=App.get_running_app().font_name, font_size=dp(15),
            background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.12, 1),
            cursor_color=(0.2, 0.4, 0.7, 1), hint_text_color=(0.6, 0.6, 0.65, 1),
            padding=dp(10),
        )
        root.add_widget(body_input)

        # 按钮
        btns = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        b_save = Button(text="保存", font_name=App.get_running_app().font_name,
                        font_size=dp(15), bold=True,
                        background_normal="", background_color=(0.16, 0.55, 0.36, 1),
                        color=(1, 1, 1, 1))
        b_cancel = Button(text="取消", font_name=App.get_running_app().font_name,
                          font_size=dp(15),
                          background_normal="", background_color=(0.72, 0.74, 0.78, 1),
                          color=(0.2, 0.2, 0.24, 1))
        b_pin = Button(text=("取消置顶" if note and note.get("pinned") else "置顶"),
                       size_hint_x=None, width=dp(80),
                       font_name=App.get_running_app().font_name, font_size=dp(14),
                       background_normal="",
                       background_color=(0.85, 0.60, 0.20, 1) if not (note and note.get("pinned"))
                                        else (0.72, 0.74, 0.78, 1),
                       color=(1, 1, 1, 1))
        btns.add_widget(b_save)
        btns.add_widget(b_pin)
        btns.add_widget(b_cancel)
        root.add_widget(btns)

        popup.content = root

        def do_save(*a):
            board_id = board_ids[board_values.index(sp.text)] if sp.text in board_values else target_board
            self._save_note(note_id, title_input.text.strip() or "（无标题）",
                            tag_input.text.strip(), body_input.text,
                            board_id, b_pin.text == "取消置顶")
            popup.dismiss()

        def toggle_pin(*a):
            b_pin.text = "取消置顶" if b_pin.text == "置顶" else "置顶"
            b_pin.background_color = (0.85, 0.60, 0.20, 1) if b_pin.text == "置顶" else (0.72, 0.74, 0.78, 1)

        b_pin.bind(on_release=toggle_pin)
        b_save.bind(on_release=do_save)
        b_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _save_note(self, note_id, title, tags, text, board_id, pinned):
        now = datetime.now().isoformat(timespec="seconds")
        if note_id:
            for n in self.notes:
                if n["id"] == note_id:
                    n.update(title=title, tags=tags, text=text, board=board_id,
                             pinned=bool(pinned), updated=now)
                    self.save_note(n)
                    break
        else:
            nid = "n_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
            note = {
                "id": nid, "title": title, "tags": tags, "text": text,
                "board": board_id, "pinned": bool(pinned),
                "created": now, "updated": now,
            }
            self.notes.append(note)
            self.save_note(note)
        self.load_all()      # 刷新统计（含板块按钮上的数字）
        self._rebuild_board_buttons()
        self.apply_filter()

    def confirm_delete_note(self, note_id):
        note = next((n for n in self.notes if n["id"] == note_id), None)
        name = (note.get("title", "") if note else "") or "（无标题）"
        if self._confirm("删除笔记", "确定删除「%s」吗？不可恢复。" % name,
                         lambda: self._do_delete_note(note_id)):
            pass

    def _do_delete_note(self, note_id):
        self.notes = [n for n in self.notes if n["id"] != note_id]
        self.delete_note_store(note_id)
        self._rebuild_board_buttons()
        self.apply_filter()

    # ---------------- 板块管理 ----------------
    def ask_new_board(self):
        self._prompt("新建板块", "板块名称：", "", self._create_board)

    def _create_board(self, name):
        name = (name or "").strip()
        if not name:
            return
        if any(b["name"] == name for b in self.boards):
            self._alert("提示", "已存在同名板块「%s」" % name)
            return
        bid = "b_" + datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.boards = list(self.boards) + [{"id": bid, "name": name}]
        self.save_boards()
        self._rebuild_board_buttons()
        self.set_current_board(bid)

    def ask_rename_board(self, board_id):
        cur = next((b["name"] for b in self.boards if b["id"] == board_id), "")
        self._prompt("重命名板块", "板块名称：", cur,
                     lambda nm: self._rename_board(board_id, nm))

    def _rename_board(self, board_id, new_name):
        new_name = (new_name or "").strip()
        if not new_name:
            return
        for b in self.boards:
            if b["id"] == board_id:
                b["name"] = new_name
                break
        self.save_boards()
        self._rebuild_board_buttons()
        self.apply_filter()

    def ask_delete_board(self):
        if self.current_board in ("", "__all__"):
            self._alert("提示", "请先选择一个具体板块（非「全部笔记」）")
            return
        bname = next((b["name"] for b in self.boards if b["id"] == self.current_board), "")
        cnt = sum(1 for n in self.notes if n.get("board") == self.current_board)

        def do_delete():
            self.boards = [b for b in self.boards if b["id"] != self.current_board]
            # 板块内笔记移入「未分类」保留，不删除内容
            for n in self.notes:
                if n.get("board") == self.current_board:
                    n["board"] = ""
                    self.save_note(n)
            self.save_boards()
            if self.boards:
                self.set_current_board(self.boards[0]["id"])
            else:
                self.current_board = ""
                self.ids.board_title.text = "请先新建一个板块"
                self.apply_filter()
            self._rebuild_board_buttons()

        self._confirm("删除板块",
                      "确定删除板块「%s」吗？\n该板块的 %d 条笔记会被移到「未分类」保留。" % (bname, cnt),
                      do_delete)

    # ---------------- 导出备份 ----------------
    def export_data(self):
        try:
            from android.storage import primary_external_storage_path
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE,
                                 Permission.READ_EXTERNAL_STORAGE])
            out_dir = primary_external_storage_path()
            out = os.path.join(out_dir, "Download")
        except Exception:
            out = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(out, exist_ok=True)
        fname = "工作笔记备份_%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S")
        full = os.path.join(out, fname)
        data = {
            "boards": list(self.boards),
            "notes": [
                {k: v for k, v in n.items() if k in
                 ("id", "title", "tags", "text", "board", "pinned", "created", "updated")}
                for n in self.notes
            ],
        }
        with open(full, "w", encoding="utf-8") as f:
            json_dump(data, f)
        self._alert("备份完成", "已保存到：\n%s" % full)

    # ---------------- 通用弹窗工具 ----------------
    def _alert(self, title, text):
        popup = Popup(title=title, size_hint=(0.8, 0.34), auto_dismiss=True,
                      title_font=App.get_running_app().font_name)
        popup.background = ""
        popup.background_color = (0.96, 0.96, 0.97, 1)
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(Label(text=text, font_name=App.get_running_app().font_name,
                             font_size=dp(14), color=(0.15, 0.15, 0.18, 1),
                             halign="center", valign="middle", text_size=self.size))
        btn = Button(text="知道了", size_hint_y=None, height=dp(42),
                     font_name=App.get_running_app().font_name, font_size=dp(15),
                     background_normal="", background_color=(0.20, 0.45, 0.75, 1),
                     color=(1, 1, 1, 1))
        btn.bind(on_release=popup.dismiss)
        box.add_widget(btn)
        popup.content = box
        popup.open()

    def _confirm(self, title, text, on_yes):
        popup = Popup(title=title, size_hint=(0.82, 0.36), auto_dismiss=True,
                      title_font=App.get_running_app().font_name)
        popup.background = ""
        popup.background_color = (0.96, 0.96, 0.97, 1)
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(Label(text=text, font_name=App.get_running_app().font_name,
                             font_size=dp(14), color=(0.15, 0.15, 0.18, 1),
                             halign="center", valign="middle", text_size=self.size))
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        b_yes = Button(text="确定", font_name=App.get_running_app().font_name,
                       font_size=dp(15),
                       background_normal="", background_color=(0.78, 0.32, 0.30, 1),
                       color=(1, 1, 1, 1))
        b_no = Button(text="取消", font_name=App.get_running_app().font_name,
                      font_size=dp(15),
                      background_normal="", background_color=(0.72, 0.74, 0.78, 1),
                      color=(0.2, 0.2, 0.24, 1))
        btns.add_widget(b_yes)
        btns.add_widget(b_no)
        box.add_widget(btns)
        popup.content = box
        b_yes.bind(on_release=lambda *a: (on_yes(), popup.dismiss()))
        b_no.bind(on_release=popup.dismiss)
        popup.open()
        return popup

    def _prompt(self, title, label, default, on_ok):
        popup = Popup(title=title, size_hint=(0.85, 0.32), auto_dismiss=False,
                      title_font=App.get_running_app().font_name)
        popup.background = ""
        popup.background_color = (0.96, 0.96, 0.97, 1)
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(Label(text=label, size_hint_y=None, height=dp(26),
                             font_name=App.get_running_app().font_name,
                             font_size=dp(14), color=(0.15, 0.15, 0.18, 1)))
        ti = TextInput(text=default, size_hint_y=None, height=dp(46),
                       multiline=False,
                       font_name=App.get_running_app().font_name, font_size=dp(15),
                       background_color=(1, 1, 1, 1), foreground_color=(0.1, 0.1, 0.12, 1),
                       cursor_color=(0.2, 0.4, 0.7, 1))
        box.add_widget(ti)
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        b_ok = Button(text="确定", font_name=App.get_running_app().font_name,
                      font_size=dp(15),
                      background_normal="", background_color=(0.16, 0.55, 0.36, 1),
                      color=(1, 1, 1, 1))
        b_cancel = Button(text="取消", font_name=App.get_running_app().font_name,
                          font_size=dp(15),
                          background_normal="", background_color=(0.72, 0.74, 0.78, 1),
                          color=(0.2, 0.2, 0.24, 1))
        btns.add_widget(b_ok)
        btns.add_widget(b_cancel)
        box.add_widget(btns)
        popup.content = box
        b_ok.bind(on_release=lambda *a: (on_ok(ti.text), popup.dismiss()))
        b_cancel.bind(on_release=popup.dismiss)
        popup.open()


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
def json_dump(obj, fp):
    import json
    json.dump(obj, fp, ensure_ascii=False, indent=2)


class WorkNotesApp(App):
    font_name = StringProperty(FONT_NAME)

    def build(self):
        self.title = "工作笔记"
        try:
            Window.clearcolor = (0.97, 0.97, 0.98, 1)
        except Exception:
            pass
        return MainScreen()

    def on_pause(self):
        return True


if __name__ == "__main__":
    WorkNotesApp().run()
