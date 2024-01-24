from io import BytesIO
from flask import Flask, render_template, request, Response
import json
from jinja2 import Template
from flask_pymongo import PyMongo
from pymongo import MongoClient
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as VirtualCanvas
import datetime
from flask import jsonify


app = Flask(__name__)
cluster_uri = "mongodb+srv://elbourkadi:elbourkadi@cluster0.y8nh7j2.mongodb.net/?retryWrites=true&w=majority"
database_name = "luxeDrive"
collection_name_reservations = "reservations"
collection_name_voitures = "voitures"

try:
    client = MongoClient(cluster_uri)
    db = client[database_name]
    collection_reservations = db[collection_name_reservations]
    collection_voitures = db[collection_name_voitures]

    print("Connected to MongoDB Atlas successfully!")

except Exception as e:
    print("Error connecting to MongoDB Atlas:", e)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/chart')
def chart():
    param = json.loads(request.args.get("param"))
    print(param)

    if param["type"] == "bar":
        try:

            data_from_mongo = collection_reservations.aggregate([
                {"$lookup": {
                    "from": "voitures",
                    "localField": "voiture_id",
                    "foreignField": "_id",
                    "as": "voiture"
                }},
                {"$unwind": "$voiture"},
                {"$group": {"_id": "$voiture.marque", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ])

            labels = []
            values = []

            for entry in data_from_mongo:
                labels.append(entry["_id"])
                values.append(entry["count"])

            fig = Figure()
            ax1 = fig.subplots(1, 1)

            ax1.bar(
                labels,
                values,
                color='blue',
                edgecolor='black',
                linewidth=1,
                alpha=0.7
            )

            # Axes styling
            ax1.set_xlabel('marque voiture', fontsize=12)
            ax1.set_ylabel('Nombre des  Reservations', fontsize=12)
            ax1.set_title('les Top 5 voitures marques par le nombre des reservations', fontsize=14)

            output = BytesIO()
            VirtualCanvas(fig).print_png(output)

            return Response(output.getvalue(), mimetype="image/png")

        except Exception as e:
            print("Error fetching data for bar chart:", e)
            return "Error fetching data for bar chart"

    elif param["type"] == "line":
        current_month = str(datetime.datetime.now().month).zfill(2)
        current_year = str(datetime.datetime.now().year)
        next_month = str((datetime.datetime.now().month % 12) + 1).zfill(2)

        data_from_mongo = db["reservations"].aggregate([
            {"$match": {
                "date_debut": {"$gte": datetime.datetime.strptime(f"{current_year}-{current_month}-01", "%Y-%m-%d"),
                               "$lt": datetime.datetime.strptime(f"{current_year}-{next_month}-01", "%Y-%m-%d")}
            }},
            {"$group": {
                "_id": {"$week": "$date_debut"},  # Group by week
                "total_price": {"$sum": "$Prix_Total"}  # Sum total price
            }},
            {"$sort": {"_id": 1}}
        ])

        labels = []
        values = []

        for entry in data_from_mongo:
            labels.append(f"Semaine {entry['_id']+1}")
            values.append(entry["total_price"])

        fig = Figure()
        ax1 = fig.subplots(1, 1)

        ax1.plot(
            labels,
            values,
            color='green',
            marker='o',
            linestyle='-',
            markersize=8,
            label='Total Price'
        )

        ax1.set_xlabel('', fontsize=12)
        ax1.set_ylabel('Le Prix des  Reservations', fontsize=12)
        ax1.set_title(f'Le revenu de ce mois  {current_month}-{current_year} par semaine', fontsize=14)
        ax1.legend()

    else:
        return "Unsupported chart type"

    output = BytesIO()
    VirtualCanvas(fig).print_png(output)

    return Response(output.getvalue(), mimetype="image/png")




@app.route('/client_chart')
def client_chart():
    desired_status = request.args.get("statuts", "client")

    data_from_mongo = db["users"].aggregate([
        {"$match": {"status": desired_status}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ])

    labels = []
    values = []

    for entry in data_from_mongo:
        labels.append(entry["_id"])
        values.append(entry["count"])

    fig = Figure()
    ax1 = fig.subplots(1, 1)

    ax1.bar(
        labels,
        values,
        color='orange',
        edgecolor='black',
        linewidth=1,
        alpha=0.7
    )

    ax1.set_xlabel('', fontsize=12)
    ax1.set_ylabel('', fontsize=12)
    ax1.set_title(f'nombre des utilisateurs avec status "{desired_status}"', fontsize=14)

    output = BytesIO()
    VirtualCanvas(fig).print_png(output)

    return Response(output.getvalue(), mimetype="image/png")

@app.route('/car_status_pie_chart')
def car_status_pie_chart():
    data_from_mongo = db["voitures"].aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ])

    labels = []
    values = []

    for entry in data_from_mongo:
        labels.append(entry["_id"])
        values.append(entry["count"])

    fig = Figure()
    ax1 = fig.subplots(1, 1)

    ax1.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=['lightgreen', 'lightcoral'],
    )

    ax1.set_title('Disponibilité des voitures', fontsize=14)

    output = BytesIO()
    VirtualCanvas(fig).print_png(output)

    return Response(output.getvalue(), mimetype="image/png")
@app.route('/user_count')
def user_count():
    try:
        user_count = db["users"].count_documents({})

        return f"<h2 style='color: white;' > {user_count}</h2>"

    except Exception as e:
        print("Error fetching user count:", e)
        return "Error fetching user count"

@app.route('/revenue')
def revenue():
    try:
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year

        # Calculate the start and end dates of the current month
        start_date = datetime.datetime(current_year, current_month, 1)
        end_date = datetime.datetime(current_year, current_month + 1, 1)

        # Fetch reservations with a start date in the current month
        data_from_mongo = collection_reservations.aggregate([
            {"$match": {"date_debut": {"$gte": start_date, "$lt": end_date}}},
            {"$group": {"_id": None, "total_revenue": {"$sum": {"$ifNull": ["$Prix_Total", 0]}}}}
        ])

        # Extract the total revenue from the aggregation result
        total_revenue = next(data_from_mongo, {"total_revenue": 0})["total_revenue"]

        return f"<h2 style='color: white;'>{total_revenue} dh</h2>"  # Return h1 with total revenue

    except Exception as e:
        print("Error calculating revenue:", e)
        return "<h1>Error calculating revenue</h1>"
@app.route('/reservations_count')
def reservations_count():
    try:
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year

        # Calculate the start and end dates of the current month
        start_date = datetime.datetime(current_year, current_month, 1)
        end_date = datetime.datetime(current_year, current_month + 1, 1)

        # Count reservations with a start date in the current month
        reservations_count = collection_reservations.count_documents({
            "date_debut": {"$gte": start_date, "$lt": end_date}
        })

        return f"<h2 style='color: white;'>{reservations_count}</h2>"  # Return h1 with reservations count

    except Exception as e:
        print("Error counting reservations:", e)
        return "<h1>Error counting reservations</h1>"
if __name__ == '__main__':
    app.run(debug=True)
