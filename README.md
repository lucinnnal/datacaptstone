# YouTube Data Capstone Project

This project collects YouTube transcripts and comments (separated into timestamp and regular comments), and utilizes the Gemini API (Gemini 2.5) to generate comprehensive video summaries for sLLM training.

## Requirements
- Python 3.x
- `yt-dlp`
- `youtube-transcript-api`
- `youtube-comment-downloader`
- `google-genai`

**Important:** You must manually install these dependencies in your Conda environment or preferred Python environment before running the scripts.

```bash
pip install -r requirements.txt
```

## Features
1. **YouTube Data Collection**: Collects video length, transcripts, timestamp comments, and regular comments, combining them into a single `combined_data.jsonl` file.
2. **Gemini Summary Generation**: Uses Gemini 2.5 to analyze the collected data and generate video summaries. The results are saved to `gemini_results_for_training.jsonl`.

## How to Run

### 1. Environment Setup
Activate your Conda environment and install requirements:
```bash
conda activate your_env_name
pip install -r requirements.txt
```

### 2. Data Collection
Run the collection script with your URLs:
```bash
./run.sh urls.jsonl output_dir
```

This creates `combined_data.jsonl` in your output directory.

### 3. Gemini Summary Generation
Export your Gemini API key and run the summary generator:
```bash
export GEMINI_API_KEY="your_api_key_here"

./run_gemini.sh output_dir/combined_data.jsonl gemini_results_for_training.jsonl
```
The summaries will be saved to `gemini_results_for_training.jsonl`.
