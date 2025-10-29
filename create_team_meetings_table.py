"""
팀 회의록 테이블 생성 스크립트
"""
from database.connection import engine
from models import Base
from models.team_meeting import TeamMeeting  # TeamMeeting 모델 import
from models.team import Team  # Team 모델 import (관계를 위해)

def create_team_meetings_table():
    print("Creating team_meetings table...")
    Base.metadata.create_all(engine)
    print("Team meetings table created successfully.")

if __name__ == "__main__":
    create_team_meetings_table()
