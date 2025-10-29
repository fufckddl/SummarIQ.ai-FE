# 🎯 Google STT 화자 구분 실패 해결 가이드

## 📋 문제 상황
- **증상**: Google STT가 모든 단어를 `speaker_tag=0`으로 반환
- **원인**: 
  1. 중간 result 병합 시 speaker=0으로 덮어쓰기
  2. 클로바더빙 AI 음성의 동질성

---

## ✅ 적용된 해결책

### 1️⃣ **코드 패치: 마지막 result만 사용**

#### **변경 전 (backend/services/google_stt.py)**
```python
# ❌ 모든 result를 순회하면서 병합
for idx, result in enumerate(response.results):
    alternative = result.alternatives[0]
    if hasattr(alternative, 'words'):
        for word_info in alternative.words:
            all_words.append({...})
```

#### **변경 후**
```python
# ✅ 마지막 result만 사용 (diarization 태그가 안정화된 result)
final_result = response.results[-1]
final_alternative = final_result.alternatives[0]

if hasattr(final_alternative, 'words'):
    for word_info in final_alternative.words:
        speaker = getattr(word_info, 'speaker_tag', 0) or 0
        all_words.append({
            "word": word_info.word,
            "start": word_info.start_time.total_seconds(),
            "end": word_info.end_time.total_seconds(),
            "confidence": getattr(word_info, 'confidence', 0.0),
            "speaker": speaker,
        })
```

### 2️⃣ **중복 병합 로직: speaker=0 배제**

#### **변경 전**
```python
# ❌ 화자 번호가 낮은 것 우선 (speaker=0 우선)
if word['speaker'] < unique_words[key]['speaker']:
    unique_words[key] = word
```

#### **변경 후**
```python
# ✅ speaker=0을 버리고 비-0 우선 채택
existing = unique_words[key]
if existing['speaker'] == 0 and word['speaker'] > 0:
    unique_words[key] = word
    print(f"   🔄 speaker 교체: {key} → speaker={word['speaker']}")
elif existing['speaker'] > 0 and word['speaker'] == 0:
    # 기존 비-0 유지
    pass
```

### 3️⃣ **STT 설정 최적화**

```python
# 🎯 화자 2명으로 고정
min_speakers: int = 2,
max_speakers: int = 2,
model: str = "latest_long",  # A/B 테스트: "latest_long" vs "video"

diarization_config = speech.SpeakerDiarizationConfig(
    enable_speaker_diarization=True,
    min_speaker_count=2,
    max_speaker_count=2,
)

config = speech.RecognitionConfig(
    encoding=encoding,
    sample_rate_hertz=16000,
    language_code="ko-KR",
    model=model,  # ✅ A/B 테스트 가능
    enable_automatic_punctuation=True,
    enable_word_time_offsets=True,
    enable_word_confidence=True,
    diarization_config=diarization_config,
)
```

### 4️⃣ **프론트엔드: 수동 화자 지정 UI 제거**

- ❌ 제거: `editingSpeaker` 상태
- ❌ 제거: `handleSpeakerChange` 함수
- ❌ 제거: 화자 선택 버튼 UI
- ✅ 유지: 화자별 색상 구분 (파란색/분홍색)

---

## 🧪 테스트 방법

### **1. 모델 A/B 테스트**

#### **latest_long 모델 (기본)**
```python
# backend/services/google_stt.py
model="latest_long"
```

#### **video 모델 (대화형 최적화)**
```python
# backend/services/google_stt.py
model="video"
```

**동일 파일로 두 모델을 테스트하여 비교**

### **2. 클로바더빙 최적화 녹음**

#### **발화 패턴**
```
화자 A: "안녕하세요, 저는 백엔드 개발자입니다"
[4-6초 침묵] 👈 중요!
화자 B: "네, 반갑습니다. 저는 프론트엔드 개발자입니다"
[4-6초 침묵] 👈 중요!
```

#### **음향 차별화**
- **턴 길이**: 2초 → 4-6초로 확대
- **RMS 레벨**: 화자별 ±2 dB 차등
- **EQ/리버브**: 화자별 다르게 적용

### **3. 스테레오 분리 (최선책)**

```python
# 화자 A → Left 채널
# 화자 B → Right 채널

config.audio_channel_count = 2
config.enable_separate_recognition_per_channel = True
```

---

## 📊 디버깅 로그 확인

### **정상 케이스**
```
✅ 마지막 result 사용: 565개 단어
🔍 전체 단어 수: 565개
🎯 중복 제거 후 단어 수: 565개
📊 화자별 단어 분포: {1: 280, 2: 285}
🎤 감지된 화자: [1, 2] (총 2명)
```

### **실패 케이스**
```
✅ 마지막 result 사용: 565개 단어
🔍 전체 단어 수: 565개
🎯 중복 제거 후 단어 수: 565개
📊 화자별 단어 분포: {0: 565}
🎤 감지된 화자: [0] (총 1명)
⚠️ 화자 구분 실패 (speaker=0만 감지됨)
```

---

## 🔧 하이브리드 파이프라인 (백업)

### **구조**
```
[Audio]
  → Google STT (전사 + word time)
  → Embedding (Resemblyzer/pyannote)
  → Clustering (n=2)
  → Align (단어 타임스탬프 ↔ 세그먼트 라벨)
  → {segments, speaker_count, speaker_ids}
```

### **구현 예시**
```python
@router.post("/stt")
async def stt_endpoint(file: UploadFile):
    audio = await file.read()
    svc = GoogleSTTService()
    out = await svc.transcribe_audio(audio)

    # diarization 실패 감지 → 백업 파이프라인 호출
    if out.get("speaker_count", 0) < 2:
        out = await fallback_diarization_with_embeddings(audio, out)

    return out
```

---

## 🎯 검증 시나리오

### **데이터셋**
1. 실제 사람 음성 (2명 대화)
2. 합성 음성 혼합 (사람 + AI)
3. 순수 합성 음성 (클로바더빙 2명)

### **메트릭**
- `speaker_count`: 2명 감지 성공 여부
- `speaker_tag==0` 비율: ≤ 1%
- DER (Diarization Error Rate): 잘못 할당된 단어 비율

### **합격 기준**
- ✅ 실제 사람 음성: `speaker_count=2`, DER < 10%
- ✅ 합성 음성: `speaker_count=2`, DER < 20%

---

## 📝 로그 확인 포인트

1. `len(response.results)`: result 개수
2. `마지막 result의 len(words)`: 단어 개수
3. `unique key 충돌 수`: 중복 병합 횟수
4. `🔄 speaker 교체`: 0→비-0 교체 로그
5. `📊 화자별 단어 분포`: {1: 280, 2: 285}
6. `segment 수`: 화자별 세그먼트 개수

---

## 🚀 운영 체크리스트

- [x] GCS 권한 설정 완료
- [x] 마지막 result만 사용하도록 코드 수정
- [x] speaker=0 배제 로직 추가
- [x] 화자 2명 고정 설정
- [x] 모델 A/B 테스트 준비 (latest_long vs video)
- [ ] 클로바더빙 최적화 녹음 테스트
- [ ] 스테레오 분리 녹음 테스트 (선택)
- [ ] 하이브리드 파이프라인 구현 (백업)

---

## 💡 결론

1. **코드 처리 오류**와 **합성음 동질성**이 결합된 문제
2. **마지막 result만 사용** + **speaker=0 배제** 로직으로 1차 해결
3. 클로바더빙은 **발화 패턴 최적화** 또는 **스테레오 분리**로 안정화
4. 실패 시 **임베딩 백업 파이프라인**으로 대응

---

## 📚 참고 자료

- [Google STT Speaker Diarization](https://cloud.google.com/speech-to-text/docs/speaker-diarization)
- [Google STT Best Practices](https://cloud.google.com/speech-to-text/docs/best-practices)
- [Resemblyzer (화자 임베딩)](https://github.com/resemble-ai/Resemblyzer)
- [pyannote.audio (화자 분리)](https://github.com/pyannote/pyannote-audio)

