import streamlit as st
import pandas as pd
import statistics
import datetime
import csv
import os
import random

# --- 核心邏輯類別 ---
class Job:
    def __init__(self, job_id, processing_time, due_date, urgent_job=False, quantity=1):
        self.job_id = job_id
        self.quantity = quantity
        self.processing_time = processing_time
        self.due_date = due_date
        self.urgent_job = urgent_job
        self.start_time = 0
        self.completion_time = 0
        self.machine_id = 1
        self.tardiness = 0
        self.lateness = 0 
        self.progress_status = ""

def calculate_schedule(jobs, rule, manual_order, machine_count):
    if rule == "SPT":
        jobs.sort(key=lambda x: x.processing_time) 
    elif rule == "LPT":
        jobs.sort(key=lambda x: x.processing_time, reverse=True) 
    elif rule == "EDD":
        jobs.sort(key=lambda x: x.due_date) 
    elif rule == "CR":
        jobs.sort(key=lambda x: x.due_date / x.processing_time if x.processing_time > 0 else 0)
    elif rule == "MANUAL" and manual_order:
        order_mapping = {job_id: index for index, job_id in enumerate(manual_order)}
        jobs.sort(key=lambda x: order_mapping.get(x.job_id, 999))

    machines_available_time = [0] * machine_count
    
    for job in jobs:
        earliest_machine_idx = machines_available_time.index(min(machines_available_time))
        job.start_time = machines_available_time[earliest_machine_idx]
        job.completion_time = job.start_time + job.processing_time
        machines_available_time[earliest_machine_idx] = job.completion_time
        job.machine_id = earliest_machine_idx + 1 
        job.lateness = job.completion_time - job.due_date 
        job.tardiness = max(0, job.lateness) 
        
        if job.lateness < 0: job.progress_status = "進度超前"
        elif job.lateness == 0: job.progress_status = "準時"
        else: job.progress_status = "進度落後"

    makespan = max(machines_available_time)
    avg_flow = sum(j.completion_time for j in jobs) / len(jobs) if jobs else 0
    tardy_count = sum(1 for j in jobs if j.tardiness > 0)
    
    return jobs, makespan, avg_flow, tardy_count

# --- Streamlit 介面 ---
st.set_page_config(page_title="AI 排程決策支援系統", layout="wide")
st.title("🏭 生產排程決策系統 (Streamlit 版)")

# 側邊欄：參數設定
with st.sidebar:
    st.header("⚙️ 參數設定")
    order_count = st.slider("訂單數量", 5, 10, 10)
    machine_count = st.slider("機台數量", 1, 5, 4)
    avg_proc = st.slider("平均加工時間 (分)", 30, 60, 45)
    urgency = st.selectbox("訂單緊迫度", ["high", "medium", "low"])
    rule = st.selectbox("排程法則", ["FCFS", "SPT", "LPT", "EDD", "CR", "MANUAL"])
    
    manual_input = ""
    if rule == "MANUAL":
        manual_input = st.text_input("手動順序 (逗號隔開)", "1,2,3,4,5,6,7,8,9,10")

# 生成資料
fixed_quantities = {1: 95, 2: 80, 3: 76, 4: 52, 5: 67, 6: 28, 7: 34, 8: 21, 9: 100, 10: 44}
random.seed(f"{order_count}_{machine_count}_{avg_proc}_{urgency}")
jobs = []
for i in range(1, order_count + 1):
    qty = fixed_quantities.get(i, 50)
    p_time = int(random.normalvariate(avg_proc, avg_proc * 0.15))
    multiplier = {"high": 1.2, "medium": 2.5, "low": 4.0}[urgency]
    d_date = random.randint(0, 20) + int(p_time * multiplier)
    jobs.append(Job(i, p_time, d_date, quantity=qty))

# 執行計算
manual_order = [int(x.strip()) for x in manual_input.split(',')] if manual_input else []
sorted_jobs, mspan, aflow, tcount = calculate_schedule(jobs, rule, manual_order, machine_count)

# --- 顯示結果 ---
col1, col2, col3 = st.columns(3)
col1.metric("最後完工時間 (Makespan)", f"{mspan} 分")
col2.metric("平均流程時間", f"{aflow:.2f} 分")
col3.metric("延誤訂單數", f"{tcount} 筆")

# 表格顯示
df = pd.DataFrame([{
    "訂單編號": f"訂單 {j.job_id}",
    "數量": j.quantity,
    "機台": f"機台 {j.machine_id}",
    "加工時間": j.processing_time,
    "交期": j.due_date,
    "開始時間": j.start_time,
    "完成時間": j.completion_time,
    "延遲時間": j.tardiness,
    "狀態": j.progress_status
} for j in sorted_jobs])

st.dataframe(df, use_container_width=True)

# --- 學生交卷區 ---
st.divider()
st.subheader("📝 提交實作心得")
with st.form("submit_form"):
    c1, c2, c3 = st.columns(3)
    s_class = c1.text_input("班級")
    s_id = c2.text_input("學號")
    s_name = c3.text_input("姓名")
    s_answer = st.text_area("針對此排程結果的分析心得：")
    
    if st.form_submit_button("確認送出"):
        file_name = 'student_answers.csv'
        header = ['時間', '班級', '學號', '姓名', '策略', '心得']
        data = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s_class, s_id, s_name, rule, s_answer]
        
        file_exists = os.path.isfile(file_name)
        with open(file_name, mode='a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists: writer.writerow(header)
            writer.writerow(data)
        st.success("答案已成功儲存！")

# 老師下載區
if os.path.exists('student_answers.csv'):
    with open('student_answers.csv', 'rb') as f:
        st.download_button(
            label="📥 老師專用：下載學生作答紀錄 (CSV)",
            data=f,
            file_name=f"answers_{datetime.datetime.now().strftime('%m%d')}.csv",
            mime="text/csv"
        )
