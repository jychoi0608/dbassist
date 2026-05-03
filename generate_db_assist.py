import argparse
import json
import re
import sqlite3
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DB Assist</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #1d2433;
      --muted: #667085;
      --line: #d8dee9;
      --accent: #2563eb;
      --accent-soft: #e8f0ff;
      --code: #101828;
      --code-bg: #f8fafc;
      --ok: #047857;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, "Malgun Gothic", sans-serif;
      font-size: 14px;
      line-height: 1.5;
    }

    button, input, select { font: inherit; }

    .top {
      position: sticky;
      top: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: minmax(260px, 420px) minmax(240px, 1fr);
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(10px);
    }

    .field {
      display: grid;
      gap: 6px;
      min-width: 0;
    }

    .field label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .field input,
    .field select {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 8px 10px;
      outline: none;
    }

    .field input:focus,
    .field select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
    }

    .content {
      width: min(1180px, calc(100% - 32px));
      margin: 18px auto 36px;
      display: grid;
      gap: 14px;
    }

    .summary {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 14px;
      min-height: 42px;
    }

    .summary h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.2;
    }

    .summary .desc {
      color: var(--muted);
      font-size: 13px;
    }

    .section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }

    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 11px 14px;
      border-bottom: 1px solid var(--line);
      background: #fbfcff;
    }

    .section-title {
      margin: 0;
      font-size: 15px;
      font-weight: 700;
    }

    .copy {
      min-width: 66px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      padding: 6px 10px;
    }

    .copy:hover {
      border-color: var(--accent);
      color: var(--accent);
    }

    .copy.done {
      border-color: #a7f3d0;
      background: #ecfdf5;
      color: var(--ok);
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th,
    td {
      padding: 9px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }

    th {
      width: 18%;
      background: #fbfcff;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }

    tr:last-child th,
    tr:last-child td {
      border-bottom: 0;
    }

    .mono { font-family: Consolas, "Courier New", monospace; }

    pre {
      margin: 0;
      overflow: auto;
      background: var(--code-bg);
      color: var(--code);
      padding: 14px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.55;
      white-space: pre;
    }

    .sql-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .empty {
      padding: 32px 16px;
      color: var(--muted);
      text-align: center;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }

    @media (max-width: 760px) {
      .top { grid-template-columns: 1fr; }
      .summary { display: grid; }
      .sql-grid { grid-template-columns: 1fr; }

      th,
      td {
        display: block;
        width: 100%;
      }

      th {
        border-bottom: 0;
        padding-bottom: 2px;
      }

      td { padding-top: 2px; }
    }
  </style>
</head>
<body>
  <header class="top">
    <div class="field">
      <label for="tableSelect">테이블</label>
      <select id="tableSelect"></select>
    </div>
    <div class="field">
      <label for="searchInput">LIKE 검색</label>
      <input id="searchInput" type="search" placeholder="테이블명, 테이블 설명, 컬럼명, 컬럼 설명 검색">
    </div>
  </header>

  <main class="content" id="content"></main>

  <script>
    const dbMeta = __DB_META_JSON__;

    const tableSelect = document.getElementById("tableSelect");
    const searchInput = document.getElementById("searchInput");
    const content = document.getElementById("content");
    let filteredTables = [...dbMeta];

    function toCamelCase(value) {
      return value
        .toLowerCase()
        .split(/[_\\s-]+/)
        .filter(Boolean)
        .map((part, index) => index === 0 ? part : part.charAt(0).toUpperCase() + part.slice(1))
        .join("");
    }

    function pascal(value) {
      const camel = toCamelCase(value);
      return camel.charAt(0).toUpperCase() + camel.slice(1);
    }

    function tableLabel(table) {
      return table.description ? `${table.name} (${table.description})` : table.name;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function sqlParam(column) {
      return `#{${toCamelCase(column.name)}}`;
    }

    function pkColumns(table) {
      const pks = table.columns.filter(column => column.pk);
      return pks.length ? pks : table.columns.slice(0, 1);
    }

    function whereByPk(table) {
      return pkColumns(table)
        .map(column => `${column.name} = ${sqlParam(column)}`)
        .join(" and ");
    }

    function myBatisSql(table, command) {
      const columns = table.columns;
      const nonPkColumns = columns.filter(column => !column.pk);
      const editableColumns = nonPkColumns.length ? nonPkColumns : columns;

      if (command === "select") {
        return [
          `<select id="select${pascal(table.name)}" parameterType="map" resultType="map">`,
          `  select ${columns.map(column => column.name).join(", ")}`,
          `    from ${table.name}`,
          `   where ${whereByPk(table)}`,
          `</select>`
        ].join("\\n");
      }

      if (command === "insert") {
        return [
          `<insert id="insert${pascal(table.name)}" parameterType="map">`,
          `  insert into ${table.name} (`,
          `    ${columns.map(column => column.name).join(", ")}`,
          `  ) values (`,
          `    ${columns.map(sqlParam).join(", ")}`,
          `  )`,
          `</insert>`
        ].join("\\n");
      }

      if (command === "update") {
        return [
          `<update id="update${pascal(table.name)}" parameterType="map">`,
          `  update ${table.name}`,
          `     set ${editableColumns.map(column => `${column.name} = ${sqlParam(column)}`).join(",\\n         ")}`,
          `   where ${whereByPk(table)}`,
          `</update>`
        ].join("\\n");
      }

      return [
        `<delete id="delete${pascal(table.name)}" parameterType="map">`,
        `  delete from ${table.name}`,
        `   where ${whereByPk(table)}`,
        `</delete>`
      ].join("\\n");
    }

    function renderSelect() {
      const selected = tableSelect.value;
      tableSelect.innerHTML = filteredTables
        .map(table => `<option value="${escapeHtml(table.name)}">${escapeHtml(tableLabel(table))}</option>`)
        .join("");

      if (filteredTables.some(table => table.name === selected)) {
        tableSelect.value = selected;
      }
    }

    function columnLine(column) {
      const length = column.length ? ` ${column.length}` : "";
      const nullable = column.nullable ? "NULL" : "NOT NULL";
      const description = column.description ? ` -- ${column.description}` : "";
      return `${column.name.toUpperCase()} ${column.type}${length} ${nullable}${description}`;
    }

    function copySection(title, text) {
      return `
        <section class="section">
          <div class="section-head">
            <h2 class="section-title">${escapeHtml(title)}</h2>
            <button class="copy" type="button" data-copy="${escapeHtml(text)}">복사</button>
          </div>
          <pre>${escapeHtml(text)}</pre>
        </section>
      `;
    }

    function renderContent() {
      const table = filteredTables.find(item => item.name === tableSelect.value) || filteredTables[0];
      if (!table) {
        content.innerHTML = `<div class="empty">검색 결과에 포함된 테이블이 없습니다.</div>`;
        return;
      }

      const columnText = table.columns.map(columnLine).join("\\n");
      const selectText = table.columns.map(column => column.name.toUpperCase()).join(", ");
      const camelText = table.columns.map(column => toCamelCase(column.name)).join(", ");
      const sqlBlocks = ["select", "insert", "update", "delete"].map(command => copySection(command, myBatisSql(table, command))).join("");

      content.innerHTML = `
        <div class="summary">
          <h1>테이블: <span class="mono">${escapeHtml(table.name.toUpperCase())}</span></h1>
          <div class="desc">${escapeHtml(table.description || "설명 없음")}</div>
        </div>

        ${copySection("컬럼", columnText)}
        ${copySection("셀렉트", selectText)}
        ${copySection("셀렉트 camelcase", camelText)}

        <div class="sql-grid">
          ${sqlBlocks}
        </div>
      `;
    }

    function tableMatches(table, keyword) {
      const haystack = [
        table.name,
        table.description,
        ...table.columns.flatMap(column => [column.name, column.description])
      ].join(" ").toLowerCase();

      return haystack.includes(keyword.toLowerCase());
    }

    function applyFilter() {
      const keyword = searchInput.value.trim();
      filteredTables = keyword ? dbMeta.filter(table => tableMatches(table, keyword)) : [...dbMeta];
      renderSelect();
      renderContent();
    }

    document.addEventListener("click", async event => {
      const button = event.target.closest("[data-copy]");
      if (!button) return;

      await navigator.clipboard.writeText(button.dataset.copy);
      button.classList.add("done");
      button.textContent = "완료";
      window.setTimeout(() => {
        button.classList.remove("done");
        button.textContent = "복사";
      }, 1100);
    });

    tableSelect.addEventListener("change", renderContent);
    searchInput.addEventListener("input", applyFilter);

    applyFilter();
  </script>
</body>
</html>
"""


TYPE_PATTERN = re.compile(r"^([A-Za-z0-9_ ]+?)(?:\s*\(([^)]+)\))?$")


def split_type(declared_type):
    value = (declared_type or "").strip()
    if not value:
      return "", ""

    match = TYPE_PATTERN.match(value)
    if not match:
      return value.upper(), ""

    return match.group(1).strip().upper(), (match.group(2) or "").strip()


def read_optional_comments(cursor):
    table_comments = {}
    column_comments = {}

    table_names = {
        row[0].lower()
        for row in cursor.execute(
            "select name from sqlite_master where type = 'table'"
        ).fetchall()
    }

    if "table_comments" in table_names:
        for table_name, description in cursor.execute(
            "select table_name, description from table_comments"
        ).fetchall():
            table_comments[str(table_name).lower()] = description or ""

    if "column_comments" in table_names:
        for table_name, column_name, description in cursor.execute(
            "select table_name, column_name, description from column_comments"
        ).fetchall():
            key = (str(table_name).lower(), str(column_name).lower())
            column_comments[key] = description or ""

    return table_comments, column_comments


def fetch_db_meta(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    table_comments, column_comments = read_optional_comments(cursor)
    rows = cursor.execute(
        """
        select name, type
          from sqlite_master
         where type in ('table', 'view')
           and name not like 'sqlite_%'
           and name not in ('table_comments', 'column_comments')
         order by type, name
        """
    ).fetchall()

    tables = []
    for table_name, object_type in rows:
        columns = []
        escaped_table_name = table_name.replace("'", "''")
        pragma_rows = cursor.execute(f"pragma table_info('{escaped_table_name}')").fetchall()

        for _, column_name, declared_type, notnull, default_value, pk in pragma_rows:
            data_type, length = split_type(declared_type)
            columns.append(
                {
                    "name": column_name,
                    "type": data_type,
                    "length": length,
                    "nullable": not bool(notnull) and not bool(pk),
                    "pk": bool(pk),
                    "default": default_value,
                    "description": column_comments.get(
                        (table_name.lower(), column_name.lower()),
                        "",
                    ),
                }
            )

        tables.append(
            {
                "name": table_name,
                "type": object_type,
                "description": table_comments.get(table_name.lower(), ""),
                "columns": columns,
            }
        )

    connection.close()
    return tables


def build_html(db_meta):
    meta_json = json.dumps(db_meta, ensure_ascii=False, indent=6)
    return HTML_TEMPLATE.replace("__DB_META_JSON__", meta_json)


def main():
    parser = argparse.ArgumentParser(
        description="SQLite DB metadata를 조회해서 DB Assist 정적 HTML을 생성합니다."
    )
    parser.add_argument(
        "--db",
        default="assist.db",
        help="조회할 SQLite DB 파일 경로입니다. 기본값: assist.db",
    )
    parser.add_argument(
        "--out",
        default="db-assist.html",
        help="생성할 HTML 파일 경로입니다. 기본값: db-assist.html",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        raise SystemExit(f"DB 파일을 찾을 수 없습니다: {db_path}")

    db_meta = fetch_db_meta(db_path)
    html = build_html(db_meta)
    out_path.write_text(html, encoding="utf-8", newline="\n")

    print(f"생성 완료: {out_path}")
    print(f"테이블 수: {len(db_meta)}")


if __name__ == "__main__":
    main()
