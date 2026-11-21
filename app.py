
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date, timedelta
import os

app = Flask(__name__)

DATABASE = "journey.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    conn = get_db()

    with open("schema.sql", "r") as file:
        conn.executescript(file.read())

    count = conn.execute(
        "SELECT COUNT(*) FROM journeys"
    ).fetchone()[0]

    if count == 0:
        buses = [
            ("Express Travels", "Hyderabad", "Bangalore",
             "08:00", "18:00", 1200, 35),
            ("Green Line", "Hyderabad", "Chennai",
             "09:30", "20:00", 1500, 30),
            ("Royal Bus", "Hyderabad", "Mumbai",
             "20:00", "08:00", 1800, 40),
            ("City Express", "Bangalore", "Hyderabad",
             "07:00", "17:00", 1100, 35),
            ("Orange Travels", "Chennai", "Hyderabad",
             "21:00", "08:00", 1400, 30)
        ]

        for offset in range(1, 8):
            journey_date = (
                date.today() + timedelta(days=offset)
            ).isoformat()

            for bus in buses:
                conn.execute("""
                    INSERT INTO journeys (
                        bus_name, source, destination,
                        departure_time, arrival_time,
                        journey_date, price, available_seats
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bus[0], bus[1], bus[2],
                    bus[3], bus[4], journey_date,
                    bus[5], bus[6]
                ))

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/journeys", methods=["GET"])
def search_journeys():
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    journey_date = request.args.get("date", "")

    if not source or not destination or not journey_date:
        return jsonify({"error": "Please fill all search fields"}), 400

    conn = get_db()

    journeys = conn.execute("""
        SELECT * FROM journeys
        WHERE LOWER(source) = LOWER(?)
        AND LOWER(destination) = LOWER(?)
        AND journey_date = ?
        AND available_seats > 0
        ORDER BY departure_time
    """, (source, destination, journey_date)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in journeys])


@app.route("/api/book", methods=["POST"])
def book_ticket():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    journey_id = data.get("journey_id")
    seats = data.get("seats")

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    if len(name) > 100 or len(email) > 150 or "@" not in email:
        return jsonify({"error": "Please enter valid details"}), 400

    if isinstance(journey_id, bool) or not isinstance(journey_id, int):
        return jsonify({"error": "Invalid journey"}), 400

    if isinstance(seats, bool) or not isinstance(seats, int) or not 1 <= seats <= 6:
        return jsonify({"error": "Select between 1 and 6 seats"}), 400

    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        journey = conn.execute("""
            SELECT * FROM journeys
            WHERE journey_id = ?
        """, (journey_id,)).fetchone()

        if not journey:
            conn.rollback()
            return jsonify({"error": "Journey not found"}), 404

        if journey["available_seats"] < seats:
            conn.rollback()
            return jsonify({"error": "Not enough seats available"}), 400

        total = journey["price"] * seats

        conn.execute("""
            UPDATE journeys
            SET available_seats = available_seats - ?
            WHERE journey_id = ?
        """, (seats, journey_id))

        cursor = conn.execute("""
            INSERT INTO bookings (
                passenger_name, passenger_email,
                journey_id, seats, total_amount
            )
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, journey_id, seats, total))

        booking_id = cursor.lastrowid
        conn.commit()

        return jsonify({
            "message": "Ticket booked successfully!",
            "booking_id": booking_id,
            "total_amount": total
        })

    except sqlite3.Error:
        conn.rollback()
        return jsonify({"error": "Booking failed. Please try again."}), 500

    finally:
        conn.close()


@app.route("/api/bookings", methods=["GET"])
def my_bookings():
    email = request.args.get("email", "").strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = get_db()

    bookings = conn.execute("""
        SELECT
            b.booking_id,
            b.passenger_name,
            b.passenger_email,
            b.seats,
            b.total_amount,
            b.booking_status,
            j.bus_name,
            j.source,
            j.destination,
            j.journey_date,
            j.departure_time,
            j.arrival_time
        FROM bookings b
        JOIN journeys j ON b.journey_id = j.journey_id
        WHERE LOWER(b.passenger_email) = LOWER(?)
        ORDER BY b.booking_id DESC
    """, (email,)).fetchall()

    conn.close()

    return jsonify([dict(row) for row in bookings])


@app.route("/api/cancel/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        booking = conn.execute("""
            SELECT * FROM bookings
            WHERE booking_id = ?
            AND LOWER(passenger_email) = LOWER(?)
        """, (booking_id, email)).fetchone()

        if not booking:
            conn.rollback()
            return jsonify({"error": "Booking not found"}), 404

        if booking["booking_status"] == "Cancelled":
            conn.rollback()
            return jsonify({"error": "Already cancelled"}), 400

        conn.execute("""
            UPDATE bookings
            SET booking_status = 'Cancelled'
            WHERE booking_id = ?
        """, (booking_id,))

        conn.execute("""
            UPDATE journeys
            SET available_seats = available_seats + ?
            WHERE journey_id = ?
        """, (booking["seats"], booking["journey_id"]))

        conn.commit()

        return jsonify({"message": "Booking cancelled successfully"})

    except sqlite3.Error:
        conn.rollback()
        return jsonify({"error": "Cancellation failed"}), 500

    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
