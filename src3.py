import os
import time
import feedparser
import requests
from datetime import datetime, timezone, timedelta
from google import genai


# ============================================================
# CẤU HÌNH
# ============================================================

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


# ============================================================
# DANH SÁCH BÁO & RSS
# ============================================================

SOURCES = {
    "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
    "BBC News": "http://feeds.bbci.co.uk/news/rss.xml",
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "The Guardian": "https://www.theguardian.com/world/rss",
    "The New York Times": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Wired": "https://www.wired.com/feed/rss",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "IEEE Spectrum": "https://spectrum.ieee.org/feeds/feed.rss",
    "Nature Electronics": "https://www.nature.com/natelectron.rss",
    "National Geographic": "https://www.nationalgeographic.com/rss/index.rss"
}


# ============================================================
# CÀO TIN
# ============================================================

def crawl_news():
    """
    Cào tất cả nguồn trong SOURCES.
    Chỉ giữ lại những bài được xuất bản trong 24 giờ gần nhất.
    """

    raw_news = []

    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(hours=24)

    print("=" * 70)
    print("BẮT ĐẦU CÀO TIN")
    print(f"Thời gian hiện tại UTC : {now}")
    print(f"Lấy tin từ             : {time_limit}")
    print("=" * 70)

    for source_name, url in SOURCES.items():

        print(f"\n[{source_name}]")
        print(f"URL: {url}")

        try:
            feed = feedparser.parse(
                url,
                agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                )
            )

            count = 0

            for entry in feed.entries:

                # ------------------------------------------------
                # Lấy ngày xuất bản
                # ------------------------------------------------

                pub_parsed = getattr(
                    entry,
                    "published_parsed",
                    None
                )

                if pub_parsed:

                    pub_date = datetime(
                        *pub_parsed[:6],
                        tzinfo=timezone.utc
                    )

                    # Bỏ bài cũ hơn 24 giờ
                    if pub_date < time_limit:
                        continue

                # ------------------------------------------------
                # Lấy thông tin bài báo
                # ------------------------------------------------

                title = getattr(
                    entry,
                    "title",
                    "Không có tiêu đề"
                )

                summary = getattr(
                    entry,
                    "summary",
                    ""
                )

                link = getattr(
                    entry,
                    "link",
                    ""
                )

                # ------------------------------------------------
                # Đưa vào danh sách
                # ------------------------------------------------

                raw_news.append(
                    f"""
[SOURCE]
{source_name}

[TITLE]
{title}

[SUMMARY]
{summary}

[LINK]
{link}

--------------------------------------------------
"""
                )

                count += 1

            print(f"→ Lấy được {count} bài")

        except Exception as e:

            print(
                f"→ LỖI khi cào {source_name}: {e}"
            )

    print("\n" + "=" * 70)
    print(f"TỔNG SỐ BÀI CÀO ĐƯỢC: {len(raw_news)}")
    print("=" * 70)

    return raw_news


# ============================================================
# GEMINI
# ============================================================

def summarize_with_ai(raw_news):
    """
    Gemini:
    - Phát hiện các bài nói về cùng một sự kiện.
    - Loại bỏ tin trùng.
    - Dịch sang tiếng Việt.
    - Tóm tắt.
    - Giữ lại nguồn và link.
    """

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    news_text = "\n".join(raw_news)

    prompt = f"""
Bạn là một hệ thống tổng hợp tin tức công nghệ và khoa học.

Dưới đây là các bài báo được lấy từ nhiều nguồn RSS:

{news_text}

Hãy xử lý toàn bộ danh sách trên theo các nguyên tắc sau:

1. PHÁT HIỆN TIN TRÙNG

Nếu nhiều bài báo nói về cùng một sự kiện,
hãy gộp chúng thành MỘT tin duy nhất.

Ví dụ:

- WIRED: OpenAI launches GPT-6...
- TechCrunch: OpenAI announces GPT-6...
- The Verge: OpenAI unveils GPT-6...

=> Đây chỉ là MỘT sự kiện và chỉ nên xuất hiện một lần.

Không được coi hai bài là trùng chỉ vì chúng cùng nói về
một chủ đề chung. Chỉ gộp khi nội dung thực sự nói về cùng
một sự kiện/thông tin.

2. ƯU TIÊN THÔNG TIN QUAN TRỌNG

Ưu tiên:

- AI
- Computer Science
- Technology
- Science
- Space
- Cybersecurity
- Hardware
- Software
- Robotics
- Semiconductor
- Research

Những tin ít liên quan đến công nghệ/khoa học vẫn có thể giữ
nếu chúng đặc biệt quan trọng.

3. DỊCH

Dịch nội dung sang tiếng Việt tự nhiên, dễ đọc.

4. TÓM TẮT

Mỗi sự kiện chỉ cần một phần tóm tắt ngắn gọn,
tập trung vào thông tin quan trọng nhất.

5. NGUỒN

PHẢI giữ lại nguồn của bài báo.

Nếu một sự kiện xuất hiện trên nhiều nguồn,
hãy ghi tất cả nguồn liên quan.

Ví dụ:

Nguồn: WIRED, TechCrunch, The Verge

6. LINK

PHẢI giữ link bài báo.

Nếu một sự kiện có nhiều bài báo,
có thể giữ các link quan trọng nhất.

7. ĐỊNH DẠNG

Sử dụng định dạng:

━━━━━━━━━━━━━━━━━━
📰 [TIÊU ĐỀ]
━━━━━━━━━━━━━━━━━━

📌 Tóm tắt:
- ...
- ...
- ...

🌐 Nguồn:
- WIRED
- TechCrunch

🔗 Link:
- https://...

━━━━━━━━━━━━━━━━━━

8. KHÔNG ĐƯỢC BỊA THÔNG TIN.

Chỉ sử dụng thông tin xuất hiện trong dữ liệu được cung cấp.

9. KHÔNG LẶP LẠI CÙNG MỘT SỰ KIỆN.

Nếu có 5 bài báo cùng nói về một sự kiện,
chỉ tạo một mục tin tức.

Hãy tạo bản tin tiếng Việt cô đọng,
dễ đọc trên Discord.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text


# ============================================================
# CHIA MESSAGE CHO DISCORD
# ============================================================

def split_message(text, max_length=3900):
    """
    Discord embed description có giới hạn ký tự.
    Chia văn bản thành các đoạn nhỏ nhưng cố gắng
    không cắt giữa một dòng.
    """

    chunks = []

    while len(text) > max_length:

        # Tìm vị trí xuống dòng gần cuối
        split_pos = text.rfind(
            "\n",
            0,
            max_length
        )

        if split_pos <= 0:
            split_pos = max_length

        chunks.append(
            text[:split_pos]
        )

        text = text[split_pos:].lstrip()

    if text:
        chunks.append(text)

    return chunks


# ============================================================
# GỬI DISCORD
# ============================================================

def send_to_discord(message):

    chunks = split_message(message)

    print(
        f"\nSố message Discord cần gửi: {len(chunks)}"
    )

    success = True

    for index, chunk in enumerate(chunks):

        data = {
            "username": "AI News Bot",

            "embeds": [
                {
                    "title": (
                        "📰 BẢN TIN AI & CÔNG NGHỆ"
                        if index == 0
                        else ""
                    ),

                    "description": chunk,

                    "footer": {
                        "text": (
                            f"AI News Bot • "
                            f"Phần {index + 1}/{len(chunks)}"
                        )
                    }
                }
            ]
        }

        try:

            response = requests.post(
                DISCORD_WEBHOOK_URL,
                json=data,
                timeout=20
            )

            if response.status_code not in (200, 204):

                print(
                    f"Discord lỗi "
                    f"{response.status_code}: "
                    f"{response.text}"
                )

                success = False

            else:

                print(
                    f"Đã gửi Discord "
                    f"{index + 1}/{len(chunks)}"
                )

        except Exception as e:

            print(
                f"Lỗi gửi Discord: {e}"
            )

            success = False

        # Tránh rate limit
        time.sleep(1)

    return success


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n🚀 NEWS AGGREGATOR STARTED\n")

    # --------------------------------------------------------
    # 1. CÀO TIN
    # --------------------------------------------------------

    raw_news = crawl_news()

    if not raw_news:

        print(
            "\n⚠ Không tìm thấy tin mới."
        )

        send_to_discord("⚠ Không tìm thấy tin tức mới trong 24 giờ qua.")

        return

    # --------------------------------------------------------
    # 2. GEMINI XỬ LÝ
    # --------------------------------------------------------

    print(
        "\n🤖 Đang gửi dữ liệu cho Gemini..."
    )

    try:

        summary = summarize_with_ai(
            raw_news
        )

    except Exception as e:

        print(
            f"\n❌ Gemini lỗi: {e}"
        )

        return

    print(
        "\n✅ Gemini đã xử lý xong."
    )

    # --------------------------------------------------------
    # 3. GỬI DISCORD
    # --------------------------------------------------------

    print(
        "\n📤 Đang gửi bản tin về Discord..."
    )

    success = send_to_discord(
        summary
    )

    if success:

        print(
            "\n✅ HOÀN THÀNH!"
        )

    else:

        print(
            "\n❌ Có lỗi khi gửi Discord."
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
