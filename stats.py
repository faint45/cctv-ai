# -*- coding: utf-8 -*-
"""讀違規紀錄,印出每日統計。用法: python stats.py"""
import csv, collections
from pathlib import Path

LOG = Path("logs/violations.csv")

def main():
    if not LOG.exists():
        print("還沒有任何違規紀錄。")
        return
    by_day = collections.Counter()
    by_type = collections.Counter()
    total = 0
    with open(LOG, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            day = row["時間"][:10]
            by_day[day] += 1
            by_type[row["違規類型"]] += 1
            total += 1
    print(f"=== 違規統計(共 {total} 筆)===")
    print("\n[依日期]")
    for d, n in sorted(by_day.items()):
        print(f"  {d}: {n} 次")
    print("\n[依類型]")
    for t, n in by_type.most_common():
        print(f"  {t}: {n} 次")

if __name__ == "__main__":
    main()
