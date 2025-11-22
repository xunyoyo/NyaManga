import flet as ft
import os
import base64
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
        "output_folder": "保存文件夹",
        "select_output_folder": "选择保存位置",
        "saved_to": "已保存至: ",
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
        "output_folder": "Output Folder",
        "select_output_folder": "Select Output Folder",
        "saved_to": "Saved to: ",
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
    loc_image_path_display = ft.Text(italic=True, size=12, color="grey")
    loc_image_path_input = ft.TextField(visible=False, expand=True, height=40, content_padding=10, text_size=12)
    
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
    loc_extra_prompt = ft.TextField(multiline=True, min_lines=2)
    loc_run_btn = ft.ElevatedButton(icon="play_arrow", style=ft.ButtonStyle(color="white", bgcolor="indigo"))
    loc_preview_image = ft.Image(src="", visible=False, height=400, fit=ft.ImageFit.CONTAIN)
    loc_result_image = ft.Image(src_base64="", visible=False, height=400, fit=ft.ImageFit.CONTAIN)
    loc_result_text = ft.Text("", selectable=True)
    loc_progress = ft.ProgressBar(visible=False)
    loc_file_picker = ft.FilePicker()
    loc_dir_picker = ft.FilePicker()
    loc_select_btn = ft.ElevatedButton(icon="upload_file")
    loc_select_folder_btn = ft.ElevatedButton(icon="folder_open")
    loc_image_dropdown = ft.Dropdown(visible=False, width=400)
    loc_manual_btn = ft.IconButton(icon="edit")
    
    loc_output_path_display = ft.Text(value="", italic=True, size=12, color="grey")
    loc_output_dir_picker = ft.FilePicker()
    loc_select_output_btn = ft.ElevatedButton(icon="save_alt")

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
        loc_image_path_display.value = f"{T('file_name')}: {Path(loc_selected_file).name}" if loc_selected_file else T("no_image")
        loc_image_path_input.label = T("image_path")
        loc_select_btn.text = T("select_image")
        loc_select_folder_btn.text = T("select_folder")
        loc_image_dropdown.label = T("folder_images")
        loc_target_lang.label = T("target_lang")
        loc_tone.label = T("tone")
        loc_bubble_hint.label = T("bubble_hint")
        loc_extra_prompt.label = T("extra_prompt")
        loc_run_btn.text = T("run_localize")
        loc_manual_btn.tooltip = T("manual_input")
        loc_select_output_btn.text = T("select_output_folder")
        if loc_output_folder:
             loc_output_path_display.value = f"{T('output_folder')}: {loc_output_folder}"
        else:
             loc_output_path_display.value = ""
        
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
    loc_output_folder: Optional[str] = None
    loc_images = []

    def loc_on_output_folder_picked(e: ft.FilePickerResultEvent):
        nonlocal loc_output_folder
        if e.path:
            loc_output_folder = e.path
            loc_output_path_display.value = f"{T('output_folder')}: {loc_output_folder}"
            page.update()

    loc_output_dir_picker.on_result = loc_on_output_folder_picked

    def set_selected_image(path: str):
        nonlocal loc_selected_file
        loc_selected_file = path
        # Update UI
        loc_image_path_display.value = f"{T('file_name')}: {Path(path).name}"
        loc_image_path_input.value = path
        
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            loc_preview_image.src_base64 = b64
            loc_preview_image.src = ""
            loc_preview_image.visible = True
        except Exception as e:
            print(f"Error loading image: {e}")
            loc_preview_image.visible = False

        if loc_image_dropdown.options:
            loc_image_dropdown.value = path
        page.update()
    
    def loc_on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            set_selected_image(e.files[0].path)

    def loc_on_folder_picked(e: ft.FilePickerResultEvent):
        nonlocal loc_images
        if not e.path:
            return
        folder = Path(e.path)
        if not folder.exists():
            show_error("Folder not found")
            return
        suffixes = {".png", ".jpg", ".jpeg", ".webp"}
        loc_images = sorted([p for p in folder.iterdir() if p.suffix.lower() in suffixes])
        if not loc_images:
            show_error("文件夹里没有图片（png/jpg/jpeg/webp）")
            return
        loc_image_dropdown.options = [ft.dropdown.Option(str(p)) for p in loc_images]
        loc_image_dropdown.value = str(loc_images[0])
        loc_image_dropdown.visible = True
        set_selected_image(str(loc_images[0]))

    loc_image_dropdown.on_change = lambda e: set_selected_image(e.control.value) if e.control.value else None

    loc_file_picker.on_result = loc_on_file_picked
    loc_dir_picker.on_result = loc_on_folder_picked
    # Ensure pickers are registered; overlay has no setter in current Flet.
    if loc_file_picker not in page.overlay:
        page.overlay.append(loc_file_picker)
    if loc_dir_picker not in page.overlay:
        page.overlay.append(loc_dir_picker)
    if loc_output_dir_picker not in page.overlay:
        page.overlay.append(loc_output_dir_picker)
    page.update()
    def on_select_file_click(_):
        try:
            loc_file_picker.pick_files(allow_multiple=False)
        except Exception as ex:
            show_error(str(ex))

    def on_select_folder_click(_):
        try:
            loc_dir_picker.get_directory_path()
        except Exception as ex:
            show_error(str(ex))

    loc_select_btn.on_click = on_select_file_click
    loc_select_folder_btn.on_click = on_select_folder_click
    loc_select_output_btn.on_click = lambda _: loc_output_dir_picker.get_directory_path()

    def toggle_manual_input(e):
        is_visible = loc_image_path_input.visible
        loc_image_path_input.visible = not is_visible
        loc_image_path_display.visible = is_visible # Toggle display
        
        page.update() # Update UI first to ensure control is rendered/visible
        
        if not is_visible:
             loc_image_path_input.value = loc_selected_file or ""
             try:
                loc_image_path_input.focus()
             except Exception:
                pass # Ignore focus errors if control is not ready

    loc_manual_btn.on_click = toggle_manual_input

    def run_localize(e):
        # Use input value if visible, else selected file
        current_file = loc_image_path_input.value if loc_image_path_input.visible else loc_selected_file

        if not current_file:
            show_error(T("select_img_first"))
            return

        loc_progress.visible = True
        loc_result_image.visible = False
        page.update()

        def task():
            try:
                pipeline = app_state.get_pipeline()
                result = pipeline.localize_panel(
                    image_path=Path(current_file),
                    source_text=None,  # auto OCR+translate via image model
                    target_language=loc_target_lang.value or "zh",
                    tone=loc_tone.value or "friendly manga voice",
                    bubble_hint=loc_bubble_hint.value if loc_bubble_hint.value else None,
                    style_hint=loc_extra_prompt.value if loc_extra_prompt.value else None
                )
                loc_result_image.src_base64 = result.edited_image_b64
                loc_result_image.visible = True
                loc_result_text.value = f"{T('result')}: {result.rewritten_text or '[auto]'}"
                
                if loc_output_folder:
                    try:
                        original_path = Path(current_file)
                        new_filename = f"{original_path.stem}_localized{original_path.suffix}"
                        save_path = Path(loc_output_folder) / new_filename
                        
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(result.edited_image_b64))
                        show_snack(f"{T('complete')} {T('saved_to')}{save_path.name}")
                    except Exception as save_ex:
                        show_error(f"Save failed: {save_ex}")
                else:
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
                            ft.Row([
                                loc_select_btn, 
                                loc_select_folder_btn,
                                loc_manual_btn,
                                ft.Container(loc_image_path_display, padding=ft.padding.only(left=10), expand=True),
                                loc_image_path_input
                            ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            loc_image_dropdown,
                            ft.Row([loc_target_lang, loc_tone]), # Row 1
                            ft.Row([loc_bubble_hint], expand=True), # Row 2 (Full width)
                            loc_extra_prompt,
                            ft.Row([loc_select_output_btn, ft.Container(loc_output_path_display, padding=ft.padding.only(left=10), expand=True)]),
                            ft.Row([loc_run_btn], alignment=ft.MainAxisAlignment.END),
                            loc_progress
                        ]),
                        build_card("output_group", [
                            ft.ResponsiveRow([
                                ft.Column([ft.Text(T("original")), loc_preview_image], col={"sm": 12, "md": 6}),
                                ft.Column([ft.Text(T("result")), loc_result_image, loc_result_text], col={"sm": 12, "md": 6}),
                            ]),
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
    ft.app(target=main, view=ft.AppView.FLET_APP)
