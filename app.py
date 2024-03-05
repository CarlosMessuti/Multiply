import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
import random

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///multiply.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # This happens after the user clicks on the "Begin!" button
    if request.method == "POST":
        # We create the history table if it doesn't exist yet
        db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, users_id INTEGER NOT NULL, wdate DATE NOT NULL, exercise_number INTEGER NOT NULL DEFAULT 0, number_correct INTEGER NOT NULL DEFAULT 0, number_incorrect INTEGER NOT NULL DEFAULT 0, villains_defeated INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (users_id) REFERENCES users(id))")
        current_date = date.today()
        # We look for the current exercise number under today's date
        exercise_number = db.execute("SELECT exercise_number FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
        # If this is the first exercise of the day, we insert a new line in the table
        if len (exercise_number) <= 0:
            db.execute("INSERT INTO history (users_id, wdate, exercise_number, number_correct, number_incorrect, villains_defeated) VALUES (?, ?, 0, 0, 0, 0)", session["user_id"], current_date)
        # We set the counter of correct and incorrect answers to 0 by storing two variables in the session, then a new exercise starts
        session["correct_answers"] = 0
        session["incorrect_answers"] = 0
        # We also check if the user has defeated a villain in the current session. If they didn't, We won't display any medals in the exercise
        villains_defeated= db.execute("SELECT villains_defeated FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
        if villains_defeated[0]["villains_defeated"] == 0:
            session["medal"] = 0
        # After everything is done, We redirect the user to the chosen villain intro
        return redirect("/v_intro")
    # This happens before the user has clicked the "Begin!" button
    else:
        return render_template("index.html")

# This is a constant which will be used frequently. It contains a list of villains and their phrases.
VILLAIN_LIST = {
    "Berenice, the witch": {
        "opening_phrases": ["Let's play a little game. If you lose, I'll turn you into my new pet frog. Ha, Ha, Ha", "Hello, my name is Berenice and my hobbies, as you'll soon see, are math and the black arts. Ha, Ha.", "You think you're good enough to beat me? Let's play a little game. If you lose I'll be the princess and you can be the frog"],
        "answer_is_correct": ["You were just lucky", "Can't believe I didn't foresee that", "You must be cheating", "I won't be so easy on you next time", "That's enough! You're going down like a witch without a broom", "Can't be. Was that the wrong spell?"],
        "answer_is_wrong": ["Gotcha!", "Next time I'll go easy on you. It's more fun if you believe you can beat me", "You still have much to learn", "I'm just warming up", "Who do you take me for? a mere fortune teller?", "You're not in Kansas anymore"],
        "victory": ["What a nice frog! I'm gonna hug you and kiss you and love you forever"],
        "defeat": ["Should have built a house out of candy instead", "I'm melting! Melting! Oh, what a world, what a world!", "Not again! I'm on a strict no-flies diet", "Next time I'll try with a poison apple"],

    },

    "Count Emil": {
        "opening_phrases": ["My name is Emil and I've been waiting FOREVER for someone to challenge me", "What a clean lovely neck you have. Care to face me in a little game?", "I need someone to guard my coffin during the day, and you look just perfect"],
        "answer_is_correct": ["Just a lucky guess", "Can't be! There must be a mistake", "Good! We can play forever after I beat you", "You're soo cool, Brewster...", "You're good, but I'm better"],
        "answer_is_wrong": ["Don't be too hard on yourself. I have centuries of experience", "Guessing will only get you so far", "Better luck next time", "Like a bat caught in a hailstorm, you're going down"],
        "victory": ["Cheer up! You'll be better at math as a vampire", "I might be a count, but at math I'm still the king", "As you'll see, the downside of being a vampire is that you have to depend on others to tell you if your hair is well-groomed"],
        "defeat": ["Should have stopped after losing to Frankenstein's monster", "I'm dead! Again!", "You, miserable little pile of secrets..."]
    },
}

@app.route("/exercise", methods=["GET", "POST"])
@login_required
def exercise():
    print(session["medal"])
    # Give the user 10 operations to resolve one by one
    # TODO
    current_date = date.today()
    current_date_str = current_date.strftime("%Y-%m-%d")
    # The following happens only after the user has submitted their first answer
    if request.method == "POST":
        # If the form returns without an answer, we provide a message, with buttons to resume the exercise or quit
        if not request.form.get("answer"):
            # First, we check if the timer ran out or if the user submitted an empty form
            if "resume" in request.form:
                session["message"] = "Time out!"
            else:
                if "timeout" in request.form and request.form["timeout"] != "true":
                    session["message"] = "You must provide an answer"
                else:
                    session["message"] = "Time out!"
                return render_template("apology_timeout.html", message=session["message"])
            # Then, if the user chooses to continue, we count the answer as incorrect and ask the question again. The message displayed will reflect the nature of the error.
            # We also have to register it in the history table in order to avoid an error later
            number_incorrect = db.execute("SELECT number_incorrect FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
            number_incorrect = number_incorrect[0]['number_incorrect'] + 1
            db.execute("UPDATE history SET number_incorrect = ? WHERE users_id = ? AND wdate = ?", number_incorrect, session["user_id"], current_date)
            session["incorrect_answers"] += 1
            db.execute("INSERT INTO progress (result) VALUES (?)", "Incorrect")
            progress = db.execute("SELECT result FROM progress")
            return render_template("exercise.html", number1 = session["number1"], number2=session ["number2"], message=session["message"], progress=progress, medal=session["medal"])
        # We get the user's answer
        answer = int(request.form.get("answer"))
        # We recover the correct result, which was previously stored in the session
        result_true = session["result_true"]
        # Once we have the current correct result, we store it in a new variable in session, to later show the user if their answer is incorrect. Since result_true will soon be overwritten, we need to perform this action now.
        session["previous_result"] = session["result_true"]
        # Now, we check if the user's answer matches the correct result. Then, we send a message and register the result in history
        if answer == result_true:
            session["message"] = "Correct!"
            number_correct = db.execute("SELECT number_correct FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
            number_correct = number_correct[0]['number_correct'] + 1
            db.execute("UPDATE history SET number_correct = ? WHERE users_id = ? AND wdate = ?", number_correct, session["user_id"], current_date)
            # We also update the counter which will end the exercise
            session["correct_answers"] += 1
        else:
            session["message"] = "Incorrect!"
            number_incorrect = db.execute("SELECT number_incorrect FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
            number_incorrect = number_incorrect[0]['number_incorrect'] + 1
            db.execute("UPDATE history SET number_incorrect = ? WHERE users_id = ? AND wdate = ?", number_incorrect, session["user_id"], current_date)
            # Same as before, we update the counter which will end the exercise
            session["incorrect_answers"] += 1
            # If the answer is incorrect, we also create a table to register the numbers in the question, so we can keep a record for future exercises and focus on errors
            exercise_number = db.execute("SELECT exercise_number FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
            db.execute("CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY AUTOINCREMENT, users_id INTEGER NOT NULL, wdate DATE NOT NULL, session_id INTEGER NOT NULL DEFAULT 0, exercise_number INTEGER NOT NULL, number_1 INTEGER NOT NULL DEFAULT 0, number_2 INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (users_id) REFERENCES users(id))")
            # We create a couple of variables which will keep track of the session, the session number will change every day
            session_id = db.execute("SELECT session_id FROM errors WHERE users_id = ? ORDER BY id DESC LIMIT 1", session["user_id"])
            last_session = db.execute("SELECT wdate FROM errors WHERE users_id = ? ORDER BY id DESC LIMIT 1", session["user_id"])
            # Then we check if the date from the last session matches our current date. If the dates are differente, we increase by one the session number.
            if session_id and session_id[0]["session_id"]:
                if last_session[0]["wdate"] != current_date_str:
                    updated_session_id = session_id[0]["session_id"] + 1
                else:
                    updated_session_id = session_id[0]["session_id"]
            # If this is the user's first error, we asign 1 to the session number
            else:
                updated_session_id = 1
            db.execute("INSERT INTO errors (users_id, wdate, session_id, exercise_number, number_1, number_2) VALUES (?, ? , ?, ?, ?, ?)", session["user_id"], current_date, updated_session_id, exercise_number[0]['exercise_number'], session["number1"], session["number2"])
    # This only happens before the user submits their first answer (On the first question)
    else:
        # We create a table (if it doesn´t exist) to register the user's amount of right and wrong answers
        db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, users_id INTEGER NOT NULL, wdate DATE NOT NULL, exercise_number INTEGER NOT NULL DEFAULT 0, number_correct INTEGER NOT NULL DEFAULT 0, number_incorrect INTEGER NOT NULL DEFAULT 0, villains_defeated INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (users_id) REFERENCES users(id))")
        exercise_number = db.execute("SELECT exercise_number FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
        exercise_number = exercise_number[0]['exercise_number'] + 1
        db.execute("UPDATE history SET exercise_number = ? WHERE users_id = ? AND wdate = ?", exercise_number, session["user_id"], current_date)
        session["correct_answers"] = 0
        session["incorrect_answers"] = 0
    # Since at the start of a session there won't be values stored for number1 and number2, in order to avoid an error, we have to give them a value
    if "number1" not in session or "number2" not in session:
        session["number1"] = None
        session["number2"] = None
    # Now we choose a random set of numbers. To avoid repeating the same operation in a row, we use a while loop with a maximum number of attempts (to avoid an infinite loop)
    max_attempts = 10
    number1, number2, result_true = generate_numbers()
    attempts = 0
    while((number1 == session["number1"] and number2 == session["number2"]) or (number1 == session["number2"] and number2 == session["number1"])):
        number1, number2, result_true = generate_numbers()
        attempts += 1
        if (attempts >= max_attempts):
            break
    # Once we have our numbers, we check that the exercise is still going
    session["result_true"] = result_true
    session["number1"] = number1
    session["number2"] = number2
    # Once we reach the end of the exercise, we provide a recap with options to continue or quit
    if (session["correct_answers"] + session["incorrect_answers"] >= 10):
        return redirect("/recap")
    elif (session["correct_answers"] + session["incorrect_answers"] <= 0):
        return render_template("exercise.html", number1=number1, number2=number2, medal=session["medal"])
    else:
        return redirect("/answer")


# This is the function that provides the two random numbers and the correct result
def generate_numbers():
    # First of all, we need to create the table errors if it doesn't yet exist or we'll get an error when we execute the following line
    db.execute("CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY AUTOINCREMENT, users_id INTEGER NOT NULL, wdate DATE NOT NULL, session_id INTEGER NOT NULL DEFAULT 0, exercise_number INTEGER NOT NULL, number_1 INTEGER NOT NULL DEFAULT 0, number_2 INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (users_id) REFERENCES users(id))")
    # We make a list with every wrong number (the numbers in each wrong answer) from the last three sessions. We also limit the results to the current month.
    wrong_numbers = db.execute("SELECT number_1, number_2 FROM errors WHERE date(wdate) >= date('now', '-1 month') AND users_id = ? ORDER BY wdate DESC, session_id DESC LIMIT 3", session["user_id"])
    wrong_numbers_list = [result["number_1"] for result in wrong_numbers] + [result["number_2"] for result in wrong_numbers]
    # We also select 4 random numbers from 0 to 10
    additional_numbers = []
    for i in range(4):
        number = random.randrange(0, 10)
        additional_numbers.append(number)
    combined_numbers = additional_numbers
    # Then we asign weights to those 4 random numbers (their chances of being picked)
    weights_combined_numbers = [0.15, 0.15, 0.15, 0.15]
    # We also asign a weight for each of the numbers in the wrong numbers list (Only if wrong numbers exists and it's not empty)
    if wrong_numbers and len(wrong_numbers) > 0:
        weights_wrong_numbers_list = [0.4 / len(wrong_numbers_list)] * len(wrong_numbers_list)
        # Then we add the wrong numbers list to the random numbers only if the list exists and it's not empty
        combined_numbers += wrong_numbers_list
        weights = weights_combined_numbers + weights_wrong_numbers_list
    else:
        weights = weights_combined_numbers
    # After we have all the numbers (list + random), we select two which, along with their product, will be sent to the user as a new question
    random_numbers = random.choices(combined_numbers, weights=weights, k=2)
    number1 = random_numbers[0]
    number2 = random_numbers[1]
    result_true = number1 * number2
    return number1, number2, result_true

@app.route("/v_intro", methods=["GET", "POST"])
@login_required
def v_intro():
    # We create the table progress to show the user how many answers were correct/incorrect
    # However, first, we have to delete the previous table, if it exists
    db.execute("DROP TABLE IF EXISTS progress")
    db.execute("CREATE TABLE IF NOT EXISTS progress (question_number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, result TEXT NOT NULL)")
    # Once the user presses the "next" button, the exercise begins
    if request.method == "POST":
        return redirect("/exercise")
    # This happens before. A Random villain is selected, as well as a random opening phrase.
    else:
        # We Select a random villain for the user to face
        chosen_villain = random.choice(list(VILLAIN_LIST.keys()))
        # The selection is stored in session for further use
        session["chosen_villain"] = chosen_villain
        # Then, we select a random opening phrase for the selected villain
        opening_phrase = random.choice(VILLAIN_LIST[chosen_villain]["opening_phrases"])
        return render_template ("v_intro.html", chosen_villain=chosen_villain, opening_phrase=opening_phrase)

@app.route("/what_to_do")
@login_required
def what_to_do():
    # Shows the user how to solve the exercises.
    return render_template("what_to_do.html")

@app.route("/history")
@login_required
def history():
    # Show history of transactions
    history = db.execute("SELECT * FROM history WHERE users_id = ?", session["user_id"])
    return render_template("history.html", history=history)

@app.route("/answer", methods=["GET", "POST"])
@login_required
def answer():
    if "chosen_answer" not in session:
        session["chosen_answer"] = None
    # The user gets a new question after they click the "Next" button
    if request.method == "POST":
        db.execute("INSERT INTO progress (result) VALUES (?)", session["message"])
        progress = db.execute("SELECT result FROM progress")
        return render_template("exercise.html", number1 = session["number1"], number2=session["number2"], message=session["message"], progress=progress, medal=session["medal"])
    # If the user gets to answer through a GET method, a quote from the villain gets chosen randomly. The quote should reflect wether the user answered right or wrong
    else:
        chosen_villain = session ["chosen_villain"]
        # We check the same quote doesn't show twice in a row through a while loop
        while True:
            if session["message"] == "Correct!":
                chosen_answer = random.choice(VILLAIN_LIST[chosen_villain]["answer_is_correct"])
            else:
                chosen_answer = random.choice(VILLAIN_LIST[chosen_villain]["answer_is_wrong"])
            # Once the random quote is different from the one stored in session, we break the loop
            if session["chosen_answer"] != chosen_answer:
                break
    session["chosen_answer"] = chosen_answer
    return render_template("answer.html", message=session["message"], chosen_villain=chosen_villain, chosen_answer=chosen_answer, previous_result=session["previous_result"])

@app.route("/recap", methods=["GET", "POST"])
@login_required
def recap():
    current_date = date.today()
    chosen_villain = session["chosen_villain"]
    villains_defeated = db.execute("SELECT villains_defeated FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
    # We reset the counters to 0 before starting a new exercise
    if request.method == "POST":
        session["correct_answers"] = 0
        session["incorrect_answers"] = 0
        if str(villains_defeated[0]["villains_defeated"]) in ["1", "2", "3", "5"]:
            print("bien")
            return redirect ("/medal")
        else:
            return redirect("/v_intro")
    # Once the exercise is finished, the user gets a screen telling them if they beat the villain or not
    else:
        if session["correct_answers"] > session["incorrect_answers"]:
            result = "You win"
            # The user also gets a random statement from the villain, which will change according to the exercise's result
            chosen_answer = random.choice(VILLAIN_LIST[chosen_villain]["defeat"])
            # In order to award the user with a medal for beating the villain, we have to update the counter in the history table
            villains_defeated = villains_defeated[0]["villains_defeated"] + 1
            db.execute("UPDATE history SET villains_defeated = ? WHERE users_id = ? AND wdate = ?", villains_defeated, session["user_id"], current_date)
        else:
            result = "You lose"
            chosen_answer = random.choice(VILLAIN_LIST[chosen_villain]["victory"])
        return render_template("recap.html", result = result, chosen_villain = chosen_villain, chosen_answer = chosen_answer)

@app.route("/medal")
@login_required
def medal():
        current_date = date.today()
        result = db.execute("SELECT villains_defeated FROM history WHERE users_id = ? AND wdate = ?", session["user_id"], current_date)
        if result:
            villains_defeated = result[0]["villains_defeated"]
            if str(villains_defeated) == "1":
                session["medal"] = "bronze"
            elif str(villains_defeated) == "2":
                session["medal"] = "silver"
            elif str(villains_defeated) == "3":
                session["medal"] = "gold"
            else:
                session["medal"] = "super-rare platinum"
        return render_template ("medal.html", medal=session["medal"])

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT NOT NULL, hash TEXT NOT NULL)")
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        # Ensure confirmation is the same as the password
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and confirmation don't match", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Check if username exists and password is correct
        if len(rows) != 0:
            return apology("username already taken", 400)

        # Hash the user's password
        hash = generate_password_hash(request.form.get("password"))

        # Add the user's entry into the database
        username = request.form.get("username")

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        return redirect("/")

    else:
        return render_template("register.html")

