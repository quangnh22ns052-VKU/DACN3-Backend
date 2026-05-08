import requests

response = requests.get('http://localhost:8000/admin/database/stats')
data = response.json()

print('📊 Database Statistics:')
print(f"  Primary (Neon): {data['primary']['scans']} scans")
print(f"  Backup (Supabase): {data['backup']['scans']} scans")
print(f"  ✅ IN SYNC: {data['in_sync']}")
