"""
Streamlit 菜谱应用（单文件）
功能：
- SQLite 本地存储菜谱
- 搜索（名称/食材/标签）
- 按国家（cuisine）和类型（Main/Dessert/Snack/...）筛选
- 添加菜谱（含图片上传）
- 导入 / 导出 CSV（方便扩充全世界菜谱）
- 随机推荐
- 可扩展：你可以批量导入大型 CSV 来实现“包含更多菜”的目标
"""

import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import random
from PIL import Image
from typing import List

DB_PATH = "recipes.db"
IMG_DIR = "recipe_images"
os.makedirs(IMG_DIR, exist_ok=True)

# ---------- DB helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cuisine TEXT,
        type TEXT,
        ingredients TEXT,
        instructions TEXT,
        servings TEXT,
        prep_time TEXT,
        cook_time TEXT,
        image_path TEXT,
        tags TEXT
    )
    """)
    conn.commit()

def recipe_exists(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM recipes")
    return c.fetchone()[0] > 0

def add_recipe(conn, recipe: dict):
    c = conn.cursor()
    c.execute("""
    INSERT INTO recipes (name, cuisine, type, ingredients, instructions, servings, prep_time, cook_time, image_path, tags)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recipe.get("name"),
        recipe.get("cuisine"),
        recipe.get("type"),
        recipe.get("ingredients"),
        recipe.get("instructions"),
        recipe.get("servings"),
        recipe.get("prep_time"),
        recipe.get("cook_time"),
        recipe.get("image_path"),
        recipe.get("tags"),
    ))
    conn.commit()
    return c.lastrowid

def query_recipes(conn, where_clause="", params=()):
    c = conn.cursor()
    sql = "SELECT * FROM recipes " + where_clause + " ORDER BY name COLLATE NOCASE"
    c.execute(sql, params)
    rows = c.fetchall()
    return [dict(r) for r in rows]

def get_recipe_by_id(conn, recipe_id):
    c = conn.cursor()
    c.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    r = c.fetchone()
    return dict(r) if r else None

# ---------- Seeding sample data ----------
SAMPLE_RECIPES = [
    {
        "name": "Pizza Margherita",
        "cuisine": "Italy",
        "type": "Main",
        "ingredients": "pizza dough,tomato,mozzarella,basil,olive oil,salt",
        "instructions": "Prepare dough, spread tomato sauce, add mozzarella and basil, bake in hot oven.",
        "servings": "2-4",
        "prep_time": "20 min",
        "cook_time": "10-12 min",
        "image_path": "",
        "tags": "classic,vegetarian"
    },
    {
        "name": "Sushi (Nigiri)",
        "cuisine": "Japan",
        "type": "Main",
        "ingredients": "sushi rice,vinegar,fish (salmon/tuna),wasabi,soy sauce",
        "instructions": "Form rice balls, slice fish, assemble and serve with soy sauce.",
        "servings": "2",
        "prep_time": "30 min",
        "cook_time": "0 min",
        "image_path": "",
        "tags": "seafood,gluten-free"
    },
    {
        "name": "Tacos al Pastor",
        "cuisine": "Mexico",
        "type": "Main",
        "ingredients": "pork,achiote,ananas,onion,coriander,tortillas",
        "instructions": "Marinate pork, roast, slice thinly, serve on tortillas with pineapple and onion.",
        "servings": "4",
        "prep_time": "2 hr (marinate)",
        "cook_time": "45 min",
        "image_path": "",
        "tags": "street-food,spicy"
    },
    {
        "name": "Butter Chicken",
        "cuisine": "India",
        "type": "Main",
        "ingredients": "chicken,tomato,cream,butter,garam masala,ginger,garlic",
        "instructions": "Cook marinated chicken, prepare tomato-cream sauce, simmer together.",
        "servings": "4",
        "prep_time": "30 min",
        "cook_time": "30 min",
        "image_path": "",
        "tags": "comfort-food"
    },
    {
        "name": "Peking Duck",
        "cuisine": "China",
        "type": "Main",
        "ingredients": "duck,scallion,cucumber,hoisin sauce,pancakes",
        "instructions": "Roast duck until crisp, slice, serve with pancakes and condiments.",
        "servings": "4",
        "prep_time": "1 hr",
        "cook_time": "1.5-2 hr",
        "image_path": "",
        "tags": "festive"
    },
    {
        "name": "Ratatouille",
        "cuisine": "France",
        "type": "Main",
        "ingredients": "eggplant,zucchini,tomato,bell pepper,onion,garlic,herbs",
        "instructions": "Slice vegetables, layer or sauté, simmer with herbs until tender.",
        "servings": "4",
        "prep_time": "20 min",
        "cook_time": "40 min",
        "image_path": "",
        "tags": "vegetarian,healthy"
    },
    {
        "name": "Baklava",
        "cuisine": "Turkey",
        "type": "Dessert",
        "ingredients": "phyllo dough,nuts (walnut/pistachio),butter,sugar,honey,lemon",
        "instructions": "Layer phyllo with nuts and butter, bake, then pour syrup.",
        "servings": "12",
        "prep_time": "30 min",
        "cook_time": "45 min",
        "image_path": "",
        "tags": "sweet,nutty"
    },
    {
        "name": "Churros",
        "cuisine": "Spain",
        "type": "Snack",
        "ingredients": "flour,water,butter,salt,sugar,cinnamon",
        "instructions": "Make choux-like dough, pipe and deep-fry, roll in cinnamon sugar.",
        "servings": "4",
        "prep_time": "15 min",
        "cook_time": "10 min",
        "image_path": "",
        "tags": "fried,snack"
    },
    {
        "name": "Pavlova",
        "cuisine": "New Zealand",
        "type": "Dessert",
        "ingredients": "egg whites,sugar,vinegar,cream,fruit (kiwi/strawberry)",
        "instructions": "Whip meringue, bake low and slow, top with cream and fruit.",
        "servings": "8",
        "prep_time": "30 min",
        "cook_time": "1 hr",
        "image_path": "",
        "tags": "meringue"
    },
    {
        "name": "Pastel de Nata",
        "cuisine": "Portugal",
        "type": "Dessert",
        "ingredients": "puff pastry,egg yolks,cream,sugar,lemon,cinnamon",
        "instructions": "Fill puff pastry cups with custard, bake at high heat until blistered.",
        "servings": "12",
        "prep_time": "25 min",
        "cook_time": "15 min",
        "image_path": "",
        "tags": "pastry"
    },
    {
        "name": "Mochi",
        "cuisine": "Japan",
        "type": "Dessert",
        "ingredients": "glutinous rice flour,sugar,red bean paste (optional)",
        "instructions": "Make sticky rice dough, shape and optionally fill with anko (red bean).",
        "servings": "6",
        "prep_time": "20 min",
        "cook_time": "10 min",
        "image_path": "",
        "tags": "chewy,traditional"
    },
    {
        "name": "Brigadeiro",
        "cuisine": "Brazil",
        "type": "Dessert",
        "ingredients": "condensed milk,cocoa powder,butter,chocolate sprinkles",
        "instructions": "Cook condensed milk + cocoa until thick, cool, roll into balls and coat with sprinkles.",
        "servings": "12",
        "prep_time": "10 min",
        "cook_time": "15 min",
        "image_path": "",
        "tags": "candy"
    },
]

# ---------- Utility ----------
def seed_db(conn):
    if not recipe_exists(conn):
        for r in SAMPLE_RECIPES:
            add_recipe(conn, r)

def save_image(file, prefix="img"):
    if file is None:
        return ""
    try:
        img = Image.open(file)
        ext = getattr(img, "format", "PNG") or "PNG"
        ext = ext.lower()
    except Exception:
        # fallback, treat as raw upload
        ext = file.type.split("/")[-1] if hasattr(file, "type") else "png"
    fname = f"{prefix}_{random.randint(100000,999999)}.{ext}"
    path = os.path.join(IMG_DIR, fname)
    # rewind and save
    file.seek(0)
    with open(path, "wb") as f:
        f.write(file.read())
    return path

def search_filter(recipes: List[dict], q: str, cuisines: List[str], types: List[str]):
    out = []
    qlow = q.strip().lower()
    for r in recipes:
        if cuisines and r.get("cuisine") not in cuisines:
            continue
        if types and r.get("type") not in types:
            continue
        if qlow:
            hay = " ".join([str(r.get(k, "")).lower() for k in ("name","ingredients","tags","cuisine","instructions")])
            if qlow not in hay:
                continue
        out.append(r)
    return out

# ---------- Streamlit UI ----------
st.set_page_config(page_title="世界菜谱 (Streamlit)", layout="wide", initial_sidebar_state="expanded")
st.title("🍽️ 世界菜谱（可扩展）")
st.markdown(
    "这是一个基于 Streamlit 的菜谱管理应用。你可以搜索、筛选、添加、导入/导出菜谱。"
)

conn = get_conn()
init_db(conn)
seed_db(conn)

# Sidebar - controls
st.sidebar.header("筛选与操作")
q = st.sidebar.text_input("搜索（名称/食材/标签/国家）", value="")
all_recipes = query_recipes(conn)
all_cuisines = sorted({r.get("cuisine") or "Unknown" for r in all_recipes})
all_types = sorted({r.get("type") or "Other" for r in all_recipes})

selected_cuisines = st.sidebar.multiselect("国家 / Cuisine", options=all_cuisines, default=[])
selected_types = st.sidebar.multiselect("类别 / Type", options=all_types, default=[])

if st.sidebar.button("随机推荐一道菜"):
    cand = search_filter(all_recipes, q, selected_cuisines, selected_types)
    if cand:
        pick = random.choice(cand)
        st.experimental_set_query_params(recipe=pick["id"])
        st.sidebar.success(f"已推荐：{pick['name']} ({pick['cuisine']})")
    else:
        st.sidebar.info("没有符合筛选条件的菜谱。")

# Import / Export
st.sidebar.markdown("---")
st.sidebar.subheader("导入 / 导出")
csv_file = st.sidebar.file_uploader("导入 CSV（模板见下）", type=["csv"])
if st.sidebar.button("从 CSV 导入"):
    if csv_file is None:
        st.sidebar.error("请先上传 CSV 文件（查看模板字段）。")
    else:
        try:
            df = pd.read_csv(csv_file)
            required = {"name","cuisine","type","ingredients","instructions"}
            if not required.issubset(set(df.columns)):
                st.sidebar.error(f"CSV 缺少必要列。至少需要：{', '.join(required)}")
            else:
                imported = 0
                for _, row in df.iterrows():
                    rec = {
                        "name": str(row.get("name","")).strip(),
                        "cuisine": str(row.get("cuisine","")).strip(),
                        "type": str(row.get("type","")).strip(),
                        "ingredients": str(row.get("ingredients","")).strip(),
                        "instructions": str(row.get("instructions","")).strip(),
                        "servings": str(row.get("servings","")).strip() if "servings" in df.columns else "",
                        "prep_time": str(row.get("prep_time","")).strip() if "prep_time" in df.columns else "",
                        "cook_time": str(row.get("cook_time","")).strip() if "cook_time" in df.columns else "",
                        "image_path": "",
                        "tags": str(row.get("tags","")).strip() if "tags" in df.columns else ""
                    }
                    if rec["name"]:
                        add_recipe(conn, rec)
                        imported += 1
                st.sidebar.success(f"成功导入 {imported} 条菜谱！")
        except Exception as e:
            st.sidebar.error(f"导入失败：{e}")

if st.sidebar.button("导出当前筛选为 CSV"):
    # apply current filters and export
    filtered = search_filter(all_recipes, q, selected_cuisines, selected_types)
    if not filtered:
        st.sidebar.info("当前没有符合筛选条件的菜谱可导出。")
    else:
        df = pd.DataFrame(filtered)
        csv = df.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button("下载 CSV", data=csv, file_name="recipes_export.csv", mime="text/csv")

st.sidebar.markdown("**CSV 模板列**: name,cuisine,type,ingredients,instructions,servings,prep_time,cook_time,tags")

st.sidebar.markdown("---")
st.sidebar.markdown("⚙️ 说明：你可以批量把大型菜谱库（CSV）导入来接近“世界所有菜”的目标。")

# Main area - Add new recipe
st.header("添加新菜谱")
with st.form("add_form", clear_on_submit=True):
    col1, col2 = st.columns([2,1])
    with col1:
        name = st.text_input("名称 / Name", "")
        cuisine = st.text_input("国家 / Cuisine", "")
        rtype = st.selectbox("类别 / Type", options=["Main","Dessert","Snack","Appetizer","Side","Drink","Other"], index=0)
        ingredients = st.text_area("食材（用逗号分隔）", help="例如: tomato, basil, mozzarella")
        instructions = st.text_area("做法 / Instructions", height=200)
    with col2:
        servings = st.text_input("份量 / Servings", "")
        prep_time = st.text_input("准备时间 / Prep time", "")
        cook_time = st.text_input("烹饪时间 / Cook time", "")
        tags = st.text_input("标签（逗号分隔）", "")
        image_file = st.file_uploader("上传菜谱图片（可选）", type=["png","jpg","jpeg","webp"])
    submitted = st.form_submit_button("添加菜谱")
    if submitted:
        if not name.strip() or not ingredients.strip() or not instructions.strip():
            st.error("请至少填写名称、食材与做法。")
        else:
            img_path = ""
            if image_file is not None:
                try:
                    img_path = save_image(image_file, prefix=name.replace(" ", "_"))
                except Exception as e:
                    st.warning(f"图片保存失败：{e}")
            rec = {
                "name": name.strip(),
                "cuisine": cuisine.strip(),
                "type": rtype,
                "ingredients": ingredients.strip(),
                "instructions": instructions.strip(),
                "servings": servings.strip(),
                "prep_time": prep_time.strip(),
                "cook_time": cook_time.strip(),
                "image_path": img_path,
                "tags": tags.strip()
            }
            add_recipe(conn, rec)
            st.success(f"已添加：{name}")

st.markdown("---")

# List / display results
st.header("菜谱列表")
filtered = search_filter(all_recipes, q, selected_cuisines, selected_types)

st.info(f"共 {len(filtered)} 道菜符合当前筛选。你可以搜索名称、食材或标签；也可以导入更多菜谱以扩展数据库。")

# pagination simple
per_page = st.selectbox("每页显示", options=[6,12,24], index=1)
page = st.number_input("页面", min_value=1, value=1, step=1)
start = (page-1)*per_page
end = start + per_page
page_items = filtered[start:end]

cols = st.columns(3)
for idx, r in enumerate(page_items):
    c = cols[idx % 3]
    with c:
        st.subheader(r["name"])
        meta = f"{r.get('cuisine','Unknown')} · {r.get('type','')}"
        st.caption(meta)
        if r.get("image_path"):
            try:
                st.image(r["image_path"], use_column_width=True)
            except Exception:
                st.write("(图片无法显示)")
        else:
            # placeholder small image
            st.image(Image.new("RGB", (400,250), color=(240,240,240)), use_column_width=True)
        st.write(r.get("ingredients","").split(",")[:6])
        cols_row = st.columns([1,1,1])
        if cols_row[0].button("查看", key=f"view_{r['id']}"):
            st.session_state["view_id"] = r["id"]
        if cols_row[1].button("复制到添加表单", key=f"copy_{r['id']}"):
            # copy to form fields by setting session_state (quick prefill via query params)
            st.experimental_set_query_params(prefill=r["id"])
            st.success("已将该菜谱的内容载入 URL 查询参数，可刷新 '添加新菜谱' 表单获取预填（或手动复制）。")
        if cols_row[2].button("删除", key=f"del_{r['id']}"):
            # warning + delete
            if st.confirm := st.checkbox(f"确认删除 {r['name']}？", key=f"confirm_{r['id']}"):
                cdel = conn.cursor()
                cdel.execute("DELETE FROM recipes WHERE id = ?", (r["id"],))
                conn.commit()
                st.experimental_rerun()

# show details if selected
if "view_id" in st.session_state:
    rid = st.session_state["view_id"]
    full = get_recipe_by_id(conn, rid)
    if full:
        st.markdown("---")
        st.header(f"🔎 {full['name']}")
        st.write(f"**国家 / Cuisine:** {full.get('cuisine','')}")
        st.write(f"**类别 / Type:** {full.get('type','')}")
        st.write(f"**份量:** {full.get('servings','')}")
        st.write(f"**准备 : 烹饪:** {full.get('prep_time','')} / {full.get('cook_time','')}")
        if full.get("image_path"):
            try:
                st.image(full["image_path"], use_column_width=False, width=400)
            except:
                pass
        st.subheader("食材 / Ingredients")
        for ing in [i.strip() for i in full.get("ingredients","").split(",") if i.strip()]:
            st.write(f"- {ing}")
        st.subheader("做法 / Instructions")
        st.write(full.get("instructions",""))
        if full.get("tags"):
            st.caption(f"标签：{full.get('tags')}")
        if st.button("关闭详情"):
            del st.session_state["view_id"]

st.markdown("---")
st.caption("提示：要实现覆盖全世界菜谱的目标，建议获取或构建包含大量条目的 CSV（常见列在侧边栏），再通过“导入 CSV”批量导入；或者连接到公开菜谱 API/数据库并编写脚本批量抓取并标准化数据。")
