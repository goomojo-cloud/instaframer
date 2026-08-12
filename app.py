import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io
import urllib.request
import os
import json
import extra_streamlit_components as stx

st.set_page_config(page_title="InstaFramer", page_icon="📷", layout="centered")

# ----------------------------------
# クッキーマネージャーの安全な初期化 (キー指定で警告回避)
# ----------------------------------
cookie_manager = stx.CookieManager(key="instaframer_cm")

st.title("📷 InstaFramer")
st.caption("写真を枠付き正方形に変換 ＋ ウォーターマーク追加")

# ----------------------------------
# フォント自動ダウンロード＆管理機能
# ----------------------------------
FONTS_DIR = "fonts"
os.makedirs(FONTS_DIR, exist_ok=True)

FONT_URLS = {
    "ゴシック体 (Zen Kaku Gothic)": "https://cdn.jsdelivr.net/fontsource/fonts/zen-kaku-gothic-new@latest/japanese-700-normal.ttf",
    "明朝体 (Shippori Mincho)": "https://cdn.jsdelivr.net/fontsource/fonts/shippori-mincho@latest/japanese-700-normal.ttf",
    "丸ゴシック (M PLUS Rounded 1c)": "https://cdn.jsdelivr.net/fontsource/fonts/m-plus-rounded-1c@latest/japanese-700-normal.ttf",
    "英文サンセリフ (Montserrat)": "https://cdn.jsdelivr.net/fontsource/fonts/montserrat@latest/latin-700-normal.ttf",
    "英文セリフ (Cinzel)": "https://cdn.jsdelivr.net/fontsource/fonts/cinzel@latest/latin-700-normal.ttf",
    "手書き風 (Caveat)": "https://cdn.jsdelivr.net/fontsource/fonts/caveat@latest/latin-700-normal.ttf",
    "筆記体 (Sacramento)": "https://cdn.jsdelivr.net/fontsource/fonts/sacramento@latest/latin-400-normal.ttf"
}

@st.cache_data
def download_fonts():
    font_paths = {}
    for font_name, url in FONT_URLS.items():
        filename = f"{font_name.split()[0]}.ttf"
        local_path = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(local_path):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(local_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception:
                pass
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            font_paths[font_name] = local_path
    return font_paths

available_fonts = download_fonts()
font_list = list(available_fonts.keys()) if available_fonts else ["デフォルト"]

# ----------------------------------
# 初期値設定 & クッキーからの復元
# ----------------------------------
DEFAULT_SETTINGS = {
    "tags_input": "#instagram #photo #japan",
    "bg_color_hex": "#FFFFFF",
    "enable_wm": False,
    "wm_type": "テキスト",
    "wm_text": "© My Photo",
    "selected_font_name": font_list[0],
    "size_ratio": 30,
    "text_color_hex": "#FFFFFF",
    "wm_position": "右下",
    "offset_x_pct": 3,
    "offset_y_pct": 3,
    "wm_opacity": 70
}

# クッキーから保存済み設定を取得
saved_cookie_val = None
try:
    cookies = cookie_manager.get_all()
    if isinstance(cookies, dict):
        saved_cookie_val = cookies.get('instaframer_user_config')
except Exception:
    pass

if "config_loaded" not in st.session_state:
    st.session_state["config_loaded"] = False

if not st.session_state["config_loaded"] and saved_cookie_val:
    try:
        loaded_cfg = json.loads(saved_cookie_val)
        for k, v in loaded_cfg.items():
            if k in DEFAULT_SETTINGS:
                st.session_state[k] = v
        st.session_state["config_loaded"] = True
        st.toast("💾 保存された個人設定を読み込みました！")
    except Exception:
        pass

# 初期値未設定のものを割り当て
for key, val in DEFAULT_SETTINGS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ----------------------------------
# サイドバー設定エリア
# ----------------------------------
st.sidebar.header("🎨 アスペクト＆背景設定")
bg_color_hex = st.sidebar.color_picker("背景色を選択", key="bg_color_hex")

bg_color_hex_clean = bg_color_hex.lstrip('#')
bg_color_rgb = tuple(int(bg_color_hex_clean[i:i+2], 16) for i in (0, 2, 4))

# --- ウォーターマーク設定 ---
st.sidebar.markdown("---")
st.sidebar.header("💧 ウォーターマーク設定")
enable_wm = st.sidebar.checkbox("ウォーターマークを有効化", key="enable_wm")

if enable_wm:
    wm_type = st.sidebar.radio("種類", ["テキスト", "ロゴ画像"], key="wm_type")
    
    if wm_type == "テキスト":
        wm_text = st.sidebar.text_input("テキスト内容", key="wm_text")
        if available_fonts:
            curr_font = st.session_state.get("selected_font_name", font_list[0])
            font_idx = font_list.index(curr_font) if curr_font in font_list else 0
            selected_font_name = st.sidebar.selectbox("フォント (字体)", font_list, index=font_idx, key="selected_font_name")
        size_ratio = st.sidebar.number_input("文字の大きさ (元画像幅の %)", min_value=5, max_value=95, step=1, key="size_ratio")
        text_color_hex = st.sidebar.color_picker("文字色", key="text_color_hex")
    else:
        wm_logo_file = st.sidebar.file_uploader("ロゴ画像をアップロード", type=["png", "jpg", "jpeg"])
        size_ratio = st.sidebar.number_input("ロゴの大きさ (元画像幅の %)", min_value=5, max_value=90, step=1, key="size_ratio")

    pos_options = ["右下", "左下", "右上", "左上", "中央"]
    curr_pos = st.session_state.get("wm_position", "右下")
    pos_idx = pos_options.index(curr_pos) if curr_pos in pos_options else 0
    wm_position = st.sidebar.selectbox("配置位置", pos_options, index=pos_idx, key="wm_position")
    
    st.sidebar.markdown("**📍 位置・透明度の微調整**")
    offset_x_pct = st.sidebar.number_input("左右余白 (写真幅の %)", min_value=0, max_value=45, step=1, key="offset_x_pct")
    offset_y_pct = st.sidebar.number_input("上下余白 (写真高の %)", min_value=0, max_value=45, step=1, key="offset_y_pct")
    wm_opacity = st.sidebar.number_input("不透明度 (%)", min_value=10, max_value=100, step=5, key="wm_opacity")

# --- 保存 / リセット ボタンエリア ---
st.sidebar.markdown("---")
col_btn1, col_btn2 = st.sidebar.columns(2)

# 保存ボタン処理（端末のクッキーに書き込み）
if col_btn1.button("💾 マイ設定を保存", use_container_width=True):
    current_config = {
        "tags_input": st.session_state.get("tags_input", "#instagram #photo #japan"),
        "bg_color_hex": st.session_state.get("bg_color_hex", "#FFFFFF"),
        "enable_wm": st.session_state.get("enable_wm", False),
        "wm_type": st.session_state.get("wm_type", "テキスト"),
        "wm_text": st.session_state.get("wm_text", "© My Photo"),
        "selected_font_name": st.session_state.get("selected_font_name", font_list[0]),
        "size_ratio": st.session_state.get("size_ratio", 30),
        "text_color_hex": st.session_state.get("text_color_hex", "#FFFFFF"),
        "wm_position": st.session_state.get("wm_position", "右下"),
        "offset_x_pct": st.session_state.get("offset_x_pct", 3),
        "offset_y_pct": st.session_state.get("offset_y_pct", 3),
        "wm_opacity": st.session_state.get("wm_opacity", 70)
    }
    json_str = json.dumps(current_config)
    try:
        cookie_manager.set('instaframer_user_config', json_str, key="set_cookie")
        st.success("お使いの端末に個人設定を保存しました！次回以降も自動復元されます。")
    except Exception as e:
        st.error(f"保存処理中にエラーが発生しました: {e}")

# リセットボタン処理（クッキーを削除）
if col_btn2.button("🔄 リセット", use_container_width=True):
    try:
        cookie_manager.delete('instaframer_user_config', key="del_cookie")
    except Exception:
        pass
    for k, v in DEFAULT_SETTINGS.items():
        st.session_state[k] = v
    st.session_state["config_loaded"] = True
    st.rerun()


def get_custom_font(font_name, font_size):
    font_path = available_fonts.get(font_name) if available_fonts else None
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            pass
    return ImageFont.load_default(size=font_size)


def apply_watermark_on_photo(base_square_img, photo_rect, position, opacity_pct, off_x_pct, off_y_pct):
    offset_x, offset_y, photo_w, photo_h = photo_rect
    
    img_rgba = base_square_img.convert("RGBA")
    overlay = Image.new("RGBA", img_rgba.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    alpha = int(255 * (opacity_pct / 100))
    margin_x = int(photo_w * (off_x_pct / 100.0))
    margin_y = int(photo_h * (off_y_pct / 100.0))
    
    wm_t = st.session_state.get("wm_type", "テキスト")
    wm_txt = st.session_state.get("wm_text", "")
    s_ratio = st.session_state.get("size_ratio", 30)
    font_n = st.session_state.get("selected_font_name", font_list[0])
    tc_hex = st.session_state.get("text_color_hex", "#FFFFFF")
    
    if wm_t == "テキスト" and wm_txt:
        target_text_w = int(photo_w * (s_ratio / 100.0))
        
        test_font_size = 100
        test_font = get_custom_font(font_n, test_font_size)
        
        bbox = draw.textbbox((0, 0), wm_txt, font=test_font)
        initial_w = bbox[2] - bbox[0]
        
        if initial_w > 0:
            calculated_font_size = int(test_font_size * (target_text_w / initial_w))
            font_size = max(10, calculated_font_size)
            font = get_custom_font(font_n, font_size)
        else:
            font = test_font

        bbox = draw.textbbox((0, 0), wm_txt, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        if position == "右下":
            rel_x = photo_w - text_w - margin_x
            rel_y = photo_h - text_h - margin_y
        elif position == "左下":
            rel_x = margin_x
            rel_y = photo_h - text_h - margin_y
        elif position == "右上":
            rel_x = photo_w - text_w - margin_x
            rel_y = margin_y
        elif position == "左上":
            rel_x = margin_x
            rel_y = margin_y
        else:  # 中央
            rel_x = (photo_w - text_w) // 2
            rel_y = (photo_h - text_h) // 2
            
        abs_x = offset_x + rel_x
        abs_y = offset_y + rel_y
            
        tc_clean = tc_hex.lstrip('#')
        tc_rgb = tuple(int(tc_clean[i:i+2], 16) for i in (0, 2, 4))
        
        draw.text((abs_x, abs_y), wm_txt, font=font, fill=(tc_rgb[0], tc_rgb[1], tc_rgb[2], alpha))
        
    elif wm_t == "ロゴ画像" and 'wm_logo_file' in globals() and wm_logo_file is not None:
        logo = Image.open(wm_logo_file).convert("RGBA")
        
        target_w = int(photo_w * (s_ratio / 100.0))
        aspect = logo.height / logo.width
        target_h = int(target_w * aspect)
        logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * (opacity_pct / 100)))
        logo = Image.merge("RGBA", (r, g, b, a))
        
        if position == "右下":
            rel_x = photo_w - target_w - margin_x
            rel_y = photo_h - target_h - margin_y
        elif position == "左下":
            rel_x = margin_x
            rel_y = photo_h - target_h - margin_y
        elif position == "右上":
            rel_x = photo_w - target_w - margin_x
            rel_y = margin_y
        elif position == "左上":
            rel_x = margin_x
            rel_y = margin_y
        else:  # 中央
            rel_x = (photo_w - target_w) // 2
            rel_y = (photo_h - target_h) // 2
            
        abs_x = offset_x + rel_x
        abs_y = offset_y + rel_y
            
        overlay.paste(logo, (abs_x, abs_y), logo)

    combined = Image.alpha_composite(img_rgba, overlay)
    return combined.convert("RGB")


# ----------------------------------
# メイン画面エリア
# ----------------------------------
# 1. 上段：画像選択エリア
st.subheader("📁 画像を選択")
uploaded_files = st.file_uploader(
    "iPhoneの写真ライブラリ等から画像を選択してください（複数可）", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

# 2. 中段：ハッシュタグエリア
st.subheader("🏷️ ハッシュタグ")
tags_input = st.text_area("ハッシュタグを入力・編集", key="tags_input", height=80)

# 3. 下段：変換結果＆ダウンロードエリア
if uploaded_files:
    st.markdown("---")
    st.success(f"{len(uploaded_files)} 枚の画像が選択されました")
    st.info("💡 iPhoneで保存する場合：画像を長押しして「'写真' に追加」を選択するとカメラロールに直接保存できます。")
    st.subheader("✨ 変換結果＆ダウンロード")
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(image)
            
            if image.mode != "RGB":
                image = image.convert("RGB")
                
            photo_w, photo_h = image.size
            max_side = max(photo_w, photo_h)
            
            square_img = Image.new("RGB", (max_side, max_side), bg_color_rgb)
            offset_x = (max_side - photo_w) // 2
            offset_y = (max_side - photo_h) // 2
            square_img.paste(image, (offset_x, offset_y))
            
            if enable_wm:
                photo_rect = (offset_x, offset_y, photo_w, photo_h)
                square_img = apply_watermark_on_photo(
                    square_img, photo_rect, 
                    st.session_state.get("wm_position", "右下"), 
                    st.session_state.get("wm_opacity", 70), 
                    st.session_state.get("offset_x_pct", 3), 
                    st.session_state.get("offset_y_pct", 3)
                )
            
            buf = io.BytesIO()
            square_img.save(buf, format="JPEG", quality=95)
            byte_im = buf.getvalue()
            
            cols = st.columns([1, 2])
            with cols[0]:
                st.image(square_img, use_container_width=True)
            with cols[1]:
                file_name = f"sq_{uploaded_file.name.split('.')[0]}.jpg"
                st.download_button(
                    label=f"💾 {file_name} を保存",
                    data=byte_im,
                    file_name=file_name,
                    mime="image/jpeg",
                    key=f"dl_{idx}"
                )
        except Exception as e:
            st.error(f"エラーが発生しました ({uploaded_file.name}): {e}")
