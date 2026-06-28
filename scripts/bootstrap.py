import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from database import db  # noqa: E402


def main():
    db.init_db()
    print("Rastro database initialized.")
    print("Run: uvicorn main:app --reload")
    print("Run: streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
