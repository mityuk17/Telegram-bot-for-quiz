import sqlite3
import json
import gspread
gc = gspread.service_account(filename='credentials.json')

def get_connection():
    con = sqlite3.connect('quiz.db')
    return con
def start_sheet():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
       userid INT PRIMARY KEY,
       activequiz TEXT,
       question_num INT,
       points INT);
    """)
        cur.execute("""CREATE TABLE IF NOT EXISTS score(
        userid INT,
        quiz TEXT,
        points INT);
    """)
def user_get_or_create(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT * FROM users WHERE userid = '{user_id}';""")
        result = cur.fetchone()
        if result:
            return result
        else:
            cur.execute(f"""INSERT INTO users VALUES(?,?,?,?);""", (user_id, '0', 0, 0))
            cur.execute(f"""SELECT * FROM users WHERE userid = '{user_id}';""")
            result = cur.fetchone()
            return result
def get_score(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT * FROM score WHERE userid = '{user_id}';""")
        results = cur.fetchall()
    msg = 'Ваши результаты:\n'
    for result in results:
        quiz = result[1]
        with open("quiz.json", "r", encoding='utf-8') as read_file:
            data = json.load(read_file)
            for key in data:
                if data[key] == quiz:
                    quiz_name = key
                    break
        points = result[2]
        msg += f'{quiz_name} : {points}\n'
    return msg
def get_all_quizes():
    with open("quiz.json", "r") as read_file:
        data = json.load(read_file)
    return data
def start_newquiz(userid, link):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""UPDATE users SET activequiz = '{link}', question_num = {0}, points = {0} WHERE userid = {userid};""")
        conn.commit()
def get_question_number(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT question_num FROM users WHERE userid = {user_id}""")
        question_num = cur.fetchone()
    return question_num[0]
def get_quiz_question(link, question_number):
    sh = gc.open_by_key(link)
    worksheet = sh.get_worksheet(0)
    question = worksheet.row_values(question_number+1)
    return question
def give_points(user_id, points):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT points FROM users WHERE userid = {user_id}""")
        current_points = cur.fetchone()[0]
        cur.execute(f"""UPDATE users SET points = '{int(current_points) + int(points)}' WHERE userid = {user_id}""")
        conn.commit()
def get_current_quiz_link(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT activequiz FROM users WHERE userid = {user_id}""")
        current_quiz = cur.fetchone()
    return current_quiz[0]
def next_question(user_id):
    new_question_num = get_question_number(user_id) +1
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""UPDATE users SET question_num = {new_question_num} WHERE userid = {user_id}""")
    question = get_quiz_question(get_current_quiz_link(user_id), new_question_num)
    return(question)
def check_questions(user_id):
    link = get_current_quiz_link(user_id)
    sh = gc.open_by_key(link)
    worksheet = sh.get_worksheet(0)
    amount_questions = len(worksheet.col_values(1))
    current_question = get_question_number(user_id)
    if current_question < amount_questions-1:
        return True
    else:
        return False
def finish_quiz(user_id,username):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT points FROM users WHERE userid = {user_id}""")
        points = cur.fetchone()[0]
        link = get_current_quiz_link(user_id)
        cur.execute("INSERT INTO score VALUES(?, ?, ?);", (user_id, link, points))
        conn.commit()
        cur.execute(f"""UPDATE users SET activequiz = '0', question_num = {0} WHERE userid = {user_id};""")
        conn.commit()
    sh = gc.open_by_key(link)
    worksheet = sh.get_worksheet(1)
    worksheet.append_row([user_id, username, points])
    with open("quiz.json", "r") as read_file:
        data = json.load(read_file)
        for key in data:
            if data[key] == link:
                quiz_name = key
                break
    msg = f'''Завершено прохождение викторины {quiz_name}
Набрано баллов {points}'''
    return msg
