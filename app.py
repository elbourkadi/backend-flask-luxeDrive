from io import BytesIO
from flask import Flask, render_template, request, Response
import json
from flask_pymongo import PyMongo
from pymongo import MongoClient
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as VirtualCanvas
import datetime

app = Flask(__name__)
cluster_uri = "mongodb+srv://elbourkadi:elbourkadi@cluster0.y8nh7j2.mongodb.net/?retryWrites=true&w=majority"
database_name = "luxeDrive"
collection_name = "voitures"

try:
    client = MongoClient(cluster_uri)
    db = client[database_name]
    collection = db[collection_name]

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
        data_from_mongo = collection.aggregate([
            {"$group": {"_id": "$marque", "count": {"$sum": 1}}},
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

        ax1.set_xlabel('', fontsize=12)
        ax1.set_ylabel('nombre de nos voitures', fontsize=12)
        ax1.set_title('les top 5 marques les plus populaires à louer', fontsize=14)

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
            labels.append(f"Week {entry['_id']+1}")
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
        ax1.set_ylabel('Total Price of Reservations', fontsize=12)
        ax1.set_title(f'Total Price of Reservations in {current_month}-{current_year} Grouped by Week', fontsize=14)
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

    ax1.set_title('Disponibilite des voitures', fontsize=14)

    output = BytesIO()
    VirtualCanvas(fig).print_png(output)

    return Response(output.getvalue(), mimetype="image/png")

if __name__ == '__main__':
    app.run(debug=True)
