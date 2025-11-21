#!/usr/bin/env fish

# 새 스터디 문서 생성 스크립트
# 사용법: ./new-study.sh "제목" "카테고리"

set title $argv[1]
set category $argv[2]

if test -z "$title"
    echo "사용법: ./new-study.sh \"제목\" \"카테고리\""
    echo "카테고리: ai, database, infra, network, programming_language, system_design, etc"
    exit 1
end

if test -z "$category"
    set category "etc"
end

# 파일명 생성 (공백을 언더스코어로)
set filename (echo $title | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
set filepath "$category/$filename.md"

# 템플릿 복사 및 제목 설정
cat template.md | sed "s/\[제목\]/$title/" > "$filepath"

echo "✅ 새 문서 생성됨: $filepath"
echo "🚀 열기: code $filepath"