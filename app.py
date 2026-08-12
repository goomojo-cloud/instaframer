import streamlit as st
from PIL import Image, ImageOps, ImageDraw, ImageFont
import io

st.set_page_config(page_title="InstaFramer", page_icon="📷", layout="centered")

st.title("📷 InstaFramer")
st.caption("写真を枠付き正方形に変換 ＋ ウォーターマーク追加")

# ----------------------------------
# サイドバー設定エリア
# ----------------------------------
st.sidebar.header("🎨 アスペクト＆背景設定")
bg_color_hex = st.sidebar.color_picker("背景色を選択", "#FFFFFF")

# 16進数カラーコードをRGBに変換
bg_color_hex_clean = bg_color_hex.lstrip('#')
bg_color_rgb = tuple(int(bg_color_hex_clean[i:i+2], 16) for i in (0, 2, 4))

# --- ウォーターマーク設定 ---
st.sidebar.markdown("---")
st.sidebar.header("💧 ウォーターマーク設定")
enable_wm = st.sidebar.checkbox("ウォーターマークを有効化", value=False)

wm_type = "テキスト"
wm_text = ""
wm_logo_file = None
wm_position = "右下"
wm_opacity = 50
size_ratio = 30
text_color_hex = "#FFFFFF"

if enable_wm:
    wm_type = st.sidebar.radio("種類", ["テキスト", "ロゴ画像"])
    
    if wm_type == "テキスト":
        wm_text = st.sidebar.text_input("テキスト内容", value="© My Photo")
        size_ratio = st.sidebar.slider("文字の横幅割合 (元画像幅の %)", 10, 95, 30)
        text_color_hex = st.sidebar.color_picker("文字色", "#FFFFFF")
    else:
        wm_logo_file = st.sidebar.file_uploader("ロゴ画像をアップロード", type=["png", "jpg", "jpeg"])
        size_ratio = st.sidebar.slider("ロゴの横幅割合 (元画像幅の %)", 5, 90, 20)

    wm_position = st.sidebar.selectbox("配置位置", ["右下", "左下", "右上", "左上", "中央"])
    wm_opacity = st.sidebar.slider("不透明度 (%)", 10, 100, 70)


def get_scalable_font(font_size):
    """OS環境に依存せず、指定サイズでスケーラブルなフォントオブジェクトを取得する関数"""
    try:
        # Pillow標準組み込みのTrueTypeフォント（FreeMono等）を取得
        return ImageFont.load_default(size=font_size)
    except TypeError:
        # 古いPillowバージョンのフォールバック処理
        try:
            return ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            try:
                return ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                return ImageFont.load_default()


def apply_watermark_on_photo(base_square_img, photo_rect, position, opacity_pct):
    """
    正方形キャンバス上の『元画像（写真本体）領域』内にウォーターマークを配置する処理
    photo_rect: (offset_x, offset_y, photo_w, photo_h)
    """
    offset_x, offset_y, photo_w, photo_h = photo_rect
    
    img_rgba = base_square_img.convert("RGBA")
    overlay = Image.new("RGBA", img_rgba.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    alpha = int(255 * (opacity_pct / 100))
    margin = int(min(photo_w, photo_h) * 0.03)
    
    if wm_type == "テキスト" and wm_text:
        target_text_w = int(photo_w * (size_ratio / 100.0))
        
        # 基準サイズ100pxでフォントを読み込んで幅を測定
        test_font_size = 100
        test_font = get_scalable_font(test_font_size)
        
        bbox = draw.textbbox((0, 0), wm_text, font=test_font)
        initial_w = bbox[2] - bbox[0]
        
        if initial_w > 0:
            calculated_font_size = int(test_font_size * (target_text_w / initial_w))
            font_size = max(10, calculated_font_size)
            font = get_scalable_font(font_size)
        else:
            font = test_font

        # 決定したサイズで描画範囲を正確に計算
        bbox = draw.textbbox((0, 0), wm_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # 写真領域内の相対位置計算
        if position == "右下":
            rel_x = photo_w - text_w - margin
            rel_y = photo_h - text_h - margin
        elif position == "左下":
            rel_x = margin
            rel_y = photo_h - text_h - margin
        elif position == "右上":
            rel_x = photo_w - text_w - margin
            rel_y = margin
        elif position == "左上":
            rel_x = margin
            rel_y = margin
        else:  # 中央
            rel_x = (photo_w - text_w) // 2
            rel_y = (photo_h - text_h) // 2
            
        abs_x = offset_x + rel_x
        abs_y = offset_y + rel_y
            
        tc_clean = text_color_hex.lstrip('#')
        tc_rgb = tuple(int(tc_clean[i:i+2], 16) for i in (0, 2, 4))
        
        draw.text((abs_x, abs_y), wm_text, font=font, fill=(tc_rgb[0], tc_rgb[1], tc_rgb[2], alpha))
        
    elif wm_type == "ロゴ画像" and wm_logo_file is not None:
        logo = Image.open(wm_logo_file).convert("RGBA")
        
        target_w = int(photo_w * (size_ratio / 100.0))
        aspect = logo.height / logo.width
        target_h = int(target_w * aspect)
        logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * (opacity_pct / 100)))
        logo = Image.merge("RGBA", (r, g, b, a))
        
        if position == "右下":
            rel_x = photo_w - target_w - margin
            rel_y = photo_h - target_h - margin
        elif position == "左下":
            rel_x = margin
            rel_y = photo_h - target_h - margin
        elif position == "右上":
            rel_x = photo_w - target_w - margin
            rel_y = margin
        elif position == "左上":
            rel_x = margin
            rel_y = margin
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
st.subheader("🏷️ ハッシュタグ")
default_tags = "#instagram #photo #japan"
tags_input = st.text_area("ハッシュタグを入力・編集", value=default_tags, height=80)

st.subheader("📁 画像を選択")
uploaded_files = st.file_uploader(
    "iPhoneの写真ライブラリ等から画像を選択してください（複数可）", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

if uploaded_files:
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
            
            # 正方形キャンバスの作成
            square_img = Image.new("RGB", (max_side, max_side), bg_color_rgb)
            offset_x = (max_side - photo_w) // 2
            offset_y = (max_side - photo_h) // 2
            square_img.paste(image, (offset_x, offset_y))
            
            # ウォーターマーク処理の適用
            if enable_wm:
                photo_rect = (offset_x, offset_y, photo_w, photo_h)
                square_img = apply_watermark_on_photo(square_img, photo_rect, wm_position, wm_opacity)
            
            # ブラウザダウンロード用バイト処理
            buf = io.BytesIO()
            square_img.save(buf, format="JPEG", quality=95)
            byte_im = buf.getvalue()
            
            # プレビュー表示と個別ダウンロードボタン
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
