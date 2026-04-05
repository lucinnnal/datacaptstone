#!/usr/bin/env python3
"""
Filter YouTube Comments with Gemini 2.5 Flash
Reads combined_data.jsonl, scores comments based on criteria using Gemini,
and outputs filtered results to a new JSONL file.
"""

import json
import os
import sys
import argparse
import time
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Please install google-genai: pip install google-genai")
    sys.exit(1)

PROMPT_TEMPLATE = """
당신은 YouTube 영상의 댓글을 분석하고 필터링하는 전문가입니다. 
당신의 목표는 주어진 Transcript(영상 자막/대본)를 바탕으로, 시청자들의 유의미한 반응과 정보가 담긴 댓글을 선별하는 것입니다. 아래의 평가 기준에 따라 각 댓글에 점수를 매기고, 총점이 6점 이상인 댓글만 '통과(Pass)'로 분류하세요.

[평가 기준]
1. 정보성 (1-3점): 댓글이 의미 있는 정보나 요약을 담고 있는가?
- 1점: 내용이 없거나 무의미한 텍스트 (예: "ㅋㅋ", "1빠", 스팸)
- 2점: 영상에 등장하는 단편적인 사실을 언급함
- 3점: 영상 내용을 훌륭하게 요약했거나, 영상과 관련된 유용한 추가 정보/인사이트를 제공함

2. 의견성 (1-3점): 시청자의 주관적인 의견, 감정, 반응이 잘 담겨 있는가?
- 1점: 의견이나 감정이 전혀 드러나지 않음 (단순 사실 나열)
- 2점: 평범하고 일상적인 반응 (예: "잘 봤습니다", "재밌네요")
- 3점: 영상에 대한 깊은 공감, 날카로운 비판, 또는 독창적인 시각이나 강렬한 주관적 감정이 드러남

3. 연관성 (1-3점): 제공된 Transcript의 내용과 직접적으로 연관되어 있는가?
- 1점: 영상의 내용과 전혀 무관함 (딴소리, 어그로)
- 2점: 영상의 전반적인 주제와는 관련이 있으나, 구체적인 내용은 아님
- 3점: Transcript에 등장하는 특정 발언, 장면, 맥락을 정확히 짚어서 이야기함

[평가 규칙]
- 총점 = 정보성 + 의견성 + 연관성
- 총점이 6점 이상(>= 6)인 경우에만 "is_pass"를 true로 설정하세요.
- 가장 중요한 규칙: 어떠한 인사말, 부가 설명, 마크다운 기호(예: ```json 등)도 절대 포함하지 마십시오. 오직 아래의 [출력 형식]과 정확히 일치하는 순수 JSON 객체만 반환해야 합니다.

[출력 형식]
{{
  "general_comments": [
    {{"id": "g1", "scores": {{"info": 1, "opinion": 2, "relevance": 1}}, "total_score": 4, "is_pass": false}}
  ],
  "timestamp_comments": [
    {{"id": "t1", "scores": {{"info": 2, "opinion": 3, "relevance": 3}}, "total_score": 8, "is_pass": true}}
  ]
}}

[입력 데이터]
## Transcript
\"\"\"
{transcript}
\"\"\"

## 일반 댓글
{general_comments}

## Timestamp 댓글
{timestamp_comments}
"""

def prepare_comments_for_prompt(comments: List[Dict[str, Any]], id_prefix: str) -> str:
    """Prepare comments into a JSON string to insert into the prompt."""
    formatted = []
    for idx, c in enumerate(comments):
        # Add an ID to each comment for tracking
        c_id = f"{id_prefix}{idx}"
        formatted.append({
            "id": c_id,
            "text": c.get('text', '').strip()
        })
    return json.dumps(formatted, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Filter comments using Gemini 2.5 Flash")
    parser.add_argument("--input", "-i", default="comment_results/combined_data.jsonl", help="Input JSONL file")
    parser.add_argument("--output", "-o", default="comment_results/filtered_comments.jsonl", help="Output JSONL file")
    parser.add_argument("--config", "-c", default="generation_configs/gemini.json", help="Path to Gemini config file")
    
    args = parser.parse_args()
    
    # Load Gemini config
    gemini_config = {}
    if os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            gemini_config = json.load(f)
    else:
        print(f"Warning: Config file {args.config} not found. Using defaults.")
        
    model_name = gemini_config.get("model_name", "gemini-2.5-flash")
    gen_config_params = gemini_config.get("generation_config", {"temperature": 0.1})
    gen_config_params["response_mime_type"] = "application/json"
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please export it: export GEMINI_API_KEY='your_api_key'")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)
        
    processed_urls = set()
    if os.path.exists(args.output):
        with open(args.output, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if 'video_url' in data:
                        processed_urls.add(data['video_url'])
                except:
                    pass

    with open(args.input, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print(f"Loaded {len(lines)} records from {args.input}")
    
    with open(args.output, 'a', encoding='utf-8') as f_out:
        for idx, line in enumerate(lines, 1):
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            video_url = data.get('video_url')
            
            if not data.get('success'):
                print(f"[{idx}/{len(lines)}] Skipping failed collection for {video_url}")
                continue
                
            if video_url in processed_urls:
                print(f"[{idx}/{len(lines)}] Skipping already processed video: {video_url}")
                continue
                
            print(f"[{idx}/{len(lines)}] Processing video: {video_url}")
            
            transcript_items = data.get('transcript', [])
            transcript_text = " ".join([item.get('text', '') for item in transcript_items])
            
            # Using 'regular_comments' as 'general_comments' based on standard schema
            regular_comments = data.get('regular_comments', [])
            timestamp_comments = data.get('timestamp_comments', [])
            
            # Prepare comment data strings
            general_comments_str = prepare_comments_for_prompt(regular_comments, "g")
            timestamp_comments_str = prepare_comments_for_prompt(timestamp_comments, "t")
            
            prompt = PROMPT_TEMPLATE.format(
                transcript=transcript_text,
                general_comments=general_comments_str,
                timestamp_comments=timestamp_comments_str
            )
            
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Use JSON schema to enforce the output format and ensure strict JSON response
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(**gen_config_params),
                    )
                    
                    response_text = response.text.strip()
                    
                    # Clean up potential markdown formatting just in case
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()
                    
                    try:
                        evaluation_result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        print(f"  ✗ Failed to parse JSON response from Gemini: {e}")
                        print(f"  Raw response: {response_text[:100]}...")
                        break # Break out of retry loop for parsing errors, not an API issue
                    
                    # Attach the evaluation result to the original data structure
                    result_data = {
                        'video_url': video_url,
                        'video_id': data.get('video_id'),
                        'title': data.get('title'),
                        'evaluation_result': evaluation_result
                    }
                    
                    f_out.write(json.dumps(result_data, ensure_ascii=False) + '\n')
                    f_out.flush()
                    
                    # Count passes
                    g_total = len(evaluation_result.get('general_comments', []))
                    t_total = len(evaluation_result.get('timestamp_comments', []))
                    g_pass = sum(1 for c in evaluation_result.get('general_comments', []) if c.get('is_pass'))
                    t_pass = sum(1 for c in evaluation_result.get('timestamp_comments', []) if c.get('is_pass'))
                    print(f"  ✓ Processed! Passed/Total: {g_pass}/{g_total} general, {t_pass}/{t_total} timestamp comments.")
                    
                    # Sleep briefly to avoid aggressive rate limiting
                    time.sleep(4.5)
                    break # Success, break out of retry loop
                    
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        retry_count += 1
                        wait_time = 15 * retry_count
                        print(f"  ⚠ Rate limit hit. Waiting {wait_time} seconds before retrying ({retry_count}/{max_retries})...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ✗ Error during evaluation: {e}")
                        break

if __name__ == "__main__":
    main()
