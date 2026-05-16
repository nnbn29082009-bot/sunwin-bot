import telebot, threading, time, requests, string, json, os, pytz, random
from datetime import datetime, timedelta

def get_datetime_hcm():
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)
    return now

# ================== CẤU HÌNH ==================
TOKEN = '8388942457:AAEvSqIT7sHIfbccH55lLp0SFnBqDuMfZnE'
OWNER_ID = 8605217948
bot = telebot.TeleBot(TOKEN)

# ================== KHỞI TẠO LOCK CHO ĐA LUỒNG ==================
data_lock = threading.Lock()

# ================== HÀM LƯU / ĐỌC FILE ==================
def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"Lỗi lưu file {filename}: {e}")

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi đọc file {filename}: {e}")
            return {}
    return {}

def save_keys_file():
    with data_lock:
        tosave = {}
        for k, v in active_keys.items():
            if isinstance(v, datetime):
                tosave[k] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                tosave[k] = str(v)
        save_json("keys.json", tosave)

def save_auth_users_file():
    with data_lock:
        tosave = {}
        for uid, v in authenticated_users.items():
            if isinstance(v, datetime):
                tosave[str(uid)] = v.strftime("%Y-%m-%d %H:%M:%S")
            else:
                tosave[str(uid)] = str(v)
        save_json("auth_users.json", tosave)

def save_kicked_file():
    with data_lock:
        save_json("kicked.json", list(kicked_users))

# ================== DỮ LIỆU BAN ĐẦU ==================
user_data = {}
_active_keys_raw = load_json("keys.json")
_authenticated_raw = load_json("auth_users.json")
_kicked_raw = load_json("kicked.json")

# Convert loaded data
active_keys = {}
for k, v in (_active_keys_raw or {}).items():
    if isinstance(v, str):
        try:
            dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except:
            try:
                dt = datetime.fromisoformat(v)
            except:
                dt = None
        if dt and dt > datetime.now():
            active_keys[k] = dt
    else:
        pass

authenticated_users = {}
if isinstance(_authenticated_raw, dict):
    for uid_str, v in _authenticated_raw.items():
        try:
            dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        except:
            try:
                dt = datetime.fromisoformat(v)
            except:
                dt = None
        if dt and dt > datetime.now():
            try:
                authenticated_users[int(uid_str)] = dt
            except:
                pass
elif isinstance(_authenticated_raw, list):
    for uid in _authenticated_raw:
        try:
            authenticated_users[int(uid)] = datetime.now() + timedelta(days=365*10)
        except:
            pass

authenticated_users[OWNER_ID] = datetime.now() + timedelta(days=365*100)

kicked_users = set(_kicked_raw) if isinstance(_kicked_raw, list) else set()
running_users = set()

# Save cleaned initial files
save_keys_file()
save_auth_users_file()
save_kicked_file()

# ================== HÀM API (ĐÃ SỬA LỖI) ==================
def get_api():
    """
    Trả về: phien(int)|None, kq (string: 'Tài'/'Xỉu' or None), xx (string 'a-b-c')
    """
    try:
        r = requests.get("https://bracket-ellen-roads-prefer.trycloudflare.com/api/tx", timeout=10)
        r.raise_for_status()
        
        js = r.json()
        if not isinstance(js, dict):
            return None, None, None

        phien = js.get("Phien") or js.get("phien_sex") or js.get("phien") or js.get("phiên")
        xx1 = js.get("Xuc_xac_1") if "Xuc_xac_1" in js else js.get("xuc_xac_1") if "xuc_xac_1" in js else js.get("Xuc_xac1") or js.get("d1") or js.get("xuc_xac_1")
        xx2 = js.get("Xuc_xac_2") if "Xuc_xac_2" in js else js.get("xuc_xac_2") if "xuc_xac_2" in js else js.get("Xuc_xac2") or js.get("d2") or js.get("xuc_xac_2")
        xx3 = js.get("Xuc_xac_3") if "Xuc_xac_3" in js else js.get("xuc_xac_3") if "xuc_xac_3" in js else js.get("Xuc_xac3") or js.get("d3") or js.get("xuc_xac_3")
        tong = js.get("Tổng") if "Tổng" in js else js.get("Tong") or js.get("total") or js.get("tong") or js.get("tổng")

        try:
            phien = int(phien)
        except:
            phien = None

        try:
            xx1 = int(xx1) if xx1 is not None else 0
        except:
            xx1 = 0
        try:
            xx2 = int(xx2) if xx2 is not None else 0
        except:
            xx2 = 0
        try:
            xx3 = int(xx3) if xx3 is not None else 0
        except:
            xx3 = 0

        if not phien or xx1 == 0 or xx2 == 0 or xx3 == 0:
            return None, None, None
            
        if not tong:
            tong = xx1 + xx2 + xx3

        if 3 <= tong <= 10:
            kq = "Xỉu"
        elif 11 <= tong <= 18:
            kq = "Tài"
        else:
            return None, None, None

        xx = f"{xx1}-{xx2}-{xx3}"
        return phien, kq, xx
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi kết nối API: {e}")
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Lỗi parse JSON API: {e}")
        return None, None, None
    except Exception as e:
        print(f"Lỗi không xác định trong get_api(): {e}")
        return None, None, None

def do_ben(data):
    if not data:
        return 0
    last = data[-1]
    count = 0
    for i in reversed(data):
        if i == last:
            count += 1
        else:
            break
    return count if count >= 3 else 0
def du_doan(data_kq, dem_sai, pattern_sai, xx, diem_lich_su, data):
    try:
        xx_list = xx.split("-")
        tong = sum(int(x) for x in xx_list)
    except:
        xx_list = ["0","0","0"]
        tong = 0

    data_kq = data_kq[-50:]  # ❗ giảm xuống để tránh nhiễu
    cuoi = data_kq[-1] if data_kq else None
    pattern = "".join("T" if x == "Tài" else "X" for x in data_kq)

    # ================== CHỐNG THUA THÔNG ==================
    # reset nếu thua quá sâu
    if dem_sai >= 5:
        return ("Tài" if tong % 2 else "Xỉu"), 75, "Reset khi thua sâu → đánh theo tổng"

    # đảo mạnh nếu thua liên tiếp
    if dem_sai >= 3:
        du_doan_tx = "Xỉu" if cuoi == "Tài" else "Tài"
        return du_doan_tx, 85, f"Đang thua {dem_sai} → đảo chiều mạnh"

    # ================== AI HỌC NHƯNG GIỚI HẠN ==================
    pattern_memory = data.get("pattern_memory", {})
    matched_pred = None
    matched_confidence = 0

    for pat, stats in pattern_memory.items():
        if pattern.endswith(pat):
            count = stats.get("count", 0)
            correct = stats.get("correct", 0)
            confidence = correct / count if count > 0 else 0

            # ❗ siết điều kiện tránh ảo
            if count >= 5 and confidence >= 0.7:
                if confidence > matched_confidence:
                    matched_confidence = confidence
                    matched_pred = stats.get("next_pred", None)

    if matched_pred:
        return matched_pred, 88, f"Học cầu ({matched_confidence:.2f})"

    # ================== CHỐNG DÍNH CẦU GIẢ ==================
    if len(data_kq) >= 4:
        last4 = data_kq[-4:]
        if last4.count("Tài") == 2 and last4.count("Xỉu") == 2:
            return ("Xỉu" if cuoi == "Tài" else "Tài"), 86, "Cầu nhiễu 2-2 → đảo"

    # ================== XỬ LÝ BỆT (GIẢM ÔM) ==================
    def do_ben(data_kq):
        if not data_kq:
            return 0
        last = data_kq[-1]
        count = 0
        for kq in reversed(data_kq):
            if kq == last:
                count += 1
            else:
                break
        return count

    ben = do_ben(data_kq)

    if ben >= 4:
        # ❗ không ôm mù nữa
        return ("Xỉu" if cuoi == "Tài" else "Tài"), 87, f"Bệt {ben} → bẻ sớm"

    if ben >= 2:
        return cuoi, 80, f"Bệt nhẹ {ben} → theo"

    # ================== XỈ NGẦU (GIỮ NHƯNG GIẢM ĐỘ TIN) ==================
    if len(set(xx_list)) == 1:
        so = xx_list[0]
        if so in ["1", "2", "4"]:
            return "Xỉu", 90, f"3 xí ngầu {so}"
        if so in ["3", "5"]:
            return "Tài", 90, f"3 xí ngầu {so}"

    # ================== LỆCH CẦU ==================
    counts = {"Tài": data_kq.count("Tài"), "Xỉu": data_kq.count("Xỉu")}
    chenh = abs(counts["Tài"] - counts["Xỉu"])

    if chenh >= 4:
        return ("Tài" if counts["Tài"] < counts["Xỉu"] else "Xỉu"), 82, "Cầu lệch → hồi"

    # ================== DEFAULT AN TOÀN ==================
    return ("Tài" if tong >= 11 else "Xỉu"), 70, "An toàn theo tổng"

# ================== XỬ LÝ PHIÊN VÀ GỬI THÔNG BÁO ==================
def xu_ly_phien(phien, kq, xx, chat_id):
    with data_lock:
        if chat_id not in user_data:
            user_data[chat_id] = {
                "last_phien": 0,
                "lich_su_kq": [],
                "lich_su_phan_hoi": [],
                "dem_sai": 0,
                "pattern_sai": set(),
                "so_dung": 0,
                "so_sai": 0,
                "lich_su_diem": [],
                "du_doan_truoc": None,
                "do_tin_cay_truoc": None,
                "phien_truoc": 0,
                "da_be_tai": False,
                "da_be_xiu": False,
                "pattern_memory": {},
                "error_memory": {}
            }

        data = user_data[chat_id]

        if not (phien and kq and xx):
            return

        if not (phien and phien > data.get("last_phien", 0)):
            return

        thong_bao = ""
        if data.get("du_doan_truoc") is not None and phien == data.get("phien_truoc", 0) + 1:
            thang = (data["du_doan_truoc"] == kq)
            thong_bao = "✓" if thang else "X"

            data.setdefault("lich_su_phan_hoi", []).append({
                "time": datetime.now().strftime("%H:%M"),
                "du_doan": data["du_doan_truoc"],
                "kq": kq,
                "thang": thang,
                "phien": phien
            })

            # Cập nhật pattern memory cho AI học
            if len(data["lich_su_kq"]) >= 3:
                pattern_key = "".join("T" if x == "Tài" else "X" for x in data["lich_su_kq"][-4:-1])
                if pattern_key not in data["pattern_memory"]:
                    data["pattern_memory"][pattern_key] = {"count": 0, "correct": 0, "next_pred": data["du_doan_truoc"]}
                
                data["pattern_memory"][pattern_key]["count"] += 1
                if thang:
                    data["pattern_memory"][pattern_key]["correct"] += 1

            # Cập nhật error memory
            if not thang and len(data["lich_su_kq"]) >= 3:
                error_key = tuple(data["lich_su_kq"][-3:])
                data["error_memory"][error_key] = data["error_memory"].get(error_key, 0) + 1

            if thang:
                data["dem_sai"] = 0
            else:
                data["dem_sai"] = data.get("dem_sai", 0) + 1
                if len(data.get("lich_su_kq", [])) >= 3:
                    pattern = tuple(data.get("lich_su_kq", [])[-3:])
                    data.setdefault("pattern_sai", set()).add(pattern)

            data["so_dung"] = data.get("so_dung", 0) + (1 if thang else 0)
            data["so_sai"] = data.get("so_sai", 0) + (0 if thang else 1)

        data["last_phien"] = phien
        data.setdefault("lich_su_kq", []).append(kq)
        if len(data["lich_su_kq"]) > 100:
            data["lich_su_kq"] = data["lich_su_kq"][-100:]

        du_doan_tx, do_tin_cay, loai_cau = du_doan(
            data["lich_su_kq"],
            data.get("dem_sai", 0),
            data.get("pattern_sai", set()),
            xx,
            data.setdefault("lich_su_diem", []),
            data
        )

        data["du_doan_truoc"] = du_doan_tx
        data["do_tin_cay_truoc"] = do_tin_cay
        data["phien_truoc"] = phien

        phien_hien_tai = phien + 1

        try:
            tong_xuc_xac = sum(map(int, xx.split("-")))
        except:
            tong_xuc_xac = None

        try:
            bot.send_message(chat_id, f"""Sun TX
Phiên: {phien} ({xx})
Kết quả: {kq} {tong_xuc_xac if tong_xuc_xac is not None else 'N/A'} {thong_bao or ''}
Phiên: {phien_hien_tai}
Dự đoán: {du_doan_tx} {do_tin_cay}%""")
        except Exception as e:
            print(f"Lỗi gửi message user {chat_id}: {e}")

# ================== VÒNG LẶP TỰ ĐỘNG CHO MỖI USER ==================
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

def auto_loop(uid):
    """
    Vòng lặp cho từng user
    """
    last_error_time = 0
    error_count = 0
    
    while uid in running_users:
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, " Key của bạn đã hết hạn hoặc không hợp lệ. Vui lòng nhập key mới để tiếp tục.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            phien, kq, xx = get_api()

            if phien and kq and xx and (uid == OWNER_ID or check_key(uid)):
                if uid not in user_data:
                    user_data[uid] = {
                        "lich_su_kq": [], "dem_sai": 0, "pattern_sai": set(),
                        "so_dung": 0, "so_sai": 0, "last_phien": 0,
                        "du_doan_truoc": "", "do_tin_cay_truoc": 0,
                        "lich_su_phan_hoi": [], "phien_truoc": 0,
                        "da_be_tai": False, "da_be_xiu": False,
                        "lich_su_diem": [], "pattern_memory": {}, "error_memory": {}
                    }
                xu_ly_phien(phien, kq, xx, uid)
                
        except Exception as e:
            error_count += 1
            current_time = time.time()
            
            if current_time - last_error_time > 60:
                print(f"Lỗi trong auto_loop user {uid}: {e}")
                last_error_time = current_time
                
            if error_count > 10:
                print(f"Dừng auto_loop cho user {uid} do quá nhiều lỗi")
                running_users.discard(uid)
                break
                
        time.sleep(3)

# ================== HANDLER MESSAGE ==================
@bot.message_handler(commands=['start'])
def handle_start(msg):
    uid = msg.from_user.id
    if uid in kicked_users:
        bot.reply_to(msg, " Bạn đã bị chặn!")
        return

    if uid != OWNER_ID:
        expiry = check_key(uid)
        if not expiry:
            bot.send_message(uid, """Hiện đang không có key hoặc key đã hết hạn, hãy mua để được sử dụng.                     
            MENU KEY TOOL
💰 3 Ngày = 50k
💰 1 Tuần = 80k 
💰 1 Tháng = 150k
💰 Vĩnh Viễn = 200k
🔑 Nếu mua key, vui lòng dùng lệnh: /muakey.
""")
            bot.send_message(uid, "Nếu cần tìm hiểu thêm về các lệnh hãy dùng:\n/help .")
            return

    bot.reply_to(msg, " Bắt đầu dự đoán!")

    if uid not in user_data:
        user_data[uid] = {
            "lich_su_kq": [], "dem_sai": 0, "pattern_sai": set(),
            "so_dung": 0, "so_sai": 0, "last_phien": 0,
            "du_doan_truoc": "", "do_tin_cay_truoc": 0,
            "lich_su_phan_hoi": [], "phien_truoc": 0,
            "pattern_memory": {}, "error_memory": {}
        }

    if uid not in running_users:
        running_users.add(uid)
        threading.Thread(target=auto_loop, args=(uid,), daemon=True).start()

    try:
        phien, kq, xx = get_api()
        if phien and kq and xx:
            xu_ly_phien(phien, kq, xx, uid)
    except:
        pass

@bot.message_handler(commands=['stop'])
def handle_stop(msg):
    uid = msg.from_user.id
    running_users.discard(uid)
    bot.reply_to(msg, " Dừng dự đoán.")
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==== CẤU HÌNH FILE + LOCK ====
ORDERS_FILE = "orders.json"
KEYS_FILE = "keys.json"
LOCK = threading.Lock()
OWNER_ID = 8605217948  # Telegram ID admin

# ----- Load / Save orders -----
def load_orders():
    try:
        with LOCK:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return {}

def save_orders(orders):
    with LOCK:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

# ----- Load / Save keys -----
def load_keys():
    try:
        with LOCK:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return {}

def save_keys(keys):
    with LOCK:
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, ensure_ascii=False, indent=2)

# ----- Tạo mã đơn & nội dung chuyển tiền -----
def make_order_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

# ----- Lưu đơn mới -----
def save_new_order(user_id, key_type, order_code):
    orders = load_orders()
    orders[order_code] = {
        "user_id": user_id,
        "key_type": key_type,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    save_orders(orders)

# ----- Tạo key hoàn toàn mới -----
def generate_unique_key():
    keys = load_keys()
    while True:
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if key not in keys:
            return key
# ===================== menu =====================
@bot.message_handler(commands=['menu'])
def handle_menu(msg):
    uid = msg.from_user.id
    running_users.discard(uid)
    bot.reply_to(msg, "MENU KEY TOOL\n"
f"💰 3 NGÀY = 50k\n"
f"💰 1 TUẦN = 80k\n"
f"💰 1 THÁNG = 150k\n"
f"💰 VĨNH VIỄN = 200k\n"
f"🔑 Nếu mua key, vui lòng dùng lệnh: /muakey.")
# ===================== /muakey =====================
@bot.message_handler(commands=['muakey'])
def handle_muakey(msg):
    text = (
        "BANG GIA KEY TOOL\n"
        "3 NGÀY: 50k\n"
        "1 TUẦN: 80k\n"
        "1 THÀNG: 150k\n"
        "VĨNH VIỄN: 200k\n"
        "Nhap lenh:\n"
        "/buy + thoi gian\n"
        "Vi du: /buy3day 1week 1month vip"
    )
    
    bot.reply_to(msg, text)
# ===================== /buy =====================
@bot.message_handler(func=lambda msg: msg.text.startswith('/buy'))
def handle_buy(msg):
    text = msg.text.lower()

    prices = {
        "3day": "50.000VND",
        "1week": "80.000VND",
        "1month": "150.000VND",
        "vip": "200.000VND"
    }

    if "/buy3day" in text:
        key_type = "3ngay"
        display_name = "3 NGÀY"
        price = prices["3day"]
    elif "/buy1week" in text:
        key_type = "1tuan"
        display_name = "1 TUẦN"
        price = prices["1week"]
    elif "/buy1month" in text:
        key_type = "1thang"
        display_name = "1 THÁNG"
        price = prices["1month"]
    elif "/buyvip" in text:
        key_type = "vinhvien"
        display_name = "VĨNH VIỄN"
        price = prices["vip"]
    else:
        bot.reply_to(msg, "Lenh khong hop le. Vi du: /buy3day")
        return

    stk = "8853451801"
    bank = "BIDV BANK"
    receiver = "NGUYEN NGOC BAO NAM"

    order_code = make_order_code()
    user_id = msg.from_user.id

    # lưu chuẩn key_type (không dấu)
    save_new_order(user_id, key_type, order_code)

    text_reply = (
        "THÔNG TIN THANH TOÁN\n"
        f"GÓI: {display_name}\n"
        f"GIÁ: {price}\n"
        f"STK: <code>{stk}</code>\n"
        f"NGÂN HÀNG: {bank}\n"
        f"CHỦ TK: {receiver}\n"
        f"NỘI DUNG: <code>{order_code}</code>\n"
        "TT XONG GỬI BILL CHO ADMIN: @kirosingapore"
    )
    bot.reply_to(msg, text_reply, parse_mode="HTML")
# ----- Tạo key hoàn toàn mới -----
def generate_unique_key():
    keys = load_keys()
    attempts = 0
    while True:
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if key not in keys:
            return key
        attempts += 1
        if attempts > 1000:
            key = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            if key not in keys:
                return key

@bot.message_handler(commands=['done'])
def handle_done(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "BẠN KHÔNG CÓ QUYỀN SỬ DỤNG LỆNH NÀY.")
        return

    try:
        order_code = msg.text.split()[1].strip()
    except IndexError:
        bot.reply_to(msg, "VUI LÒNG NHẬP: /done <MÃ ĐƠN>")
        return

    orders = load_orders()

    if order_code not in orders:
        bot.reply_to(msg, f"ĐƠN {order_code} KHÔNG TỒN TẠI.")
        return

    order_info = orders[order_code]

    if order_info.get("status") == "done":
        bot.reply_to(msg, f"ĐƠN {order_code} ĐÃ ĐƯỢC XỬ LÝ.")
        return

    user_id = order_info["user_id"]
    key_type = order_info["key_type"]
    now = datetime.now()

    # 🔥 CHUẨN HÓA LOẠI GÓI
    loai_hien_thi = {
        "3ngay": "3 NGÀY",
        "1tuan": "1 TUẦN",
        "1thang": "1 THÁNG",
        "vinhvien": "VĨNH VIỄN"
    }.get(key_type, key_type)

    # 🔥 TÍNH HẠN
    if key_type == "3ngay":
        expire_time = now + timedelta(days=3)
    elif key_type == "1tuan":
        expire_time = now + timedelta(days=7)
    elif key_type == "1thang":
        expire_time = now + timedelta(days=30)
    elif key_type == "vinhvien":
        expire_time = now + timedelta(days=100000)
    else:
        expire_time = now + timedelta(days=1)

    # 🔥 TẠO KEY
    key = generate_unique_key()

    keys = load_keys()
    keys[key] = expire_time.isoformat()
    save_keys(keys)

    # 🔥 UPDATE ORDER
    order_info["status"] = "done"
    order_info["delivered_key"] = key
    order_info["done_at"] = now.isoformat()
    orders[order_code] = order_info
    save_orders(orders)

    # 🔥 AUTO KÍCH HOẠT
    authenticated_users[user_id] = expire_time
    save_auth_users_file()

    # 📩 GỬI CHO USER
    bot.send_message(
        user_id,
        f"KÍCH HOẠT THÀNH CÔNG\n"
        f"GÓI: {loai_hien_thi}\n"
        f"HẾT HẠN: {expire_time.strftime('%H:%M %d-%m-%Y')}\n"
        f"KEY: <code>{key}</code>",
        parse_mode="HTML"
    )

    # 🛠 ADMIN LOG
    user = bot.get_chat(user_id)
    username = user.username if user.username else user.first_name

    bot.reply_to(
        msg,
        f"DUYỆT THÀNH CÔNG\n"
        f"ĐƠN: {order_code}\n"
        f"GÓI: {loai_hien_thi}\n"
        f"NGƯỜI DÙNG: @{username}"
    )

    bot.reply_to(msg, f"ID NGƯỜI DÙNG: {user_id}")
@bot.message_handler(commands=['taokey'])
def handle_taokey(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "Khong co quyen.")
        return

    try:
        parts = msg.text.strip().split()
        if len(parts) != 2:
            raise ValueError

        duration_str = parts[1].lower()
        unit = duration_str[-1]
        amount = int(duration_str[:-1])

        now = datetime.now()

        if unit == 'm':
            expire_time = now + timedelta(minutes=amount)
        elif unit == 'h':
            expire_time = now + timedelta(hours=amount)
        elif unit == 'd':
            expire_time = now + timedelta(days=amount)
        elif unit == 'm':  # tháng (viết M hoặc m đều ăn)
            expire_time = now + timedelta(days=30 * amount)
        else:
            bot.reply_to(msg, "Don vi khong hop le. Dung m/h/d/M")
            return

        # 🔥 load file
        keys = load_keys()

        # 🔥 tạo key không trùng
        while True:
            key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            if key not in keys:
                break

        # 🔥 lưu ISO giống /done
        keys[key] = expire_time.isoformat()
        save_keys(keys)

        bot.reply_to(
            msg,
            f"Key: <code>{key}</code>\nHet han: {expire_time.strftime('%H:%M %d-%m-%Y')}",
            parse_mode="HTML"
        )

    except:
        bot.reply_to(msg, "Sai cu phap. Dung: /taokey 30m")
import json
from datetime import datetime

ACTIVE_KEYS_FILE = "active_keys.json"
AUTH_USERS_FILE = "authenticated_users.json"

# Hàm lưu active_keys ra file
def save_keys_file():
    with open(ACTIVE_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump({k: v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v 
                   for k, v in active_keys.items()}, f, ensure_ascii=False, indent=2)

# Hàm load active_keys từ file
def load_keys_file():
    global active_keys
    try:
        with open(ACTIVE_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            active_keys = {k: datetime.strptime(v, "%Y-%m-%d %H:%M:%S") for k, v in data.items()}
    except:
        active_keys = {}

# Hàm lưu authenticated_users ra file
def save_auth_users_file():
    with open(AUTH_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, datetime) else v 
                   for k, v in authenticated_users.items()}, f, ensure_ascii=False, indent=2)

# Hàm load authenticated_users từ file
def load_auth_users_file():
    global authenticated_users
    try:
        with open(AUTH_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            authenticated_users = {int(k): datetime.strptime(v, "%Y-%m-%d %H:%M:%S") for k, v in data.items()}
    except:
        authenticated_users = {}

# Load dữ liệu khi bot khởi động
load_keys_file()
load_auth_users_file()

# ===== LỆNH /key =====
@bot.message_handler(commands=['key'])
def handle_key(msg):
    uid = msg.from_user.id
    parts = msg.text.strip().split()

    keys = load_keys()  # 🔥 luôn load từ file

    # OWNER xem danh sách key
    if uid == OWNER_ID and len(parts) == 1:
        text = "\n".join(
            f"{k} → {datetime.fromisoformat(v).strftime('%H:%M %d-%m-%Y')}"
            for k, v in keys.items()
        )
        bot.reply_to(msg, f"Danh sach key:\n{text or 'Trong'}")
        return

    # USER nhập key
    if len(parts) == 2:
        key = parts[1].strip()

        if key not in keys:
            bot.reply_to(msg, "Key sai hoac khong ton tai.")
            return

        expire = datetime.fromisoformat(keys[key])

        if expire <= datetime.now():
            bot.reply_to(msg, "Key da het han.")
            keys.pop(key, None)
            save_keys(keys)
            return

        # kích hoạt user
        authenticated_users[uid] = expire
        save_auth_users_file()

        # xóa key sau khi dùng
        keys.pop(key, None)
        save_keys(keys)

        bot.reply_to(msg, "Kich hoat thanh cong!")
        try:
            bot.send_message(uid, "Chuc ban su dung vui ve!")
        except:
            pass
    else:
        bot.reply_to(msg, "Sai cu phap. Dung: /key <ma_key>")
@bot.message_handler(commands=['menugame'])
def handle_menugame(msg):
    menugame_text = """GAME SUNWIN
/start /stop /stopsicbosun /sicbosun /sicbolive /stopsicbolive - Bật,Tắt dự đoán Sun
        GAME HIT CLUB
/sicbohit /hitxanh /hitmd5 /stopsicbohit /stophitxanh /stophitmd5 - Bật,Tắt dự đoán Hit
        GAME 789CLUB
/club789 /stopclub789 - Bật,Tắt dự đoán Club789
        GAME 68GB
/gb68md5 /stopgb68md5 -Bật,Tắt dự đoán 68gb
        GAME B52 CLUB
/b52hu /b52md5 /stopb52hu /stopb52md5 - Bật,Tắt dự đoán B52
        GAME LC79
/lc79 /lc79md5 /stoplc79 /stoplc79md5 - Bật,Tắt dự đoán Lc"""
    bot.reply_to(msg, menugame_text)       
@bot.message_handler(commands=['help'])
def handle_help(msg):
    help_text = """📌 Danh sách lệnh bạn có thể dùng:
        LỆNH TỔNG HỢP
/menu - Menu key bot
/reset - Reset dữ liệu bot
/key <mã> bỏ ngoặc - Nhập key để kích hoạt bot
/muakey - Tạo lệnh mua key bot 
/lichsu - Xem lịch sử dự đoán và kết quả
/checkkey - Xem thời hạn key 
/menugame - Menu Game Tool
👉 Nếu gặp lỗi hoặc cần hỗ trợ, vui lòng liên hệ Admin: @contimvonat
  """
    bot.reply_to(msg, help_text)

@bot.message_handler(commands=['checkkey'])
def handle_checkkey(msg):
    uid = msg.from_user.id
    expire = check_key(uid)

    if not expire and uid != OWNER_ID:
        bot.reply_to(msg, " Bạn chưa kích hoạt key hoặc key đã hết hạn.")
        return

    if uid == OWNER_ID:
        bot.reply_to(msg, " Bạn là Admin, không cần key.")
        return

    now = datetime.now()
    remaining = expire - now
    days = remaining.days
    hours, remainder = divmod(remaining.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    text = "🔑 Key của bạn còn lại: "
    if days > 0:
        text += f"{days} ngày "
    if hours > 0:
        text += f"{hours} giờ "
    if minutes > 0:
        text += f"{minutes} phút"

    text += f"\n🕒 Hết hạn: {expire.strftime('%H:%M %d-%m-%Y')}"

    bot.reply_to(msg, text)

@bot.message_handler(commands=['lichsu'])
def handle_lichsu(msg):
    uid = msg.from_user.id
    if uid not in authenticated_users and uid != OWNER_ID:
        bot.reply_to(msg, " Bạn chưa được cấp quyền.")
        return
    ls = user_data.get(uid, {}).get("lich_su_phan_hoi", [])
    if not ls:
        bot.reply_to(msg, "Chưa có lịch sử.")
        return
    text = "\n".join(
        f"Phiên {x['phien']}| Dự: {x['du_doan']}| KQ: {x['kq']}| {'✅' if x['thang'] else '❌'}"
        for x in ls[-20:][::-1]
    )
    bot.reply_to(msg, f" Lịch sử:\n{text}")

@bot.message_handler(commands=['xoakey'])
def handle_xoakey(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, " Không có quyền.")
        return
    try:
        key = msg.text.split()[1]
        if key in active_keys:
            active_keys.pop(key, None)
            save_keys_file()
            bot.reply_to(msg, f" Đã xóa key {key}.")
        else:
            bot.reply_to(msg, " Key không tồn tại.")
    except:
        bot.reply_to(msg, " Cú pháp: /xoakey <key>")

@bot.message_handler(commands=['kickid'])
def handle_kick(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, " Không có quyền.")
        return
    try:
        uid = int(msg.text.split()[1])
        authenticated_users.pop(uid, None)
        kicked_users.add(uid)
        save_auth_users_file()
        save_kicked_file()
        running_users.discard(uid)
        bot.reply_to(msg, f" Đã kick ID: {uid}")
    except:
        bot.reply_to(msg, " Cú pháp: /kickid <id>")

@bot.message_handler(commands=['unkickid'])
def handle_unkick(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, " Không có quyền.")
        return
    try:
        uid = int(msg.text.split()[1])
        kicked_users.discard(uid)
        save_kicked_file()
        bot.reply_to(msg, f" Đã mở khóa ID: {uid}")
    except:
        bot.reply_to(msg, " Cú pháp: /unkickid <id>")

@bot.message_handler(commands=['uidstart'])
def handle_uidstart(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, " Không có quyền.")
        return
    text = "👥 Users đang dùng bot:\n"
    for uid in running_users:
        if uid in authenticated_users and uid not in kicked_users:
            try:
                user = bot.get_chat(uid)
                username = f"@{user.username}" if getattr(user, "username", None) else "Không rõ"
                text += f"• {uid} ({username})\n"
            except:
                text += f"• {uid} (Không thể lấy username)\n"
    bot.reply_to(msg, text)

@bot.message_handler(commands=['reset'])
def handle_reset(msg):
    uid = msg.from_user.id
    parts = msg.text.split()
    if uid == OWNER_ID and len(parts) > 1 and parts[1].lower() == "all":
        active_keys.clear()
        authenticated_users.clear()
        authenticated_users[OWNER_ID] = datetime.now() + timedelta(days=365*100)
        kicked_users.clear()
        save_keys_file()
        save_auth_users_file()
        save_kicked_file()
        user_data.clear()
        bot.reply_to(msg, "Đã xóa toàn bộ dữ liệu persistent (keys/auth/kicked).")
        return

    user_data.pop(uid, None)
    running_users.discard(uid)
    bot.reply_to(msg, "Đã reset dữ liệu, vui lòng /start để bắt đầu lại.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== HÀM DỰ ĐOÁN =====
def predict_taixiu(lich_su):

    if len(lich_su) < 5:
        return "ĐANG PHÂN TÍCH", [], 50, None

    recent = lich_su[-20:]
    last5 = lich_su[-5:]

    tai, xiu = 0, 0
    freq = {}
    pattern = ""

    for i, t in enumerate(recent):
        weight = (i + 1) / len(recent)

        if t >= 11:
            tai += weight
            pattern += "T"
        else:
            xiu += weight
            pattern += "X"

        freq[t] = freq.get(t, 0) + weight

    last3 = pattern[-3:]
    streak = 1

    for i in range(len(pattern)-1, 0, -1):
        if pattern[i] == pattern[i-1]:
            streak += 1
        else:
            break

    last = pattern[-1]

    if streak >= 4:
        prediction = "TÀI" if last == "T" else "XỈU"
    elif streak == 3:
        prediction = "TÀI" if last == "T" else "XỈU"
    elif last3 == "TTT":
        prediction = "XỈU"
    elif last3 == "XXX":
        prediction = "TÀI"
    elif pattern[-2:] in ["TX", "XT"]:
        prediction = "TÀI" if pattern[-2] == "T" else "XỈU"
    else:
        prediction = "TÀI" if tai > xiu else "XỈU"

    if prediction == "TÀI":
        candidates = list(range(11, 18))
    else:
        candidates = list(range(4, 11))

    center_bias = {
        4:1,5:2,6:3,7:4,8:5,9:4,10:3,
        11:3,12:4,13:5,14:4,15:3,16:2,17:1
    }

    trend_boost = {}
    for t in last5:
        trend_boost[t] = trend_boost.get(t, 0) + 2

    scored = []
    for k in candidates:
        score = (
            freq.get(k, 0) * 0.6 +
            center_bias.get(k, 0) * 0.3 +
            trend_boost.get(k, 0)
        )
        scored.append((k, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    vi = [k for k, v in scored[:3]]

    # ===== XÚC XẮC =====
    combos = []

    for a in range(1,7):
        for b in range(1,7):
            for c in range(1,7):
                if a + b + c in vi:
                    combos.append((a, b, c))

    combo_str = None
    if combos:
        pick = combos[len(combos)//2]  # chọn giữa (không cần random)
        combo_str = f"{pick[0]}-{pick[1]}-{pick[2]}"

    total = tai + xiu
    tin_cay = int((max(tai, xiu) / total) * 100)

    if streak >= 3:
        tin_cay += 5

    if tin_cay > 95:
        tin_cay = 95

    return prediction, vi, tin_cay, combo_str


# ===== AUTO =====
def sicbosun_auto(uid, chat_id):
    time = __import__("time")
    urllib = __import__("urllib.request").request
    json = __import__("json")

    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:
        try:
            if uid != OWNER_ID:
                if not check_key(uid):
                    bot.send_message(uid, "Key hết hạn!")
                    running_users.discard(uid)
                    break

            try:
                res = urllib.urlopen(
                    "https://afterwards-motels-honors-vendors.trycloudflare.com/api/sunsicbo",
                    timeout=5
                )
                data = json.loads(res.read().decode())
            except:
                time.sleep(3)
                continue

            phien = data.get("phien")
            tong = data.get("tong")
            ket_qua = data.get("ket_qua")

            xx1 = data.get("xuc_xac_1")
            xx2 = data.get("xuc_xac_2")
            xx3 = data.get("xuc_xac_3")

            if not phien or tong is None:
                time.sleep(3)
                continue

            tong = int(tong)

            if uid in user_data and user_data[uid].get("last_phien") == phien:
                time.sleep(3)
                continue

            user_data.setdefault(uid, {
                "lich_su_diem": [],
                "last_phien": 0
            })

            user_data[uid]["lich_su_diem"].append(tong)

            if len(user_data[uid]["lich_su_diem"]) > 50:
                user_data[uid]["lich_su_diem"].pop(0)

            du_doan, vi, tin_cay, combo = predict_taixiu(
                user_data[uid]["lich_su_diem"]
            )

            msg_text = (
                f"🎲 SicBo Sun\n"
                f"Phiên: {phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"────────────\n"
                f"Dự đoán: {du_doan} {tin_cay}%\n"
                f"Gợi ý vị: {', '.join(map(str, vi))}"
            )

            if combo:
                msg_text += f"\nXúc xắc đẹp: {combo}"

            bot.send_message(chat_id, msg_text)

            user_data[uid]["last_phien"] = phien

        except Exception as e:
            error_count += 1
            now = time.time()

            if now - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = now

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== COMMAND =====
@bot.message_handler(commands=['sicbosun'])
def sicbosun_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key!")
            return

    if uid in running_users:
        bot.reply_to(msg, "Đang chạy rồi!")
        return

    bot.reply_to(msg, "🚀 Bắt đầu Sicbo Sun...")

    threading.Thread(
        target=sicbosun_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


@bot.message_handler(commands=['stopsicbosun'])
def stopsicbosun_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Chưa chạy!")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "⛔ Đã dừng.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== HÀM DỰ ĐOÁN =====
def predict_taixiu(lich_su):

    if len(lich_su) < 5:
        return "ĐANG PHÂN TÍCH", [], 50, None

    recent = lich_su[-20:]
    last5 = lich_su[-5:]

    tai, xiu = 0, 0
    freq = {}
    pattern = ""

    for i, t in enumerate(recent):
        weight = (i + 1) / len(recent)

        if t >= 11:
            tai += weight
            pattern += "T"
        else:
            xiu += weight
            pattern += "X"

        freq[t] = freq.get(t, 0) + weight

    last3 = pattern[-3:]
    streak = 1

    for i in range(len(pattern)-1, 0, -1):
        if pattern[i] == pattern[i-1]:
            streak += 1
        else:
            break

    last = pattern[-1]

    if streak >= 4:
        prediction = "TÀI" if last == "T" else "XỈU"
    elif streak == 3:
        prediction = "TÀI" if last == "T" else "XỈU"
    elif last3 == "TTT":
        prediction = "XỈU"
    elif last3 == "XXX":
        prediction = "TÀI"
    elif pattern[-2:] in ["TX", "XT"]:
        prediction = "TÀI" if pattern[-2] == "T" else "XỈU"
    else:
        prediction = "TÀI" if tai > xiu else "XỈU"

    if prediction == "TÀI":
        candidates = list(range(11, 18))
    else:
        candidates = list(range(4, 11))

    center_bias = {
        4:1,5:2,6:3,7:4,8:5,9:4,10:3,
        11:3,12:4,13:5,14:4,15:3,16:2,17:1
    }

    trend_boost = {}
    for t in last5:
        trend_boost[t] = trend_boost.get(t, 0) + 2

    scored = []
    for k in candidates:
        score = (
            freq.get(k, 0) * 0.6 +
            center_bias.get(k, 0) * 0.3 +
            trend_boost.get(k, 0)
        )
        scored.append((k, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    vi = [k for k, v in scored[:3]]

    # ===== XÚC XẮC =====
    combos = []

    for a in range(1,7):
        for b in range(1,7):
            for c in range(1,7):
                if a + b + c in vi:
                    combos.append((a, b, c))

    combo_str = None
    if combos:
        pick = combos[len(combos)//2]  # chọn giữa (không cần random)
        combo_str = f"{pick[0]}-{pick[1]}-{pick[2]}"

    total = tai + xiu
    tin_cay = int((max(tai, xiu) / total) * 100)

    if streak >= 3:
        tin_cay += 5

    if tin_cay > 95:
        tin_cay = 95

    return prediction, vi, tin_cay, combo_str


# ===== AUTO =====
def sicbolive_auto(uid, chat_id):
    time = __import__("time")
    urllib = __import__("urllib.request").request
    json = __import__("json")

    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:
        try:
            if uid != OWNER_ID:
                if not check_key(uid):
                    bot.send_message(uid, "Key hết hạn!")
                    running_users.discard(uid)
                    break

            try:
                res = urllib.urlopen(
                    "https://letters-carries-hip-seeking.trycloudflare.com/sun/x88",
                    timeout=5
                )
                data = json.loads(res.read().decode())
            except:
                time.sleep(3)
                continue

            phien = data.get("phien")
            tong = data.get("tong")
            ket_qua = data.get("ket_qua")

            xx1 = data.get("xuc_xac_1")
            xx2 = data.get("xuc_xac_2")
            xx3 = data.get("xuc_xac_3")

            if not phien or tong is None:
                time.sleep(3)
                continue

            tong = int(tong)

            if uid in user_data and user_data[uid].get("last_phien") == phien:
                time.sleep(3)
                continue

            user_data.setdefault(uid, {
                "lich_su_diem": [],
                "last_phien": 0
            })

            user_data[uid]["lich_su_diem"].append(tong)

            if len(user_data[uid]["lich_su_diem"]) > 50:
                user_data[uid]["lich_su_diem"].pop(0)

            du_doan, vi, tin_cay, combo = predict_taixiu(
                user_data[uid]["lich_su_diem"]
            )

            msg_text = (
                f"🎲 SicBo Live\n"
                f"Phiên: {phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"────────────\n"
                f"Dự đoán: {du_doan} {tin_cay}%\n"
                f"Gợi ý vị: {', '.join(map(str, vi))}"
            )

            if combo:
                msg_text += f"\nXúc xắc đẹp: {combo}"

            bot.send_message(chat_id, msg_text)

            user_data[uid]["last_phien"] = phien

        except Exception as e:
            error_count += 1
            now = time.time()

            if now - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = now

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== COMMAND =====
@bot.message_handler(commands=['sicbolive'])
def sicbolive_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key!")
            return

    if uid in running_users:
        bot.reply_to(msg, "Đang chạy rồi!")
        return

    bot.reply_to(msg, "🚀 Bắt đầu Sicbo Live...")

    threading.Thread(
        target=sicbolive_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


@bot.message_handler(commands=['stopsicbolive'])
def stopsicbolive_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Chưa chạy!")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "⛔ Đã dừng.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()
group_start_times = {}  # Lưu thời gian bắt đầu nhóm
group_stats_data = {}   # Lưu thống kê riêng cho nhóm  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_gb68_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO 68GB MD5 =====
def gb68md5_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID and msg.chat.id != GROUP_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(msg.chat.id, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://character-retention-accepts-bouquet.trycloudflare.com/api/68/md5", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_gb68md5") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_gb68md5"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_gb68", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_gb68"].append(state)

            user_data[uid]["history_gb68"] = user_data[uid]["history_gb68"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_gb68_ai(user_data[uid]["history_gb68"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"68GB MD5\n"
                f"Phiên:#{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả:{ket_qua} {tong}\n"
                f"=============\n"
                f"Phiên:#{phien_ht}\n"
                f"Đoán:{du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['gb68md5'])
def gb68md5_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID and msg.chat.id != GROUP_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "68GB MD5 đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI 68GB MD5...")

    threading.Thread(
        target=gb68md5_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stopgb68md5'])
def stopgb68md5_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng 68GB MD5.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AUTO SICBO HIT CHO USER RIÊNG =====
def sicbohit_auto(uid, chat_id):
    """
    Vòng lặp riêng cho từng user
    """
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, " Key của bạn đã hết hạn hoặc không hợp lệ. Vui lòng nhập key mới để tiếp tục.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://sichit.onrender.com/sicbo", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")
            if not phien or (uid in user_data and user_data[uid].get("last_phien_hit") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_hit"] = phien

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("Xuc_xac1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("Xuc_xac2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("Xuc_xac3") or data.get("d3")
            tong = data.get("Tổng") or data.get("Tong") or data.get("total") or data.get("tong")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")
            phien_ht = data.get("phien_hien_tai")
            du_doan = data.get("du_doan")
            vi = data.get("dudoan_vi", [])
            tin_cay = data.get("do_tin_cay")

            msg_text = (
                f"SicBo Hit\n"
                f"Phiên: {phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"Phiên tiếp: {phien_ht}\n"
                f"Dự đoán: {du_doan} {tin_cay}\n"
                f"Gợi ý vị: {vi}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()
            if current_time - last_error_time > 60:
                print(f"Lỗi trong auto_loop user {uid}: {e}")
                last_error_time = current_time
            if error_count > 10:
                print(f"Dừng auto_loop Sicbo Hit cho user {uid} do quá nhiều lỗi")
                running_users.discard(uid)
                break

        time.sleep(3)

# ===== LỆNH /sicbohit =====
@bot.message_handler(commands=['sicbohit'])
def sicbohit_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # Kiểm tra user bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # Kiểm tra key nếu không phải admin
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key, vui lòng kích hoạt để sử dụng lệnh.")
            return

    if uid in running_users:
        bot.reply_to(msg, "Sicbo Hit đang chạy")
        return

    bot.reply_to(msg, "Bắt đầu dự đoán Sicbo Hit")

    threading.Thread(
        target=sicbohit_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()
# ===== LỆNH /stopsicbohit =====
@bot.message_handler(commands=['stopsicbohit'])
def stopsicbohit_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy Sicbo Hit hoặc đã dừng rồi.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Dừng dự đoán Sicbo Hit.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()
group_start_times = {}  # Lưu thời gian bắt đầu nhóm
group_stats_data = {}   # Lưu thống kê riêng cho nhóm  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_hitxanh_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO B52 MD5 =====
def hitxanh_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID and msg.chat.id != GROUP_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(msg.chat.id, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://nirvana-corners-discussing-treating.trycloudflare.com/api/tx", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_hitxanh") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_hitxanh"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_hitxanh", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_hitxanh"].append(state)

            user_data[uid]["history_hitxanh"] = user_data[uid]["history_hitxanh"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_hitxanh_ai(user_data[uid]["history_hitxanh"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"Hit Xanh\n"
                f"Phiên:#{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả:{ket_qua} {tong}\n"
                f"=============\n"
                f"Phiên:#{phien_ht}\n"
                f"Đoán:{du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['hitxanh'])
def hitxanh_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID and msg.chat.id != GROUP_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "Hit Xanh đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI Hit Xanh...")

    threading.Thread(
        target=hitxanh_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stophitxanh'])
def stophitxanh_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng Hit Xanh.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_hit_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO B52 MD5 =====
def hitmd5_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://letting-tackle-newton-oak.trycloudflare.com/api/tx", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_hitmd5") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_hitmd5"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_hit", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_hit"].append(state)

            user_data[uid]["history_hit"] = user_data[uid]["history_hit"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_hit_ai(user_data[uid]["history_hit"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"HIT MD5\n"
                f"Phiên: #{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"--------------------------\n"
                f"Phiên tiếp: #{phien_ht}\n"
                f"Dự đoán: {du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['hitmd5'])
def md5_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "HIT MD5 đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI HIT MD5...")

    threading.Thread(
        target=hitmd5_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stophitmd5'])
def stophitmd5_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng HIT MD5.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_lc79_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO LC79 =====
def lc79_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://chance-compete-chambers-feelings.trycloudflare.com/api/tx", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_lc79") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_lc79"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_lc79", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_lc79"].append(state)

            user_data[uid]["history_lc79"] = user_data[uid]["history_lc79"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_lc79_ai(user_data[uid]["history_lc79"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"LC79\n"
                f"Phiên: #{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"--------------------------\n"
                f"Phiên tiếp: #{phien_ht}\n"
                f"Dự đoán: {du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['lc79'])
def lc79_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "LC79 đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI LC79...")

    threading.Thread(
        target=lc79_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stoplc79'])
def stoplc79_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng LC79.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_lc79md5_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO LC79 MD5 =====
def lc79md5_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://chance-compete-chambers-feelings.trycloudflare.com/api/txmd5", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_lc79md5") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_lc79md5"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_lc79md5", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_lc79md5"].append(state)

            user_data[uid]["history_lc79md5"] = user_data[uid]["history_lc79md5"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_lc79md5_ai(user_data[uid]["history_lc79md5"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"LC79 MD5\n"
                f"Phiên: #{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"--------------------------\n"
                f"Phiên tiếp: #{phien_ht}\n"
                f"Dự đoán: {du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['lc79md5'])
def lc79md5_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "LC79 MD5 đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI LC79 MD5...")

    threading.Thread(
        target=lc79md5_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stoplc79md5'])
def stoplc79md5_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng LC79 MD5.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_b52_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO B52 MD5 =====
def b52md5_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://gold-ultra-fails-handles.trycloudflare.com/txmd5", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_b52md5") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_b52md5"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_b52", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_b52"].append(state)

            user_data[uid]["history_b52"] = user_data[uid]["history_b52"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_b52_ai(user_data[uid]["history_b52"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"B52 MD5\n"
                f"Phiên: #{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"--------------------------\n"
                f"Phiên tiếp: #{phien_ht}\n"
                f"Dự đoán: {du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['b52md5'])
def b52md5_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "B52 MD5 đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI B52 MD5...")

    threading.Thread(
        target=b52md5_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stopb52md5'])
def stopb52md5_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng B52 MD5.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AI LOGIC (HỌC TRƯỢT + TRỌNG SỐ) =====
def predict_789club_ai(history):
    if len(history) < 10:
        return f"{len(history)}/10", 0

    train = history[-10:]
    tx = [x.split("_")[0] for x in train]

    m1 = {}
    for i in range(len(tx) - 1):
        a, b = tx[i], tx[i+1]
        weight = i + 1

        if a not in m1:
            m1[a] = {"TÀI": 0, "XỈU": 0}

        m1[a][b] += weight

    m2 = {}
    for i in range(len(tx) - 2):
        key = (tx[i], tx[i+1])
        nxt = tx[i+2]
        weight = i + 1

        if key not in m2:
            m2[key] = {"TÀI": 0, "XỈU": 0}

        m2[key][nxt] += weight

    last1 = tx[-1]
    last2 = (tx[-2], tx[-1])

    if last2 in m2:
        tai = m2[last2]["TÀI"]
        xiu = m2[last2]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    if last1 in m1:
        tai = m1[last1]["TÀI"]
        xiu = m1[last1]["XỈU"]
        if tai + xiu > 0:
            if tai > xiu:
                return "TÀI", int(50 + (tai/(tai+xiu))*50)
            elif xiu > tai:
                return "XỈU", int(50 + (xiu/(tai+xiu))*50)

    return "TÀI", 50


# ===== AUTO 789CLUB =====
def club789_auto(uid, chat_id):
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:   # ✅ PHẢI NẰM TRONG HÀM
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, "Key hết hạn hoặc không hợp lệ.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://dependent-epinions-somebody-enclosed.trycloudflare.com/api/tx", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien") or data.get ("phiên")

            if not phien or (uid in user_data and user_data[uid].get("last_phien_club789") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_club789"] = phien

            # ===== FIX PHIÊN TIẾP =====
            try:
                phien_ht = int(phien) + 1
            except:
                phien_ht = "..."

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("d3")

            tong = data.get("Tong") or data.get("tong") or data.get("total")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")

            # ===== LƯU HISTORY =====
            user_data[uid].setdefault("history_club789", [])

            if ket_qua and tong:
                state = f"{ket_qua.upper()}_{tong}"
                user_data[uid]["history_club789"].append(state)

            user_data[uid]["history_club789"] = user_data[uid]["history_club789"][-50:]

            # ===== AI =====
            du_doan, tin_cay = predict_789club_ai(user_data[uid]["history_club789"])

            if tin_cay == 0:
                du_doan_text = du_doan
            else:
                du_doan_text = f"{du_doan}"

            msg_text = (
                f"CLUB789\n"
                f"Phiên: #{phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"--------------------------\n"
                f"Phiên tiếp: #{phien_ht}\n"
                f"Dự đoán: {du_doan_text}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()

            if current_time - last_error_time > 60:
                print(f"Lỗi user {uid}: {e}")
                last_error_time = current_time

            if error_count > 10:
                running_users.discard(uid)
                break

        time.sleep(3)
# ===== LỆNH START =====
@bot.message_handler(commands=['club789'])
def club789_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # check key
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key.")
            return

    # đang chạy rồi
    if uid in running_users:
        bot.reply_to(msg, "789CLUB đang chạy rồi.")
        return

    bot.reply_to(msg, "Bắt đầu AI 789CLUB...")

    threading.Thread(
        target=club789_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()


# ===== LỆNH STOP =====
@bot.message_handler(commands=['stopclub789'])
def stopclub789_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy hoặc đã dừng.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Đã dừng 789.")
# ===== QUẢN LÝ TRẠNG THÁI GAME =====
game_running = {}
game_last_phien = {}
running_users = set()  # lưu user đang chạy
user_data = {}         # lưu data user

# ===== HÀM CHECK KEY =====
def check_key(uid):
    """
    Kiểm tra key của user có hợp lệ không.
    """
    with data_lock:
        expiry = authenticated_users.get(uid)
        if not expiry:
            return None

        if isinstance(expiry, str):
            try:
                expiry = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
                authenticated_users[uid] = expiry
                save_auth_users_file()
            except Exception as e:
                print(f"Lỗi convert expiry string: {e}")
                return None

        now = datetime.now()
        if isinstance(expiry, datetime) and expiry > now:
            return expiry
        
        return None

# ===== AUTO B52 HŨ CHO USER RIÊNG =====
def b52hu_auto(uid, chat_id):
    """
    Vòng lặp riêng cho từng user
    """
    last_error_time = 0
    error_count = 0
    running_users.add(uid)

    while uid in running_users:
        try:
            if uid != OWNER_ID:
                expiry = check_key(uid)
                if not expiry:
                    try:
                        bot.send_message(uid, " Key của bạn đã hết hạn hoặc không hợp lệ. Vui lòng nhập key mới để tiếp tục.")
                    except:
                        pass
                    running_users.discard(uid)
                    break

            r = requests.get("https://b52-cbqn.onrender.com/api/taixiu", timeout=5)
            if r.status_code != 200:
                time.sleep(3)
                continue

            data = r.json()
            phien = data.get("Phien") or data.get("phien")
            if not phien or (uid in user_data and user_data[uid].get("last_phien_b52hu") == phien):
                time.sleep(3)
                continue

            user_data.setdefault(uid, {})
            user_data[uid]["last_phien_b52hu"] = phien

            xx1 = data.get("Xuc_xac_1") or data.get("xuc_xac_1") or data.get("Xuc_xac1") or data.get("d1")
            xx2 = data.get("Xuc_xac_2") or data.get("xuc_xac_2") or data.get("Xuc_xac2") or data.get("d2")
            xx3 = data.get("Xuc_xac_3") or data.get("xuc_xac_3") or data.get("Xuc_xac3") or data.get("d3")
            tong = data.get("Tổng") or data.get("Tong") or data.get("total") or data.get("tong")
            ket_qua = data.get("Ket_qua") or data.get("ket_qua")
            phien_ht = data.get("phien_hien_tai")
            du_doan = data.get("du_doan")
            tin_cay = data.get("do_tin_cay")

            msg_text = (
                f"B52 Hũ\n"
                f"Phiên: {phien} ({xx1}-{xx2}-{xx3})\n"
                f"Kết quả: {ket_qua} {tong}\n"
                f"Phiên tiếp: {phien_ht}\n"
                f"Dự đoán: {du_doan} {tin_cay}"
            )

            bot.send_message(chat_id, msg_text)

        except Exception as e:
            error_count += 1
            current_time = time.time()
            if current_time - last_error_time > 60:
                print(f"Lỗi trong auto_loop user {uid}: {e}")
                last_error_time = current_time
            if error_count > 10:
                print(f"Dừng auto_loop B52 Hũ cho user {uid} do quá nhiều lỗi")
                running_users.discard(uid)
                break

        time.sleep(3)

# ===== LỆNH /b52hu =====
@bot.message_handler(commands=['b52hu'])
def b52hu_cmd(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id

    # Kiểm tra user bị chặn
    if uid in kicked_users:
        bot.reply_to(msg, "Bạn đã bị chặn!")
        return

    # Kiểm tra key nếu không phải admin
    if uid != OWNER_ID:
        if not check_key(uid):
            bot.reply_to(msg, "Bạn chưa kích hoạt key, vui lòng kích hoạt để sử dụng lệnh.")
            return

    if uid in running_users:
        bot.reply_to(msg, "B52 Hũ đang chạy")
        return

    bot.reply_to(msg, "Bắt đầu dự đoán B52 Hũ")

    threading.Thread(
        target=b52hu_auto,
        args=(uid, chat_id),
        daemon=True
    ).start()
@bot.message_handler(commands=['stopb52hu'])
def stopb52hu_cmd(msg):
    uid = msg.from_user.id

    if uid not in running_users:
        bot.reply_to(msg, "Bạn chưa chạy B52 Hũ hoặc đã dừng rồi.")
        return

    running_users.discard(uid)
    bot.reply_to(msg, "Dừng dự đoán B52 Hũ.")
# ================== Khởi động BOT ==================
print(" Xâm nhập thành công.")

save_keys_file()
save_auth_users_file()
save_kicked_file()
try:
    bot.infinity_polling(skip_pending=True)

except KeyboardInterrupt:
    print("Bot đang dừng...")
    save_keys_file()
    save_auth_users_file()
    save_kicked_file()
    print("Đã lưu dữ liệu và thoát.")

except Exception as e:
    print(f"Lỗi không xác định: {e}")