import requests
import pandas as pd
import streamlit as st

# --- 1. CẤU HÌNH HỆ THỐNG ---
TOKEN = "8625420422:AAGzsK5MEsJx_38KN7Tl08c1RyyIPgTXpG4"
GROUP_CHAT_ID = "-5057134145"

# --- 2. HÀM GỬI THÔNG BÁO TELEGRAM ---
def send_telegram_alert(product_name, old_price, new_price, store_name, link):
    # Tính toán mức giảm giá thực tế
    discount = round((1 - new_price/old_price) * 100)
    
    # Nội dung tin nhắn định dạng HTML chuyên nghiệp
    message = f"""
🔥 <b>KÈO THƠM LAPTOP - GIẢM {discount}%</b> 🔥

🚀 <b>Sản phẩm:</b> {product_name}
💰 <b>Giá cũ:</b> {old_price:,.0f} đ
✅ <b>Giá mới:</b> {new_price:,.0f} đ
🏪 <b>Cửa hàng:</b> {store_name}

👉 <a href='{link}'>Xem chi tiết tại đây</a>
    """
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Lỗi gửi tin nhắn: {e}")

# --- 3. GIAO DIỆN STREAMLIT (TUẦN 4) ---
st.set_page_config(page_title="TechPrice Final", layout="wide")
st.title("🚀 Hệ Thống Tổng Hợp & Cảnh Báo Giá Laptop")

# --- 4. ĐỌC DỮ LIỆU THẬT ---
# Thay 'data_final.csv' bằng tên file CSV 
try:
    df = pd.read_csv('data_final.csv') 
    
    st.write(f"### ✅ Dữ liệu thực tế ({len(df)} sản phẩm)")
    st.dataframe(df, use_container_width=True)

    # --- 5. NÚT KÍCH HOẠT QUÉT & GỬI BOT ---
    st.sidebar.header("Điều khiển")
    threshold = st.sidebar.slider("Ngưỡng giảm giá để báo Bot (%)", 5, 50, 10)

    if st.sidebar.button("⚡ Kích hoạt quét Deal"):
        count = 0
        st.write("---")
        st.write("🔍 **Nhật ký quét hệ thống:**")
        
        for _, row in df.iterrows():
            # Tính % giảm giá thực tế của từng dòng
            actual_discount = (1 - row['Giá hiện tại']/row['Giá gốc']) * 100
            
            if actual_discount >= threshold:
                send_telegram_alert(
                    row['Tên máy'], 
                    row['Giá gốc'], 
                    row['Giá hiện tại'], 
                    row['Cửa hàng'],
                    row['Link']
                )
                st.write(f"🔔 Đã bắn tin nhắn: {row['Tên máy']} (Giảm {actual_discount:.1f}%)")
                count += 1
        
        if count > 0:
            st.success(f"Hoàn thành! Đã gửi {count} cảnh báo về Telegram.")
        else:
            st.warning("Không tìm thấy máy nào giảm giá đạt ngưỡng yêu cầu.")

except FileNotFoundError:
    st.error("❌ Không tìm thấy file 'data_final.csv'. Hãy đảm bảo file dữ liệu nằm cùng thư mục với code.")