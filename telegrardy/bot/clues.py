import sqlite3
import re

# TODO: Significant optimizations are needed!
def random_question():
    with sqlite3.connect("clues.db") as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT clues.id, clue, answer, category, value
            FROM clues
            JOIN documents ON clues.id = documents.id
            JOIN classifications ON clues.id = classifications.clue_id
            JOIN categories ON classifications.category_id = categories.id
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
        clue = cur.fetchone()

        # TODO: Get rid of "a" or "the" at the beginning and periods.
        return {
            "question": clue[1],
            "answer": re.sub(r"\([^)]*\)", "", clue[2]).strip().lower(),
            "hint": re.sub(r"\w", "-", clue[2]),
            "category": clue[3],
            "value": clue[4],
        }
