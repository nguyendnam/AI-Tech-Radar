# AI Tech Radar

AI Tech Radar tự động theo dõi tin tức, nghiên cứu, model AI, công cụ lập trình, repository, release và package từ RSS, arXiv, Hacker News, GitHub, Hugging Face và PyPI. Gemini đánh giá và tóm tắt bằng tiếng Việt; Supabase lưu dữ liệu trong một bảng `radar_items`; Telegram nhận các nội dung đáng chú ý.

## Cài đặt

Yêu cầu Python 3.12+. Node.js 22+ nếu dùng Cloudflare scheduler.

Tạo môi trường Python và cài dependencies:

```sh
python -m venv .venv
```

Kích hoạt trên Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Hoặc Linux/macOS:

```sh
source .venv/bin/activate
```

```sh
pip install -r requirements.txt
```

Copy `.env.example` thành `.env` và điền:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SECRET_KEY=YOUR_SECRET_OR_SERVICE_ROLE_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

Dùng Supabase secret/service-role key, không dùng anon key. Có thể thêm `GITHUB_TOKEN` để collector GitHub có hạn mức API cao hơn.

Trong Supabase SQL Editor, chạy toàn bộ [sql/schema.sql](sql/schema.sql) **một lần** để tạo database. Đây là schema cài mới; nếu đã tạo bảng thì bỏ qua bước này. Khi thay thế bản cũ, dừng lịch chạy và xóa các bảng cũ của dự án trước khi chạy schema.

## Chạy dự án

Chạy các lệnh tại thư mục gốc:

```sh
python scripts/test_connections.py
python collect.py
python digest.py
python cleanup.py
```

- `test_connections.py`: kiểm tra kết nối Gemini, Supabase và Telegram.
- `collect.py`: thu thập mọi nguồn, phân tích bằng Gemini và lưu nội dung đủ điểm; tối đa 25 request AI mỗi lượt, tính cả retry.
- `digest.py`: gửi tối đa 12 nội dung chưa gửi, từ 6.5 điểm trở lên.
- `cleanup.py`: dọn dữ liệu cũ theo mức điểm, giữ các mục đã lưu hoặc có trạng thái `ADOPT`.

Tùy chỉnh từ khóa, watchlist và giới hạn trong [config/profile.yaml](config/profile.yaml). RSS và giới hạn Hacker News nằm trong `src/config.py`.

Nếu chưa biết chat ID, nhắn cho bot Telegram rồi chạy `python scripts/get_telegram_chat_id.py`.

## Chạy tự động

Push code lên GitHub, thêm repository Secrets: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Có thể đặt Variable `GEMINI_MODEL` để đổi model.

Trong tab Actions, chạy lần lượt `AI Tech Radar - collect`, `AI Tech Radar - digest`, `AI Tech Radar - cleanup` để kiểm tra. Workflow `Check AI Tech Radar` tự kiểm tra code và tests khi push hoặc mở PR.

Cloudflare Worker kích hoạt các workflow theo lịch. Kiểm tra owner/repo/branch trong `scheduler/wrangler.jsonc`, rồi deploy:

```sh
cd scheduler
npm ci
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npm run deploy
```

`GITHUB_TOKEN` của Worker cần quyền **Actions: write** với repository. Nếu secret đã có và còn hợp lệ, bỏ qua lệnh đặt secret.

Lịch giờ Việt Nam (UTC+7): collect **06:45** mỗi ngày, digest **07:30** mỗi ngày, cleanup **03:00 Chủ Nhật**. Sau khi deploy, hệ thống chạy trên Cloudflare và GitHub Actions, không cần để máy cá nhân mở.
