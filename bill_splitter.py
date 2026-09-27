import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="مقسم الفاتورة", page_icon="🧾", layout="centered")
st.title("🧾 مقسم الفاتورة بين الأصحاب")
st.caption("وزّع الفاتورة بعدل، واعرف مين يدفع لمين بأقل عدد تحويلات")

if "people" not in st.session_state:
    st.session_state.people = []

st.header("1️⃣ أضف الأصحاب وطلباتهم")

with st.form("add_person_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("اسم الشخص")
    with col2:
        paid = st.number_input("كم دفع فعلياً (لو دفع من جيبه)", min_value=0.0, step=1.0)

    st.markdown("**أصناف هذا الشخص:**")
    items_raw = st.text_area(
        "اكتب كل صنف بسطر، بصيغة: الاسم, السعر",
        placeholder="برجر, 25\nعصير, 8",
        height=100,
    )
    submitted = st.form_submit_button("➕ إضافة الشخص")

    if submitted and name.strip():
        items = []
        for line in items_raw.strip().splitlines():
            if "," in line:
                item_name, price = line.rsplit(",", 1)
                try:
                    items.append((item_name.strip(), float(price.strip())))
                except ValueError:
                    st.warning(f"تجاهلت السطر (سعر غير صحيح): {line}")
        st.session_state.people.append({"name": name.strip(), "items": items, "paid": paid})
        st.success(f"تمت إضافة {name} ✅")

if st.session_state.people:
    st.subheader("الأشخاص المضافين")
    for i, p in enumerate(st.session_state.people):
        subtotal = sum(price for _, price in p["items"])
        with st.expander(f"{p['name']} — طلباته: {subtotal:.2f}"):
            for item_name, price in p["items"]:
                st.write(f"• {item_name}: {price:.2f}")
            st.write(f"💵 دفع فعلياً: {p['paid']:.2f}")
            if st.button(f"حذف {p['name']}", key=f"del_{i}"):
                st.session_state.people.pop(i)
                st.rerun()

    if st.button("🗑️ مسح الكل"):
        st.session_state.people = []
        st.rerun()

st.header("2️⃣ الضريبة والخدمة (اختياري)")
col1, col2 = st.columns(2)
with col1:
    tax_percent = st.number_input("نسبة الضريبة %", min_value=0.0, max_value=100.0, value=0.0)
with col2:
    service_percent = st.number_input("نسبة الخدمة %", min_value=0.0, max_value=100.0, value=0.0)

split_mode = st.radio(
    "طريقة التقسيم",
    ["حسب طلب كل شخص (غير متساوي)", "بالتساوي بين الكل"],
    horizontal=True,
)


def calculate_shares(people, tax_percent, service_percent, split_mode):
    n = len(people)
    if n == 0:
        return {}

    subtotals = {p["name"]: sum(price for _, price in p["items"]) for p in people}
    grand_subtotal = sum(subtotals.values())

    extra_rate = (tax_percent + service_percent) / 100.0
    shares = {}

    if split_mode == "بالتساوي بين الكل":
        total_bill = grand_subtotal * (1 + extra_rate)
        equal_share = total_bill / n
        for p in people:
            shares[p["name"]] = equal_share
    else:
        for p in people:
            personal_subtotal = subtotals[p["name"]]
            personal_extra = personal_subtotal * extra_rate
            shares[p["name"]] = personal_subtotal + personal_extra

    return shares


def simplify_debts(people, shares):
    balances = {}
    for p in people:
        balances[p["name"]] = round(p["paid"] - shares.get(p["name"], 0), 2)

    creditors = [[name, amt] for name, amt in balances.items() if amt > 0.01]
    debtors = [[name, -amt] for name, amt in balances.items() if amt < -0.01]

    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_name, debt_amt = debtors[i]
        creditor_name, credit_amt = creditors[j]
        pay_amount = min(debt_amt, credit_amt)

        if pay_amount > 0.01:
            transactions.append((debtor_name, creditor_name, round(pay_amount, 2)))

        debtors[i][1] -= pay_amount
        creditors[j][1] -= pay_amount

        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return balances, transactions


st.header("3️⃣ النتيجة النهائية")

if not st.session_state.people:
    st.info("أضف شخص واحد على الأقل عشان تظهر النتائج.")
else:
    shares = calculate_shares(st.session_state.people, tax_percent, service_percent, split_mode)
    balances, transactions = simplify_debts(st.session_state.people, shares)

    df = pd.DataFrame({
        "الاسم": list(shares.keys()),
        "نصيبه من الفاتورة": [round(v, 2) for v in shares.values()],
        "دفع فعلياً": [p["paid"] for p in st.session_state.people],
        "الرصيد (+له / -عليه)": [balances[name] for name in shares.keys()],
    })
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_bill = sum(shares.values())
    st.metric("💰 إجمالي الفاتورة", f"{total_bill:.2f}")

    fig, ax = plt.subplots()
    ax.pie(shares.values(), labels=shares.keys(), autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    st.pyplot(fig)

    st.subheader("🔄 التسوية النهائية (أقل عدد تحويلات)")
    if not transactions:
        st.success("الكل متعادل! ما فيه تحويلات مطلوبة 🎉")
    else:
        summary_lines = []
        for debtor, creditor, amount in transactions:
            line = f"➡️ {debtor} يدفع {amount:.2f} إلى {creditor}"
            st.write(line)
            summary_lines.append(line)

        export_text = "ملخص تقسيم الفاتورة\n" + "=" * 25 + "\n"
        export_text += f"إجمالي الفاتورة: {total_bill:.2f}\n\n"
        export_text += "\n".join(summary_lines)

        st.download_button(
            "⬇️ تحميل الملخص كملف نصي",
            data=export_text,
            file_name="bill_split_summary.txt",
            mime="text/plain",
        )
