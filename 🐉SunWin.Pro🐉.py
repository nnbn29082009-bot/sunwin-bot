import telebot, threading, time, requests, random, string, json, os
from datetime import datetime, timedelta

# ================== CẤU HÌNH ==================
TOKEN = '8176274816:AAEGj0JqTX_psPEwJpMNsccygdP2vME9GoE'
OWNER_ID = 7061786824
bot = telebot.TeleBot(TOKEN)

# ================== HÀM LƯU / ĐỌC FILE ==================
def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_keys_file():
    # lưu active_keys dưới dạng string yyyy-mm-dd HH:MM:SS
    tosave = {}
    for k, v in active_keys.items():
        if isinstance(v, datetime):
            tosave[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            tosave[k] = str(v)
    save_json("keys.json", tosave)

def save_auth_users_file():
    # authenticated_users: dict { str(uid): "YYYY-mm-dd HH:MM:SS" }
    tosave = {}
    for uid, v in authenticated_users.items():
        if isinstance(v, datetime):
            tosave[str(uid)] = v.strftime("%Y-%m-%d %H:%M:%S")
        else:
            tosave[str(uid)] = str(v)
    save_json("auth_users.json", tosave)

def save_kicked_file():
    save_json("kicked.json", list(kicked_users))
    
# ================== DỮ LIỆU BAN ĐẦU ==================
user_data = {}  # runtime per-user state (not persisted)
# Load persisted structures
_active_keys_raw = load_json("keys.json")          # {key: "YYYY-MM-DD HH:MM:SS"}
_authenticated_raw = load_json("auth_users.json")  # dict or list
_kicked_raw = load_json("kicked.json")             # list

# Convert loaded data
active_keys = {}
for k, v in (_active_keys_raw or {}).items():
    # v expected string time
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
        # expired keys are skipped (auto-deleted)
    else:
        # if something else, skip
        pass

# authenticated_users: mapping uid -> expiry datetime
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
    # older format: list of uids — treat as permanent until reset (give long expiry)
    for uid in _authenticated_raw:
        try:
            authenticated_users[int(uid)] = datetime.now() + timedelta(days=365*10)
        except:
            pass

# ensure owner always authenticated far into future
authenticated_users[OWNER_ID] = datetime.now() + timedelta(days=365*100)

kicked_users = set(_kicked_raw) if isinstance(_kicked_raw, list) else set()
running_users = set()

# Save cleaned initial files
save_keys_file()
save_auth_users_file()
save_kicked_file()

# ================== HÀM API (SỬA LỖI 0-0-0) ==================
def get_api():
    """
    Trả về: phien(int)|None, kq (string: 'Tài'/'Xỉu' or None), xx (string 'a-b-c')
    Nếu dữ liệu xúc xắc chưa đầy đủ (bất kỳ xúc xắc == 0 hoặc thiếu) -> trả về (None, None, None)
    """
    try:
        r = requests.get("https://ahihidonguoccut.onrender.com/mohobomaycai", timeout=5)
        js = r.json()

        # Lấy các trường theo API mẫu bạn cung cấp
        phien = js.get("Phien")
        kq = js.get("Ket_qua") or js.get("KetQua") or js.get("ket_qua") or js.get("ketqua")
        xx1 = js.get("Xuc_xac_1") if "Xuc_xac_1" in js else js.get("xuc_xac_1") if "xuc_xac_1" in js else js.get("Xuc_xac1")
        xx2 = js.get("Xuc_xac_2") if "Xuc_xac_2" in js else js.get("xuc_xac_2") if "xuc_xac_2" in js else js.get("Xuc_xac2")
        xx3 = js.get("Xuc_xac_3") if "Xuc_xac_3" in js else js.get("xuc_xac_3") if "xuc_xac_3" in js else js.get("Xuc_xac3")

        # an toàn convert
        try:
            phien = int(phien)
        except:
            phien = None

        try:
            xx1 = int(xx1)
        except:
            xx1 = 0
        try:
            xx2 = int(xx2)
        except:
            xx2 = 0
        try:
            xx3 = int(xx3)
        except:
            xx3 = 0

        # Nếu bất kỳ xúc xắc chưa hợp lệ (0) -> bỏ qua (đừng trả về "0-0-0")
        if not phien or xx1 == 0 or xx2 == 0 or xx3 == 0:
            return None, None, None

        # Kiểm tra kết quả Tài/Xỉu hợp lệ
        if isinstance(kq, str):
            kq = kq.strip()
        if kq not in ["Tài", "Xỉu", "Tai", "Xiu"]:
            return None, None, None

        # Chuẩn hóa nội dung "Xỉu"/"Tài"
        if kq in ["Tai"]:
            kq = "Tài"
        if kq in ["Xiu"]:
            kq = "Xỉu"

        xx = f"{xx1}-{xx2}-{xx3}"
        return phien, kq, xx
    except Exception as e:
        # in log để debug nếu cần
        print("Lỗi API get_api():", e)
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

# ================== HÀM DỰ ĐOÁN (GIỮ NGUYÊN LOGIC CŨ + AI tự học lỗi) ==================
def du_doan(data_kq, dem_sai, pattern_sai, xx, diem_lich_su, data):
    # Lưu ý: data_kq là list các kết quả trước đó như ["Tài","Xỉu",...]
    # data["pattern_memory"] là dict lưu mẫu cầu đã học
    # data["error_memory"] là dict lưu mẫu dẫn tới sai
    try:
        xx_list = xx.split("-")
        tong = sum(int(x) for x in xx_list)
    except:
        xx_list = ["0","0","0"]
        tong = 0

    data_kq = data_kq[-100:]  # giữ an toàn
    cuoi = data_kq[-1] if data_kq else None
    pattern = "".join("T" if x == "Tài" else "X" for x in data_kq)

    # === AI tự học: dò tìm mẫu cầu đã học với xác suất đúng cao để dự đoán ===
    pattern_memory = data.get("pattern_memory", {})
    matched_pattern = None
    matched_confidence = 0
    matched_pred = None
    for pat, stats in pattern_memory.items():
        if pattern.endswith(pat):
            count = stats.get("count", 0)
            correct = stats.get("correct", 0)
            confidence = correct / count if count > 0 else 0
            if confidence > matched_confidence and count >= 3 and confidence >= 0.6:
                matched_confidence = confidence
                matched_pattern = pat
                matched_pred = stats.get("next_pred", None)
    if matched_pattern and matched_pred:
        score = 90 + int(matched_confidence * 10)
        return matched_pred, score, f"Dự đoán theo mẫu cầu đã học '{matched_pattern}' với tin cậy {matched_confidence:.2f}"

    # === AI tự học lỗi & tự sửa thuật toán ===
    error_memory = data.get("error_memory", {})
    if len(data_kq) >= 3:
        last3 = tuple(data_kq[-3:])
        # Nếu mẫu này từng gây sai >= 2 lần => đảo hướng
        if last3 in error_memory and error_memory[last3] >= 2:
            du_doan_tx = "Xỉu" if cuoi == "Tài" else "Tài"
            return du_doan_tx, 89, f"AI tự học lỗi: mẫu {last3} đã gây sai nhiều lần → Đổi sang {du_doan_tx}"

    # Nếu sai liên tiếp nhiều lần => thử đảo chiều
    if dem_sai >= 4:
        du_doan_tx = "Xỉu" if cuoi == "Tài" else "Tài"
        return du_doan_tx, 87, f"AI phát hiện sai liên tiếp {dem_sai} → Đổi sang {du_doan_tx}"

    # Nếu kết quả đảo liên tục sau bệt => nhận diện đổi cầu
    if len(data_kq) >= 5:
        if data_kq[-5:].count("Tài") == data_kq[-5:].count("Xỉu") and data_kq[-1] != data_kq[-2]:
            du_doan_tx = "Xỉu" if cuoi == "Tài" else "Tài"
            return du_doan_tx, 88, "AI phát hiện dấu hiệu đổi cầu → Đổi hướng"

    # --- Phần cũ giữ nguyên ---
    if len(data_kq) < 1:
        if tong >= 16:
            return "Tài", 98, f"Tay đầu đặc biệt → Tổng {tong} >=16 → Tài"
        if tong <= 6:
            return "Xỉu", 98, f"Tay đầu đặc biệt → Tổng {tong} <=6 → Xỉu"
        return ("Tài" if tong >= 11 else "Xỉu"), 75, f"Tay đầu → Dựa tổng: {tong}"

    if len(data_kq) == 1:
        if tong >= 16:
            return "Tài", 98, f"Tay 2 → Tổng {tong} >=16 → Tài"
        if tong <= 6:
            return "Xỉu", 98, f"Tay 2 → Tổng {tong} <=6 → Xỉu"
        du_doan_tx = "Xỉu" if cuoi == "Tài" else "Tài"
        return du_doan_tx, 80, f"Tay đầu dự đoán ngược kết quả trước ({cuoi})"

    ben = do_ben(data_kq)
    counts = {"Tài": data_kq.count("Tài"), "Xỉu": data_kq.count("Xỉu")}
    chenh = abs(counts["Tài"] - counts["Xỉu"])
    diem_lich_su.append(tong)
    if len(diem_lich_su) > 6:
        diem_lich_su.pop(0)

    # --- Xử lý cầu bệt bệt ---
    if len(pattern) >= 9:
        for i in range(4, 7):
            if len(pattern) >= i*2:
                sub1 = pattern[-i*2:-i]
                sub2 = pattern[-i:]
                if sub1 == "T"*i and sub2 == "X"*i:
                    return "Xỉu", 90, f"Phát hiện cầu bệt-bệt: {sub1 + sub2}"
                if sub1 == "X"*i and sub2 == "T"*i:
                    return "Tài", 90, f"Phát hiện cầu bệt-bệt: {sub1 + sub2}"

    if len(diem_lich_su) >= 3 and len(set(diem_lich_su[-3:])) == 1:
        return ("Tài" if tong % 2 == 1 else "Xỉu"), 96, f"3 lần lặp điểm: {tong}"
    if len(diem_lich_su) >= 2 and diem_lich_su[-1] == diem_lich_su[-2]:
        return ("Tài" if tong % 2 == 0 else "Xỉu"), 94, f"Kép điểm: {tong}"

    if len(set(xx_list)) == 1:
        so = xx_list[0]
        if so in ["1", "2", "4"]:
            return "Xỉu", 97, f"3 xúc xắc {so} → Xỉu"
        if so in ["3", "5"]:
            return "Tài", 97, f"3 xúc xắc {so} → Tài"
        if so == "6" and ben >= 3:
            return "Tài", 97, f"3 xúc xắc 6 + bệt → Tài"

    if ben >= 3:
        if cuoi == "Tài":
            if ben >= 5 and "3" not in xx_list:
                if not data.get("da_be_tai"):
                    data["da_be_tai"] = True
                    return "Xỉu", 80, "⚠️ Bệt Tài ≥5 chưa có xx3 → Bẻ thử"
                else:
                    return "Tài", 90, "Ôm tiếp bệt Tài chờ xx3"
            elif "3" in xx_list:
                data["da_be_tai"] = False
                return "Xỉu", 95, "Bệt Tài + Xí ngầu 3 → Bẻ"
        elif cuoi == "Xỉu":
            if ben >= 5 and "5" not in xx_list:
                if not data.get("da_be_xiu"):
                    data["da_be_xiu"] = True
                    return "Tài", 80, "⚠️ Bệt Xỉu ≥5 chưa có xx5 → Bẻ thử"
                else:
                    return "Xỉu", 90, "Ôm tiếp bệt Xỉu chờ xx5"
            elif "5" in xx_list:
                data["da_be_xiu"] = False
                return "Tài", 95, "Bệt Xỉu + Xí ngầu 5 → Bẻ"
        return cuoi, 93, f"Bệt {cuoi} ({ben} tay)"

    def ends(pats):
        return any(pattern.endswith(p) for p in pats)

    cau_mau = {
        "1-1": ["TXTX=> bẻ X", "XTXT=>bẻ T", "TXTXT=> bẻ T", "XTXTX=> bẻ X"],
        "2-2": ["TTXXTT=>bẻ T", "XXTTXX=>bẻ X"],
        "2-2": ["TTXXTTX=>bẻ T", "XXTTXXT=>bẻ X"],
        "3-3": ["TTTXXX=>T", "XXXTTT=>X"],
        "1-2-3": ["TXXTTT", "XTTXXX"],
        "3-2-1": ["TTTXXT", "XXXTTX"],
        "1-2-1": ["TXXT", "XTTX"],
        "2-1-1-2": ["TTXTXX", "XXTXTT"],
        "2-1-2": ["TTXTT", "XXTXX"],
        "3-1-3": ["TTTXTTT", "XXXTXXX"],
        "1-2": ["TXX", "XTT"],
        "2-1": ["TTX", "XXT"],
        "1-3-2": ["TXXXTT", "XTTTXX"],
        "1-2-4": ["TXXTTTT", "XTTXXXX"],
        "1-5-3": ["TXXXXXTTT", "XTTTTXXX"],
        "5-1-3": ["TTTTXTTT", "XXXXXTXXX"],
        "1-4-2": ["TXXXXTT", "XTTTTXX"],
        "1-3-5": ["TXXXTTTTT", "XTTTXXXXX"]
    }

    for loai, mau_list in {"1-1": cau_mau["1-1"]}.items():
        for mau in mau_list:
            if pattern.endswith(mau):
                length_cau = len(mau)
                if length_cau == 4:
                    current_len = len(data_kq)
                    if current_len == 5:
                        return ("Xỉu" if cuoi == "Tài" else "Tài"), 85, f"Bẻ nhẹ cầu 1-1 tại tay 5 ({mau})"
                    elif current_len == 6:
                        return ("Xỉu" if cuoi == "Tài" else "Tài"), 90, f"Ôm thêm tay 6 rồi bẻ cầu 1-1 ({mau})"
                    else:
                        return cuoi, 72, "Không rõ mẫu → Theo tay gần nhất"

    for loai, mau in cau_mau.items():
        if ends(mau):
            return ("Xỉu" if cuoi == "Tài" else "Tài"), 90, f"Phát hiện cầu {loai}"

    if len(data_kq) >= 6:
        last_6 = data_kq[-6:]
        for i in range(2, 6):
            if i * 2 <= len(last_6):
                seq = last_6[-i*2:]
                alt1 = []
                alt2 = []
                for j in range(i*2):
                    alt1.append("Tài" if j % 2 == 0 else "Xỉu")
                    alt2.append("Xỉu" if j % 2 == 0 else "Tài")
                if seq == alt1 or seq == alt2:
                    return ("Tài" if cuoi == "Xỉu" else "Xỉu"), 90, f"Bẻ cầu 1-1 ({i*2} tay)"

    if dem_sai >= 3:
        return ("Xỉu" if cuoi == "Tài" else "Tài"), 88, "Sai 3 lần → Đổi chiều"
    if tuple(data_kq[-3:]) in pattern_sai:
        return ("Xỉu" if cuoi == "Tài" else "Tài"), 86, "Mẫu sai cũ"
    if chenh >= 3:
        uu = "Tài" if counts["Tài"] > counts["Xỉu"] else "Xỉu"
        return uu, 84, f"Lệch {chenh} cầu → Ưu tiên {uu}"

    return cuoi, 72, "Không rõ mẫu → Theo tay gần nhất"

# ================== XỬ LÝ PHIÊN VÀ GỬI THÔNG BÁO ==================
def xu_ly_phien(phien, kq, xx, chat_id):
    # Khởi tạo data cho user nếu chưa có
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
            # Các flag để bẻ cầu
            "da_be_tai": False,
            "da_be_xiu": False,
        }

    data = user_data[chat_id]

    # Nếu dữ liệu xúc xắc hoặc kết quả không hợp lệ -> bỏ qua (không xử lý)
    if not (phien and kq and xx):
        return

    # Bỏ qua phiên không mới hơn phiên đã xử lý
    if not (phien and phien > data.get("last_phien", 0)):
        return

    thong_bao = ""
    # Nếu có dự đoán trước và phiên hiện tại là phiên tiếp theo phiên dự đoán
    if data.get("du_doan_truoc") is not None and phien == data.get("phien_truoc", 0) + 1:
        thang = (data["du_doan_truoc"] == kq)
        thong_bao = "✅ ĐÚNG" if thang else "❌ SAI"

        data.setdefault("lich_su_phan_hoi", []).append({
            "time": datetime.now().strftime("%H:%M"),
            "du_doan": data["du_doan_truoc"],
            "kq": kq,
            "thang": thang,
            "phien": phien
        })

        if thang:
            data["dem_sai"] = 0
        else:
            data["dem_sai"] = data.get("dem_sai", 0) + 1
            # Nếu sai và lịch sử kq có ít nhất 3 kết quả, thêm pattern sai
            if len(data.get("lich_su_kq", [])) >= 3:
                pattern = tuple(data.get("lich_su_kq", [])[-3:])
                data.setdefault("pattern_sai", set()).add(pattern)

        data["so_dung"] = data.get("so_dung", 0) + (1 if thang else 0)
        data["so_sai"] = data.get("so_sai", 0) + (0 if thang else 1)

    # Cập nhật phiên mới nhất đã xử lý
    data["last_phien"] = phien

    # Thêm kết quả thực tế vào lịch sử kết quả
    data.setdefault("lich_su_kq", []).append(kq)
    if len(data["lich_su_kq"]) > 100:
        data["lich_su_kq"] = data["lich_su_kq"][-100:]

    # Gọi hàm dự đoán mới
    du_doan_tx, do_tin_cay, loai_cau = du_doan(
        data["lich_su_kq"],
        data.get("dem_sai", 0),
        data.get("pattern_sai", set()),
        xx,
        data.setdefault("lich_su_diem", []),
        data
    )

    # Lưu dự đoán mới, độ tin cậy và phiên dự đoán
    data["du_doan_truoc"] = du_doan_tx
    data["do_tin_cay_truoc"] = do_tin_cay
    data["phien_truoc"] = phien

    # Chuỗi cầu dạng T/X 10 tay gần nhất
    chuoi_cau = "".join(["T" if x == "Tài" else "X" for x in data["lich_su_kq"][-10:]])

    # Tính tổng xúc xắc để gửi
    try:
        tong_xuc_xac = sum(map(int, xx.split("-")))
    except:
        tong_xuc_xac = None

    # Tính chuỗi thắng liên tiếp cuối cùng (dự đoán đúng liên tiếp)
    lich_su_phan_hoi = data.get("lich_su_phan_hoi", [])
    chuoi_thang_lien_tiep = 0
    for ph in reversed(lich_su_phan_hoi):
        if ph.get("thang") == True:
            chuoi_thang_lien_tiep += 1
        else:
            break

    # Gửi tin nhắn cho user
    try:
        bot.send_message(chat_id, f"""🤖 SunWin.pro
#️⃣ Phiên: {phien}
🎯 Kết quả: {kq}
🎲 Xúc xắc: {xx}
➕ Tổng: {tong_xuc_xac if tong_xuc_xac is not None else 'N/A'}
❓ Dự đoán trước: {thong_bao or '⏳...'}
====================
🔮 Dự đoán tiếp theo: {du_doan_tx}
📈 Xác suất: {do_tin_cay}%
====================
📊 Tổng dự đoán: {data.get('so_dung',0) + data.get('so_sai',0)}
🟢 Đúng: {data.get('so_dung',0)}
🔴 Sai:  {data.get('so_sai',0)}
🔥 Chuỗi thắng liên tiếp: {chuoi_thang_lien_tiep}
====================
TOOL BY @wills29nopro.
""")

    except Exception as e:
        # tránh crash nếu gửi tin nhắn lỗi
        print("Lỗi gửi message:", e)

# ================== VÒNG LẶP TỰ ĐỘNG CHO MỖI USER ==================
def auto_loop(uid):
    """
    Vòng lặp cho từng user: lấy API liên tục và xử lý nếu user vẫn còn active.
    """
    while uid in running_users:
        try:
            expiry = authenticated_users.get(uid)
            if not expiry or expiry <= datetime.now():
                # Key hết hạn hoặc không có → dừng chạy và kick user
                try:
                    bot.send_message(uid, "🔔 Key của bạn đã hết hạn hoặc không hợp lệ. Bot sẽ dừng dự đoán và bạn bị kick khỏi bot. Vui lòng nhập key mới để tiếp tục.")
                except:
                    pass
                authenticated_users.pop(uid, None)
                kicked_users.add(uid)
                save_auth_users_file()
                save_kicked_file()
                running_users.discard(uid)
                break

            phien, kq, xx = get_api()

            # CHỈ xử lý khi cả 3 đều hợp lệ (không null và không 0-0-0)
            if phien and kq and xx and uid in authenticated_users and uid not in kicked_users:
                if uid not in user_data:
                    user_data[uid] = {
                        "lich_su_kq": [], "dem_sai": 0, "pattern_sai": set(),
                        "so_dung": 0, "so_sai": 0, "last_phien": 0,
                        "du_doan_truoc": "", "do_tin_cay_truoc": 0,
                        "lich_su_phan_hoi": [], "phien_truoc": 0,
                        "da_be_tai": False,
                        "da_be_xiu": False,
                        "lich_su_diem": [],
                    }
                xu_ly_phien(phien, kq, xx, uid)
        except Exception as e:
            # Có thể ghi log nếu muốn
            # print("auto_loop error:", e)
            pass
        time.sleep(3)

@bot.message_handler(commands=['start'])
def handle_start(msg):
    uid = msg.from_user.id
    if uid in kicked_users:
        bot.reply_to(msg, "⛔ Bạn đã bị chặn!")
        return

    if uid != OWNER_ID:
        expiry = authenticated_users.get(uid)
        if (not expiry) or (expiry <= datetime.now()):
            # Nếu key không tồn tại hoặc đã hết hạn thì xóa user khỏi authenticated_users nếu còn sót
            if uid in authenticated_users:
                authenticated_users.pop(uid)
                save_auth_users_file()
            bot.send_message(uid, """👋 Chào mừng bạn đến với 🤖 SunWin.us

Bạn muốn có bot để dùng?
Hãy nhìn bảng giá key dưới đây và quyết định:

💰 1 ngày = 30k
💰 1 tuần = 50k 
💰 1 tháng = 120k

🔑 Nếu mua key, vui lòng chuyển khoản vào:

🏦 Số tài khoản: 8853451801  
🏦 Ngân hàng: BIDV BANK  

📩 Sau khi chuyển, hãy gửi bill và liên hệ Admin: @wills29nopro để được cấp key.

Nếu cần tìm hiểu thêm về các lệnh, bạn dùng:
 /help nhé.
""")
            return  # KHÔNG chạy vòng lặp dự đoán nếu key không hợp lệ

    bot.reply_to(msg, "✅ Bắt đầu dự đoán!")
    if uid not in user_data:
        user_data[uid] = {
            "lich_su_kq": [], "dem_sai": 0, "pattern_sai": set(),
            "so_dung": 0, "so_sai": 0, "last_phien": 0,
            "du_doan_truoc": "", "do_tin_cay_truoc": 0,
            "lich_su_phan_hoi": [], "phien_truoc": 0
        }
    if uid not in running_users:
        running_users.add(uid)
        threading.Thread(target=auto_loop, args=(uid,), daemon=True).start()
        
@bot.message_handler(commands=['stop'])
def handle_stop(msg):
    uid = msg.from_user.id
    running_users.discard(uid)
    bot.reply_to(msg, "⏸️ Dừng dự đoán.")
    
@bot.message_handler(commands=['taokey'])
def handle_taokey(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "❌ Không có quyền.")
        return
    try:
        parts = msg.text.split()
        if len(parts) != 2:
            raise ValueError
        duration_str = parts[1]
        unit = duration_str[-1]
        amount = int(duration_str[:-1])
        now = datetime.now()
        if unit == 'm':
            expire_time = now + timedelta(minutes=amount)
        elif unit == 'h':
            expire_time = now + timedelta(hours=amount)
        elif unit == 'd':
            expire_time = now + timedelta(days=amount)
        elif unit == 'M':
            expire_time = now + timedelta(days=30 * amount)
        else:
            bot.reply_to(msg, "❌ Đơn vị không hợp lệ. Dùng m/h/d/M")
            return
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        active_keys[key] = expire_time
        save_keys_file()
        bot.reply_to(msg, f"""🔑 Key: `{key}`
🕒 Hết hạn: {expire_time.strftime('%H:%M %d-%m-%Y')}""", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(msg, "❌ Sai cú pháp. Dùng: /taokey <số+m/h/d/M>\nVD: /taokey 30m")

@bot.message_handler(commands=['key'])
def handle_key(msg):
    uid = msg.from_user.id
    parts = msg.text.strip().split()

    if uid == OWNER_ID and len(parts) == 1:
        keys = "\n".join(
            f"{k} → {v.strftime('%H:%M %d-%m-%Y')}" if isinstance(v, datetime) else f"{k} → {v}"
            for k, v in active_keys.items()
        )
        bot.reply_to(msg, f"🗝️ Danh sách key:\n{keys or 'Trống'}")
        return

    if len(parts) == 2:
        key = parts[1].strip()
        expire = active_keys.get(key)
        if not expire:
            bot.reply_to(msg, "❌ Key sai hoặc đã dùng/không tồn tại.")
            return
        if isinstance(expire, datetime) and expire <= datetime.now():
            bot.reply_to(msg, "❌ Key đã hết hạn.")
            active_keys.pop(key, None)
            save_keys_file()
            return

        # Gán key mới cho user
        authenticated_users[uid] = expire
        save_auth_users_file()

        # Xóa key đã dùng
        active_keys.pop(key, None)
        save_keys_file()

        # Nếu user cũ bị kick thì mở khóa
        if uid in kicked_users:
            kicked_users.discard(uid)
            save_kicked_file()

        # KHÔNG tự động bật vòng lặp auto_loop khi nhập key, người dùng phải /start lại để chạy
        bot.reply_to(msg, "✅ Kích hoạt thành công! Vui lòng dùng lệnh /start để bắt đầu dự đoán.")
        try:
            bot.send_message(uid, "Chúc bạn thắng lớn, và có một trải nghiệm thật tốt từ chúng tôi 🎉, nếu có sai sót gì hoặc bot không báo quá lâu hãy liên hệ lại admin.")
        except:
            pass
    else:
        bot.reply_to(msg, "❌ Sai cú pháp. Dùng: /key <mã_key>")
@bot.message_handler(commands=['help'])
def handle_help(msg):
    help_text = """📌 Danh sách lệnh bạn có thể dùng:

/start - Bắt đầu chạy dự đoán  
/reset - Reset dữ liệu bot (sau đó dùng lại /start)  
/key <mã_key> - Nhập key để kích hoạt bot 
/lichsu - Xem lịch sử dự đoán và kết quả
/checkkey - xem thời hạn key 
/stop - Dừng bot cho bạn  

👉 Nếu gặp lỗi hoặc cần hỗ trợ, vui lòng liên hệ Admin: @wills29nopro ."""
    bot.reply_to(msg, help_text)
@bot.message_handler(commands=['checkkey'])
def handle_checkkey(msg):
    uid = msg.from_user.id
    expire = authenticated_users.get(uid)

    if not expire:
        bot.reply_to(msg, "⛔ Bạn chưa kích hoạt key hoặc key đã hết hạn.")
        return

    if isinstance(expire, str):
        try:
            expire = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
        except:
            bot.reply_to(msg, "⚠️ Dữ liệu key không hợp lệ.")
            return

    now = datetime.now()
    if expire <= now:
        bot.reply_to(msg, "❌ Key của bạn đã hết hạn.")
        return

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
    if uid not in authenticated_users:
        bot.reply_to(msg, "⛔ Bạn chưa được cấp quyền.")
        return
    ls = user_data.get(uid, {}).get("lich_su_phan_hoi", [])
    if not ls:
        bot.reply_to(msg, "⏳ Chưa có lịch sử.")
        return
    text = "\n".join(
        f"{x['time']} | Phiên {x['phien']} | Dự: {x['du_doan']} | KQ: {x['kq']} | {'✅' if x['thang'] else '❌'}"
        for x in ls[-20:][::-1]
    )
    bot.reply_to(msg, f"📜 Lịch sử:\n{text}")

@bot.message_handler(commands=['xoakey'])
def handle_xoakey(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "❌ Không có quyền.")
        return
    try:
        key = msg.text.split()[1]
        if key in active_keys:
            active_keys.pop(key, None)
            save_keys_file()
            bot.reply_to(msg, f"✅ Đã xóa key {key}.")
        else:
            bot.reply_to(msg, "❌ Key không tồn tại.")
    except:
        bot.reply_to(msg, "❌ Cú pháp: /xoakey <key>")

@bot.message_handler(commands=['kickid'])
def handle_kick(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "❌ Không có quyền.")
        return
    try:
        uid = int(msg.text.split()[1])
        authenticated_users.pop(uid, None)
        kicked_users.add(uid)
        save_auth_users_file()
        save_kicked_file()
        running_users.discard(uid)
        bot.reply_to(msg, f"✅ Đã kick ID: {uid}")
    except:
        bot.reply_to(msg, "❌ Cú pháp: /kickid <id>")

@bot.message_handler(commands=['unkickid'])
def handle_unkick(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "❌ Không có quyền.")
        return
    try:
        uid = int(msg.text.split()[1])
        kicked_users.discard(uid)
        save_kicked_file()
        bot.reply_to(msg, f"✅ Đã mở khóa ID: {uid}")
    except:
        bot.reply_to(msg, "❌ Cú pháp: /unkickid <id>")

@bot.message_handler(commands=['uidstart'])
def handle_uidstart(msg):
    if msg.from_user.id != OWNER_ID:
        bot.reply_to(msg, "❌ Không có quyền.")
        return
    text = "👥 Users đang dùng bot (đang chạy dự đoán):\n"
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
    """
    Reset dữ liệu runtime cho user (không xóa key/auth).
    Nếu là owner và có tham số 'all', xóa toàn bộ file (keys/auth/kicked).
    """
    uid = msg.from_user.id
    parts = msg.text.split()
    if uid == OWNER_ID and len(parts) > 1 and parts[1].lower() == "all":
        # Danger: owner requested wiping persistent data
        active_keys.clear()
        authenticated_users.clear()
        authenticated_users.add(OWNER_ID)
        kicked_users.clear()
        save_keys_file()
        save_auth_users_file()
        save_kicked_file()
        user_data.clear()
        bot.reply_to(msg, "✅ Đã xóa toàn bộ dữ liệu persistent (keys/auth/kicked).")
        return

    # bình thường reset user riêng
    user_data.pop(uid, None)
    running_users.discard(uid)
    bot.reply_to(msg, "🔄 Đã reset dữ liệu bot cho bạn (runtime). Nếu muốn xóa key/auth, liên hệ Admin.")

# ================== Khởi động BOT ==================
print("🤖 SUNWIN BOT — ĐÃ KHỞI ĐỘNG")
# đảm bảo lưu lần đầu các file nếu chưa tồn tại
save_keys_file()
save_auth_users_file()
save_kicked_file()

bot.infinity_polling(skip_pending=True)
