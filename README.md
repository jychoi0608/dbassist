# dbassist

SQLite 데이터베이스의 테이블/컬럼 메타데이터를 조회해서 개발 중 바로 참고하고 복사할 수 있는 정적 HTML 화면을 생성합니다.

생성된 `db-assist.html`은 DB에 다시 접속하지 않고 브라우저에서 바로 열어 사용할 수 있습니다.

## 기능

- 테이블 목록 셀렉트박스 표시
- 테이블명, 테이블 설명, 컬럼명, 컬럼 설명 LIKE 검색
- 컬럼 정보 표시: 컬럼명, 타입, 길이, NULL 여부, 설명
- 컬럼 목록 복사
- camelcase 컬럼 목록 복사
- MyBatis `select`, `insert`, `update`, `delete` SQL 생성 및 복사

## 필요 환경

- Python 3
- SQLite DB 파일

별도 패키지 설치는 필요하지 않습니다. Python 표준 라이브러리만 사용합니다.

## 사용 방법

기본 파일명인 `assist.db`를 읽어서 `db-assist.html`을 생성하려면 다음 명령을 실행합니다.

```powershell
python generate_db_assist.py
```

DB 파일이나 출력 파일명을 직접 지정할 수도 있습니다.

```powershell
python generate_db_assist.py --db assist.db --out db-assist.html
```

생성 후 `db-assist.html` 파일을 브라우저에서 열면 됩니다.

## 설명 메타데이터

SQLite는 테이블/컬럼 설명을 기본 메타데이터로 저장하지 않습니다. 설명을 화면에 표시하려면 아래 보조 테이블을 만들면 `generate_db_assist.py`가 자동으로 읽습니다.

```sql
create table table_comments (
    table_name text primary key,
    description text
);

create table column_comments (
    table_name text not null,
    column_name text not null,
    description text,
    primary key (table_name, column_name)
);
```

예시:

```sql
insert into table_comments (table_name, description)
values ('users', '사용자');

insert into column_comments (table_name, column_name, description)
values ('users', 'name', '사용자명');
```

## 생성 파일

- `generate_db_assist.py`: SQLite DB를 조회해서 HTML을 생성하는 스크립트
- `db-assist.html`: 생성된 정적 HTML 화면
- `assist.db`: 기본 입력 DB 파일

## 동작 방식

`generate_db_assist.py`는 SQLite의 `sqlite_master`와 `pragma table_info`를 조회해서 테이블과 컬럼 정보를 수집합니다. 수집한 데이터는 `db-assist.html` 내부 JavaScript 변수에 JSON으로 포함되므로, HTML 파일을 연 뒤에는 추가 DB 조회가 발생하지 않습니다.
