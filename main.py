from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import DataRequired, URL, AnyOf
import csv
import os
import pandas as pd
import requests
from flight_data import FlightData
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'FLASK_KEY'
# app.config['SECRET_KEY']=  os.environ.get('FLASK_KEY')
Bootstrap5(app)

# CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///cafes.db")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flights.db'

db = SQLAlchemy()
db.init_app(app)

# reading list for cities of the world
cities = pd.read_csv('./simplemaps_worldcities_basicv1.76/worldcities.csv')

# TEQUILA API KEYS
TEQUILA_ENDPOINT = "https://tequila-api.kiwi.com"
TEQUILA_API_KEY = "JCqyS2gjrLh2sHLdX0mGEZS0-R3ky4Nu"


tomorrow = datetime.now() + timedelta(days=(40))
six_month_from_today = datetime.now() + timedelta(days=(7 * 30))


class Flight(db.Model):
    __tablename__ = "flights"
    id = db.Column(db.Integer, primary_key=True)
    origin_city = db.Column(db.String(250), unique=False, nullable=False)
    origin_airport = db.Column(db.String(250), nullable=False)
    destination_city = db.Column(db.String(250), nullable=False)
    destination_airport = db.Column(db.String(250), nullable=False)
    out_date = db.Column(db.Text, nullable=False)
    return_date = db.Column(db.Text, nullable=False)
    airlines = db.Column(db.Text, nullable=False)
    price = db.Column(db.Text, nullable=False)


class Destinations(FlaskForm):
    origin_city = StringField(u'Origin City', validators=[DataRequired(), ])
    city_1 = StringField(u'Destination City', validators=[DataRequired(), ])
    city_2 = StringField(u'Destination City', )
    city_3 = StringField(u'Destination City', )
    city_4 = StringField(u'Destination City', )
    city_5 = StringField(u'Destination City', )
    # origin_city_2 = SelectField(u'Programming Language', choices=cities['city'])
    submit = SubmitField('Submit')


def get_destination_code(city_name):
    location_endpoint = f"{TEQUILA_ENDPOINT}/locations/query"
    headers = {"apikey": TEQUILA_API_KEY}
    query = {"term": city_name, "location_types": "city"}
    response = requests.get(url=location_endpoint, headers=headers, params=query)
    results = response.json()["locations"]
    code = results[0]["code"]
    return code


def check_flights( origin_city_code, destination_city_code, from_time, to_time):
    headers = {"apikey": TEQUILA_API_KEY}
    query = {
        "fly_from": origin_city_code,
        "fly_to": destination_city_code,
        "date_from": from_time.strftime("%d/%m/%Y"),
        "date_to": to_time.strftime("%d/%m/%Y"),
        "nights_in_dst_from": 7,
        "nights_in_dst_to": 21,
        "flight_type": "round",
        "one_for_city": 1,
        "max_stopovers": 0,
        "curr": "AED"
    }

    response = requests.get(
        url=f"{TEQUILA_ENDPOINT}/v2/search",
        headers=headers,
        params=query,
    )

    try:
        data = response.json()["data"][0]
        # data_json = json.dumps(data, indent=4)
        # with open(f"{destination_city_code}.json", "w") as outfile:
        #     outfile.write(data_json)
        # print(data_json)
    except IndexError:
        print(f"No flights found for {destination_city_code}.")
        return None

    flight_data = FlightData(
        price=data["price"],
        origin_city=data["route"][0]["cityFrom"],
        origin_airport=data["route"][0]["flyFrom"],
        destination_city=data["route"][0]["cityTo"],
        destination_airport=data["route"][0]["flyTo"],
        out_date=data["route"][0]["local_departure"].split("T")[0],
        return_date=data["route"][1]["local_departure"].split("T")[0],
        airlines=data["airlines"][0],

    )
    print(
        f"{flight_data.destination_city}: AED{flight_data.price} : from {flight_data.out_date} : to {flight_data.return_date} : on {flight_data.airlines} airlines")
    return flight_data


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/add', methods=["GET", "POST"])
def add_flight():
    form = Destinations()
    destination_codes = []
    if form.validate_on_submit():
        for field in form:
            if "city" in field.name and field.data != "":
                destination_codes.append(get_destination_code(field.data))

        for destination in destination_codes[1:]:
            flight = check_flights(destination_codes[0], destination, tomorrow, six_month_from_today)
            if flight is not None:
                new_flight = Flight(
                origin_city= flight.origin_city,
                origin_airport = flight.origin_airport,
                destination_city = flight.destination_city,
                destination_airport = flight.destination_airport,
                out_date = flight.out_date,
                return_date = flight.return_date,
                airlines = flight.airlines,
                price = flight.price,
                )
                db.session.add(new_flight)
                db.session.commit()

        return redirect(url_for('flights'))
    return render_template('add.html', form=form)


@app.route('/flights')
def flights():


    result = db.session.execute(db.select(Flight))
    flights = result.scalars().all()

    return render_template('flights.html', all_flights=flights)


if __name__ == '__main__':
    app.run(debug=True, port=5002)
