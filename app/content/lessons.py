"""תוכנית הלימודים של הבוט.

כל שיעור מורכב מהסבר, דוגמת קוד, תרגיל אחד וכמה שאלות חידון.
הטקסט מיועד ל-Telegram במצב parse_mode=HTML, ולכן מותר בו רק
<b>, <i>, <u>, <code>, <pre>, <a>.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Quiz:
    question: str
    options: tuple[str, ...]
    answer: int  # אינדקס התשובה הנכונה בתוך options
    explanation: str


@dataclass(frozen=True)
class Exercise:
    prompt: str
    hint: str
    solution: str
    #  מילות מפתח שחייבות להופיע בפתרון כשאין בדיקה חכמה זמינה
    required: tuple[str, ...] = ()
    #  הפלט המדויק שהקוד אמור להדפיס, אם יש כזה (משמש את /run)
    expected_output: str | None = None


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    emoji: str
    goal: str
    body: str
    example: str
    exercise: Exercise
    quizzes: tuple[Quiz, ...] = field(default_factory=tuple)

    @property
    def display_title(self) -> str:
        return f"{self.emoji} {self.title}"


LESSONS: tuple[Lesson, ...] = (
    Lesson(
        id="01-hello",
        title="שלום Python",
        emoji="👋",
        goal="להריץ את שורת הקוד הראשונה ולהדפיס טקסט למסך.",
        body=(
            "Python היא שפת תכנות שנקראת כמעט כמו אנגלית. כל תוכנית היא רשימת "
            "הוראות שהמחשב מבצע לפי הסדר, שורה אחרי שורה.\n\n"
            "הפקודה הראשונה שכדאי להכיר היא <code>print()</code> - היא מדפיסה "
            "למסך כל מה שנכתוב בתוך הסוגריים.\n\n"
            "טקסט בפייתון נקרא <b>מחרוזת</b> (string) ועוטפים אותו במרכאות, "
            "בודדות או כפולות - שתי הצורות זהות.\n\n"
            "שורה שמתחילה ב-<code>#</code> היא <b>הערה</b>: פייתון מתעלמת ממנה "
            "לגמרי, והיא נועדה להסביר את הקוד לבני אדם."
        ),
        example=(
            '# התוכנית הראשונה שלי\n'
            'print("שלום עולם!")\n'
            'print("אני לומד Python")\n'
            '\n'
            '# אפשר גם לחשב בתוך print\n'
            'print(7 * 6)\n'
        ),
        exercise=Exercise(
            prompt=(
                "כתבו תוכנית שמדפיסה בדיוק שתי שורות:\n"
                "בשורה הראשונה את השם שלכם, ובשנייה את המספר 2026."
            ),
            hint="צריך שתי פקודות print נפרדות. מספרים נכתבים בלי מרכאות.",
            solution='print("דנה")\nprint(2026)\n',
            required=("print",),
        ),
        quizzes=(
            Quiz(
                question="מה תדפיס השורה <code>print(\"3 + 4\")</code>?",
                options=("7", "3 + 4", "שגיאה", '"3 + 4"'),
                answer=1,
                explanation=(
                    "מה שבתוך המרכאות הוא טקסט, ולכן הוא מודפס כמו שהוא. "
                    "בלי המרכאות - <code>print(3 + 4)</code> - היה מודפס 7."
                ),
            ),
            Quiz(
                question="איזו שורה היא הערה שפייתון מתעלמת ממנה?",
                options=("// הערה", "# הערה", "<!-- הערה -->", "-- הערה"),
                answer=1,
                explanation="בפייתון הערה בשורה אחת מתחילה בסולמית <code>#</code>.",
            ),
        ),
    ),
    Lesson(
        id="02-variables",
        title="משתנים",
        emoji="📦",
        goal="לשמור ערכים בזיכרון ולהשתמש בהם שוב.",
        body=(
            "<b>משתנה</b> הוא שם שמצביע על ערך. יוצרים אותו עם סימן שווה אחד:\n"
            "<code>age = 25</code> קורא לערך 25 בשם <code>age</code>.\n\n"
            "סימן <code>=</code> בפייתון אינו 'שווה' מתמטי אלא <b>השמה</b>: קח את "
            "הערך מימין ושמור אותו בשם שמשמאל.\n\n"
            "כללים לשמות משתנים:\n"
            "• אותיות, ספרות וקו תחתון בלבד, ולא מתחילים בספרה\n"
            "• יש הבדל בין אותיות גדולות לקטנות: <code>name</code> ו-<code>Name</code> "
            "הם שני משתנים שונים\n"
            "• בחרו שם שמסביר את התוכן: <code>price</code> עדיף על <code>p</code>\n\n"
            "ערך של משתנה אפשר לשנות בכל רגע - הערך החדש פשוט מחליף את הישן."
        ),
        example=(
            'name = "דנה"\n'
            'age = 25\n'
            'height = 1.68\n'
            '\n'
            'print(name, age, height)\n'
            '\n'
            '# שינוי ערך קיים\n'
            'age = age + 1\n'
            'print("בשנה הבאה:", age)\n'
        ),
        exercise=Exercise(
            prompt=(
                "צרו משתנה <code>price</code> עם הערך 100 ומשתנה "
                "<code>discount</code> עם הערך 25.\n"
                "חשבו את המחיר אחרי ההנחה לתוך משתנה <code>final</code> והדפיסו אותו."
            ),
            hint="המחיר הסופי הוא price פחות discount. השתמשו ב-print(final).",
            solution="price = 100\ndiscount = 25\nfinal = price - discount\nprint(final)\n",
            required=("price", "discount", "final", "print"),
            expected_output="75",
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה יודפס?\n<pre>x = 5\nx = 8\nprint(x)</pre>"
                ),
                options=("5", "8", "13", "שגיאה"),
                answer=1,
                explanation="ההשמה השנייה דורסת את הראשונה, ולכן נשאר הערך 8.",
            ),
            Quiz(
                question="איזה שם משתנה אינו חוקי בפייתון?",
                options=("total_price", "price2", "2price", "_price"),
                answer=2,
                explanation="שם משתנה לא יכול להתחיל בספרה.",
            ),
        ),
    ),
    Lesson(
        id="03-types",
        title="טיפוסי נתונים",
        emoji="🔢",
        goal="להכיר מספרים, טקסט ובוליאנים - ולדעת להמיר ביניהם.",
        body=(
            "לכל ערך בפייתון יש <b>טיפוס</b>. ארבעת הבסיסיים:\n"
            "• <code>int</code> - מספר שלם, למשל 42\n"
            "• <code>float</code> - מספר עשרוני, למשל 3.14\n"
            "• <code>str</code> - מחרוזת טקסט, למשל \"שלום\"\n"
            "• <code>bool</code> - אמת או שקר: <code>True</code> / <code>False</code>\n\n"
            "הפונקציה <code>type(x)</code> מגלה את הטיפוס של כל ערך.\n\n"
            "הטיפוס קובע מה מותר לעשות: <code>2 + 3</code> נותן 5, אבל "
            "<code>\"2\" + \"3\"</code> נותן <code>\"23\"</code> כי חיבור מחרוזות "
            "מדביק אותן. <code>\"2\" + 3</code> פשוט יזרוק שגיאה.\n\n"
            "לכן ממירים בין טיפוסים: <code>int(\"5\")</code>, "
            "<code>float(\"2.5\")</code>, <code>str(10)</code>."
        ),
        example=(
            'count = 10\n'
            'price = 19.90\n'
            'name = "ספר"\n'
            'in_stock = True\n'
            '\n'
            'print(type(count), type(price), type(name), type(in_stock))\n'
            '\n'
            '# חיבור מחרוזות מול חיבור מספרים\n'
            'print("2" + "3")\n'
            'print(2 + 3)\n'
            '\n'
            '# המרה\n'
            'print(int("2") + 3)\n'
        ),
        exercise=Exercise(
            prompt=(
                "נתונה המחרוזת <code>year = \"1991\"</code>.\n"
                "המירו אותה למספר שלם, הוסיפו 30 והדפיסו את התוצאה."
            ),
            hint="השתמשו ב-int(year) כדי לקבל מספר.",
            solution='year = "1991"\nresult = int(year) + 30\nprint(result)\n',
            required=("int(", "print"),
            expected_output="2021",
        ),
        quizzes=(
            Quiz(
                question="מה הטיפוס של הערך <code>3.0</code>?",
                options=("int", "float", "str", "bool"),
                answer=1,
                explanation="נקודה עשרונית הופכת את המספר ל-float, גם כשהשארית אפס.",
            ),
            Quiz(
                question="מה התוצאה של <code>\"5\" * 3</code>?",
                options=("15", "555", "שגיאה", "53"),
                answer=1,
                explanation=(
                    "כפל מחרוזת במספר שלם משכפל אותה, ולכן מתקבל "
                    "<code>\"555\"</code>."
                ),
            ),
        ),
    ),
    Lesson(
        id="04-input",
        title="קלט מהמשתמש",
        emoji="⌨️",
        goal="לקרוא נתונים מהמשתמש ולהמיר אותם לטיפוס הנכון.",
        body=(
            "הפונקציה <code>input()</code> עוצרת את התוכנית, מחכה שהמשתמש יקליד "
            "שורה, ומחזירה אותה.\n\n"
            "נקודה קריטית: <code>input()</code> מחזירה <b>תמיד מחרוזת</b>, גם כשהמשתמש "
            "הקליד מספר. אם צריך לחשב - חייבים להמיר:\n"
            "<code>age = int(input(\"גיל: \"))</code>\n\n"
            "אפשר לשלב ערכים בתוך טקסט בעזרת <b>f-string</b>: מוסיפים "
            "<code>f</code> לפני המרכאות וכותבים שמות משתנים בתוך סוגריים מסולסלים.\n"
            "<code>print(f\"שלום {name}, אתה בן {age}\")</code>"
        ),
        example=(
            'name = input("איך קוראים לך? ")\n'
            'age = int(input("בן כמה אתה? "))\n'
            '\n'
            'print(f"נעים להכיר, {name}!")\n'
            'print(f"בעוד 10 שנים תהיה בן {age + 10}")\n'
        ),
        exercise=Exercise(
            prompt=(
                "קראו מהמשתמש שני מספרים שלמים והדפיסו את הסכום שלהם "
                "במשפט מלא, למשל: <code>הסכום הוא 12</code>."
            ),
            hint="שני input נפרדים, כל אחד עטוף ב-int(), ואז f-string.",
            solution=(
                'a = int(input("מספר ראשון: "))\n'
                'b = int(input("מספר שני: "))\n'
                'print(f"הסכום הוא {a + b}")\n'
            ),
            required=("input", "int(", "print"),
        ),
        quizzes=(
            Quiz(
                question=(
                    "המשתמש הקליד 5. מה יקרה?\n"
                    "<pre>x = input()\nprint(x + 1)</pre>"
                ),
                options=("יודפס 6", "יודפס 51", "תיזרק שגיאה", "יודפס 5"),
                answer=2,
                explanation=(
                    "input מחזירה מחרוזת, וחיבור של מחרוזת עם מספר זורק "
                    "<code>TypeError</code>. הפתרון: <code>int(x) + 1</code>."
                ),
            ),
            Quiz(
                question="מה מדפיס <code>print(f\"{2 + 2}\")</code>?",
                options=("2 + 2", "4", "{2 + 2}", "שגיאה"),
                answer=1,
                explanation="בתוך f-string הביטוי בסוגריים המסולסלים מחושב לפני ההדפסה.",
            ),
        ),
    ),
    Lesson(
        id="05-conditions",
        title="תנאים",
        emoji="🔀",
        goal="לגרום לתוכנית להחליט בין מסלולים שונים.",
        body=(
            "<code>if</code> מריץ בלוק קוד רק כשהתנאי נכון. אם לא - אפשר לתת חלופה "
            "עם <code>elif</code> (תנאי נוסף) ו-<code>else</code> (כל השאר).\n\n"
            "אופרטורים להשוואה: <code>==</code> שווה, <code>!=</code> שונה, "
            "<code>&gt;</code>, <code>&lt;</code>, <code>&gt;=</code>, <code>&lt;=</code>.\n"
            "שימו לב: <code>=</code> זו השמה, <code>==</code> זו השוואה.\n\n"
            "מחברים תנאים עם <code>and</code>, <code>or</code> ו-<code>not</code>.\n\n"
            "<b>הזחה קובעת מבנה</b>: בפייתון אין סוגריים מסולסלים. מה ששייך ל-if "
            "מוזח פנימה בארבעה רווחים, ומי שלא מוזח כבר לא חלק מהתנאי."
        ),
        example=(
            'grade = 85\n'
            '\n'
            'if grade >= 90:\n'
            '    print("מצוין")\n'
            'elif grade >= 70:\n'
            '    print("טוב")\n'
            'else:\n'
            '    print("צריך לתרגל")\n'
            '\n'
            '# שילוב תנאים\n'
            'age = 20\n'
            'has_ticket = True\n'
            'if age >= 18 and has_ticket:\n'
            '    print("אפשר להיכנס")\n'
        ),
        exercise=Exercise(
            prompt=(
                "כתבו תוכנית שמקבלת מספר לתוך משתנה <code>n</code> ומדפיסה "
                "<code>חיובי</code>, <code>שלילי</code> או <code>אפס</code> בהתאם לערכו."
            ),
            hint="שלושה מקרים: if n > 0, elif n < 0, else.",
            solution=(
                'n = 5\n'
                'if n > 0:\n'
                '    print("חיובי")\n'
                'elif n < 0:\n'
                '    print("שלילי")\n'
                'else:\n'
                '    print("אפס")\n'
            ),
            required=("if", "elif", "else", "print"),
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה יודפס?\n"
                    "<pre>x = 10\nif x > 5:\n    print(\"א\")\nelif x > 8:\n"
                    "    print(\"ב\")</pre>"
                ),
                options=("א", "ב", "א ואז ב", "כלום"),
                answer=0,
                explanation=(
                    "ברגע שתנאי אחד מתקיים, הפייתון מדלגת על כל ה-elif שאחריו - "
                    "גם אם גם הם נכונים."
                ),
            ),
            Quiz(
                question="מה בודקים עם <code>==</code>?",
                options=(
                    "מכניסים ערך למשתנה",
                    "בודקים אם שני ערכים שווים",
                    "בודקים אם ערכים שונים",
                    "מחברים מספרים",
                ),
                answer=1,
                explanation="<code>=</code> משים ערך, <code>==</code> משווה בין ערכים.",
            ),
        ),
    ),
    Lesson(
        id="06-loops-while",
        title="לולאת while",
        emoji="🔄",
        goal="לחזור על פעולה כל עוד תנאי מתקיים.",
        body=(
            "<code>while</code> מריצה בלוק שוב ושוב כל עוד התנאי נכון. היא מתאימה "
            "כשלא יודעים מראש כמה חזרות יידרשו.\n\n"
            "שלושת החלקים שחייבים להיות:\n"
            "1. אתחול משתנה לפני הלולאה\n"
            "2. תנאי עצירה\n"
            "3. עדכון המשתנה בתוך הלולאה - בלעדיו נקבל <b>לולאה אינסופית</b>\n\n"
            "שתי פקודות שימושיות בתוך לולאה:\n"
            "• <code>break</code> - יציאה מיידית מהלולאה\n"
            "• <code>continue</code> - דילוג לסיבוב הבא"
        ),
        example=(
            'count = 1\n'
            'while count <= 5:\n'
            '    print(count)\n'
            '    count = count + 1\n'
            '\n'
            'print("סיימתי")\n'
            '\n'
            '# עצירה מוקדמת\n'
            'n = 0\n'
            'while True:\n'
            '    n += 1\n'
            '    if n == 3:\n'
            '        break\n'
            'print(n)\n'
        ),
        exercise=Exercise(
            prompt=(
                "השתמשו בלולאת <code>while</code> כדי לחשב את סכום המספרים "
                "מ-1 עד 10 ולהדפיס אותו."
            ),
            hint="התחילו עם total = 0 ו-i = 1, והעלו את i בכל סיבוב עד שהוא עובר 10.",
            solution=(
                'total = 0\n'
                'i = 1\n'
                'while i <= 10:\n'
                '    total += i\n'
                '    i += 1\n'
                'print(total)\n'
            ),
            required=("while", "print"),
            expected_output="55",
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה הבעיה בקוד?\n<pre>i = 0\nwhile i < 3:\n    print(i)</pre>"
                ),
                options=(
                    "שגיאת תחביר",
                    "לולאה אינסופית - i לא מתעדכן",
                    "הלולאה לא תרוץ בכלל",
                    "אין בעיה",
                ),
                answer=1,
                explanation="בלי <code>i += 1</code> התנאי נשאר נכון לנצח.",
            ),
            Quiz(
                question="מה עושה <code>continue</code> בתוך לולאה?",
                options=(
                    "עוצרת את הלולאה",
                    "מדלגת לסיבוב הבא",
                    "מאתחלת את הלולאה מחדש",
                    "מסיימת את התוכנית",
                ),
                answer=1,
                explanation=(
                    "<code>continue</code> מדלגת על שארית הסיבוב הנוכחי וממשיכה "
                    "לסיבוב הבא, בניגוד ל-<code>break</code> שיוצאת מהלולאה."
                ),
            ),
        ),
    ),
    Lesson(
        id="07-loops-for",
        title="לולאת for ו-range",
        emoji="🎯",
        goal="לעבור על רצף ערכים בצורה קצרה וברורה.",
        body=(
            "<code>for</code> עוברת על כל פריט באוסף, אחד אחרי השני, בלי לנהל "
            "מונה ידנית.\n\n"
            "<code>range()</code> מייצרת רצף מספרים:\n"
            "• <code>range(5)</code> - 0,1,2,3,4\n"
            "• <code>range(2, 6)</code> - 2,3,4,5\n"
            "• <code>range(0, 10, 2)</code> - 0,2,4,6,8\n\n"
            "הערך העליון תמיד <b>לא כלול</b> - זו טעות נפוצה למתחילים.\n\n"
            "אפשר לעבור גם על מחרוזת (אות אחר אות) ועל רשימה (איבר אחר איבר)."
        ),
        example=(
            'for i in range(5):\n'
            '    print(i)\n'
            '\n'
            'for letter in "פייתון":\n'
            '    print(letter)\n'
            '\n'
            '# לוח הכפל של 7\n'
            'for i in range(1, 11):\n'
            '    print(f"7 x {i} = {7 * i}")\n'
        ),
        exercise=Exercise(
            prompt=(
                "הדפיסו בעזרת <code>for</code> את כל המספרים הזוגיים בין 1 ל-20 "
                "(כולל 20), כל אחד בשורה נפרדת."
            ),
            hint="range(2, 21, 2) מייצר בדיוק את המספרים הזוגיים.",
            solution="for i in range(2, 21, 2):\n    print(i)\n",
            required=("for", "range", "print"),
        ),
        quizzes=(
            Quiz(
                question="כמה פעמים ירוץ הבלוק של <code>for i in range(3, 8):</code>?",
                options=("3", "5", "8", "4"),
                answer=1,
                explanation="הרצף הוא 3,4,5,6,7 - חמישה ערכים; 8 אינו כלול.",
            ),
            Quiz(
                question="מה מדפיס <code>print(list(range(0, 10, 3)))</code>?",
                options=(
                    "[0, 3, 6, 9]",
                    "[0, 3, 6, 9, 12]",
                    "[3, 6, 9]",
                    "[0, 1, 2, ..., 9]",
                ),
                answer=0,
                explanation="הקפיצה היא 3, והרצף נעצר לפני 10.",
            ),
        ),
    ),
    Lesson(
        id="08-lists",
        title="רשימות",
        emoji="📋",
        goal="לאחסן אוסף ערכים במשתנה אחד ולעבד אותו.",
        body=(
            "<b>רשימה</b> (list) מחזיקה כמה ערכים בסדר קבוע, בתוך סוגריים מרובעים:\n"
            "<code>fruits = [\"תפוח\", \"בננה\", \"תמר\"]</code>\n\n"
            "ניגשים לאיבר לפי <b>אינדקס</b>, שמתחיל מ-0:\n"
            "<code>fruits[0]</code> הוא הראשון, <code>fruits[-1]</code> הוא האחרון.\n\n"
            "פעולות שימושיות:\n"
            "• <code>len(fruits)</code> - כמה איברים יש\n"
            "• <code>fruits.append(\"ענב\")</code> - הוספה בסוף\n"
            "• <code>fruits.remove(\"בננה\")</code> - הסרה לפי ערך\n"
            "• <code>fruits.sort()</code> - מיון\n"
            "• <code>\"תמר\" in fruits</code> - בדיקת הימצאות\n\n"
            "פרוסות (slicing) מחזירות חלק מהרשימה: <code>fruits[1:3]</code>."
        ),
        example=(
            'grades = [90, 75, 88, 100, 62]\n'
            '\n'
            'print(grades[0], grades[-1])\n'
            'print(len(grades))\n'
            'print(sum(grades) / len(grades))\n'
            '\n'
            'grades.append(95)\n'
            'grades.sort()\n'
            'print(grades)\n'
            '\n'
            'for g in grades:\n'
            '    if g >= 90:\n'
            '        print(f"ציון גבוה: {g}")\n'
        ),
        exercise=Exercise(
            prompt=(
                "נתונה הרשימה <code>nums = [4, 17, 8, 23, 42, 15]</code>.\n"
                "הדפיסו את הגדול ביותר ואת הממוצע."
            ),
            hint="max(nums) מחזיר את הגדול, ו-sum(nums) / len(nums) את הממוצע.",
            solution=(
                'nums = [4, 17, 8, 23, 42, 15]\n'
                'print(max(nums))\n'
                'print(sum(nums) / len(nums))\n'
            ),
            required=("nums", "print"),
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה יודפס?\n<pre>items = [10, 20, 30]\nprint(items[1])</pre>"
                ),
                options=("10", "20", "30", "שגיאה"),
                answer=1,
                explanation="אינדקס 0 הוא 10, אינדקס 1 הוא 20 - הספירה מתחילה מאפס.",
            ),
            Quiz(
                question="איזו פעולה מוסיפה איבר לסוף רשימה?",
                options=("add()", "append()", "insert_end()", "push()"),
                answer=1,
                explanation="<code>append()</code> מוסיפה איבר יחיד בסוף הרשימה.",
            ),
        ),
    ),
    Lesson(
        id="09-strings",
        title="עבודה עם מחרוזות",
        emoji="✂️",
        goal="לחתוך, לחפש ולעצב טקסט.",
        body=(
            "מחרוזת היא רצף תווים, ואפשר לגשת אליה כמו לרשימה: "
            "<code>text[0]</code>, <code>text[-1]</code>, <code>text[2:5]</code>.\n\n"
            "מתודות נפוצות:\n"
            "• <code>.upper()</code> / <code>.lower()</code> - שינוי רישיות\n"
            "• <code>.strip()</code> - מסיר רווחים מההתחלה ומהסוף\n"
            "• <code>.split(\",\")</code> - מפצל לרשימה\n"
            "• <code>.replace(\"א\", \"ב\")</code> - החלפה\n"
            "• <code>.startswith()</code> / <code>.endswith()</code>\n"
            "• <code>\",\".join(items)</code> - מחבר רשימה למחרוזת\n\n"
            "מחרוזות הן <b>בלתי ניתנות לשינוי</b>: כל מתודה מחזירה מחרוזת חדשה "
            "ולא משנה את המקורית. צריך לשמור את התוצאה במשתנה."
        ),
        example=(
            'text = "  Hello Python World  "\n'
            '\n'
            'clean = text.strip()\n'
            'print(clean)\n'
            'print(clean.upper())\n'
            'print(clean.split(" "))\n'
            'print(len(clean))\n'
            '\n'
            'email = "dana@example.com"\n'
            'user = email.split("@")[0]\n'
            'print(user)\n'
        ),
        exercise=Exercise(
            prompt=(
                "נתונה המחרוזת <code>s = \"python is fun\"</code>.\n"
                "הדפיסו אותה באותיות גדולות, ואז הדפיסו כמה מילים יש בה."
            ),
            hint="upper() לאותיות גדולות, ו-len(s.split()) לספירת המילים.",
            solution=(
                's = "python is fun"\n'
                'print(s.upper())\n'
                'print(len(s.split()))\n'
            ),
            required=("upper", "split", "print"),
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה יודפס?\n<pre>s = \"abc\"\ns.upper()\nprint(s)</pre>"
                ),
                options=("ABC", "abc", "שגיאה", "None"),
                answer=1,
                explanation=(
                    "מחרוזות אינן ניתנות לשינוי. <code>upper()</code> מחזירה מחרוזת "
                    "חדשה, ובלי השמה התוצאה נזרקת."
                ),
            ),
            Quiz(
                question="מה מחזיר <code>\"a,b,c\".split(\",\")</code>?",
                options=(
                    '"abc"',
                    "['a', 'b', 'c']",
                    "['a,b,c']",
                    "שגיאה",
                ),
                answer=1,
                explanation="<code>split</code> מפצל לפי התו שנתנו ומחזיר רשימה.",
            ),
        ),
    ),
    Lesson(
        id="10-dicts",
        title="מילונים",
        emoji="🗂",
        goal="לשמור נתונים לפי מפתח במקום לפי מיקום.",
        body=(
            "<b>מילון</b> (dict) שומר זוגות של מפתח וערך בתוך סוגריים מסולסלים:\n"
            "<code>person = {\"name\": \"דנה\", \"age\": 25}</code>\n\n"
            "ניגשים לפי מפתח ולא לפי אינדקס: <code>person[\"name\"]</code>.\n"
            "גישה למפתח שלא קיים זורקת <code>KeyError</code>, ולכן בטוח יותר "
            "להשתמש ב-<code>person.get(\"city\", \"לא ידוע\")</code> שמחזיר "
            "ברירת מחדל.\n\n"
            "פעולות נפוצות:\n"
            "• <code>person[\"city\"] = \"חיפה\"</code> - הוספה או עדכון\n"
            "• <code>del person[\"age\"]</code> - מחיקה\n"
            "• <code>\"name\" in person</code> - בדיקת קיום מפתח\n"
            "• <code>person.keys()</code>, <code>.values()</code>, <code>.items()</code>"
        ),
        example=(
            'student = {"name": "יוסי", "grade": 88, "city": "תל אביב"}\n'
            '\n'
            'print(student["name"])\n'
            'print(student.get("phone", "אין טלפון"))\n'
            '\n'
            'student["grade"] = 92\n'
            'student["age"] = 17\n'
            '\n'
            'for key, value in student.items():\n'
            '    print(f"{key}: {value}")\n'
        ),
        exercise=Exercise(
            prompt=(
                "צרו מילון <code>prices</code> עם שלושה מוצרים ומחיריהם, "
                "והדפיסו את סכום כל המחירים."
            ),
            hint="sum(prices.values()) מחשב את סכום הערכים.",
            solution=(
                'prices = {"לחם": 8, "חלב": 6, "גבינה": 14}\n'
                'print(sum(prices.values()))\n'
            ),
            required=("prices", "print"),
        ),
        quizzes=(
            Quiz(
                question="מה קורה בגישה למפתח שלא קיים, כמו <code>d[\"x\"]</code>?",
                options=(
                    "מוחזר None",
                    "נזרקת שגיאת KeyError",
                    "המפתח נוצר אוטומטית",
                    "מוחזרת מחרוזת ריקה",
                ),
                answer=1,
                explanation=(
                    "לגישה בטוחה השתמשו ב-<code>.get()</code> שמחזיר ברירת מחדל "
                    "במקום לזרוק שגיאה."
                ),
            ),
            Quiz(
                question="מה מחזיר <code>.items()</code> של מילון?",
                options=(
                    "רק את המפתחות",
                    "רק את הערכים",
                    "זוגות של מפתח וערך",
                    "את מספר האיברים",
                ),
                answer=2,
                explanation="<code>.items()</code> מתאים ללולאת for עם שני משתנים.",
            ),
        ),
    ),
    Lesson(
        id="11-functions",
        title="פונקציות",
        emoji="⚙️",
        goal="לארוז קוד חוזר בשם אחד ולהשתמש בו שוב ושוב.",
        body=(
            "<b>פונקציה</b> היא קטע קוד עם שם, שמקבל קלט ומחזיר פלט. מגדירים "
            "אותה עם <code>def</code>:\n"
            "<pre>def greet(name):\n    return f\"שלום {name}\"</pre>\n"
            "ההגדרה לבדה לא מריצה כלום - צריך <b>לקרוא</b> לפונקציה: "
            "<code>greet(\"דנה\")</code>.\n\n"
            "<code>return</code> מחזיר ערך ומסיים את הפונקציה מיד. פונקציה בלי "
            "<code>return</code> מחזירה <code>None</code>.\n\n"
            "אפשר לתת לפרמטר <b>ערך ברירת מחדל</b>: "
            "<code>def greet(name, greeting=\"שלום\")</code>.\n\n"
            "משתנה שנוצר בתוך פונקציה הוא <b>מקומי</b> וקיים רק בזמן הריצה שלה."
        ),
        example=(
            'def add(a, b):\n'
            '    return a + b\n'
            '\n'
            '\n'
            'def greet(name, greeting="שלום"):\n'
            '    return f"{greeting} {name}!"\n'
            '\n'
            '\n'
            'print(add(3, 4))\n'
            'print(greet("דנה"))\n'
            'print(greet("יוסי", "בוקר טוב"))\n'
            '\n'
            '\n'
            'def is_even(n):\n'
            '    return n % 2 == 0\n'
            '\n'
            '\n'
            'print(is_even(10))\n'
        ),
        exercise=Exercise(
            prompt=(
                "כתבו פונקציה <code>area(width, height)</code> שמחזירה את שטח "
                "המלבן, וקראו לה עם 5 ו-3 בתוך <code>print</code>."
            ),
            hint="def area(width, height): ואז return width * height.",
            solution=(
                'def area(width, height):\n'
                '    return width * height\n'
                '\n'
                '\n'
                'print(area(5, 3))\n'
            ),
            required=("def", "return", "print"),
            expected_output="15",
        ),
        quizzes=(
            Quiz(
                question=(
                    "מה יודפס?\n<pre>def f(x):\n    x * 2\n\nprint(f(5))</pre>"
                ),
                options=("10", "5", "None", "שגיאה"),
                answer=2,
                explanation=(
                    "חסר <code>return</code>, ולכן הפונקציה מחזירה "
                    "<code>None</code> למרות שהחישוב בוצע."
                ),
            ),
            Quiz(
                question="מה קורה לקוד שכתוב אחרי <code>return</code> בתוך פונקציה?",
                options=(
                    "הוא רץ כרגיל",
                    "הוא לא רץ - return מסיים את הפונקציה",
                    "נזרקת שגיאה",
                    "הוא רץ רק בתנאי",
                ),
                answer=1,
                explanation="<code>return</code> מחזיר ערך ויוצא מהפונקציה מיד.",
            ),
        ),
    ),
    Lesson(
        id="12-errors",
        title="שגיאות וטיפול בהן",
        emoji="🛡",
        goal="להבין הודעות שגיאה ולמנוע קריסה של התוכנית.",
        body=(
            "שגיאות הן חלק מהעבודה. שלוש נפוצות:\n"
            "• <code>SyntaxError</code> - טעות כתיב, למשל נקודתיים חסרות\n"
            "• <code>NameError</code> - שימוש במשתנה שלא הוגדר\n"
            "• <code>TypeError</code> - פעולה על טיפוס לא מתאים, כמו "
            "<code>\"5\" + 1</code>\n"
            "• <code>ValueError</code> - טיפוס נכון אבל ערך לא חוקי, כמו "
            "<code>int(\"abc\")</code>\n\n"
            "קראו את הודעת השגיאה <b>מלמטה למעלה</b>: השורה האחרונה אומרת מה קרה, "
            "והשורה שמעליה מראה איפה.\n\n"
            "כדי שהתוכנית לא תקרוס עוטפים קוד מסוכן ב-<code>try</code> / "
            "<code>except</code> - ותופסים שגיאה ספציפית, לא כל שגיאה שהיא."
        ),
        example=(
            'text = input("הכניסו מספר: ")\n'
            '\n'
            'try:\n'
            '    number = int(text)\n'
            '    print(f"הכפלה: {number * 2}")\n'
            'except ValueError:\n'
            '    print("זה לא מספר תקין")\n'
            '\n'
            '\n'
            '# חלוקה באפס\n'
            'try:\n'
            '    print(10 / 0)\n'
            'except ZeroDivisionError:\n'
            '    print("אי אפשר לחלק באפס")\n'
            'finally:\n'
            '    print("הבלוק הזה תמיד רץ")\n'
        ),
        exercise=Exercise(
            prompt=(
                "כתבו קוד שמנסה להמיר את המחרוזת <code>\"12a\"</code> למספר שלם, "
                "ואם זה נכשל מדפיס <code>קלט לא תקין</code> במקום לקרוס."
            ),
            hint="try: int(\"12a\") ואז except ValueError:",
            solution=(
                'try:\n'
                '    number = int("12a")\n'
                '    print(number)\n'
                'except ValueError:\n'
                '    print("קלט לא תקין")\n'
            ),
            required=("try", "except", "print"),
            expected_output="קלט לא תקין",
        ),
        quizzes=(
            Quiz(
                question="איזו שגיאה תיזרק מ-<code>int(\"hello\")</code>?",
                options=("TypeError", "ValueError", "NameError", "SyntaxError"),
                answer=1,
                explanation=(
                    "הטיפוס נכון (מחרוזת), אבל הערך לא ניתן להמרה - ולכן "
                    "<code>ValueError</code>."
                ),
            ),
            Quiz(
                question="מתי רץ הבלוק של <code>finally</code>?",
                options=(
                    "רק כשיש שגיאה",
                    "רק כשאין שגיאה",
                    "תמיד, עם שגיאה או בלעדיה",
                    "אף פעם",
                ),
                answer=2,
                explanation="<code>finally</code> מתאים לניקוי משאבים, למשל סגירת קובץ.",
            ),
        ),
    ),
)

LESSONS_BY_ID: dict[str, Lesson] = {lesson.id: lesson for lesson in LESSONS}


def find_lesson(lesson_id: str) -> Lesson | None:
    return LESSONS_BY_ID.get(lesson_id)


def lesson_index(lesson_id: str) -> int:
    """מיקום השיעור ברשימה, או -1 אם אינו קיים."""
    for index, lesson in enumerate(LESSONS):
        if lesson.id == lesson_id:
            return index
    return -1


def next_lesson(lesson_id: str) -> Lesson | None:
    index = lesson_index(lesson_id)
    if index == -1 or index + 1 >= len(LESSONS):
        return None
    return LESSONS[index + 1]
