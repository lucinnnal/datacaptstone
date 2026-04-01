# YouTube Data Capstone Project

YouTube 채널 리스트를 입력받아 각 채널의 최신 영상에서 **transcript(자막)**, **timestamp 댓글**, **일반 댓글**을 자동 수집하고, Gemini 2.5를 활용하여 sLLM 학습용 요약 데이터를 생성하는 파이프라인입니다.

## 파이프라인 개요

```
channels.jsonl ─► channel_collector.py ─► combined_data.jsonl ─► summarize_with_gemini.py ─► gemini_results_for_training.jsonl
                  (채널별 최신 10개 영상      (transcript + 댓글       (Gemini 2.5 요약)           (sLLM 학습 데이터)
                   URL 추출 → 데이터 수집)     원시 데이터)
```

## 요구사항

- Python 3.x
- Conda 환경 (`datacapstone`)

```bash
conda activate datacapstone
pip install -r requirements.txt
```

### 패키지 목록
| 패키지 | 용도 |
|--------|------|
| `yt-dlp` | 채널 영상 목록 추출, 영상 길이 조회 |
| `youtube-transcript-api` | 자막(transcript) 수집 |
| `youtube-comment-downloader` | 댓글 수집 |
| `google-genai` | Gemini API 호출 |

## 사용법

### 1. 채널 리스트 준비

`channels.jsonl` 파일에 수집할 채널을 한 줄에 하나씩 JSON 형식으로 작성합니다.

```jsonl
{"channel_url": "https://www.youtube.com/@channel_handle", "channel_name": "채널이름1"}
{"channel_url": "https://www.youtube.com/channel/UC...", "channel_name": "채널이름2"}
```

지원하는 필드: `channel_url` (또는 `url`, `channel`), `channel_name` (또는 `name`)

### 2. 데이터 수집 실행

```bash
./run.sh channels.jsonl [output_directory] [videos_per_channel]
```

- `channels.jsonl` — 채널 리스트 파일 (필수)
- `output_directory` — 출력 디렉토리 (기본값: `output_dir`)
- `videos_per_channel` — 채널당 수집할 영상 수 (기본값: `10`)

#### 수집 결과 (output_dir/)
| 파일 | 내용 |
|------|------|
| `urls.jsonl` | 수집 대상 영상 URL 목록 |
| `combined_data.jsonl` | 영상별 transcript + 댓글 원시 데이터 |
| `collection_log.json` | 수집 실행 로그 |

### 3. Gemini 요약 생성

```bash
export GEMINI_API_KEY="your_api_key_here"
./run_gemini.sh output_dir/combined_data.jsonl [output.jsonl]
```

출력: `gemini_results_for_training.jsonl` — 영상별 요약 (sLLM 학습 데이터)

## 프로젝트 구조

```
datacaptstone/
├── channel_collector.py       # 메인 수집기: 채널 → 영상 URL 추출 → 데이터 수집
├── youtube_collector.py       # 단일 영상 수집 모듈 (transcript + 댓글)
├── batch_collector.py         # URL 리스트 기반 배치 수집 (레거시)
├── parse_comments.py          # combined_data.jsonl → 댓글/자막 분리 저장 (유틸리티)
├── summarize_with_gemini.py   # Gemini 2.5 요약 생성
├── channels.jsonl             # 채널 리스트 입력 파일
├── run.sh                     # 데이터 수집 실행 스크립트
├── run_gemini.sh              # Gemini 요약 실행 스크립트
├── requirements.txt           # Python 패키지 목록
└── output_dir/                # 출력 디렉토리
```

## 데이터 형식

### combined_data.jsonl (한 줄 = 한 영상)
```json
{
  "video_url": "https://www.youtube.com/watch?v=...",
  "video_id": "...",
  "success": true,
  "video_length": 600,
  "channel_name": "채널이름",
  "title": "영상제목",
  "transcript": [{"text": "...", "start": 0.0, "duration": 3.5}, ...],
  "timestamp_comments": [{"text": "1:23 이 부분 좋아요", "timestamps_found": [...], ...}, ...],
  "regular_comments": [{"text": "좋은 영상이네요", ...}, ...]
}
```

### gemini_results_for_training.jsonl (한 줄 = 한 영상)
```json
{
  "video_url": "...",
  "video_id": "...",
  "video_length": 600,
  "prompt": "...",
  "gemini_summary": "1. 비디오 핵심 요약 ... 2. 주요 하이라이트 ... 3. 시청자 반응 요약 ..."
}
```
