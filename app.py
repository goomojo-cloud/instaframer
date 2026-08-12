import streamlit as st
from PIL import Image, ImageOps
import io

st.set_page_config(page_title="InstaFramer", page_icon="📷", layout="centered")

st.title("📷 InstaFramer")
st.caption("3:2などの写真を枠付き正方形に美しく変換")

# ----------------------------------
# 1. 設定エリア
# ----------------------------------
col1, col2 = st.columns([1, 1])

with col1:
    bg_color_hex = st.color_picker("背景色を選択", "#FFFFFF")

# 16進数カラーコードをRGBに変換
bg_color_hex_clean = bg_color_hex.lstrip('#')
bg_color_rgb = tuple(int(bg_color_hex_clean[i:i+2], 16) for i in (0, 2, 4))

# ----------------------------------
# 2. ハッシュタグエリア
# ----------------------------------
st.subheader("🏷️ ハッシュタグ")
default_tags = "#instagram #photo #japan"
tags_input = st.text_area("ハッシュタグを入力・編集", value=default_tags, height=100)

# ----------------------------------
# 3. 画像アップロード＆変換エリア
# ----------------------------------
st.subheader("📁 画像を選択")
uploaded_files = st.file_uploader(
    "iPhoneの写真ライブラリ等から画像を選択してください（複数可）", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} 枚の画像が選択されました")
    
    st.subheader("✨ 変換結果＆ダウンロード")
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(image)
            
            if image.mode != "RGB":
                image = image.convert("RGB")
                
            width, height = image.size
            max_side = max(width, height)
            
            square_img = Image.new("RGB", (max_side, max_side), bg_color_rgb)
            offset_x = (max_side - width) // 2
            offset_y = (max_side - height) // 2
            square_img.paste(image, (offset_x, offset_y))
            
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