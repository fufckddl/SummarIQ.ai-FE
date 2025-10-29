-- 팀 공개 관련 데이터 삭제 (전부 비공개로 변경)
-- 1. 모든 팀의 공개 허용을 비활성화
UPDATE teams SET is_share = FALSE;

-- 2. 모든 팀의 초대 허용을 비활성화 (플랜별 제한으로 대체)
UPDATE teams SET is_invite = FALSE;

-- 3. 변경 사항 확인
SELECT 
    id,
    name,
    is_share,
    is_invite,
    created_at
FROM teams 
ORDER BY id;

-- 4. 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_teams_is_share ON teams(is_share);
CREATE INDEX IF NOT EXISTS idx_teams_is_invite ON teams(is_invite);
