#!/usr/bin/env python3
# kodi_sync_skeleton.py
# Extended: supports --search and syncing watched/resume status from SQLite to MySQL.

from __future__ import annotations
import sqlite3
import pymysql
import argparse
import sys
import re
from typing import List, Tuple, Dict

# ----------------------- CONNECTIONS -----------------------
def connect_sqlite(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    print(f"[+] Connected to SQLite: {path}")
    return conn

def connect_mysql(host: str, port: int, user: str, password: str, db: str):
    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db, charset='utf8mb3')
    print(f"[+] Connected to MySQL: {user}@{host}:{port}/{db}")
    return conn

# ----------------------- TABLE COUNTS -----------------------
def table_count_sqlite(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.execute("SELECT count(*) AS c FROM sqlite_master WHERE type='table' AND name=?", (table,))
    exists = cur.fetchone()["c"] > 0
    if not exists:
        return 0
    cur = conn.execute(f"SELECT COUNT(*) AS c FROM {table}")
    return cur.fetchone()["c"]

def table_count_mysql(conn, table: str) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (conn.db.decode() if isinstance(conn.db, bytes) else conn.db, table))
    if cur.fetchone()[0] == 0:
        return 0
    cur.execute(f"SELECT COUNT(*) FROM `{table}`")
    val = cur.fetchone()[0]
    cur.close()
    return val

# ----------------------- UNIQUEID SAMPLES -----------------------
def sample_uniqueid_sqlite(conn: sqlite3.Connection, limit: int = 5) -> List[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM uniqueid LIMIT ?", (limit,))
    return cur.fetchall()

def sample_uniqueid_mysql(conn, limit: int = 5) -> List[Tuple]:
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM uniqueid LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    return rows

# ----------------------- MATCH BY UNIQUEID -----------------------
def find_matches_by_uniqueid(sqlite_conn, mysql_conn, limit: int = 20):
    cur = sqlite_conn.execute("SELECT media_id, media_type, type, value FROM uniqueid WHERE type IN ('tvdb','imdb') LIMIT ?", (limit,))
    src_rows = cur.fetchall()
    print(f"[+] Found {len(src_rows)} sample uniqueid rows (types tvdb/imdb) in source sqlite")
    if len(src_rows) == 0:
        src_rows = sqlite_conn.execute("SELECT media_id, media_type, type, value FROM uniqueid LIMIT ?", (limit,)).fetchall()
        print(f"[!] Fallback used: using any uniqueid values (count {len(src_rows)})")

    tgt_cur = mysql_conn.cursor(pymysql.cursors.DictCursor)
    matches = []
    for r in src_rows:
        typ = r["type"]
        val = r["value"]
        tgt_cur.execute("SELECT * FROM uniqueid WHERE type = %s AND value = %s LIMIT 5", (typ, val))
        found = tgt_cur.fetchall()
        matches.append((r, found))
    tgt_cur.close()
    return matches

def print_matches(matches):
    for src, found in matches:
        print("----")
        print(f"Source: media_id={src['media_id']!r} media_type={src['media_type']!r} type={src['type']!r} value={src['value']!r}")
        if not found:
            print("  -> No match on target.")
        else:
            for f in found:
                print(f"  -> Target uniqueid_id={f.get('uniqueid_id')} media_id={f.get('media_id')} media_type={f.get('media_type')} type={f.get('type')} value={f.get('value')}")

# ----------------------- MYSQL SEARCH -----------------------
def normalize_search_words(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9']+", text) if w]

def search_mysql_titles(conn, search_text: str) -> List[Tuple[str,int]]:
    words = normalize_search_words(search_text)
    if not words:
        print("[!] Please provide some search words.")
        return []

    like_clause = " AND ".join(f"LOWER(t.c00) LIKE %s" for _ in words)
    params = [f"%{w}%" for w in words]

    sql = f"""
    SELECT 'movie' AS type, m.idMovie AS id, t.c00 AS title, u.type AS id_type, u.value AS id_value
    FROM movie m
    JOIN uniqueid u ON u.media_id = m.idMovie AND u.media_type='movie'
    JOIN movie_view t ON t.idMovie = m.idMovie
    WHERE {like_clause}

    UNION ALL

    SELECT 'tvshow' AS type, s.idShow AS id, t.c00 AS title, u.type AS id_type, u.value AS id_value
    FROM tvshow s
    JOIN uniqueid u ON u.media_id = s.idShow AND u.media_type='tvshow'
    JOIN tvshow_view t ON t.idShow = s.idShow
    WHERE {like_clause}

    ORDER BY type, title;
    """

    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute(sql, params * 2)
    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("[!] No results found.")
        return []

    results: Dict[Tuple[str,int], str] = {}
    print("\n[+] Search results:")
    for row in rows:
        print(f"{row['type']}: {row['title']} [{row['id_type']}: {row['id_value']}]")
        results[(row['type'], row['id'])] = row['title']

    return list(results.keys())  # return (type,id) pairs for updates

# ----------------------- SYNC RESUME/WATCHED -----------------------
def sync_resume_watched(sqlite_conn, mysql_conn, search: str | None = None, dry_run: bool = True):
    """
    Sync watched status (playCount) and resume points (bookmarks) from SQLite to MySQL.
    - Matches by strFilename in files table.
    - Optionally filters by search term.
    - dry_run=True will just print the intended updates without applying them.
    """
    # Prepare search filtering
    search_words: list[str] = search.lower().split() if search else []

    mcur = mysql_conn.cursor(pymysql.cursors.DictCursor)

    # Sync playCount (watched count)
    s_files = sqlite_conn.execute("SELECT strFilename, playCount FROM files").fetchall()
    for f in s_files:
        filename = f["strFilename"]
        play_count = f["playCount"]  # Keep None intact

        # Apply search filter
        if search_words and not all(w in filename.lower() for w in search_words):
            continue

        # Find matching file in MySQL
        mcur.execute("SELECT idFile, playCount FROM files WHERE strFilename=%s", (filename,))
        target = mcur.fetchone()
        if not target:
            continue

        # Build the SQL safely
        if play_count is None:
            sql = "UPDATE files SET playCount=NULL WHERE idFile=%s"
            params = (target["idFile"],)
            action = "set playCount=NULL"
        else:
            sql = "UPDATE files SET playCount=%s WHERE idFile=%s"
            params = (play_count, target["idFile"])
            action = f"set playCount={play_count}"

        if dry_run:
            print(f"[DRY-RUN] Would {action} for '{filename}' (idFile={target['idFile']})")
        else:
            print(f"Updating {action} for '{filename}' (idFile={target['idFile']})")
            mcur.execute(sql, params)

    # 2️⃣ Sync bookmarks (resume points)
    s_bookmarks = sqlite_conn.execute(
        "SELECT idFile, timeInSeconds, totalTimeInSeconds, player, playerState, type FROM bookmark"
    ).fetchall()

    for b in s_bookmarks:
        # Map SQLite idFile → filename → MySQL idFile
        s_file = sqlite_conn.execute("SELECT strFilename FROM files WHERE idFile=?", (b["idFile"],)).fetchone()
        if not s_file:
            continue
        filename = s_file["strFilename"]

        # Apply search filter
        if search_words and not all(w in filename.lower() for w in search_words):
            continue

        mcur.execute("SELECT idFile FROM files WHERE strFilename=%s", (filename,))
        target = mcur.fetchone()
        if not target:
            continue
        target_idFile = target["idFile"]

        if dry_run:
            print(f"[DRY-RUN] Would upsert bookmark for '{filename}': time={b['timeInSeconds']}/{b['totalTimeInSeconds']}")
        else:
            # Delete old bookmark
            mcur.execute("DELETE FROM bookmark WHERE idFile=%s", (target_idFile,))
            # Insert new bookmark
            mcur.execute(
                "INSERT INTO bookmark (idFile, timeInSeconds, totalTimeInSeconds, player, playerState, type) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (target_idFile, b["timeInSeconds"], b["totalTimeInSeconds"], b["player"], b["playerState"], b["type"])
            )

    if not dry_run:
        mysql_conn.commit()
    mcur.close()

# ----------------------- MAIN -----------------------
def main(argv):
    p = argparse.ArgumentParser(description="Kodi sync skeleton: test connections, sample uniqueid matching, search, and update watched/resume.")
    p.add_argument("--sqlite", required=True, help="Path to Shield SQLite MyVideos DB (e.g. MyVideos131.db)")
    p.add_argument("--mysql-host", required=True, help="MySQL host (iPad DB host)")
    p.add_argument("--mysql-port", required=False, default=3307, type=int)
    p.add_argument("--mysql-user", required=True)
    p.add_argument("--mysql-pass", required=True)
    p.add_argument("--mysql-db", required=True, help="Target MySQL database name (e.g. MyVideos121)")
    p.add_argument("--search", required=False, help="Optional search term to look up titles in MySQL (movie/tvshow)")
    p.add_argument("--dry-run", action="store_true", help="Do not actually update MySQL; just show what would be done.")
    args = p.parse_args(argv)

    try:
        sconn = connect_sqlite(args.sqlite)
    except Exception as e:
        print("[ERROR] sqlite connect:", e)
        return 1

    try:
        mconn = connect_mysql(args.mysql_host, args.mysql_port, args.mysql_user, args.mysql_pass, args.mysql_db)
    except Exception as e:
        print("[ERROR] mysql connect:", e)
        return 2

    # If search provided, get filtered keys
    filter_keys = None
    if args.search:
        filter_keys = search_mysql_titles(mconn, args.search)
        if not filter_keys:
            print("[!] No titles matched search; nothing to update.")
            sconn.close()
            mconn.close()
            return 0

    # Perform resume/watched sync
    print("\n[+] Syncing watched/resume status...")
    sync_resume_watched(sconn, mconn, search=args.search, dry_run=args.dry_run)

    sconn.close()
    mconn.close()
    print("\n[+] Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

