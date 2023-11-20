
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


# Test default login information
username = "Pixelte"
name = "James"


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.75.94.195/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.75.94.195/proj1part2"
#
DATABASEURI = "postgresql://agw2135:155539@34.74.171.121/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
conn = engine.connect()

# The string needs to be wrapped around text()

conn.execute(text("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);"""))
conn.execute(text("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');"""))

# To make the queries run, we need to add this commit line

conn.commit() 

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/2.0.x/quickstart/?highlight=routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

def loginPage(error=False):
  context = dict(error="Invalid login information") if error else dict(error = "")
    
  return render_template("login.html", **context)

@app.route('/')
def index():
  return loginPage()

@app.route('/login', methods=['POST'])
def login():
  username = request.form['username']
  password = request.form['password']
  
  cursor = g.conn.execute(text("SELECT * FROM account WHERE username = :username AND password = :password"), {"username":username, "password":password})
  
  user = None
  for result in cursor:
    user = result
  
  cursor.close()
  
  if user == None:
    return loginPage(error=True)
  else:
    username = user[0]
    name = user[2] if user[2] != None else username
    return redirect('/home/')
    
@app.route('/home/')
def home():
  
  context = dict(username=username, name=name)
  
  cursor = g.conn.execute(text("SELECT region FROM game"))
  games = []
  for result in cursor:
    games.append(result[0])
  cursor.close()
  
  context["games"] = games
  
  return render_template("home.html", **context)

@app.route('/region', methods=['POST'])
def region():
  region = request.form['region'] if "region" in request.form else None
  if region == None:
    return redirect('/home/')

  cursor = g.conn.execute(text("SELECT name FROM trainer WHERE region = :region"), {"region":region})
  trainers = []
  for result in cursor:
    trainers.append(result[0])
  cursor.close()

  cursor = g.conn.execute(text("SELECT name, type, badge_name FROM gym WHERE region = :region"), {"region":region})
  gyms = []
  for result in cursor:
    gyms.append((result[0], result[1][0].upper() + result[1][1:], result[2]))
  cursor.close()

  context = dict(username=username, name=name, trainers=trainers, gyms=gyms)

  return render_template("region.html", **context)

@app.route('/gym', methods=['POST'])
def gym():
  gym_id = request.form['gym'] if "gym" in request.form else None
  if gym_id == None:
    return redirect('/home/')
  gym_id = gym_id.split('|')
  gym_name = ""
  for x in gym_id[:-1]:
    gym_name += x
  gym_type = gym_id[-1]
  gym_type = gym_type.lower()
  
  cursor = g.conn.execute(text("SELECT name FROM trainer WHERE gym_name = :gym_name AND gym_type = :gym_type"), {"gym_name":gym_name, "gym_type":gym_type})
  trainers = []
  for result in cursor:
    trainers.append(result[0])
  cursor.close()
  context = dict(username=username, name=name, trainers=trainers)
  if (len(trainers) == 1):
    return redirect('/trainer/'+trainers[0])
  
  return render_template("gym.html", **context)

@app.route('/trainer/<trainer_name>')
def trainer(trainer_name):
  cursor = g.conn.execute(text("SELECT * FROM trainer WHERE name = :trainer_name"), {"trainer_name":trainer_name})
  trainer = None
  for result in cursor:
    trainer = result
  cursor.close()
  
  cursor = g.conn.execute(text("SELECT P.pokedex_number, P.name, P.attack, P.defense, P.hp, P.sp_attack, P.sp_defense, P.speed, P.weight, P.generation, P.is_legendary FROM pokemon P, trainer_owns T WHERE T.trainer_name = :trainer_name AND T.trainer_region = :trainer_region AND T.pokedex_number = P.pokedex_number"), {"trainer_name":trainer[0], "trainer_region":trainer[3]})
  pokemon = []
  for result in cursor:
    pokemon.append(result)
  cursor.close()
    
  context = dict(username=username, name=name, trainer=trainer, pokemon=pokemon)
  
  return render_template("trainer.html", **context)

@app.route('/trainer-name/', methods=['POST'])
def trainer_name():
  trainer_name = request.form['name'] if "name" in request.form else None
  if trainer_name == None:
    return redirect('/home/')
  return redirect('/trainer-search/'+trainer_name)

@app.route('/trainer-search/<trainer_name>')
def trainer_search(trainer_name):
  cursor = g.conn.execute(text("SELECT name FROM trainer WHERE name LIKE :trainer_name"), {"trainer_name":trainer_name+"%"})
  trainers = []
  for result in cursor:
    trainers.append(result[0])
  cursor.close()
  context = dict(username=username, name=name, trainers=trainers)

  return render_template("trainer-search.html", **context)

  
@app.route('/test')
def test():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: https://flask.palletsprojects.com/en/2.0.x/api/?highlight=incoming%20request%20data

  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)


  #
  # example of a database query 
  #
  cursor = g.conn.execute(text("SELECT name FROM test"))
  g.conn.commit()

  # 2 ways to get results

  # Indexing result by column number
  names = []
  for result in cursor:
    names.append(result[0])  

  # Indexing result by column name
  # names = []
  # results = cursor.mappings().all()
  # for result in results:
  #   names.append(result["name"])
  cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #
  #     # creates a <div> tag for each element in data
  #     # will print:
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  context = dict(data = names)


  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at:
#
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#
@app.route('/another')
def another():
  return render_template("another.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add(): 
  name = request.form['name']
  params_dict = {"name":name}
  g.conn.execute(text('INSERT INTO test(name) VALUES (:name)'), params_dict)
  g.conn.commit()
  return redirect('/test')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
