
import os
from flask import Flask, render_template, request, redirect, url_for, send_file
app = Flask(__name__)

@app.route('/')
def main():
   return render_template('index.html')
@app.route('/login')
def login():
    return render_template('login.html')
@app.route('/userDetail')
def userDetail():
    return render_template('userDetail.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1')
