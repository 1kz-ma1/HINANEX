import pandas as pd

from src.hinanex.adapters.edogawa_shelter import (
    fetch_edogawa_shelters,
)


def main() -> None:
    path = fetch_edogawa_shelters()

    print(f"Raw saved: {path}")

    # 日本の自治体CSVではShift_JIS系も多いため、
    # まずcp932で読み込む
    df = pd.read_csv(path, encoding="cp932")

    print()
    print("=== Columns ===")

    for column in df.columns:
        print(repr(column))

    print()
    print("=== Shape ===")
    print(df.shape)

    print()
    print("=== First 3 rows ===")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()