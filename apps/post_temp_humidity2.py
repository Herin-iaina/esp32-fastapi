# -*- coding: utf-8 -*-
import psycopg2
from apps.config_database import *
import datetime
import threading
import pandas as pd
from sqlalchemy import create_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_TEMPERATURE = 37.5
DEFAULT_HUMIDITY = 45
STEPPER_DEFAULT_TIME = "06:00"


# Obtenir la connexion à la base de données
# conn = get_db_connection()

def add_data(data_to_insert) :

    
    # Requête SQL pour l'insertion des données sans spécifier l'identifiant (id)
    sql_insert_query = """
        INSERT INTO data_temp (sensor, temperature, humidity, date_serveur, average_temperature, 
        average_humidity, fan_status, humidifier_status, numfailedsensors)
        VALUES (%(sensor)s, %(temperature)s, %(humidity)s, %(date_serveur)s, 
        %(average_temperature)s, %(average_humidity)s, %(fan_status)s, %(humidifier_status)s, %(numfailedsensors)s )
    """
   
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Exécuter la requête SQL avec les données à insérer
                cursor.execute(sql_insert_query, data_to_insert)
            # Valider les modifications dans la base de données
            conn.commit()
        logger.info("Données insérées avec succès dans la table data_temp.")
        return True
    except psycopg2.Error as e:
        logger.error("Erreur lors de l'insertion des données:", e)
        return False
    # finally:
    #     # Fermer la connexion à la base de données
    #     conn.close()


def post_stepper_status():

    # global stepper
    stepper = "OFF"
    number_stepper = 2
    start_date = ""
    stepper_date = ""
    id_stepper = ""
    date_now = datetime.datetime.today()
    # delai = 60 * 60
    delai = 60 * 60

    select_parameter = """
        SELECT   stat_stepper,number_stepper
        FROM parameter_data ORDER BY id DESC LIMIT 1
        """
    select_stepper = """ SELECT id, start_date, status FROM stepper ORDER BY id DESC LIMIT 1 """
    update_stepper = """ 
        UPDATE stepper 
        SET start_date = %(start_date)s, status = %(status)s 
        WHERE id = %(id)s 
    """
    

    def default_(date_on = None) :

        date_now = datetime.datetime.now()
        # Convert the time difference to a formatted string
        formatted_date = date_now.strftime("%H:%M")
        # Convert formatted_date to datetime object
        formatted_datetime = datetime.datetime.strptime(formatted_date, "%H:%M").time()
        formatted_datetime = datetime.datetime.combine(datetime.datetime.min, formatted_datetime)

        # Convert formatted_date to datetime object
        if not date_on :
            date_on = datetime.datetime.strptime("06:00", "%H:%M").time()
            date_on = datetime.datetime.combine(datetime.datetime.min, date_on)
        else :
             date_on = date_on.strftime("%H:%M")
             date_on = datetime.datetime.strptime(date_on, "%H:%M").time()
             date_on = datetime.datetime.combine(datetime.datetime.min, date_on)

        # date_on = datetime.datetime.combine(datetime.datetime.min, date_on)
        
        # Calculate the time difference
        diff_time = formatted_datetime - date_on
        if diff_time >= datetime.timedelta(hours=0) and diff_time <= datetime.timedelta(hours=0, minutes= 2):
            stepper = "ON"
        else : 
            stepper = "OFF"
        return stepper
    
    def stepper_on():
        stepper = "ON"
        return stepper

    try :
        # Créer un curseur pour exécuter la requête SQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(select_parameter)
        # Récupération des résultats
        # Récupération du premier résultat (le dernier enregistrement)
        resultat = cursor.fetchone()

        cursor.execute(select_stepper)
        resultat_stepper = cursor.fetchone

        if resultat_stepper : 
            stepper_date = resultat_stepper[1]
            id_stepper = resultat_stepper[0]
        else :
            stepper_date = datetime.datetime.strptime('06:00:00', '%H:%M:%S').time()
        

        if resultat :
            stepper = resultat[0]
            number_stepper = resultat[1]
            start_date = resultat[2]

        if start_date :
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            date_diff = date_now - start_date
            if date_diff >= datetime.timedelta(days=20):
                stepper = "OFF"
            else : 
                if  stepper == "ON" :
                    # delai = delai * number_stepper
                    delai = delai / number_stepper
                    if  number_stepper > 0 :
                        # thread = threading.Timer(delai, stepper_on)
                        # thread.start() # Lancer le thread
                        if stepper_date :
                            stepper = default_(stepper_date)
                        else :
                            stepper = default_()
                        # Définir l'heure de départ
                        heure_depart = datetime.datetime.strptime(stepper_date, '%H:%M:%S').time()
                        # Ajouter des heures
                        heure_depart_dt = datetime.datetime.combine(datetime.datetime.today(), heure_depart)
                        heure_arrivee = heure_depart_dt + datetime.timedelta(hours= delai)
                        update_data = {
                            'id': id_stepper,
                            'start_date': heure_arrivee,
                            'status': stepper
                        }
                        cursor.execute(update_stepper,update_data)
                        conn.commit()
                        
    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)
        stepper = "OFF"

    return stepper

def get_last_data():

    average_temperature = 0
    average_humidity = 0
    fan_humidity_status = ["OFF", "OFF"]
    set_temp = 37.3
    set_humid = 45
    start_date = ""
    date_now = datetime.datetime.today()
    date_diff = ""


    sql_select_data = """
    SELECT id, average_temperature, average_humidity 
    FROM data_temp ORDER BY id DESC LIMIT 1
    """
    select_parameter = """
    SELECT temperatur, humidity, start_date
    FROM parameter_data ORDER BY id DESC LIMIT 1
    """
    try : 
        # Créer un curseur pour exécuter la requête SQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_select_data)
        # Récupération des résultats
        # Récupération du premier résultat (le dernier enregistrement)
        resultat = cursor.fetchone()

        cursor.execute(select_parameter)
        resultat_param = cursor.fetchone()

        if resultat_param[0] :
            set_temp = resultat_param[0]
        
        if resultat_param[1] :
            set_humid = resultat[1] 
        
        if resultat_param[2] :
            start_date = resultat_param[2] 

        if start_date : 
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            date_diff = date_now - start_date
            if date_diff >= datetime.timedelta(days=20):
            #    set_temp = set_temp - 0.3 
               set_humid = set_humid + 10

        if resultat:
            average_temperature = resultat[1]
            average_humidity = resultat[2]

        if average_temperature >= set_temp : 
            fan_humidity_status[0] = "OFF"
        else:
            fan_humidity_status[0] = "ON"
        
        if average_humidity >= set_humid :
            fan_humidity_status[1] = "OFF"
        else :
            fan_humidity_status[1] = "ON"

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)

    return fan_humidity_status



def get_all_data(date_ini, date_end):

    conn = get_db_connection()
    resultats = []
    # select_all_data = """
    # SELECT * 
    # FROM data_temp
    # """
    today = datetime.date.today()
    day_after =  today + datetime.timedelta(days=1)
    seven_days_ago = today - datetime.timedelta(days=7)

    select_all_data = """
        SELECT
            sensor,
            date_trunc('minute', date_serveur) as heure,
            AVG(temperature) as temperature,
            AVG(humidity) as humidite, 
            AVG(average_temperature) as temperature_moyenne,
            AVG(average_humidity) as humidite_moyenne,
            AVG(numfailedsensors) as failed       
        FROM
            data_temp
        WHERE
            date_serveur BETWEEN %(date_ini)s AND %(date_end)s
        GROUP BY
            heure,
            sensor
        ORDER BY
            heure;
    """

    if not date_ini or not date_end : 
        date_ini = seven_days_ago
        date_end = day_after

    try :
        conn = get_db_connection()
        cursor = conn.cursor()    
        cursor.execute(select_all_data,{'date_ini' : date_ini ,'date_end' : date_end})
        # Récupération des résultats 
        data  = cursor.fetchall()
        for element in data :
            Sensor = element[0] 
            dateserveur = element[1]
            temperature  = format(element[2], ".2f")
            humidity  = format(element[3], ".2f")
            temperature_moyenne = format(element[4], ".2f")
            humidite_moyenne = format(element[5], ".2f")
            failed = format(element[6], ".0f") if element[6] else 0

            Sensor_Data = {
                'Sensor' : Sensor,
                'date' : dateserveur,
                'temperature' : temperature,
                'humidity' : humidity,
                'temperature_moyenne' : temperature_moyenne,
                'humidite_moyenne' : humidite_moyenne,
                'failed' : failed
            }
            resultats.append(Sensor_Data)
        
        cursor.close()
        conn.close()

    except Exception as e :
        logger.error("Erreur lors de la récupération des données:", e)

    return resultats


def create_parameter(data_to_insert = None):

    date_now = datetime.datetime.today()

    def date_values():
        hour = date_now.hour
        if hour <= 6:
            return datetime.timedelta(hours=6)
        elif hour <= 12:
            return datetime.timedelta(hours=12)
        elif hour <= 18:
            return datetime.timedelta(hours=18)
        return datetime.timedelta(hours=6)
    

    sql_insert_param = """
        INSERT INTO parameter_data (temperature, humidity, start_date, stat_stepper, number_stepper, espece, timetoclose)
        VALUES (37.5, 45, %(start_date)s, 'ON', 3, 'poule', 21)
    """


    select_parameter = """
        SELECT id
        FROM parameter_data
        ORDER BY id DESC
        LIMIT 1
    """

    sql_update_param = """
        UPDATE parameter_data 
        SET temperature = %(temperature)s, humidity = %(humidity)s, start_date = %(start_date)s, 
            stat_stepper = %(stat_stepper)s, number_stepper = %(number_stepper)s, espece = %(espece)s,
            timetoclose = %(timetoclose)s
        WHERE id = %(id)s
    """

    select_stepper = """ 
        SELECT id, start_date, status 
        FROM stepper 
        ORDER BY id DESC 
        LIMIT 1 
    """

    update_stepper = """ 
        UPDATE stepper 
        SET start_date = %(start_date)s, status = %(status)s 
        WHERE id = %(id)s 
    """

    insert_stepper = """
        INSERT INTO stepper (start_date, status)
        VALUES (%(start_date)s, %(status)s)
    """

    try : 
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(select_parameter)
        id_result = cursor.fetchone()

        cursor.execute(select_stepper)
        id_stepper = cursor.fetchone()

        if id_result :

            data_to_insert['id'] = id_result[0]
            cursor.execute(sql_update_param,data_to_insert)
            conn.commit()

        else : 
            cursor.execute(sql_insert_param, {'start_date' : datetime.datetime.today()})
            conn.commit()

        if id_stepper :

            now_timedelta = date_values()
            status = data_to_insert['stat_stepper']
            stepper_v = {
                'id': id_stepper[0],
                'start_date': now_timedelta,
                'status': status
            }

            cursor.execute(update_stepper,stepper_v)
            conn.commit
        else :
            now_timedelta = date_values()
            stepper_data = {
                'start_date': now_timedelta,
                'status': True
            }
            cursor.execute(insert_stepper, stepper_data)
            conn.commit()

        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return False
    
def get_parameter() :

    select_parameter = """
        SELECT id, temperature, humidity, start_date,stat_stepper,number_stepper, espece, timetoclose
        FROM parameter_data ORDER BY id DESC LIMIT 1 """
    
    # select_stepper = """ SELECT id, start_date, status FROM stepper ORDER BY id DESC LIMIT 1 """

    result = {
                'id': 1,
                'temperature': 37.5,
                'humidity': 40,
                'start_date': str(datetime.datetime.today()),
                'stat_stepper': "OFF",
                'number_stepper': 2
            }

    try : 
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(select_parameter)
        id_result = cursor.fetchone()
        result = ""

        # cursor.execute(select_stepper)
        # id_stepper = cursor.fetchone()
        
        # Création du dictionnaire JSON
        if id_result  :
            result = {
                'id': id_result[0],
                'temperature': id_result[1],
                'humidity': id_result[2],
                'start_date': str(id_result[3]),
                'stat_stepper': id_result[4],
                'number_stepper': id_result[5],
                'espece' : id_result[6], 
                'timetoclose' : id_result[7]
            }
        
        else : 
            create_parameter()

        cursor.close()
        conn.close()
    except Exception as e :
        logger.error("Erreur lors de la récupération des données:", e)

    return result


def get_weather_data():

    

    # Combine temperature and humidity queries for efficiency
    select_latest_data = """
    SELECT 
        id,
        average_temperature, 
        average_humidity 
    FROM data_temp 
    ORDER BY id DESC 
    LIMIT 1
    """

    # Combine max temperature and humidity queries for efficiency
    select_max_values = """
        SELECT 
            MAX(temperature) AS max_temperature, 
            MAX(humidity) AS max_humidity 
        FROM data_temp
        WHERE date_serveur >= %(seven_days_ago)s
    """

    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)

    data_send = {}

    try:
        conn = get_db_connection()  # Assume get_db_connection() returns a database connection
        cursor = conn.cursor()

        # Execute the combined queries
        cursor.execute(select_latest_data)
        latest_data = cursor.fetchone()

        logger.info(latest_data)

        cursor.execute(select_max_values, {'seven_days_ago': seven_days_ago})
        max_values = cursor.fetchone()

        if latest_data:
            data_send = {
                'id': latest_data[0],
                'average_temperature': latest_data[1],
                'average_humidity': latest_data[2]
            }

        if max_values:
            data_send.update({
                'temperature': max_values[0],
                'humidity': max_values[1]
            })

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)

    return data_send


def get_data_average () :
    # Requête SQL pour récupérer toutes les données
    query_data = """
    SELECT 
        date_trunc('hour', date_serveur) as heure, 
        AVG(temperature) as temperature_moyenne,
        AVG(humidity) as humidite_moyenne
    FROM 
        data_temp
    WHERE 
        date_trunc('minute', date_serveur) >= %(Today)s
    GROUP BY 
        heure
    ORDER BY 
        heure;
    """

    To_day = datetime.date.today()
    temperatureData = []

    try : 
        conn = get_db_connection()  # Assume get_db_connection() returns a database connection
        cursor = conn.cursor()

        # Execute the combined queries
        cursor.execute(query_data, {'Today': To_day} )
        data = cursor.fetchall()

        for temperature in data :
            hour = temperature[0] 
            temperature_data  = format(temperature[1], ".2f")
            humidity_data  = format(temperature[2], ".2f")
            temperature_Data = {
                'hour' : hour,
                'temperature' : temperature_data,
                'humidity' : humidity_data
            }
            temperatureData.append(temperature_Data)


    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)

    logger.info(temperatureData)

    return temperatureData


def data_table():
    sql_data_table = """
        SELECT
            date_trunc('minute', date_serveur) as heure,
            AVG(temperature) as temperature_moyenne,
            AVG(humidity) as humidite_moyenne, 
            AVG(average_temperature) as temps,
            AVG(average_humidity) as humid,
            AVG(numfailedsensors) as failed,
            sensor
        FROM
            data_temp
        WHERE
            date_serveur >= '2024-07-28'  -- Troncature à la seconde supprimée
        GROUP BY
            heure,
            sensor
        ORDER BY
            heure;
    """


def login(user,password):
    sql_login ="""
       SELECT * FROM login WHERE mail_id = %(user)s
    """
    try : 
        conn = get_db_connection()  # Assume get_db_connection() returns a database connection
        cursor = conn.cursor()
        # Execute the queries
        cursor.execute(sql_login, {'user': user} )
        data = cursor.fetchone()
        logger.info(data)

        if data:
            if password == data[2] :
                return data[0] # Retourner l'ID de l'utilisateur
            else :
                return False
            return data[0]
        else :
            return False
    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)
        return False
    
def getdateinit(date) :
    sqldateinit = """
        SELECT start_date, espece, timetoclose FROM parameter_data
    """
    try : 
        conn = get_db_connection()  # Assume get_db_connection() returns a database connection
        cursor = conn.cursor()
        # Execute the queries
        cursor.execute(sqldateinit )
        data = cursor.fetchone()

        if data:
            try : 
                date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                today = datetime.date.today()
                date_remain =   date - data[0]  
                logger.info(data[0] , date, type(data[0]), type(date))
                days_v = 28 #PouleCanneOieCailleAutre
                if data[1] == "poule" :
                    days_v = 21
                elif data[1] == "canne" :
                    days_v = 28
                elif data[1] == "oie" :
                    days_v = 30
                elif data[1] == "caille" :
                    days_v = 18
                else :
                    days_v = data[2]

                remain_time = datetime.timedelta(days=1)
                days_remain = datetime.timedelta(days=days_v)
                remain_now = today - data[0]

                logger.info( remain_now ,"gdgfgdgdgdg", days_remain)
                logger.info(remain_time,"rrrrrrr",date_remain)

                if today < date :
                    return False
                
                if date < data[0] : 
                    return False

                if date_remain > days_remain or date_remain < remain_time or remain_now > days_remain :
                    return True # Retourner vrais si on peut lancer un nouveau processus
                else :
                    return False

            except Exception as e:
                logger.error("Erreur lors de la récupération des données:", e)
                return False
            
        else :
            return True
    except Exception as e:
        logger.error("Erreur lors de la récupération des données:", e)
        return False

def validate_temperature(temp):
    return isinstance(temp, (int, float)) and 0 <= temp <= 50

def validate_humidity(humid):
    return isinstance(humid, (int, float)) and 0 <= humid <= 100