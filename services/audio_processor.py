from pydub import AudioSegment
import io
from services.audio_enhancement import audio_enhancement_service


class AudioProcessor:
    """오디오 파일 변환 서비스"""
    
    @staticmethod
    def convert_to_wav_linear16(audio_content: bytes, input_format: str = "m4a", enhance_audio: bool = True) -> bytes:
        """
        오디오를 WAV LINEAR16 16kHz mono로 변환 (Google STT 표준)
        음성 품질 개선 옵션 포함
        
        Args:
            audio_content: 입력 오디오 파일 바이트
            input_format: 입력 파일 형식 (m4a, mp3, wav 등)
            enhance_audio: 음성 품질 개선 적용 여부
            
        Returns:
            WAV LINEAR16 16kHz mono 바이트
        """
        try:
            # 🎤 음성 품질 개선 적용
            if enhance_audio:
                print("🎤 음성 품질 개선 적용 중...")
                enhanced_content = audio_enhancement_service.enhance_audio(
                    audio_content, 
                    input_format,
                    enhancement_options={
                        'noise_reduction': True,    # 노이즈 제거
                        'amplification': True,      # 음성 증폭
                        'normalization': True,     # 정규화
                        'auto_correction': True    # 자동 보정
                    }
                )
                audio_content = enhanced_content
                print("✅ 음성 품질 개선 완료")
            
            # 입력 오디오 로드
            audio = AudioSegment.from_file(
                io.BytesIO(audio_content), 
                format=input_format
            )
            
            # 🎯 Google STT 표준 형식으로 변환
            # - 샘플레이트: 16kHz
            # - 채널: 모노 (1채널)
            # - 인코딩: LINEAR16 (pcm_s16le)
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # WAV LINEAR16으로 내보내기
            output = io.BytesIO()
            audio.export(
                output, 
                format="wav",
                codec="pcm_s16le",  # LINEAR16
                parameters=["-ac", "1", "-ar", "16000"]
            )
            output.seek(0)
            
            return output.read()
        
        except Exception as e:
            print(f"Audio conversion error: {e}")
            raise Exception(f"오디오 변환 실패: {str(e)}")
    
    @staticmethod
    def convert_to_wav_linear16_from_file(file_path: str) -> bytes:
        """
        파일 경로에서 직접 WAV LINEAR16 16kHz mono로 변환
        (AAC, MP3 등 복잡한 형식 처리에 최적)
        
        Args:
            file_path: 입력 오디오 파일 경로
            
        Returns:
            WAV LINEAR16 16kHz mono 바이트
        """
        try:
            # 파일에서 직접 로드 (AAC moov atom 문제 해결)
            audio = AudioSegment.from_file(file_path)
            
            # 🎯 Google STT 표준 형식으로 변환
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # WAV LINEAR16으로 내보내기
            output = io.BytesIO()
            audio.export(
                output, 
                format="wav",
                codec="pcm_s16le",
                parameters=["-ac", "1", "-ar", "16000"]
            )
            output.seek(0)
            
            return output.read()
        
        except Exception as e:
            print(f"Audio conversion from file error: {e}")
            raise Exception(f"파일 변환 실패: {str(e)}")
    
    @staticmethod
    def compress_audio_opus(audio_content: bytes, input_format: str = "m4a", target_bitrate: str = "24k") -> bytes:
        """
        오디오를 Opus 코덱으로 압축 (최고 압축률)
        
        Args:
            audio_content: 입력 오디오 파일 바이트
            input_format: 입력 파일 형식
            target_bitrate: 목표 비트레이트 (기본 24kbps - Opus 음성 최적)
            
        Returns:
            압축된 WebM/Opus 바이트
        """
        try:
            print(f"🔍 [Opus 압축] 입력: {input_format}, {len(audio_content) / 1024 / 1024:.1f}MB")
            
            # 입력 오디오 로드
            audio = AudioSegment.from_file(
                io.BytesIO(audio_content), 
                format=input_format
            )
            
            # 원본 정보
            original_duration = len(audio) / 1000
            print(f"🎵 [Opus 압축] 원본: {original_duration:.1f}초, {audio.channels}채널, {audio.frame_rate}Hz")
            
            # 음성 최적화: 16kHz mono
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # Opus 코덱으로 압축 (WebM 컨테이너)
            output = io.BytesIO()
            audio.export(
                output,
                format="webm",
                codec="libopus",
                bitrate=target_bitrate,
                parameters=["-ac", "1", "-ar", "16000", "-application", "voip"]
            )
            output.seek(0)
            
            compressed = output.read()
            
            # 압축 비율
            original_size = len(audio_content) / (1024 * 1024)
            compressed_size = len(compressed) / (1024 * 1024)
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            print(f"📦 [Opus 압축] 완료: {original_size:.1f}MB → {compressed_size:.1f}MB (절약: {ratio:.1f}%)")
            
            return compressed
            
        except Exception as e:
            print(f"❌ [Opus 압축] 실패: {e}, MP3로 폴백")
            # Opus 실패 시 MP3로 폴백
            return AudioProcessor.compress_audio(audio_content, input_format, "32k")
    
    @staticmethod
    def compress_audio(audio_content: bytes, input_format: str = "m4a", target_bitrate: str = "32k") -> bytes:
        """
        오디오를 압축하여 파일 크기 감소 (업로드 최적화)
        
        Args:
            audio_content: 입력 오디오 파일 바이트
            input_format: 입력 파일 형식
            target_bitrate: 목표 비트레이트 (기본 32kbps - 음성 최적화)
            
        Returns:
            압축된 MP3 바이트
        """
        try:
            print(f"🔍 [압축] 입력 형식: {input_format}, 입력 크기: {len(audio_content) / 1024 / 1024:.1f}MB")
            
            # 입력 오디오 로드
            audio = AudioSegment.from_file(
                io.BytesIO(audio_content), 
                format=input_format
            )
            
            # 원본 오디오 정보
            original_duration = len(audio) / 1000  # 초
            original_channels = audio.channels
            original_sample_rate = audio.frame_rate
            
            print(f"🎵 [압축] 원본: {original_duration:.1f}초, {original_channels}채널, {original_sample_rate}Hz")
            
            # 음성 최적화 설정
            # - 샘플레이트: 16kHz (음성 인식에 충분)
            # - 채널: 모노 (1채널)
            # - 비트레이트: 32kbps (음성 품질 유지하면서 크기 최소화)
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # MP3로 압축 내보내기
            output = io.BytesIO()
            audio.export(
                output, 
                format="mp3",
                bitrate=target_bitrate,
                parameters=["-ac", "1", "-ar", "16000"]
            )
            output.seek(0)
            
            compressed = output.read()
            
            # 압축 비율 로깅
            original_size = len(audio_content) / (1024 * 1024)  # MB
            compressed_size = len(compressed) / (1024 * 1024)  # MB
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            print(f"📦 압축 완료: {original_size:.1f}MB → {compressed_size:.1f}MB (절약: {ratio:.1f}%)")
            print(f"🎵 [압축] 압축 후: {original_duration:.1f}초, 1채널, 16000Hz, 32kbps MP3")
            
            # 압축된 파일이 비정상적으로 작거나 크면 경고
            if compressed_size < 0.1:
                print(f"⚠️  [압축] 경고: 압축 파일이 너무 작음 ({compressed_size:.1f}MB)")
            elif compressed_size > original_size:
                print(f"⚠️  [압축] 경고: 압축 파일이 원본보다 큼 - 원본 사용")
                return audio_content
            
            return compressed
        
        except Exception as e:
            print(f"❌ 압축 실패: {e}")
            import traceback
            traceback.print_exc()
            # 압축 실패 시 원본 반환
            print(f"⚠️  [압축] 실패로 원본 반환")
            return audio_content
    
    @staticmethod
    def convert_m4a_to_ogg(m4a_content: bytes) -> bytes:
        """
        M4A를 OGG Opus로 변환 (레거시 - 호환성 유지)
        
        Args:
            m4a_content: M4A 파일 바이트
            
        Returns:
            OGG Opus 파일 바이트
        """
        try:
            # M4A 로드
            audio = AudioSegment.from_file(
                io.BytesIO(m4a_content), 
                format="m4a"
            )
            
            # 16kHz 모노로 변환 (Google STT 최적)
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # OGG Opus로 내보내기
            output = io.BytesIO()
            audio.export(output, format="ogg", codec="libopus", bitrate="16k")
            output.seek(0)
            
            return output.read()
        
        except Exception as e:
            print(f"Audio conversion error: {e}")
            raise Exception(f"오디오 변환 실패: {str(e)}")
    
    @staticmethod
    def get_audio_duration(audio_content: bytes, format: str = "m4a") -> int:
        """
        오디오 파일의 길이를 밀리초 단위로 반환
        
        Args:
            audio_content: 오디오 파일 바이트
            format: 파일 형식
            
        Returns:
            밀리초 단위 길이
        """
        try:
            audio = AudioSegment.from_file(
                io.BytesIO(audio_content),
                format=format
            )
            return len(audio)
        except Exception as e:
            print(f"Duration calculation error: {e}")
            return 0

