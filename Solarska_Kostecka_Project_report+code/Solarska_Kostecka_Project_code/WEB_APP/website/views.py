from flask import Blueprint, render_template
import sqlite3

views = Blueprint('views', __name__)

@views.route('/')
def home():
    return render_template("home.html")


