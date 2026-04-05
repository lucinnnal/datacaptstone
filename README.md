# YouTube Data Capstone Project

YouTube 채널 리스트를 입력받아 각 채널의 최신 영상에서 **transcript(자막)**, **timestamp 댓글**, **일반 댓글**을 자동 수집하고, Gemini 2.5를 활용하여 유의미한 댓글 필터링 및 sLLM 학습용 요약 데이터를 생성하는 파이프라인입니다.

## 파이프라인 개요

```text
inputs/channels.jsonl ─► scripts/crowl_comments.sh ─► comment_results/combined_data.jsonl
                        (채널별 최신 영상 수집)      (transcript + 댓글 원시 데이터)        

[선택 1] 댓글 필터링: 
combined_data.jsonl ─► scripts/run_filter_gemini.sh ─► comment_results/filtered_comments.jsonl
                      (Gemini 2.5 기반 유의미한 댓글 선별)

[선택 2] 영상 요약:
combined_data.jsonl ─► scripts/run_gemini.sh ─► comment_results/gemini_results_for_training.jsonl
                      (Gemini 2.5 영상 및 반응 요약)
```

## 요구사항

- Python 3.10 (for vllm version)
- Conda 환경 (`datacapstone`)

```bash
conda create -n datacapstone python=3.10
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
| `python-dotenv` | 환경 변수 관리 (`.env`) |
| `vllm` | 모델 서빙 패키지 (0.10.0 버전 통일) |

## 설정 (Environment Variables)

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 Gemini API 키를 설정합니다. `.env.example` 파일을 참고하세요.

```bash
cp .env.example .env
# .env 파일을 열어 API 키를 입력하세요.
# GEMINI_API_KEY=your_actual_api_key_here
```

## 사용법

### 1. 채널 리스트 준비

`inputs/channels.jsonl` 파일에 수집할 채널을 한 줄에 하나씩 JSON 형식으로 작성합니다.

```jsonl
{"channel_url": "https://www.youtube.com/@channel_handle", "channel_name": "채널이름1"}
{"channel_url": "https://www.youtube.com/channel/UC...", "channel_name": "채널이름2"}
```

### 2. 데이터 수집 실행

```bash
./scripts/crowl_comments.sh inputs/channels.jsonl [output_directory] [videos_per_channel]
```

- `inputs/channels.jsonl` — 채널 리스트 파일 (기본 위치)
- `output_directory` — 출력 디렉토리 (기본값: `comment_results`)
- `videos_per_channel` — 채널당 수집할 영상 수 (기본값: `10`)

#### 수집 결과 (`comment_results/`)
| 파일 | 내용 |
|------|------|
| `urls.jsonl` | 수집 대상 영상 URL 목록 |
| `combined_data.jsonl` | 영상별 transcript + 댓글 원시 데이터 |
| `collection_log.json` | 수집 실행 로그 |

### 3. Gemini 댓글 필터링 생성 (신규)

수집된 댓글에서 정보성, 의견성, 연관성 기준(각 1~3점)을 평가하여 총점 6점 이상인 유의미한 댓글만 선별합니다. `.env` 파일에 `GEMINI_API_KEY`가 설정되어 있어야 합니다. (선택적으로 `generation_configs/gemini.json` 파일을 통해 모델 설정 및 temperature 등을 관리할 수 있습니다.)

```bash
./scripts/filter_comments.sh --input comment_results/combined_data.jsonl --output comment_results/filtered_comments.jsonl
```

출력: `comment_results/filtered_comments.jsonl` — 영상별 평가된 댓글 (총점 및 통과 여부 포함)

### 4. EXAONE 댓글 필터링 생성 (신규)

수집된 댓글에서 정보성, 의견성, 연관성 기준(각 1~3점)을 평가하여 총점 6점 이상인 유의미한 댓글만 선별합니다. 로컬 GPU를 활용하여 EXAONE 4.0 32B 모델을 vLLM으로 서빙하고 결과를 추론합니다. `scripts/run_filter_exaone.sh` 스크립트가 서빙과 추론을 자동으로 순차 진행하고 완료 시 서버를 종료합니다.

```bash
./scripts/run_filter_exaone.sh comment_results/combined_data.jsonl comment_results/filtered_comments_exaone.jsonl 1
```

- `1` (세 번째 인자)는 텐서 병렬화(Tensor Parallel) 사이즈입니다. (기본값: 1)

출력: `comment_results/filtered_comments_exaone.jsonl` — 영상별 평가된 댓글 (총점 및 통과 여부 포함)

### 5. Gemini 요약 생성

`.env` 파일에 `GEMINI_API_KEY`가 설정되어 있어야 합니다.

```bash
./scripts/run_gemini.sh comment_results/combined_data.jsonl [output.jsonl]
```

출력: `comment_results/gemini_results_for_training.jsonl` — 영상별 요약 (sLLM 학습 데이터)

## 프로젝트 구조

```
datacaptstone/
├── channel_collector.py           # 메인 수집기: 채널 → 영상 URL 추출 → 데이터 수집
├── youtube_collector.py           # 단일 영상 수집 모듈 (transcript + 댓글)
├── batch_collector.py             # URL 리스트 기반 배치 수집 (레거시)
├── parse_comments.py              # combined_data.jsonl → 댓글/자막 분리 저장 (유틸리티)
├── summarize_with_gemini.py       # Gemini 2.5 요약 생성 (sLLM 학습용)
├── filter_comments_with_gemini.py # Gemini 2.5 댓글 필터링 (평가 기준 적용)
├── filter_comments_with_exaone.py # EXAONE 4.0 32B 댓글 필터링 (vLLM 활용)
├── analyze_comments.py            # 수집된 댓글 분석 유틸리티
├── check_timestamps.py            # 타임스탬프 유효성 검사 유틸리티
├── comment_stats.py               # 댓글 통계 생성 유틸리티
├── requirements.txt               # Python 패키지 목록
├── .env                           # 환경 변수 (API 키 등 - Git 제외)
├── .env.example                   # .env 템플릿
├── inputs/
│   └── channels.jsonl             # 채널 리스트 입력 파일
├── comment_results/               # 데이터 수집 결과 저장 폴더
└── scripts/
    ├── crowl_comments.sh          # 데이터 수집 통합 실행 스크립트
    ├── run_filter_gemini.sh       # Gemini 댓글 필터링 실행 스크립트
    ├── run_filter_exaone.sh       # EXAONE 댓글 필터링 서빙 및 추론 실행 스크립트
    └── run_gemini.sh              # Gemini 요약 실행 스크립트
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
`
