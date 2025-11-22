import flet as ft
import base64
import os
from pathlib import Path
from typing import Optional
import threading

from nyamanga.config import ApiConfig
from nyamanga.pipeline import TypesettingPipeline

# --- Translations ---
TRANSLATIONS = {
    "zh": {
        "app_title": "NyaManga 漫画嵌字",
        "settings": "设置",
        "localize": "一键嵌字",
        "rewrite": "仅翻译",
        "api_key": "API 密钥",
        "base_url": "API 地址",
        "chat_model": "对话模型",
        "image_model": "图像模型",
        "save_config": "保存配置",
        "select_image": "选择图片",
        "select_folder": "选择文件夹",
        "folder_images": "文件夹中的图片",
        "no_image": "未选择图片",
        "target_lang": "目标语言",
        "tone": "语气/风格",
        "bubble_hint": "气泡位置提示 (如: 左上)",
        "extra_prompt": "附加提示词（可选，描述风格/排版/注意事项）",
        "run_localize": "开始嵌字",
        "original": "原图",
        "result": "结果",
        "run_rewrite": "开始翻译",
        "source_text": "源文本",
        "enter_text": "请输入文本",
        "language_switch": "界面语言 / Language",
        "theme_switch": "深色模式",
        "processing": "处理中...",
        "complete": "完成!",
        "error": "错误: ",
        "save_success": "设置已保存!",
        "select_img_first": "请先选择图片",
        "input_group": "输入",
        "output_group": "输出",
        "path_input": "手动输入图片路径",
        "load_path": "加载路径",
    },
    "en": {
        "app_title": "NyaManga UI",
        "settings": "Settings",
        "localize": "Localize",
        "rewrite": "Rewrite",
        "api_key": "API Key",
        "base_url": "Base URL",
        "chat_model": "Chat Model",
        "image_model": "Image Model",
        "save_config": "Save Configuration",
        "select_image": "Select Image",
        "select_folder": "Select Folder",
        "folder_images": "Images in folder",
        "no_image": "No image selected",
        "target_lang": "Target Language",
        "tone": "Tone",
        "bubble_hint": "Bubble Hint (e.g. 'top-left')",
        "extra_prompt": "Extra prompt (style/layout guidance, optional)",
        "run_localize": "Run Localize",
        "original": "Original",
        "result": "Result",
        "run_rewrite": "Rewrite",
        "source_text": "Source Text",
        "enter_text": "Please enter text",
        "language_switch": "Language",
        "theme_switch": "Dark Mode",
        "processing": "Processing...",
        "complete": "Complete!",
        "error": "Error: ",
        "save_success": "Settings saved!",
        "select_img_first": "Please select an image first",
        "input_group": "Input",
        "output_group": "Output",
        "path_input": "Manual image path",
        "load_path": "Load path",
    }
}

# Global configuration state
class AppState:
    def __init__(self):
        self.api_key = os.environ.get("NYAMANGA_API_KEY") or os.environ.get("EPHONE_API_KEY") or ""
        self.base_url = os.environ.get("NYAMANGA_BASE_URL", "https://api.ephone.chat/v1")
        self.chat_model = os.environ.get("NYAMANGA_CHAT_MODEL", "nano-banana-2")
        self.image_model = os.environ.get("NYAMANGA_IMAGE_MODEL", "nano-banana-2")
        self.pipeline: Optional[TypesettingPipeline] = None
        self.ui_lang = "zh"  # Default to Chinese

    def get_config(self) -> ApiConfig:
        if not self.api_key:
            raise ValueError("API Key is required. Please set it in Settings.")
        return ApiConfig(
            api_key=self.api_key,
            base_url=self.base_url,
            chat_model=self.chat_model,
            image_model=self.image_model,
        )

    def get_pipeline(self) -> TypesettingPipeline:
        return TypesettingPipeline(self.get_config())

app_state = AppState()

def main(page: ft.Page):
    page.title = TRANSLATIONS[app_state.ui_lang]["app_title"]
    page.theme = ft.Theme(color_scheme_seed="indigo")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0  # Use container padding instead
    
    # Helper to get text
    def T(key: str) -> str:
        return TRANSLATIONS[app_state.ui_lang].get(key, key)

    # --- Components ---

    def show_snack(message: str, color: str = "green"):
        page.overlay.append(ft.SnackBar(content=ft.Text(message), bgcolor=color, open=True))
        page.update()

    def show_error(message: str):
        show_snack(f"{T('error')}{message}", "red")

    # --- UI Elements References (needed for updates) ---
    
    # Navigation
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[], # Will be populated by update_ui
    )

    # Settings Fields
    api_key_field = ft.TextField(password=True, can_reveal_password=True, value=app_state.api_key)
    base_url_field = ft.TextField(value=app_state.base_url)
    chat_model_field = ft.TextField(value=app_state.chat_model)
    image_model_field = ft.TextField(value=app_state.image_model)
    save_btn = ft.ElevatedButton(on_click=lambda e: save_settings(e))
    lang_switch = ft.Dropdown(
        value=app_state.ui_lang,
        options=[
            ft.dropdown.Option("zh", "中文"),
            ft.dropdown.Option("en", "English"),
        ],
        width=150,
    )

    # Localize Fields
    loc_image_path = ft.Text(italic=True)
    loc_source_text = ft.TextField(multiline=True, min_lines=3)
    loc_target_lang = ft.Dropdown(
        value="zh",
        options=[
            ft.dropdown.Option("zh", "Chinese (Simplified)"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("ja", "Japanese"),
            ft.dropdown.Option("ko", "Korean"),
        ],
        expand=True
    )
    loc_tone = ft.TextField(value="friendly manga voice", expand=True)
    loc_bubble_hint = ft.TextField(value="")
    loc_run_btn = ft.ElevatedButton(icon="play_arrow")
    loc_preview_image = ft.Image(src="", visible=False, height=400, fit=ft.ImageFit.CONTAIN)
    loc_result_image = ft.Image(src_base64="", visible=False, height=400, fit=ft.ImageFit.CONTAIN)
    loc_result_text = ft.Text("", selectable=True)
    loc_progress = ft.ProgressBar(visible=False)
    loc_file_picker = ft.FilePicker()
    loc_select_btn = ft.ElevatedButton(icon="upload_file")

    # Rewrite Fields
    rw_source = ft.TextField(multiline=True, min_lines=3)
    rw_lang = ft.Dropdown(
        value="zh",
        options=[
            ft.dropdown.Option("zh", "Chinese"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("ja", "Japanese"),
        ],
        expand=True
    )
    rw_tone = ft.TextField(value="friendly manga voice", expand=True)
    rw_run_btn = ft.ElevatedButton()
    rw_result = ft.TextField(read_only=True, multiline=True)
    rw_progress = ft.ProgressBar(visible=False)

    # --- Logic ---

    def update_ui_text():
        page.title = T("app_title")
        
        # Nav
        rail.destinations = [
            ft.NavigationRailDestination(
                icon="translate", selected_icon="translate_outlined", label=T("localize")
            ),
            ft.NavigationRailDestination(
                icon="text_fields", selected_icon="text_fields_outlined", label=T("rewrite")
            ),
            ft.NavigationRailDestination(
                icon="settings", selected_icon="settings_outlined", label=T("settings")
            ),
        ]
        
        # Settings
        api_key_field.label = T("api_key")
        base_url_field.label = T("base_url")
        chat_model_field.label = T("chat_model")
        image_model_field.label = T("image_model")
        save_btn.text = T("save_config")
        lang_switch.label = T("language_switch")

        # Localize
        loc_image_path.value = T("no_image") if not loc_selected_file else loc_selected_file
        loc_select_btn.text = T("select_image")
        loc_source_text.label = T("source_text")
        loc_target_lang.label = T("target_lang")
        loc_tone.label = T("tone")
        loc_bubble_hint.label = T("bubble_hint")
        loc_run_btn.text = T("run_localize")
        
        # Rewrite
        rw_source.label = T("source_text")
        rw_lang.label = T("target_lang")
        rw_tone.label = T("tone")
        rw_run_btn.text = T("run_rewrite")
        rw_result.label = T("result")

        page.update()

    def on_lang_change(e):
        app_state.ui_lang = lang_switch.value or "zh"
        update_ui_text()

    lang_switch.on_change = on_lang_change

    def save_settings(e):
        app_state.api_key = api_key_field.value or ""
        app_state.base_url = base_url_field.value or ""
        app_state.chat_model = chat_model_field.value or ""
        app_state.image_model = image_model_field.value or ""
        show_snack(T("save_success"))

    # Localize Logic
    loc_selected_file: Optional[str] = None
    
    def loc_on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal loc_selected_file
        if e.files:
            loc_selected_file = e.files[0].path
            loc_image_path.value = loc_selected_file
            loc_preview_image.src = loc_selected_file
            loc_preview_image.visible = True
            page.update()

    loc_file_picker.on_result = loc_on_file_picked
    page.overlay.append(loc_file_picker)
    loc_select_btn.on_click = lambda _: loc_file_picker.pick_files(allow_multiple=False)

    def run_localize(e):
        if not loc_selected_file:
            show_error(T("select_img_first"))
            return
        if not loc_source_text.value:
            show_error(T("enter_text"))
            return

        loc_progress.visible = True
        loc_result_image.visible = False
        page.update()

        def task():
            try:
                pipeline = app_state.get_pipeline()
                result = pipeline.localize_panel(
                    image_path=Path(loc_selected_file or ""),
                    source_text=loc_source_text.value or "",
                    target_language=loc_target_lang.value or "zh",
                    tone=loc_tone.value or "friendly manga voice",
                    bubble_hint=loc_bubble_hint.value if loc_bubble_hint.value else None
                )
                loc_result_image.src_base64 = result.edited_image_b64
                loc_result_image.visible = True
                loc_result_text.value = f"{T('result')}: {result.rewritten_text}"
                show_snack(T("complete"))
            except Exception as ex:
                show_error(str(ex))
            finally:
                loc_progress.visible = False
                page.update()

        threading.Thread(target=task).start()
    
    loc_run_btn.on_click = run_localize

    # Rewrite Logic
    def run_rewrite(e):
        if not rw_source.value:
            show_error(T("enter_text"))
            return
        rw_progress.visible = True
        page.update()
        
        def task():
            try:
                pipeline = app_state.get_pipeline()
                res = pipeline.embedder.rewrite_dialogue(
                    source_text=rw_source.value or "",
                    target_language=rw_lang.value or "zh",
                    tone=rw_tone.value or "friendly manga voice"
                )
                rw_result.value = res.text
            except Exception as ex:
                show_error(str(ex))
            finally:
                rw_progress.visible = False
                page.update()
        threading.Thread(target=task).start()

    rw_run_btn.on_click = run_rewrite

    # --- Layout Construction ---

    def build_card(title_key, content_controls):
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text(T(title_key), style=ft.TextThemeStyle.TITLE_MEDIUM, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        *content_controls
                    ],
                    spacing=20
                ),
                padding=20,
            ),
            margin=10
        )

    # Views
    def get_settings_view():
        return ft.ListView(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text(T("settings"), style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        build_card("settings", [
                            lang_switch,
                            api_key_field,
                            base_url_field,
                            chat_model_field,
                            image_model_field,
                            save_btn
                        ])
                    ]),
                    padding=20
                )
            ],
            expand=True
        )

    def get_localize_view():
        return ft.ListView(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text(T("localize"), style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        build_card("input_group", [
                            ft.Row([loc_select_btn, ft.Container(loc_image_path, expand=True)]),
                            loc_source_text,
                            ft.Row([loc_target_lang, loc_tone]), # Row 1
                            loc_bubble_hint,                     # Row 2 (Full width)
                            loc_run_btn,
                            loc_progress
                        ]),
                        build_card("output_group", [
                            ft.ResponsiveRow([
                                ft.Column([ft.Text(T("original")), loc_preview_image], col={"sm": 12, "md": 6}),
                                ft.Column([ft.Text(T("result")), loc_result_image, loc_result_text], col={"sm": 12, "md": 6}),
                            ])
                        ])
                    ]),
                    padding=20
                )
            ],
            expand=True
        )

    def get_rewrite_view():
        return ft.ListView(
            [
                ft.Container(
                    content=ft.Column([
                        ft.Text(T("rewrite"), style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        build_card("input_group", [
                            rw_source,
                            ft.Row([rw_lang, rw_tone]),
                            rw_run_btn,
                            rw_progress
                        ]),
                        build_card("output_group", [
                            rw_result
                        ])
                    ]),
                    padding=20
                )
            ],
            expand=True
        )

    # Navigation Logic
    body = ft.Container(expand=True)

    def nav_change(e):
        idx = e.control.selected_index
        if idx == 0:
            body.content = get_localize_view()
        elif idx == 1:
            body.content = get_rewrite_view()
        elif idx == 2:
            body.content = get_settings_view()
        body.update()

    rail.on_change = nav_change

    # Initial UI Setup
    update_ui_text()
    body.content = get_localize_view() # Default view

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                body,
            ],
            expand=True,
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
