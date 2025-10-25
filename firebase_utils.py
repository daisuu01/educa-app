# =============================================
# firebase_utils.py（Excel+CSV登録／二重PW対応／コード列空欄の前方補完を堅牢化）
# =============================================

import pandas as pd
import hashlib
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
from typing import Dict

# ==============================
# 🔧 Firebase 初期化
# ==============================
load_dotenv()
firebase_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "educa-app-firebase-adminsdk.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
USERS = db.collection("users")


# ==============================
# 🔐 パスワード関連ユーティリティ
# ==============================
def hash_password(password: str) -> str:
    """パスワードをSHA256でハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(input_pw: str, user_doc: dict) -> bool:
    """
    入力PWが Firestore 内の初期PW/変更後PW/旧形式(password_hash)のいずれかに一致すれば True
    """
    if not user_doc:
        return False
    input_hash = hash_password(input_pw)
    init_hash = user_doc.get("init_password_hash")
    custom_hash = user_doc.get("custom_password_hash")
    legacy_hash = user_doc.get("password_hash")
    return input_hash in {init_hash, custom_hash, legacy_hash}


def update_user_password(member_id: str, new_password: str):
    """
    ユーザーが任意PWを設定した際に custom_password_hash を更新（初期PWは有効のまま）
    """
    try:
        hashed_new = hash_password(new_password)
        USERS.document(member_id).update({
            "custom_password_hash": hashed_new,
            "password_changed": True
        })
        return True
    except Exception as e:
        print(f"❌ パスワード更新エラー: {e}")
        return False


# ==============================
# 🧰 ヘルパー：列名マップ＆前処理
# ==============================
def _normalize_columns(df: pd.DataFrame) -> Dict[str, str]:
    """列名の全角スペース除去・トリム＋ゆらぎ対応して、標準キーにマッピング"""
    # 列名正規化
    df.columns = [str(c).strip().replace("　", "") for c in df.columns]

    # 候補パターン
    candidates = {
        "code": ["コード", "ｺｰﾄﾞ", "code", "Code", "CODE"],
        "member": ["会員番号", "会員ID", "ID", "id"],
        "family": ["姓", "性", "苗字", "姓氏"],
        "given": ["名", "名前", "氏名（名）", "下の名前"],
    }

    resolved = {}
    for key, opts in candidates.items():
        found = next((c for c in df.columns if c in opts), None)
        if not found and key in ("family", "given"):
            # 姓名が1列（例：「氏名」）しかない場合に備えて
            if key == "family":
                found = next((c for c in df.columns if c in ["氏名", "名前"]), None)
            else:
                found = None
        if found:
            resolved[key] = found

    # 必須：会員番号/コード/姓/名（姓名1列の場合はgiven欠落を許容）
    missing = []
    for req in ("code", "member"):
        if req not in resolved:
            missing.append(req)
    if "family" not in resolved and "given" not in resolved:
        missing.extend(["family_or_fullname"])
    if missing:
        print(f"⚠ 必須列が見つかりません: {missing}")

    return resolved


def _ffill_code_column(df: pd.DataFrame, code_col: str) -> pd.Series:
    """
    コード列の空欄（空文字/空白/全角空白/'nan'文字等）をNaN化→前方補完→文字整形
    """
    col = df[code_col].copy()

    # 文字化・空白/全角空白のトリム
    col = col.astype(str).str.replace("\u3000", "", regex=False).str.strip()

    # 'nan'/'None'/空文字をNaNに
    col = col.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})

    # 数値型が文字化され '.0' がつくパターンに対応 → ffill 後に整形
    # 前方補完
    col = col.ffill()

    # 補完後にも残る可能性のある '.0' や小数表現を除去
    # 例: '10100.0' -> '10100'
    col = col.str.replace(r"\.0$", "", regex=True)

    # 万一「全てがNaNで先頭も空」だった場合の保険（そのまま返す）
    return col


# ==============================
# 🧾 Firestore 登録処理
# ==============================
def import_students_from_excel_and_csv(excel_file, csv_file):
    """
    Excel（会員番号, 姓/性, 名 or 氏名, コード）＋CSV（会員番号, 初期PW）を統合してFirestoreに登録。
    コード列は空欄を上の値で前方補完して確実に埋める。
    既存会員番号はスキップ。
    """
    try:
        # --- Excel読み込み＆列名正規化 ---
        df_excel = pd.read_excel(excel_file)
        col_map = _normalize_columns(df_excel)

        # --- コード列の補完 ---
        code_col = col_map.get("code")
        if code_col:
            df_excel[code_col] = _ffill_code_column(df_excel, code_col)
        else:
            print("❌ コード列が見つかりません。登録をスキップします。")
            return pd.DataFrame()

        # --- CSV読み込み（会員番号, 初期PW） ---
        df_csv = pd.read_csv(csv_file)
        df_csv.columns = [str(c).strip().replace("　", "") for c in df_csv.columns]
        # 1列目=会員番号, 2列目=初期PW として扱う（列名ゆらぎ対策）
        if df_csv.shape[1] < 2:
            print("❌ CSVの列数が不足しています（会員番号/初期PWの2列必要）。")
            return pd.DataFrame()
        df_csv.iloc[:, 0] = df_csv.iloc[:, 0].astype(str).str.strip()
        df_csv.iloc[:, 1] = df_csv.iloc[:, 1].astype(str).str.strip()

        registered = []

        # --- 行ごと処理 ---
        for _, row in df_excel.iterrows():
            try:
                # 会員番号
                member_col = col_map.get("member")
                if not member_col or pd.isna(row.get(member_col)):
                    continue
                member_id = str(row[member_col]).strip()

                # 氏名
                family_col = col_map.get("family")
                given_col  = col_map.get("given")
                if family_col and given_col:
                    family = str(row.get(family_col, "")).strip()
                    given  = str(row.get(given_col, "")).strip()
                    name = f"{family} {given}".strip()
                else:
                    # 氏名1列（例：「氏名」「名前」）のとき
                    fullname_col = col_map.get("family")  # family に氏名1列が入っているケース
                    name = str(row.get(fullname_col, "")).strip()

                # クラスコード（補完済）
                class_code = str(row.get(code_col, "")).strip()
                if class_code == "" or class_code.lower() == "nan":
                    # ここまで来た時点で本来埋まっている想定だが、念のためスキップ
                    print(f"⚠ {member_id}: コードが空です。スキップ。")
                    continue

                # CSVから初期PW取得
                # （1列目=会員番号, 2列目=初期PW）
                hit = df_csv[df_csv.iloc[:, 0] == member_id]
                if hit.empty:
                    print(f"⚠ {member_id}: CSVに初期PWが見つかりません。スキップ。")
                    continue
                init_pw = str(hit.iloc[0, 1]).strip()
                hashed_init = hash_password(init_pw)

                # 既存チェック
                doc_ref = USERS.document(member_id)
                if doc_ref.get().exists:
                    print(f"スキップ: {member_id} は既に登録済み")
                    continue

                # Firestore登録
                doc_ref.set({
                    "member_id": member_id,
                    "name": name,
                    "class_code": class_code,
                    "role": "student",
                    "init_password_hash": hashed_init,
                    "custom_password_hash": None,
                    "password_changed": False
                })

                registered.append({
                    "会員番号": member_id,
                    "氏名": name,
                    "クラス": class_code,
                    "初期PW": init_pw
                })

            except Exception as e:
                print(f"登録エラー: {row} → {e}")

        return pd.DataFrame(registered)

    except Exception as e:
        print(f"❌ 登録中エラー: {e}")
        return pd.DataFrame()


# ==============================
# 📋 Firestore 全ユーザー一覧取得
# ==============================
def fetch_all_users():
    """
    Firestoreの users コレクションをDataFrameとして返す。
    """
    try:
        users = []
        for doc in USERS.stream():
            data = doc.to_dict()
            users.append({
                "会員番号": data.get("member_id"),
                "氏名": data.get("name"),
                "クラス": data.get("class_code"),
                "PW変更済": "✅" if data.get("password_changed") else "❌"
            })
        return pd.DataFrame(users)
    except Exception as e:
        print(f"❌ Firestore一覧取得エラー: {e}")
        return pd.DataFrame()
