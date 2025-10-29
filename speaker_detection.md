# 🎯 Google STT 기반 화자 수 자동 감지 (FastAPI 환경)

## 🧩 목적

Google Speech-to-Text API를 사용하여 **오디오 내 화자 수를 자동 추정**하고, `speaker_count` 및 `speaker_ids`를 반환하도록 구성한다.

---

## 📂 구현 파일

- **`backend/services/google_stt.py`** - Google STT 서비스
- **`backend/routers/stt.py`** - STT API 엔드포인트

---

## 💡 핵심 변경점 요약

| 항목        | 기존                               | 개선 후                                              |
| --------- | -------------------------------- | ------------------------------------------------- |
| 화자 설정     | `diarization_speaker_count=2` 고정 | `min_speaker_count`, `max_speaker_count` 기반 자동 추정 |
| 반환값       | 텍스트, 세그먼트                        | `speaker_count`, `speaker_ids` 추가                 |
| 필터링       | 없음                               | 중복 단어 및 세그먼트 제거                                   |
| 화자 구분 정확도 | 중간                               | Google STT diarization + 세그먼트 중복 제거              |

---

## ⚙️ 핵심 코드

### **1. 화자 분리 설정**

```python
# 🎯 화자 분리 설정 (자동 감지)
diarization_config = speech.SpeakerDiarizationConfig(
    enable_speaker_diarization=True,
    min_speaker_count=1,  # 최소 1명
    max_speaker_count=6,  # 최대 6명
)

config = speech.RecognitionConfig(
    encoding=actual_encoding,
    sample_rate_hertz=sample_rate,
    language_code=language_codes[0],
    model="latest_long",
    enable_automatic_punctuation=True,
    enable_word_time_offsets=True,
    enable_word_confidence=True,
    diarization_config=diarization_config,  # 👈 화자 분리 설정
)
```

### **2. 화자 정보 추출**

```python
# 🎯 화자 수 및 ID 추출
speaker_set = sorted({w["speaker"] for w in all_words if w["speaker"] > 0})
speaker_count = len(speaker_set)

print(f"🎤 최종 화자 정보: {speaker_count}명 (IDs: {speaker_set})")
```

### **3. 중복 제거**

#### **중복 단어 제거**
```python
# 동일한 시간+단어는 하나만 유지
unique_words = {}
for word in all_words:
    key = f"{word['start']:.2f}:{word['end']:.2f}:{word['word']}"
    if key not in unique_words:
        unique_words[key] = word
    else:
        # 화자 번호가 더 낮은 것으로 유지
        if word['speaker'] < unique_words[key]['speaker']:
            unique_words[key] = word

all_words = sorted(unique_words.values(), key=lambda w: w['start'])
```

#### **중복 세그먼트 제거**
```python
# 동일한 텍스트는 하나만 유지
unique_segments = []
seen_texts = set()

for seg in segments:
    if seg["text"] not in seen_texts:
        unique_segments.append(seg)
        seen_texts.add(seg["text"])
```

---

## 🚀 반환 값 예시

```json
{
  "text": "안녕하세요 오늘 회의 시작하겠습니다 네 반갑습니다.",
  "language": "ko-KR",
  "confidence": 0.95,
  "segments": [
    {
      "speaker": 1,
      "start": 0.2,
      "end": 3.1,
      "text": "안녕하세요 오늘 회의 시작하겠습니다",
      "confidence": 0.94
    },
    {
      "speaker": 2,
      "start": 3.2,
      "end": 5.0,
      "text": "네 반갑습니다",
      "confidence": 0.96
    }
  ],
  "speaker_count": 2,
  "speaker_ids": [1, 2]
}
```

---

## 🔍 동작 방식

### **화자 감지 프로세스**

1. **Google STT 호출**
   ```
   min_speaker_count=1, max_speaker_count=6
   ↓
   Google이 자동으로 화자 수 감지
   ```

2. **단어별 화자 정보 수집**
   ```
   word_info.speaker_tag = 1, 2, 3...
   ↓
   각 단어에 화자 번호 할당
   ```

3. **중복 제거**
   ```
   동일한 시간+단어 → 하나만 유지
   ↓
   화자 번호가 낮은 것 우선
   ```

4. **세그먼트 조립**
   ```
   화자 변경 또는 1초 이상 침묵 시 세그먼트 분리
   ↓
   중복 텍스트 제거
   ```

5. **화자 정보 추출**
   ```
   speaker_set = {1, 2, 3...}
   speaker_count = len(speaker_set)
   ```

---

## ✅ 사용 시 주의사항

### **1. 오디오 형식**
- ✅ **WAV LINEAR16 16kHz Mono** 권장
- ⚠️ 다른 형식은 정확도 저하 가능

### **2. 녹음 길이**
- ✅ **60초 이하**: 화자별 재전사 가능
- ⚠️ **60초 이상**: GCS URI 필요 (청크 기반 유지)

### **3. 화자 수**
- ✅ **1~6명**: 자동 감지
- ⚠️ **6명 이상**: `max_speaker_count` 증가 (정확도 저하)

### **4. 음질**
- ✅ **각 화자가 5초 이상** 발화해야 정확
- ⚠️ **배경 소음 최소화** 필요

---

## 🧪 테스트 시나리오

### **시나리오 1: 2명 대화**
```
화자 A: "안녕하세요, OAuth2를 사용합니다." (5초)
화자 B: "네, FastAPI로 개발합니다." (5초)

기대 결과:
speaker_count: 2
speaker_ids: [1, 2]
segments: 2개 (중복 없음)
```

### **시나리오 2: 3명 회의**
```
화자 A: "프로젝트 시작하겠습니다." (3초)
화자 B: "네, 준비되었습니다." (3초)
화자 C: "좋습니다." (2초)

기대 결과:
speaker_count: 3
speaker_ids: [1, 2, 3]
segments: 3개
```

---

## 📊 백엔드 로그 예시

```
🔍 Google STT response.results 개수: 1
🔍 전체 단어 수: 200개
🎯 중복 제거 후 단어 수: 100개
🔍 첫 20개 word 샘플:
   word='▁안녕하세요' (speaker=1, 0.2s-0.5s)
   word='▁오늘' (speaker=1, 0.5s-0.8s)
   ...
   word='▁네' (speaker=2, 5.0s-5.2s)
   ...
🎤 감지된 화자: [1, 2] (총 2명)

🎯 _assemble_segments 결과: 3개 세그먼트 생성 (중복 제거 완료)
   화자별 세그먼트 수: {1: 2, 2: 1}
   세그먼트 0: speaker=1, 0.2s-3.1s, text='안녕하세요 오늘 회의 시작하겠습니다'
   세그먼트 1: speaker=2, 3.2s-5.0s, text='네 반갑습니다'
   세그먼트 2: speaker=1, 5.1s-8.0s, text='좋습니다'

🎤 최종 화자 정보: 2명 (IDs: [1, 2])
```

---

## 🔧 주요 개선 사항

### **Before**
```python
enable_speaker_diarization=True,
diarization_speaker_count=2,  # 고정
```

### **After**
```python
diarization_config = speech.SpeakerDiarizationConfig(
    enable_speaker_diarization=True,
    min_speaker_count=1,  # 자동 감지
    max_speaker_count=6,
)
```

---

## 📝 API 응답 구조

```python
{
    "text": str,              # 전체 텍스트
    "language": str,          # 언어 코드 (예: "ko-KR")
    "confidence": float,      # 평균 신뢰도
    "segments": [             # 화자별 세그먼트
        {
            "speaker": int,       # 화자 번호 (1, 2, 3...)
            "start": float,       # 시작 시간 (초)
            "end": float,         # 종료 시간 (초)
            "text": str,          # 세그먼트 텍스트
            "confidence": float   # 신뢰도
        }
    ],
    "speaker_count": int,     # 🎯 감지된 화자 수
    "speaker_ids": List[int]  # 🎯 화자 ID 목록 (예: [1, 2])
}
```

---

## 🎉 정리

- ✅ **화자 자동 감지**: 1~6명 자동 감지
- ✅ **중복 제거**: 단어 및 세그먼트 중복 완전 제거
- ✅ **화자 정보**: `speaker_count`, `speaker_ids` 반환
- ✅ **60초 제한**: GCS URI 필요 시 청크 기반 유지

---

**작성자**: SummarIQ 개발팀  
**날짜**: 2025-10-10  
**버전**: 1.0

