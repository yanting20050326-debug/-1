from flask import Flask, request, jsonify, render_template
import statistics
import datetime 
import os 
import random
import gspread # 新增的 Google 試算表套件

app = Flask(__name__)

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
    if rule == "FCFS":
        pass 
    elif rule == "SPT":
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
    total_flow_time = 0
    tardy_jobs_count = 0
    
    for job in jobs:
        earliest_machine_idx = machines_available_time.index(min(machines_available_time))
        job.start_time = machines_available_time[earliest_machine_idx]
        job.completion_time = job.start_time + job.processing_time
        
        machines_available_time[earliest_machine_idx] = job.completion_time
        job.machine_id = earliest_machine_idx + 1 
        
        total_flow_time += job.completion_time 
        job.lateness = job.completion_time - job.due_date 
        job.tardiness = max(0, job.lateness) 
        
        if job.tardiness > 0:
            tardy_jobs_count += 1 
            
        if job.lateness < 0:
            job.progress_status = "進度超前"
        elif job.lateness == 0:
            job.progress_status = "準時"
        else:
            job.progress_status = "進度落後"

    makespan = max(machines_available_time) if machines_available_time else 0
    mean_flow_time = total_flow_time / len(jobs) if jobs else 0
    average_jobs_in_system = total_flow_time / makespan if makespan > 0 else 0
    
    return jobs, makespan, mean_flow_time, tardy_jobs_count, average_jobs_in_system

def ai_decision_support(jobs):
    if not jobs: return "無資料"
    total_tardiness = sum(job.tardiness for job in jobs)
    processing_times = [job.processing_time for job in jobs]
    
    if any(job.urgent_job for job in jobs):
        return "發現急單，建議重新檢視插單優先權"
    threshold = 20 
    if total_tardiness > threshold:
        return "延誤嚴重，建議改採 EDD (最早到期日) 來降低延誤"
    variance_threshold = 10
    if len(processing_times) > 1 and statistics.variance(processing_times) > variance_threshold:
        return "加工時間長短不一，建議測試 SPT (最短處理時間) 以加速流通"
    return "目前排程狀態良好，符合公司策略"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/schedule', methods=['POST'])
def schedule_api():
    data = request.json
    rule = data.get('rule', 'FCFS') 
    is_calculate = data.get('isCalculate', False) 
    
    try: order_count = int(data.get('orderCount', 10))
    except ValueError: order_count = 10
    if is_calculate and not (5 <= order_count <= 10):
        return jsonify({"error": "執行失敗：訂單數量請設定在 5 ~ 10 筆之間！"}), 400
    order_count = max(5, min(10, order_count)) 
    
    try: machine_count = int(data.get('machineCount', 4))
    except ValueError: machine_count = 4
    if is_calculate and not (1 <= machine_count <= 5):
        return jsonify({"error": "執行失敗：機台數請設定在 1 ~ 5 台之間！"}), 400
    machine_count = max(1, min(5, machine_count)) 
    
    try: avg_processing = int(data.get('avgProcessingTime', 45))
    except ValueError: avg_processing = 45
    if is_calculate and not (30 <= avg_processing <= 60):
        return jsonify({"error": "執行失敗：平均加工時間請設定在 30 ~ 60 分鐘之間！"}), 400
    avg_processing = max(30, min(60, avg_processing)) 

    urgency = data.get('urgency', 'high')
    manual_order_str = data.get('manualOrder', '1, 2, 3, 4, 5, 6, 7, 8, 9, 10')
    try: manual_order = [int(x.strip()) for x in manual_order_str.split(',')]
    except: manual_order = list(range(1, order_count + 1))
        
    random.seed(f"{order_count}_{machine_count}_{avg_processing}_{urgency}")
    fixed_quantities = {1: 95, 2: 80, 3: 76, 4: 52, 5: 67, 6: 28, 7: 34, 8: 21, 9: 100, 10: 44}
    
    jobs = []
    for i in range(1, order_count + 1):
        qty = fixed_quantities.get(i, 50)
        p_time = max(30, min(60, int(random.normalvariate(avg_processing, avg_processing * 0.15))))
        if urgency == 'high': multiplier = random.uniform(1.0, 1.5)
        elif urgency == 'medium': multiplier = random.uniform(1.5, 3.0)
        else: multiplier = random.uniform(3.0, 5.0) 
            
        base_offset = random.randint(0, int((order_count * avg_processing) / machine_count / 2) + 1)
        d_date = base_offset + int(p_time * multiplier)
        is_urgent = random.random() < 0.1
        jobs.append(Job(i, processing_time=p_time, due_date=d_date, urgent_job=is_urgent, quantity=qty))
        
    random.seed() 
    sorted_jobs, makespan, mean_flow_time, tardy_jobs_count, average_jobs_in_system = calculate_schedule(jobs, rule, manual_order, machine_count)
    
    if not is_calculate:
        result = {
            "makespan": "-", "mean_flow_time": "-", "tardy_jobs_count": "-", "average_jobs": "-", 
            "ai_suggestion": "請輸入條件並按下「重新執行排程計算」",
            "job_order": [
                {
                    "id": f"訂單 {j.job_id}", "original_id": j.job_id, "quantity": f"{j.quantity} 件", 
                    "machine_id": f"機台 {j.machine_id}", "processing_time": "-", "due_date": "-", 
                    "urgent": "-", "start": "-", "end": "-", "tardiness": "-", "lateness": "-", "status": "-"
                } for j in sorted_jobs
            ]
        }
        return jsonify(result)

    ai_suggestion = ai_decision_support(sorted_jobs) 
    result = {
        "makespan": makespan,
        "mean_flow_time": round(mean_flow_time, 2),
        "tardy_jobs_count": tardy_jobs_count,
        "average_jobs": round(average_jobs_in_system, 2), 
        "ai_suggestion": ai_suggestion,
        "job_order": [
            {
                "id": f"訂單 {j.job_id}", "original_id": j.job_id, "quantity": f"{j.quantity} 件", 
                "machine_id": f"機台 {j.machine_id}", "processing_time": f"{j.processing_time} 分", 
                "due_date": f"{j.due_date} 分", "urgent": "是" if j.urgent_job else "否",
                "start": j.start_time, "end": f"{j.completion_time} 分", 
                "tardiness": j.tardiness, "lateness": j.lateness, "status": j.progress_status 
            } for j in sorted_jobs
        ]
    }
    return jsonify(result)

# === 這是寫入 Google 試算表的核心區塊 ===
@app.route('/api/submit', methods=['POST'])
def submit_answer():
    data = request.json
    student_class = data.get('studentClass', '')
    student_id = data.get('studentId', '')
    student_name = data.get('studentName', '')
    rule_used = data.get('rule', '')
    answer = data.get('answer', '')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # 讀取你在 Render 存放的金鑰
        gc = gspread.service_account(filename='/etc/secrets/credentials.json')
        
        # 這是你剛才提供的專屬試算表網址
        sheet_url = "https://docs.google.com/spreadsheets/d/1rJBpWG5yCz7JHW-33vWWAyIK-rOvoZWvSa8hswca5Pw/edit"
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.sheet1 
        
        # 將學生資料寫入試算表
        worksheet.append_row([timestamp, student_class, student_id, student_name, rule_used, answer])
        
        print(f"✅ 收到新答案！ {student_class} {student_name} 已交卷至雲端。")
        return jsonify({"status": "success", "message": "答案已成功送出並儲存到 Google 試算表！"})
        
    except Exception as e:
        print(f"❌ 雲端寫入錯誤: {e}")
        return jsonify({"status": "error", "message": f"儲存失敗，系統發生錯誤。({e})"}), 500

if __name__ == '__main__':
    app.run(debug=True)
