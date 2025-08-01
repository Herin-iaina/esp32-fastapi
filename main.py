# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, request, send_from_directory, url_for, redirect
import json
from apps import post_temp_humidity
import datetime 
from apps import config_database
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import os
from datetime import timedelta
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity


app = Flask(__name__)

# Une liste de dictionnaires de clés API autorisées
api_keys = [
    {'key': 'votre_cle_api_1'},
    {'key': 'votre_cle_api_2'},
    {'key': 'Votre_Cle_API'},
    
]

# Configuration de JWT
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)

@app.route("/")
def hello():
    # return "hello"
    return render_template('main.html')


@app.route("/values" , methods=['POST'])
def data__():
    data = request.json
     # Vérifier si la clé API est valide

    humidity = 0
    temperature = 0
    average_temperature = 0
    average_humidity = 0
    num_failed_sensors = 0
    sensor_name = ""
    fan_status = ""
    humidifier_status = ""
    date_serveur = datetime.datetime.now()  

    result = False


    api_key = request.headers.get('X-API-KEY')
    # print(api_key)


    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized


    if not any(api['key'] == api_key for api in api_keys):
        return jsonify({'message': 'Clé API non valide'}), 401  # Non autorisé
    
    try : 
        # Retrieve other values
        average_temperature = float(data['average_temperature'])
        average_humidity = float(data['average_humidity'])
        fan_status = data['fan_status']
        humidifier_status = data['humidifier_status']
        num_failed_sensors = int(data['numFailedSensors'])
        
    except Exception : 
            return jsonify({'message': 'Missing data'}), 400  # Mauvaise requête
    
    # Vérifier si les données de température et d'humidité sont présentes
    for sensor_name, sensor_data in data.items():
    # Check if it's a sensor data
        if sensor_name.startswith('sensor'):
            # Retrieve humidity and temperature values
            # Vérifier si les données de température et d'humidité sont présentes
            try : 
                humidity = float(sensor_data['humidity'])
                temperature = float(sensor_data['temperature'])
            except Exception : 
                return jsonify({'message': 'Missing data'}), 406  # Mauvaise requête
            
            data_to_insert = {
            'sensor': sensor_name,
            'temperature': temperature,
            'humidity': humidity,
            'average_humidity': average_humidity,
            'average_temperature': average_temperature,
            'fan_status': fan_status,
            'humidifier_status': humidifier_status,
            'numfailedsensors': num_failed_sensors,
            'date_serveur': date_serveur
            }
            # Ajouter les données dans la base
            result = post_temp_humidity.add_data(data_to_insert)     
    
    
    if result == True : 
        config_database.close_db_connection()
        return jsonify({'message': 'Data received successfully'}), 200  # Succès
    else :
        return jsonify({'message': 'Internal Server Error'}),500 # Erreur


@app.route("/getdata", methods=['GET'])
def get_data():
    api_key = request.headers.get('X-API-KEY')
    print(api_key)
    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized

    fan_humidity_status = post_temp_humidity.get_last_data()
    fan_status = fan_humidity_status[0]  # Utiliser l'indice 0 pour la première valeur
    humidifier_status = fan_humidity_status[1]  # Utiliser l'indice 1 pour la deuxième valeur
    motor_status = post_temp_humidity.post_stepper_status()

    data_to_send = {
        'FAN': fan_status,
        'Humidity': humidifier_status,
        'Motor': motor_status
    }
    return jsonify(data_to_send), 202

@app.route("/WeatherData", methods= ['GET'])
def WeatherData() :
    # results = {
    # "temperature": 30.5,
    # "humidity": 60,
    # "average_temperature": 33.8,
    # "average_humidity": 67
    # }

    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized
    
    
    Weather_Data = post_temp_humidity.get_weather_data()
    
    return jsonify(Weather_Data),202
    

@app.route("/WeatherDF", methods=['GET'])
def get_dataWeatherDatafram() :
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized
    
    Weather_DF = post_temp_humidity.get_data_average()

    return jsonify(Weather_DF), 202



@app.route("/alldata", methods=['GET'])
def get_all_data() : 
    

    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized
    
    # print(request.url)
    
    def formater_date(date_str):
        try:
            # Convertir la chaîne en objet datetime
            datetime_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            # Formater l'objet datetime dans le format souhaité
            return datetime_obj.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            # Si le format ne correspond pas, essayer sans les secondes
            try:
                datetime_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                return datetime_obj.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    datetime_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M")
                    return datetime_obj.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        datetime_obj = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        return datetime_obj.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        return "Format de date invalide"
            

    if 'date_int' not in request.args or 'date_end' not in request.args:
        # return jsonify({'message': 'Missing parameters'}), 400  # Bad Request
        results = post_temp_humidity.get_all_data(False,False)
        return jsonify(results), 202
    
    else:  
        date_int = request.args['date_int']
        date_end = request.args['date_end']

        # print(date_int,date_end)

        time_delta = datetime.timedelta(hours=0)

        if ':' not in date_int:  # Vérifie si l'heure est spécifiée
            date_int = date_int + " 00:00"
            # print(date_int)

        if ':' not in date_end:  # Vérifie si l'heure est spécifiée
            date_end = date_end + " 00:00"

        try : 
            date_int = formater_date(date_int)
            date_end = formater_date(date_end)
            print(date_int,date_end)
            # # return jsonify(date_end), 202
            results = post_temp_humidity.get_all_data(date_int,date_end)
            return jsonify(results), 202
        
        except Exception :
            return jsonify("Internal serveur error"), 500
        
@app.route("/isrunning", methods=['GET','POST'])
def getinitialdate() :
    if request.method == 'POST':
        # Vérifier si les données sont envoyées en JSON
        if request.is_json:
            data = request.get_json()
            dateinit = data.get('date')
        else:
            # Sinon, traiter comme des données de formulaire
            dateinit = request.form.get('date')
        print(dateinit,"date")

        if dateinit :
            dateformated = 0

            def checkdate():
                try:
                # Convertir la chaîne en objet datetime
                    datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d %H:%M")
                    except ValueError:
                        try:
                            datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%dT%H:%M")
                        except ValueError:
                            try:
                                datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%dT%H:%M:%S.%fZ")
                            except ValueError:
                                try:
                                    datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d")
                                except ValueError :
                                    try:
                                        datetime_obj = datetime.datetime.strptime(dateinit, '%d/%m/%Y %H:%M')
                                    except ValueError:
                                        try :
                                            datetime_obj = datetime.datetime.strptime(dateinit, "%d/%m/%Y")
                                        except ValueError :
                                        # Si une ValueError est levée, ce n'est pas une date valide
                                            return None
                # Formater l'objet datetime dans le format souhaité
                return datetime_obj.strftime("%Y-%m-%d")
                                                                  
            dateformated = checkdate()
            is_ok = post_temp_humidity.getdateinit(dateformated)
            return jsonify(is_ok), 202
        else : 
            return jsonify("Veillez renseigner la date"), 202
    else : 
        print ("NOK")

@app.route("/parameter", methods=['GET', 'POST'])
def create_parameter():

    def fromateddate(dateinit):
        try:
            # Convertir la chaîne en objet datetime
            datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%dT%H:%M")
                except ValueError:
                    try:
                        datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError:
                        try:
                            datetime_obj = datetime.datetime.strptime(dateinit, "%Y-%m-%d")
                        except ValueError :
                            try:
                                datetime_obj = datetime.datetime.strptime(dateinit, '%d/%m/%Y %H:%M')
                            except ValueError:
                                try :
                                    datetime_obj = datetime.datetime.strptime(dateinit, "%d/%m/%Y")
                                except ValueError :
                                    # Si une ValueError est levée, ce n'est pas une date valide
                                    return dateinit
                                    # return None
        # Formater l'objet datetime dans le format souhaité
        return datetime_obj.strftime("%Y-%m-%d %H:%M")

    api_key = request.headers.get('X-API-KEY')

    if not api_key:
        return jsonify({'message': 'API key missing'}), 401  # Unauthorized

    if not any(api['key'] == api_key for api in api_keys):
        return jsonify({'message': 'Clé API non valide'}), 401  # Unauthorized

    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                # print(data, 1)
            else:
                data = request.form
                # print(data, 2)

            temperature = float(data.get('temperature'))
            humidity = float(data.get('humidity'))
            start_date = str(data.get('start_date'))
            stat_stepper = data.get('stat_stepper')
            number_stepper = data.get('number_stepper')
            espece = data.get('espece')
            timetoclose =  data.get('timetoclose')

            # print(temperature,humidity,start_date,stat_stepper,number_stepper,espece,"ererererrerre")
            print(type(start_date))

            if not all([temperature, humidity, start_date, stat_stepper, number_stepper, espece]):
                raise ValueError("Missing data")

        except (TypeError, ValueError) as e:
            return jsonify({'message': 'Invalid or missing data'}), 400  # Bad Request

        espece_mapping = {
            "option1": "poule",
            "option2": "canne",
            "option3": "oie",
            "option4": "caille",
            "option5": "other"
        }

        remaindate = {
            "poule" : 21,
            "canne" : 28,
            "oie" : 30,
            "caille" : 18,
            "other" : timetoclose
        }

        espece_value = espece_mapping.keys()
        timetoclose_v = remaindate.keys()

        if espece not in espece_value:
            return jsonify({'message': 'Espece non reconnue'}), 401  # Unauthorized

        espece_name = espece_mapping.get(espece)
        dayclose = remaindate.get(espece_name)
        try:
            dayclose = int(dayclose)
        except (TypeError, ValueError) as e :
            dayclose = 28
        # print(dayclose)

        if dayclose < 0 :
            dayclose = 28

        formatted_date = fromateddate(start_date)
        # print(formatted_date)

        if not formatted_date:
            return jsonify({'message': 'Invalid date format'}), 400  # Bad Request

        data_to_insert = {
            'temperature': temperature if temperature > 0 else 23 ,
            'humidity': humidity if humidity > 0 else 40,
            'start_date': formatted_date,
            'stat_stepper': stat_stepper,
            'number_stepper': number_stepper if number_stepper > 0 else 3,
            'espece': espece_name,
            'timetoclose' : dayclose
        }

        result = post_temp_humidity.create_parameter(data_to_insert)

        if result:
            config_database.close_db_connection()
            return jsonify({'message': 'Data received successfully'}), 200  # Success
        else:
            return jsonify({'message': 'Internal Server Error'}), 500  # Server Error
        
    else:
        result = post_temp_humidity.get_parameter()
        return jsonify(result), 202  # Accepted


    
@app.route('/templates/<path:filename>')
def serve_templates(filename):
    return send_from_directory('templates', filename)


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)



app.secret_key = os.urandom(24)  # Génère une clé secrète aléatoire

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Spécifie la vue de connexion
# Durée de session par défaut (2 jours)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)

# # Dummy user for demonstration purposes
# Gestion des utilisateurs avec Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login.<extension>', methods=['GET', 'POST'])
def login(extension=None):
    if request.method == 'POST':
        # print(request.url)
        # Traitez les données du formulaire ici
        # Vérifier si les données sont envoyées en JSON
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            rememberMe = data.get('rememberMe')
            # print(data,username,password,rememberMe)
        else:
            # Sinon, traiter comme des données de formulaire
            username = request.form.get('username')
            password = request.form.get('password')
            rememberMe = request.form.get('rememberMe')

        if not username or not password :
            return jsonify({'message': 'Username and password required'}), 400
        
        if rememberMe : 
            # Mettre à jour la durée de session ( 1 semaine)
            app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
        
        user_id = post_temp_humidity.login(username,password)
        if user_id :
            user = User(id=user_id)
            login_user(user)
            print("ok")
            return jsonify({'success': True}), 200
            
        else : 
            # error = 'Nom d\'utilisateur ou mot de passe incorrect'
            return jsonify({'message': 'Nom d\'utilisateur ou mot de passe incorrect'}), 401
    
    return render_template('login.html')

@app.route('/check_session', methods=['GET'])
def check_session():
    if current_user.is_authenticated:
        return jsonify({'is_authenticated': True})
    else:
        return jsonify({'is_authenticated': False})



@app.route('/parametre')
@login_required
def parametre():
    return render_template('parametre.html')
    # return f"Welcome {current_user.id}! You are logged in."


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
    
  


app.static_folder = 'static'

if __name__ == "__main__":
    app.run("0.0.0.0",debug=True, port= 5005)


