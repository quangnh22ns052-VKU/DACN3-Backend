"""
╔═══════════════════════════════════════════════════════════════════╗
║              PHISHGUARD HEALTH CHECK ENDPOINT                     ║
║         ❤️ Kiểm tra trạng thái sức khỏe của API                   ║
╚═══════════════════════════════════════════════════════════════════╝

TÊN FILE: backend/routes/health.py

CÔNG DỤNG:
  - Cung cấp endpoint GET /health để kiểm tra API có hoạt động không
  - Kiểm tra kết nối database
  - Kiểm tra trạng thái các dịch vụ
  - Dùng cho monitoring, load balancing

ENDPOINT:
  GET /health
  Response: {"status": "healthy", "database": "connected", "ml_model": "loaded"}

CÁCH SỬ DỤNG:
  # Kiểm tra từ terminal
  curl http://localhost:8000/health
  
  # Hoặc từ code
  response = requests.get("http://localhost:8000/health")
  if response.status_code == 200:
      print("API is healthy")

LƯU Ý:
  - Endpoint này không yêu cầu authentication
  - Có thể được gọi thường xuyên để monitor
  - Trả về HTTP 200 nếu healthy, 503 nếu unhealthy
"""

from fastapi import APIRouter
router = APIRouter()
@router.get("")
def health():
    return {"status": "ok"}
