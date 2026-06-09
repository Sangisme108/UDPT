# Load Aware Scheduler

Demo scheduling cho Dkron bằng controller bên ngoài viết bằng Python.

Project hiện có 2 chức năng:

- Feature 1: Load-aware Scheduling
- Feature 2: Retry + Reassignment

## Yêu cầu

- Docker Desktop hoặc Docker Engine có hỗ trợ `docker compose`
- Python 3

## Feature 1: Load-aware Scheduling

Script `load_scheduler.py` đọc CPU/RAM của các container Dkron, tính score, chọn agent có tải thấp nhất, sau đó tạo và chạy job trên đúng agent đó qua Dkron API.

### Chạy trên Windows

```powershell
docker compose up -d
python -m pip install -r requirements.txt
.\run_scheduler.ps1
```

### Chạy trên macOS/Linux

```bash
docker compose up -d
python3 -m pip install -r requirements.txt
chmod +x run_scheduler.sh
./run_scheduler.sh
```

### Kết quả mong đợi

- In danh sách agent Dkron đang kiểm tra
- In CPU/RAM/score của từng agent
- Chọn agent có score thấp nhất
- Tạo và run job `load-aware-job` trên agent được chọn

## Feature 2: Retry + Reassignment

### Ý tưởng

`retry_reassignment.py` là controller demo bên ngoài Dkron core. Script tạo job `retry-reassign-demo` trên một agent ban đầu, cố tình cho command fail, sau đó kiểm tra retry count, đổi tag target sang agent khác và run lại job với command thành công.

Vì project này không chứa source code Dkron gốc, chức năng này không sửa lõi scheduler bên trong Dkron. Đây là demo-level reassignment thông qua Dkron API. Nếu muốn sửa sâu vào core Dkron, cần mở project source Dkron gốc riêng.

### Luồng demo

```text
docker compose up -d
docker ps
python3 load_scheduler.py
python3 retry_reassignment.py
```

### Chạy trên Windows

```powershell
docker compose up -d
python -m pip install -r requirements.txt
python retry_reassignment.py
```

Hoặc:

```powershell
.\run_retry.ps1
```

### Chạy trên macOS/Linux

```bash
docker compose up -d
python3 -m pip install -r requirements.txt
chmod +x run_retry.sh
python3 retry_reassignment.py
```

Hoặc:

```bash
./run_retry.sh
```

### Kết quả mong đợi

- In danh sách agent từ `http://localhost:8080/v1/members`
- Tạo job fail trên agent ban đầu, mặc định `dkron1`
- In agent fail và retry count
- Chọn agent mới khác agent fail
- Update job với tag mới, ví dụ `"agent": "dkron2:1"`
- Run retry job và in kết quả success

## Dashboard

Mở dashboard Dkron tại:

```text
http://localhost:8080
```

## Nếu container cũ đã tồn tại

Nếu `docker compose up -d` báo lỗi trùng tên container, xoá các container cũ rồi chạy lại:

```bash
docker rm -f dkron1 dkron2 dkron3
docker compose up -d
```

## Cấu hình tuỳ chọn

Mặc định script gọi API:

```text
http://localhost:8080/v1
```

Có thể đổi bằng biến môi trường:

```bash
DKRON_API_URL=http://localhost:8080/v1 python3 ./load_scheduler.py
DKRON_API_URL=http://localhost:8080/v1 python3 ./retry_reassignment.py
```

Biến môi trường riêng cho Feature 2:

```bash
INITIAL_AGENT=dkron1 MAX_RETRY=2 python3 ./retry_reassignment.py
```
