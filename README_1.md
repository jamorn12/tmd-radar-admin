# tmd-radar-admin

หน้า Admin ของระบบทันฝน (Streamlit Community Cloud)

แยกออกจาก repo `tmd-radar-archive` เพราะ repo นั้นใหญ่ ~1.2 GB และมี commit ทุก 15 นาที
Streamlit Cloud ต้อง clone ทั้ง repo ทุกครั้งที่บูต จึงค้างที่ "Cloning repository..."

แอปนี้ไม่อ่านไฟล์ในเครื่องเลย ทุกอย่างดึงผ่าน GitHub API และ raw.githubusercontent.com
ตามค่าใน Secrets: `GITHUB_TOKEN`, `REPO_OWNER` (jamorn12), `REPO_NAME` (tmd-radar-archive)
