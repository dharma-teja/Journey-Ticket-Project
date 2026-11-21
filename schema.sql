
CREATE TABLE IF NOT EXISTS journeys (
    journey_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_name TEXT NOT NULL,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    journey_date TEXT NOT NULL,
    price REAL NOT NULL,
    available_seats INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_name TEXT NOT NULL,
    passenger_email TEXT NOT NULL,
    journey_id INTEGER NOT NULL,
    seats INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    booking_status TEXT DEFAULT 'Confirmed',
    FOREIGN KEY (journey_id) REFERENCES journeys(journey_id)
);
