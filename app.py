import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io
import os
import zipfile
import gc

st.set_page_config(page_title="InstaFramer", page_icon="📷", layout="centered")

try:
    import requests
except ImportError:
    requests = None

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
    if not requests:
        return font_paths

    headers = {'User-Agent': 'Mozilla/5.0'}
    for font_name, url in FONT_URLS.items():
        filename = f"{font_name.split()[0]}.ttf"
        local_path = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(local_path):
            try:
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(res.content)
            except Exception:
                pass
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            font_paths[font_name] = local_path
    return font_paths

try:
    available_fonts = download_fonts()
except Exception:
    available_fonts = {}

font_list = list(available_fonts.keys()) if available_fonts else ["デフォルトフォント"]

# ----------------------------------
# 初期値設定 & URLパラメータからの復元
# ----------------------------------
DEFAULT_SETTINGS = {
    "tags_input": "#instagram #photo #japan",
    "bg_color_hex": "#FFFFFF",
    "enable_wm": True,
    "wm_type": "テキスト",
    "wm_text": "© My Photo",
    "selected_font_name": font_list[0],
    "size_ratio": 20,
    "text_color_hex": "#FFFFFF",
    "wm_position": "左下",
    "offset_x_pct": 3,
    "offset_y_pct": 3,
    "wm_opacity": 70
}

params = st.query_params

if "init_loaded" not in st.session_state:
    st.session_state["init_loaded"] = True
    if "bg" in params:
        st.session_state["bg_color_hex"] = f"#{params.get('bg')}"
    if "wm" in params:
        st.session_state["enable_wm"] = params.get("wm") == "1"
    if "wmt" in params:
        st.session_state["wm_type"] = params.get("wmt")
    if "txt" in params:
        st.session_state["wm_text"] = params.get("txt")
    if "fnt" in params and params.get("fnt") in font_list:
        st.session_state["selected_font_name"] = params.get("fnt")
    if "sz" in params:
        try: st.session_state["size_ratio"] = int(params.get("sz"))
        except: pass
    if "tc" in params:
        st.session_state["text_color_hex"] = f"#{params.get('tc')}"
    if "pos" in params:
        st.session_state["wm_position"] = params.get("pos")
    if "ox" in params:
        try: st.session_state["offset_x_pct"] = int(params.get("ox"))
        except: pass
    if "oy" in params:
        try: st.session_state["offset_y_pct"] = int(params.get("oy"))
        except: pass
    if "op" in params:
        try: st.session_state["wm_opacity"] = int(params.get("op"))
        except: pass
    if "tags" in params:
        st.session_state["tags_input"] = params.get("tags")

for k, v in DEFAULT_SETTINGS.items():
    if k not in st.session_state:
        st.session_state[k] = v

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

wm_logo_file = None
if enable_wm:
    wm_type = st.sidebar.radio("種類", ["テキスト", "ロゴ画像"], key="wm_type")
    
    if wm_type == "テキスト":
        wm_text = st.sidebar.text_input("テキスト内容", key="wm_text")
        if font_list:
            curr_font = st.session_state.get("selected_font_name", font_list[0])
            font_idx = font_list.index(curr_font) if curr_font in font_list else 0
            selected_font_name = st.sidebar.selectbox("フォント (字体)", font_list, index=font_idx, key="selected_font_name")
        size_ratio = st.sidebar.number_input("文字の大きさ (元画像幅の %)", min_value=5, max_value=95, step=1, key="size_ratio")
        text_color_hex = st.sidebar.color_picker("文字色", key="text_color_hex")
    else:
        wm_logo_file = st.sidebar.file_uploader("ロゴ画像をアップロード", type=["png", "jpg", "jpeg"])
        size_ratio = st.sidebar.number_input("ロゴの大きさ (元画像幅の %)", min_value=5, max_value=90, step=1, key="size_ratio")

    pos_options = ["右下", "左下", "右上", "左上", "中央"]
    curr_pos = st.session_state.get("wm_position", "左下")
    pos_idx = pos_options.index(curr_pos) if curr_pos in pos_options else 1
    wm_position = st.sidebar.selectbox("配置位置", pos_options, index=pos_idx, key="wm_position")
    
    st.sidebar.markdown("**📍 位置・透明度の微調整**")
    offset_x_pct = st.sidebar.number_input("左右余白 (写真幅の %)", min_value=0, max_value=45, step=1, key="offset_x_pct")
    offset_y_pct = st.sidebar.number_input("上下余白 (写真高の %)", min_value=0, max_value=45, step=1, key="offset_y_pct")
    wm_opacity = st.sidebar.number_input("不透明度 (%)", min_value=10, max_value=100, step=5, key="wm_opacity")

# --- 設定リンク作成エリア ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 マイ設定の保存")

new_params = {
    "bg": st.session_state.get("bg_color_hex", "#FFFFFF").lstrip('#'),
    "wm": "1" if st.session_state.get("enable_wm", True) else "0",
    "wmt": st.session_state.get("wm_type", "テキスト"),
    "txt": st.session_state.get("wm_text", "© My Photo"),
    "fnt": st.session_state.get("selected_font_name", font_list[0]),
    "sz": str(st.session_state.get("size_ratio", 20)),
    "tc": st.session_state.get("text_color_hex", "#FFFFFF").lstrip('#'),
    "pos": st.session_state.get("wm_position", "左下"),
    "ox": str(st.session_state.get("offset_x_pct", 3)),
    "oy": str(st.session_state.get("offset_y_pct", 3)),
    "op": str(st.session_state.get("wm_opacity", 70)),
    "tags": st.session_state.get("tags_input", "#instagram #photo #japan")
}

st.sidebar.info("💡 設定変更後に下のボタンでURLを更新し、ブックマークしてください。")

if st.sidebar.button("🔗 この設定用のURLを作成", use_container_width=True):
    st.query_params.clear()
    for k, v in new_params.items():
        st.query_params[k] = v
    st.sidebar.success("URLに設定を反映しました！この画面のブラウザURLをブックマーク登録してください。")

if st.sidebar.button("🔄 デフォルトに戻す", use_container_width=True):
    st.query_params.clear()
    for k, v in DEFAULT_SETTINGS.items():
        st.session_state[k] = v
    st.rerun()


def get_custom_font(font_name, font_size):
    font_path = available_fonts.get(font_name) if available_fonts else None
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=font_size)
    except TypeError:
        return ImageFont.load_default()


def process_single_image(uploaded_file, idx, bg_rgb, enable_watermark, logo_file):
    """単一の画像を処理し、(ファイル名, JPEGバイナリ) を返してメモリを即時解放する"""
    MAX_DIM = 1920  # フルHD基準サイズに縮小してメモリ領域を大幅削減
    
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    
    if max(image.size) > MAX_DIM:
        image.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)
    
    if image.mode != "RGB":
        image = image.convert("RGB")
        
    photo_w, photo_h = image.size
    max_side = max(photo_w, photo_h)
    
    square_img = Image.new("RGB", (max_side, max_side), bg_rgb)
    offset_x = (max_side - photo_w) // 2
    offset_y = (max_side - photo_h) // 2
    square_img.paste(image, (offset_x, offset_y))
    del image
    
    if enable_watermark:
        img_rgba = square_img.convert("RGBA")
        overlay = Image.new("RGBA", img_rgba.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        opacity_pct = st.session_state.get("wm_opacity", 70)
        alpha = int(255 * (opacity_pct / 100))
        off_x_pct = st.session_state.get("offset_x_pct", 3)
        off_y_pct = st.session_state.get("offset_y_pct", 3)
        margin_x = int(photo_w * (off_x_pct / 100.0))
        margin_y = int(photo_h * (off_y_pct / 100.0))
        
        wm_t = st.session_state.get("wm_type", "テキスト")
        wm_txt = st.session_state.get("wm_text", "")
        s_ratio = st.session_state.get("size_ratio", 20)
        font_n = st.session_state.get("selected_font_name", font_list[0])
        tc_hex = st.session_state.get("text_color_hex", "#FFFFFF")
        position = st.session_state.get("wm_position", "左下")
        
        if wm_t == "テキスト" and wm_txt:
            target_text_w = int(photo_w * (s_ratio / 100.0))
            test_font = get_custom_font(font_n, 100)
            try:
                bbox = draw.textbbox((0, 0), wm_txt, font=test_font)
                initial_w = bbox[2] - bbox[0]
            except Exception:
                initial_w = 100

            font_size = max(10, int(100 * (target_text_w / initial_w))) if initial_w > 0 else 20
            font = get_custom_font(font_n, font_size)

            try:
                bbox = draw.textbbox((0, 0), wm_txt, font=font)
                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                text_w, text_h = 100, 20
            
            if position == "右下":
                rel_x, rel_y = photo_w - text_w - margin_x, photo_h - text_h - margin_y
            elif position == "左下":
                rel_x, rel_y = margin_x, photo_h - text_h - margin_y
            elif position == "右上":
                rel_x, rel_y = photo_w - text_w - margin_x, margin_y
            elif position == "左上":
                rel_x, rel_y = margin_x, margin_y
            else:
                rel_x, rel_y = (photo_w - text_w) // 2, (photo_h - text_h) // 2
                
            tc_clean = tc_hex.lstrip('#')
            tc_rgb = tuple(int(tc_clean[i:i+2], 16) for i in (0, 2, 4))
            draw.text((offset_x + rel_x, offset_y + rel_y), wm_txt, font=font, fill=(tc_rgb[0], tc_rgb[1], tc_rgb[2], alpha))
            
        elif wm_t == "ロゴ画像" and logo_file is not None:
            logo = Image.open(logo_file).convert("RGBA")
            target_w = int(photo_w * (s_ratio / 100.0))
            target_h = int(target_w * (logo.height / logo.width))
            logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            r, g, b, a = logo.split()
            a = a.point(lambda p: int(p * (opacity_pct / 100)))
            logo = Image.merge("RGBA", (r, g, b, a))
            
            if position == "右下":
                rel_x, rel_y = photo_w - target_w - margin_x, photo_h - target_h - margin_y
            elif position == "左下":
                rel_x, rel_y = margin_x, photo_h - target_h - margin_y
            elif position == "右上":
                rel_x, rel_y = photo_w - target_w - margin_x, margin_y
            elif position == "左上":
                rel_x, rel_y = margin_x, margin_y
            else:
                rel_x, rel_y = (photo_w - target_w) // 2, (photo_h - target_h) // 2
                
            overlay.paste(logo, (offset_x + rel_x, offset_y + rel_y), logo)

        combined = Image.alpha_composite(img_rgba, overlay)
        square_img = combined.convert("RGB")
        del img_rgba, overlay

    buf = io.BytesIO()
    square_img.save(buf, format="JPEG", quality=88, optimize=True)
    byte_im = buf.getvalue()
    
    del square_img
    gc.collect()
    
    raw_name = os.path.splitext(uploaded_file.name)[0]
    file_name = f"sq_{idx+1}_{raw_name}.jpg"
    return file_name, byte_im


# ----------------------------------
# メイン画面エリア
# ----------------------------------
st.subheader("📁 画像を選択")
uploaded_files = st.file_uploader(
    "iPhoneの写真ライブラリ等から画像を選択してください（複数可）", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

st.subheader("🏷️ ハッシュタグ")
tags_input = st.text_area("ハッシュタグを入力・編集", key="tags_input", height=80)

if uploaded_files:
    st.markdown("---")
    st.success(f"{len(uploaded_files)} 枚の画像が選択されました")
    st.subheader("✨ 変換結果＆ダウンロード")
    
    # 複数枚選択時のZIP作成（ストリーム書き込みで省メモリ化）
    if len(uploaded_files) > 1:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    fname, bdata = process_single_image(uploaded_file, idx, bg_color_rgb, enable_wm, wm_logo_file)
                    zip_file.writestr(fname, bdata)
                    del bdata
                    gc.collect()
                except Exception as e:
                    st.error(f"エラー ({uploaded_file.name}): {e}")
        
        st.download_button(
            label=f"📦 全 {len(uploaded_files)} 枚をまとめてダウンロード (.zip)",
            data=zip_buffer.getvalue(),
            file_name="instaframer_images.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )
        st.markdown("---")

    # 個別表示＆ダウンロード（1枚ずつ順番に生成＆表示）
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            fname, bdata = process_single_image(uploaded_file, idx, bg_color_rgb, enable_wm, wm_logo_file)
            cols = st.columns([1, 2])
            with cols[0]:
                st.image(bdata, use_container_width=True)
            with cols[1]:
                st.download_button(
                    label=f"💾 {fname} を保存",
                    data=bdata,
                    file_name=fname,
                    mime="image/jpeg",
                    key=f"dl_{idx}"
                )
            del bdata
            gc.collect()
        except Exception as e:
            st.error(f"エラー ({uploaded_file.name}): {e}")
