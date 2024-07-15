import os
from flask import Flask, render_template, request, redirect, url_for, make_response
from googlesearch import search
from fuzzywuzzy import process
from bs4 import BeautifulSoup
import requests
import json
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

app = Flask(__name__)

responses = {}
history = [] 
x = []
y = []
def summarize_text(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 2) 
    summarized_text = ""
    for sentence in summary:
        summarized_text += str(sentence) + "\n"
    return summarized_text


def read_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = ' '.join([p.get_text() for p in soup.find_all('p')])
        return text.strip()
    except Exception as e:
        print("Error:", e)
        return None

def generate_plot(x, y):
    plt.plot(x, y)
    plt.xlabel('Days')
    plt.ylabel('StudyHour')
    plt.title('Progress')


    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

   
    plot_data = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return plot_data

@app.route('/update_progress', methods=['POST'])
def update_progress():
    
    progress_value = float(request.form.get('progress_data'))

  
    x.append(len(x) + 1) 
    y.append(progress_value)


    plot_data = generate_plot(x, y)

    username = request.cookies.get('username')


    save_plot_data(username, plot_data)

    return performance()

def save_plot_data(username, plot_data):
    user_data_file = f'{username}_data.json'
    user_data = read_json(user_data_file)
    user_data['plot_data'] = plot_data
    with open(user_data_file, 'w') as file:
        json.dump(user_data, file)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        login_credentials = read_json('login_credentials.json')
        if username in login_credentials and login_credentials[username] == password:
     
            response = make_response(redirect(url_for('home')))
            response.set_cookie('username', username)
            return response
        else:

            return render_template('login_page.html', message='Incorrect username or password.')
    else:
        return render_template('login_page.html')

@app.route('/register.html', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
   
        with open('login_credentials.json', 'r') as f:
            login_credentials = json.load(f)
        
        if username in login_credentials:
            return render_template('register.html', message="This username already exists")
        else:
            login_credentials[username] = password
            with open('login_credentials.json', 'w') as f:
                json.dump(login_credentials, f)
            
  
            user_data_file = f'{username}_data.json'
            with open(user_data_file, 'w') as f:
                json.dump({}, f)
                
            return redirect(url_for('home'))
    else:
        return render_template('register.html')
    
@app.route('/personal_assistant.html', methods=['GET', 'POST'])
def chatbot():
    global history  


    username = request.cookies.get('username')

    if request.method == 'POST':
        user_input = request.form['user_input']
        response = chatbot_response(user_input)

       
        save_user_interaction(username, user_input, response)

        plot_data = generate_plot(x, y)
       
        history.append({'user_input': user_input, 'response': response})
        return render_template('personal_assistant.html', user_input=user_input, response=response, plot_data=plot_data, history=history)
    else:
      
        user_data = load_user_data(username)
        history = user_data.get('interactions', [])
        progress_data = user_data.get('progress', [])
        return render_template('personal_assistant.html', history=history, progress_data=progress_data)

def save_user_interaction(username, user_input, response):
    user_data_file = f'{username}_data.json'
    user_data = read_json(user_data_file)
    user_data.setdefault('interactions', []).append({'user_input': user_input, 'response': response})
    with open(user_data_file, 'w') as file:
        json.dump(user_data, file)

def load_user_data(username):
    user_data_file = f'{username}_data.json'
    return read_json(user_data_file)

@app.route('/performance.html')
def performance():
 
    username = request.cookies.get('username')

    
    plot_data = load_plot_data(username)

    return render_template('performance.html', plot_data=plot_data)

def load_plot_data(username):
    user_data_file = f'{username}_data.json'
    user_data = read_json(user_data_file)
    return user_data.get('plot_data', None)

@app.route('/whiteboard.html')
def whiteboard():
    return render_template('whiteboard.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        username = request.cookies.get('username')
        name = request.form.get('name')
        class_name = request.form.get('class')

       
        user_data_file = f'{username}_data.json'
        user_data = read_json(user_data_file)

    
        user_data['name'] = name
        user_data['class'] = class_name

       
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f)

     
        return redirect(url_for('home'))
    else:
       
        username = request.cookies.get('username')
        user_data_file = f'{username}_data.json'
        profile_data = read_json(user_data_file)
          
        return render_template('HOME_page.html', profile_data=profile_data)





def chatbot_response(user_input):
    user_input = user_input.lower().strip("?.,!")
    if "qsfm" in user_input:
        search_results = list(search(user_input, num=3, stop=3, pause=2,safe=True))
        if search_results:
            search_summaries = []
            for url in search_results:
                text = extract_text_from_url(url)
                if text:
                    search_summaries.append(text[:500])
            if search_summaries:
                return "Here are summaries of the search results:\n" + '\n'.join(search_summaries)
            else:
                return "I'm sorry, I couldn't find any relevant information."
        else:
            return "I'm sorry, I couldn't find any relevant information."
    if "summarize" in user_input or "summary" in user_input:
       
       return summarize_text(user_input)

    


    matched_key, similarity_score = process.extractOne(user_input, responses.keys())
    if similarity_score < 65: 
        return "I'm sorry, I don't understand."

    response = responses[matched_key].replace(".", "<br>")
    return response

if __name__ == '__main__':
    USER_DATA_FILE = 'USER_DATA.json'
    user_data = read_json(USER_DATA_FILE)
    responses.update(user_data)
    
    LOGIN_CREDENTIALS_FILE = 'login_credentials.json'
    login_credentials = read_json(LOGIN_CREDENTIALS_FILE)
    
    for username in login_credentials.keys():
        user_data_file = f'{username}_data.json'
        if not os.path.exists(user_data_file):
            
            with open(user_data_file, 'w') as f:
                json.dump({}, f)
    
    app.run(debug=True)
