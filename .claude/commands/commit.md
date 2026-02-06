# Commit with Current File Name

현재 IDE에서 열려있는 파일명을 커밋 메시지로 사용하여 커밋합니다.

## Instructions

1. 현재 IDE에서 열려있는 파일의 경로에서 파일명을 추출합니다.
2. 파일명에서 확장자(.md 등)를 제거합니다.
3. 다음 명령어를 순서대로 실행합니다:
   - `git add .`
   - `git commit -m "파일명"`

예시:
- 열린 파일: `Comprehensive Guide to Cassandra Architecture.md`
- 커밋 메시지: `Comprehensive Guide to Cassandra Architecture`

$ARGUMENTS가 있으면 해당 값을 커밋 메시지로 사용하고, 없으면 현재 열린 파일명을 사용합니다.
