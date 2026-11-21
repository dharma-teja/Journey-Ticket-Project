
const searchForm = document.getElementById("searchForm");
const results = document.getElementById("results");
const message = document.getElementById("message");
const bookingModal = document.getElementById("bookingModal");

const today = new Date();
today.setMinutes(today.getMinutes() - today.getTimezoneOffset());

document.getElementById("journeyDate").min =
    today.toISOString().split("T")[0];


function showMessage(text, error = false) {
    message.innerHTML = "";

    const alert = document.createElement("div");
    alert.className = error ? "alert error" : "alert";
    alert.textContent = text;

    message.appendChild(alert);
}


function addText(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;

    if (className) {
        element.className = className;
    }

    parent.appendChild(element);
    return element;
}


// Search journeys
searchForm.addEventListener("submit", async function(e) {
    e.preventDefault();

    const source = document.getElementById("source").value;
    const destination = document.getElementById("destination").value;
    const date = document.getElementById("journeyDate").value;

    if (source.toLowerCase() === destination.toLowerCase()) {
        showMessage("Source and destination cannot be the same.", true);
        return;
    }

    results.textContent = "Searching buses...";

    try {
        const response = await fetch(
            `/api/journeys?source=${encodeURIComponent(source)}&destination=${encodeURIComponent(destination)}&date=${encodeURIComponent(date)}`
        );

        const data = await response.json();

        results.replaceChildren();

        if (!response.ok) {
            showMessage(data.error || "Search failed", true);
            return;
        }

        if (data.length === 0) {
            results.textContent = "No buses available for this journey.";
            return;
        }

        showMessage(`${data.length} buses found!`);

        data.forEach(bus => {
            const card = document.createElement("div");
            card.className = "bus-card";

            addText(card, "h3", bus.bus_name);
            addText(card, "p", `From: ${bus.source}`);
            addText(card, "p", `To: ${bus.destination}`);
            addText(card, "p", `Date: ${bus.journey_date}`);
            addText(card, "p", `Departure: ${bus.departure_time}`);
            addText(card, "p", `Arrival: ${bus.arrival_time}`);
            addText(card, "p", `Available seats: ${bus.available_seats}`);
            addText(card, "p", `₹${bus.price}`, "price");

            const button = document.createElement("button");
            button.textContent = "Book Now";

            button.addEventListener("click", () => {
                openBooking(bus);
            });

            card.appendChild(button);
            results.appendChild(card);
        });

    } catch (error) {
        showMessage("Unable to connect to the server.", true);
    }
});


// Open booking popup
function openBooking(bus) {
    document.getElementById("selectedJourney").value = bus.journey_id;

    document.getElementById("seats").max =
        Math.min(bus.available_seats, 6);

    document.getElementById("seats").value = 1;

    bookingModal.style.display = "flex";
}


// Close booking popup
document.getElementById("closeModal").addEventListener("click", () => {
    bookingModal.style.display = "none";
});


// Book ticket
document.getElementById("bookingForm").addEventListener(
    "submit", async function(e) {
        e.preventDefault();

        const data = {
            name: document.getElementById("passengerName").value,
            email: document.getElementById("passengerEmail").value,
            journey_id: Number(document.getElementById("selectedJourney").value),
            seats: Number(document.getElementById("seats").value)
        };

        try {
            const response = await fetch("/api/book", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                showMessage(result.error, true);
                return;
            }

            bookingModal.style.display = "none";

            document.getElementById("bookingForm").reset();

            showMessage(
                `Booking successful! Booking ID: ${result.booking_id}. Total: ₹${result.total_amount}`
            );

            document.getElementById("bookingEmail").value = data.email;

            loadBookings(data.email);

            searchForm.dispatchEvent(
                new Event("submit", { bubbles: true, cancelable: true })
            );

        } catch (error) {
            showMessage("Booking failed. Please try again.", true);
        }
    }
);


// View booking history
document.getElementById("bookingSearchForm").addEventListener(
    "submit", function(e) {
        e.preventDefault();

        const email = document.getElementById("bookingEmail").value.trim();

        loadBookings(email);
    }
);


async function loadBookings(email) {
    const container = document.getElementById("bookingResults");

    container.textContent = "Loading bookings...";

    try {
        const response = await fetch(
            `/api/bookings?email=${encodeURIComponent(email)}`
        );

        const data = await response.json();

        container.replaceChildren();

        if (!response.ok) {
            container.textContent = data.error || "Unable to load bookings.";
            return;
        }

        if (data.length === 0) {
            container.textContent = "No bookings found.";
            return;
        }

        data.forEach(booking => {
            const card = document.createElement("div");
            card.className = "booking-card";

            addText(card, "h3", `Booking ID: ${booking.booking_id}`);
            addText(card, "p", `Passenger: ${booking.passenger_name}`);
            addText(card, "p", `Bus: ${booking.bus_name}`);
            addText(card, "p", `Route: ${booking.source} to ${booking.destination}`);
            addText(card, "p", `Date: ${booking.journey_date}`);
            addText(card, "p", `Seats: ${booking.seats}`);
            addText(card, "p", `Total: ₹${booking.total_amount}`);

            const status = addText(
                card,
                "p",
                `Status: ${booking.booking_status}`,
                booking.booking_status === "Cancelled"
                    ? "status cancelled"
                    : "status"
            );

            if (booking.booking_status === "Confirmed") {
                const cancelButton = document.createElement("button");

                cancelButton.textContent = "Cancel Booking";
                cancelButton.className = "cancel-btn";

                cancelButton.addEventListener("click", () => {
                    cancelBooking(booking.booking_id, email);
                });

                card.appendChild(cancelButton);
            }

            container.appendChild(card);
        });

    } catch (error) {
        container.textContent = "Unable to connect to server.";
    }
}


// Cancel booking
async function cancelBooking(bookingId, email) {
    if (!confirm("Are you sure you want to cancel this booking?")) {
        return;
    }

    try {
        const response = await fetch(`/api/cancel/${bookingId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email })
        });

        const result = await response.json();

        if (!response.ok) {
            showMessage(result.error, true);
            return;
        }

        showMessage(result.message);

        loadBookings(email);

    } catch (error) {
        showMessage("Unable to cancel booking.", true);
    }
}
