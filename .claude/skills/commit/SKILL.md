---
name: commit
description: Use this skill when the user wants to commit the currently opened markdown file using its filename (without extension) as the commit message. Trigger on `/commit` or when the user says things like "지금 열린 파일로 커밋해줘", "이 파일명으로 커밋", "파일명을 커밋 메시지로". If `$ARGUMENTS` is supplied, use that as the commit message instead.
---

# Commit with Current File Name

현재 IDE에서 열려있는 파일명을 커밋 메시지로 사용하여 커밋합니다.

## 동작 방식

1. `$ARGUMENTS`가 있으면 → 그 값을 커밋 메시지로 사용
2. 없으면 → 현재 IDE에서 열려있는 파일의 경로에서 파일명을 추출하고 확장자(.md 등) 제거
3. 다음 명령어를 순서대로 실행:
   - `git add .`
   - `git commit -m "파일명"`

## 예시

- 열린 파일: `Comprehensive Guide to Cassandra Architecture.md`
- 커밋 메시지: `Comprehensive Guide to Cassandra Architecture`
