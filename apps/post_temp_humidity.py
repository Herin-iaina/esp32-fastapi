# -*- coding: utf-8 -*-
import datetime
import logging
from sqlalchemy import func
from apps.database_configuration import (
    db_manager, 
    DataTempModel, 
    StepperModel, 
    ParameterDataModel
)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_data(data_to_insert):
    try:
        with db_manager.get_session_context() as session:
            new_data = DataTempModel(
                sensor=data_to_insert['sensor'],
                temperature=data_to_insert['temperature'],
                humidity=data_to_insert['humidity'],
                date_serveur=data_to_insert.get('date_serveur', datetime.datetime.now()),
                average_temperature=data_to_insert['average_temperature'],
                average_humidity=data_to_insert['average_humidity'],
                fan_status=data_to_insert['fan_status'],
                humidifier_status=data_to_insert['humidifier_status'],
                numfailedsensors=data_to_insert['numfailedsensors']
            )
            session.add(new_data)
            logger.info("Données insérées avec succès dans la table data_temp.")
            return True
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion des données: {e}")
        return False


def post_stepper_status():
    try:
        with db_manager.get_session_context() as session:
            # Récupérer les derniers paramètres
            parameter = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
            stepper = session.query(StepperModel).order_by(StepperModel.id.desc()).first()
            
            current_status = "OFF"
            if parameter and parameter.stat_stepper:
                current_status = "ON"
                
            return current_status
            
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du status stepper: {e}")
        return "OFF"

def get_last_data():
    try:
        with db_manager.get_session_context() as session:
            last_data = session.query(DataTempModel).order_by(DataTempModel.id.desc()).first()
            
            if last_data:
                return {
                    'average_temperature': last_data.average_temperature,
                    'average_humidity': last_data.average_humidity
                }
            return None
            
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        return None
    finally:
        session.close()
        
def get_all_data(date_ini, date_end):
    try:
        with db_manager.get_session_context() as session:
            if not date_ini or not date_end:
                today = datetime.date.today()
                date_end = today + datetime.timedelta(days=1)
                date_ini = today - datetime.timedelta(days=7)

            query = session.query(
                DataTempModel.sensor,
                func.date_trunc('minute', DataTempModel.date_serveur).label('heure'),
                func.avg(DataTempModel.temperature).label('temperature'),
                func.avg(DataTempModel.humidity).label('humidite'),
                func.avg(DataTempModel.average_temperature).label('temperature_moyenne'),
                func.avg(DataTempModel.average_humidity).label('humidite_moyenne'),
                func.avg(DataTempModel.numfailedsensors).label('failed')
            ).filter(
                DataTempModel.date_serveur.between(date_ini, date_end)
            ).group_by(
                'heure',
                DataTempModel.sensor
            ).order_by('heure')

            results = []
            for row in query.all():
                results.append({
                    'Sensor': row.sensor,
                    'date': row.heure,
                    'temperature': format(row.temperature, ".2f"),
                    'humidity': format(row.humidite, ".2f"),
                    'temperature_moyenne': format(row.temperature_moyenne, ".2f"),
                    'humidite_moyenne': format(row.humidite_moyenne, ".2f"),
                    'failed': format(row.failed, ".0f") if row.failed else "0"
                })
            return results

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        return []
    
def create_parameter(data_to_insert=None):
    try:
        with db_manager.get_session_context() as session:
            # Valeurs par défaut
            default_values = {
                'temperature': 37.5,
                'humidity': 45,
                'start_date': datetime.datetime.today(),
                'stat_stepper': True,
                'number_stepper': 3,
                'espece': 'poule',
                'timetoclose': 21
            }

            # Si des données sont fournies, les utiliser, sinon utiliser les valeurs par défaut
            parameter_data = data_to_insert if data_to_insert else default_values

            # Récupérer le dernier paramètre
            last_parameter = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()

            if last_parameter:
                # Mise à jour du paramètre existant
                for key, value in parameter_data.items():
                    setattr(last_parameter, key, value)
            else:
                # Création d'un nouveau paramètre
                new_parameter = ParameterDataModel(**default_values)
                session.add(new_parameter)

            # Gestion du stepper
            last_stepper = session.query(StepperModel).order_by(StepperModel.id.desc()).first()
            
            def get_time_hour():
                hour = datetime.datetime.now().hour
                if hour <= 6:
                    return datetime.time(6, 0, 0)
                elif hour <= 12:
                    return datetime.time(12, 0, 0)
                elif hour <= 18:
                    return datetime.time(18, 0, 0)
                return datetime.time(6, 0, 0)

            now_time = get_time_hour()
            
            stepper_status = parameter_data.get('stat_stepper', True)

            if last_stepper:
                # Mise à jour du stepper existant
                last_stepper.start_date = now_time
                last_stepper.status = stepper_status
            else:
                # Création d'un nouveau stepper
                new_stepper = StepperModel(
                    start_date=now_time,
                    status=stepper_status
                )
                session.add(new_stepper)

            session.commit()
            logger.info("Paramètres créés/mis à jour avec succès")
            return True

    except Exception as e:
        logger.error(f"Erreur lors de la création/mise à jour des paramètres: {e}")
        return False
    
def get_parameter():
    try:
        with db_manager.get_session_context() as session:
            # Récupérer le dernier paramètre
            parameter = session.query(ParameterDataModel).order_by(ParameterDataModel.id.desc()).first()
            
            if parameter:
                result = {
                    'id': parameter.id,
                    'temperature': parameter.temperature,
                    'humidity': parameter.humidity,
                    'start_date': str(parameter.start_date),
                    'stat_stepper': parameter.stat_stepper,
                    'number_stepper': parameter.number_stepper,
                    'espece': parameter.espece,
                    'timetoclose': parameter.timetoclose
                }
            else:
                # Si aucun paramètre n'existe, créer un nouveau
                result = create_parameter()
                if not result:
                    # Retourner des valeurs par défaut si la création échoue
                    return {
                        'id': 1,
                        'temperature': 37.5,
                        'humidity': 40,
                        'start_date': str(datetime.datetime.today()),
                        'stat_stepper': "OFF",
                        'number_stepper': 2,
                        'espece': 'poule',
                        'timetoclose': 21
                    }
            
            return result

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres: {e}")
        # Retourner des valeurs par défaut en cas d'erreur
        return {
            'id': 1,
            'temperature': 37.5,
            'humidity': 40,
            'start_date': str(datetime.datetime.today()),
            'stat_stepper': "OFF",
            'number_stepper': 2,
            'espece': 'poule',
            'timetoclose': 21
        }
def get_weather_data():
    try:
        with db_manager.get_session_context() as session:
            # Récupérer les dernières données
            latest_data = session.query(DataTempModel).order_by(DataTempModel.id.desc()).first()
            
            # Calculer la date d'il y a 7 jours
            seven_days_ago = datetime.date.today() - datetime.timedelta(days=7)
            
            # Récupérer les valeurs maximales
            max_values = session.query(
                func.max(DataTempModel.temperature).label('max_temperature'),
                func.max(DataTempModel.humidity).label('max_humidity')
            ).filter(DataTempModel.date_serveur >= seven_days_ago).first()

            data_send = {}
            if latest_data:
                data_send = {
                    'id': latest_data.id,
                    'average_temperature': latest_data.average_temperature,
                    'average_humidity': latest_data.average_humidity
                }

            if max_values:
                data_send.update({
                    'temperature': max_values.max_temperature,
                    'humidity': max_values.max_humidity
                })

            return data_send

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        return {}

def data_table():
    try:
        with db_manager.get_session_context() as session:
            data = session.query(
                func.date_trunc('minute', DataTempModel.date_serveur).label('heure'),
                func.avg(DataTempModel.temperature).label('temperature_moyenne'),
                func.avg(DataTempModel.humidity).label('humidite_moyenne'),
                func.avg(DataTempModel.average_temperature).label('temps'),
                func.avg(DataTempModel.average_humidity).label('humid'),
                func.avg(DataTempModel.numfailedsensors).label('failed'),
                DataTempModel.sensor
            ).filter(
                DataTempModel.date_serveur >= '2024-07-28'
            ).group_by(
                'heure',
                DataTempModel.sensor
            ).order_by('heure')
            
            return data.all()

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données: {e}")
        return []

def getdateinit(date):
    try:
        with db_manager.get_session_context() as session:
            parameter_data = session.query(
                ParameterDataModel.start_date,
                ParameterDataModel.espece,
                ParameterDataModel.timetoclose
            ).first()

            if parameter_data:
                try:
                    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                    today = datetime.date.today()
                    date_remain = date - parameter_data.start_date.date()

                    days_v = {
                        "poule": 21,
                        "canne": 28,
                        "oie": 30,
                        "caille": 18
                    }.get(parameter_data.espece, parameter_data.timetoclose)

                    remain_time = datetime.timedelta(days=1)
                    days_remain = datetime.timedelta(days=days_v)
                    remain_now = today - parameter_data.start_date.date()

                    if today < date or date < parameter_data.start_date.date():
                        return False

                    return date_remain > days_remain or date_remain < remain_time or remain_now > days_remain

                except Exception as e:
                    logger.error(f"Erreur lors du calcul des dates: {e}")
                    return False
            return True

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres: {e}")
        return False

def validate_temperature(temp):
    return isinstance(temp, (int, float)) and 0 <= temp <= 50

def validate_humidity(humid):
    return isinstance(humid, (int, float)) and 0 <= humid <= 100


def get_data_average():
    try:
        with db_manager.get_session_context() as session:
            today = datetime.date.today()
            query = session.query(
                func.date_trunc('hour', DataTempModel.date_serveur).label('heure'),
                func.avg(DataTempModel.temperature).label('temperature_moyenne'),
                func.avg(DataTempModel.humidity).label('humidite_moyenne')
            ).filter(
                func.date_trunc('minute', DataTempModel.date_serveur) >= today
            ).group_by(
                'heure'
            ).order_by('heure')

            temperatureData = []
            for row in query.all():
                temperatureData.append({
                    'hour': row.heure,
                    'temperature': format(row.temperature_moyenne, ".2f"),
                    'humidity': format(row.humidite_moyenne, ".2f")
                })
            return temperatureData

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des moyennes: {e}")
        return []
    finally:
        session.close()