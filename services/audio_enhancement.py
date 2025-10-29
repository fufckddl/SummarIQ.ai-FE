"""
🎤 고급 오디오 품질 개선 서비스
노이즈 제거, 음성 증폭, 정규화, 자동 보정 기능
"""

import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
from scipy import signal
from scipy.signal import butter, filtfilt
import io
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class AudioEnhancementService:
    """오디오 품질 개선 서비스"""
    
    def __init__(self):
        self.sample_rate = 16000  # Google STT 표준 샘플레이트
        self.target_db = -20.0    # 목표 음량 (dB)
        self.max_amplification = 20.0  # 최대 증폭 (dB)
    
    def enhance_audio(
        self, 
        audio_content: bytes, 
        input_format: str = "m4a",
        enhancement_options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        종합적인 오디오 품질 개선
        
        Args:
            audio_content: 입력 오디오 파일 바이트
            input_format: 입력 파일 형식
            enhancement_options: 개선 옵션
            
        Returns:
            개선된 오디오 바이트
        """
        try:
            # 기본 옵션 설정
            options = enhancement_options or {}
            enable_noise_reduction = options.get('noise_reduction', True)
            enable_amplification = options.get('amplification', True)
            enable_normalization = options.get('normalization', True)
            enable_auto_correction = options.get('auto_correction', True)
            
            logger.info(f"🎤 오디오 개선 시작 - 노이즈제거:{enable_noise_reduction}, 증폭:{enable_amplification}, 정규화:{enable_normalization}, 자동보정:{enable_auto_correction}")
            
            # 1. 오디오 로드
            audio_data, sr = self._load_audio(audio_content, input_format)
            logger.info(f"📊 원본 오디오: {len(audio_data)} samples, {sr}Hz")
            
            # 2. 노이즈 제거
            if enable_noise_reduction:
                audio_data = self._reduce_noise(audio_data, sr)
                logger.info("🔇 노이즈 제거 완료")
            
            # 3. 음성 증폭
            if enable_amplification:
                audio_data = self._amplify_voice(audio_data, sr)
                logger.info("📢 음성 증폭 완료")
            
            # 4. 음성 정규화
            if enable_normalization:
                audio_data = self._normalize_audio(audio_data)
                logger.info("🎵 음성 정규화 완료")
            
            # 5. 자동 음성 보정
            if enable_auto_correction:
                audio_data = self._auto_correct_audio(audio_data, sr)
                logger.info("🔄 자동 음성 보정 완료")
            
            # 6. 최종 처리 및 내보내기
            enhanced_audio = self._export_enhanced_audio(audio_data, sr)
            logger.info(f"✅ 오디오 개선 완료: {len(enhanced_audio)} bytes")
            print(f"🎤 음성 품질 개선 결과:")
            print(f"   - 원본 크기: {len(audio_content)} bytes")
            print(f"   - 개선 크기: {len(enhanced_audio)} bytes")
            print(f"   - 개선률: {((len(enhanced_audio) - len(audio_content)) / len(audio_content) * 100):.1f}%")
            
            return enhanced_audio
            
        except Exception as e:
            logger.error(f"❌ 오디오 개선 실패: {str(e)}")
            # 실패 시 원본 반환
            return audio_content
    
    def _load_audio(self, audio_content: bytes, input_format: str) -> Tuple[np.ndarray, int]:
        """오디오 파일 로드 - pydub 사용"""
        try:
            # pydub로 먼저 로드 (형식 자동 인식)
            from pydub import AudioSegment
            audio_io = io.BytesIO(audio_content)
            
            # pydub로 오디오 로드
            audio = AudioSegment.from_file(audio_io, format=input_format)
            
            # numpy 배열로 변환
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            
            # 정규화 (-1.0 ~ 1.0)
            if audio.sample_width == 2:  # 16-bit
                samples = samples / 32768.0
            elif audio.sample_width == 4:  # 32-bit
                samples = samples / 2147483648.0
            
            # 스테레오 → 모노 변환
            if audio.channels == 2:
                samples = samples.reshape((-1, 2)).mean(axis=1)
            
            # 리샘플링 (librosa 사용)
            if audio.frame_rate != self.sample_rate:
                samples = librosa.resample(
                    samples,
                    orig_sr=audio.frame_rate,
                    target_sr=self.sample_rate
                )
            
            return samples, self.sample_rate
            
        except Exception as e:
            logger.error(f"오디오 로드 실패: {e}")
            raise
    
    def _reduce_noise(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        """
        노이즈 제거 (배경 소음, 에코 제거)
        """
        try:
            # noisereduce 라이브러리 사용
            # 첫 0.5초를 노이즈 샘플로 사용
            noise_sample_length = min(int(0.5 * sr), len(audio_data) // 4)
            noise_sample = audio_data[:noise_sample_length]
            
            # 더 강력한 노이즈 제거 적용
            reduced_noise = nr.reduce_noise(
                y=audio_data,
                sr=sr,
                y_noise=noise_sample,
                prop_decrease=0.9,  # 90% 노이즈 감소
                stationary=False,   # 비정상 노이즈
                use_tqdm=False,
                n_std_thresh_stationary=1.5,  # 더 엄격한 임계값
                n_fft=1024,
                win_length=512,
                hop_length=256
            )
            
            print(f"   - 노이즈 제거: RMS {np.sqrt(np.mean(audio_data**2)):.4f} → {np.sqrt(np.mean(reduced_noise**2)):.4f}")
            
            return reduced_noise.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"노이즈 제거 실패, 원본 사용: {e}")
            return audio_data
    
    def _amplify_voice(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        """
        음성 증폭 (작은 소리 증폭)
        """
        try:
            # 현재 음량 측정 (RMS)
            current_rms = np.sqrt(np.mean(audio_data**2))
            current_db = 20 * np.log10(current_rms + 1e-10)
            
            # 더 드라마틱한 증폭을 위한 목표 음량 설정
            target_db = -12  # 더 큰 목표 음량
            db_diff = target_db - current_db
            
            # 더 큰 최대 증폭 허용
            max_amplification = 20  # 20dB까지 증폭 허용
            db_diff = min(db_diff, max_amplification)
            db_diff = max(db_diff, -max_amplification)
            
            # 증폭 적용
            amplification_factor = 10 ** (db_diff / 20)
            amplified_audio = audio_data * amplification_factor
            
            # 클리핑 방지
            max_val = np.max(np.abs(amplified_audio))
            if max_val > 1.0:
                amplified_audio = amplified_audio / max_val * 0.95
            
            print(f"   - 음성 증폭: {current_db:.1f}dB → {current_db + db_diff:.1f}dB (x{amplification_factor:.1f})")
            return amplified_audio.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"음성 증폭 실패, 원본 사용: {e}")
            return audio_data
    
    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        음성 정규화 (볼륨 균등화)
        """
        try:
            # 더 강력한 피크 정규화
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                normalized_audio = audio_data / max_val * 0.98  # 98%로 더 강한 정규화
            else:
                normalized_audio = audio_data
            
            # 더 큰 RMS 정규화 (전체적인 음량 균등화)
            target_rms = 0.2  # 더 큰 목표 RMS 값
            current_rms = np.sqrt(np.mean(normalized_audio**2))
            
            if current_rms > 0:
                rms_factor = target_rms / current_rms
                normalized_audio = normalized_audio * rms_factor
                
                # 다시 클리핑 방지
                max_val = np.max(np.abs(normalized_audio))
                if max_val > 1.0:
                    normalized_audio = normalized_audio / max_val * 0.95
            
            print(f"   - 음성 정규화: RMS {current_rms:.4f} → {np.sqrt(np.mean(normalized_audio**2)):.4f}")
            return normalized_audio.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"정규화 실패, 원본 사용: {e}")
            return audio_data
    
    def _auto_correct_audio(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        """
        자동 음성 보정
        """
        try:
            corrected_audio = audio_data.copy()
            
            # 1. 고주파 노이즈 제거 (hiss 제거)
            corrected_audio = self._remove_high_frequency_noise(corrected_audio, sr)
            
            # 2. 저주파 노이즈 제거 (hum 제거)
            corrected_audio = self._remove_low_frequency_noise(corrected_audio, sr)
            
            # 3. 클릭/팝 노이즈 제거
            corrected_audio = self._remove_clicks_pops(corrected_audio)
            
            # 4. 동적 범위 압축 (Dynamic Range Compression)
            corrected_audio = self._apply_compression(corrected_audio)
            
            logger.info("🔄 자동 보정 완료")
            return corrected_audio.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"자동 보정 실패, 원본 사용: {e}")
            return audio_data
    
    def _remove_high_frequency_noise(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        """고주파 노이즈 제거 (hiss 제거)"""
        try:
            # 8kHz 이상 고주파 필터링
            nyquist = sr / 2
            cutoff = 8000 / nyquist
            b, a = butter(4, cutoff, btype='low')
            return filtfilt(b, a, audio_data)
        except:
            return audio_data
    
    def _remove_low_frequency_noise(self, audio_data: np.ndarray, sr: int) -> np.ndarray:
        """저주파 노이즈 제거 (hum 제거)"""
        try:
            # 60Hz 이하 저주파 필터링 (전원 노이즈 제거)
            nyquist = sr / 2
            cutoff = 60 / nyquist
            b, a = butter(4, cutoff, btype='high')
            return filtfilt(b, a, audio_data)
        except:
            return audio_data
    
    def _remove_clicks_pops(self, audio_data: np.ndarray) -> np.ndarray:
        """클릭/팝 노이즈 제거"""
        try:
            # 간단한 클릭 제거 (급격한 변화 감지 및 완화)
            diff = np.abs(np.diff(audio_data))
            threshold = np.percentile(diff, 99)  # 상위 1% 변화량
            
            # 급격한 변화 지점 찾기
            click_indices = np.where(diff > threshold)[0]
            
            # 클릭 지점 완화
            for idx in click_indices:
                if idx > 0 and idx < len(audio_data) - 1:
                    # 주변 값으로 평활화
                    audio_data[idx] = (audio_data[idx-1] + audio_data[idx+1]) / 2
            
            return audio_data
        except:
            return audio_data
    
    def _apply_compression(self, audio_data: np.ndarray) -> np.ndarray:
        """동적 범위 압축 적용"""
        try:
            # 간단한 소프트 클리핑 (Soft Clipping)
            threshold = 0.8
            compressed = np.where(
                np.abs(audio_data) > threshold,
                np.sign(audio_data) * (threshold + (np.abs(audio_data) - threshold) * 0.3),
                audio_data
            )
            return compressed
        except:
            return audio_data
    
    def _export_enhanced_audio(self, audio_data: np.ndarray, sr: int) -> bytes:
        """개선된 오디오를 M4A 형식으로 내보내기"""
        try:
            from pydub import AudioSegment
            
            # 먼저 WAV 형식으로 메모리에 저장
            wav_buffer = io.BytesIO()
            sf.write(
                wav_buffer,
                audio_data,
                sr,
                format='WAV',
                subtype='PCM_16'
            )
            wav_buffer.seek(0)
            
            # pydub로 WAV 로드
            audio_segment = AudioSegment.from_wav(wav_buffer)
            
            # M4A 형식으로 변환
            output_buffer = io.BytesIO()
            audio_segment.export(
                output_buffer,
                format='ipod',  # M4A/AAC 형식
                codec='aac',
                bitrate='128k'
            )
            
            output_buffer.seek(0)
            enhanced_audio = output_buffer.read()
            
            logger.info(f"📦 M4A 내보내기 완료: {len(enhanced_audio)} bytes")
            return enhanced_audio
            
        except Exception as e:
            logger.error(f"오디오 내보내기 실패: {e}")
            raise


# 전역 인스턴스
audio_enhancement_service = AudioEnhancementService()
