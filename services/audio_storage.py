"""
오디오 파일 로컬 저장 서비스
"""
import os
import aiofiles
from pathlib import Path
from typing import List
from database.config import SERVER_BASE_URL

# 저장 디렉토리
STORAGE_DIR = Path(__file__).parent.parent / "storage" / "audio"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class AudioStorage:
    """오디오 파일 저장 관리"""
    
    def __init__(self):
        self.storage_dir = STORAGE_DIR
    
    def get_recording_dir(self, recording_id: str) -> Path:
        """녹음별 디렉토리 경로"""
        recording_dir = self.storage_dir / recording_id
        recording_dir.mkdir(parents=True, exist_ok=True)
        return recording_dir
    
    async def save_chunk(
        self,
        recording_id: str,
        seq: int,
        audio_content: bytes
    ) -> str:
        """
        청크 파일 저장
        
        Returns:
            저장된 파일의 로컬 경로
        """
        recording_dir = self.get_recording_dir(recording_id)
        file_path = recording_dir / f"chunk_{seq:04d}.m4a"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_content)
        
        print(f"✅ Chunk {seq} saved to {file_path}")
        return str(file_path)
    
    async def save_full_audio(
        self,
        recording_id: str,
        audio_content: bytes,
        file_ext: str = "m4a"
    ) -> str:
        """
        전체 오디오 파일 저장 (업로드된 파일)
        
        Args:
            recording_id: 녹음 ID
            audio_content: 오디오 바이트
            file_ext: 파일 확장자 (원본 형식 유지)
        
        Returns:
            저장된 파일의 로컬 경로
        """
        recording_dir = self.get_recording_dir(recording_id)
        file_path = recording_dir / f"full.{file_ext}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_content)
        
        print(f"✅ Full audio saved to {file_path}")
        return str(file_path)
    
    async def merge_chunks(
        self,
        recording_id: str,
        chunk_count: int
    ) -> tuple[str, int]:
        """
        청크 파일들을 하나로 병합
        
        Returns:
            (병합된 파일의 로컬 경로, 실제 길이(밀리초))
        """
        from pydub import AudioSegment
        
        recording_dir = self.get_recording_dir(recording_id)
        merged_path = recording_dir / "merged.m4a"
        
        # 모든 청크 파일 병합
        combined = None
        
        for seq in range(chunk_count):
            chunk_path = recording_dir / f"chunk_{seq:04d}.m4a"
            
            if not chunk_path.exists():
                print(f"⚠️  Chunk {seq} not found, skipping...")
                continue
            
            try:
                chunk_audio = AudioSegment.from_file(str(chunk_path), format="m4a")
                
                if combined is None:
                    combined = chunk_audio
                else:
                    combined += chunk_audio
                
            except Exception as e:
                print(f"❌ Failed to load chunk {seq}: {e}")
        
        if combined:
            # 병합된 파일 저장
            combined.export(str(merged_path), format="mp4", codec="aac")
            
            # 실제 길이 계산 (밀리초)
            actual_duration = len(combined)
            
            print(f"✅ Merged {chunk_count} chunks to {merged_path}")
            print(f"   실제 길이: {actual_duration}ms ({actual_duration/1000:.1f}초)")
            
            return str(merged_path), actual_duration
        else:
            raise Exception("No chunks found to merge")
    
    def get_audio_path(self, recording_id: str) -> str:
        """
        녹음의 오디오 파일 경로 가져오기
        
        Returns:
            파일 경로 (merged.m4a 또는 full.* 형식)
        """
        recording_dir = self.get_recording_dir(recording_id)
        
        # merged.m4a 우선 확인
        merged_path = recording_dir / "merged.m4a"
        if merged_path.exists():
            return str(merged_path)
        
        # full.* 파일 확인 (다양한 확장자 지원)
        for ext in ["m4a", "aac", "mp3", "wav", "ogg"]:
            full_path = recording_dir / f"full.{ext}"
            if full_path.exists():
                return str(full_path)
        
        raise FileNotFoundError(f"Audio file not found for recording {recording_id}")
    
    def get_public_url(self, recording_id: str) -> str:
        """
        오디오 파일의 공개 URL 생성
        """
        return f"{SERVER_BASE_URL}/stt/audio/{recording_id}"
    
    def delete_recording_files(self, recording_id: str) -> bool:
        """
        녹음 파일 삭제
        """
        import shutil
        
        recording_dir = self.get_recording_dir(recording_id)
        
        if recording_dir.exists():
            shutil.rmtree(recording_dir)
            print(f"✅ Deleted audio files for recording {recording_id}")
            return True
        
        return False

