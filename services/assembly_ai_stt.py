from typing import Dict, List
import os
import requests
import json
import time
import logging

# 로깅 설정
logger = logging.getLogger(__name__)


class AssemblyAISTTService:
    """Assembly AI Speech-to-Text API 서비스"""
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: Assembly AI API 키
        """
        self.api_key = api_key or os.getenv("ASSEMBLY_AI_API_KEY")
        if not self.api_key:
            raise Exception("ASSEMBLY_AI_API_KEY 환경변수가 설정되어 있지 않습니다.")
        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
        # 마스킹된 키 로그
        try:
            masked = self.api_key[:6] + "****" + self.api_key[-4:]
            print(f"🔑 AssemblyAI API 키 사용: {masked}")
        except Exception:
            pass
    
    def _validate_audio_content(self, audio_content: bytes) -> bool:
        """오디오 파일 내용 검증"""
        try:
            # 파일 크기 검증 (최소 1KB)
            if len(audio_content) < 1024:
                logger.warning("오디오 파일이 너무 작습니다.")
                return False
            
            # 기본적인 오디오 헤더 검증 (M4A, MP3, WAV 등)
            audio_signatures = [
                b'ftyp',  # M4A/MP4
                b'ID3',   # MP3
                b'RIFF',  # WAV
                b'OggS',  # OGG
            ]
            
            has_valid_signature = any(sig in audio_content[:20] for sig in audio_signatures)
            if not has_valid_signature:
                logger.warning("유효하지 않은 오디오 파일 형식입니다.")
                return False
                
            logger.info(f"✅ 오디오 파일 검증 통과: {len(audio_content)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"오디오 파일 검증 실패: {e}")
            return False
    
    def _upload_audio_file(self, audio_content: bytes) -> str:
        """오디오 파일을 Assembly AI에 업로드하고 업로드 URL 반환
        주의: AssemblyAI는 multipart/form-data가 아닌 RAW 바이트 업로드를 권장
        """
        # 오디오 파일 검증
        if not self._validate_audio_content(audio_content):
            raise Exception("오디오 파일 검증에 실패했습니다. 녹음된 파일을 확인해주세요.")
        
        upload_url = f"{self.base_url}/upload"
        
        # 파일 크기에 따라 타임아웃 동적 조정 (최소 10분, 최대 30분)
        file_size_mb = len(audio_content) / (1024 * 1024)
        # 1MB당 10초 + 기본 600초 (10분)
        timeout_seconds = max(600, min(1800, int(file_size_mb * 10 + 600)))
        
        print(f"📊 업로드 정보: 파일 크기 {file_size_mb:.1f}MB, 타임아웃 {timeout_seconds}초")
        
        # RAW 바이트로 전송 (application/octet-stream)
        response = requests.post(
            upload_url,
            data=audio_content,
            headers={
                "authorization": self.api_key,
                "content-type": "application/octet-stream"
            },
            timeout=timeout_seconds
        )
        response.raise_for_status()
        url = response.json().get("upload_url")
        if not url:
            raise Exception("Assembly AI 업로드 URL 생성 실패")
        
        print(f"✅ 업로드 완료: {url[:50]}...")
        return url
    
    def _submit_transcription(
        self, 
        audio_url: str, 
        speaker_labels: bool = True,
        speech_model: str = "best",
        mode: str = "auto",
        speakers_expected: int = None
    ) -> str:
        """
        Assembly AI에 전사 작업 제출
        
        Args:
            audio_url: 오디오 URL
            speaker_labels: 화자 구분 여부
            speech_model: "best" (가장 정확) 또는 "nano" (가장 빠름)
            mode: "ko" (한국어 전용) 또는 "auto" (다국어 자동 감지, 기본값)
            speakers_expected: 예상 화자 수 (선택)
        """
        transcript_url = f"{self.base_url}/transcript"
        
        # 모드에 따라 언어 설정 분기
        if mode == "ko":
            # 한국어 우선 모드 (한국어 회의 전용)
            data = {
                "audio_url": audio_url,
                "speaker_labels": speaker_labels,
                "language_code": "ko",         # 한국어 강제
                "punctuate": True,
                "format_text": True,
                "speech_model": speech_model
            }
            print(f"📝 AssemblyAI 요청 (한국어 전용 모드, speech_model={speech_model})")
        elif mode == "auto":
            # 다국어 자동 감지 모드 (혼용 회의) - 언어 감지 비활성화로 안정성 향상
            data = {
                "audio_url": audio_url,
                "speaker_labels": speaker_labels,
                "language_detection": False,   # 언어 감지 비활성화 (음성이 없을 때 오류 방지)
                "language_code": "ko",         # 한국어 기본값 설정
                "punctuate": True,
                "format_text": True,
                "speech_model": speech_model
            }
            print(f"📝 AssemblyAI 요청 (한국어 기본 모드, speech_model={speech_model})")
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'ko' or 'auto'")
        
        # 예상 화자 수 설정 (정확도 향상)
        if speakers_expected:
            data["speakers_expected"] = speakers_expected
            print(f"🎤 예상 화자 수: {speakers_expected}명")
        
        print(f"📊 요청 데이터: {data}")
        
        response = requests.post(transcript_url, json=data, headers=self.headers)
        
        # 에러 응답 상세 로깅
        if not response.ok:
            try:
                error_detail = response.json()
                print(f"❌ AssemblyAI 에러 응답: {error_detail}")
            except:
                print(f"❌ AssemblyAI 에러 (JSON 파싱 실패): {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ AssemblyAI 전사 작업 제출 완료: {result.get('id')}")
        
        return result["id"]
    
    def _poll_transcription(self, transcript_id: str, max_wait: int = 300) -> Dict:
        """전사 완료까지 폴링"""
        poll_url = f"{self.base_url}/transcript/{transcript_id}"
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = requests.get(poll_url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            status = result["status"]
            
            if status == "completed":
                return result
            elif status == "error":
                error_msg = result.get('error', 'Unknown error')
                # 구체적인 오류 메시지 제공
                if "no spoken audio" in str(error_msg).lower():
                    raise Exception("녹음된 파일에 음성이 감지되지 않습니다. 마이크를 확인하고 다시 녹음해주세요.")
                elif "language_detection" in str(error_msg).lower():
                    raise Exception("음성 언어 감지에 실패했습니다. 한국어로 다시 녹음해주세요.")
                else:
                    raise Exception(f"Assembly AI 전사 실패: {error_msg}")
            
            print(f"🔄 Assembly AI 전사 진행 중... ({status})")
            time.sleep(3)
        
        raise Exception("Assembly AI transcription timeout")
    
    def _parse_assembly_result(self, result: Dict) -> Dict:
        """Assembly AI 결과를 기존 형식으로 변환"""
        text = result.get("text", "")
        confidence = result.get("confidence", 0.0)
        
        # 감지된 언어 코드 가져오기 (AssemblyAI는 자동으로 언어 감지)
        detected_language = result.get("language_code", "unknown")
        print(f"🌐 감지된 언어: {detected_language}")
        
        # 화자별 세그먼트 파싱
        segments = []
        speaker_count = 0
        speaker_ids = set()
        
        utterances = result.get("utterances", [])
        if utterances:
            print(f"🎤 Assembly AI 화자 구분 결과: {len(utterances)}개 발화")
            
            for i, utterance in enumerate(utterances):
                speaker = utterance.get("speaker", f"Speaker_{i}")
                speaker_ids.add(speaker)
                
                # 화자 이름을 더 명확하게 (Speaker_A, Speaker_B 등)
                speaker_label = f"Speaker_{speaker}" if isinstance(speaker, str) and speaker.startswith("Speaker_") else f"Speaker_{speaker}"
                
                segments.append({
                    "speaker": speaker_label,
                    "text": utterance.get("text", ""),
                    "start": utterance.get("start", 0) / 1000,  # ms to seconds
                    "end": utterance.get("end", 0) / 1000,
                    "confidence": utterance.get("confidence", confidence)
                })
            
            speaker_count = len(speaker_ids)
            print(f"🎤 감지된 화자: {speaker_count}명 (IDs: {list(speaker_ids)})")
        else:
            print(f"⚠️  Assembly AI 화자 구분 실패 - utterances 없음")
            # 화자 구분 실패 시 전체 텍스트를 하나의 세그먼트로
            segments.append({
                "speaker": "Speaker_A",
                "text": text,
                "start": 0,
                "end": len(text) * 0.1,  # 추정 길이
                "confidence": confidence
            })
            speaker_count = 1
        
        # 다국어 지원을 위해 언어 코드를 적절한 형식으로 변환
        # AssemblyAI: en, ko 등 → 우리 시스템: ko-KR, en-US 등
        language_map = {
            "ko": "ko-KR",
            "en": "en-US",
            "ja": "ja-JP",
            "zh": "zh-CN",
            "es": "es-ES",
            "fr": "fr-FR",
            "de": "de-DE"
        }
        formatted_language = language_map.get(detected_language, detected_language)
        
        return {
            "text": text,
            "language": formatted_language,
            "confidence": confidence,
            "segments": segments,
            "speaker_count": speaker_count,
            "speaker_ids": list(speaker_ids) if speaker_ids else ["Speaker_A"]
        }
    
    async def transcribe_audio(
        self, 
        audio_content: bytes,
        language_codes: List[str] = ["ko-KR", "en-US"],
        encoding: str = "LINEAR16",
        sample_rate: int = 16000,
        use_wav: bool = True,
        min_speakers: int = 3,
        max_speakers: int = 5,
        speech_model: str = "best",
        mode: str = "auto",
        speakers_expected: int = None
    ) -> Dict[str, any]:
        """
        Assembly AI로 오디오를 텍스트로 변환
        
        Args:
            audio_content: 오디오 파일 바이트
            speech_model: "best" (가장 정확, 기본값) 또는 "nano" (가장 빠름)
            mode: "ko" (한국어 전용) 또는 "auto" (다국어 자동 감지, 기본값)
            speakers_expected: 예상 화자 수 (정확도 향상)
        
        Returns:
            {
                "text": "변환된 텍스트",
                "language": "ko-KR",
                "confidence": 0.95,
                "segments": [...]  # 화자 기반 세그먼트
            }
        """
        try:
            print(f"🎤 Assembly AI STT 시작...")
            
            # 1. 오디오 파일 업로드
            print(f"📤 오디오 파일 업로드 중...")
            audio_url = self._upload_audio_file(audio_content)
            print(f"✅ 업로드 완료: {audio_url[:50]}...")
            
            # 2. 전사 작업 제출
            print(f"📝 전사 작업 제출 중...")
            transcript_id = self._submit_transcription(
                audio_url, 
                speaker_labels=True,
                speech_model=speech_model,
                mode=mode,
                speakers_expected=speakers_expected
            )
            print(f"✅ 전사 ID: {transcript_id}")
            
            # 3. 완료까지 폴링
            print(f"⏳ 전사 완료 대기 중...")
            result = self._poll_transcription(transcript_id)
            print(f"✅ 전사 완료!")
            
            # 4. 결과 파싱
            parsed_result = self._parse_assembly_result(result)
            
            # 📊 사용량 로깅
            duration_sec = len(audio_content) / (16000 * 2)  # 추정
            estimated_cost_usd = (duration_sec / 60) * 0.00065  # Assembly AI: $0.00065/min
            print(f"📊 Assembly AI 완료: {duration_sec:.1f}초 → ${estimated_cost_usd:.4f} (예상 비용)")
            
            return parsed_result
            
        except Exception as e:
            print(f"❌ Assembly AI STT 실패: {e}")
            raise Exception(f"Assembly AI Speech-to-Text 변환 실패: {str(e)}")
