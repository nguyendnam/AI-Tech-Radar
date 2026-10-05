# AI Tech Radar

Một hệ thống theo dõi tin tức, nghiên cứu, model AI, developer tool, repository, release và package. Mọi nguồn dùng chung pipeline, ngân sách AI, database và bản tin Telegram.

```text
RSS / arXiv / Hacker News / GitHub / Hugging Face / PyPI
  → chuẩn hóa và khử trùng → xếp hạng → Gemini → radar_items → Telegram
```

## Chạy local

Python 3.12+ và Node.js 22+ cho scheduler.

```sh
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` thành `.env`, điền Supabase secret/service-role key, Gemini API key và Telegram bot/chat ID. Không dùng Supabase anon key.

```sh
python collect.py
python digest.py
python cleanup.py
```

- `collect.py`: mọi nguồn dùng chung tối đa 25 HTTP request Gemini mỗi lượt, bao gồm retry và request thất bại. Nghỉ tối thiểu 6 giây giữa request, retry tối đa 3 lần thử cho lỗi 429/500/502/503/504 với thời gian chờ tăng dần. Chia lượt phân tích giữa các loại nội dung để model/repo không chiếm hết quota.
- `digest.py`: một luồng bản tin, tối đa 12 mục; cân bằng loại nội dung. Chỉ cập nhật `sent_at` sau khi gửi thành công, mục thất bại được thử lại lần chạy sau.
- `cleanup.py`: giữ mục dưới 7 điểm trong 30 ngày, từ 7 đến dưới 9 trong 90 ngày, từ 9 trở lên trong 365 ngày. Không xóa mục `saved=true` hoặc `ADOPT`. Có thể đổi qua `RETENTION_*_DAYS`.

Tùy chỉnh từ khóa, watchlist, giới hạn và điểm trong `config/profile.yaml`. RSS và giới hạn Hacker News ở `src/config.py`. `GEMINI_MODEL` mặc định `gemini-3.5-flash-lite`, có thể đổi qua biến môi trường.

## Supabase — chỉ một lần Run

Đây là schema cài mới, không phải migration dữ liệu cũ.

1. Tạm dừng lịch Worker trong thời gian đổi database và code. Sao lưu nếu cần giữ dữ liệu cũ.
2. Xóa các bảng cũ của dự án: `radar_metrics` trước, rồi `articles` và `radar_items`.
3. Mở `sql/schema.sql`, copy **toàn bộ file** vào Supabase SQL Editor và bấm **Run một lần**. File có transaction; không chạy các đoạn riêng lẻ.
4. Chạy code mới và bật lại lịch.

Chỉ có bảng `public.radar_items`, dùng chung cho mọi nguồn. Stars, forks, downloads, likes, source, version và các dữ kiện nguồn nằm trong `metadata` JSONB; không lưu lịch sử metrics riêng. Schema bao gồm unique URL, unique ID theo nguồn, check điểm/loại/status, index và RLS. `anon`/`authenticated` không có quyền; backend dùng secret/service-role key.

File yêu cầu bảng mới chưa tồn tại. Chạy lại khi bảng tồn tại sẽ báo lỗi và rollback, không tự xóa dữ liệu của bạn.

## GitHub Actions và Cloudflare

Repository: https://github.com/nguyendnam/AI-Tech-Radar

Trong GitHub repository, cấu hình Secrets: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Có thể đặt repository Variable `GEMINI_MODEL`; workflow collect tự cung cấp `github.token` cho collector GitHub.

Ba workflow dùng cùng concurrency group để collect/digest/cleanup không ghi dữ liệu chồng nhau. Giữ tên `collect-news.yml` để Worker đã deploy vẫn dispatch được, nhưng workflow này thu thập **tất cả** nguồn.

Worker dùng `GITHUB_OWNER=nguyendnam`, `GITHUB_REPO=AI-Tech-Radar`, `GITHUB_REF=main` trong `scheduler/wrangler.jsonc`. Secret `GITHUB_TOKEN` của Worker phải có quyền Actions write cho repository này. Local collector chỉ cần quyền đọc repository công khai; có thể đặt token trong `.env` để tăng hạn mức API.

Sau khi push code mới, deploy lại Worker để áp dụng cấu hình username trên Cloudflare:

```sh
cd scheduler
npm ci
npx wrangler secret put GITHUB_TOKEN
npm run deploy
```

Nếu Worker đã có token hợp lệ thì không cần đặt lại. Việc đổi username không tự cập nhật vars trong Worker đã deploy.

Lịch UTC+7: collect 06:45, digest 07:30, cleanup Chủ Nhật 03:00. Cloudflare cron dùng UTC.

## Cấu trúc

```text
collect.py / digest.py / cleanup.py  # entrypoints
src/pipeline.py                    # orchestration chung
src/collectors/                    # nguồn GitHub, Hugging Face, PyPI
src/rss_collector.py, hn_collector.py
src/ai.py, scoring.py               # đánh giá và xếp hạng
src/database.py                    # một storage contract
src/digest.py, telegram_sender.py   # render và gửi
config/profile.yaml                # cấu hình ưu tiên và quota
sql/schema.sql                     # toàn bộ database
scheduler/                         # Cloudflare cron → GitHub Actions
```

## Kiểm tra

```sh
pip install -r requirements.txt
ruff check src scripts tests collect.py digest.py cleanup.py
ruff format --check src scripts tests collect.py digest.py cleanup.py
python -m unittest discover -s tests -v
node --test scheduler/src/index.test.js
python scripts/test_connections.py
```

Unit tests chạy offline, mock các dịch vụ ngoài. SQL được kiểm tra cú pháp bằng PostgreSQL parser; cần chạy thực tế trên Supabase để xác nhận quyền và môi trường của project. `test_connections.py` đọc bảng mới, kiểm tra Gemini và Telegram getChat, không gửi bản tin hay ghi database.

Nếu Telegram đã nhận tin nhưng kết nối timeout hoặc việc đánh dấu database thất bại, lần retry vẫn có thể gửi trùng; Telegram không hỗ trợ transaction chung với Supabase. Nguồn nào lỗi được ghi warning và nguồn khác tiếp tục. Lỗi Gemini tạm thời ghi `deferred`, không làm hỏng lượt collect nếu đã phân tích thành công nội dung khác; candidate chưa lưu có thể được thử lại nếu nguồn còn trả về ở lượt sau. Nếu quota 429 vẫn lỗi sau retry, ngừng gọi AI trong lượt đó. Nếu mọi lần phân tích đều lỗi tạm thời, cấu hình key/model sai, không có dữ liệu nguồn hoặc có lỗi xử lý/lưu/gửi, job vẫn thất bại. Log Gemini có HTTP code, status và thông báo đã che API key.

`checks.yml` chạy lint, format, Python tests và Worker tests khi push hoặc mở PR. Nó không dùng secrets, không gọi Gemini thật và không gửi Telegram; giữ workflow này để phát hiện lỗi code trước khi các job theo lịch chạy.

Gemini generate-content/JSON output: https://ai.google.dev/api/generate-content
