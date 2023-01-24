from flask import Blueprint, render_template, request, flash, redirect, session, url_for, jsonify
import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

auth = Blueprint('auth', __name__)

def auth_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            return jsonify({'message': 'Authorization header is missing'}), 401

        if not is_valid_token(auth_token):
            return jsonify({'message': 'Invalid token'}), 401
        
        return func(*args, **kwargs)
    return wrapper

def is_valid_token(token):
    # check if token is valid
    # return boolean value
    pass

def login_required(func):
    @wraps(func)
    def wrap():
        if "username" not in session:
            flash("You need to be logged in!", category="error")
            return redirect('/login')
        return func()
    return wrap

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_id = request.form.get('user_id')
               
        conn = sqlite3.connect('test.db', timeout=10)
        c = conn.cursor()
        c.execute("SELECT * FROM User WHERE Username=?", (username,))
        user = c.fetchone()
        c.close()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["username"] = username

            flash("You are logged in!", category="success")
            return redirect("/login")
        else:
            flash("Incorrect password or username", category="error")
            return render_template("login.html")
    else:
        return render_template("login.html")

@auth.route('/')
def home():
    return render_template("home.html")

@auth.route('/logout')
def logout():
    if "username" in session:
        session.pop("username",None)
        flash("You have been logged out", category="error")
    
    return redirect("/")
  

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        if len(username) < 4:
            flash('Username must be more than 4 characters long', category='error')
        elif len(password) < 4:
            flash('Password must be more than 4 characters long', category='error')
        else:
            conn = sqlite3.connect('test.db', timeout=10)
            c = conn.cursor()
            c.execute("INSERT INTO User (Username, Password) VALUES (?,?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash('Account created!', category='success')
    return render_template("sign_up.html")


@auth.route('/datadump', methods=['GET', 'POST'])
@login_required
def datadump():
    conn = sqlite3.connect('test.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT Companies.CompanyName, Analysis.FairPrice, Analysis.CurrentPrice, Analysis.Currency, Stock.Dividend, Stock.DividendGrowthRate, Stock.HurdleRate, Stock.DividendDate, Stock.CurrentDate FROM Analysis JOIN Companies ON Analysis.Company_id = Companies.Company_id JOIN Stock ON Analysis.Company_id = Stock.Company_id ") 
    datadump = c.fetchall()
    print(datadump)
    column_names = [description[0] for description in c.description]
    conn.close()
    return render_template("datadump.html", datadump=datadump, column_names=column_names)


if not os.path.exists("/website/static/"):
    os.makedirs("/website/static/")

@auth.route('/statistics', methods=['GET', 'POST'])
@login_required
def statistics():
    conn = sqlite3.connect('test.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM Analysis")
    statistics_inputs = c.fetchall()
    INPUTY = statistics_inputs[0][0]
    print(INPUTY)
    c.execute("SELECT Currency, ROUND(SUM(ABS(CurrentPrice-FairPrice)),2) FROM Analysis WHERE Currency IS NOT Null GROUP BY Currency ORDER BY Currency")
    value_diff = c.fetchall()
    print(value_diff)
    graph_data = pd.read_sql_query('SELECT Currency, count(*) as Number_of_calculations FROM Analysis where currency is not null group by currency', conn)
    graph = graph_data.plot.bar(x = 'Currency').figure
    graph.savefig('/website/static/graph.png')
    c.close()
    conn.close()
    return render_template("statistics.html", INPUTY=INPUTY, value_diff=value_diff)


@auth.route('/gordon_result', methods=['GET'])
def gordon_result():
    return render_template("gordon_result.html")

def get_max_company_id():
    conn = sqlite3.connect('test.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT MAX(Company_id) FROM Stock")
    max_company_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return max_company_id if max_company_id is not None else 0

def get_max_input_id():
    conn = sqlite3.connect('test.db', timeout=10)
    c = conn.cursor()
    c.execute("SELECT MAX(Input_id) FROM Analysis")
    max_input_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return max_input_id if max_input_id is not None else 0
           
@auth.route('/gordongrowthmodel', methods=['GET', 'POST'])
@login_required
def Gordon_growth_model():
    if request.method == 'POST':
        dividend = request.form.get('dividend')
        growth_rate = request.form.get('growth_rate')
        discount_rate = request.form.get('discount_rate')
        companyname = request.form.get('companyname')
        current_price = request.form.get('current_price')
        currency = request.form.get('currency')
        dividend_date = request.form.get('dividend_date')
        current_date = request.form.get('current_date')
        conservative_approach = request.form.get('conservative_approach')
        aggresive_approach = request.form.get('aggresive_approach')
        neutral_approach = request.form.get('aggresive_approach')
        company_id = request.form.get('company_id')
        input_id = request.form.get('input_id')
        if not all([dividend, growth_rate, discount_rate, companyname, current_price, currency, dividend_date, current_date]):
            flash('Please fill all the fields!', category='error')
            return redirect(url_for('auth.Gordon_growth_model'))
        if dividend and growth_rate and discount_rate:
            if float(discount_rate) > float(growth_rate):
                fairprice = round((float(dividend) * (1 + float(growth_rate))) / (float(discount_rate) - float(growth_rate)),4)
                company_id = get_max_company_id() + 1
                input_id = get_max_input_id() + 1 
                #conservative approach
                if float(current_price) < 0.8 * float(fairprice):
                    conservative_approach = "buy"
                elif float(current_price) > 1.2 * float(fairprice):
                    conservative_approach = "sell"
                else:
                    conservative_approach = "hold"
                # neutral approach
                if float(current_price) < 0.9 * float(fairprice):
                    neutral_approach = "buy"
                elif float(current_price) > 1.1 * float(fairprice):
                    neutral_approach = "sell"
                else:
                    neutral_approach = "hold"     
                # aggresive approach
                if float(current_price) < 0.95 * float(fairprice):
                    aggresive_approach = "buy"
                elif float(current_price) > 1.05 * float(fairprice):
                    aggresive_approach = "sell"
                else:
                    aggresive_approach = "hold"  
                conn = sqlite3.connect('test.db')
                c = conn.cursor()                
                c.execute("INSERT INTO Companies (CompanyName) VALUES (?)", (companyname,))
                c.execute("INSERT INTO Stock (Company_id, Dividend, DividendDate, DividendGrowthRate, CurrentDate, HurdleRate, CurrentPrice, Currency) VALUES (?,?,?,?,?,?,?,?)", (company_id, dividend, dividend_date, growth_rate, current_date, discount_rate, current_price, currency,))
                c.execute("INSERT INTO Analysis (Company_id, CurrentPrice, FairPrice, Currency, Input_id) VALUES (?,?,?,?,?)", (company_id, current_price, fairprice, currency, input_id,))
                c.close()
                conn.commit()
                conn.close()                      
                return render_template("gordon_result.html", fairprice=fairprice, conservative_approach=conservative_approach, aggresive_approach=aggresive_approach, neutral_approach= neutral_approach)
            else:
                flash('Discount rate must be greater than growth rate', category='error')
                return redirect(url_for('auth.Gordon_growth_model'))                
        else:
            flash('Please fill all the fields', category='error')
            return redirect(url_for('auth.Gordon_growth_model'))
    return render_template("Gordon_growth_model.html")







   
    
    
 


